import os
import wandb

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")

def download_production_model(artifact_name: str, filename: str, dest_dir: str = "./model_weights"):
    api = wandb.Api()
    artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/{artifact_name}:production")
    local_dir = artifact.download(root=dest_dir)
    return os.path.join(local_dir, filename)