import os
import wandb

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")

def download_production_model_dir(artifact_name: str, dest_dir: str | None = None) -> str:
    """
    Downloads the full 'production'-tagged artifact directory for
    artifact_name. Use this when the model consists of multiple files
    (weights + scalers + config), which is the common case here.
    """
    api = wandb.Api()
    artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/{artifact_name}:production")
    local_dir = artifact.download(root=dest_dir) if dest_dir else artifact.download()
    return local_dir

def download_production_model(artifact_name: str, filename: str, dest_dir: str = "./model_weights"):
    api = wandb.Api()
    artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/{artifact_name}:production")
    local_dir = artifact.download(root=dest_dir)
    return os.path.join(local_dir, filename)