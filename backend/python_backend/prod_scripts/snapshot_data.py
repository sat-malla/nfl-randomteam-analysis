import os
import wandb
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WANDB_PROJECT = os.getenv("WANDB_PROJECT")
WANDB_ENTITY = os.getenv("WANDB_ENTITY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLES_TO_SNAPSHOT = {
    "player-stats": "player_stats",
    "team-stats": "team_stats",
    "return-stats": "return_stats",
    "punt-stats": "punt_stats",
    "coaches": "coaches",
    "schedules": "schedules",
}

OUTPUT_DIR = "scripts/snapshot_tmp"

def fetch_full_table(table_name: str, page_size: int = 1000) -> pd.DataFrame:
    all_rows = []
    start = 0
    while True:
        end = start + page_size - 1
        resp = supabase.table(table_name).select("*").range(start, end).execute()
        rows = resp.data
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        start += page_size
    return pd.DataFrame(all_rows)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run = wandb.init(project=WANDB_PROJECT, entity=WANDB_ENTITY, job_type="data-snapshot")

    for artifact_name, table_name in TABLES_TO_SNAPSHOT.items():
        print(f"Pulling {table_name} from Supabase...")
        df = fetch_full_table(table_name)
        if df.empty:
            print(f"WARNING: {table_name} came back empty, skipping.")
            continue

        csv_path = os.path.join(OUTPUT_DIR, f"{table_name}.csv")
        df.to_csv(csv_path, index=False)

        artifact = wandb.Artifact(
            name=artifact_name,
            type="dataset",
            description=f"Snapshot of Supabase table '{table_name}'",
            metadata={"row_count": len(df), "columns": list(df.columns), "source_table": table_name},
        )
        artifact.add_file(csv_path)
        run.log_artifact(artifact)
        print(f"Logged artifact '{artifact_name}' ({len(df)} rows).")

    run.finish()

if __name__ == "__main___":
    main()

