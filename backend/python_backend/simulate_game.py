from fastapi import FastAPI, HTTPException
from supabase import create_client
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from scipy import stats

import pandas as pd
import numpy as np
import random
import os
import json
import certifi
import httpx

PLAY_CALL_URL = os.getenv("PLAY_CALL_URL", "http://localhost:8003")
OUTCOME_URL = os.getenv("OUTCOME_URL", "http://localhost:8004")
ML_TIMEOUT = 2.0

_DEF_TIERS_PATH = os.path.join(os.path.dirname(__file__), "outcome_model_weights", "outcome_def_tiers.json")
_DEF_TIERS: dict = {}
try:
    with open(_DEF_TIERS_PATH) as _f:
        _DEF_TIERS = json.load(_f)
except FileNotFoundError:
    pass

def _ml_play_call(down: int, ydstogo: float, yardline_100: float,
                  score_diff: float, qtr: int, secs_remaining: float,
                  shotgun: int = 0, goal_to_go: int = 0) -> dict | None:
    try:
        r = httpx.post(f"{PLAY_CALL_URL}/predict", json={"game_state": {
            "down": down, "ydstogo": ydstogo, "yardline_100": yardline_100,
            "score_differential": score_diff, "qtr": qtr,
            "game_seconds_remaining": secs_remaining,
            "shotgun": shotgun, "goal_to_go": goal_to_go,
        }}, timeout=ML_TIMEOUT)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def _ml_outcome(play_type: str, down: int, ydstogo: float, yardline_100: float,
                score_diff: float, qtr: int, shotgun: int = 0, goal_to_go: int = 0,
                air_yards: float = 0.0, kick_distance: float = 0.0,
                def_pass_tier: int = 2, def_rush_tier: int = 2,
                def_sack_tier: int = 2, def_coverage_tier: int = 2) -> dict | None:
    """Returns outcome dict or None on failure."""
    try:
        r = httpx.post(f"{OUTCOME_URL}/predict", json={
            "play_type": play_type, "down": down, "ydstogo": ydstogo,
            "yardline_100": yardline_100, "score_differential": score_diff,
            "qtr": qtr, "shotgun": shotgun, "goal_to_go": goal_to_go,
            "air_yards": air_yards, "kick_distance": kick_distance,
            "def_pass_tier": def_pass_tier, "def_rush_tier": def_rush_tier,
            "def_sack_tier": def_sack_tier, "def_coverage_tier": def_coverage_tier,
        }, timeout=ML_TIMEOUT)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _get_nfl_def_tiers(team: str, season: int) -> dict:
    """Look up pre-computed defensive tiers for an NFL team and season."""
    key = f"{team}|{season}"
    entry = _DEF_TIERS.get(key, {})
    return {
        "def_pass_tier": int(entry.get("def_pass_tier", 2)),
        "def_rush_tier": int(entry.get("def_rush_tier", 2)),
        "def_sack_tier": int(entry.get("def_sack_tier", 2)),
        "def_coverage_tier": int(entry.get("def_coverage_tier", 2)),
    }


def _compute_user_def_tiers(players: list, player_df: pd.DataFrame) -> dict:
    """
    Estimate defensive tiers for the user's generated team from player ratings.
    Uses position group quality scores derived from historical stats.
    (0 = elite, 4 = bad).
    """
    PASS_DEF_POS = {"CB", "FS", "SS", "S", "SAF", "Nickel", "Dime"}
    RUSH_DEF_POS = {"DT", "NT", "DE", "ILB", "MLB", "LB"}
    SACK_POS = {"DE", "DT", "OLB", "NT"}
    COVERAGE_POS = {"CB", "FS", "SS", "S", "SAF", "LB", "OLB", "Nickel", "Dime"}

    def _pos_quality(pos_set: set, stat: str, default: float, good_threshold: float) -> float:
        """Average per-game stat for players in the given positions. Returns 0-1 quality score."""
        scores = []
        for p in players:
            if p["position"] not in pos_set:
                continue
            rows = player_df[player_df["player_display_name"] == p["name"]] if not player_df.empty else pd.DataFrame()
            if rows.empty or stat not in rows.columns:
                scores.append(default)
                continue
            total = pd.to_numeric(rows[stat], errors="coerce").sum()
            games = max(len(rows), 1)
            scores.append(float(total / games))
        if not scores:
            return 0.5
        avg = float(np.mean(scores))
        return float(np.clip(avg / good_threshold, 0.0, 2.0))

    def _quality_to_tier(q: float) -> int:
        if q >= 1.5: return 0
        elif q >= 1.1: return 1
        elif q >= 0.7: return 2
        elif q >= 0.4: return 3
        else: return 4

    pass_q = _pos_quality(PASS_DEF_POS, "def_pass_defended", 0.5, 2.5)
    rush_q = _pos_quality(RUSH_DEF_POS, "def_tackles_solo", 3.0, 6.0)
    sack_q = _pos_quality(SACK_POS, "def_sacks", 0.3, 0.8)
    coverage_q = _pos_quality(COVERAGE_POS, "def_interceptions", 0.1, 0.3)

    return {
        "def_pass_tier": _quality_to_tier(pass_q),
        "def_rush_tier": _quality_to_tier(rush_q),
        "def_sack_tier": _quality_to_tier(sack_q),
        "def_coverage_tier": _quality_to_tier(coverage_q),
    }

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
mongo_client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
mongo_db = mongo_client["nfl-random-teams"]

N_GAMES = 17

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
    "CB": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "FS": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "SS": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "S": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "SAF": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "Nickel": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "Dime": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "K": ["fg_made", "fg_att"],
    "P": [],
    "OT": [], "G": [], "C": [], "LS": [],
    "RS": ["kickoff_return_yards", "kickoff_returns", "punt_return_yards", "punt_returns"],
}

SEASON_TOTAL_STATS = {"fg_made", "fg_att", "kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards"}

_POS_STAT_CAPS_PER_GAME = {
    "QB": {"passing_yards": 450, "passing_tds": 6, "passing_interceptions": 4, "carries": 12, "rushing_yards": 80, "rushing_tds": 2},
    "RB": {"carries": 30, "rushing_yards": 250, "rushing_tds": 4, "receptions": 10, "targets": 12, "receiving_yards": 120, "receiving_tds": 2},
    "FB": {"carries": 15, "rushing_yards": 100, "rushing_tds": 2, "receptions": 6, "targets": 8, "receiving_yards": 60, "receiving_tds": 1},
    "WR": {"receptions": 14, "receiving_yards": 250, "receiving_tds": 3, "targets": 16, "carries": 5, "rushing_yards": 60, "rushing_tds": 1},
    "TE": {"receptions": 12, "receiving_yards": 220, "receiving_tds": 3, "targets": 14},
    "DE": {"def_sacks": 3, "def_tackles_solo": 10, "def_pass_defended": 4},
    "DT": {"def_sacks": 2, "def_tackles_solo": 8, "def_pass_defended": 3},
    "LB": {"def_tackles_solo": 18, "def_sacks": 2, "def_interceptions": 1, "def_pass_defended": 3},
    "OLB": {"def_tackles_solo": 15, "def_sacks": 3, "def_interceptions": 1, "def_pass_defended": 3},
    "ILB": {"def_tackles_solo": 18, "def_sacks": 2, "def_interceptions": 1, "def_pass_defended": 3},
    "MLB": {"def_tackles_solo": 18, "def_sacks": 2, "def_interceptions": 1, "def_pass_defended": 3},
    "CB": {"def_interceptions": 2, "def_pass_defended": 5, "def_tackles_solo": 8},
    "FS": {"def_interceptions": 2, "def_pass_defended": 4, "def_tackles_solo": 8},
    "SS": {"def_interceptions": 2, "def_pass_defended": 4, "def_tackles_solo": 8},
    "S": {"def_interceptions": 2, "def_pass_defended": 4, "def_tackles_solo": 8},
    "SAF": {"def_interceptions": 2, "def_pass_defended": 4, "def_tackles_solo": 8},
    "Nickel": {"def_interceptions": 2, "def_pass_defended": 5, "def_tackles_solo": 7},
    "Dime": {"def_interceptions": 2, "def_pass_defended": 5, "def_tackles_solo": 6},
    "K": {"fg_made": 40, "fg_att": 50},
    "RS": {"kickoff_return_yards": 550, "kickoff_returns": 30, "punt_return_yards": 400, "punt_returns": 35},
}

DEPTH_SLOT_SCALE = {1: 1.35, 2: 0.50, 3: 0.30}
_STARTER_BOOST: dict[str, float] = {
    "RB": 1.25,
    "FB": 1.10,
    "WR": 1.30,
    "TE": 1.20,
}

_POS_STATS_CACHE: dict = {}

def get_generated_team(team_id: str) -> dict:
    return mongo_db.teams.find_one({"_id": ObjectId(team_id)})

def fetch_player_stats(player_names: list) -> pd.DataFrame:
    r = supabase.table("player_stats").select("*").in_("player_display_name", player_names).gte("season", 2021).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def fetch_position_stats_cached(position: str) -> pd.DataFrame:
    if position in _POS_STATS_CACHE:
        return _POS_STATS_CACHE[position]
    r = supabase.table("player_stats").select("*").eq("position", position).gte("season", 2021).execute()
    df = pd.DataFrame(r.data) if r.data else pd.DataFrame()
    _POS_STATS_CACHE[position] = df
    return df

def fetch_nfl_roster(team_full_name: str, season: int) -> list[dict]:
    """Return top starters from player_stats for an NFL team + season."""
    r = supabase.table("player_stats").select("*").eq("team", team_full_name).eq("season", season).execute()
    if not r.data:
        return []
    df = pd.DataFrame(r.data)
    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != "season"]
    group_cols = [c for c in ["player_display_name", "position", "team", "season"] if c in df.columns]
    agg = df.groupby(group_cols)[numeric_cols].sum().reset_index()

    POS_PRIMARY = {
        "QB": "passing_yards", "RB": "rushing_yards", "FB": "rushing_yards",
        "WR": "receiving_yards", "TE": "receiving_yards",
        "DE": "def_sacks", "DT": "def_sacks", "NT": "def_tackles_solo",
        "LB": "def_tackles_solo", "OLB": "def_tackles_solo", "ILB": "def_tackles_solo",
        "MLB": "def_tackles_solo", "CB": "def_pass_defended",
        "FS": "def_tackles_solo", "SS": "def_tackles_solo", "S": "def_tackles_solo", "SAF": "def_tackles_solo",
        "K": "fg_made",
    }
    POS_MAX = {
        "QB": 1, "RB": 2, "FB": 1, "WR": 3, "TE": 2,
        "DE": 2, "DT": 2, "NT": 1,
        "LB": 2, "OLB": 2, "ILB": 2, "MLB": 2,
        "CB": 2, "FS": 1, "SS": 1, "S": 2, "SAF": 2,
        "K": 1,
    }
    roster = []
    for pos, primary in POS_PRIMARY.items():
        sub = agg[agg["position"] == pos]
        if sub.empty:
            continue
        if primary in sub.columns:
            sub = sub.sort_values(primary, ascending=False)
        for _, row in sub.head(POS_MAX.get(pos, 2)).iterrows():
            roster.append({"name": row["player_display_name"], "position": pos, "nfl_team": team_full_name})
    return roster


def fetch_team_season_stats(team_full_name: str, season: int) -> pd.DataFrame:
    r = supabase.table("team_stats").select("*").eq("team", team_full_name).eq("season", season).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_pos_dist_mean(position: str, stat: str) -> float:
    """Population mean for a position+stat, used as fallback."""
    df = fetch_position_stats_cached(position)
    if df.empty or stat not in df.columns:
        return 0.0
    group_cols = [c for c in ["player_display_name", "season"] if c in df.columns]
    if group_cols:
        grp = df.groupby(group_cols)[stat].sum().reset_index()
        vals = pd.to_numeric(grp[stat], errors="coerce").dropna()
    else:
        vals = pd.to_numeric(df[stat], errors="coerce").dropna()
    vals = vals[vals > 0]
    if len(vals) < 5:
        return 0.0
    mean = float(vals.mean())
    if stat not in SEASON_TOTAL_STATS:
        mean = mean / N_GAMES
    return mean


DEF_POSITIONS = {"DE", "DT", "NT", "LB", "OLB", "ILB", "MLB", "CB", "FS", "SS", "S", "SAF", "Nickel", "Dime"}

def build_player_dist(player_df: pd.DataFrame, name: str, position: str, depth_slot: int = 1) -> dict:
    """Build per-game truncated-normal distributions for one player."""
    stat_cols = POS_STAT_MAPPING.get(position, [])
    dists = {}
    caps = _POS_STAT_CAPS_PER_GAME.get(position, {})
    if position in DEF_POSITIONS:
        scale = 1.0
    else:
        scale = DEPTH_SLOT_SCALE.get(depth_slot, 0.3)
        if depth_slot == 1:
            scale *= _STARTER_BOOST.get(position, 1.0)

    player_data = player_df[player_df["player_display_name"] == name].copy() if not player_df.empty else pd.DataFrame()

    if not player_data.empty and "season" in player_data.columns:
        agg_cols = [c for c in stat_cols if c in player_data.columns]
        if agg_cols:
            player_data = player_data.groupby("season")[agg_cols].sum().reset_index()

    for stat in stat_cols:
        cap = caps.get(stat, 9999)
        if not player_data.empty and stat in player_data.columns:
            vals = pd.to_numeric(player_data[stat], errors="coerce").dropna()
            vals = vals[vals > 0]
            if len(vals) >= 2:
                season_mean = float(vals.mean())
                season_std = float(vals.std())
                if stat not in SEASON_TOTAL_STATS:
                    mean = season_mean / N_GAMES
                    std = season_std / N_GAMES
                else:
                    mean = season_mean
                    std = season_std
                std = min(std, max(mean * 0.5, 0.01))
                mean = min(mean * scale, cap)
                std = max(std * scale, 0.01)
                a = -mean / std if std > 0 else -10
                dists[stat] = stats.truncnorm(a=a, b=5, loc=mean, scale=std)
                continue

        pop_mean = get_pos_dist_mean(position, stat)
        if pop_mean <= 0:
            continue
        mean = min(pop_mean * scale, cap)
        std = max(mean * 0.35, 0.01)
        a = -mean / std
        dists[stat] = stats.truncnorm(a=a, b=5, loc=mean, scale=std)

    return dists


def build_all_dists(team_obj: dict, player_df: pd.DataFrame) -> dict:
    result = {}
    pos_counter: dict = {}
    for player in team_obj["players"]:
        name = player["name"]
        pos = player["position"]
        pos_counter[pos] = pos_counter.get(pos, 0) + 1
        slot = pos_counter[pos]
        dists = build_player_dist(player_df, name, pos, depth_slot=slot)
        result[name] = {"position": pos, "depth_slot": slot, "distributions": dists}
    return result


def _player_ypc(name: str, player_df: pd.DataFrame, default: float = 4.2) -> float:
    if player_df.empty:
        return default
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return default
    carries = pd.to_numeric(rows.get("carries", pd.Series()), errors="coerce").sum()
    rush_yds = pd.to_numeric(rows.get("rushing_yards", pd.Series()), errors="coerce").sum()
    if carries < 10:
        return default
    return float(np.clip(rush_yds / carries, 2.5, 8.0))


_YPR_FALLBACK_BY_POS = {"WR": 12.5, "TE": 9.5, "RB": 7.0, "FB": 6.5}

def _player_ypr(name: str, player_df: pd.DataFrame, pos: str = "WR") -> float:
    fallback = _YPR_FALLBACK_BY_POS.get(pos, 9.5)
    if player_df.empty:
        return fallback
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return fallback
    recs = pd.to_numeric(rows.get("receptions", pd.Series()), errors="coerce").sum()
    rec_yds = pd.to_numeric(rows.get("receiving_yards", pd.Series()), errors="coerce").sum()
    if recs < 5:
        return fallback
    return float(np.clip(rec_yds / recs, 4.0, 22.0))


_TARGET_SHARE_CAP = {"WR": 10.0, "TE": 5.5, "RB": 4.0, "FB": 2.0}
_TARGET_SHARE_DEFAULT = {"WR": 4.0, "TE": 2.0, "RB": 2.5, "FB": 1.0}

def _player_target_share(name: str, player_df: pd.DataFrame, pos: str) -> float:
    default = _TARGET_SHARE_DEFAULT.get(pos, 3.0)
    cap = _TARGET_SHARE_CAP.get(pos, 8.0)
    if player_df.empty:
        return default
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return default
    season_col = "season" if "season" in rows.columns else None
    tgts = pd.to_numeric(rows.get("targets", pd.Series(dtype=float)), errors="coerce")
    if season_col:
        n_seasons = rows[season_col].nunique()
        avg = float(tgts.sum()) / max(n_seasons, 1) / N_GAMES
    else:
        avg = float(tgts.mean())
    if avg < 0.5:
        return default
    return float(np.clip(avg, default, cap))


def _player_rush_share(name: str, player_df: pd.DataFrame) -> float:
    if player_df.empty:
        return 3.0
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return 3.0
    season_col = "season" if "season" in rows.columns else None
    carries = pd.to_numeric(rows.get("carries", pd.Series(dtype=float)), errors="coerce")
    if season_col:
        n_seasons = rows[season_col].nunique()
        avg = float(carries.sum()) / max(n_seasons, 1) / N_GAMES
    else:
        avg = float(carries.mean())
    if avg < 0.5:
        return 3.0
    return float(np.clip(avg, 3.0, 22.0))

_RUN_PROB = {
    (1, "short"): 0.48,
    (1, "medium"): 0.45,
    (1, "long"): 0.40,
    (2, "short"): 0.52,
    (2, "medium"): 0.38,
    (2, "long"): 0.22,
    (3, "short"): 0.42,
    (3, "medium"): 0.18,
    (3, "long"): 0.10,
    (4, "short"): 0.55,
    (4, "medium"): 0.25,
    (4, "long"): 0.10,
}

_SACK_PROB = 0.028
_INT_PROB = 0.020
_INCOMP_PROB = 0.28
_FUMBLE_PROB = 0.006

_RUN_YARDS_MEAN = 4.2
_RUN_YARDS_STD = 3.5
_PASS_YARDS_MEAN = 9.5
_PASS_YARDS_STD = 6.0

_FG_ATTEMPT_DIST = 0.35
_FG_MAKE_PROB_BASE = 0.87

_SACK_WEIGHT = {"DE": 5, "DT": 4, "NT": 3, "OLB": 3, "LB": 1, "ILB": 1, "MLB": 1}
_INT_WEIGHT = {"CB": 4, "FS": 2, "SS": 2, "S": 2, "SAF": 2, "Nickel": 3, "Dime": 3}
_FUMBLE_WEIGHT = {"DE": 3, "DT": 2, "OLB": 3, "LB": 2, "ILB": 2, "MLB": 2, "CB": 1, "FS": 1, "SS": 1, "S": 1, "Nickel": 1, "Dime": 1}
_PD_WEIGHT = {"CB": 5, "FS": 3, "SS": 3, "S": 3, "SAF": 3, "LB": 1, "OLB": 1, "Nickel": 4, "Dime": 4}
_RUN_TACKLE_WEIGHT = {"ILB": 6, "MLB": 6, "LB": 5, "OLB": 4, "DE": 3, "DT": 2, "NT": 2, "SS": 2, "FS": 1, "CB": 1, "Nickel": 1, "Dime": 1}
_PASS_TACKLE_WEIGHT = {"CB": 5, "FS": 4, "SS": 4, "S": 4, "SAF": 4, "OLB": 2, "ILB": 2, "MLB": 2, "LB": 2, "DE": 1, "Nickel": 4, "Dime": 4}

_PLAY_TEMPLATES = {
    "run": [
        "{rusher} takes the handoff, gains {yards} yards.",
        "{rusher} up the middle for {yards}.",
        "{rusher} cuts outside for {yards} yards.",
        "{rusher} powers through contact for {yards} hard yards.",
    ],
    "pass_complete": [
        "{qb} finds {receiver} for {yards} yards.",
        "{qb} hits {receiver} over the middle, {yards} yards.",
        "{qb} throws to {receiver}, who gains {yards}.",
        "{qb} connects with {receiver} for {yards} yards.",
    ],
    "pass_incomplete": [
        "{qb} throws incomplete intended for {receiver}.",
        "{qb} can't connect with {receiver}, ball falls incomplete.",
        "Incomplete pass by {qb} intended for {receiver}.",
    ],
    "sack": [
        "{defender} beats the block and sacks {qb} for a loss!",
        "Pressure up the middle... {defender} gets home and sacks {qb}!",
        "{defender} strips {qb} on the sack... fumble recovered by the offense.",
    ],
    "interception": [
        "{qb} throws... INTERCEPTED by {defender}, intended for {receiver}!",
        "{qb} tries to find {receiver}... {defender} reads it perfectly! PICK!",
        "Tipped and caught... {defender} intercepts {qb}'s pass intended for {receiver}!",
        "{defender} undercuts the route on {receiver}... INTERCEPTION! Turnover!",
    ],
    "fumble_forced": [
        "{defender} punches the ball out on {rusher}! FUMBLE recovered by the defense!",
        "{defender} strips {rusher}... ball on the ground, DEFENSE RECOVERS!",
        "Huge hit by {defender} jars the ball loose from {rusher}! TURNOVER!",
    ],
    "pass_defended": [
        "{defender} bats the ball away... incomplete!",
        "{defender} in tight coverage, breaks it up at the last second!",
        "Good defense by {defender}, forces the incompletion.",
    ],
    "opp_fumble_forced": [
        "{defender} rips the ball away from {rusher}! Big turnover for your team!",
        "{defender} lays the hit on {rusher} and forces the fumble! Defense recovers!",
        "Strip by {defender}! {rusher} loses the ball... your defense takes over!",
    ],
    "opp_pass_defended": [
        "{defender} swats it away... no gain!",
        "{defender} blanketed the receiver, forces the incompletion.",
        "Nice play by {defender} to break that one up!",
    ],
    "rushing_td": [
        "{rusher} punches it in from {yards} yards! TOUCHDOWN!",
        "{rusher} breaks a tackle and scores from {yards} out! TD!",
        "{rusher} up the gut from {yards} yards... TOUCHDOWN!",
        "{rusher} fights through the pile and scores! {yards}-yard TD!",
    ],
    "passing_td": [
        "{qb} fires to {receiver} in the end zone... TOUCHDOWN! {yards} yards!",
        "{qb} threads the needle to {receiver} for a {yards}-yard TD!",
        "Beautiful throw from {qb}, {receiver} hauls it in for a {yards}-yard score!",
        "{qb} rolls out and finds {receiver} for a {yards}-yard TOUCHDOWN!",
    ],
    "fg_good": [
        "{kicker} lines it up from {yards} yards... it's GOOD! 3 points.",
        "Field goal by {kicker} from {yards} yards... RIGHT down the middle!",
        "{kicker} splits the uprights from {yards}. 3 MORE on the board.",
    ],
    "fg_miss": [
        "{kicker} pulls it wide left from {yards}. NO GOOD!",
        "{kicker}'s {yards}-yard attempt MISSES right. NO GOOD!",
        "The kick is off... {kicker} MISSES from {yards} yards.",
    ],
    "punt": [
        "Offense stalls. Punting unit takes the field.",
        "Can't convert on third down... punt.",
        "Three-and-out. Forced to punt.",
    ],
    "opp_run": [
        "{rusher} runs for {yards} yards.",
        "{rusher} gains {yards} on the carry.",
    ],
    "opp_pass_complete": [
        "{qb} completes to {receiver} for {yards} yards.",
        "{qb} finds {receiver}, who gains {yards}.",
    ],
    "opp_pass_incomplete": [
        "{qb} throws incomplete for {receiver}.",
        "Incomplete pass by {qb}.",
    ],
    "opp_sack": [
        "{defender} gets home and sacks {qb} for a loss!",
        "Pressure! {defender} brings down {qb} for the sack!",
    ],
    "opp_interception": [
        "{qb} fires for {receiver}... INTERCEPTED by {defender}! Huge turnover for your team!",
        "{defender} steps in front of {receiver} and takes it... INTERCEPTION!",
        "{qb} telegraphs it to {receiver}... {defender} reads it perfectly! INTERCEPTION!",
        "{defender} picks off {qb}, intended for {receiver}! Not a great read by {qb}!",
    ],
    "opp_rushing_td": [
        "{rusher} scores from {yards} yards out! TD for {team}!",
        "{rusher} punches it in... {yards}-yard TD run for {team}!",
    ],
    "opp_passing_td": [
        "{qb} connects with {receiver} for a {yards}-yard TD! {team} scores!",
        "{qb} fires to {receiver} in the end zone... TOUCHDOWN for {team}!",
    ],
    "opp_fg_good": [
        "{kicker} hits from {yards} yards. {team} adds 3 points.",
        "Field goal good for {team}. {kicker} connects from {yards}.",
    ],
    "opp_fg_miss": [
        "{kicker} misses from {yards} yards. No good for {team}.",
        "Wide! {kicker}'s {yards}-yard attempt for {team} is no good.",
    ],
    "opp_punt": [
        "{team} punts after failing to convert.",
        "Three-and-out for {team}. Punt.",
        "{team} stalls and punts it away.",
    ],
}

def _pick_template(key: str, **kw) -> str:
    return random.choice(_PLAY_TEMPLATES[key]).format(**kw)

def _dist_bucket(yards_to_go: int) -> str:
    if yards_to_go <= 3:
        return "short"
    if yards_to_go <= 7:
        return "medium"
    return "long"

def _fg_make_prob(distance: int) -> float:
    if distance < 30: return 0.93
    if distance < 40: return 0.87
    if distance < 50: return 0.79
    if distance < 60: return 0.60
    return 0.38

def _weighted_pick(pool: list[tuple]) -> str:
    if not pool:
        return "DEF"
    names, weights = zip(*pool)
    return random.choices(names, weights=weights, k=1)[0]


def simulate_game_drives(
    user_team: dict,
    user_player_df: pd.DataFrame,
    opp_roster: list,
    opp_player_df: pd.DataFrame,
    opp_name: str,
    opp_quality: float = 1.0,
    season: int = 2024,
) -> tuple[dict, dict, list[dict], int, int]:
    """
    Drive-based game simulation. Returns:
      (user_game_stats, opp_game_stats, play_log, user_score, opp_score)
    where *_game_stats are dicts of {player_name: {stat: value}}.
    """

    def _first(players, positions):
        for p in players:
            if p["position"] in positions:
                return p["name"]
        return None

    user_players = user_team["players"]
    opp_def_tiers = _get_nfl_def_tiers(opp_name, season)
    user_def_tiers = _compute_user_def_tiers(user_players, user_player_df)

    user_qb = _first(user_players, {"QB"}) or "QB"
    user_kicker = _first(user_players, {"K"})  or "K"
    user_punter = _first(user_players, {"P"})  or None
    user_returner = _first(user_players, {"RS"}) or None
    user_rushers = [(p["name"], _player_rush_share(p["name"], user_player_df))
                    for p in user_players if p["position"] in ("RB", "FB")]
    _u_skill_wr_te = [(p["name"], _player_target_share(p["name"], user_player_df, p["position"]))
                      for p in user_players if p["position"] in ("WR", "TE")]
    _u_skill_rb = [(p["name"], _player_target_share(p["name"], user_player_df, p["position"]))
                   for p in user_players if p["position"] in ("RB", "FB")]
    user_receivers = _u_skill_wr_te + _u_skill_rb
    def _build_def_pools(players):
        """Build defender pools with depth-based weight variation within same position."""
        pos_depth: dict[str, int] = {}
        sack_pool, int_pool, fumble_pool, pd_pool, run_tkl_pool, pass_tkl_pool = [], [], [], [], [], []
        for p in players:
            pos = p["position"]
            slot = pos_depth.get(pos, 0) + 1
            pos_depth[pos] = slot
            depth_scale = max(0.3, 1.0 - (slot - 1) * 0.30)
            name = p["name"]
            if pos in _SACK_WEIGHT:
                sack_pool.append((name, _SACK_WEIGHT[pos] * depth_scale))
            if pos in _INT_WEIGHT:
                int_pool.append((name, _INT_WEIGHT[pos] * depth_scale))
            if pos in _FUMBLE_WEIGHT:
                fumble_pool.append((name, _FUMBLE_WEIGHT[pos] * depth_scale))
            if pos in _PD_WEIGHT:
                pd_pool.append((name, _PD_WEIGHT[pos] * depth_scale))
            if pos in _RUN_TACKLE_WEIGHT:
                run_tkl_pool.append((name, _RUN_TACKLE_WEIGHT[pos] * depth_scale))
            if pos in _PASS_TACKLE_WEIGHT:
                pass_tkl_pool.append((name, _PASS_TACKLE_WEIGHT[pos] * depth_scale))
        return sack_pool, int_pool, fumble_pool, pd_pool, run_tkl_pool, pass_tkl_pool

    (user_sack_pool, user_int_pool, user_fumble_pool,
     user_pd_pool, user_run_tkl_pool, user_pass_tkl_pool) = _build_def_pools(user_players)

    opp_qb = _first(opp_roster, {"QB"}) or f"{opp_name} QB"
    opp_kicker = _first(opp_roster, {"K"})  or f"{opp_name} K"
    opp_rushers = [(p["name"], _player_rush_share(p["name"], opp_player_df))
                   for p in opp_roster if p["position"] in ("RB", "FB")]
    opp_receivers = (
        [(p["name"], _player_target_share(p["name"], opp_player_df, p["position"]))
         for p in opp_roster if p["position"] in ("WR", "TE")] +
        [(p["name"], _player_target_share(p["name"], opp_player_df, p["position"]))
         for p in opp_roster if p["position"] in ("RB", "FB")]
    )
    (opp_sack_pool, opp_int_pool, opp_fumble_pool,
     opp_pd_pool, opp_run_tkl_pool, opp_pass_tkl_pool) = _build_def_pools(opp_roster)

    _user_pos_map = {p["name"]: p["position"] for p in user_players}
    _opp_pos_map = {p["name"]: p["position"] for p in opp_roster}

    _user_ypc = {n: _player_ypc(n, user_player_df) for n, _ in user_rushers}
    _user_ypr = {n: _player_ypr(n, user_player_df, _user_pos_map.get(n, "WR")) for n, _ in user_receivers}
    _opp_ypc = {n: _player_ypc(n, opp_player_df)  for n, _ in opp_rushers}
    _opp_ypr = {n: _player_ypr(n, opp_player_df,  _opp_pos_map.get(n, "WR"))  for n, _ in opp_receivers}
    _user_wr_te_names = {p["name"] for p in user_players if p["position"] in ("WR", "TE")}
    _opp_wr_te_names = {p["name"] for p in opp_roster  if p["position"] in ("WR", "TE")}
    _user_wr_names = {p["name"] for p in user_players if p["position"] == "WR"}
    _opp_wr_names = {p["name"] for p in opp_roster  if p["position"] == "WR"}
    _user_te_names = {p["name"] for p in user_players if p["position"] == "TE"}
    _opp_te_names = {p["name"] for p in opp_roster  if p["position"] == "TE"}

    _TARGET_SHARE_BY_POS = {"WR": 0.74, "TE": 0.18, "RB": 0.07, "FB": 0.01}
    _MIN_WEIGHT_FLOOR = {"WR": 0.3, "TE": 0.2, "RB": 0.1, "FB": 0.05}

    def _normalize_receiver_pool(pool, wr_names: set, te_names: set) -> dict:
        """Build per-pos-group normalized pools keyed by group name.
        Returns {"WR": [(name, w), ...], "TE": [...], "RB": [...]}
        with weights normalized within group and a minimum floor applied.
        """
        if not pool:
            return {"WR": [], "TE": [], "RB": []}
        groups: dict[str, list] = {"WR": [], "TE": [], "RB": []}
        for name, w in pool:
            if name in wr_names:
                groups["WR"].append((name, w))
            elif name in te_names:
                groups["TE"].append((name, w))
            else:
                groups["RB"].append((name, w))

        result: dict[str, list] = {}
        for pos, members in groups.items():
            if not members:
                result[pos] = []
                continue
            floor = _MIN_WEIGHT_FLOOR.get(pos, 0.2)
            floored = [(n, max(w, floor)) for n, w in members]
            total_w = sum(w for _, w in floored)
            result[pos] = [(n, w / total_w) for n, w in floored]
        return result

    _user_rec_pools = _normalize_receiver_pool(user_receivers, _user_wr_names, _user_te_names)
    _opp_rec_pools = _normalize_receiver_pool(opp_receivers,  _opp_wr_names,  _opp_te_names)

    def _pick_rusher(pool):
        if not pool: return ("RB", 4.2)
        names, weights = zip(*pool)
        name = random.choices(names, weights=weights, k=1)[0]
        return name, _user_ypc.get(name, _opp_ypc.get(name, 4.2))

    def _pick_receiver(pool, ypr_map, rec_pos_probs: dict | None = None):
        """Pick a receiver using outcome-model position probabilities when available.
        rec_pos_probs: {"WR": float, "TE": float, "RB": float} from outcome model.
        Falls back to _TARGET_SHARE_BY_POS if not provided.
        """
        is_user = (pool is user_receivers)
        group_pools = _user_rec_pools if is_user else _opp_rec_pools

        if rec_pos_probs is not None:
            wr_p = float(rec_pos_probs.get("WR", _TARGET_SHARE_BY_POS["WR"]))
            te_p = float(rec_pos_probs.get("TE", _TARGET_SHARE_BY_POS["TE"]))
            rb_p = float(rec_pos_probs.get("RB", _TARGET_SHARE_BY_POS["RB"]))
        else:
            wr_p = _TARGET_SHARE_BY_POS["WR"]
            te_p = _TARGET_SHARE_BY_POS["TE"]
            rb_p = _TARGET_SHARE_BY_POS["RB"]

        wr_p = float(np.clip(wr_p, 0.58, 0.85)) if group_pools["WR"] else 0.0
        te_p = float(np.clip(te_p, 0.08, 0.22)) if group_pools["TE"] else 0.0
        rb_p = float(np.clip(rb_p, 0.04, 0.10)) if group_pools["RB"] else 0.0

        total = wr_p + te_p + rb_p
        if total <= 0:
            if not pool: return ("WR", 9.5)
            names, weights = zip(*pool)
            return random.choices(names, weights=weights, k=1)[0], 9.5
        wr_p /= total; te_p /= total; rb_p /= total

        group = random.choices(["WR", "TE", "RB"], weights=[wr_p, te_p, rb_p], k=1)[0]
        members = group_pools.get(group, [])
        if not members:
            for fallback in ["WR", "TE", "RB"]:
                if group_pools.get(fallback):
                    members = group_pools[fallback]
                    break
        if not members:
            return ("WR", 9.5)
        names, weights = zip(*members)
        name = random.choices(names, weights=weights, k=1)[0]
        return name, ypr_map.get(name, 9.5)

    _DEF_ZERO = {"def_tackles_solo": 0, "def_sacks": 0, "def_interceptions": 0, "def_pass_defended": 0}
    _DL_ZERO = {"def_tackles_solo": 0, "def_sacks": 0, "def_pass_defended": 0}
    _DB_ZERO = {"def_tackles_solo": 0, "def_interceptions": 0, "def_pass_defended": 0}
    _QB_ZERO = {"passing_attempts": 0, "passing_completions": 0, "passing_yards": 0, "passing_tds": 0, "passing_interceptions": 0}
    _RB_ZERO = {"carries": 0, "rushing_yards": 0, "rushing_tds": 0, "receptions": 0, "targets": 0, "receiving_yards": 0, "receiving_tds": 0}
    _WR_ZERO = {"targets": 0, "receptions": 0, "receiving_yards": 0, "receiving_tds": 0}
    _TE_ZERO = {"targets": 0, "receptions": 0, "receiving_yards": 0, "receiving_tds": 0}
    _K_ZERO = {"fg_made": 0, "fg_att": 0, "xp_made": 0, "xp_att": 0}
    _P_ZERO = {"punts": 0, "punt_yards": 0}
    _RS_ZERO = {"kickoff_returns": 0, "kickoff_return_yards": 0, "kickoff_return_tds": 0, "punt_returns": 0, "punt_return_yards": 0, "punt_return_tds": 0}
    _POS_ZERO = {
        "QB": _QB_ZERO,
        "RB": _RB_ZERO, "FB": _RB_ZERO,
        "WR": _WR_ZERO, "TE": _TE_ZERO,
        "K": _K_ZERO, "P": _P_ZERO, "RS": _RS_ZERO,
        "DE": _DL_ZERO, "DT": _DL_ZERO, "NT": _DL_ZERO,
        "LB": _DEF_ZERO, "OLB": _DEF_ZERO, "ILB": _DEF_ZERO, "MLB": _DEF_ZERO,
        "CB": _DB_ZERO, "FS": _DB_ZERO, "SS": _DB_ZERO, "S": _DB_ZERO, "SAF": _DB_ZERO,
    }
    user_stats: dict[str, dict] = {}
    for p in user_team["players"]:
        zeros = _POS_ZERO.get(p["position"])
        if zeros is not None:
            user_stats[p["name"]] = dict(zeros)
    opp_stats: dict[str, dict] = {}
    for p in opp_roster:
        zeros = _POS_ZERO.get(p["position"])
        if zeros is not None:
            opp_stats[p["name"]] = dict(zeros)

    def _add(stats_dict, name, **kwargs):
        if name not in stats_dict:
            stats_dict[name] = {}
        for k, v in kwargs.items():
            stats_dict[name][k] = stats_dict[name].get(k, 0) + v

    play_log: list[dict] = []
    user_score = 0
    opp_score = 0

    def _log(quarter: int, team: str, text: str, is_score: bool = False):
        play_log.append({
            "quarter": f"Q{quarter}",
            "team": team,
            "play": text,
            "score": f"{user_score}-{opp_score}",
            "is_score": is_score,
        })

    user_name = user_team.get("team_name", "Your Team")

    def run_play(side: str, down: int, ytg: int, quarter: int, score_diff: int, current_yardline: int = 75) -> tuple[int, str, bool]:
        if side == "user":
            qb = user_qb
            rushers_pool = user_rushers
            receivers_pool = user_receivers
            ypr_map = _user_ypr
            sack_pool = opp_sack_pool
            int_pool = opp_int_pool
            fumble_pool = opp_fumble_pool
            pd_pool = opp_pd_pool
            run_tkl_pool = opp_run_tkl_pool
            pass_tkl_pool = opp_pass_tkl_pool
            def_stats = opp_stats
            name = user_name
        else:
            qb = opp_qb
            rushers_pool = opp_rushers
            receivers_pool = opp_receivers
            ypr_map = _opp_ypr
            sack_pool = user_sack_pool
            int_pool = user_int_pool
            fumble_pool = user_fumble_pool
            pd_pool = user_pd_pool
            run_tkl_pool = user_run_tkl_pool
            pass_tkl_pool = user_pass_tkl_pool
            def_stats = user_stats
            name = opp_name
        yardline_100 = current_yardline

        secs_remaining = max(0.0, (4 - quarter) * 900.0 + 450.0)
        goal_to_go_flag = int(ytg >= int(100 - yardline_100))
        ml_pc = _ml_play_call(
            down=down, ydstogo=float(ytg), yardline_100=float(yardline_100),
            score_diff=float(score_diff), qtr=quarter,
            secs_remaining=secs_remaining, goal_to_go=goal_to_go_flag,
        )
        if ml_pc is not None:
            run_p  = ml_pc.get("run", 0.40)
            pass_p = ml_pc.get("pass", 0.40)
            total_rp = run_p + pass_p
            if total_rp > 0:
                run_prob = run_p / total_rp
            else:
                run_prob = 0.40
            run_prob = 0.55 * run_prob + 0.45 * 0.42
        else:
            bucket = _dist_bucket(ytg)
            run_prob = _RUN_PROB.get((down, bucket), 0.40)

        if ytg >= 8 and down >= 2:
            run_prob = min(run_prob, 0.30)
        if ytg <= 2:
            run_prob = max(run_prob, 0.60)

        if score_diff < -10 and quarter >= 4:
            run_prob *= 0.55
        if score_diff > 10 and quarter >= 4:
            run_prob *= 1.35
        run_prob = float(np.clip(run_prob, 0.05, 0.52))

        is_run = random.random() < run_prob
        is_highlight = False

        facing_def = opp_def_tiers if side == "user" else user_def_tiers

        if is_run:
            rusher, ypc = _pick_rusher(rushers_pool if side == "user" else [(n, w) for n, w in opp_rushers])

            ml_out = _ml_outcome(
                play_type="run", down=down, ydstogo=float(ytg),
                yardline_100=float(yardline_100), score_diff=float(score_diff),
                qtr=quarter, goal_to_go=goal_to_go_flag,
                def_pass_tier=facing_def["def_pass_tier"],
                def_rush_tier=facing_def["def_rush_tier"],
                def_sack_tier=facing_def["def_sack_tier"],
                def_coverage_tier=facing_def["def_coverage_tier"],
            )
            ypc_sample = np.random.normal(ypc, _RUN_YARDS_STD)
            if ml_out is not None:
                run_td_prob = float(ml_out["td_prob"])
                raw_yards = 0.35 * ml_out["yards"] + 0.65 * ypc_sample
                fumble_prob = float(np.clip(ml_out["turnover_prob"], 0.005, 0.015))
            else:
                run_td_prob = 0.0
                raw_yards = ypc_sample
                fumble_prob = _FUMBLE_PROB

            yards = int(np.clip(round(raw_yards), -3, 35))

            if yardline_100 <= 10 and run_td_prob > 0:
                boost = 2.0 if yardline_100 <= 5 else 1.4
                if random.random() < run_td_prob * boost:
                    td_yards = min(int(yardline_100), max(1, yards))
                    if side == "user":
                        _add(user_stats, rusher, carries=1, rushing_yards=td_yards, rushing_tds=1)
                    else:
                        _add(opp_stats, rusher, carries=1, rushing_yards=td_yards, rushing_tds=1)
                    if side == "user":
                        text = _pick_template("rushing_td", rusher=rusher, yards=td_yards)
                    else:
                        text = _pick_template("opp_rushing_td", rusher=rusher, yards=td_yards, team=opp_name)
                    _log(quarter, name, text, is_score=True)
                    return int(yardline_100) + 1, "td", True

            is_highlight = yards >= 12

            if random.random() < fumble_prob:
                strip_defender = _weighted_pick(fumble_pool)
                if side == "user":
                    _add(user_stats, rusher, carries=1, rushing_yards=max(0, yards))
                    _add(opp_stats, strip_defender, def_tackles_solo=1)
                    tmpl = "fumble_forced"
                else:
                    _add(opp_stats, rusher, carries=1, rushing_yards=max(0, yards))
                    _add(user_stats, strip_defender, def_tackles_solo=1)
                    tmpl = "opp_fumble_forced"
                text = _pick_template(tmpl, defender=strip_defender, rusher=rusher)
                _log(quarter, name, text)
                return yards, "fumble", True

            if side == "user":
                _add(user_stats, rusher, carries=1, rushing_yards=max(0, yards))
            else:
                _add(opp_stats, rusher, carries=1, rushing_yards=max(0, yards))
            if run_tkl_pool:
                tackler = _weighted_pick(run_tkl_pool)
                _add(def_stats, tackler, def_tackles_solo=1)

            if is_highlight:
                tmpl = "run" if side == "user" else "opp_run"
                text = _pick_template(tmpl, rusher=rusher, yards=abs(yards))
                _log(quarter, name, text)
            return yards, "", is_highlight

        else:
            ml_out = _ml_outcome(
                play_type="pass", down=down, ydstogo=float(ytg),
                yardline_100=float(yardline_100), score_diff=float(score_diff),
                qtr=quarter, goal_to_go=goal_to_go_flag,
                def_pass_tier=facing_def["def_pass_tier"],
                def_rush_tier=facing_def["def_rush_tier"],
                def_sack_tier=facing_def["def_sack_tier"],
                def_coverage_tier=facing_def["def_coverage_tier"],
            )
            if ml_out is not None:
                raw_td_prob = float(ml_out["td_prob"])
                int_prob = float(np.clip(ml_out["turnover_prob"], 0.010, 0.050))
                incomp_prob = float(np.clip(
                    1.0 - raw_td_prob * 2.0 - int_prob - 0.60, 0.15, 0.35
                ))
                pass_yards = ml_out["yards"]
                rec_pos_probs = ml_out.get("receiver_pos_probs")
            else:
                raw_td_prob = 0.0
                int_prob = _INT_PROB
                incomp_prob = _INCOMP_PROB
                pass_yards = None
                rec_pos_probs = None

            if random.random() < _SACK_PROB:
                sacker = _weighted_pick(sack_pool)
                sack_yds = random.randint(5, 12)
                if side == "opp":
                    _add(user_stats, sacker, def_sacks=1, def_tackles_solo=1)
                else:
                    _add(opp_stats, sacker, def_sacks=1, def_tackles_solo=1)
                tmpl = "sack" if side == "user" else "opp_sack"
                text = _pick_template(tmpl, defender=sacker, qb=qb)
                _log(quarter, name, text)
                return -sack_yds, "", False

            intended_receiver, ypr = _pick_receiver(receivers_pool, ypr_map, rec_pos_probs)

            if random.random() < int_prob:
                interceptor = _weighted_pick(int_pool)
                if side == "opp":
                    _add(user_stats, interceptor, def_interceptions=1, def_pass_defended=1)
                    _add(opp_stats, qb, passing_attempts=1, passing_yards=0, passing_interceptions=1)
                    _add(opp_stats, intended_receiver, targets=1)
                else:
                    _add(opp_stats, interceptor, def_interceptions=1, def_pass_defended=1)
                    _add(user_stats, qb, passing_attempts=1, passing_yards=0, passing_interceptions=1)
                    _add(user_stats, intended_receiver, targets=1)
                tmpl = "interception" if side == "opp" else "opp_interception"
                text = _pick_template(tmpl, defender=interceptor, qb=qb, receiver=intended_receiver)
                _log(quarter, name, text, is_score=False)
                return 0, "int", True

            if random.random() < incomp_prob:
                pd_defender = _weighted_pick(pd_pool)
                if side == "user":
                    _add(user_stats, qb, passing_attempts=1, passing_yards=0)
                    _add(user_stats, intended_receiver, targets=1)
                    _add(opp_stats, pd_defender, def_pass_defended=1)
                    if down >= 3:
                        text = _pick_template("opp_pass_defended", defender=pd_defender)
                        _log(quarter, opp_name, text)
                else:
                    _add(opp_stats, qb, passing_attempts=1, passing_yards=0)
                    _add(opp_stats, intended_receiver, targets=1)
                    _add(user_stats, pd_defender, def_pass_defended=1)
                    if down >= 3:
                        text = _pick_template("pass_defended", defender=pd_defender)
                        _log(quarter, user_name, text)
                return 0, "", False

            receiver = intended_receiver
            ypr_sample = np.random.normal(ypr, _PASS_YARDS_STD)
            if pass_yards is not None:
                blended = 0.35 * pass_yards + 0.65 * ypr_sample
            else:
                blended = ypr_sample
            yards = int(np.clip(round(blended), 1, 55))

            in_red_zone = yardline_100 <= 20
            if in_red_zone and raw_td_prob > 0:
                td_threshold = raw_td_prob * (1.8 if yardline_100 <= 10 else 1.2)
                if random.random() < td_threshold:
                    td_yards = min(int(yardline_100), yards, 20)
                    td_yards = max(1, td_yards)
                    if side == "user":
                        _add(user_stats, qb, passing_attempts=1, passing_completions=1, passing_yards=td_yards, passing_tds=1)
                        _add(user_stats, receiver, receptions=1, targets=1, receiving_yards=td_yards, receiving_tds=1)
                    else:
                        _add(opp_stats, qb, passing_attempts=1, passing_completions=1, passing_yards=td_yards, passing_tds=1)
                        _add(opp_stats, receiver, receptions=1, targets=1, receiving_yards=td_yards, receiving_tds=1)
                    if side == "user":
                        text = _pick_template("passing_td", qb=qb, receiver=receiver, yards=td_yards)
                    else:
                        text = _pick_template("opp_passing_td", qb=qb, receiver=receiver, yards=td_yards, team=opp_name)
                    _log(quarter, name, text, is_score=True)
                    return int(yardline_100) + 1, "td", True

            is_highlight = yards >= 20

            if side == "user":
                _add(user_stats, qb, passing_attempts=1, passing_completions=1, passing_yards=yards)
                _add(user_stats, receiver, receptions=1, targets=1, receiving_yards=yards)
            else:
                _add(opp_stats, qb, passing_attempts=1, passing_completions=1, passing_yards=yards)
                _add(opp_stats, receiver, receptions=1, targets=1, receiving_yards=yards)
            if pass_tkl_pool:
                tackler = _weighted_pick(pass_tkl_pool)
                _add(def_stats, tackler, def_tackles_solo=1)

            if is_highlight:
                tmpl = "pass_complete" if side == "user" else "opp_pass_complete"
                text = _pick_template(tmpl, qb=qb, receiver=receiver, yards=yards)
                _log(quarter, name, text)
            return yards, "", is_highlight

    XP_MAKE_PROB = 0.944
    TWO_PT_SUCCESS_PROB = 0.475

    def _should_go_for_two(my_score: int, their_score: int, quarter: int) -> bool:
        diff = my_score + 6 - their_score
        if quarter >= 4:
            if diff in (-2, -9, 5, 12):
                return True
            if diff < 0 and abs(diff) > 8 and random.random() < 0.35:
                return True
        return random.random() < 0.03

    def _attempt_pat(side: str, my_score_ref: list, their_score: int, quarter: int, stats: dict, kicker: str):
        team_name = user_name if side == "user" else opp_name
        if _should_go_for_two(my_score_ref[0], their_score, quarter):
            if random.random() < TWO_PT_SUCCESS_PROB:
                my_score_ref[0] += 2
                _log(quarter, team_name, "2-point conversion GOOD!", is_score=True)
            else:
                _log(quarter, team_name, "2-point conversion NO GOOD.")
        else:
            if kicker:
                _add(stats, kicker, xp_att=1)
            if random.random() < XP_MAKE_PROB:
                my_score_ref[0] += 1
                if kicker:
                    _add(stats, kicker, xp_made=1)

    def score_td(side: str, quarter: int, how: str, rusher_or_receiver: str = "", yards: int = 5):
        nonlocal user_score, opp_score
        if side == "user":
            user_score += 6
            if how == "rush":
                _add(user_stats, rusher_or_receiver, rushing_tds=1)
                text = _pick_template("rushing_td", rusher=rusher_or_receiver, yards=yards)
            else:
                _add(user_stats, user_qb, passing_attempts=1, passing_completions=1, passing_yards=yards, passing_tds=1)
                _add(user_stats, rusher_or_receiver, receptions=1, targets=1, receiving_yards=yards, receiving_tds=1)
                text = _pick_template("passing_td", qb=user_qb, receiver=rusher_or_receiver, yards=yards)
            _log(quarter, user_name, text, is_score=True)
            ref = [user_score]
            _attempt_pat("user", ref, opp_score, quarter, user_stats, user_kicker)
            user_score = ref[0]
        else:
            opp_score += 6
            if how == "rush":
                _add(opp_stats, rusher_or_receiver, rushing_tds=1)
                text = _pick_template("opp_rushing_td", rusher=rusher_or_receiver, yards=yards, team=opp_name)
            else:
                _add(opp_stats, opp_qb, passing_attempts=1, passing_completions=1, passing_yards=yards, passing_tds=1)
                _add(opp_stats, rusher_or_receiver, receptions=1, targets=1, receiving_yards=yards, receiving_tds=1)
                text = _pick_template("opp_passing_td", qb=opp_qb, receiver=rusher_or_receiver, yards=yards, team=opp_name)
            _log(quarter, opp_name, text, is_score=True)
            ref = [opp_score]
            _attempt_pat("opp", ref, user_score, quarter, opp_stats, "")
            opp_score = ref[0]

    def attempt_fg(side: str, quarter: int, distance: int, current_yardline: int = 75):
        nonlocal user_score, opp_score
        if side == "user":
            kicker = user_kicker
            team = user_name
            sdiff  = float(user_score - opp_score)
        else:
            kicker = opp_kicker
            team = opp_name
            sdiff  = float(opp_score - user_score)
        yl100 = float(current_yardline)

        ml_out = _ml_outcome(
            play_type="field_goal", down=4, ydstogo=float(distance),
            yardline_100=yl100, score_diff=sdiff, qtr=quarter,
            kick_distance=float(distance),
        )
        if ml_out is not None:
            fg_probs = ml_out.get("fg_result_probs", {})
            made_p    = fg_probs.get("made",    _fg_make_prob(distance))
            blocked_p = fg_probs.get("blocked", 0.02)
        else:
            made_p    = _fg_make_prob(distance)
            blocked_p = 0.02

        roll = random.random()
        if roll < made_p:
            if side == "user":
                user_score += 3
                _add(user_stats, kicker, fg_made=1, fg_att=1)
            else:
                opp_score += 3
                _add(opp_stats, kicker, fg_made=1, fg_att=1)
            tmpl = "fg_good" if side == "user" else "opp_fg_good"
            text = _pick_template(tmpl, kicker=kicker, yards=distance, team=team)
            _log(quarter, team, text, is_score=True)
        else:
            if side == "user":
                _add(user_stats, kicker, fg_att=1)
            else:
                _add(opp_stats, kicker, fg_att=1)
            tmpl = "fg_miss" if side == "user" else "opp_fg_miss"
            text = _pick_template(tmpl, kicker=kicker, yards=distance, team=team)
            _log(quarter, team, text, is_score=False)

    _PUNT_RET_TD_PROB  = 0.005 * 0.02
    _KO_RET_TD_PROB    = 0.004 * 0.02

    def _do_punt(side: str, punt_yardline: int, quarter: int) -> int:
        nonlocal user_score
        yl100 = float(punt_yardline)
        sdiff = float((user_score - opp_score) if side == "user" else (opp_score - user_score))
        kick_dist = float(max(30, 100 - punt_yardline))
        ml_out = _ml_outcome(
            play_type="punt", down=4, ydstogo=15.0,
            yardline_100=yl100, score_diff=sdiff, qtr=quarter,
            kick_distance=kick_dist,
        )
        if ml_out is not None:
            net_yds = int(np.clip(round(ml_out["punt_net_yards"]), 15, 65))
            blocked_p = ml_out.get("punt_blocked_prob", 0.01)
        else:
            net_yds = random.randint(28, 46)
            blocked_p = 0.01

        if side == "user" and user_punter:
            _add(user_stats, user_punter, punts=1, punt_yards=net_yds)

        if random.random() < blocked_p:
            _log(quarter, ("opp" if side == "user" else user_name), "Punt is BLOCKED!")
            return max(15, 100 - punt_yardline - 5)

        if side == "opp" and user_returner:
            ret_yds = random.randint(5, 14)
            if random.random() < _PUNT_RET_TD_PROB:
                user_score += 6
                _log(quarter, user_name, f"{user_returner} takes the punt return ALL THE WAY... TOUCHDOWN!", is_score=True)
                _add(user_stats, user_returner, punt_returns=1, punt_return_yards=100, punt_return_tds=1)
                ref = [user_score]
                _attempt_pat("user", ref, opp_score, quarter, user_stats, user_kicker)
                user_score = ref[0]
                return 35
            _add(user_stats, user_returner, punt_returns=1, punt_return_yards=ret_yds)

        return max(15, 100 - punt_yardline - net_yds)

    def _do_kickoff_return(quarter: int) -> None:
        """Credit the returner for a kickoff return, with infinitesimal TD chance."""
        nonlocal user_score
        if not user_returner:
            return
        ret_yds = random.randint(18, 32)
        if random.random() < _KO_RET_TD_PROB:
            user_score += 6
            _log(quarter, user_name, f"{user_returner} returns the kickoff for a TOUCHDOWN!", is_score=True)
            _add(user_stats, user_returner, kickoff_returns=1, kickoff_return_yards=100, kickoff_return_tds=1)
            ref = [user_score]
            _attempt_pat("user", ref, opp_score, quarter, user_stats, user_kicker)
            user_score = ref[0]
        else:
            _add(user_stats, user_returner, kickoff_returns=1, kickoff_return_yards=ret_yds)

    def simulate_drive(side: str, start_yardline: int, quarter: int) -> tuple[int, int]:
        """Simulate a full drive. Returns (ending_quarter, final_yardline)."""
        nonlocal user_score, opp_score
        down = 1
        ytg = 10
        yardline = start_yardline
        plays_run = 0
        MAX_PLAYS = 20

        while plays_run < MAX_PLAYS:
            score_diff = (user_score - opp_score) if side == "user" else (opp_score - user_score)
            yards, event, _ = run_play(side, down, ytg, quarter, score_diff, yardline)
            plays_run += 1
            yardline += yards

            if event == "td":
                if side == "user":
                    user_score += 6
                    ref = [user_score]
                    _attempt_pat("user", ref, opp_score, quarter, user_stats, user_kicker)
                    user_score = ref[0]
                else:
                    opp_score += 6
                    ref = [opp_score]
                    _attempt_pat("opp", ref, user_score, quarter, opp_stats, "")
                    opp_score = ref[0]
                    _do_kickoff_return(quarter)
                return quarter, 35

            if yardline >= 100:
                td_yards = max(1, yards)
                if side == "user":
                    rusher_name, _ = _pick_rusher(user_rushers)
                    rec_name, _  = _pick_receiver(user_receivers, _user_ypr, None)
                else:
                    rusher_name, _ = _pick_rusher([(n, w) for n, w in opp_rushers])
                    rec_name, _ = _pick_receiver(opp_receivers, _opp_ypr, None)
                is_rush_td = random.random() < 0.40
                scorer = rusher_name if is_rush_td else rec_name
                score_td(side, quarter, "rush" if is_rush_td else "pass", scorer, min(td_yards, 20))
                if side == "opp":
                    _do_kickoff_return(quarter)
                return quarter, 35

            if event == "int" or event == "fumble":
                return quarter, 100 - max(20, yardline)

            if yardline <= 0:
                yardline = 5
                down = 1
                ytg = 10
                continue
            if yards >= ytg:
                down = 1
                ytg  = 10
            else:
                ytg  -= yards
                down += 1

            if down == 4:
                dist_to_goal = 100 - yardline
                if dist_to_goal <= 52 and random.random() < _FG_ATTEMPT_DIST:
                    attempt_fg(side, quarter, dist_to_goal + 17, yardline)
                    if side == "opp":
                        _do_kickoff_return(quarter)
                    return quarter, 35
                else:
                    return quarter, _do_punt(side, yardline, quarter)

        return quarter, _do_punt(side, yardline, quarter)

    possession_order = []
    for q in range(1, 5):
        if q == 1:
            sides = ["user", "opp", "user", "opp"]
        elif q == 3:
            sides = random.choice([["opp", "user", "opp", "user"],
                                   ["user", "opp", "user", "opp"]])
        else:
            last = possession_order[-1][0] if possession_order else "user"
            first = "opp" if last == "user" else "user"
            sides = [first, "user" if first == "opp" else "opp",
                     first, "user" if first == "opp" else "user"]
        for s in sides:
            possession_order.append((s, q))

    yardline = {"user": 35, "opp": 35}
    drives_per_team = {"user": 0, "opp": 0}
    MAX_DRIVES_PER_TEAM = 12

    for side, quarter in possession_order:
        if drives_per_team[side] >= MAX_DRIVES_PER_TEAM:
            continue
        start = yardline[side]
        _, end_yl = simulate_drive(side, start, quarter)
        opp_side = "opp" if side == "user" else "user"
        yardline[opp_side] = end_yl
        drives_per_team[side] += 1

    if opp_quality != 1.0:
        for pstats in opp_stats.values():
            for stat in ("passing_yards", "rushing_yards", "receptions", "receiving_yards"):
                if stat in pstats:
                    pstats[stat] *= opp_quality

    _TACKLE_MEAN_BY_POS = {
        "DE": 4.0, "DT": 3.0, "NT": 3.5,
        "LB": 7.0, "OLB": 6.0, "ILB": 8.0, "MLB": 8.0,
        "CB": 4.5, "FS": 5.0, "SS": 5.5, "S": 5.0, "SAF": 5.0,
        "Nickel": 4.0, "Dime": 3.5,
    }
    def _distribute_tackles(player_df: pd.DataFrame):
        defenders = [p for p in user_team["players"] if p["position"] in _TACKLE_MEAN_BY_POS]
        if not defenders:
            return

        weights = []
        for p in defenders:
            rows = player_df[player_df["player_display_name"] == p["name"]] if not player_df.empty else pd.DataFrame()
            if not rows.empty and "def_tackles_solo" in rows.columns:
                hist = pd.to_numeric(rows["def_tackles_solo"], errors="coerce").sum()
                games = len(rows)
                per_game = float(hist / games) if games > 0 and hist > 0 else _TACKLE_MEAN_BY_POS[p["position"]]
            else:
                per_game = _TACKLE_MEAN_BY_POS[p["position"]]
            weights.append(max(per_game, 0.5))

        total_weight = sum(weights)
        total_tackles = max(20, int(np.random.normal(38, 6)))

        for p, w in zip(defenders, weights):
            share = w / total_weight
            raw = np.random.normal(share * total_tackles, share * total_tackles * 0.25)
            tackles = max(0, round(raw))
            existing = user_stats.get(p["name"], {}).get("def_tackles_solo", 0)
            if p["name"] not in user_stats:
                user_stats[p["name"]] = {}
            user_stats[p["name"]]["def_tackles_solo"] = existing + tackles

    _distribute_tackles(user_player_df)

    return user_stats, opp_stats, play_log, user_score, opp_score


def _passer_rating(yards: float, tds: float, ints: float, attempts: float) -> float:
    if attempts < 1:
        return 0.0
    comp_pct = 0.63
    a = max(0.0, min((comp_pct - 0.3) * 5, 2.375))
    b = max(0.0, min((yards / attempts - 3) * 0.25, 2.375))
    c = max(0.0, min((tds / attempts) * 20, 2.375))
    d = max(0.0, min(2.375 - (ints / attempts) * 25, 2.375))
    return round(((a + b + c + d) / 6) * 100, 1)


def build_box_score(user_game: dict, team_players: list) -> list[dict]:
    POS_ORDER = ["QB", "RB", "FB", "WR", "TE", "K", "RS",
                 "DE", "DT", "NT", "LB", "OLB", "ILB", "MLB", "CB", "FS", "SS", "S", "SAF", "Nickel", "Dime"]

    INT_STATS = {
        "carries", "rushing_yards", "rushing_tds",
        "receptions", "targets", "receiving_yards", "receiving_tds",
        "passing_yards", "passing_tds", "passing_interceptions",
        "def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended",
        "fg_made", "fg_att", "xp_made", "xp_att",
        "punts", "punt_yards",
        "kickoff_returns", "kickoff_return_yards", "kickoff_return_tds",
        "punt_returns", "punt_return_yards", "punt_return_tds",
    }

    MIN_THRESHOLDS = {
        "carries": 1, "rushing_yards": 2, "rushing_tds": 1,
        "receptions": 1, "targets": 1, "receiving_yards": 3, "receiving_tds": 1,
        "passing_yards": 10, "passing_tds": 1, "passing_interceptions": 1,
        "def_tackles_solo": 1, "def_sacks": 1, "def_interceptions": 1, "def_pass_defended": 1,
        "fg_made": 1, "fg_att": 1,
        "kickoff_returns": 1, "kickoff_return_yards": 5, "punt_returns": 1, "punt_return_yards": 3,
    }

    STAT_DISPLAY = {
        "carries": "Car", "rushing_yards": "Rush Yds", "rushing_tds": "Rush TD",
        "receptions": "Rec", "targets": "Tgt", "receiving_yards": "Rec Yds", "receiving_tds": "Rec TD",
        "def_sacks": "Sacks", "def_tackles_solo": "Tackles", "def_interceptions": "INT",
        "def_pass_defended": "PD",
        "fg_made": "FG", "fg_att": "FGA", "fg_pct": "FG%", "xp_made": "XP", "xp_att": "XPA", "xp_pct": "XP%",
        "punts": "Punts", "punt_yards": "Punt Yds",
        "kickoff_returns": "KR", "kickoff_return_yards": "KR Yds", "kickoff_return_tds": "KR TD",
        "punt_returns": "PR", "punt_return_yards": "PR Yds", "punt_return_tds": "PR TD",
    }

    box = []
    sorted_players = sorted(
        team_players,
        key=lambda p: (POS_ORDER.index(p["position"]) if p["position"] in POS_ORDER else 99, p["name"])
    )
    for p in sorted_players:
        name = p["name"]
        pos = "NT" if p["position"] == "DT" else p["position"]
        raw = user_game.get(name, {})
        if pos in ("OL", "OT", "OG", "C", "LS"):
            continue

        stat_lines: dict[str, float | int] = {}

        if pos == "QB":
            pass_yds = round(raw.get("passing_yards", 0))
            pass_tds = round(raw.get("passing_tds", 0))
            ints = round(raw.get("passing_interceptions", 0))
            attempts = round(raw.get("passing_attempts", 0))
            completions = round(raw.get("passing_completions", 0))
            comp_pct = round((completions / attempts * 100), 1) if attempts > 0 else 0.0
            rating = _passer_rating(pass_yds, pass_tds, ints, attempts)
            if attempts > 0:
                stat_lines["Cmp"] = completions
                stat_lines["Att"] = attempts
                stat_lines["Cmp%"] = comp_pct
                stat_lines["Pass Yds"] = pass_yds
                stat_lines["Pass TD"] = pass_tds
                stat_lines["INT"] = ints
                stat_lines["PRAT"] = rating
        elif pos in ("RB", "FB"):
            rb_order = ["carries", "rushing_yards", "rushing_tds", "receptions", "receiving_yards", "receiving_tds"]
            for k in rb_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "WR":
            wr_order = ["targets", "receptions", "receiving_yards", "receiving_tds", "carries", "rushing_yards", "rushing_tds"]
            for k in wr_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "TE":
            te_order = ["targets", "receptions", "receiving_yards", "receiving_tds"]
            for k in te_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos in ("DE", "DT", "NT"):
            dl_order = ["def_tackles_solo", "def_sacks", "def_pass_defended"]
            for k in dl_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos in ("LB", "OLB", "ILB", "MLB"):
            lb_order = ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"]
            for k in lb_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos in ("CB", "FS", "SS", "S", "SAF", "Nickel", "Dime"):
            db_order = ["def_tackles_solo", "def_interceptions", "def_pass_defended"]
            for k in db_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "K":
            fg_made = round(raw.get("fg_made", 0))
            fg_att = round(raw.get("fg_att", 0))
            xp_made = round(raw.get("xp_made", 0))
            xp_att = round(raw.get("xp_att", 0))
            stat_lines["FG"] = fg_made
            stat_lines["FGA"] = fg_att
            stat_lines["FG%"] = round(fg_made / fg_att * 100, 1) if fg_att > 0 else 0.0
            stat_lines["XP"] = xp_made
            stat_lines["XPA"] = xp_att
            stat_lines["XP%"] = round(xp_made / xp_att * 100, 1) if xp_att > 0 else 0.0
        elif pos == "P":
            p_order = ["punts", "punt_yards"]
            for k in p_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "RS":
            rs_order = ["kickoff_returns", "kickoff_return_yards", "kickoff_return_tds",
                        "punt_returns", "punt_return_yards", "punt_return_tds"]
            for k in rs_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        else:
            for k, v in raw.items():
                threshold = MIN_THRESHOLDS.get(k, 0.5)
                if v < threshold:
                    continue
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)

        if stat_lines:
            box.append({"name": name, "position": pos, "nfl_team": p.get("nfl_team", ""), "stats": [{"label": k, "val": v} for k, v in stat_lines.items()]})
    return box


def simulate_overtime_period(
    ot_num: int,
    user_team: dict,
    user_player_df,
    opp_roster: list,
    opp_player_df,
    opp_name: str,
    opp_quality: float,
    playoff_mode: bool,
) -> tuple[dict, dict, list[dict], int, int]:
    """
    Simulate one overtime period (sudden death, 10-min drive series).
    """
    scratch_user_stats: dict = {}
    scratch_opp_stats: dict = {}
    ot_play_log: list = []
    u_score = 0
    o_score = 0

    first = random.choice(["user", "opp"])
    order = [first, "opp" if first == "user" else "user"]

    def _first(players, positions):
        for p in players:
            if p["position"] in positions:
                return p["name"]
        return None

    user_players = user_team["players"]
    user_qb = _first(user_players, {"QB"}) or "QB"
    user_kicker = _first(user_players, {"K"}) or "K"
    user_rushers = [(p["name"], _player_rush_share(p["name"], user_player_df))
                    for p in user_players if p["position"] in ("RB", "FB")]
    user_receivers = [(p["name"], _player_target_share(p["name"], user_player_df, p["position"]))
                      for p in user_players if p["position"] in ("WR", "TE", "RB", "FB")]
    user_sack_pool = [(p["name"], _SACK_WEIGHT.get(p["position"], 1))
                      for p in user_players if p["position"] in _SACK_WEIGHT]
    user_int_pool = [(p["name"], _INT_WEIGHT.get(p["position"], 1))
                     for p in user_players if p["position"] in _INT_WEIGHT]
    user_fumble_pool = [(p["name"], _FUMBLE_WEIGHT.get(p["position"], 1))
                        for p in user_players if p["position"] in _FUMBLE_WEIGHT]
    user_pd_pool = [(p["name"], _PD_WEIGHT.get(p["position"], 1))
                    for p in user_players if p["position"] in _PD_WEIGHT]

    opp_qb = _first(opp_roster, {"QB"}) or f"{opp_name} QB"
    opp_kicker = _first(opp_roster, {"K"}) or f"{opp_name} K"
    opp_rushers = [(p["name"], _player_rush_share(p["name"], opp_player_df))
                   for p in opp_roster if p["position"] in ("RB", "FB")]
    opp_receivers = [(p["name"], _player_target_share(p["name"], opp_player_df, p["position"]))
                     for p in opp_roster if p["position"] in ("WR", "TE", "RB", "FB")]
    opp_sack_pool = [(p["name"], _SACK_WEIGHT.get(p["position"], 1))
                     for p in opp_roster if p["position"] in _SACK_WEIGHT]
    opp_int_pool = [(p["name"], _INT_WEIGHT.get(p["position"], 1))
                    for p in opp_roster if p["position"] in _INT_WEIGHT]
    opp_fumble_pool = [(p["name"], _FUMBLE_WEIGHT.get(p["position"], 1))
                       for p in opp_roster if p["position"] in _FUMBLE_WEIGHT]
    opp_pd_pool = [(p["name"], _PD_WEIGHT.get(p["position"], 1))
                   for p in opp_roster if p["position"] in _PD_WEIGHT]

    _ot_user_pos_map = {p["name"]: p["position"] for p in user_players}
    _ot_opp_pos_map = {p["name"]: p["position"] for p in opp_roster}

    _user_ypc = {n: _player_ypc(n, user_player_df) for n, _ in user_rushers}
    _user_ypr = {n: _player_ypr(n, user_player_df, _ot_user_pos_map.get(n, "WR")) for n, _ in user_receivers}
    _opp_ypc = {n: _player_ypc(n, opp_player_df) for n, _ in opp_rushers}
    _opp_ypr = {n: _player_ypr(n, opp_player_df, _ot_opp_pos_map.get(n, "WR")) for n, _ in opp_receivers}
    user_name = user_team.get("team_name", "Your Team")

    _ot_user_wr = {p["name"] for p in user_players if p["position"] == "WR"}
    _ot_user_te = {p["name"] for p in user_players if p["position"] == "TE"}
    _ot_opp_wr = {p["name"] for p in opp_roster  if p["position"] == "WR"}
    _ot_opp_te = {p["name"] for p in opp_roster  if p["position"] == "TE"}

    def _ot_build_rec_pools(pool, wr_names, te_names):
        groups: dict = {"WR": [], "TE": [], "RB": []}
        for name, w in pool:
            g = "WR" if name in wr_names else ("TE" if name in te_names else "RB")
            groups[g].append((name, max(w, 0.3)))
        result = {}
        for pos, members in groups.items():
            if not members:
                result[pos] = []
                continue
            total = sum(w for _, w in members)
            result[pos] = [(n, w / total) for n, w in members]
        return result

    _ot_user_rec_pools = _ot_build_rec_pools(user_receivers, _ot_user_wr, _ot_user_te)
    _ot_opp_rec_pools = _ot_build_rec_pools(opp_receivers,  _ot_opp_wr,  _ot_opp_te)

    int_scale = 0.80 if playoff_mode else 1.0
    incomp_scale = 0.85 if playoff_mode else 1.0

    def _add(stats_dict, name, **kwargs):
        if name not in stats_dict:
            stats_dict[name] = {}
        for k, v in kwargs.items():
            stats_dict[name][k] = stats_dict[name].get(k, 0) + v

    def _log_ot(team_name: str, text: str, is_score: bool = False):
        ot_play_log.append({
            "quarter": f"OT{ot_num}",
            "team": team_name,
            "play": text,
            "score": f"{u_score}-{o_score}",
            "is_score": is_score,
        })

    def _pick_rusher(pool, ypc_map):
        if not pool: return ("RB", 4.2)
        names, weights = zip(*pool)
        name = random.choices(names, weights=weights, k=1)[0]
        return name, ypc_map.get(name, 4.2)

    def _pick_receiver(pool, ypr_map):
        is_user = (pool is user_receivers)
        group_pools = _ot_user_rec_pools if is_user else _ot_opp_rec_pools
        wr_p = 0.57 if group_pools["WR"] else 0.0
        te_p = 0.22 if group_pools["TE"] else 0.0
        rb_p = 0.21 if group_pools["RB"] else 0.0
        wr_p = float(np.clip(wr_p, 0.58, 0.85)) if group_pools["WR"] else 0.0
        te_p = float(np.clip(te_p, 0.08, 0.22)) if group_pools["TE"] else 0.0
        rb_p = float(np.clip(rb_p, 0.04, 0.10)) if group_pools["RB"] else 0.0
        total = wr_p + te_p + rb_p
        if total <= 0 or not pool:
            return ("WR", 9.5)
        wr_p /= total; te_p /= total; rb_p /= total
        group = random.choices(["WR", "TE", "RB"], weights=[wr_p, te_p, rb_p], k=1)[0]
        members = group_pools.get(group, [])
        if not members:
            for fallback in ["WR", "TE", "RB"]:
                if group_pools.get(fallback):
                    members = group_pools[fallback]
                    break
        if not members:
            return ("WR", 9.5)
        names, weights = zip(*members)
        name = random.choices(names, weights=weights, k=1)[0]
        return name, ypr_map.get(name, 9.5)

    scored = False

    def run_ot_drive(side: str, start_yl: int) -> tuple[bool, int]:
        nonlocal u_score, o_score, scored

        if side == "user":
            qb, kicker = user_qb, user_kicker
            rushers_pool, receivers_pool = user_rushers, user_receivers
            ypc_map, ypr_map = _user_ypc, _user_ypr
            sack_pool, int_pool, fumble_pool, pd_pool = opp_sack_pool, opp_int_pool, opp_fumble_pool, opp_pd_pool
            team_name = user_name
        else:
            qb, kicker = opp_qb, opp_kicker
            rushers_pool, receivers_pool = opp_rushers, opp_receivers
            ypc_map, ypr_map = _opp_ypc, _opp_ypr
            sack_pool, int_pool, fumble_pool, pd_pool = user_sack_pool, user_int_pool, user_fumble_pool, user_pd_pool
            team_name = opp_name

        down, ytg, yardline = 1, 10, start_yl
        plays_run = 0

        while plays_run < 20:
            bucket = _dist_bucket(ytg)
            run_prob = _RUN_PROB.get((down, bucket), 0.40)
            run_prob = float(np.clip(run_prob, 0.05, 0.90))
            is_run = random.random() < run_prob
            plays_run += 1

            if is_run:
                rusher, ypc = _pick_rusher(rushers_pool, ypc_map)
                yards = int(np.clip(round(np.random.normal(ypc, _RUN_YARDS_STD)), -3, 35))
                fumble_p = _FUMBLE_PROB
                if random.random() < fumble_p:
                    strip_def = _weighted_pick(fumble_pool)
                    text = _pick_template("fumble_forced" if side == "user" else "opp_fumble_forced",
                                          defender=strip_def, rusher=rusher)
                    _log_ot(team_name, text)
                    return False, 100 - max(20, yardline + yards)
                if side == "user":
                    _add(scratch_user_stats, rusher, carries=1, rushing_yards=max(0, yards))
                else:
                    _add(scratch_opp_stats, rusher, carries=1, rushing_yards=max(0, yards))
                yardline += yards
            else:
                int_prob = _INT_PROB * int_scale
                incomp_prob = _INCOMP_PROB * incomp_scale
                if random.random() < _SACK_PROB:
                    sacker = _weighted_pick(sack_pool)
                    sack_yds = random.randint(5, 12)
                    if side == "user":
                        _add(scratch_opp_stats, sacker, def_sacks=1)
                    else:
                        _add(scratch_user_stats, sacker, def_sacks=1)
                    text = _pick_template("sack" if side == "user" else "opp_sack", defender=sacker, qb=qb)
                    _log_ot(team_name, text)
                    yardline -= sack_yds
                    yards = -sack_yds
                elif random.random() < int_prob:
                    interceptor = _weighted_pick(int_pool)
                    receiver, _ = _pick_receiver(receivers_pool, ypr_map)
                    if side == "user":
                        _add(scratch_opp_stats, interceptor, def_interceptions=1)
                    else:
                        _add(scratch_user_stats, interceptor, def_interceptions=1)
                    text = _pick_template("interception" if side == "opp" else "opp_interception", defender=interceptor, qb=qb, receiver=receiver)
                    _log_ot(team_name, text)
                    return False, 100 - max(20, yardline)
                elif random.random() < incomp_prob:
                    receiver, _ = _pick_receiver(receivers_pool, ypr_map)
                    pd_def = _weighted_pick(pd_pool)
                    if side == "user":
                        _add(scratch_opp_stats, pd_def, def_pass_defended=1)
                    else:
                        _add(scratch_user_stats, pd_def, def_pass_defended=1)
                    yards = 0
                else:
                    receiver, ypr = _pick_receiver(receivers_pool, ypr_map)
                    yards = int(np.clip(round(np.random.normal(ypr, _PASS_YARDS_STD)), 1, 55))
                    if side == "user":
                        _add(scratch_user_stats, qb, passing_yards=yards)
                        _add(scratch_user_stats, receiver, receptions=1, receiving_yards=yards)
                    else:
                        _add(scratch_opp_stats, qb, passing_yards=yards)
                        _add(scratch_opp_stats, receiver, receptions=1, receiving_yards=yards)
                    if yards >= 20:
                        tmpl = "pass_complete" if side == "user" else "opp_pass_complete"
                        _log_ot(team_name, _pick_template(tmpl, qb=qb, receiver=receiver, yards=yards))
                    yardline += yards

            if yardline >= 100:
                is_rush_td = random.random() < 0.40
                rusher_name, _ = _pick_rusher(rushers_pool, ypc_map)
                rec_name, _    = _pick_receiver(receivers_pool, ypr_map)
                scorer = rusher_name if is_rush_td else rec_name
                td_yards = max(1, min(yards, 20))
                if side == "user":
                    u_score += 7
                    text = _pick_template("rushing_td" if is_rush_td else "passing_td",
                                          **{"rusher": scorer, "yards": td_yards} if is_rush_td
                                          else {"qb": qb, "receiver": scorer, "yards": td_yards})
                else:
                    o_score += 7
                    text = _pick_template("opp_rushing_td" if is_rush_td else "opp_passing_td",
                                          **{"rusher": scorer, "yards": td_yards, "team": opp_name} if is_rush_td
                                          else {"qb": qb, "receiver": scorer, "yards": td_yards, "team": opp_name})
                _log_ot(team_name, text, is_score=True)
                scored = True
                return True, 35

            if yardline <= 0:
                yardline, down, ytg = 5, 1, 10
                continue
            if yards >= ytg:
                down, ytg = 1, 10
            else:
                ytg -= yards
                down += 1

            if down == 4:
                dist_to_goal = 100 - yardline
                if dist_to_goal <= 52 and random.random() < _FG_ATTEMPT_DIST:
                    make_p = _fg_make_prob(dist_to_goal + 17)
                    if random.random() < make_p:
                        if side == "user":
                            u_score += 3
                            _add(scratch_user_stats, kicker, fg_made=1, fg_att=1)
                        else:
                            o_score += 3
                            _add(scratch_opp_stats, kicker, fg_made=1, fg_att=1)
                        text = _pick_template("fg_good" if side == "user" else "opp_fg_good",
                                              kicker=kicker, yards=dist_to_goal + 17, team=team_name)
                        _log_ot(team_name, text, is_score=True)
                        scored = True
                        return True, 35
                    else:
                        text = _pick_template("fg_miss" if side == "user" else "opp_fg_miss",
                                              kicker=kicker, yards=dist_to_goal + 17, team=team_name)
                        _log_ot(team_name, text)
                        return False, max(20, 100 - yardline - 5)
                else:
                    net_yds = random.randint(28, 46)
                    tmpl = "punt" if side == "user" else "opp_punt"
                    _log_ot(team_name, _pick_template(tmpl, team=team_name))
                    return False, max(15, 100 - yardline - net_yds)

        return False, 35

    yl = {"user": 35, "opp": 35}
    max_drives = 20
    drive_count = 0
    while not scored and drive_count < max_drives:
        for side in order:
            if scored:
                break
            s_yl = yl[side]
            did_score, new_yl = run_ot_drive(side, s_yl)
            opp_side = "opp" if side == "user" else "user"
            yl[opp_side] = new_yl
            drive_count += 1
            if did_score:
                break

    return scratch_user_stats, scratch_opp_stats, ot_play_log, u_score, o_score


def run_game_simulation(team_id: str, nfl_opponent: str, season: int, is_home: bool = True, playoff_mode: bool = False) -> dict:
    _POS_STATS_CACHE.clear()

    team = get_generated_team(team_id)
    if not team:
        raise ValueError(f"Team {team_id} not found")

    user_player_names = [p["name"] for p in team["players"]]
    user_player_df = fetch_player_stats(user_player_names)

    opp_roster = fetch_nfl_roster(nfl_opponent, season)
    if not opp_roster:
        raise ValueError(f"No roster data found for {nfl_opponent} in {season}")
    opp_player_names = [p["name"] for p in opp_roster]
    opp_player_df = fetch_player_stats(opp_player_names)
    opp_team_stats = fetch_team_season_stats(nfl_opponent, season)
    opp_quality = 1.0

    if not opp_team_stats.empty:
        avg_pass = float(opp_team_stats["passing_yards"].mean()) if "passing_yards" in opp_team_stats.columns else 230
        avg_rush = float(opp_team_stats["rushing_yards"].mean()) if "rushing_yards" in opp_team_stats.columns else 115
        opp_quality = float(np.clip((avg_pass / 230 + avg_rush / 115) / 2, 0.80, 1.25))

    if playoff_mode:
        opp_quality = float(np.clip(opp_quality * 1.15, 0.80, 1.40))

    location_boost = 1.04 if is_home else 0.96

    user_stats, _opp_stats, play_log, user_score, opp_score = simulate_game_drives(
        user_team=team,
        user_player_df=user_player_df,
        opp_roster=opp_roster,
        opp_player_df=opp_player_df,
        opp_name=nfl_opponent,
        opp_quality=opp_quality,
        season=season,
    )

    if location_boost != 1.0:
        for pstats in user_stats.values():
            for stat in ("passing_yards", "rushing_yards", "receptions", "receiving_yards", "carries"):
                if stat in pstats:
                    pstats[stat] *= location_boost

    if user_score == opp_score and random.random() < 0.88:
        if random.random() < 0.5:
            user_score += random.choice([3, 7])
        else:
            opp_score += random.choice([3, 7])

    overtime_periods = 0

    if user_score == opp_score:
        max_ot = 10 if playoff_mode else 1
        for ot_num in range(1, max_ot + 1):
            ot_u_stats, _, ot_log, ot_u_delta, ot_o_delta = simulate_overtime_period(
                ot_num=ot_num,
                user_team=team,
                user_player_df=user_player_df,
                opp_roster=opp_roster,
                opp_player_df=opp_player_df,
                opp_name=nfl_opponent,
                opp_quality=opp_quality,
                playoff_mode=playoff_mode,
            )
            overtime_periods += 1
            user_score += ot_u_delta
            opp_score += ot_o_delta
            for name, stats in ot_u_stats.items():
                if name not in user_stats:
                    user_stats[name] = {}
                for k, v in stats.items():
                    user_stats[name][k] = user_stats[name].get(k, 0) + v
            play_log.extend(ot_log)
            if user_score != opp_score:
                break
            if not playoff_mode:
                break

    user_name = team.get("team_name", "Your Team")
    winner = user_name if user_score > opp_score else (nfl_opponent if opp_score > user_score else "TIE")

    box = build_box_score(user_stats, team["players"])

    return {
        "user_team": user_name,
        "opponent": nfl_opponent,
        "season": season,
        "is_home": is_home,
        "playoff_mode": playoff_mode,
        "overtime_periods": overtime_periods,
        "final_score": {"user": user_score, "opponent": opp_score},
        "winner": winner,
        "play_by_play": play_log,
        "box_score": box,
    }


app = FastAPI()

class SimulateGameRequest(BaseModel):
    team_id: str
    nfl_opponent: str
    season: int
    is_home: bool = True
    playoff_mode: bool = False

@app.post("/simulate-game")
async def simulate_game_endpoint(req: SimulateGameRequest):
    try:
        result = run_game_simulation(req.team_id, req.nfl_opponent, req.season, req.is_home, req.playoff_mode)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simulate_game:app", host="0.0.0.0", port=8006, reload=False)
