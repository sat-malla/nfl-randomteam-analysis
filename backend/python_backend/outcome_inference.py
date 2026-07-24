import json
import os
import pickle

import torch
import torch.nn as nn
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "outcome_model_weights")

with open(f"{WEIGHTS_DIR}/outcome_config.json") as f:
    CFG = json.load(f)
with open(f"{WEIGHTS_DIR}/outcome_feature_meta.json") as f:
    META = json.load(f)
with open(f"{WEIGHTS_DIR}/outcome_yards_scaler.pkl", "rb") as f:
    YARDS_SCALER = pickle.load(f)
with open(f"{WEIGHTS_DIR}/outcome_punt_yards_scaler.pkl", "rb") as f:
    PUNT_YARDS_SCALER = pickle.load(f)

FEAT_CARDINALITY: dict = META["feat_cardinality"]
PLAY_TYPE_MAP: dict = META["play_type_map"]
RECEIVER_POS: dict = META["receiver_pos_classes"]
FG_RESULT: dict = META["fg_result_classes"]

EMB_DIM: int = CFG["emb_dim"]
HIDDEN: int = CFG["hidden"]

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

class OutcomeMLP(nn.Module):
    def __init__(self, feat_cardinality: dict, emb_dim: int, hidden: int):
        super().__init__()
        self.feat_names = list(feat_cardinality.keys())
        self.embeddings = nn.ModuleList([
            nn.Embedding(card, emb_dim) for card in feat_cardinality.values()
        ])
        in_dim = len(feat_cardinality) * emb_dim
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, hidden), 
            nn.LayerNorm(hidden), 
            nn.SiLU(), 
            nn.Dropout(0.3),
            nn.Linear(hidden, hidden), 
            nn.LayerNorm(hidden), 
            nn.SiLU(), 
            nn.Dropout(0.3),
            nn.Linear(hidden, hidden // 2), 
            nn.LayerNorm(hidden // 2), 
            nn.SiLU(),
        )
        h = hidden // 2
        self.yards_head = nn.Linear(h, 1)
        self.turnover_head = nn.Linear(h, 2)
        self.td_head = nn.Linear(h, 2)
        self.receiver_pos_head = nn.Linear(h, 3)
        self.punt_yards_head = nn.Linear(h, 1)
        self.punt_blocked_head = nn.Linear(h, 2)
        self.fg_result_head = nn.Linear(h, 3)

    def forward(self, x: torch.Tensor):
        embs = [self.embeddings[i](x[:, i]) for i in range(len(self.feat_names))]
        h = self.encoder(torch.cat(embs, dim=-1))
        return (
            self.yards_head(h).squeeze(-1),
            self.turnover_head(h),
            self.td_head(h),
            self.receiver_pos_head(h),
            self.punt_yards_head(h).squeeze(-1),
            self.punt_blocked_head(h),
            self.fg_result_head(h),
        )


model = OutcomeMLP(FEAT_CARDINALITY, EMB_DIM, HIDDEN).to(DEVICE)
model.load_state_dict(torch.load(f"{WEIGHTS_DIR}/outcome_model.pt", map_location=DEVICE))
model.eval()
print(f"Outcome model loaded on {DEVICE}.")

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

def _air_yards_bucket(x: float) -> int:
    if x < 0: return 0
    elif x <= 5: return 1
    elif x <= 15: return 2
    else: return 3

def _kick_dist_bucket(x: float) -> int:
    if x <= 30: return 0
    elif x <= 40: return 1
    elif x <= 50: return 2
    else: return 3

def encode_features(
    play_type: str,
    down: int,
    ydstogo: float,
    yardline_100: float,
    score_differential: float,
    qtr: int,
    shotgun: int = 0,
    goal_to_go: int = 0,
    air_yards: float = 0.0,
    kick_distance: float = 0.0,
) -> torch.Tensor:
    feats = [
        PLAY_TYPE_MAP.get(play_type, 0),
        max(0, min(3, down - 1)),
        _dist_bucket(ydstogo),
        _yard_zone(yardline_100),
        _score_bucket(score_differential),
        max(0, min(4, qtr - 1)),
        min(1, max(0, shotgun)),
        min(1, max(0, goal_to_go)),
        _air_yards_bucket(air_yards),
        _kick_dist_bucket(kick_distance),
    ]
    return torch.LongTensor([feats]).to(DEVICE)

app = FastAPI(title="Outcome Predictor", version="1.0")

class PlayRequest(BaseModel):
    play_type: str               # "run" | "pass" | "punt" | "field_goal"
    down: int                    # 1-4
    ydstogo: float
    yardline_100: float          # yards to opponent end zone
    score_differential: float    # offense - defense
    qtr: int                     # 1-5
    shotgun: int = 0
    goal_to_go: int = 0
    air_yards: float = 0.0       # pass plays: intended air yards
    kick_distance: float = 0.0   # FG/punt: distance of kick

@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": DEVICE,
        "play_types": list(PLAY_TYPE_MAP.keys()),
        "receiver_pos": RECEIVER_POS,
        "fg_results": FG_RESULT,
    }

@app.post("/predict")
def predict(req: PlayRequest):
    if req.play_type not in PLAY_TYPE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown play_type '{req.play_type}'. Must be one of {list(PLAY_TYPE_MAP.keys())}")
    try:
        x = encode_features(
            play_type=req.play_type,
            down=req.down,
            ydstogo=req.ydstogo,
            yardline_100=req.yardline_100,
            score_differential=req.score_differential,
            qtr=req.qtr,
            shotgun=req.shotgun,
            goal_to_go=req.goal_to_go,
            air_yards=req.air_yards,
            kick_distance=req.kick_distance,
        )
        with torch.no_grad():
            y_hat, to_l, td_l, rp_l, py_hat, pb_l, fg_l = model(x)

        yards = float(YARDS_SCALER.inverse_transform(
            y_hat.cpu().numpy().reshape(-1, 1)
        ).flatten()[0])

        punt_yards = float(PUNT_YARDS_SCALER.inverse_transform(
            py_hat.cpu().numpy().reshape(-1, 1)
        ).flatten()[0])

        to_prob = float(torch.softmax(to_l, -1)[0, 1].cpu())
        td_prob = float(torch.softmax(td_l, -1)[0, 1].cpu())
        rp_probs = torch.softmax(rp_l, -1)[0].cpu().numpy()
        pb_prob = float(torch.softmax(pb_l, -1)[0, 1].cpu())
        fg_probs = torch.softmax(fg_l, -1)[0].cpu().numpy()

        return {
            "yards": yards,
            "turnover_prob": to_prob,
            "td_prob": td_prob,
            "receiver_pos_probs": {
                RECEIVER_POS[str(i)]: float(rp_probs[i]) for i in range(3)
            },
            "punt_net_yards": max(0.0, punt_yards),
            "punt_blocked_prob": pb_prob,
            "fg_result_probs": {
                FG_RESULT[str(i)]: float(fg_probs[i]) for i in range(3)
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("outcome_inference:app", host="0.0.0.0", port=8004, reload=False)
