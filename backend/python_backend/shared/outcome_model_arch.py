import torch
import torch.nn as nn

EMB_DIM = 8
HIDDEN = 512
DROPOUT = 0.3

PLAY_TYPE_MAP = {"run": 0, "pass": 1, "punt": 2, "field_goal": 3}

FEATURE_COLS = [
    "feat_play_type", "feat_down", "feat_dist", "feat_zone",
    "feat_score", "feat_qtr", "feat_shotgun", "feat_goal_to_go",
    "feat_air_yards", "feat_kick_dist", "feat_def_pass_tier",
    "feat_def_rush_tier", "feat_def_sack_tier", "feat_def_coverage_tier",
]

FEAT_CARDINALITY = {
    "feat_play_type": 4, "feat_down": 4, "feat_dist": 4, "feat_zone": 6,
    "feat_score": 5, "feat_qtr": 5, "feat_shotgun": 2, "feat_goal_to_go": 2,
    "feat_air_yards": 4, "feat_kick_dist": 4, "feat_def_pass_tier": 5,
    "feat_def_rush_tier": 5, "feat_def_sack_tier": 5, "feat_def_coverage_tier": 5,
}

def dist_bucket(x: float) -> int:
    if x <= 2: return 0
    elif x <= 6: return 1
    elif x <= 10: return 2
    else: return 3

def yard_zone(x: float) -> int:
    if x >= 80: return 0
    elif x >= 60: return 1
    elif x >= 40: return 2
    elif x >= 20: return 3
    elif x >= 5: return 4
    else: return 5

def score_bucket(x: float) -> int:
    if x <= -17: return 0
    elif x <= -7: return 1
    elif x <= 6: return 2
    elif x <= 16: return 3
    else: return 4

def air_yards_bucket(x: float) -> int:
    if x < 0: return 0
    elif x <= 5: return 1
    elif x <= 15: return 2
    else: return 3

def kick_dist_bucket(x: float) -> int:
    if x <= 30: return 0
    elif x <= 40: return 1
    elif x <= 50: return 2
    else: return 3

class OutcomeMLP(nn.Module):
    def __init__(self, feat_cardinality: dict, emb_dim: int, hidden: int, dropout: float = DROPOUT):
        super().__init__()
        self.feat_names = list(feat_cardinality.keys())
        self.embeddings = nn.ModuleList([nn.Embedding(card, emb_dim) for card in feat_cardinality.values()])
        in_dim = len(feat_cardinality) * emb_dim
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.LayerNorm(hidden),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.SiLU(),
            nn.Dropout(dropout),
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

    def predict(self, x, yards_scaler, punt_yards_scaler):
        self.eval()
        with torch.no_grad():
            y_hat, to_l, td_l, rp_l, py_hat, pb_l, fg_l = self.forward(x)
        yards = yards_scaler.inverse_transform(y_hat.cpu().numpy().reshape(-1, 1)).flatten()
        punt_yards = punt_yards_scaler.inverse_transform(py_hat.cpu().numpy().reshape(-1, 1)).flatten()
        to_prob = torch.softmax(to_l, -1)[:, 1].cpu().numpy()
        td_prob = torch.softmax(td_l, -1)[:, 1].cpu().numpy()
        rp_probs = torch.softmax(rp_l, -1).cpu().numpy()
        pb_prob = torch.softmax(pb_l, -1)[:, 1].cpu().numpy()
        fg_probs = torch.softmax(fg_l, -1).cpu().numpy()
        return yards, to_prob, td_prob, rp_probs, punt_yards, pb_prob, fg_probs

def encode_features(
    play_type: str, down: int, ydstogo: float, yardline_100: float,
    score_differential: float, qtr: int, shotgun: int = 0, goal_to_go: int = 0,
    air_yards: float = 0.0, kick_distance: float = 0.0,
    def_pass_tier: int = 2, def_rush_tier: int = 2, def_sack_tier: int = 2, def_coverage_tier: int = 2,
    device: str = "cpu",
) -> torch.Tensor:
    feats = [
        PLAY_TYPE_MAP.get(play_type, 0),
        max(0, min(3, down-1)),
        dist_bucket(ydstogo),
        yard_zone(yardline_100),
        score_bucket(score_differential),
        max(0, min(4, qtr-1)),
        min(1, max(0, shotgun)),
        min(1, max(0, goal_to_go)),
        air_yards_bucket(air_yards),
        kick_dist_bucket(kick_distance),
        min(4, max(0, def_pass_tier)),
        min(4, max(0, def_rush_tier)),
        min(4, max(0, def_sack_tier)),
        min(4, max(0, def_coverage_tier)),
    ]
    return torch.LongTensor([feats]).to(device)