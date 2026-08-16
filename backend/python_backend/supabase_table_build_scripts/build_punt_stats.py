import os
import nflreadpy
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

SEASONS = [2021, 2022, 2023, 2024]

df = nflreadpy.load_player_stats(seasons=SEASONS, summary_level="reg")

punters = df.filter((df["pt_att"] > 0) & (df["position"] == "P")).select([
    "player_display_name",
    "player_id",
    "position",
    "recent_team",
    "season",
    "pt_att",
    "pt_yards",
])

rows = []
for row in punters.to_dicts():
    rows.append({
        "player_display_name": row["player_display_name"],
        "player_id": row["player_id"],
        "position": row["position"],
        "team": row["recent_team"],
        "season": row["season"],
        "punt_attempts_season": int(row["pt_att"] or 0),
        "punt_yards_season": int(row["pt_yards"] or 0),
    })

print(f"Found {len(rows)} punter season rows")

BATCH = 500
for i in range(0, len(rows), BATCH):
    batch = rows[i:i + BATCH]
    supabase.table("punt_stats").upsert(
        batch,
        on_conflict="player_display_name,season"
    ).execute()
    print(f"Upserted rows {i + 1}–{min(i + BATCH, len(rows))} of {len(rows)}")

print("Done.")
