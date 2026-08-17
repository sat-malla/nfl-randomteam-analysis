from supabase import create_client
import os
import time
import nflreadpy as nfl
import polars as pl
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

YEARS = list(range(2015, datetime.now().year + 1))

def get_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment")
    return create_client(url, key)

def store_table(supabase, table_name, df):
    if df.is_empty():
        return
    
    records = df.to_dicts()
    supabase.table(table_name).delete().neq("id", 0).execute()

    chunk_size = 1000
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        supabase.table(table_name).insert(chunk).execute()
        time.sleep(0.5)

def player_stats_preprocess(df):
    df = df.filter(pl.col("season_type") == "REG")
    
    keep = [
        "player_id", "player_display_name", "position", "season", "season_type", "team",
        "completions", "attempts", "passing_yards", "passing_tds",
        "passing_interceptions", "pacr", "carries", "rushing_yards",
        "rushing_tds", "rushing_fumbles", "receptions", "targets",
        "receiving_yards", "receiving_tds", "def_tackles_solo", "def_sacks",
        "def_interceptions", "def_pass_defended", "fg_made", "fg_att", "fg_pct", 
        "punt_returns", "punt_return_yards", "kickoff_returns", "kickoff_return_yards"
    ]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)
    
    relevant_positions = ['DL', 'G', 'LS', 'P', 'NT', 'S', 'SAF', 'QB', 'FB', 'ILB', 'LB', 'DE', 'TE', 'CB', 'OLB', 'MLB', 'OT', 'FS', 'WR', 'RB', 'DB', 'C', 'OL', 'DT', 'K']
    df = df.filter(pl.col("position").is_in(relevant_positions))
    df = df.filter(pl.col("player_id").is_not_null() & pl.col("player_display_name").is_not_null())

    numeric_cols = [c for c in existing if c not in ["player_id", "player_display_name", "season_type", "position", "team"]]
    for c in numeric_cols:
        df = df.with_columns(pl.col(c).fill_null(0))
    
    team_mapping = {
      "ARI": "Arizona Cardinals",
      "ARZ": "Arizona Cardinals",
      "ATL": "Atlanta Falcons",
      "BAL": "Baltimore Ravens",
      "BLT": "Baltimore Ravens",
      "BUF": "Buffalo Bills",
      "CAR": "Carolina Panthers",
      "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals",
      "CLE": "Cleveland Browns",
      "CLV": "Cleveland Browns",
      "DAL": "Dallas Cowboys",
      "DEN": "Denver Broncos",
      "DET": "Detroit Lions",
      "GB": "Green Bay Packers",
      "HOU": "Houston Texans",
      "HST": "Houston Texans",
      "IND": "Indianapolis Colts",
      "JAX": "Jacksonville Jaguars",
      "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams",
      "LA": "Los Angeles Rams",
      "SL": "Los Angeles Rams",
      "STL": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers",
      "SD": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders",
      "OAK": "Las Vegas Raiders",
      "MIA": "Miami Dolphins",
      "MIN": "Minnesota Vikings",
      "NE": "New England Patriots",
      "NO": "New Orleans Saints",
      "NYG": "New York Giants",
      "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles",
      "PIT": "Pittsburgh Steelers",
      "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks",
      "TB": "Tampa Bay Buccaneers",
      "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
    }

    df = df.with_columns(pl.col("team").replace(team_mapping))

    return df


def team_stats_preprocess(df):
    df = df.filter(pl.col("season_type") == "REG")

    keep = [
        "team", "season", "season_type",
        "passing_yards", "passing_tds", "passing_interceptions",
        "rushing_yards", "rushing_tds", "carries",
        "receiving_yards", "receiving_tds", "def_tackles_solo",
        "def_sacks", "def_interceptions", "def_pass_defended",
        "fg_made", "fg_att", "fg_pct",
        "sacks_suffered", "def_qb_hits",
        "pt_att", "pt_yards", "pt_inside_20", "pt_net_yards",
        "pat_made", "pat_att",
    ]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)

    numeric_cols = [c for c in existing if c not in ["team", "season_type"]]
    for col in numeric_cols:
        df = df.with_columns(pl.col(col).fill_null(0))

    team_mapping = {
      "ARI": "Arizona Cardinals",
      "ARZ": "Arizona Cardinals",
      "ATL": "Atlanta Falcons",
      "BAL": "Baltimore Ravens",
      "BLT": "Baltimore Ravens",
      "BUF": "Buffalo Bills",
      "CAR": "Carolina Panthers",
      "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals",
      "CLE": "Cleveland Browns",
      "CLV": "Cleveland Browns",
      "DAL": "Dallas Cowboys",
      "DEN": "Denver Broncos",
      "DET": "Detroit Lions",
      "GB": "Green Bay Packers",
      "HOU": "Houston Texans",
      "HST": "Houston Texans",
      "IND": "Indianapolis Colts",
      "JAX": "Jacksonville Jaguars",
      "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams",
      "LA": "Los Angeles Rams",
      "STL": "Los Angeles Rams",
      "SL": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers",
      "SD": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders",
      "OAK": "Las Vegas Raiders",
      "MIA": "Miami Dolphins",
      "MIN": "Minnesota Vikings",
      "NE": "New England Patriots",
      "NO": "New Orleans Saints",
      "NYG": "New York Giants",
      "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles",
      "PIT": "Pittsburgh Steelers",
      "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks",
      "TB": "Tampa Bay Buccaneers",
      "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
    }

    df = df.with_columns(pl.col("team").replace(team_mapping))
    
    return df

def coaches_preprocess(df):
    keep = ["season", "home_team", "home_coach", "away_team", "away_coach"]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)

    df = df.filter(
        pl.col("home_coach").is_not_null() & pl.col("away_coach").is_not_null()
    )

    team_mapping = {
      "ARI": "Arizona Cardinals", "ARZ": "Arizona Cardinals",
      "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BLT": "Baltimore Ravens",
      "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "CLV": "Cleveland Browns",
      "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions",
      "GB": "Green Bay Packers", "HOU": "Houston Texans", "HST": "Houston Texans",
      "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams", "LA": "Los Angeles Rams", "STL": "Los Angeles Rams", "SL": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers", "SD": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders", "OAK": "Las Vegas Raiders",
      "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings", "NE": "New England Patriots",
      "NO": "New Orleans Saints", "NYG": "New York Giants", "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
    }

    home = df.select([
        pl.col("season"),
        pl.col("home_team").replace(team_mapping).alias("team"),
        pl.col("home_coach").alias("head_coach"),
    ])
    away = df.select([
        pl.col("season"),
        pl.col("away_team").replace(team_mapping).alias("team"),
        pl.col("away_coach").alias("head_coach"),
    ])

    combined = pl.concat([home, away])
    # Keep only the most recent coach per season per team
    combined = combined.sort("season", descending=True).unique(subset=["season", "team"], keep="first")

    return combined.sort(["season", "team"])


def schedules_preprocess(df):
    df = df.filter(pl.col("game_type") == "REG")
    
    keep = [
        "game_id", "season", "game_type", "week",
        "away_team", "away_score", "home_team", "home_score",
        "result", "total", "overtime", "roof", "surface", "temp", "wind",
    ]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)

    df = df.filter(pl.col("away_score").is_not_null() & pl.col("home_score").is_not_null())

    if "temp" in df.columns:
        df = df.with_columns(pl.col("temp").fill_null(70))
    if "wind" in df.columns:
        df = df.with_columns(pl.col("wind").fill_null(0))
    if "roof" in df.columns:
        df = df.with_columns(pl.col("roof").fill_null("unknown"))
    if "surface" in df.columns:
        df = df.with_columns(pl.col("surface").fill_null("unknown"))
    
    team_mapping = {
      "ARI": "Arizona Cardinals",
      "ARZ": "Arizona Cardinals",
      "ATL": "Atlanta Falcons",
      "BAL": "Baltimore Ravens",
      "BLT": "Baltimore Ravens",
      "BUF": "Buffalo Bills",
      "CAR": "Carolina Panthers",
      "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals",
      "CLE": "Cleveland Browns",
      "CLV": "Cleveland Browns",
      "DAL": "Dallas Cowboys",
      "DEN": "Denver Broncos",
      "DET": "Detroit Lions",
      "GB": "Green Bay Packers",
      "HOU": "Houston Texans",
      "HST": "Houston Texans",
      "IND": "Indianapolis Colts",
      "JAX": "Jacksonville Jaguars",
      "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams",
      "LA": "Los Angeles Rams",
      "STL": "Los Angeles Rams",
      "SL": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers",
      "SD": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders",
      "OAK": "Las Vegas Raiders",
      "MIA": "Miami Dolphins",
      "MIN": "Minnesota Vikings",
      "NE": "New England Patriots",
      "NO": "New Orleans Saints",
      "NYG": "New York Giants",
      "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles",
      "PIT": "Pittsburgh Steelers",
      "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks",
      "TB": "Tampa Bay Buccaneers",
      "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
    }

    df = df.with_columns(pl.col("away_team").replace(team_mapping))
    df = df.with_columns(pl.col("home_team").replace(team_mapping))
    
    return df

def rosters_preprocess(df):
    df = df.filter(pl.col("game_type") == "REG")
    
    keep = [
        "season", "team", "position", "depth_chart_position",
        "jersey_number", "status", "full_name", "first_name", "last_name",
         "height", "weight", "college", "sleeper_id", "game_type",
        "years_exp", "entry_year", "rookie_year", "draft_club", "draft_number",
    ]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)

    df = df.filter(pl.col("full_name").is_not_null())
    
    relevant_positions = ['DL', 'G', 'LS', 'P', 'NT', 'S', 'SAF', 'QB', 'FB', 'ILB', 'LB', 'DE', 'TE', 'CB', 'OLB', 'MLB', 'OT', 'FS', 'WR', 'RB', 'DB', 'C', 'OL', 'DT', 'K']
    df = df.filter(pl.col("position").is_in(relevant_positions))

    if "draft_number" in df.columns:
        df = df.with_columns(pl.col("draft_number").fill_null("UDFA"))
    if "depth_chart_position" in df.columns:
        df = df.with_columns(pl.col("depth_chart_position").fill_null("Practice Squad"))

    numeric_cols = [c for c in existing if c not in ["full_name", "position", "game_type", "team", "college"]]
    for c in numeric_cols:
        df = df.with_columns(pl.col(c).fill_null(0))
    
    team_mapping = {
      "ARI": "Arizona Cardinals",
      "ARZ": "Arizona Cardinals",
      "ATL": "Atlanta Falcons",
      "BAL": "Baltimore Ravens",
      "BLT": "Baltimore Ravens",
      "BUF": "Buffalo Bills",
      "CAR": "Carolina Panthers",
      "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals",
      "CLE": "Cleveland Browns",
      "CLV": "Cleveland Browns",
      "DAL": "Dallas Cowboys",
      "DEN": "Denver Broncos",
      "DET": "Detroit Lions",
      "GB": "Green Bay Packers",
      "HOU": "Houston Texans",
      "HST": "Houston Texans",
      "IND": "Indianapolis Colts",
      "JAX": "Jacksonville Jaguars",
      "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams",
      "LA": "Los Angeles Rams",
      "STL": "Los Angeles Rams",
      "SL": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers",
      "SD": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders",
      "OAK": "Las Vegas Raiders",
      "MIA": "Miami Dolphins",
      "MIN": "Minnesota Vikings",
      "NE": "New England Patriots",
      "NO": "New Orleans Saints",
      "NYG": "New York Giants",
      "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles",
      "PIT": "Pittsburgh Steelers",
      "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks",
      "TB": "Tampa Bay Buccaneers",
      "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
    }

    df = df.with_columns(pl.col("team").replace(team_mapping))

    return df

def depth_charts_preprocess(df):
    df = df.filter(pl.col("game_type") == "REG")
    
    keep = [
        "season", "club_code", "week", "game_type",
        "full_name", "position", "depth_position",
        "team", "player_name", "pos_name", "pos_rank"
    ]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)

    df = df.filter(pl.col("full_name").is_not_null())
    
    relevant_positions = ['DL', 'G', 'LS', 'P', 'NT', 'S', 'SAF', 'QB', 'FB', 'ILB', 'LB', 'DE', 'TE', 'CB', 'OLB', 'MLB', 'OT', 'FS', 'WR', 'RB', 'DB', 'C', 'OL', 'DT', 'K']
    df = df.filter(pl.col("position").is_in(relevant_positions))

    if "draft_number" in df.columns:
        df = df.with_columns(pl.col("draft_number").fill_null("UDFA"))
    if "depth_chart_position" in df.columns:
        df = df.with_columns(pl.col("depth_chart_position").fill_null("Practice Squad"))

    numeric_cols = [c for c in existing if c not in ["full_name", "position", "game_type", "team"]]
    for c in numeric_cols:
        df = df.with_columns(pl.col(c).fill_null(0))
    
    team_mapping = {
      "ARI": "Arizona Cardinals",
      "ARZ": "Arizona Cardinals",
      "ATL": "Atlanta Falcons",
      "BAL": "Baltimore Ravens",
      "BLT": "Baltimore Ravens",
      "BUF": "Buffalo Bills",
      "CAR": "Carolina Panthers",
      "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals",
      "CLE": "Cleveland Browns",
      "CLV": "Cleveland Browns",
      "DAL": "Dallas Cowboys",
      "DEN": "Denver Broncos",
      "DET": "Detroit Lions",
      "GB": "Green Bay Packers",
      "HOU": "Houston Texans",
      "HST": "Houston Texans",
      "IND": "Indianapolis Colts",
      "JAX": "Jacksonville Jaguars",
      "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams",
      "LA": "Los Angeles Rams",
      "STL": "Los Angeles Rams",
      "SL": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers",
      "SD": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders",
      "OAK": "Las Vegas Raiders",
      "MIA": "Miami Dolphins",
      "MIN": "Minnesota Vikings",
      "NE": "New England Patriots",
      "NO": "New Orleans Saints",
      "NYG": "New York Giants",
      "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles",
      "PIT": "Pittsburgh Steelers",
      "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks",
      "TB": "Tampa Bay Buccaneers",
      "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
    }

    df = df.with_columns(
        team = pl.when(pl.col("team").is_null())
                    .then(pl.col("club_code").replace(team_mapping))
                    .otherwise(pl.col("team"))
    )

    return df

def snap_counts_preprocess(df):
    df = df.filter(pl.col("game_type") == "REG")

    keep = ["game_id", "season", "game_type", "week", "player", "position", "team",
            "offense_pct", "st_pct"]
    existing = [col for col in keep if col in df.columns]
    df = df.select(existing)

    df = df.filter(pl.col("player").is_not_null() & pl.col("team").is_not_null())

    for c in ["offense_pct", "st_pct"]:
        if c in df.columns:
            df = df.with_columns(pl.col(c).fill_null(0.0))

    ol_ls_positions = ["T", "G", "C", "LS"]
    df = df.filter(pl.col("position").is_in(ol_ls_positions))

    df = (
        df.sort("offense_pct", descending=True)
        .unique(subset=["game_id", "player"], keep="first")
    )

    team_mapping = {
        "ARI": "Arizona Cardinals",   "ARZ": "Arizona Cardinals",
        "ATL": "Atlanta Falcons",     "BAL": "Baltimore Ravens",
        "BLT": "Baltimore Ravens",    "BUF": "Buffalo Bills",
        "CAR": "Carolina Panthers",   "CHI": "Chicago Bears",
        "CIN": "Cincinnati Bengals",  "CLE": "Cleveland Browns",
        "CLV": "Cleveland Browns",    "DAL": "Dallas Cowboys",
        "DEN": "Denver Broncos",      "DET": "Detroit Lions",
        "GB":  "Green Bay Packers",   "HOU": "Houston Texans",
        "HST": "Houston Texans",      "IND": "Indianapolis Colts",
        "JAX": "Jacksonville Jaguars","KC":  "Kansas City Chiefs",
        "LAR": "Los Angeles Rams",    "LA":  "Los Angeles Rams",
        "SL":  "Los Angeles Rams",    "STL": "Los Angeles Rams",
        "LAC": "Los Angeles Chargers","SD":  "Los Angeles Chargers",
        "LV":  "Las Vegas Raiders",   "OAK": "Las Vegas Raiders",
        "MIA": "Miami Dolphins",      "MIN": "Minnesota Vikings",
        "NE":  "New England Patriots","NO":  "New Orleans Saints",
        "NYG": "New York Giants",     "NYJ": "New York Jets",
        "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
        "SF":  "San Francisco 49ers", "SEA": "Seattle Seahawks",
        "TB":  "Tampa Bay Buccaneers","TEN": "Tennessee Titans",
        "WAS": "Washington Commanders",
    }
    df = df.with_columns(pl.col("team").replace(team_mapping))

    return df


def upsert_snap_counts(supabase, df):
    """Upsert snap_counts in chunks — too large for wipe-reinsert."""
    if df.is_empty():
        return
    records = df.to_dicts()
    chunk_size = 1000
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        seen = {}
        for row in chunk:
            key = (row["game_id"], row["player"])
            if key not in seen:
                seen[key] = row
        chunk = list(seen.values())
        supabase.table("snap_counts").upsert(chunk, on_conflict="game_id,player").execute()
        time.sleep(0.2)

def main():
    supabase_client = get_client()

    # Player stats
    player_stats = nfl.load_player_stats(seasons=YEARS)
    player_stats = player_stats_preprocess(player_stats)
    store_table(supabase_client, "player_stats", player_stats)

    # Depth charts
    depth_charts = nfl.load_depth_charts(seasons=list(range(2015, 2026)))
    depth_charts = depth_charts_preprocess(depth_charts)
    store_table(supabase_client, "depth_charts", depth_charts)

    # Rosters
    rosters = nfl.load_rosters(seasons=list(range(2015, 2026)))
    rosters = rosters_preprocess(rosters)
    store_table(supabase_client, "rosters", rosters)

    # Team stats (now includes sacks_suffered, def_qb_hits, pt_*, pat_*)
    team_stats = nfl.load_team_stats(seasons=list(range(2015, 2026)))
    team_stats = team_stats_preprocess(team_stats)
    store_table(supabase_client, "team_stats", team_stats)

    # Schedules
    schedules_raw = nfl.load_schedules(seasons=list(range(2015, 2026)))
    schedules = schedules_preprocess(schedules_raw)
    store_table(supabase_client, "schedules", schedules)

    # Coaches
    coaches = coaches_preprocess(schedules_raw)
    store_table(supabase_client, "coaches", coaches)

    # Snap counts
    print("Loading snap counts (OL/LS only)...")
    snap_counts_raw = nfl.load_snap_counts(seasons=list(range(2015, 2026)))
    snap_counts = snap_counts_preprocess(snap_counts_raw)
    print(f"Upserting {len(snap_counts)} snap count rows...")
    upsert_snap_counts(supabase_client, snap_counts)

if __name__ == "__main__":
    main()
