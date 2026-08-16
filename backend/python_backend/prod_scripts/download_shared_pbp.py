import os
import sys
import wandb
from dotenv import load_dotenv

load_dotenv()

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")

SHARED_PBP_DIR = "prod_scripts/_shared_pbp_cache"

def main():
    api = wandb.Api()
    artifact = api.artifact(f"{WANDB_ENTITY}/{WANDB_PROJECT}/pbp-raw:latest")
    artifact.download(root=SHARED_PBP_DIR)
    print(f"Downloaded pbp-raw to {SHARED_PBP_DIR}")

if __name__ == "__main__":
    main()