"""
tabsyn_inference.py  —  TabSyn Inference Microservice  (port 8002)

Loads trained VAE + diffusion weights on startup and exposes:
  POST /generate   { n_samples: int }  →  list of team-season stat dicts
  GET  /health     →  { status: "ok" }

team_analysis.py calls /generate to replace the old Gaussian copula sampler.
"""

import json
import os
import pickle
import uvicorn

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "tabsyn_weights")

with open(f"{WEIGHTS_DIR}/model_config.json") as f: CFG = json.load(f)
with open(f"{WEIGHTS_DIR}/column_meta.json") as f: COL_META = json.load(f)
with open(f"{WEIGHTS_DIR}/cat_encoders.json") as f: CAT_ENC = json.load(f)

LATENT_D = CFG["latent_dim"]
HIDDEN_D = CFG["hidden_dim"]
CAT_EMB_DIM = CFG["cat_emb_dim"]
N_CONT = CFG["n_continuous"]
N_CAT = CFG["n_categorical"]
CAT_DIMS = CFG["cat_dims"]
T_STEPS = CFG["T_steps"]
BETA_MIN = CFG["beta_min"]
BETA_MAX = CFG["beta_max"]
DDPM_STEPS = CFG["ddpm_sample_steps"]

CONT_COLS = COL_META["continuous_columns"]
CAT_COLS = COL_META["categorical_columns"]
ALL_COLS = COL_META["all_columns"]
DROP_COLS = COL_META["dropped_columns"]

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
        self.mu_head  = nn.Linear(hidden_dim, latent_dim)
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

IN_DIM = N_CONT + N_CAT * CAT_EMB_DIM

cat_embeddings = nn.ModuleList([nn.Embedding(d, CAT_EMB_DIM) for d in CAT_DIMS]).to(DEVICE)
decoder = Decoder(LATENT_D, N_CONT, CAT_DIMS, HIDDEN_D).to(DEVICE)
score_net = ScoreNet(LATENT_D, HIDDEN_D).to(DEVICE)

ckpt = torch.load(f"{WEIGHTS_DIR}/vae_best.pt", map_location=DEVICE)
decoder.load_state_dict(ckpt["decoder"])
cat_embeddings.load_state_dict(ckpt["cat_embeddings"])

score_net.load_state_dict(
    torch.load(f"{WEIGHTS_DIR}/score_net_best.pt", map_location=DEVICE)
)

norm_stats = torch.load(f"{WEIGHTS_DIR}/latent_norm.pt", map_location=DEVICE)
Z_MEAN = norm_stats["z_mean"].to(DEVICE)
Z_STD = norm_stats["z_std"].to(DEVICE)

with open(f"{WEIGHTS_DIR}/quantile_transformer.pkl", "rb") as f:
    QT = pickle.load(f)

decoder.eval()
score_net.eval()
cat_embeddings.eval()

betas = torch.linspace(BETA_MIN, BETA_MAX, T_STEPS).to(DEVICE)
alphas = 1.0 - betas
alpha_bar = torch.cumprod(alphas, dim=0)

print(f"TabSyn inference service loaded on {DEVICE}.")

@torch.no_grad()
def ddpm_sample(n_samples: int) -> torch.Tensor:
    z = torch.randn(n_samples, LATENT_D, device=DEVICE)
    step_indices = torch.linspace(T_STEPS - 1, 0, DDPM_STEPS, dtype=torch.long)

    for t_idx in step_indices:
        t_val = t_idx.float() / T_STEPS
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

    return z * Z_STD + Z_MEAN


@torch.no_grad()
def latents_to_rows(z_samples: torch.Tensor) -> list[dict]:
    recon_cont, recon_cat = decoder(z_samples)

    cont_np = recon_cont.cpu().numpy()
    cont_np = QT.inverse_transform(cont_np)

    # Rescale to match training distribution (VAE compresses variance on small datasets)
    gen_mean = cont_np.mean(axis=0)
    gen_std = cont_np.std(axis=0).clip(min=1e-6)
    qt_range = (QT.references_[-1] - QT.references_[0]) if hasattr(QT, "references_") else None
    if qt_range is not None:
        target_std = np.array([
            np.std(QT.inverse_transform(
                np.expand_dims(np.linspace(-3, 3, 100), 1) *
                np.ones((100, N_CONT))
            )[:, i]) for i in range(N_CONT)
        ]).clip(min=1e-6)
        target_mean = QT.inverse_transform(np.zeros((1, N_CONT)))[0]
    else:
        target_std = gen_std
        target_mean = gen_mean

    cont_np = (cont_np - gen_mean) / gen_std * target_std + target_mean
    cont_np = np.maximum(cont_np, 0)

    rows = []
    for i in range(len(cont_np)):
        row: dict = {}
        for j, col in enumerate(CONT_COLS):
            row[col] = float(cont_np[i, j])

        for k, col in enumerate(CAT_COLS):
            code = int(recon_cat[k][i].argmax().item())
            rev_enc = CAT_ENC.get(col, {})
            row[col] = rev_enc.get(str(code), code)

        for col in DROP_COLS:
            if col != "team":
                row[col] = 0.0

        rows.append(row)

    return rows


app = FastAPI(title="TabSyn Inference", version="1.0")

class GenerateRequest(BaseModel):
    n_samples: int = 1

@app.get("/health")
def health():
    return {"status": "ok", "device": DEVICE}

@app.post("/generate")
def generate(req: GenerateRequest):
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
