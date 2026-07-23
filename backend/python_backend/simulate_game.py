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
import certifi

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
    "TE": {"receptions": 12, "receiving_yards": 180, "receiving_tds": 3, "targets": 14},
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
    "K": {"fg_made": 40, "fg_att": 50},
    "RS": {"kickoff_return_yards": 550, "kickoff_returns": 30, "punt_return_yards": 400, "punt_returns": 35},
}

# Slot 1 gets a boost above raw population mean because the population mean is diluted
# by backups, committee backs, and injured players. The starter is above average by definition.
DEPTH_SLOT_SCALE = {1: 1.35, 2: 0.50, 3: 0.30}

# Per-position starter multiplier — some positions (RB carry volume) are even more skewed
# toward the starter, so apply an additional boost on top of DEPTH_SLOT_SCALE for slot 1.
_STARTER_BOOST: dict[str, float] = {
    "RB": 1.25,  # RB1 starter gets ~25% more carries/yards than DEPTH_SLOT_SCALE alone gives
    "FB": 1.10,
    "WR": 1.15,  # WR1 target share is concentrated
    "TE": 1.10,
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


DEF_POSITIONS = {"DE", "DT", "NT", "LB", "OLB", "ILB", "MLB", "CB", "FS", "SS", "S", "SAF"}

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


def _player_ypr(name: str, player_df: pd.DataFrame, default: float = 10.0) -> float:
    if player_df.empty:
        return default
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return default
    recs = pd.to_numeric(rows.get("receptions", pd.Series()), errors="coerce").sum()
    rec_yds = pd.to_numeric(rows.get("receiving_yards", pd.Series()), errors="coerce").sum()
    if recs < 5:
        return default
    return float(np.clip(rec_yds / recs, 4.0, 22.0))


def _player_target_share(name: str, player_df: pd.DataFrame, pos: str) -> float:
    """Season target total — used as relative weight for target distribution."""
    POS_DEFAULT = {"WR": 80.0, "TE": 55.0, "RB": 35.0, "FB": 15.0}
    if player_df.empty:
        return POS_DEFAULT.get(pos, 30.0)
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return POS_DEFAULT.get(pos, 30.0)
    tgts = pd.to_numeric(rows.get("targets", pd.Series()), errors="coerce").sum()
    return float(tgts) if tgts >= 5 else POS_DEFAULT.get(pos, 30.0)


def _player_rush_share(name: str, player_df: pd.DataFrame) -> float:
    """Season carry total — used as relative weight for rush distribution."""
    if player_df.empty:
        return 100.0
    rows = player_df[player_df["player_display_name"] == name]
    if rows.empty:
        return 100.0
    carries = pd.to_numeric(rows.get("carries", pd.Series()), errors="coerce").sum()
    return float(carries) if carries >= 10 else 50.0


# ─── Play-call probabilities calibrated from real ESPN play-by-play data ───
# Source: Bills-Jags (145 plays) and Colts-Dolphins (135 plays) full PBP
_RUN_PROB = {
    # (down, distance_bucket) -> run probability
    # distance_bucket: "short"=1-3, "medium"=4-7, "long"=8+
    (1, "short"):  0.48,
    (1, "medium"): 0.45,
    (1, "long"):   0.40,
    (2, "short"):  0.52,
    (2, "medium"): 0.38,
    (2, "long"):   0.22,
    (3, "short"):  0.42,
    (3, "medium"): 0.18,
    (3, "long"):   0.10,
    (4, "short"):  0.55,
    (4, "medium"): 0.25,
    (4, "long"):   0.10,
}

_SACK_PROB = 0.055        # 5.5% of pass plays result in sack
_INT_PROB  = 0.025        # 2.5% of pass plays result in INT
_INCOMP_PROB = 0.30       # 30% of pass plays incomplete
_FUMBLE_PROB = 0.008      # 0.8% of run plays result in fumble lost

# Yards distributions calibrated from PBP data
_RUN_YARDS_MEAN = 4.2
_RUN_YARDS_STD  = 4.5
_PASS_YARDS_MEAN = 9.5
_PASS_YARDS_STD  = 8.0

# Drive terminal outcomes — probability mass once a drive stalls on 4th down
_FG_ATTEMPT_DIST = 0.55   # if in FG range (≤52 yds) and 4th down, attempt FG vs punt
_FG_MAKE_PROB_BASE = 0.87  # base FG make rate (adjusted by distance)

_SACK_WEIGHT = {"DE": 5, "DT": 4, "NT": 3, "OLB": 3, "LB": 1, "ILB": 1, "MLB": 1}
_INT_WEIGHT  = {"CB": 4, "FS": 2, "SS": 2, "S": 2, "SAF": 2}

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
        "Pressure up the middle — {defender} gets home and sacks {qb}!",
        "{defender} strips {qb} on the sack... fumble recovered by the offense.",
    ],
    "interception": [
        "{defender} reads the route and picks off {qb}! Turnover!",
        "Tipped at the line... {defender} comes down with the PICK!",
        "{defender} undercuts the route — INTERCEPTION!",
    ],
    "rushing_td": [
        "{rusher} punches it in from {yards} yards! TOUCHDOWN!",
        "{rusher} breaks a tackle and scores from {yards} out! TD!",
        "{rusher} up the gut from {yards} yards — TOUCHDOWN!",
        "{rusher} fights through the pile and scores! {yards}-yard TD!",
    ],
    "passing_td": [
        "{qb} fires to {receiver} in the end zone — TOUCHDOWN! {yards} yards!",
        "{qb} threads the needle to {receiver} for a {yards}-yard TD!",
        "Beautiful throw from {qb}, {receiver} hauls it in for a {yards}-yard score!",
        "{qb} rolls out and finds {receiver} for a {yards}-yard TOUCHDOWN!",
    ],
    "fg_good": [
        "{kicker} lines it up from {yards} yards... it's GOOD! 3 points.",
        "Field goal by {kicker} from {yards} yards — right down the middle!",
        "{kicker} splits the uprights from {yards}. 3 more on the board.",
    ],
    "fg_miss": [
        "{kicker} pulls it wide left from {yards}. No good.",
        "{kicker}'s {yards}-yard attempt misses right. No good.",
        "The kick is off — {kicker} misses from {yards} yards.",
    ],
    "punt": [
        "Offense stalls. Punting unit takes the field.",
        "Can't convert on third down — punt.",
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
        "{defender} picks off {qb}! Huge turnover for your team!",
        "{defender} reads it perfectly — INTERCEPTION!",
    ],
    "opp_rushing_td": [
        "{rusher} scores from {yards} yards out! TD for {team}!",
        "{rusher} punches it in — {yards}-yard TD run for {team}!",
    ],
    "opp_passing_td": [
        "{qb} connects with {receiver} for a {yards}-yard TD! {team} scores!",
        "{qb} fires to {receiver} in the end zone — TOUCHDOWN for {team}!",
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
    # NFL averages: ~93% <30, ~87% 30-39, ~79% 40-49, ~60% 50-59, ~40% 60+
    if distance < 30:   return 0.93
    if distance < 40:   return 0.87
    if distance < 50:   return 0.79
    if distance < 60:   return 0.60
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
) -> tuple[dict, dict, list[dict], int, int]:
    """
    Drive-based game simulation. Returns:
      (user_game_stats, opp_game_stats, play_log, user_score, opp_score)
    where *_game_stats are dicts of {player_name: {stat: value}}.
    """

    # ── Roster lookups ──────────────────────────────────────────────────────
    def _first(players, positions):
        for p in players:
            if p["position"] in positions:
                return p["name"]
        return None

    user_players = user_team["players"]
    user_qb       = _first(user_players, {"QB"}) or "QB"
    user_kicker   = _first(user_players, {"K"})  or "K"
    user_punter   = _first(user_players, {"P"})  or None
    user_returner = _first(user_players, {"RS"}) or None
    user_rushers = [(p["name"], _player_rush_share(p["name"], user_player_df))
                    for p in user_players if p["position"] in ("RB", "FB")]
    user_receivers = [(p["name"], _player_target_share(p["name"], user_player_df, p["position"]))
                      for p in user_players if p["position"] in ("WR", "TE", "RB", "FB")]
    user_sack_pool = [(p["name"], _SACK_WEIGHT.get(p["position"], 1))
                      for p in user_players if p["position"] in _SACK_WEIGHT]
    user_int_pool  = [(p["name"], _INT_WEIGHT.get(p["position"], 1))
                      for p in user_players if p["position"] in _INT_WEIGHT]

    opp_qb      = _first(opp_roster, {"QB"}) or f"{opp_name} QB"
    opp_kicker  = _first(opp_roster, {"K"})  or f"{opp_name} K"
    opp_rushers = [(p["name"], _player_rush_share(p["name"], opp_player_df))
                   for p in opp_roster if p["position"] in ("RB", "FB")]
    opp_receivers = [(p["name"], _player_target_share(p["name"], opp_player_df, p["position"]))
                     for p in opp_roster if p["position"] in ("WR", "TE", "RB", "FB")]
    opp_sack_pool = [(p["name"], _SACK_WEIGHT.get(p["position"], 1))
                     for p in opp_roster if p["position"] in _SACK_WEIGHT]
    opp_int_pool  = [(p["name"], _INT_WEIGHT.get(p["position"], 1))
                     for p in opp_roster if p["position"] in _INT_WEIGHT]

    # ── Per-player YPC / YPR lookup helpers ─────────────────────────────────
    _user_ypc = {n: _player_ypc(n, user_player_df) for n, _ in user_rushers}
    _user_ypr = {n: _player_ypr(n, user_player_df)
                 for n, _ in user_receivers}
    _opp_ypc  = {n: _player_ypc(n, opp_player_df)  for n, _ in opp_rushers}
    _opp_ypr  = {n: _player_ypr(n, opp_player_df)
                 for n, _ in opp_receivers}

    def _pick_rusher(pool):
        if not pool: return ("RB", 4.2)
        names, weights = zip(*pool)
        name = random.choices(names, weights=weights, k=1)[0]
        return name, _user_ypc.get(name, _opp_ypc.get(name, 4.2))

    def _pick_receiver(pool, ypr_map):
        if not pool: return ("WR", 9.5)
        names, weights = zip(*pool)
        name = random.choices(names, weights=weights, k=1)[0]
        return name, ypr_map.get(name, 9.5)

    # ── Stat accumulators ────────────────────────────────────────────────────
    # Pre-seed every player with zero stats so they always appear in box score
    _DEF_ZERO = {"def_tackles_solo": 0, "def_sacks": 0, "def_interceptions": 0, "def_pass_defended": 0}
    _DL_ZERO  = {"def_tackles_solo": 0, "def_sacks": 0, "def_pass_defended": 0}
    _DB_ZERO  = {"def_tackles_solo": 0, "def_interceptions": 0, "def_pass_defended": 0}
    _POS_ZERO = {
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

    def _add(stats_dict, name, **kwargs):
        if name not in stats_dict:
            stats_dict[name] = {}
        for k, v in kwargs.items():
            stats_dict[name][k] = stats_dict[name].get(k, 0) + v

    # ── Play log ─────────────────────────────────────────────────────────────
    play_log: list[dict] = []
    user_score = 0
    opp_score  = 0

    def _log(quarter: int, team: str, text: str, is_score: bool = False):
        play_log.append({
            "quarter": f"Q{quarter}",
            "team": team,
            "play": text,
            "score": f"{user_score}-{opp_score}",
            "is_score": is_score,
        })

    # ── Single play execution ────────────────────────────────────────────────
    user_name = user_team.get("team_name", "Your Team")

    def run_play(side: str, down: int, ytg: int, quarter: int, score_diff: int) -> tuple[int, str, bool]:
        """
        Execute one play. Returns (yards_gained, terminal_event, is_highlight).
        terminal_event: "" | "td" | "int" | "fumble"
        """
        bucket = _dist_bucket(ytg)

        # Game-script: trailing team passes more in Q4
        run_prob = _RUN_PROB.get((down, bucket), 0.40)
        if score_diff < -10 and quarter >= 4:
            run_prob *= 0.60   # desperation passing mode
        if score_diff > 10 and quarter >= 4:
            run_prob *= 1.35   # clock-killing run mode
        run_prob = float(np.clip(run_prob, 0.05, 0.90))

        is_run = random.random() < run_prob

        if side == "user":
            qb = user_qb
            rushers_pool = user_rushers
            receivers_pool = user_receivers
            ypr_map = _user_ypr
            sack_pool = opp_sack_pool
            int_pool  = opp_int_pool
            name = user_name
        else:
            qb = opp_qb
            rushers_pool = opp_rushers
            receivers_pool = opp_receivers
            ypr_map = _opp_ypr
            sack_pool = user_sack_pool
            int_pool  = user_int_pool
            name = opp_name

        is_highlight = False

        if is_run:
            rusher, ypc = _pick_rusher(rushers_pool if side == "user" else [(n, w) for n, w in opp_rushers])
            raw_yards = np.random.normal(ypc, _RUN_YARDS_STD)
            yards = int(np.clip(round(raw_yards), -3, 25))
            is_highlight = yards >= 12

            # Fumble?
            if random.random() < _FUMBLE_PROB:
                if side == "user":
                    _add(user_stats, rusher, carries=1, rushing_yards=max(0, yards))
                else:
                    _add(opp_stats, rusher, carries=1, rushing_yards=max(0, yards))
                    defender = _weighted_pick(user_sack_pool)
                    _add(user_stats, defender, def_tackles_solo=1)
                tmpl = "opp_run" if side == "opp" else "run"
                text = f"FUMBLE! {rusher} loses the ball — defense recovers. Turnover!"
                _log(quarter, name, text)
                return yards, "fumble", True

            if side == "user":
                _add(user_stats, rusher, carries=1, rushing_yards=max(0, yards))
            else:
                _add(opp_stats, rusher, carries=1, rushing_yards=max(0, yards))

            if is_highlight:
                tmpl = "run" if side == "user" else "opp_run"
                text = _pick_template(tmpl, rusher=rusher, yards=abs(yards))
                _log(quarter, name, text)
            return yards, "", is_highlight

        else:
            # Pass play
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

            if random.random() < _INT_PROB:
                interceptor = _weighted_pick(int_pool)
                if side == "opp":
                    _add(user_stats, interceptor, def_interceptions=1, def_pass_defended=1)
                else:
                    _add(opp_stats, interceptor, def_interceptions=1, def_pass_defended=1)
                tmpl = "interception" if side == "opp" else "opp_interception"
                text = _pick_template(tmpl, defender=interceptor, qb=qb)
                _log(quarter, name, text, is_score=False)
                return 0, "int", True

            if random.random() < _INCOMP_PROB:
                receiver, _ = _pick_receiver(receivers_pool, ypr_map)
                if side == "user":
                    _add(user_stats, qb, passing_yards=0)
                    _add(user_stats, receiver, targets=1)
                else:
                    _add(opp_stats, qb, passing_yards=0)
                    _add(opp_stats, receiver, targets=1)
                return 0, "", False

            # Completion
            receiver, ypr = _pick_receiver(receivers_pool, ypr_map)
            raw_yards = np.random.normal(ypr, _PASS_YARDS_STD)
            yards = int(np.clip(round(raw_yards), 1, 55))
            is_highlight = yards >= 20

            if side == "user":
                _add(user_stats, qb, passing_yards=yards)
                _add(user_stats, receiver, receptions=1, targets=1, receiving_yards=yards)
            else:
                _add(opp_stats, qb, passing_yards=yards)
                _add(opp_stats, receiver, receptions=1, targets=1, receiving_yards=yards)

            if is_highlight:
                tmpl = "pass_complete" if side == "user" else "opp_pass_complete"
                text = _pick_template(tmpl, qb=qb, receiver=receiver, yards=yards)
                _log(quarter, name, text)
            return yards, "", is_highlight

    XP_MAKE_PROB = 0.944  # NFL average XP make rate

    def score_td(side: str, quarter: int, how: str, rusher_or_receiver: str = "", yards: int = 5):
        nonlocal user_score, opp_score
        if side == "user":
            user_score += 6
            if how == "rush":
                _add(user_stats, rusher_or_receiver, rushing_tds=1)
                text = _pick_template("rushing_td", rusher=rusher_or_receiver, yards=yards)
            else:
                _add(user_stats, user_qb, passing_tds=1)
                _add(user_stats, rusher_or_receiver, receiving_tds=1)
                text = _pick_template("passing_td", qb=user_qb, receiver=rusher_or_receiver, yards=yards)
            _log(quarter, user_name, text, is_score=True)
            # Extra point
            _add(user_stats, user_kicker, xp_att=1)
            if random.random() < XP_MAKE_PROB:
                user_score += 1
                _add(user_stats, user_kicker, xp_made=1)
        else:
            opp_score += 6
            if how == "rush":
                _add(opp_stats, rusher_or_receiver, rushing_tds=1)
                text = _pick_template("opp_rushing_td", rusher=rusher_or_receiver, yards=yards, team=opp_name)
            else:
                _add(opp_stats, opp_qb, passing_tds=1)
                _add(opp_stats, rusher_or_receiver, receiving_tds=1)
                text = _pick_template("opp_passing_td", qb=opp_qb, receiver=rusher_or_receiver, yards=yards, team=opp_name)
            _log(quarter, opp_name, text, is_score=True)
            if random.random() < XP_MAKE_PROB:
                opp_score += 1

    def attempt_fg(side: str, quarter: int, distance: int):
        nonlocal user_score, opp_score
        if side == "user":
            kicker = user_kicker
            team = user_name
        else:
            kicker = opp_kicker
            team = opp_name
        make_prob = _fg_make_prob(distance)
        if random.random() < make_prob:
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

    # ── Punt + return helper ─────────────────────────────────────────────────
    # Punt return TD: ~1 per 200 punt returns in real NFL ≈ 0.005 per return.
    # Kickoff return TD: ~1 per 250 kickoff returns ≈ 0.004 per return.
    # Both are already rare; we apply an additional 0.02 multiplier so across
    # a full season of simulated games it feels like a once-a-year surprise.
    _PUNT_RET_TD_PROB  = 0.005 * 0.02   # ≈ 0.0001
    _KO_RET_TD_PROB    = 0.004 * 0.02   # ≈ 0.00008

    def _do_punt(side: str, yardline: int, quarter: int) -> int:
        """Log punt stats, maybe a return TD, return next possession yardline."""
        punt_yds = random.randint(38, 58)
        if side == "user" and user_punter:
            _add(user_stats, user_punter, punts=1, punt_yards=punt_yds)

        # Receiving team's returner handles the punt return
        if side == "opp" and user_returner:
            ret_yds = random.randint(5, 14)
            if random.random() < _PUNT_RET_TD_PROB:
                nonlocal user_score
                user_score += 7
                _add(user_stats, user_returner, punt_returns=1, punt_return_yards=100, punt_return_tds=1)
                _log(quarter, user_name, f"{user_returner} takes the punt return ALL THE WAY — TOUCHDOWN! 🏈", is_score=True)
                return 25
            _add(user_stats, user_returner, punt_returns=1, punt_return_yards=ret_yds)

        net_yds = punt_yds - random.randint(5, 12)
        return max(15, 100 - yardline - net_yds)

    def _do_kickoff_return(quarter: int) -> None:
        """Credit the returner for a kickoff return, with infinitesimal TD chance."""
        if not user_returner:
            return
        ret_yds = random.randint(18, 32)
        if random.random() < _KO_RET_TD_PROB:
            nonlocal user_score
            user_score += 7
            _add(user_stats, user_returner, kickoff_returns=1, kickoff_return_yards=100, kickoff_return_tds=1)
            _log(quarter, user_name, f"{user_returner} returns the kickoff for a TOUCHDOWN!", is_score=True)
        else:
            _add(user_stats, user_returner, kickoff_returns=1, kickoff_return_yards=ret_yds)

    # ── Drive simulation ─────────────────────────────────────────────────────
    def simulate_drive(side: str, start_yardline: int, quarter: int) -> tuple[int, int]:
        """Simulate a full drive. Returns (ending_quarter, final_yardline)."""
        down = 1
        ytg  = 10
        yardline = start_yardline   # yards from own end zone (0=own goal, 100=opp goal)
        plays_run = 0
        MAX_PLAYS = 20

        while plays_run < MAX_PLAYS:
            score_diff = (user_score - opp_score) if side == "user" else (opp_score - user_score)
            yards, event, _ = run_play(side, down, ytg, quarter, score_diff)
            plays_run += 1
            yardline += yards

            # Touchdown
            if yardline >= 100:
                td_yards = max(1, yards)
                if side == "user":
                    rusher_name, _ = _pick_rusher(user_rushers)
                    rec_name, _    = _pick_receiver(user_receivers, _user_ypr)
                else:
                    rusher_name, _ = _pick_rusher([(n, w) for n, w in opp_rushers])
                    rec_name, _    = _pick_receiver(opp_receivers, _opp_ypr)
                # Decide rush vs pass TD based on field position and down
                bucket = _dist_bucket(ytg)
                is_rush_td = random.random() < _RUN_PROB.get((down, bucket), 0.40)
                scorer = rusher_name if is_rush_td else rec_name
                score_td(side, quarter, "rush" if is_rush_td else "pass", scorer, min(td_yards, 20))
                if side == "opp":
                    _do_kickoff_return(quarter)
                return quarter, 25

            # Turnover
            if event == "int" or event == "fumble":
                return quarter, 100 - max(20, yardline)   # opponent gets ball

            # Safety (ball behind own goal line)
            if yardline <= 0:
                yardline = 5
                down = 1
                ytg = 10
                continue

            # Made first down
            if yards >= ytg:
                down = 1
                ytg  = 10
            else:
                ytg  -= yards
                down += 1

            # 4th down decision
            if down == 4:
                dist_to_goal = 100 - yardline
                if dist_to_goal <= 52 and random.random() < _FG_ATTEMPT_DIST:
                    attempt_fg(side, quarter, dist_to_goal + 17)
                    if side == "opp":
                        _do_kickoff_return(quarter)
                    return quarter, 25
                else:
                    return quarter, _do_punt(side, yardline, quarter)

        # Drive ran too long — force punt
        return quarter, _do_punt(side, yardline, quarter)

    # ── Game loop ────────────────────────────────────────────────────────────
    # Typical NFL game: 11-12 drives per team (22-24 total), ~4 per quarter
    # We simulate quarter by quarter and alternate possession
    possession_order = []
    for q in range(1, 5):
        # Each quarter has ~2 drives per team; coin flip for who gets first in Q3
        if q == 1:
            sides = ["user", "opp", "user", "opp"]
        elif q == 3:
            sides = random.choice([["opp", "user", "opp", "user"],
                                   ["user", "opp", "user", "opp"]])
        else:
            # Continue alternating from where Q left off
            last = possession_order[-1][0] if possession_order else "user"
            first = "opp" if last == "user" else "user"
            sides = [first, "user" if first == "opp" else "opp",
                     first, "user" if first == "opp" else "user"]
        for s in sides:
            possession_order.append((s, q))

    yardline = {"user": 25, "opp": 25}
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

    # ── Apply opp quality factor to opp offensive stats ──────────────────────
    if opp_quality != 1.0:
        for pstats in opp_stats.values():
            for stat in ("passing_yards", "rushing_yards", "receptions", "receiving_yards"):
                if stat in pstats:
                    pstats[stat] *= opp_quality

    # ── Distribute realistic tackle counts across all defenders ──────────────
    # The drive sim only assigns tackles on sacks/INTs/fumbles — every other
    # defender stays at 0. We fix this by distributing a realistic total tackle
    # count across all defenders weighted by their historical tackle averages.
    # Typical NFL game: ~120-140 total tackles split across both teams → ~60-70
    # per team, but only solo tackles show in box score (~35-45 per team).
    _TACKLE_MEAN_BY_POS = {
        "DE": 4.0, "DT": 3.0, "NT": 3.5,
        "LB": 7.0, "OLB": 6.0, "ILB": 8.0, "MLB": 8.0,
        "CB": 4.5, "FS": 5.0, "SS": 5.5, "S": 5.0, "SAF": 5.0,
    }
    def _distribute_tackles(player_df: pd.DataFrame):
        defenders = [p for p in user_team["players"] if p["position"] in _TACKLE_MEAN_BY_POS]
        if not defenders:
            return

        # Build weights: use historical tackle mean if available, else positional default
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
        # Total solo tackles for the user defense in this game: normally distributed around 38
        total_tackles = max(20, int(np.random.normal(38, 6)))

        for p, w in zip(defenders, weights):
            share = w / total_weight
            raw = np.random.normal(share * total_tackles, share * total_tackles * 0.25)
            tackles = max(0, round(raw))
            # Add to whatever the sim already gave them (sack tackles etc.)
            existing = user_stats.get(p["name"], {}).get("def_tackles_solo", 0)
            if p["name"] not in user_stats:
                user_stats[p["name"]] = {}
            user_stats[p["name"]]["def_tackles_solo"] = existing + tackles

    _distribute_tackles(user_player_df)

    return user_stats, opp_stats, play_log, user_score, opp_score


def _passer_rating(yards: float, tds: float, ints: float, attempts: float) -> float:
    """NFL passer rating formula (0-158.3 scale)."""
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
                 "DE", "DT", "NT", "LB", "OLB", "ILB", "MLB", "CB", "FS", "SS", "S", "SAF"]

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
        "fg_made": "FG", "fg_att": "FGA", "xp_made": "XP", "xp_att": "XPA",
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
        if not raw:
            continue

        stat_lines: dict[str, float | int] = {}

        if pos == "QB":
            pass_yds = round(raw.get("passing_yards", 0))
            pass_tds = round(raw.get("passing_tds", 0))
            ints = round(raw.get("passing_interceptions", 0))
            attempts = round(pass_yds / 7.5) if pass_yds > 0 else 0
            completions = round(attempts * 0.63)
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
        elif pos in ("CB", "FS", "SS", "S", "SAF"):
            db_order = ["def_tackles_solo", "def_interceptions", "def_pass_defended"]
            for k in db_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "K":
            k_order = ["fg_made", "fg_att", "xp_made", "xp_att"]
            for k in k_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
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


def run_game_simulation(team_id: str, nfl_opponent: str, season: int, is_home: bool = True) -> dict:
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

    # Opponent quality factor — better teams push the user's stats down slightly
    opp_team_stats = fetch_team_season_stats(nfl_opponent, season)
    opp_quality = 1.0
    if not opp_team_stats.empty:
        avg_pass = float(opp_team_stats["passing_yards"].mean()) if "passing_yards" in opp_team_stats.columns else 230
        avg_rush = float(opp_team_stats["rushing_yards"].mean()) if "rushing_yards" in opp_team_stats.columns else 115
        opp_quality = float(np.clip((avg_pass / 230 + avg_rush / 115) / 2, 0.80, 1.25))

    # Home/away quality bump
    location_boost = 1.04 if is_home else 0.96

    user_stats, _opp_stats, play_log, user_score, opp_score = simulate_game_drives(
        user_team=team,
        user_player_df=user_player_df,
        opp_roster=opp_roster,
        opp_player_df=opp_player_df,
        opp_name=nfl_opponent,
        opp_quality=opp_quality,
    )

    # Apply home/away multiplier to user offensive stats post-simulation
    if location_boost != 1.0:
        for pstats in user_stats.values():
            for stat in ("passing_yards", "rushing_yards", "receptions", "receiving_yards", "carries"):
                if stat in pstats:
                    pstats[stat] *= location_boost

    user_name = team.get("team_name", "Your Team")
    winner = user_name if user_score > opp_score else (nfl_opponent if opp_score > user_score else "TIE")

    box = build_box_score(user_stats, team["players"])

    return {
        "user_team": user_name,
        "opponent": nfl_opponent,
        "season": season,
        "is_home": is_home,
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

@app.post("/simulate-game")
async def simulate_game_endpoint(req: SimulateGameRequest):
    try:
        result = run_game_simulation(req.team_id, req.nfl_opponent, req.season, req.is_home)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
