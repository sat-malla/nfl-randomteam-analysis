import torch
import torch.nn as nn

LATENT_D = 256
HIDDEN_D = 512
CAT_EMB_DIM = 8
T_STEPS = 1000
BETA_MIN = 1e-4
BETA_MAX = 0.02
DDPM_SAMPLE_STEPS = 200
CATEGORICAL_COLS = ["season", "ls_roster_churn"]
DROP_COLS = ["team", "rs1_kr_att", "rs1_kr_yds", "rs1_pr_att", "rs1_pr_yds"]

class Encoder(nn.Module):
    def __init__(self, in_dim: int, latent_dim: int, hidden_dim: int):
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

    def forward(self, x: torch.Tensor):
        h = self.net(x)
        return self.mu_head(h), self.log_head(h)

class Decoder(nn.Module):
    def __init__(self, latent_dim: int, out_cont: int, cat_dims: list, hidden_dim: int):
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

    def forward(self, z: torch.Tensor):
        h = self.net(z)
        x_cont = self.cont_head(h)
        x_cat = [head(h) for head in self.cat_heads]
        return x_cont, x_cat

class ScoreNet(nn.Module):
    def __init__(self, latent_dim: int, hidden_dim: int):
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

    def forward(self, z_noisy: torch.Tensor, t: torch.Tensor):
        t_emb = self.time_emb(t.unsqueeze(-1).float())
        h = torch.cat([z_noisy, t_emb], dim=-1)
        return self.net(h)

def build_noise_schedule(device: str):
    betas = torch.linspace(BETA_MIN, BETA_MAX, T_STEPS).to(device)
    alphas = 1.0 - betas
    alpha_bar = torch.cumprod(alphas, dim=0)
    return betas, alphas, alpha_bar