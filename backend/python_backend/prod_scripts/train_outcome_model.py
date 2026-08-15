import os
import wandb
import pandas as pd
import torch
import json
import pickle
import warnings
import numpy as np
import sys
import torch
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.outcome_model_arch import (
    OutcomeMLP, FEATURE_COLS, FEAT_CARDINALITY, PLAY_TYPE_MAP,
    EMB_DIM, HIDDEN, DROPOUT,
    dist_bucket, yard_zone, score_bucket, air_yards_bucket, kick_dist_bucket
)

warnings.filterwarnings("ignore")

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

EPOCHS = 60
BATCH_SIZE = 4096
LR = 3e-3
W_YARDS, W_TURNOVER, W_TD = 1.0, 2.0, 4.0
W_REC_POS, W_REC_POS_ENTROPY = 2.0, 0.3
W_PUNT_YARDS, W_PUNT_BLOCK, W_FG_RESULT = 1.0, 3.0, 2.0
PROMOTION_TOLERANCE = 1.02
HOLDOUT_SEASON = 2025

def load_pbp_data(run) -> pd.DataFrame:
    artifact = run.use_artifact("pbp-raw:latest")
    data_dir = artifact.download()
    return pd.read_csv(os.path.join(data_dir, "pbp_raw.csv"), low_memory=False)

def build_defensive_tiers(pbp_all: pd.DataFrame) -> pd.DataFrame:
    scrimmage = pbp_all[
        pbp_all["play_type"].isin({"run", "pass"}) &
        pbp_all["defteam"].notna() &
        pbp_all["season"].notna()
    ].copy()

    scrimmage["yards_gained"] = scrimmage["yards_gained"].fillna(0)
    scrimmage["sack"] = scrimmage.get("sack", pd.Series(0, index=scrimmage.index)).fillna(0)
    scrimmage["interception"] = scrimmage.get("interception", pd.Series(0, index=scrimmage.index)).fillna(0)
    scrimmage["pass_attempt"] = (scrimmage["play_type"] == "pass").astype(int)
    scrimmage["run_attempt"] = (scrimmage["play_type"] == "run").astype(int)
    scrimmage["pass_defended"] = scrimmage["pass_defended"].fillna(0) if "pass_defended" in scrimmage.columns else 0

    def_agg = scrimmage.groupby(["defteam", "season"]).agg(
        pass_plays=("pass_attempt", "sum"),
        run_plays=("run_attempt", "sum"),
        pass_yards_allowed=("yards_gained", lambda x: x[scrimmage.loc[x.index, "play_type"] == "pass"].sum()),
        rush_yards_allowed=("yards_gained", lambda x: x[scrimmage.loc[x.index, "play_type"] == "run"].sum()),
        sacks=("sack", "sum"),
        ints=("interception", "sum"),
        pds=("pass_defended", "sum"),
    ).reset_index()

    def_agg["pass_ypp"] = def_agg["pass_yards_allowed"] / def_agg["pass_plays"].clip(lower=1)
    def_agg["rush_ypp"] = def_agg["rush_yards_allowed"] / def_agg["run_plays"].clip(lower=1)
    def_agg["sack_rate"] = def_agg["sacks"] / def_agg["pass_plays"].clip(lower=1)
    def_agg["coverage_rate"] = (def_agg["ints"] + def_agg["pds"]) / def_agg["pass_plays"].clip(lower=1)

    def quintile_tier(series, ascending=True):
        return pd.qcut(series.rank(method="first", ascending=ascending), q=5, labels=[0, 1, 2, 3, 4]).astype(int)

    tiers_list = []
    for season, grp in def_agg.groupby("season"):
        g = grp.copy()
        g["def_pass_tier"] = quintile_tier(g["pass_ypp"], ascending=True)
        g["def_rush_tier"] = quintile_tier(g["rush_ypp"], ascending=True)
        g["def_sack_tier"] = quintile_tier(g["sack_rate"], ascending=False)
        g["def_coverage_tier"] = quintile_tier(g["coverage_rate"], ascending=False)
        tiers_list.append(g)

    return pd.concat(tiers_list, ignore_index=True)

def build_targets(df: pd.DataFrame) -> pd.DataFrame:
    df["target_yards"] = df["yards_gained"].clip(-10, 50).astype(float)
    df["target_turnover"] = (
        (df.get("interception", pd.Series(0, index=df.index)).fillna(0) == 1) |
        (df.get("fumble_lost", pd.Series(0, index=df.index)).fillna(0) == 1)
    ).astype(int)
    df["target_td"] = df.get("touchdown", pd.Series(0, index=df.index)).fillna(0).astype(int)

    pos_col = next((c for c in ["receiver_player_position", "receiver_position"] if c in df.columns), None)

    def infer_receiver_pos(row):
        if row["play_type"] != "pass": return 0
        if pos_col and pd.notna(row.get(pos_col)):
            p = str(row[pos_col]).upper()
            if p == "WR": return 0
            if p == "TE": return 1
            if p in ("RB", "HB", "FB"): return 2
        air = row.get("air_yards", 0) or 0
        if air < 0: return 2
        elif air < 6: return 1
        else: return 0

    df["target_receiver_pos"] = df.apply(infer_receiver_pos, axis=1)
    df["target_punt_yards"] = df["punt_net_yards"].astype(float)
    df["target_punt_blocked"] = df.get("punt_blocked", pd.Series(0, index=df.index)).fillna(0).astype(int)

    def fg_result_label(row):
        if row["play_type"] != "field_goal": return 0
        res = str(row.get("field_goal_result", "")).lower()
        if "made" in res or res == "good": return 0
        if "blocked" in res: return 2
        return 1

    df["target_fg_result"] = df.apply(fg_result_label, axis=1)
    return df

def prepare_dataset(pbp_raw: pd.DataFrame):
    KEEP_TYPES = {"run", "pass", "punt", "field_goal"}
    df = pbp_raw[
        pbp_raw["play_type"].isin(KEEP_TYPES) &
        pbp_raw["yardline_100"].notna() &
        pbp_raw["score_differential"].notna() &
        pbp_raw["qtr"].notna()
    ].copy()
    df["down"] = df["down"].fillna(4)
    df["ydstogo"] = df["ydstogo"].fillna(10)
    df["yards_gained"] = df["yards_gained"].fillna(0)
    df["shotgun"] = df["shotgun"].fillna(0).astype(int)
    df["goal_to_go"] = df["goal_to_go"].fillna(0).astype(int)
    df["air_yards"] = df["air_yards"].fillna(0)
    df["kick_distance"] = df["kick_distance"].fillna(0)
    df["return_yards"] = df["return_yards"].fillna(0)
    df["punt_net_yards"] = np.where(
        df["play_type"] == "punt",
        (df["kick_distance"] - df["return_yards"]).clip(0, 80),
        0.0,
    )

    def_tiers = build_defensive_tiers(pbp_raw)
    df = build_targets(df)

    df["feat_play_type"] = df["play_type"].map(PLAY_TYPE_MAP)
    df["feat_down"] = df["down"].astype(int).clip(1, 4) - 1
    df["feat_dist"] = df["ydstogo"].apply(dist_bucket)
    df["feat_zone"] = df["yardline_100"].apply(yard_zone)
    df["feat_score"] = df["score_differential"].apply(score_bucket)
    df["feat_qtr"] = (df["qtr"].clip(1, 5) - 1).astype(int)
    df["feat_shotgun"] = df["shotgun"]
    df["feat_goal_to_go"] = df["goal_to_go"]
    df["feat_air_yards"] = df["air_yards"].apply(air_yards_bucket)
    df["feat_kick_dist"] = df["kick_distance"].apply(kick_dist_bucket)

    tier_cols = ["def_pass_tier", "def_rush_tier", "def_sack_tier", "def_coverage_tier"]
    df["defteam_str"] = df["defteam"].fillna("UNK")
    df["season_int"] = df["season"].fillna(2020).astype(int)
    df = df.merge(
        def_tiers[["defteam", "season"] + tier_cols],
        left_on=["defteam_str", "season_int"], right_on=["defteam", "season"],
        how="left", suffixes=("", "_tier"),
    )
    for col in tier_cols:
        df[col] = df[col].fillna(2).astype(int)
    df["feat_def_pass_tier"] = df["def_pass_tier"]
    df["feat_def_rush_tier"] = df["def_rush_tier"]
    df["feat_def_sack_tier"] = df["def_sack_tier"]
    df["feat_def_coverage_tier"] = df["def_coverage_tier"]

    return df, def_tiers

def masked_loss(loss_fn, logits, targets, mask):
    if mask.sum() == 0:
        return torch.tensor(0.0, device=DEVICE)
    return loss_fn(logits[mask], targets[mask])

def build_tensors(df: pd.DataFrame, yards_scaler=None, punt_yards_scaler=None, fit_scalers=False):
    X = df[FEATURE_COLS].values.astype(np.int64)
    y_yards = df["target_yards"].values.astype(np.float32)
    y_punt_yards = df["target_punt_yards"].values.astype(np.float32)
    y_turnover = df["target_turnover"].values.astype(np.int64)
    y_td = df["target_td"].values.astype(np.int64)
    y_rec_pos = df["target_receiver_pos"].values.astype(np.int64)
    y_punt_block = df["target_punt_blocked"].values.astype(np.int64)
    y_fg_result = df["target_fg_result"].values.astype(np.int64)

    if fit_scalers:
        yards_scaler = StandardScaler()
        y_yards_sc = yards_scaler.fit_transform(y_yards.reshape(-1, 1)).flatten().astype(np.float32)
        punt_mask_all = df["play_type"].values == "punt"
        punt_yards_scaler = StandardScaler()
        punt_yards_scaler.fit(y_punt_yards[punt_mask_all].reshape(-1, 1))
        y_punt_yards_sc = punt_yards_scaler.transform(y_punt_yards.reshape(-1, 1)).flatten().astype(np.float32)
    else:
        y_yards_sc = yards_scaler.transform(y_yards.reshape(-1, 1)).flatten().astype(np.float32)
        y_punt_yards_sc = punt_yards_scaler.transform(y_punt_yards.reshape(-1, 1)).flatten().astype(np.float32)

    tensors = dict(
        X=torch.LongTensor(X).to(DEVICE),
        yw=torch.FloatTensor(y_yards_sc).to(DEVICE),
        yp=torch.FloatTensor(y_punt_yards_sc).to(DEVICE),
        yt=torch.LongTensor(y_turnover).to(DEVICE),
        ytd=torch.LongTensor(y_td).to(DEVICE),
        yrp=torch.LongTensor(y_rec_pos).to(DEVICE),
        ypb=torch.LongTensor(y_punt_block).to(DEVICE),
        yfg=torch.LongTensor(y_fg_result).to(DEVICE),
    )
    return tensors, yards_scaler, punt_yards_scaler

def compute_val_loss(model, t: dict) -> float:
    model.eval()
    with torch.no_grad():
        y_hat, to_l, td_l, rp_l, py_hat, pb_l, fg_l = model(t["X"])
        pt = t["X"][:, 0]
        sc_m = (pt == 0) | (pt == 1)
        pa_m = pt == 1
        pu_m = pt == 2
        fg_m = pt == 3
        loss = (
            W_YARDS * masked_loss(F.mse_loss, y_hat, t["yw"], sc_m).item() +
            W_TURNOVER * masked_loss(F.cross_entropy, to_l, t["yt"], sc_m).item() +
            W_TD * masked_loss(F.cross_entropy, td_l, t["ytd"], sc_m).item() +
            W_REC_POS * masked_loss(F.cross_entropy, rp_l, t["yrp"], pa_m).item() +
            W_PUNT_YARDS * masked_loss(F.mse_loss, py_hat, t["yp"], pu_m).item() +
            W_PUNT_BLOCK * masked_loss(F.cross_entropy, pb_l, t["ypb"], pu_m).item() +
            W_FG_RESULT * masked_loss(F.cross_entropy, fg_l, t["yfg"], fg_m).item()
        )
    return loss

# Training and evaluation

def train_model(train_tensors: dict) -> OutcomeMLP:
    model = OutcomeMLP(FEAT_CARDINALITY, EMB_DIM, HIDDEN, DROPOUT).to(DEVICE)

    rp_class_counts = np.bincount(train_tensors["yrp"].cpu().numpy(), minlength=3).astype(float)
    rp_class_counts = np.maximum(rp_class_counts, 1)
    rp_class_weights = (1.0 / rp_class_counts)
    rp_class_weights = rp_class_weights / rp_class_weights.sum() * 3
    rp_weights_t = torch.FloatTensor(rp_class_weights).to(DEVICE)

    train_ds = TensorDataset(
        train_tensors["X"], train_tensors["yw"], train_tensors["yp"], train_tensors["yt"],
        train_tensors["ytd"], train_tensors["yrp"], train_tensors["ypb"], train_tensors["yfg"],
    )
    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=LR, steps_per_epoch=len(train_dl), epochs=EPOCHS
    )

    for epoch in range(1, EPOCHS + 1):
        model.train()
        for xb, ywb, ypb_y, ytb, ytdb, yrpb, ypbb, yfgb in train_dl:
            optimizer.zero_grad()
            y_hat, to_l, td_l, rp_l, py_hat, pb_l, fg_l = model(xb)
            pt = xb[:, 0]
            sc_m = (pt == 0) | (pt == 1)
            pa_m = pt == 1
            pu_m = pt == 2
            fg_m = pt == 3
            loss = (
                W_YARDS * masked_loss(F.mse_loss, y_hat, ywb, sc_m) +
                W_TURNOVER * masked_loss(F.cross_entropy, to_l, ytb, sc_m) +
                W_TD * masked_loss(F.cross_entropy, td_l, ytdb, sc_m) +
                W_REC_POS * masked_loss(lambda l, t: F.cross_entropy(l, t, weight=rp_weights_t), rp_l, yrpb, pa_m) +
                    (W_REC_POS * W_REC_POS_ENTROPY * (-(torch.softmax(rp_l[pa_m], -1) * torch.log_softmax(rp_l[pa_m], -1)).sum(-1).mean())
                    if pa_m.sum() > 0 else torch.tensor(0.0, device=DEVICE)) +
                W_PUNT_YARDS * masked_loss(F.mse_loss, py_hat, ypb_y, pu_m) +
                W_PUNT_BLOCK * masked_loss(F.cross_entropy, pb_l, ypbb, pu_m) +
                W_FG_RESULT * masked_loss(F.cross_entropy, fg_l, yfgb, fg_m)
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{EPOCHS}")

    return model

def evaluate_on_holdout(model: OutcomeMLP, holdout_tensors: dict) -> float:
    return compute_val_loss(model, holdout_tensors)

# Main

def load_current_production_model():
    api = wandb.Api()
    try:
        artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/outcome-model:production")
    except wandb.errors.CommError:
        return None
    model_dir = artifact.download()
    model = OutcomeMLP(FEAT_CARDINALITY, EMB_DIM, HIDDEN, DROPOUT).to(DEVICE)
    model.load_state_dict(torch.load(os.path.join(model_dir, "outcome_model.pt"), map_location=DEVICE))
    return model

def main():
    run = wandb.init(project=WANDB_PROJECT, entity=WANDB_ENTITY, job_type="train-outcome-model")
    pbp_raw = load_pbp_data(run)
    df, def_tiers = prepare_dataset(pbp_raw)
    holdout_df = df[df["season_int"] == HOLDOUT_SEASON]
    train_df = df[df["season_int"] != HOLDOUT_SEASON]
    print(f"Train: {len(train_df):,}  Holdout ({HOLDOUT_SEASON}): {len(holdout_df):,}")

    train_tensors, yards_scaler, punt_yards_scaler = build_tensors(train_df, fit_scalers=True)
    holdout_tensors, _, _ = build_tensors(holdout_df, yards_scaler, punt_yards_scaler, fit_scalers=False)
    candidate_model = train_model(train_tensors)
    candidate_score = evaluate_on_holdout(candidate_model, holdout_tensors)
    current_model = load_current_production_model()
    current_score = evaluate_on_holdout(current_model, holdout_tensors) if current_model is not None else None
    promoted = current_score is None or candidate_score <= current_score * PROMOTION_TOLERANCE

    os.makedirs("prod_scripts/train_tmp", exist_ok=True)
    model_path = "prod_scripts/train_tmp/outcome_model.pt"
    torch.save(candidate_model.state_dict(), model_path)

    yards_scaler_path = "prod_scripts/train_tmp/outcome_yards_scaler.pkl"
    punt_scaler_path = "prod_scripts/train_tmp/outcome_punt_yards_scaler.pkl"

    with open(yards_scaler_path, "wb") as f:
        pickle.dump(yards_scaler, f)
    with open(punt_scaler_path, "wb") as f:
        pickle.dump(punt_yards_scaler, f)

    def_tiers_json = {
         f"{r['defteam']}|{r['season']}": {
            "def_pass_tier": int(r["def_pass_tier"]),
            "def_rush_tier": int(r["def_rush_tier"]),
            "def_sack_tier": int(r["def_sack_tier"]),
            "def_coverage_tier": int(r["def_coverage_tier"]),
        }
        for r in def_tiers[["defteam", "season", "def_pass_tier", "def_rush_tier", "def_sack_tier", "def_coverage_tier"]].to_dict("records")
    }
    def_tiers_path = "prod_scripts/train_tmp/outcome_def_tiers.json"
    with open(def_tiers_path, "w") as f:
        json.dump(def_tiers_json, f)

    model_artifact = wandb.Artifact(
        name="outcome-model",
        type="model",
        metadata={"holdout_loss": candidate_score, "current_production_loss": current_score, "promoted": promoted},
    )
    for p in [model_path, yards_scaler_path, punt_scaler_path, def_tiers_path]:
        model_artifact.add_file(p)
    run.log_artifact(model_artifact)

    if promoted:
        model_artifact.wait()
        model_artifact.aliases.append("production")
        model_artifact.save()
        print(f"PROMOTED. candidate={candidate_score:.4f} vs current={current_score}")
    else:
        print(f"REJECTED. candidate={candidate_score:.4f} vs current={current_score:.4f}")

    run.summary["promoted"] = promoted
    run.summary["candidate_score"] = candidate_score
    run.summary["current_score"] = current_score

    gh_output = os.getenv("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"promoted={'true' if promoted else 'false'}\n")

    run.finish()

if __name__ == "__main__":
    main()