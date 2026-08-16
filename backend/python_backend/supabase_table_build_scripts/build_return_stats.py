import os
import nflreadpy
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

SEASONS = [2021, 2022, 2023, 2024]

df = nflreadpy.load_player_stats(seasons=SEASONS, summary_level="reg")

ret = df.filter(
    (df["kickoff_return_yards"] > 0) | (df["punt_return_yards"] > 0)
).select([
    "player_display_name",
    "player_id",
    "position",
    "recent_team",
    "season",
    "kickoff_returns",
    "kickoff_return_yards",
    "punt_returns",
    "punt_return_yards",
])

rows = []
for row in ret.to_dicts():
    rows.append({
        "player_display_name": row["player_display_name"],
        "player_id": row["player_id"],
        "position": row["position"],
        "team": row["recent_team"],
        "season": row["season"],
        "kickoff_returns": int(row["kickoff_returns"] or 0),
        "kickoff_return_yards": int(row["kickoff_return_yards"] or 0),
        "punt_returns": int(row["punt_returns"] or 0),
        "punt_return_yards": int(row["punt_return_yards"] or 0),
    })

BATCH = 500
for i in range(0, len(rows), BATCH):
    batch = rows[i:i + BATCH]
    supabase.table("return_stats").upsert(
        batch,
        on_conflict="player_display_name,season"
    ).execute()
    print(f"Upserted rows {i + 1}-{min(i + BATCH, len(rows))} of {len(rows)}")

print("Done.")
