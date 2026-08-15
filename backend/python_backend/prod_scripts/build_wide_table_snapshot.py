import os
import sys
import wandb
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_wide_table import (
    extract_player_stats, extract_team_stats, extract_snap_counts,
    build_ol_ls_features, reshape_to_wide, validate,
)

WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")
OUTPUT_DIR = "prod_scripts/snapshot_tmp/wide_table"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run = wandb.init(project=WANDB_PROJECT, entity=WANDB_ENTITY, job_type="wide-table-snapshot")

    print("Fetching player_stats, team_stats, snap_counts from Supabase...")
    ps = extract_player_stats()
    ts = extract_team_stats()
    sc = extract_snap_counts()

    print("Building OL/LS features...")
    ol_ls = build_ol_ls_features(ts, sc)

    print("Reshaping to wide team-season table...")
    df_wide = reshape_to_wide(ps, ts, ol_ls)
    validate(df_wide)

    csv_path = os.path.join(OUTPUT_DIR, "wide_team_seasons.csv")
    df_wide.to_csv(csv_path, index=False)

    artifact = wandb.Artifact(
        name="wide-team-seasons",
        type="dataset",
        description="Wide team-season table (one row per team-season), input to TabSyn training",
        metadata={"row_count": len(df_wide), "columns": list(df_wide.columns)},
    )
    artifact.add_file(csv_path)
    run.log_artifact(artifact)
    run.finish()
    print(f"Logged 'wide-team-seasons' artifact ({len(df_wide)} rows).")

if __name__ == "__main__":
    main()