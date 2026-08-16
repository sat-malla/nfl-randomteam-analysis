import json
import os
import pickle
import torch
import uvicorn
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.outcome_model_arch import OutcomeMLP, encode_features as _encode_features
from shared.model_loader import download_production_model_dir

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "outcome_model_weights")

def resolve_weights_dir():
    try:
        model_dir = download_production_model_dir("outcome-model")
        print(f"Loaded outcome-model from WandB production artifact: {model_dir}")
        return model_dir
    except Exception as e:
        print(f"WARNING: could not pull production model from WandB ({e}). Falling back to local weights.")
        return WEIGHTS_DIR

ACTIVE_WEIGHTS_DIR = resolve_weights_dir()

with open(f"{ACTIVE_WEIGHTS_DIR}/outcome_config.json") as f:
    CFG = json.load(f)
with open(f"{ACTIVE_WEIGHTS_DIR}/outcome_feature_meta.json") as f:
    META = json.load(f)
with open(f"{ACTIVE_WEIGHTS_DIR}/outcome_yards_scaler.pkl", "rb") as f:
    YARDS_SCALER = pickle.load(f)
with open(f"{ACTIVE_WEIGHTS_DIR}/outcome_punt_yards_scaler.pkl", "rb") as f:
    PUNT_YARDS_SCALER = pickle.load(f)

FEAT_CARDINALITY = META["feat_cardinality"]
PLAY_TYPE_MAP = META["play_type_map"]
RECEIVER_POS = META["receiver_pos_classes"]
FG_RESULT = META["fg_result_classes"]

EMB_DIM = CFG["emb_dim"]
HIDDEN = CFG["hidden"]

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

model = OutcomeMLP(FEAT_CARDINALITY, EMB_DIM, HIDDEN).to(DEVICE)
model.load_state_dict(torch.load(f"{ACTIVE_WEIGHTS_DIR}/outcome_model.pt", map_location=DEVICE))
model.eval()
print(f"Outcome model loaded on {DEVICE} from {ACTIVE_WEIGHTS_DIR}.")

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
    def_pass_tier: int = 2,
    def_rush_tier: int = 2,
    def_sack_tier: int = 2,
    def_coverage_tier: int = 2,
) -> torch.Tensor:
    return _encode_features(
        play_type=play_type, down=down, ydstogo=ydstogo,
        yardline_100=yardline_100, score_differential=score_differential, qtr=qtr,
        shotgun=shotgun, goal_to_go=goal_to_go, air_yards=air_yards, kick_distance=kick_distance,
        def_pass_tier=def_pass_tier, def_rush_tier=def_rush_tier,
        def_sack_tier=def_sack_tier, def_coverage_tier=def_coverage_tier,
        device=DEVICE,
    )

app = FastAPI(title="Outcome Predictor", version="1.0")
class PlayRequest(BaseModel):
    play_type: str
    down: int
    ydstogo: float
    yardline_100: float
    score_differential: float
    qtr: int
    shotgun: int = 0
    goal_to_go: int = 0
    air_yards: float = 0.0
    kick_distance: float = 0.0
    def_pass_tier: int = 2
    def_rush_tier: int = 2
    def_sack_tier: int = 2
    def_coverage_tier: int = 2

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
            def_pass_tier=req.def_pass_tier,
            def_rush_tier=req.def_rush_tier,
            def_sack_tier=req.def_sack_tier,
            def_coverage_tier=req.def_coverage_tier,
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