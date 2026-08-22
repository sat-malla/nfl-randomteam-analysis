from fastapi import FastAPI, HTTPException
from supabase import create_client
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from scipy import stats
from scipy.stats import norm

import pandas as pd
import numpy as np

import random
import os
import httpx
import certifi
import traceback

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

mongo_client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
mongo_db = mongo_client["nfl-random-teams"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POS_STAT_MAPPING = {
    "QB": ["passing_yards", "passing_tds", "passing_interceptions", "carries", "rushing_yards", "rushing_tds"],
    "RB": ["carries", "rushing_yards", "rushing_tds", "receptions", "targets", "receiving_yards", "receiving_tds"],
    "FB": ["carries", "rushing_yards", "rushing_tds", "receptions", "targets", "receiving_yards", "receiving_tds"],
    "WR": ["receptions", "receiving_yards", "receiving_tds", "targets", "carries", "rushing_yards", "rushing_tds"],
    "TE": ["receptions", "receiving_yards", "receiving_tds", "targets"],
    "DE": ["def_sacks", "def_tackles_solo", "def_pass_defended"],
    "DT": ["def_sacks", "def_tackles_solo", "def_pass_defended"],
    "NT": ["def_tackles_solo", "def_sacks", "def_pass_defended"],
    "DL": ["def_sacks", "def_tackles_solo", "def_pass_defended"],
    "LB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"],
    "OLB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"],
    "ILB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"],
    "MLB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"],
    "SLB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"],
    "WLB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"],
    "CB": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "FS": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "SS": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "S": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "SAF": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "Nickel": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "Dime": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "K": ["fg_made", "fg_att"],
    "P": ["punt_yards_season", "punt_attempts_season"],
    "OT": [],
    "G": [],
    "C": [],
    "LS": [],
    "RS": ["kickoff_return_yards", "kickoff_returns", "punt_return_yards", "punt_returns"],
}

POSITION_PRIMARY_STAT = {
    "QB": "passing_yards",
    "RB": "rushing_yards",
    "WR": "receiving_yards",
    "TE": "receiving_yards",
    "K": "fg_made",
    "P": "punt_attempts_season",
    "RS": "kickoff_return_yards",
    "LB":  "def_tackles_solo",
    "OLB": "def_tackles_solo",
    "ILB": "def_tackles_solo",
    "MLB": "def_tackles_solo",
    "SLB": "def_tackles_solo",
    "WLB": "def_tackles_solo",
    "CB": "def_interceptions",
    "FS": "def_tackles_solo",
    "SS": "def_tackles_solo",
    "Nickel": "def_interceptions",
    "Dime": "def_interceptions",
    "DE": "def_sacks",
    "DT": "def_sacks",
    "NT": "def_sacks",
    "DL": "def_sacks",
    "OT": None,
    "G": None,
    "C": None,
    "LS": None,
}

_POS_STATS_CACHE: dict[str, pd.DataFrame] = {}

_RATE_STATS = {
    "def_tackles_solo", "def_interceptions", "def_pass_defended",
    "passing_interceptions", "passing_tds", "passing_yards", "carries",
}

_VOLUME_STAT = {
    "QB": "passing_yards",
    "RB": "carries",
    "FB": "carries",
    "WR": "targets",
    "TE": "targets",
    "K": "fg_att",
    "P": "punt_attempts_season",
}
_VOLUME_MIN = {
    "QB": 1800,
    "RB": 80,
    "FB": 40,
    "WR": 40,
    "TE": 25,
    "K": 15,
    "P": 30,
}

TEAM_MAPPING = {
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

NFL_TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens",
    "Buffalo Bills", "Carolina Panthers", "Chicago Bears",
    "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys",
    "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars",
    "Kansas City Chiefs", "Los Angeles Chargers", "Los Angeles Rams",
    "Las Vegas Raiders", "Miami Dolphins", "Minnesota Vikings",
    "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers",
    "Seattle Seahawks", "San Francisco 49ers", "Tampa Bay Buccaneers",
    "Tennessee Titans", "Washington Commanders"
]

def get_generated_team(team_id):
    team = mongo_db.teams.find_one({"_id": ObjectId(team_id)})
    return team

# print(get_generated_team("69c23dfdd66c10dce78df7b3"))

def fetch_player_historical_stats(player_names):
    response = supabase.table("player_stats").select("*").in_("player_display_name", player_names).gte("season", 2021).execute()
    return pd.DataFrame(response.data)

def fetch_player_return_stats(player_names):
    response = supabase.table("return_stats").select("*").in_("player_display_name", player_names).gte("season", 2021).execute()
    return pd.DataFrame(response.data)

def fetch_player_punt_stats(player_names):
    response = supabase.table("punt_stats").select("*").in_("player_display_name", player_names).gte("season", 2021).execute()
    return pd.DataFrame(response.data)

# print(fetch_player_historical_stats(["Josh Allen", "Justin Herbert"]))

def fetch_team_historical_stats(teams):
    response = supabase.table("team_stats").select("*").in_("team", teams).gte("season", 2021).execute()
    return pd.DataFrame(response.data)

# print(fetch_team_historical_stats(["Buffalo Bills"]))

def fetch_position_stats(position: str) -> pd.DataFrame:
    if position in _POS_STATS_CACHE:
        return _POS_STATS_CACHE[position]
    if position == "RS":
        response = supabase.table("return_stats").select("*").gte("season", 2021).execute()
    elif position == "P":
        response = supabase.table("punt_stats").select("*").gte("season", 2021).execute()
    else:
        response = supabase.table("player_stats").select("*").eq("position", position).gte("season", 2021).execute()
    df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
    _POS_STATS_CACHE[position] = df
    return df

_LB_ALIASES = {"LB", "OLB", "ILB", "MLB", "SLB", "WLB"}

_POS_STAT_CAPS = {
    "WR": {"carries": 0.25, "rushing_yards": 3.0, "rushing_tds": 0.04},
    "TE": {},
    "QB": {"rushing_tds": 0.5, "passing_interceptions": 1.0},
    "RB": {"rushing_tds": 1.2, "receiving_tds": 0.5},
    "DE": {"def_sacks": 0.88, "def_tackles_solo": 3.2, "def_pass_defended": 0.35},
    "DT": {"def_sacks": 0.47, "def_tackles_solo": 2.6, "def_pass_defended": 0.24},
    "NT": {"def_sacks": 0.29, "def_tackles_solo": 2.4, "def_pass_defended": 0.18},
    "DL": {"def_sacks": 0.59, "def_tackles_solo": 2.9, "def_pass_defended": 0.29},
    "LB": {"def_tackles_solo": 6.5, "def_sacks": 0.29, "def_interceptions": 0.18, "def_pass_defended": 0.47},
    "OLB": {"def_tackles_solo": 4.7, "def_sacks": 0.47, "def_interceptions": 0.12, "def_pass_defended": 0.35},
    "ILB": {"def_tackles_solo": 6.5, "def_sacks": 0.24, "def_interceptions": 0.18, "def_pass_defended": 0.41},
    "MLB": {"def_tackles_solo": 7.1, "def_sacks": 0.18, "def_interceptions": 0.18, "def_pass_defended": 0.41},
    "SLB": {"def_tackles_solo": 5.3, "def_sacks": 0.35, "def_interceptions": 0.15, "def_pass_defended": 0.41},
    "WLB": {"def_tackles_solo": 5.3, "def_sacks": 0.29, "def_interceptions": 0.15, "def_pass_defended": 0.41},
    "CB": {"def_tackles_solo": 4.1, "def_interceptions": 0.29, "def_pass_defended": 0.94},
    "FS": {"def_tackles_solo": 4.7, "def_interceptions": 0.35, "def_pass_defended": 0.71},
    "SS": {"def_tackles_solo": 4.7, "def_interceptions": 0.24, "def_pass_defended": 0.59},
    "S": {"def_tackles_solo": 4.7, "def_interceptions": 0.35, "def_pass_defended": 0.71},
    "SAF": {"def_tackles_solo": 4.7, "def_interceptions": 0.35, "def_pass_defended": 0.71},
    "Nickel": {"def_tackles_solo": 4.1, "def_interceptions": 0.29, "def_pass_defended": 0.94},
    "Dime": {"def_tackles_solo": 3.5, "def_interceptions": 0.24, "def_pass_defended": 0.82},
    "K": {"fg_made": 1.6, "fg_att": 2.0},
    "RS": {"kickoff_return_yards": 550, "kickoff_returns": 30, "punt_return_yards": 400, "punt_returns": 35},
}

def get_position_dist(all_stats_df: pd.DataFrame, position: str, stat: str) -> tuple[float, float]:
    def _compute(df: pd.DataFrame) -> tuple[float, float] | None:
        if df.empty or stat not in df.columns:
            return None
        if position in ("RS", "P"):
            pos_df = df
        elif position in _LB_ALIASES and "position" in df.columns:
            pos_df = df[df["position"].isin(_LB_ALIASES)]
        else:
            pos_df = df[df["position"] == position] if "position" in df.columns else df
        if pos_df.empty:
            return None
        group_cols = [c for c in ["player_display_name", "season"] if c in pos_df.columns]
        if group_cols:
            extra_cols = [c for c in ["kickoff_returns", "punt_returns", "fg_att"] if c in pos_df.columns and c != stat]
            agg_cols = list(dict.fromkeys([stat] + extra_cols))
            pos_df = pos_df.groupby(group_cols)[agg_cols].sum().reset_index()
        if position == "RS":
            kr_col = "kickoff_returns" if "kickoff_returns" in pos_df.columns else None
            pr_col = "punt_returns" if "punt_returns" in pos_df.columns else None
            if kr_col and pr_col:
                kr = pd.to_numeric(pos_df[kr_col], errors="coerce").fillna(0)
                pr = pd.to_numeric(pos_df[pr_col], errors="coerce").fillna(0)
                pos_df = pos_df[(kr >= 10) | (pr >= 10)]
            elif kr_col:
                pos_df = pos_df[pd.to_numeric(pos_df[kr_col], errors="coerce").fillna(0) >= 10]
            elif pr_col:
                pos_df = pos_df[pd.to_numeric(pos_df[pr_col], errors="coerce").fillna(0) >= 10]
        if position == "K" and "fg_att" in pos_df.columns:
            fg_att_vals = pd.to_numeric(pos_df["fg_att"], errors="coerce").fillna(0)
            pos_df = pos_df[fg_att_vals >= 15]
        values = pd.to_numeric(pos_df[stat], errors="coerce").dropna()
        if stat not in _RATE_STATS:
            values = values[values > 0]
        if len(values) < 5:
            return None
        return float(values.mean()), float(values.std()) if len(values) > 1 else float(values.mean() * 0.3)

    result = _compute(all_stats_df)
    if result is None:
        pos_df = fetch_position_stats("LB" if position in _LB_ALIASES else position)
        result = _compute(pos_df)
    if result is None and position == "SS":
        s_df = fetch_position_stats("S")
        if not s_df.empty and stat in s_df.columns:
            group_cols = [c for c in ["player_display_name", "season"] if c in s_df.columns]
            grouped = s_df.groupby(group_cols)[stat].sum().reset_index() if group_cols else s_df
            values = pd.to_numeric(grouped[stat], errors="coerce").dropna()
            values = values[values > 0]
            if len(values) >= 5:
                result = (float(values.mean()), min(float(values.std()), float(values.mean()) * 0.5))
    if result is None:
        cap = _POS_STAT_CAPS.get(position, {}).get(stat)
        if cap is not None:
            season_equiv = cap * N_GAMES
            return (season_equiv, season_equiv * 0.4)
        return (0.0, 0.01)
    mean_v, std_v = result
    std_v = min(std_v, max(mean_v * 0.5, 0.01))
    return (mean_v, std_v)


DEPTH_VOLUME_STATS = {
    "carries", "rushing_yards", "rushing_tds",
    "receptions", "targets", "receiving_yards", "receiving_tds",
    "fg_made", "fg_att",
    "kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards",
    "punt_attempts_season", "punt_yards_season",
    "def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended",
}

DEPTH_SLOT_SCALE = {1: 1.0, 2: 0.50, 3: 0.30}

SEASON_TOTAL_STATS = {
    "fg_made", "fg_att",
    "kickoff_returns", "kickoff_return_yards",
    "punt_returns", "punt_return_yards",
}
N_GAMES = 17

SYNTHETIC_STATS = {"punt_attempts_season", "punt_yards_season"}

def make_truncnorm(mean: float, std: float, b: float = 5.0):
    # custom truncnorm to prevent inflation of statistics. result dist true mean matches intended mean
    std = max(std, 0.01)
    loc = mean
    for _ in range(4):
        a = (0 - loc) / std
        phi_a, phi_b = norm.pdf(a), norm.pdf(b)
        Phi_a, Phi_b = norm.cdf(a), norm.cdf(b)
        denom = max(Phi_b - Phi_a, 1e-6)
        offset = std * (phi_a - phi_b) / denom
        loc = mean - offset
    a = (0 - loc) / std
    return stats.truncnorm(a=a, b=b, loc=loc, scale=std)

def build_player_distributions(player_stats, player_name, player_pos, depth_slot=1):
    stat_cols = POS_STAT_MAPPING.get(player_pos, [])
    if not stat_cols:
        return {}

    _PLAYMAKING_STATS = {"def_sacks", "def_interceptions", "def_pass_defended"}
    _UNPROVEN_PLAYMAKING_CUT = 0.45

    if "player_display_name" not in player_stats.columns:
        player_data = pd.DataFrame()
    else:
        player_data = player_stats[player_stats["player_display_name"] == player_name].copy()

    is_unproven = player_data.empty

    vol_stat = _VOLUME_STAT.get(player_pos)

    if not is_unproven and vol_stat and vol_stat in player_data.columns and "season" in player_data.columns:
        season_totals = player_data.groupby("season")[vol_stat].sum()
        best_season = season_totals.max() if not season_totals.empty else 0
        if best_season < _VOLUME_MIN.get(player_pos, 0):
            player_data = pd.DataFrame()
            is_unproven = True

    if player_pos in ("RS", "P", "K") and not player_data.empty and "season" in player_data.columns:
        agg_cols = [c for c in stat_cols if c in player_data.columns]
        if agg_cols:
            player_data = player_data.groupby("season")[agg_cols].sum().reset_index()

    distributions = {}
    vol_scale = DEPTH_SLOT_SCALE.get(depth_slot, DEPTH_SLOT_SCALE[2])

    for sc in stat_cols:
        if player_data.empty or sc not in player_data.columns:
            pos_mean, pos_std = get_position_dist(player_stats, player_pos, sc)
            if is_unproven and sc in _PLAYMAKING_STATS:
                pos_mean *= _UNPROVEN_PLAYMAKING_CUT
                pos_std *= _UNPROVEN_PLAYMAKING_CUT
            season_mean = max(0.0, float(np.random.normal(pos_mean, pos_std)))
            if sc in SEASON_TOTAL_STATS or sc in SYNTHETIC_STATS:
                mean = season_mean
                std = max(pos_std, 0.01)
            else:
                mean = season_mean / N_GAMES
                std = max(pos_std / N_GAMES, 0.01)

        else:
            print(f"DEBUG {player_name} {sc}: raw values={player_data[sc].tolist() if sc in player_data.columns else 'MISSING'}")
            values = pd.to_numeric(player_data[sc], errors="coerce").dropna()
            if values.empty or (sc not in _RATE_STATS and (values == 0).all()):
                pos_mean, pos_std = get_position_dist(player_stats, player_pos, sc)
                if is_unproven and sc in _PLAYMAKING_STATS:
                    pos_mean *= _UNPROVEN_PLAYMAKING_CUT
                    pos_std *= _UNPROVEN_PLAYMAKING_CUT
                season_mean = max(0.0, float(np.random.normal(pos_mean, pos_std)))
                if sc in SEASON_TOTAL_STATS or sc in SYNTHETIC_STATS:
                    mean = season_mean
                    std = max(pos_std, 0.01)
                else:
                    mean = season_mean / N_GAMES
                    std = max(pos_std / N_GAMES, 0.01)
            else:
                mean = float(values.mean())
                pos_mean, pos_std = get_position_dist(player_stats, player_pos, sc)
                if len(values) > 1:
                    std = float(values.std())
                else:
                    std = max(mean * 0.30, pos_std)

        if depth_slot > 1 and sc in DEPTH_VOLUME_STATS:
            mean = mean * vol_scale
            std = std * vol_scale

        pos_caps = _POS_STAT_CAPS.get(player_pos, {})
        if sc in pos_caps:
            if sc in SEASON_TOTAL_STATS:
                mean = min(mean, pos_caps[sc] * N_GAMES)
            else:
                mean = min(mean, pos_caps[sc])

        std = max(std, 0.01)
        print(f"DEBUG final {player_name} {sc}: mean={mean:.3f} std={std:.3f} cap={pos_caps.get(sc)} depth_slot={depth_slot}")
        distribution = make_truncnorm(mean, std)
        distributions[sc] = distribution

    return distributions

def build_all_player_dists(team, player_stats, return_stats=None, punt_stats=None):
    result = {}
    pos_slot_counter = {}
    for player in team["players"]:
        name = player["name"]
        position = player["position"]
        pos_slot_counter[position] = pos_slot_counter.get(position, 0) + 1
        depth_slot = pos_slot_counter[position]
        if position == "RS" and return_stats is not None:
            stats_df = return_stats
        elif position == "P" and punt_stats is not None:
            stats_df = punt_stats
        else:
            stats_df = player_stats
        dists = build_player_distributions(stats_df, name, position, depth_slot=depth_slot)
        result[name] = {
            "position": position,
            "depth_slot": depth_slot,
            "distributions": dists
        }

    return result

def build_pos_correlation_mat(team_players):
    n = len(team_players)
    corr = np.eye(n)
    offense_pos = {"QB", "RB", "WR", "TE"}
    defense_pos = {"LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "FS", "SS", "Nickel", "Dime", "DE", "DT", "NT"}
    ol_pos = {"OT", "G", "C", "LS"}

    for i, p1 in enumerate(team_players):
        for j, p2 in enumerate(team_players):
            if i == j:
                continue
                
            pos1, pos2 = p1["position"], p2["position"]

            if pos1 == "QB" and pos2 in ["WR", "TE"]:
                corr[i][j] = 0.6
            elif pos1 == "QB" and pos2 == "RB":
                corr[i][j] = 0.3
            elif pos1 in ["WR", "TE"] and pos2 in ["WR", "TE"]:
                corr[i][j] = 0.35
            elif pos1 in defense_pos and pos2 in defense_pos:
                corr[i][j] = 0.3
            elif pos1 in offense_pos and pos2 in defense_pos:
                corr[i][j] = -0.1

            elif pos1 == "K" and pos2 in offense_pos:
                corr[i][j] = 0.35
            elif pos1 == "K" and pos2 == "RS":
                corr[i][j] = 0.2 
            elif pos1 == "K" and pos2 in defense_pos:
                corr[i][j] = 0.15 

            elif pos1 == "P" and pos2 in offense_pos:
                corr[i][j] = -0.3
            elif pos1 == "P" and pos2 in defense_pos:
                corr[i][j] = 0.2   
            elif pos1 == "P" and pos2 == "K":
                corr[i][j] = -0.2  

            elif pos1 == "RS" and pos2 in offense_pos:
                corr[i][j] = 0.1
            elif pos1 in ol_pos or pos2 in ol_pos:
                corr[i][j] = 0.05
            else:
                corr[i][j] = 0.05
    
    off_diag = corr.copy()
    np.fill_diagonal(off_diag, 0)
    assert np.max(off_diag) < 1.0, "off-diagonal 1.0 detected"

    return corr

def build_corr_matrix(team_players):
    return build_pos_correlation_mat(team_players)

def build_flat_corr(distributions, corr_mat):
    flat_keys = []
    for name, data in distributions.items():
        for sc in data["distributions"].keys():
            flat_keys.append((name, sc))

    if not flat_keys:
        return flat_keys, None

    n = len(flat_keys)
    names = list(distributions.keys())
    name_to_idx = {name: i for i, name in enumerate(names)}

    if corr_mat.shape[0] != len(names):
        corr_mat = np.eye(len(names))

    flat_corr = np.eye(n)
    for i, (p1, _) in enumerate(flat_keys):
        for j, (p2, _) in enumerate(flat_keys):
            if i == j:
                continue
            pi = name_to_idx[p1]
            pj = name_to_idx[p2]
            flat_corr[i][j] = 0.7 if p1 == p2 else corr_mat[pi][pj] * 0.8

    flat_corr = np.clip(np.nan_to_num(flat_corr, nan=0.0, posinf=1.0, neginf=-1.0), -1.0, 1.0)
    np.fill_diagonal(flat_corr, 1.0)

    # ensure positive semidefinite - done once, not per game
    eigenvalues, eigenvectors = np.linalg.eigh(flat_corr)
    eigenvalues = np.maximum(eigenvalues, 1e-6)
    flat_corr = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
    print(f"DEBUG flat_corr: has_nan={np.isnan(flat_corr).any()} has_inf={np.isinf(flat_corr).any()} min={np.nanmin(flat_corr):.3f} max={np.nanmax(flat_corr):.3f}")

    if not np.all(np.isfinite(flat_corr)):
        flat_corr = np.eye(n)

    return flat_keys, flat_corr

def fetch_tabsyn_sample() -> dict:
    """Call the TabSyn inference microservice and return one generated team-season row."""
    tabsyn_url = os.getenv("TABSYN_URL", "http://localhost:8002")
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{tabsyn_url}/generate", json={"n_samples": 1})
            resp.raise_for_status()
            return resp.json()["samples"][0]
    except Exception:
        return {}


_TABSYN_STAT_MAP = {
    "qb_passing_yards": ("QB", 1, "passing_yards"),
    "qb_passing_tds": ("QB", 1, "passing_tds"),
    "qb_interceptions": ("QB", 1, "passing_interceptions"),
    "qb_carries": ("QB", 1, "carries"),
    "qb_rushing_yards": ("QB", 1, "rushing_yards"),
    "qb_rushing_tds": ("QB", 1, "rushing_tds"),
    "wr1_targets": ("WR", 1, "targets"),
    "wr1_receptions": ("WR", 1, "receptions"),
    "wr1_receiving_yards":("WR", 1, "receiving_yards"),
    "wr1_receiving_tds": ("WR", 1, "receiving_tds"),
    "wr2_targets": ("WR", 2, "targets"),
    "wr2_receptions": ("WR", 2, "receptions"),
    "wr2_receiving_yards": ("WR", 2, "receiving_yards"),
    "wr2_receiving_tds": ("WR", 2, "receiving_tds"),
    "wr3_targets": ("WR", 3, "targets"),
    "wr3_receptions": ("WR", 3, "receptions"),
    "wr3_receiving_yards": ("WR", 3, "receiving_yards"),
    "wr3_receiving_tds": ("WR", 3, "receiving_tds"),
    "rb1_carries": ("RB", 1, "carries"),
    "rb1_rushing_yards": ("RB", 1, "rushing_yards"),
    "rb1_rushing_tds": ("RB", 1, "rushing_tds"),
    "rb1_receptions":("RB", 1, "receptions"),
    "rb1_receiving_yards": ("RB", 1, "receiving_yards"),
    "rb1_receiving_tds": ("RB", 1, "receiving_tds"),
    "rb2_carries": ("RB", 2, "carries"),
    "rb2_rushing_yards": ("RB", 2, "rushing_yards"),
    "rb2_rushing_tds": ("RB", 2, "rushing_tds"),
    "rb2_receptions": ("RB", 2, "receptions"),
    "rb2_receiving_yards": ("RB", 2, "receiving_yards"),
    "rb2_receiving_tds": ("RB", 2, "receiving_tds"),
    "te1_targets": ("TE", 1, "targets"),
    "te1_receptions": ("TE", 1, "receptions"),
    "te1_receiving_yards": ("TE", 1, "receiving_yards"),
    "te1_receiving_tds": ("TE", 1, "receiving_tds"),
    "te2_targets": ("TE", 2, "targets"),
    "te2_receptions": ("TE", 2, "receptions"),
    "te2_receiving_yards": ("TE", 2, "receiving_yards"),
    "te2_receiving_tds": ("TE", 2, "receiving_tds"),
    "k_fg_made": ("K", 1, "fg_made"),
    "k_fg_att": ("K", 1, "fg_att"),
    "edge1_sacks": ("DE", 1, "def_sacks"),
    "edge1_tackles": ("DE", 1, "def_tackles_solo"),
    "edge1_pass_defended": ("DE", 1, "def_pass_defended"),
    "edge2_sacks": ("DE", 2, "def_sacks"),
    "edge2_tackles": ("DE", 2, "def_tackles_solo"),
    "edge2_pass_defended": ("DE", 2, "def_pass_defended"),
    "dt1_tackles": ("DT", 1, "def_tackles_solo"),
    "dt1_sacks": ("DT", 1, "def_sacks"),
    "dt1_pass_defended": ("DT", 1, "def_pass_defended"),
    "dt2_tackles": ("DT", 2, "def_tackles_solo"),
    "dt2_sacks": ("DT", 2, "def_sacks"),
    "dt2_pass_defended": ("DT", 2, "def_pass_defended"),
    "lb1_tackles": ("LB", 1, "def_tackles_solo"),
    "lb1_sacks": ("LB", 1, "def_sacks"),
    "lb1_interceptions": ("LB", 1, "def_interceptions"),
    "lb1_pass_defended": ("LB", 1, "def_pass_defended"),
    "lb2_tackles": ("LB", 2, "def_tackles_solo"),
    "lb2_sacks": ("LB", 2, "def_sacks"),
    "lb2_interceptions": ("LB", 2, "def_interceptions"),
    "lb2_pass_defended": ("LB", 2, "def_pass_defended"),
    "cb1_interceptions": ("CB", 1, "def_interceptions"),
    "cb1_pass_defended": ("CB", 1, "def_pass_defended"),
    "cb1_tackles": ("CB", 1, "def_tackles_solo"),
    "cb2_interceptions": ("CB", 2, "def_interceptions"),
    "cb2_pass_defended": ("CB", 2, "def_pass_defended"),
    "cb2_tackles": ("CB", 2, "def_tackles_solo"),
    "s1_tackles": ("FS", 1, "def_tackles_solo"),
    "s1_interceptions": ("FS", 1, "def_interceptions"),
    "s1_pass_defended": ("FS", 1, "def_pass_defended"),
}

_POS_ALIASES = {
    "DE": ["DE"],
    "DT": ["DT", "NT", "DL"],
    "LB": ["LB", "ILB", "MLB", "OLB", "SLB", "WLB"],
    "CB": ["CB", "Nickel", "Dime"],
    "FS": ["FS", "SS", "S", "SAF"],
}


def apply_tabsyn_priors(distributions: dict, tabsyn_row: dict) -> dict:
    """
    Override each player's distribution means with TabSyn season totals.
    Keeps the historical STD so variance is preserved; only the center shifts.
    Players are matched by position + depth slot order.
    """
    if not tabsyn_row:
        return distributions

    pos_slot_names: dict[tuple, str] = {}
    pos_counter: dict[str, int] = {}
    for name, data in distributions.items():
        pos = data["position"]
        pos_counter[pos] = pos_counter.get(pos, 0) + 1
        pos_slot_names[(pos, pos_counter[pos])] = name

    for wide_col, (pos, slot, stat) in _TABSYN_STAT_MAP.items():
        if wide_col not in tabsyn_row:
            continue
        aliases = _POS_ALIASES.get(pos, [pos])
        player_name = None
        for alias_pos in aliases:
            player_name = pos_slot_names.get((alias_pos, slot))
            if player_name is not None:
                break
        if player_name is None:
            continue
        player_dists = distributions[player_name]["distributions"]
        if stat not in player_dists:
            continue

        _SEASON_CAPS = {
            "passing_interceptions": 20, "passing_tds": 55,
            "rushing_tds": 15, "receiving_tds": 20,
            "fg_made": 40, "fg_att": 50,
        }
        _STD_CAPS = {
            "passing_yards": 80, "passing_tds": 2.5, "passing_interceptions": 1.0,
            "rushing_yards": 40, "rushing_tds": 0.5, "carries": 8,
            "receiving_yards": 40, "receiving_tds": 0.4, "receptions": 4, "targets": 5,
            "def_sacks": 0.5, "def_tackles_solo": 3, "def_interceptions": 0.3,
            "def_pass_defended": 0.5, "fg_made": 2, "fg_att": 3,
        }
        season_val = min(float(tabsyn_row[wide_col]), _SEASON_CAPS.get(stat, 99999))
        tabsyn_mean = season_val if stat in SEASON_TOTAL_STATS or stat in SYNTHETIC_STATS else season_val / N_GAMES
        print(f"DEBUG tabsyn override: {player_name} {stat}: tabsyn_row[{wide_col}]={tabsyn_row[wide_col]} -> tabsyn_mean={tabsyn_mean:.3f}")
        old_dist = player_dists[stat]
        old_std = old_dist.args[3] if hasattr(old_dist, "args") and len(old_dist.args) >= 4 else old_dist.kwds.get("scale", 1.0)
        old_std = float(np.clip(old_std, 0.01, _STD_CAPS.get(stat, 999)))
        a = -tabsyn_mean / old_std
        player_dists[stat] = stats.truncnorm(a=a, b=5, loc=tabsyn_mean, scale=old_std)

    return distributions


def sample_all_games(distributions, flat_keys, flat_corr, n_season_sims, n_games):
    n = len(flat_keys)
    total_samples = n_season_sims * n_games
    mv_samples = np.random.multivariate_normal(np.zeros(n), flat_corr, size=total_samples)
    uniform_samples = norm.cdf(mv_samples)

    raw = np.zeros((total_samples, n))
    for i, (name, sc) in enumerate(flat_keys):
        dist = distributions[name]["distributions"][sc]
        raw[:, i] = dist.ppf(np.clip(uniform_samples[:, i], 1e-6, 1 - 1e-6))

    return raw.reshape(n_season_sims, n_games, n)

def yards_to_points(passing_yards, rushing_yards, fg_made):
    return (passing_yards + rushing_yards) / 17.0 + fg_made * 3

_TALENT_BASELINES = {
    "QB":  {"passing_yards": 230.0, "rushing_yards": 15.0},
    "RB":  {"rushing_yards": 55.0, "receiving_yards": 20.0},
    "FB":  {"rushing_yards": 15.0, "receiving_yards": 10.0},
    "WR":  {"receiving_yards": 55.0},
    "TE":  {"receiving_yards": 35.0},
}

_TALENT_WEIGHTS = {"QB": 0.34, "RB": 0.22, "FB": 0.04, "WR": 0.28, "TE": 0.12}


def compute_offense_talent(distributions):
    """
    Roster-wide offensive talent index (~0.80 weak .. ~1.20 elite, centered on 1.0).
    Distinguishes equipped rosters from backup-heavy ones by comparing each skill
    player's projected per-game production against NFL positional baselines.
    Depth players count less (their volume is already scaled down in distributions).
    """
    group_scores: dict[str, list[float]] = {}
    for name, data in distributions.items():
        pos = data.get("position", "")
        base = _TALENT_BASELINES.get(pos)
        if not base:
            continue
        dist_map = data.get("distributions", {})
        ratios = []
        for stat, baseline in base.items():
            dist = dist_map.get(stat)
            if dist is not None and baseline > 0:
                ratios.append(dist.mean() / baseline)
        if ratios:
            group_scores.setdefault(pos, []).append(float(np.mean(ratios)))

    if not group_scores:
        return 1.0

    total_w = 0.0
    weighted = 0.0
    for pos, scores in group_scores.items():
        w = _TALENT_WEIGHTS.get(pos, 0.0)
        if w <= 0:
            continue
        scores_sorted = sorted(scores, reverse=True)
        starter = scores_sorted[0]
        depth = float(np.mean(scores_sorted[1:])) if len(scores_sorted) > 1 else starter
        group_val = 0.75 * starter + 0.25 * depth
        weighted += w * group_val
        total_w += w

    if total_w <= 0:
        return 1.0
    raw = weighted / total_w
    index = 1.0 + (raw - 1.0) * 0.55
    return float(np.clip(index, 0.80, 1.18))


def compute_kicker_reliability(distributions):
    """
    Penalty-only kicker factor in (0.94 .. 1.0]. A poor FG% shaves team points
    (missed kicks cost games); a good FG% is neutral (never boosts scoring).
    """
    best_pct = None
    for data in distributions.values():
        if data.get("position") != "K":
            continue
        dist_map = data.get("distributions", {})
        made = dist_map.get("fg_made")
        att = dist_map.get("fg_att")
        if made is not None and att is not None and att.mean() > 0:
            pct = made.mean() / att.mean()
            if best_pct is None or pct > best_pct:
                best_pct = pct
    if best_pct is None:
        return 1.0
    if best_pct >= 0.84:
        return 1.0
    penalty = 1.0 - (0.84 - min(best_pct, 0.84)) * 0.6
    return float(np.clip(penalty, 0.94, 1.0))

def generate_schedule(n_games=17):
    opponents = random.sample(NFL_TEAMS, min(n_games, len(NFL_TEAMS)))
    return [
        {"week": week, "opponent": opp, "home": random.choice([True, False])}
        for week, opp in enumerate(opponents, 1)
    ]

def get_opponent_strength(opponent, team_stats):
    opp_data = team_stats[team_stats["team"] == opponent]
    if opp_data.empty:
        return 1.0

    avg_passing = opp_data["passing_yards"].mean()
    avg_rushing = opp_data["rushing_yards"].mean()

    passing_factor = max(avg_passing, 1) / 230
    rushing_factor = max(avg_rushing, 1) / 115
    strength = (passing_factor + rushing_factor) / 2
    return float(np.clip(strength, 0.8, 1.25))
    
OL_POSITIONS = {"OT", "G", "C", "OL"}

def compute_ol_multiplier(team_players):
    ol_count = sum(1 for p in team_players if p["position"] in OL_POSITIONS)
    raw = 1.0 - max(0, (5 - ol_count)) * 0.07
    return float(np.clip(raw, 0.72, 1.0))

def sim_season(team, distributions, corr_matrix, team_stats, n_season_sims=300, coach_multiplier=1.0, ol_multiplier=1.0):
    n_games = 17
    schedule = generate_schedule(n_games)

    all_player_stats = {
        p["name"]: {stat: [] for stat in distributions[p["name"]]["distributions"].keys()}
        for p in team["players"]
        if distributions[p["name"]]["distributions"]
    }

    flat_keys, flat_corr = build_flat_corr(distributions, corr_matrix)
    if flat_corr is None:
        return {}

    all_samples = sample_all_games(distributions, flat_keys, flat_corr, n_season_sims, n_games)
    all_samples = np.maximum(all_samples, 0)

    key_to_idx = {key: i for i, key in enumerate(flat_keys)}

    for name in all_player_stats:
        rec_idx = key_to_idx.get((name, "receptions"))
        tgt_idx = key_to_idx.get((name, "targets"))
        if rec_idx is not None and tgt_idx is not None:
            all_samples[:, :, rec_idx] = np.minimum(
                all_samples[:, :, rec_idx], all_samples[:, :, tgt_idx]
            )
        car_idx = key_to_idx.get((name, "carries"))
        ryd_idx = key_to_idx.get((name, "rushing_yards"))
        rtd_idx = key_to_idx.get((name, "rushing_tds"))
        pos = distributions[name]["position"]
        if pos in ("WR", "TE") and car_idx is not None:
            no_carry = all_samples[:, :, car_idx] < 0.5
            if ryd_idx is not None:
                all_samples[:, :, ryd_idx] = np.where(no_carry, 0.0, all_samples[:, :, ryd_idx])
            if rtd_idx is not None:
                all_samples[:, :, rtd_idx] = np.where(no_carry, 0.0, all_samples[:, :, rtd_idx])
    stat_col_indices = {name: {} for name in all_player_stats}
    for name in all_player_stats:
        for stat in all_player_stats[name]:
            k = (name, stat)
            if k in key_to_idx:
                stat_col_indices[name][stat] = key_to_idx[k]

    opp_strengths = np.array([get_opponent_strength(g["opponent"], team_stats) for g in schedule])

    _QB_POSITIONS = {"QB"}
    _RB_POSITIONS = {"RB", "FB"}
    passing_indices = [key_to_idx[k] for k in flat_keys if k[1] == "passing_yards" and distributions[k[0]]["position"] in _QB_POSITIONS]
    rushing_indices = [key_to_idx[k] for k in flat_keys if k[1] == "rushing_yards" and distributions[k[0]]["position"] in _RB_POSITIONS]
    fg_indices = [key_to_idx[k] for k in flat_keys if k[1] == "fg_made"]

    home_away = np.where(np.array([g["home"] for g in schedule]), 1.05, 0.97)

    passing_per_game = np.sum(all_samples[:, :, passing_indices], axis=2) if passing_indices else np.zeros((n_season_sims, n_games))
    rushing_per_game = np.sum(all_samples[:, :, rushing_indices], axis=2) if rushing_indices else np.zeros((n_season_sims, n_games))
    fg_per_game = (np.sum(all_samples[:, :, fg_indices], axis=2) / N_GAMES) if fg_indices else np.zeros((n_season_sims, n_games))
    offense_talent = compute_offense_talent(distributions)
    offense_talent_dampened = 1.0 + (offense_talent - 1.0) * 0.6
    kicker_reliability = compute_kicker_reliability(distributions)
    team_score_mult = home_away * coach_multiplier * offense_talent_dampened * kicker_reliability
    team_points = yards_to_points(passing_per_game * team_score_mult, rushing_per_game * team_score_mult, fg_per_game)

    print(f"DEBUG scoring: offense_talent={offense_talent:.3f} kicker_reliability={kicker_reliability:.3f} coach_multiplier={coach_multiplier:.3f}")
    print(f"DEBUG scoring: home_away mean={home_away.mean():.4f}")
    print(f"DEBUG scoring: passing_per_game mean={passing_per_game.mean():.2f} rushing_per_game mean={rushing_per_game.mean():.2f} fg_per_game mean={fg_per_game.mean():.2f}")
    print(f"DEBUG scoring: team_score_mult mean={team_score_mult.mean():.3f}")
    print(f"DEBUG scoring: team_points mean={team_points.mean():.2f}")

    DEF_POSITIONS = {"DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "FS", "SS", "S", "SAF", "DB", "Nickel", "Dime"}
    def_sack_mean = 0.0
    def_tackle_mean = 0.0
    def_int_mean = 0.0
    def_count = 0
    for name in all_player_stats:
        pos = distributions[name].get("position", "")
        if pos in DEF_POSITIONS:
            dist_map = distributions[name].get("distributions", {})
            if "def_sacks" in dist_map:
                def_sack_mean += dist_map["def_sacks"].mean()
            if "def_tackles_solo" in dist_map:
                def_tackle_mean += dist_map["def_tackles_solo"].mean()
            if "def_interceptions" in dist_map:
                def_int_mean += dist_map["def_interceptions"].mean()
            def_count += 1

    sack_score = np.clip(def_sack_mean / 2.2, 0.7, 1.4)
    tackle_score = np.clip(def_tackle_mean / 33.0, 0.7, 1.4)
    turnover_score = np.clip(def_int_mean / 0.7, 0.7, 1.5)
    def_quality = float(np.clip(
        0.30 * sack_score + 0.25 * tackle_score + 0.45 * turnover_score,
        0.85, 1.22
    ))

    NFL_AVG_PTS = 23.0
    def_quality_dampened = 1.0 + (def_quality - 1.0) * 0.6
    ball_control_factor = float(np.clip(1.0 - (offense_talent - 1.0) * 0.15, 0.92, 1.05))
    opp_base = (NFL_AVG_PTS * opp_strengths) / def_quality_dampened * ball_control_factor
    opp_points = np.random.normal(
        loc=opp_base,
        scale=7.0,
        size=(n_season_sims, n_games)
    )

    takeaway_edge = np.clip(turnover_score - 1.0, 0.0, 0.5)
    wins_matrix = (team_points > opp_points)
    margin = team_points - opp_points
    close_loss = (margin <= 0) & (margin > -10.0)
    baseline_upset_chance = 0.08
    flip_prob = np.clip(takeaway_edge * 0.5 + baseline_upset_chance, 0.0, 0.6)
    flip = close_loss & (np.random.random(margin.shape) < flip_prob)

    if np.any(flip):
        turnover_swing = np.abs(margin) + np.random.uniform(1.0, 4.0, size=margin.shape)
        opp_points = np.where(flip, np.maximum(opp_points - turnover_swing, 0.0), opp_points)

    wins_matrix = (team_points > opp_points)
    all_szn_wins = wins_matrix.sum(axis=1)
    season_win_rate = all_szn_wins / n_games
    def_stat_scale = np.clip(0.85 + 0.3 * (season_win_rate - 0.5), 0.75, 1.25)
    def_stat_scale = def_stat_scale.reshape(-1, 1)

    _OL_BOOSTED_STATS = {"rushing_yards", "carries", "rushing_tds", "passing_yards", "passing_tds"}
    _OL_HURT_STATS = {"passing_interceptions"}
    _OL_AFFECTED_POS = {"RB", "FB", "QB", "WR", "TE"}
    _DEF_PLAYMAKING_STATS = {"def_sacks", "def_interceptions", "def_pass_defended"}
    _SEASON_STAT_CEILINGS = {
        "def_interceptions": {"LB": 5, "CB": 8, "FS": 8, "SS": 7, "S": 8, "DE": 2, "DT": 1},
        "def_sacks": {"DE": 17, "DT": 12, "NT": 8, "DL": 14, "LB": 12, "CB": 3, "FS": 2, "SS": 2, "S": 2},
        "def_pass_defended": {"CB": 22, "FS": 15, "SS": 14, "S": 15, "LB": 14, "DE": 6, "DT": 4},
    }

    for name in all_player_stats:
        pos = distributions[name]["position"]
        for stat, col_idx in stat_col_indices[name].items():
            if stat in SYNTHETIC_STATS or stat in SEASON_TOTAL_STATS:
                season_totals = all_samples[:, :, col_idx].mean(axis=1)
            else:
                if pos in _OL_AFFECTED_POS:
                    if stat in _OL_BOOSTED_STATS:
                        season_totals = (all_samples[:, :, col_idx] * ol_multiplier).sum(axis=1)
                    elif stat in _OL_HURT_STATS:
                        int_penalty = 1.0 + (1.0 - ol_multiplier) * 1.5
                        season_totals = (all_samples[:, :, col_idx] * int_penalty).sum(axis=1)
                    else:
                        season_totals = all_samples[:, :, col_idx].sum(axis=1)
                elif stat in _DEF_PLAYMAKING_STATS and pos in DEF_POSITIONS:
                    season_totals = (all_samples[:, :, col_idx] * def_stat_scale).sum(axis=1)
                else:
                    season_totals = all_samples[:, :, col_idx].sum(axis=1)
            ceiling = _SEASON_STAT_CEILINGS.get(stat, {}).get(pos)
            if ceiling is not None:
                season_totals = np.minimum(season_totals, ceiling)
            all_player_stats[name][stat] = season_totals.tolist()
    
    wins_array = np.array(all_szn_wins)

    nfl_team_map = {p["name"]: TEAM_MAPPING.get(p["nfl_team"], p["nfl_team"]) for p in team["players"]}

    POS_ORDER = ["QB", "RB", "FB", "WR", "TE", "OT", "G", "C", "DE", "DT", "NT", "DL",
                 "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "Nickel", "Dime", "FS", "SS", "S", "SAF", "DB", "K", "P", "RS", "LS"]

    player_projs_raw = {}
    for name, stats in all_player_stats.items():
        pos = distributions[name]["position"]
        primary_stat = POSITION_PRIMARY_STAT.get(pos)
        primary_arr = np.array(stats.get(primary_stat, [0])) if primary_stat else np.array([0])

        stat_entries = {}
        for stat, v in stats.items():
            arr = np.array(v)
            stat_entries[stat] = {
                "projected_total": round(float(np.mean(arr))),
                "floor": round(float(np.percentile(arr, 10))),
                "ceiling": round(float(np.percentile(arr, 90))),
            }

        if pos == "K" and "fg_made" in stats and "fg_att" in stats:
            made_arr = np.array(stats["fg_made"])
            att_arr = np.array(stats["fg_att"])
            safe_att = np.where(att_arr > 0, att_arr, 1.0)
            pct_arr = (made_arr / safe_att) * 100
            proj_made = stat_entries["fg_made"]["projected_total"]
            proj_att = stat_entries["fg_att"]["projected_total"]
            proj_pct = round((proj_made / proj_att) * 100, 1) if proj_att > 0 else 0.0
            stat_entries["fg_pct"] = {
                "projected_total": proj_pct,
                "floor": round(float(np.percentile(pct_arr, 10)), 1),
                "ceiling": round(float(np.percentile(pct_arr, 90)), 1),
            }

        player_projs_raw[name] = {
            "position": pos,
            "nfl_team": nfl_team_map.get(name, ""),
            "_primary_proj": float(np.mean(primary_arr)),
            "stats": stat_entries,
        }

    sorted_names = sorted(
        player_projs_raw.keys(),
        key=lambda n: (
            POS_ORDER.index(player_projs_raw[n]["position"]) if player_projs_raw[n]["position"] in POS_ORDER else 99,
            -player_projs_raw[n]["_primary_proj"]
        )
    )
    player_projs = [
        {"name": name, **{k: v for k, v in player_projs_raw[name].items() if k != "_primary_proj"}}
        for name in sorted_names
    ]
    
    win_vals = wins_array.astype(float)
    playoff_prob_per_sim = 1 / (1 + np.exp(-0.7 * (win_vals - 9.5)))
    playoff_probability = round(float(np.mean(playoff_prob_per_sim)) * 100, 1)
    avg_wins = float(np.mean(wins_array))
    win_quality = np.clip((avg_wins - 7) / 6, 0.3, 1.5)
    defense_sb_bonus = 1.0 + np.clip(def_quality - 1.0, 0.0, 0.30) * 0.5
    superbowl_probability = round(playoff_probability * (1 / 14) * win_quality * defense_sb_bonus, 1)
    avg_team_points = float(np.mean(team_points.sum(axis=1)))
    avg_opp_points = float(np.mean(opp_points.sum(axis=1)))

    return {
        "schedule": schedule,
        "projected_wins": int(round(float(np.mean(wins_array)))),
        "win_floor": int(np.percentile(wins_array, 10)),
        "win_ceiling": int(np.percentile(wins_array, 90)),
        "playoff_probability": playoff_probability,
        "superbowl_probability": superbowl_probability,
        "player_projections": player_projs,
        "win_distribution": {str(w): int(np.sum(wins_array == w)) for w in range(18)},
        "points_for": round(avg_team_points),
        "points_against": round(avg_opp_points),
        "points_per_game": round(avg_team_points / n_games, 1),
    }

def fetch_coach_factor(coach_name, qb_name):
    """
    Returns a multiplier (0.90-1.10) based on:
    - Coach's historical win rate from schedules (vs NFL average of ~0.5)
    - Bonus if coach has coached this QB on the same team in the same season
    """
    if not coach_name:
        return 1.0, {}

    coach_home = supabase.table("coaches").select("season,team").eq("head_coach", coach_name).execute()

    coach_teams = {row["season"]: row["team"] for row in (coach_home.data or [])}

    if not coach_teams:
        return 1.0, {"coach": coach_name, "note": "No historical data found"}

    wins = 0
    losses = 0
    for season, team in coach_teams.items():
        home_data = supabase.table("schedules").select("home_score,away_score") \
            .eq("season", season).eq("home_team", team).execute()
        for row in (home_data.data or []):
            if row["home_score"] is not None and row["away_score"] is not None:
                if row["home_score"] > row["away_score"]:
                    wins += 1
                elif row["home_score"] < row["away_score"]:
                    losses += 1
        away_data = supabase.table("schedules").select("home_score,away_score") \
            .eq("season", season).eq("away_team", team).execute()
        for row in (away_data.data or []):
            if row["home_score"] is not None and row["away_score"] is not None:
                if row["away_score"] > row["home_score"]:
                    wins += 1
                elif row["away_score"] < row["home_score"]:
                    losses += 1

    total = wins + losses
    win_rate = wins / total if total > 0 else 0.5
    coach_multiplier = 0.88 + (win_rate * 0.24)
    coach_multiplier = float(np.clip(coach_multiplier, 0.90, 1.10))
    
    qb_familiarity = False
    qb_data = supabase.table("player_stats").select("season,team").eq("player_display_name", qb_name).eq("position", "QB").execute()
    qb_seasons = {(row["season"], row["team"]) for row in (qb_data.data or [])}
    for season, team in coach_teams.items():
        if (season, team) in qb_seasons:
            qb_familiarity = True
            break

    if qb_familiarity:
        coach_multiplier = float(np.clip(coach_multiplier + 0.03, 0.90, 1.10))

    latest_season = max(coach_teams.keys())
    latest_team_abbrev = coach_teams[latest_season]
    latest_team_full = TEAM_MAPPING.get(latest_team_abbrev, latest_team_abbrev)

    meta = {
        "coach": coach_name,
        "team": latest_team_full,
        "seasons_coached": len(coach_teams),
        "record": f"{wins}–{losses}",
        "win_rate": round(win_rate, 3),
        "coach_multiplier": round(coach_multiplier, 3),
        "qb_familiarity": qb_familiarity,
    }
    return coach_multiplier, meta

def run_full_analysis(team_id):
    _POS_STATS_CACHE.clear()
    team = get_generated_team(team_id)
    player_names = [p["name"] for p in team["players"]]
    nfl_teams = list(set(TEAM_MAPPING[p["nfl_team"]] for p in team["players"]))

    qb = next((p["name"] for p in team["players"] if p["position"] == "QB"), "")
    coach_name = team.get("head_coach", "")
    coach_multiplier, coach_meta = fetch_coach_factor(coach_name, qb)

    player_stats = fetch_player_historical_stats(player_names)
    return_stats = fetch_player_return_stats(player_names)
    punt_stats = fetch_player_punt_stats(player_names)
    team_stats = fetch_team_historical_stats(nfl_teams)

    dists = build_all_player_dists(team, player_stats, return_stats=return_stats, punt_stats=punt_stats)
    for name, d in dists.items():
        if d["position"] == "K":
            for stat, dist in d["distributions"].items():
                print(f"DEBUG dist {name} {stat}: mean={dist.mean():.3f}")
    tabsyn_row = fetch_tabsyn_sample()
    dists = apply_tabsyn_priors(dists, tabsyn_row)
    corr_matrix = build_corr_matrix(team["players"])

    ol_multiplier = compute_ol_multiplier(team["players"])
    results = sim_season(team, dists, corr_matrix, team_stats, coach_multiplier=coach_multiplier, ol_multiplier=ol_multiplier)
    results["coach_analysis"] = coach_meta

    return results

app = FastAPI()
class AnalyzeRequest(BaseModel):
    team_id: str

@app.post("/analyze-team")
async def analyze_team(request: AnalyzeRequest):
    try:
        results = run_full_analysis(request.team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    go_url = os.getenv("GO_API_URL", "http://localhost:8000")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{go_url}/api/analysis/{request.team_id}",
                json={"team_id": request.team_id, "analysis": results},
            )
    except Exception as e:
        print(f"Warning: failed to cache analysis to Go backend: {e}")

    return results