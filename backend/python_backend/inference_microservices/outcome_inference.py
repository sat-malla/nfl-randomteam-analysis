import json
import os
import pickle
import torch
import uvicorn
import sys
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.outcome_model_arch import OutcomeMLP, encode_features as _encode_features
from shared.model_loader import download_production_model_dir

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "outcome_model_weights")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model_state = {
    "ready": False,
    "error": None,
    "model": None,
    "yards_scaler": None,
    "punt_yards_scaler": None,
    "feat_cardinality": None,
    "play_type_map": None,
    "receiver_pos": None,
    "fg_result": None,
}

def _load_model_blocking():
    try:
        try:
            model_dir = download_production_model_dir("outcome-model")
            print(f"Loaded outcome-model from WandB production artifact: {model_dir}")
        except Exception as e:
            print(f"WARNING: could not pull production model from WandB ({e}). Falling back to local weights.")
            model_dir = WEIGHTS_DIR

        with open(f"{model_dir}/outcome_config.json") as f:
            cfg = json.load(f)
        with open(f"{model_dir}/outcome_feature_meta.json") as f:
            meta = json.load(f)
        with open(f"{model_dir}/outcome_yards_scaler.pkl", "rb") as f:
            yards_scaler = pickle.load(f)
        with open(f"{model_dir}/outcome_punt_yards_scaler.pkl", "rb") as f:
            punt_yards_scaler = pickle.load(f)

        feat_cardinality = meta["feat_cardinality"]
        model = OutcomeMLP(feat_cardinality, cfg["emb_dim"], cfg["hidden"]).to(DEVICE)
        model.load_state_dict(torch.load(f"{model_dir}/outcome_model.pt", map_location=DEVICE))
        model.eval()
        print(f"Outcome model loaded on {DEVICE} from {model_dir}.")

        _model_state.update({
            "model": model,
            "yards_scaler": yards_scaler,
            "punt_yards_scaler": punt_yards_scaler,
            "feat_cardinality": feat_cardinality,
            "play_type_map": meta["play_type_map"],
            "receiver_pos": meta["receiver_pos_classes"],
            "fg_result": meta["fg_result_classes"],
            "ready": True,
        })
    except Exception as e:
        _model_state["error"] = str(e)
        print(f"ERROR loading outcome model: {e}")

def encode_features(**kwargs) -> torch.Tensor:
    return _encode_features(**kwargs, device=DEVICE)

app = FastAPI(title="Outcome Predictor", version="1.0")

@app.on_event("startup")
async def _startup():
    threading.Thread(target=_load_model_blocking, daemon=True).start()
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
    if _model_state["error"]:
        return {"status": "error", "detail": _model_state["error"]}
    if not _model_state["ready"]:
        return {"status": "loading"}
    return {
        "status": "ok",
        "device": DEVICE,
        "play_types": list(_model_state["play_type_map"].keys()),
        "receiver_pos": _model_state["receiver_pos"],
        "fg_results": _model_state["fg_result"],
    }

@app.post("/predict")
def predict(req: PlayRequest):
    if not _model_state["ready"]:
        raise HTTPException(status_code=503, detail="Model still loading, try again shortly.")

    play_type_map = _model_state["play_type_map"]
    if req.play_type not in play_type_map:
        raise HTTPException(status_code=400, detail=f"Unknown play_type '{req.play_type}'. Must be one of {list(play_type_map.keys())}")

    try:
        x = encode_features(
            play_type=req.play_type, down=req.down, ydstogo=req.ydstogo,
            yardline_100=req.yardline_100, score_differential=req.score_differential, qtr=req.qtr,
            shotgun=req.shotgun, goal_to_go=req.goal_to_go, air_yards=req.air_yards,
            kick_distance=req.kick_distance, def_pass_tier=req.def_pass_tier,
            def_rush_tier=req.def_rush_tier, def_sack_tier=req.def_sack_tier,
            def_coverage_tier=req.def_coverage_tier,
        )
        model = _model_state["model"]
        with torch.no_grad():
            y_hat, to_l, td_l, rp_l, py_hat, pb_l, fg_l = model(x)

        yards = float(_model_state["yards_scaler"].inverse_transform(
            y_hat.cpu().numpy().reshape(-1, 1)
        ).flatten()[0])
        punt_yards = float(_model_state["punt_yards_scaler"].inverse_transform(
            py_hat.cpu().numpy().reshape(-1, 1)
        ).flatten()[0])

        to_prob = float(torch.softmax(to_l, -1)[0, 1].cpu())
        td_prob = float(torch.softmax(td_l, -1)[0, 1].cpu())
        rp_probs = torch.softmax(rp_l, -1)[0].cpu().numpy()
        pb_prob = float(torch.softmax(pb_l, -1)[0, 1].cpu())
        fg_probs = torch.softmax(fg_l, -1)[0].cpu().numpy()

        receiver_pos = _model_state["receiver_pos"]
        fg_result = _model_state["fg_result"]

        return {
            "yards": yards,
            "turnover_prob": to_prob,
            "td_prob": td_prob,
            "receiver_pos_probs": {receiver_pos[str(i)]: float(rp_probs[i]) for i in range(3)},
            "punt_net_yards": max(0.0, punt_yards),
            "punt_blocked_prob": pb_prob,
            "fg_result_probs": {fg_result[str(i)]: float(fg_probs[i]) for i in range(3)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("outcome_inference:app", host="0.0.0.0", port=8004, reload=False)