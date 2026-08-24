import json
import os
import pickle
import sys
import threading
import numpy as np
import torch
import torch.nn as nn
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.model_loader import download_production_model_dir

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "play_call_weights")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
class PlayCallMLP(nn.Module):
    def __init__(self, feat_cardinality: dict, emb_dim: int, hidden: int, n_classes: int):
        super().__init__()
        self.feat_names = list(feat_cardinality.keys())
        self.embeddings = nn.ModuleList([
            nn.Embedding(card, emb_dim) for card in feat_cardinality.values()
        ])
        in_dim = len(feat_cardinality) * emb_dim
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.LayerNorm(hidden),
            nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden), nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden, hidden // 2),
            nn.LayerNorm(hidden // 2),
            nn.SiLU(),
            nn.Linear(hidden // 2, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        embs = [self.embeddings[i](x[:, i]) for i in range(len(self.feat_names))]
        return self.net(torch.cat(embs, dim=-1))

_model_state = {
    "ready": False,
    "error": None,
    "model": None,
    "classes": None,
}

def _load_model_blocking():
    try:
        try:
            model_dir = download_production_model_dir("play-call-model")
            print(f"Loaded play-call-model from WandB production artifact: {model_dir}")
        except Exception as e:
            print(f"WARNING: could not pull production model from WandB ({e}). Falling back to local weights.")
            model_dir = WEIGHTS_DIR

        with open(f"{model_dir}/play_call_config.json") as f:
            cfg = json.load(f)
        with open(f"{model_dir}/play_call_feature_meta.json") as f:
            meta = json.load(f)
        with open(f"{model_dir}/play_call_label_encoder.pkl", "rb") as f:
            le = pickle.load(f)

        feat_cardinality = meta["feat_cardinality"]
        classes = meta["classes"]

        model = PlayCallMLP(feat_cardinality, cfg["emb_dim"], cfg["hidden"], cfg["n_classes"]).to(DEVICE)
        model.load_state_dict(torch.load(f"{model_dir}/play_call_model.pt", map_location=DEVICE))
        model.eval()
        print(f"Play call model loaded on {DEVICE}. Classes: {classes}")

        _model_state.update({
            "model": model,
            "classes": classes,
            "ready": True,
        })
    except Exception as e:
        _model_state["error"] = str(e)
        print(f"ERROR loading play call model: {e}")

def _dist_bucket(x: float) -> int:
    if x <= 2: return 0
    elif x <= 6: return 1
    elif x <= 10: return 2
    else: return 3

def _yard_zone(yardline_100: float) -> int:
    if yardline_100 >= 80: return 0
    elif yardline_100 >= 60: return 1
    elif yardline_100 >= 40: return 2
    elif yardline_100 >= 20: return 3
    elif yardline_100 >= 5: return 4
    else: return 5

def _score_bucket(x: float) -> int:
    if x <= -17: return 0
    elif x <= -7: return 1
    elif x <= 6: return 2
    elif x <= 16: return 3
    else: return 4

def _time_bucket(game_seconds_remaining: float, qtr: int) -> int:
    if game_seconds_remaining <= 120 and qtr >= 4: return 0
    elif game_seconds_remaining <= 480 and qtr == 4: return 1
    elif qtr == 3 or (qtr == 4 and game_seconds_remaining > 480): return 2
    elif qtr == 2: return 3
    else: return 4

def encode_features(
    down: int,
    ydstogo: float,
    yardline_100: float,
    score_differential: float,
    qtr: int,
    game_seconds_remaining: float,
    shotgun: int = 0,
    goal_to_go: int = 0,
) -> torch.Tensor:
    half_end = int(
        (qtr == 2 and game_seconds_remaining <= 1860) or
        (qtr >= 4 and game_seconds_remaining <= 120)
    )
    trailing = int(score_differential < 0)
    feats = [
        max(0, min(3, down - 1)),
        _dist_bucket(ydstogo),
        _yard_zone(yardline_100),
        _score_bucket(score_differential),
        max(0, min(4, qtr - 1)),
        _time_bucket(game_seconds_remaining, qtr),
        half_end,
        trailing,
        min(1, max(0, shotgun)),
        min(1, max(0, goal_to_go)),
    ]
    return torch.LongTensor([feats]).to(DEVICE)

app = FastAPI(title="Play Call Predictor", version="1.0")

@app.on_event("startup")
async def _startup():
    threading.Thread(target=_load_model_blocking, daemon=True).start()
class GameState(BaseModel):
    down: int
    ydstogo: float
    yardline_100: float
    score_differential: float
    qtr: int
    game_seconds_remaining: float
    shotgun: int = 0
    goal_to_go: int = 0
class PredictRequest(BaseModel):
    game_state: GameState

@app.get("/health")
def health():
    if _model_state["error"]:
        return {"status": "error", "detail": _model_state["error"]}
    if not _model_state["ready"]:
        return {"status": "loading"}
    return {"status": "ok", "device": DEVICE, "classes": _model_state["classes"]}

@app.post("/predict")
def predict(req: PredictRequest):
    if not _model_state["ready"]:
        raise HTTPException(status_code=503, detail="Model still loading, try again shortly.")

    gs = req.game_state
    try:
        x = encode_features(
            down=gs.down,
            ydstogo=gs.ydstogo,
            yardline_100=gs.yardline_100,
            score_differential=gs.score_differential,
            qtr=gs.qtr,
            game_seconds_remaining=gs.game_seconds_remaining,
            shotgun=gs.shotgun,
            goal_to_go=gs.goal_to_go,
        )
        model = _model_state["model"]
        classes = _model_state["classes"]
        with torch.no_grad():
            probs = torch.softmax(model(x), dim=-1).cpu().numpy()[0]
        return {cls: float(p) for cls, p in zip(classes, probs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("play_call_inference:app", host="0.0.0.0", port=8003, reload=False)