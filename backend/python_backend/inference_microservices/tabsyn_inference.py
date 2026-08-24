"""
tabsyn_inference.py  —  TabSyn Inference Microservice

Loads trained VAE + diffusion weights on startup and exposes:
  POST /generate { n_samples: int } -> list of team-season stat dicts
  GET  /health -> { status: "ok" }
"""

import json
import os
import pickle
import uvicorn
import sys
import threading
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.model_loader import download_production_model_dir

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "tabsyn_weights")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
class Encoder(nn.Module):
    def __init__(self, in_dim, latent_dim, hidden_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
        )
        self.mu_head = nn.Linear(hidden_dim, latent_dim)
        self.log_head = nn.Linear(hidden_dim, latent_dim)

    def forward(self, x):
        h = self.net(x)
        return self.mu_head(h), self.log_head(h)
class Decoder(nn.Module):
    def __init__(self, latent_dim, out_cont, cat_dims, hidden_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
        )
        self.cont_head = nn.Linear(hidden_dim, out_cont)
        self.cat_heads = nn.ModuleList([nn.Linear(hidden_dim, d) for d in cat_dims])

    def forward(self, z):
        h = self.net(z)
        x_cont = self.cont_head(h)
        x_cat = [head(h) for head in self.cat_heads]
        return x_cont, x_cat
class ScoreNet(nn.Module):
    def __init__(self, latent_dim, hidden_dim):
        super().__init__()
        self.time_emb = nn.Sequential(
            nn.Linear(1, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.net = nn.Sequential(
            nn.Linear(latent_dim + hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, z_noisy, t):
        t_emb = self.time_emb(t.unsqueeze(-1).float())
        h = torch.cat([z_noisy, t_emb], dim=-1)
        return self.net(h)

_model_state = {
    "ready": False,
    "error": None,
    "decoder": None,
    "score_net": None,
    "cat_embeddings": None,
    "z_mean": None,
    "z_std": None,
    "qt": None,
    "betas": None,
    "alphas": None,
    "alpha_bar": None,
    "cont_cols": None,
    "cat_cols": None,
    "cat_enc": None,
    "drop_cols": None,
    "n_cont": None,
    "t_steps": None,
    "ddpm_steps": None,
    "latent_d": None,
}

def _load_model_blocking():
    try:
        try:
            model_dir = download_production_model_dir("tabsyn-model")
            print(f"Loaded tabsyn-model from WandB production artifact: {model_dir}")
        except Exception as e:
            print(f"WARNING: could not pull production model from WandB ({e}). Falling back to local weights.")
            model_dir = WEIGHTS_DIR

        with open(f"{model_dir}/model_config.json") as f:
            cfg = json.load(f)
        with open(f"{model_dir}/column_meta.json") as f:
            col_meta = json.load(f)
        with open(f"{model_dir}/cat_encoders.json") as f:
            cat_enc = json.load(f)

        latent_d = cfg["latent_dim"]
        hidden_d = cfg["hidden_dim"]
        cat_emb_dim = cfg["cat_emb_dim"]
        n_cont = cfg["n_continuous"]
        cat_dims = cfg["cat_dims"]
        t_steps = cfg["T_steps"]
        beta_min = cfg["beta_min"]
        beta_max = cfg["beta_max"]
        ddpm_steps = cfg["ddpm_sample_steps"]

        cont_cols = col_meta["continuous_columns"]
        cat_cols = col_meta["categorical_columns"]
        drop_cols = col_meta["dropped_columns"]

        cat_embeddings = nn.ModuleList([nn.Embedding(d, cat_emb_dim) for d in cat_dims]).to(DEVICE)
        decoder = Decoder(latent_d, n_cont, cat_dims, hidden_d).to(DEVICE)
        score_net = ScoreNet(latent_d, hidden_d).to(DEVICE)

        ckpt = torch.load(f"{model_dir}/vae_best.pt", map_location=DEVICE)
        decoder.load_state_dict(ckpt["decoder"])
        cat_embeddings.load_state_dict(ckpt["cat_embeddings"])

        score_net.load_state_dict(
            torch.load(f"{model_dir}/score_net_best.pt", map_location=DEVICE)
        )

        norm_stats = torch.load(f"{model_dir}/latent_norm.pt", map_location=DEVICE)
        z_mean = norm_stats["z_mean"].to(DEVICE)
        z_std = norm_stats["z_std"].to(DEVICE)

        with open(f"{model_dir}/quantile_transformer.pkl", "rb") as f:
            qt = pickle.load(f)

        decoder.eval()
        score_net.eval()
        cat_embeddings.eval()

        betas = torch.linspace(beta_min, beta_max, t_steps).to(DEVICE)
        alphas = 1.0 - betas
        alpha_bar = torch.cumprod(alphas, dim=0)

        print(f"TabSyn inference service loaded on {DEVICE}.")

        _model_state.update({
            "decoder": decoder,
            "score_net": score_net,
            "cat_embeddings": cat_embeddings,
            "z_mean": z_mean,
            "z_std": z_std,
            "qt": qt,
            "betas": betas,
            "alphas": alphas,
            "alpha_bar": alpha_bar,
            "cont_cols": cont_cols,
            "cat_cols": cat_cols,
            "cat_enc": cat_enc,
            "drop_cols": drop_cols,
            "n_cont": n_cont,
            "t_steps": t_steps,
            "ddpm_steps": ddpm_steps,
            "latent_d": latent_d,
            "ready": True,
        })
    except Exception as e:
        _model_state["error"] = str(e)
        print(f"ERROR loading tabsyn model: {e}")

@torch.no_grad()
def ddpm_sample(n_samples: int) -> torch.Tensor:
    latent_d = _model_state["latent_d"]
    t_steps = _model_state["t_steps"]
    ddpm_steps = _model_state["ddpm_steps"]
    alphas = _model_state["alphas"]
    alpha_bar = _model_state["alpha_bar"]
    betas = _model_state["betas"]
    score_net = _model_state["score_net"]
    z_mean = _model_state["z_mean"]
    z_std = _model_state["z_std"]

    z = torch.randn(n_samples, latent_d, device=DEVICE)
    step_indices = torch.linspace(t_steps - 1, 0, ddpm_steps, dtype=torch.long)

    for t_idx in step_indices:
        t_val = t_idx.float() / t_steps
        t_batch = t_val.expand(n_samples).to(DEVICE)

        pred_noise = score_net(z, t_batch)
        alpha_t = alphas[t_idx]
        alpha_bar_t = alpha_bar[t_idx]
        beta_t = betas[t_idx]

        coef1 = 1.0 / torch.sqrt(alpha_t)
        coef2 = beta_t / torch.sqrt(1 - alpha_bar_t)
        mean = coef1 * (z - coef2 * pred_noise)

        if t_idx > 0:
            z = mean + torch.sqrt(beta_t) * torch.randn_like(z)
        else:
            z = mean

    return z * z_std + z_mean

@torch.no_grad()
def latents_to_rows(z_samples: torch.Tensor) -> list[dict]:
    decoder = _model_state["decoder"]
    qt = _model_state["qt"]
    cont_cols = _model_state["cont_cols"]
    cat_cols = _model_state["cat_cols"]
    cat_enc = _model_state["cat_enc"]
    drop_cols = _model_state["drop_cols"]
    n_cont = _model_state["n_cont"]

    recon_cont, recon_cat = decoder(z_samples)

    cont_np = recon_cont.cpu().numpy()
    cont_np = qt.inverse_transform(cont_np)

    gen_mean = cont_np.mean(axis=0)
    gen_std = cont_np.std(axis=0).clip(min=1e-6)
    qt_range = (qt.references_[-1] - qt.references_[0]) if hasattr(qt, "references_") else None
    if qt_range is not None:
        target_std = np.array([
            np.std(qt.inverse_transform(
                np.expand_dims(np.linspace(-3, 3, 100), 1) *
                np.ones((100, n_cont))
            )[:, i]) for i in range(n_cont)
        ]).clip(min=1e-6)
        target_mean = qt.inverse_transform(np.zeros((1, n_cont)))[0]
    else:
        target_std = gen_std
        target_mean = gen_mean

    cont_np = (cont_np - gen_mean) / gen_std * target_std + target_mean
    cont_np = np.maximum(cont_np, 0)

    rows = []
    for i in range(len(cont_np)):
        row: dict = {}
        for j, col in enumerate(cont_cols):
            row[col] = float(cont_np[i, j])

        for k, col in enumerate(cat_cols):
            code = int(recon_cat[k][i].argmax().item())
            rev_enc = cat_enc.get(col, {})
            row[col] = rev_enc.get(str(code), code)

        for col in drop_cols:
            if col != "team":
                row[col] = 0.0

        rows.append(row)

    return rows

app = FastAPI(title="TabSyn Inference", version="1.0")

@app.on_event("startup")
async def _startup():
    threading.Thread(target=_load_model_blocking, daemon=True).start()

class GenerateRequest(BaseModel):
    n_samples: int = 1

@app.get("/health")
def health():
    if _model_state["error"]:
        return {"status": "error", "detail": _model_state["error"]}
    if not _model_state["ready"]:
        return {"status": "loading"}
    return {"status": "ok", "device": DEVICE}

@app.post("/generate")
def generate(req: GenerateRequest):
    if not _model_state["ready"]:
        raise HTTPException(status_code=503, detail="Model still loading, try again shortly.")
    if req.n_samples < 1 or req.n_samples > 500:
        raise HTTPException(status_code=400, detail="n_samples must be between 1 and 500")
    try:
        z = ddpm_sample(req.n_samples)
        rows = latents_to_rows(z)
        return {"samples": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("tabsyn_inference:app", host="0.0.0.0", port=8002, reload=False)