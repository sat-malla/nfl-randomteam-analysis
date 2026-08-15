import torch
import torch.nn as nn

EMB_DIM = 8
HIDDEN = 512
DROPOUT = 0.3

FEATURE_COLS = [
    "feat_down", "feat_dist", "feat_zone", "feat_score",
    "feat_qtr", "feat_time", "feat_half_end", "feat_trailing",
    "feat_shotgun", "feat_goal_to_go",
]

FEAT_CARDINALITY = {
    "feat_down": 4, "feat_dist": 4, "feat_zone": 6, "feat_score": 5,
    "feat_qtr": 5, "feat_time": 5, "feat_half_end": 2, "feat_trailing": 2,
    "feat_shotgun": 2, "feat_goal_to_go": 2,
}

INFERENCE_TEMPERATURE = 0.8
PASS_BOOST = 2.0

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

def time_bucket(secs: float, qtr: int) -> int:
    if secs <= 120 and qtr >= 4: return 0
    elif secs <= 480 and qtr == 4: return 1
    elif qtr == 3 or (qtr == 4 and secs > 480): return 2
    elif qtr == 2: return 3
    else: return 4

class PlayCallMLP(nn.Module):
    def __init__(self, feat_cardinality: dict, emb_dim: int, hidden: int, n_classes: int, dropout: float = DROPOUT):
        super().__init__()
        self.feat_names = list(feat_cardinality.keys())
        self.embeddings = nn.ModuleList([nn.Embedding(card, emb_dim) for card in feat_cardinality.values()])
        in_dim = len(feat_cardinality) * emb_dim
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), 
            nn.LayerNorm(hidden), 
            nn.SiLU(), 
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden), 
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
            nn.Linear(hidden // 2, n_classes),
        )

    def forward(self, x: torch.Tensor):
        embs = [self.embeddings[i](x[:, i]) for i in range(len(self.feat_names))]
        return self.net(torch.cat(embs, dim=-1))

    def predict_proba(self, x: torch.Tensor, temperature: float = 1.0):
        return torch.softmax(self.forward(x) / temperature, dim=-1)