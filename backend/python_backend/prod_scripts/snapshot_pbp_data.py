import os
import wandb
import nflreadpy as nfl
from dotenv import load_dotenv

load_dotenv()

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")

SEASONS = list(range(2015, 2026))
OUTPUT_DIR = "prod_scripts/snapshot_tmp/pbp"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run = wandb.init(project=WANDB_PROJECT, entity=WANDB_ENTITY, job_type="pbp-snapshot")
    pbp_raw = nfl.load_pbp(SEASONS).to_pandas()
    csv_path = os.path.join(OUTPUT_DIR, "pbp_raw.csv")
    pbp_raw.to_csv(csv_path, index=False)
    artifact = wandb.Artifact(
        name="pbp-raw",
        type="dataset",
        description="Raw nflverse multi-season play-by-play data",
        metadata={"seasons": SEASONS, "row_count": len(pbp_raw), "columns": list(pbp_raw.columns)},
    )
    artifact.add_file(csv_path)
    run.log_artifact(artifact)
    run.finish()

if __name__ == "__main__":
    main()