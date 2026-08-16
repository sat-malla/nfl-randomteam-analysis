import os
import json
import pickle
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import DataLoader, TensorDataset
import wandb
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.play_call_model_arch import (
    PlayCallMLP, FEATURE_COLS, FEAT_CARDINALITY, EMB_DIM, HIDDEN, DROPOUT,
    dist_bucket, yard_zone, score_bucket, time_bucket, INFERENCE_TEMPERATURE, PASS_BOOST,
)

warnings.filterwarnings("ignore")

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SHARED_PBP_DIR = "prod_scripts/_shared_pbp_cache"

EPOCHS = 80
BATCH_SIZE = 4096
LR = 3e-3
HOLDOUT_SEASON = 2025
PROMOTION_TOLERANCE = 0.98  # candidate must reach >= 98% of current production's val accuracy

def load_pbp_data(run) -> pd.DataFrame:
    csv_path = os.path.join(SHARED_PBP_DIR, "pbp_raw.csv")
    if os.path.exists(csv_path):
        print(f"Using shared cached PBP data at {csv_path}")
    else:
        artifact = run.use_artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/pbp-raw:latest")
        data_dir = artifact.download(root=SHARED_PBP_DIR)
        csv_path = os.path.join(data_dir, "pbp_raw.csv")
    return pd.read_csv(csv_path, low_memory=False)

def prepare_dataset(pbp_raw: pd.DataFrame):
    KEEP_TYPES = {"run", "pass", "punt", "field_goal"}
    df = pbp_raw[
        pbp_raw["play_type"].isin(KEEP_TYPES) &
        pbp_raw["down"].notna() &
        pbp_raw["ydstogo"].notna() &
        pbp_raw["yardline_100"].notna() &
        pbp_raw["score_differential"].notna() &
        pbp_raw["qtr"].notna() &
        pbp_raw["game_seconds_remaining"].notna()
    ].copy()

    df["shotgun"] = df["shotgun"].fillna(0).astype(int)
    df["goal_to_go"] = df["goal_to_go"].fillna(0).astype(int)
    df["feat_down"] = df["down"].astype(int) - 1
    df["feat_dist"] = df["ydstogo"].apply(dist_bucket)
    df["feat_zone"] = df["yardline_100"].apply(yard_zone)
    df["feat_score"] = df["score_differential"].apply(score_bucket)
    df["feat_qtr"] = (df["qtr"].clip(1, 5) - 1).astype(int)
    df["feat_time"] = df.apply(lambda r: time_bucket(r["game_seconds_remaining"], r["qtr"]), axis=1)
    df["feat_half_end"] = (
        ((df["qtr"] == 2) & (df["game_seconds_remaining"] <= 1860)) |
        ((df["qtr"] >= 4) & (df["game_seconds_remaining"] <= 120))
    ).astype(int)
    df["feat_trailing"] = (df["score_differential"] < 0).astype(int)
    df["feat_shotgun"] = df["shotgun"]
    df["feat_goal_to_go"] = df["goal_to_go"]

    return df

def oversample_passing_situations(df: pd.DataFrame) -> pd.DataFrame:
    passing_situation = (
        ((df["down"] >= 2) & (df["ydstogo"] >= 7) & (df["play_type"].isin(["run", "pass"]))) |
        ((df["down"] == 3) & (df["ydstogo"] >= 4) & (df["play_type"].isin(["run", "pass"]))) |
        ((df["shotgun"] == 1) & (df["play_type"].isin(["run", "pass"])))
    )
    df_passing = df[passing_situation]
    return pd.concat([df, df_passing.sample(frac=0.5, random_state=42)], ignore_index=True)

def build_class_weights(y_train: np.ndarray, le: LabelEncoder, n_classes: int) -> torch.Tensor:
    class_counts = np.bincount(y_train, minlength=n_classes)
    class_weights = 1.0 / np.maximum(class_counts.astype(float), 1)
    class_weights = class_weights / class_weights.sum() * n_classes
    pass_idx = list(le.classes_).index("pass")
    class_weights[pass_idx] *= PASS_BOOST
    class_weights = class_weights / class_weights.sum() * n_classes
    return torch.FloatTensor(class_weights).to(DEVICE)

def train_model(X_train: np.ndarray, y_train: np.ndarray, le: LabelEncoder, n_classes: int) -> PlayCallMLP:
    model = PlayCallMLP(FEAT_CARDINALITY, EMB_DIM, HIDDEN, n_classes, DROPOUT).to(DEVICE)
    class_weights_t = build_class_weights(y_train, le, n_classes)

    X_tr_t = torch.LongTensor(X_train).to(DEVICE)
    y_tr_t = torch.LongTensor(y_train).to(DEVICE)
    train_dl = DataLoader(TensorDataset(X_tr_t, y_tr_t), batch_size=BATCH_SIZE, shuffle=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=LR, steps_per_epoch=len(train_dl), epochs=EPOCHS)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        for xb, yb in train_dl:
            optimizer.zero_grad()
            loss = F.cross_entropy(model(xb), yb, weight=class_weights_t)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{EPOCHS}")

    return model

def evaluate_on_holdout(model: PlayCallMLP, X_holdout: np.ndarray, y_holdout: np.ndarray) -> float:
    model.eval()
    X_t = torch.LongTensor(X_holdout).to(DEVICE)
    y_t = torch.LongTensor(y_holdout).to(DEVICE)
    with torch.no_grad():
        logits = model(X_t)
        acc = (logits.argmax(-1) == y_t).float().mean().item()
    return acc

def load_current_production_model(n_classes: int):
    api = wandb.Api()
    try:
        artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/play-call-model:production")
    except wandb.errors.CommError:
        return None
    model_dir = artifact.download()
    model = PlayCallMLP(FEAT_CARDINALITY, EMB_DIM, HIDDEN, n_classes, DROPOUT).to(DEVICE)
    model.load_state_dict(torch.load(os.path.join(model_dir, "play_call_model.pt"), map_location=DEVICE))
    return model

def main():
    run = wandb.init(project=WANDB_PROJECT, entity=WANDB_ENTITY, job_type="train-play-call-model")

    pbp_raw = load_pbp_data(run)
    df = prepare_dataset(pbp_raw)

    le = LabelEncoder()
    df["label"] = le.fit_transform(df["play_type"])
    n_classes = len(le.classes_)

    holdout_df = df[df["season"] == HOLDOUT_SEASON]
    train_df = df[df["season"] != HOLDOUT_SEASON]
    train_df_aug = oversample_passing_situations(train_df)

    X_train = train_df_aug[FEATURE_COLS].values.astype(np.int64)
    y_train = train_df_aug["label"].values.astype(np.int64)
    X_holdout = holdout_df[FEATURE_COLS].values.astype(np.int64)
    y_holdout = holdout_df["label"].values.astype(np.int64)

    print(f"Train: {len(X_train):,}; Holdout ({HOLDOUT_SEASON}): {len(X_holdout):,}")

    candidate_model = train_model(X_train, y_train, le, n_classes)
    candidate_score = evaluate_on_holdout(candidate_model, X_holdout, y_holdout)

    current_model = load_current_production_model(n_classes)
    current_score = evaluate_on_holdout(current_model, X_holdout, y_holdout) if current_model is not None else None

    promoted = current_score is None or candidate_score >= current_score * PROMOTION_TOLERANCE

    os.makedirs("prod_scripts/train_tmp", exist_ok=True)
    model_path = "prod_scripts/train_tmp/play_call_model.pt"
    torch.save(candidate_model.state_dict(), model_path)

    le_path = "prod_scripts/train_tmp/play_call_label_encoder.pkl"
    with open(le_path, "wb") as f:
        pickle.dump(le, f)

    feature_meta = {"feature_cols": FEATURE_COLS, "feat_cardinality": FEAT_CARDINALITY, "classes": list(le.classes_)}
    meta_path = "prod_scripts/train_tmp/play_call_feature_meta.json"
    with open(meta_path, "w") as f:
        json.dump(feature_meta, f, indent=2)

    config_path = "prod_scripts/train_tmp/play_call_config.json"
    with open(config_path, "w") as f:
        json.dump({
            "emb_dim": EMB_DIM, "hidden": HIDDEN, "dropout": DROPOUT,
            "n_classes": n_classes, "n_features": len(FEATURE_COLS),
            "inference_temperature": INFERENCE_TEMPERATURE, "pass_boost": PASS_BOOST,
            "holdout_accuracy": candidate_score,
        }, f, indent=2)

    model_artifact = wandb.Artifact(
        name="play-call-model", type="model",
        metadata={"holdout_accuracy": candidate_score, "current_production_accuracy": current_score, "promoted": promoted},
    )
    for p in [model_path, le_path, meta_path, config_path]:
        model_artifact.add_file(p)
    run.log_artifact(model_artifact)

    if promoted:
        model_artifact.wait()
        model_artifact.aliases.append("production")
        model_artifact.save()
        print(f"PROMOTED. candidate_acc={candidate_score:.4f} vs current_acc={current_score}")
    else:
        print(f"REJECTED. candidate_acc={candidate_score:.4f} vs current_acc={current_score:.4f}")

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