import os
import json
import pickle
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import QuantileTransformer
from torch.utils.data import DataLoader, TensorDataset
import wandb
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.tabsyn_arch import (
    Encoder, Decoder, ScoreNet, build_noise_schedule,
    LATENT_D, HIDDEN_D, CAT_EMB_DIM, T_STEPS,
    CATEGORICAL_COLS, DROP_COLS, DDPM_SAMPLE_STEPS,
    BETA_MIN, BETA_MAX
)

warnings.filterwarnings("ignore")

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

VAE_EPOCHS = 2000
DIFF_EPOCHS = 5000
BATCH_SIZE = 64
N_VALIDATE = 500
PROMOTION_TOLERANCE = 1.10

def load_wide_table(run) -> pd.DataFrame:
    artifact = run.use_artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/wide-team-seasons:latest")
    data_dir = artifact.download()
    return pd.read_csv(os.path.join(data_dir, "wide_team_seasons.csv"))

def prepare_data(df_raw: pd.DataFrame):
    df = df_raw.drop(columns=[c for c in DROP_COLS if c in df_raw.columns]).copy()
    assert df.isnull().sum().sum() == 0, "NaNs found in wide table - fix upstream before training"

    continuous_cols = [c for c in df.columns if c not in CATEGORICAL_COLS]
    cat_encoders = {}
    for col in CATEGORICAL_COLS:
        unique_vals = sorted(df[col].unique())
        encoder = {v: i for i, v in enumerate(unique_vals)}
        cat_encoders[col] = encoder
        df[col] = df[col].map(encoder)

    df_train, df_val = train_test_split(df, test_size=0.10, random_state=42)

    qt = QuantileTransformer(output_distribution="normal", random_state=42)

    X_train_cont = qt.fit_transform(df_train[continuous_cols].values.astype(float))
    X_val_cont = qt.transform(df_val[continuous_cols].values.astype(float))
    X_train_cat = df_train[CATEGORICAL_COLS].values.astype(int)
    X_val_cat = df_val[CATEGORICAL_COLS].values.astype(int)

    cat_dims = [int(df[col].max()) + 1 for col in CATEGORICAL_COLS]

    reverse_encoders = {
        col: {str(int(code)): int(val) for val, code in enc.items()}
        for col, enc in cat_encoders.items()
    }
    col_meta = {
        "all_columns": list(df.columns),
        "continuous_columns": continuous_cols,
        "categorical_columns": CATEGORICAL_COLS,
        "dropped_columns": DROP_COLS,
    }

    train_cont_mean = df_raw[[c for c in continuous_cols if c in df_raw.columns]].mean().values.astype(float)
    train_cont_std = df_raw[[c for c in continuous_cols if c in df_raw.columns]].std().values.astype(float).clip(min=1e-6)

    return {
        "X_train_cont": X_train_cont, "X_val_cont": X_val_cont,
        "X_train_cat": X_train_cat, "X_val_cat": X_val_cat,
        "cat_dims": cat_dims, "qt": qt,
        "reverse_encoders": reverse_encoders, "col_meta": col_meta,
        "continuous_cols": continuous_cols,
        "train_cont_mean": train_cont_mean, "train_cont_std": train_cont_std,
    }

def build_input(cat_embeddings: nn.ModuleList, x_cont_t, x_cat_t, n_cat: int):
    embs = [cat_embeddings[i](x_cat_t[:, i]) for i in range(n_cat)]
    return torch.cat([x_cont_t] + embs, dim=-1)

def vae_loss(encoder, decoder, cat_embeddings, x_cont_t, x_cat_t, n_cat, beta=0.001):
    x_in = build_input(cat_embeddings, x_cont_t, x_cat_t, n_cat)
    mu, log = encoder(x_in)
    std = torch.exp(0.5 * log)
    z = mu + std * torch.randn_like(std)

    recon_cont, recon_cat = decoder(z)
    loss_cont = F.mse_loss(recon_cont, x_cont_t)
    loss_cat = sum(F.cross_entropy(recon_cat[i], x_cat_t[:, i]) for i in range(n_cat)) / max(n_cat, 1)
    kl = -0.5 * (1 + log - mu.pow(2) - log.exp()).mean()

    return loss_cont + loss_cat + beta * kl

def train_vae(data: dict):
    n_cont = len(data["continuous_cols"])
    n_cat = len(CATEGORICAL_COLS)
    cat_dims = data["cat_dims"]
    cat_embeddings = nn.ModuleList([nn.Embedding(d, CAT_EMB_DIM) for d in cat_dims]).to(DEVICE)
    in_dim = n_cont + n_cat * CAT_EMB_DIM
    encoder = Encoder(in_dim, LATENT_D, HIDDEN_D).to(DEVICE)
    decoder = Decoder(LATENT_D, n_cont, cat_dims, HIDDEN_D).to(DEVICE)

    vae_params = list(encoder.parameters()) + list(decoder.parameters()) + list(cat_embeddings.parameters())
    vae_opt = torch.optim.AdamW(vae_params, lr=1e-3, weight_decay=1e-4)
    vae_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(vae_opt, T_max=VAE_EPOCHS)

    X_cont_tr = torch.FloatTensor(data["X_train_cont"]).to(DEVICE)
    X_cat_tr = torch.LongTensor(data["X_train_cat"]).to(DEVICE)
    X_cont_vl = torch.FloatTensor(data["X_val_cont"]).to(DEVICE)
    X_cat_vl = torch.LongTensor(data["X_val_cat"]).to(DEVICE)

    train_dl = DataLoader(TensorDataset(X_cont_tr, X_cat_tr), batch_size=BATCH_SIZE, shuffle=True)

    best_val_loss = float("inf")
    best_state = None

    for epoch in range(1, VAE_EPOCHS + 1):
        encoder.train(); decoder.train(); cat_embeddings.train()
        for xc, xk in train_dl:
            vae_opt.zero_grad()
            loss = vae_loss(encoder, decoder, cat_embeddings, xc, xk, n_cat)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(vae_params, 1.0)
            vae_opt.step()
        vae_scheduler.step()

        if epoch % 200 == 0 or epoch == 1:
            encoder.eval()
            decoder.eval()
            cat_embeddings.eval()
            with torch.no_grad():
                val_loss = vae_loss(encoder, decoder, cat_embeddings, X_cont_vl, X_cat_vl, n_cat).item()
            print(f"VAE epoch {epoch:4d} | val {val_loss:.4f}")
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {
                    "encoder": {k: v.clone() for k, v in encoder.state_dict().items()},
                    "decoder": {k: v.clone() for k, v in decoder.state_dict().items()},
                    "cat_embeddings": {k: v.clone() for k, v in cat_embeddings.state_dict().items()},
                }

    encoder.load_state_dict(best_state["encoder"])
    decoder.load_state_dict(best_state["decoder"])
    cat_embeddings.load_state_dict(best_state["cat_embeddings"])
    print(f"VAE training complete. Best val loss: {best_val_loss:.4f}")
    return encoder, decoder, cat_embeddings

def train_diffusion(encoder, cat_embeddings, data: dict):
    n_cat = len(CATEGORICAL_COLS)
    X_cont_tr = torch.FloatTensor(data["X_train_cont"]).to(DEVICE)
    X_cat_tr = torch.LongTensor(data["X_train_cat"]).to(DEVICE)

    encoder.eval()
    cat_embeddings.eval()
    with torch.no_grad():
        x_in_full = build_input(cat_embeddings, X_cont_tr, X_cat_tr, n_cat)
        mu_train, _ = encoder(x_in_full)

    Z_train = mu_train.cpu()
    z_mean = Z_train.mean(0)
    z_std = Z_train.std(0).clamp(min=1e-6)
    Z_norm = (Z_train - z_mean) / z_std

    score_net = ScoreNet(LATENT_D, HIDDEN_D).to(DEVICE)
    diff_opt = torch.optim.AdamW(score_net.parameters(), lr=1e-3, weight_decay=1e-4)
    diff_sched = torch.optim.lr_scheduler.CosineAnnealingLR(diff_opt, T_max=DIFF_EPOCHS)

    betas, alphas, alpha_bar = build_noise_schedule(DEVICE)
    Z_dl = DataLoader(TensorDataset(Z_norm.to(DEVICE)), batch_size=BATCH_SIZE, shuffle=True)

    def diffusion_loss(z0_batch):
        B = z0_batch.shape[0]
        t = torch.randint(0, T_STEPS, (B,), device=DEVICE)
        noise = torch.randn_like(z0_batch)
        ab = alpha_bar[t].unsqueeze(1)
        z_t = torch.sqrt(ab) * z0_batch + torch.sqrt(1 - ab) * noise
        t_frac = t.float() / T_STEPS
        pred_noise = score_net(z_t, t_frac)
        return F.mse_loss(pred_noise, noise)

    best_diff_loss = float("inf")
    best_state = None

    for epoch in range(1, DIFF_EPOCHS + 1):
        score_net.train()
        epoch_loss = 0.0
        for (z,) in Z_dl:
            diff_opt.zero_grad()
            loss = diffusion_loss(z)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(score_net.parameters(), 1.0)
            diff_opt.step()
            epoch_loss += loss.item()
        diff_sched.step()

        if epoch % 500 == 0 or epoch == 1:
            avg = epoch_loss / len(Z_dl)
            print(f"Diff epoch {epoch:5d} | loss {avg:.6f}")
            if avg < best_diff_loss:
                best_diff_loss = avg
                best_state = {k: v.clone() for k, v in score_net.state_dict().items()}

    score_net.load_state_dict(best_state)
    print(f"Diffusion training complete. Best loss: {best_diff_loss:.6f}")
    return score_net, z_mean, z_std

def train_model(data: dict) -> dict:
    encoder, decoder, cat_embeddings = train_vae(data)
    score_net, z_mean, z_std = train_diffusion(encoder, cat_embeddings, data)
    return {
        "encoder": encoder, "decoder": decoder, "cat_embeddings": cat_embeddings,
        "score_net": score_net, "z_mean": z_mean, "z_std": z_std,
    }

@torch.no_grad()
def ddpm_sample(score_net, z_mean, z_std, n_samples: int, ddpm_steps: int = DDPM_SAMPLE_STEPS) -> torch.Tensor:
    betas, alphas, alpha_bar = build_noise_schedule(DEVICE)
    score_net.eval()
    z_mean_d, z_std_d = z_mean.to(DEVICE), z_std.to(DEVICE)
    z = torch.randn(n_samples, LATENT_D, device=DEVICE)

    step_indices = torch.linspace(T_STEPS - 1, 0, ddpm_steps, dtype=torch.long)
    for t_idx in step_indices:
        t_val = t_idx.float() / T_STEPS
        t_batch = t_val.expand(n_samples).to(DEVICE)
        pred_noise = score_net(z, t_batch)
        alpha_t, alpha_bar_t, beta_t = alphas[t_idx], alpha_bar[t_idx], betas[t_idx]
        coef1 = 1.0 / torch.sqrt(alpha_t)
        coef2 = beta_t / torch.sqrt(1 - alpha_bar_t)
        mean = coef1 * (z - coef2 * pred_noise)
        if t_idx > 0:
            z = mean + torch.sqrt(beta_t) * torch.randn_like(z)
        else:
            z = mean

    return z * z_std_d + z_mean_d

@torch.no_grad()
def latents_to_df(decoder, z_samples: torch.Tensor, data: dict) -> pd.DataFrame:
    decoder.eval()
    recon_cont, recon_cat = decoder(z_samples)
    cont_np = data["qt"].inverse_transform(recon_cont.cpu().numpy())
    gen_mean = cont_np.mean(axis=0)
    gen_std = cont_np.std(axis=0).clip(min=1e-6)
    cont_np = (cont_np - gen_mean) / gen_std * data["train_cont_std"] + data["train_cont_mean"]
    cont_np = np.maximum(cont_np, 0)
    df_out = pd.DataFrame(cont_np, columns=data["continuous_cols"])

    for i, col in enumerate(CATEGORICAL_COLS):
        codes = recon_cat[i].argmax(dim=-1).cpu().numpy()
        rev_enc = data["reverse_encoders"][col]
        df_out[col] = [rev_enc.get(str(c), c) for c in codes]

    for col in data["col_meta"]["all_columns"]:
        if col not in df_out.columns:
            df_out[col] = 0

    df_out = df_out[[c for c in data["col_meta"]["all_columns"] if c != "team"]]
    return df_out

def count_violations(df_gen: pd.DataFrame) -> int:
    total = 0

    wr_td_sum = df_gen["wr1_receiving_tds"] + df_gen["wr2_receiving_tds"] + df_gen["wr3_receiving_tds"]
    skill_td_sum = (
        wr_td_sum + df_gen["rb1_receiving_tds"] + df_gen["rb2_receiving_tds"]
        + df_gen["te1_receiving_tds"] + df_gen["te2_receiving_tds"]
    )
    total += int((skill_td_sum > df_gen["team_passing_tds"] + 5).sum())
    total += int((df_gen["k_fg_made"] > df_gen["k_fg_att"] + 0.5).sum())
    total += int((df_gen["rb2_carries"] > df_gen["rb1_carries"]).sum())
    total += int((df_gen["wr2_targets"] > df_gen["wr1_targets"]).sum())

    return total

def evaluate_on_holdout(model_dict: dict, data: dict) -> float:
    z_samples = ddpm_sample(model_dict["score_net"], model_dict["z_mean"], model_dict["z_std"], N_VALIDATE)
    df_gen = latents_to_df(model_dict["decoder"], z_samples, data)
    return float(count_violations(df_gen))

def load_current_production_model(data: dict):
    api = wandb.Api()
    try:
        artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/tabsyn-model:production")
    except wandb.errors.CommError:
        return None
    model_dir = artifact.download()

    n_cont = len(data["continuous_cols"])
    cat_dims = data["cat_dims"]
    n_cat = len(CATEGORICAL_COLS)
    cat_embeddings = nn.ModuleList([nn.Embedding(d, CAT_EMB_DIM) for d in cat_dims]).to(DEVICE)
    in_dim = n_cont + n_cat * CAT_EMB_DIM
    encoder = Encoder(in_dim, LATENT_D, HIDDEN_D).to(DEVICE)
    decoder = Decoder(LATENT_D, n_cont, cat_dims, HIDDEN_D).to(DEVICE)
    score_net = ScoreNet(LATENT_D, HIDDEN_D).to(DEVICE)

    vae_ckpt = torch.load(os.path.join(model_dir, "vae_best.pt"), map_location=DEVICE)
    encoder.load_state_dict(vae_ckpt["encoder"])
    decoder.load_state_dict(vae_ckpt["decoder"])
    cat_embeddings.load_state_dict(vae_ckpt["cat_embeddings"])
    score_net.load_state_dict(torch.load(os.path.join(model_dir, "score_net_best.pt"), map_location=DEVICE))
    norm = torch.load(os.path.join(model_dir, "latent_norm.pt"), map_location=DEVICE)

    return {
        "encoder": encoder, "decoder": decoder, "cat_embeddings": cat_embeddings,
        "score_net": score_net, "z_mean": norm["z_mean"], "z_std": norm["z_std"],
    }

def main():
    run = wandb.init(project=WANDB_PROJECT, entity=WANDB_ENTITY, job_type="train-tabsyn")

    df_raw = load_wide_table(run)
    data = prepare_data(df_raw)

    candidate_model = train_model(data)
    candidate_score = evaluate_on_holdout(candidate_model, data)
    current_model = load_current_production_model(data)
    current_score = evaluate_on_holdout(current_model, data) if current_model is not None else None
    promoted = current_score is None or candidate_score <= current_score * PROMOTION_TOLERANCE

    os.makedirs("prod_scripts/train_tmp", exist_ok=True)
    vae_path = "prod_scripts/train_tmp/vae_best.pt"
    torch.save({
        "encoder": candidate_model["encoder"].state_dict(),
        "decoder": candidate_model["decoder"].state_dict(),
        "cat_embeddings": candidate_model["cat_embeddings"].state_dict(),
    }, vae_path)

    score_net_path = "prod_scripts/train_tmp/score_net_best.pt"
    torch.save(candidate_model["score_net"].state_dict(), score_net_path)

    latent_norm_path = "prod_scripts/train_tmp/latent_norm.pt"
    torch.save({"z_mean": candidate_model["z_mean"], "z_std": candidate_model["z_std"]}, latent_norm_path)

    qt_path = "prod_scripts/train_tmp/quantile_transformer.pkl"
    with open(qt_path, "wb") as f:
        pickle.dump(data["qt"], f)

    cat_enc_path = "prod_scripts/train_tmp/cat_encoders.json"
    with open(cat_enc_path, "w") as f:
        json.dump(data["reverse_encoders"], f, indent=2)

    col_meta_path = "prod_scripts/train_tmp/column_meta.json"
    with open(col_meta_path, "w") as f:
        json.dump(data["col_meta"], f, indent=2)

    config_path = "prod_scripts/train_tmp/model_config.json"
    with open(config_path, "w") as f:
        json.dump({
            "latent_dim": LATENT_D, "hidden_dim": HIDDEN_D, "cat_emb_dim": CAT_EMB_DIM,
            "n_continuous": len(data["continuous_cols"]), "n_categorical": len(CATEGORICAL_COLS),
            "cat_dims": data["cat_dims"], "T_steps": T_STEPS,
            "beta_min": BETA_MIN, "beta_max": BETA_MAX,
            "ddpm_sample_steps": DDPM_SAMPLE_STEPS,
        }, f, indent=2)

    model_artifact = wandb.Artifact(
        name="tabsyn-model", type="model",
        metadata={"violation_count": candidate_score, "current_production_violations": current_score, "promoted": promoted},
    )
    for p in [vae_path, score_net_path, latent_norm_path, qt_path, cat_enc_path, col_meta_path, config_path]:
        model_artifact.add_file(p)
    run.log_artifact(model_artifact)

    if promoted:
        model_artifact.wait()
        model_artifact.aliases.append("production")
        model_artifact.save()
        print(f"PROMOTED. candidate_violations={candidate_score} vs current={current_score}")
    else:
        print(f"REJECTED. candidate_violations={candidate_score} vs current={current_score}")

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