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

def build_flat_corr(distributions: dict, team_players: list) -> tuple:
    flat_keys = []
    for name, data in distributions.items():
        for sc in data["distributions"]:
            flat_keys.append((name, sc))
    if not flat_keys:
        return flat_keys, None

    n = len(flat_keys)
    names = list(distributions.keys())

    pos_corr_map = {}
    OFFENSE = {"QB", "RB", "WR", "TE", "FB"}
    DEFENSE = {"DE", "DT", "LB", "OLB", "ILB", "MLB", "CB", "FS", "SS", "S", "SAF"}
    for p in team_players:
        for q in team_players:
            pi, qi = p["name"], q["name"]
            pp, qp = p["position"], q["position"]
            if pp == "QB" and qp in ("WR", "TE"):
                c = 0.6
            elif pp in OFFENSE and qp in OFFENSE:
                c = 0.3
            elif pp in DEFENSE and qp in DEFENSE:
                c = 0.3
            elif pp in OFFENSE and qp in DEFENSE:
                c = -0.1
            else:
                c = 0.05
            pos_corr_map[(pi, qi)] = c

    flat_corr = np.eye(n)
    for i, (p1, _) in enumerate(flat_keys):
        for j, (p2, _) in enumerate(flat_keys):
            if i == j:
                continue
            flat_corr[i][j] = 0.7 if p1 == p2 else pos_corr_map.get((p1, p2), 0.05) * 0.8

    flat_corr = np.clip(np.nan_to_num(flat_corr, nan=0.0), -1.0, 1.0)
    np.fill_diagonal(flat_corr, 1.0)
    eigvals, eigvecs = np.linalg.eigh(flat_corr)
    eigvals = np.maximum(eigvals, 1e-6)
    flat_corr = eigvecs @ np.diag(eigvals) @ eigvecs.T
    if not np.all(np.isfinite(flat_corr)):
        flat_corr = np.eye(n)

    return flat_keys, flat_corr


def sample_one_game(distributions: dict, flat_keys: list, flat_corr) -> dict:
    """Sample one game's worth of per-game stats for every player."""
    n = len(flat_keys)
    mv = np.random.multivariate_normal(np.zeros(n), flat_corr, size=1)
    u = norm.cdf(mv)[0]
    result: dict = {}
    for i, (name, sc) in enumerate(flat_keys):
        dist = distributions[name]["distributions"][sc]
        val = float(max(0.0, dist.ppf(float(np.clip(u[i], 1e-6, 1 - 1e-6)))))
        if sc in SEASON_TOTAL_STATS:
            val = val / N_GAMES
        if name not in result:
            result[name] = {}
        result[name][sc] = val
    return result


def reconcile_game_stats(game: dict, team_players: list, player_df: pd.DataFrame) -> dict:
    """
    Enforce internal consistency so the box score makes sense:
    - QB completions = sum of all receiver receptions
    - QB pass yards = sum of all receiver receiving yards
    - Total rush yards distributed across RBs/FBs by workload share
    - Carries proportional to rushing yards share
    - Targets distributed so receptions <= targets per player
    """
    game = {k: dict(v) for k, v in game.items()}  # shallow copy

    pos_map = {p["name"]: p["position"] for p in team_players}
    qb_name = next((p["name"] for p in team_players if p["position"] == "QB"), None)

    receivers = [p["name"] for p in team_players if p["position"] in ("WR", "TE", "RB", "FB")]
    rushers   = [p["name"] for p in team_players if p["position"] in ("RB", "FB")]

    # ── 1. Establish QB totals as the authoritative numbers ──────────────────
    if qb_name and qb_name in game:
        qb = game[qb_name]
        total_pass_yds = float(qb.get("passing_yards", 0))
        total_completions = round(total_pass_yds / 7.5) if total_pass_yds > 0 else 0
    else:
        total_pass_yds = 0.0
        total_completions = 0

    # ── 2. Build per-receiver target-share weights from historical data ───────
    def _hist_mean(name: str, stat: str) -> float:
        if player_df.empty:
            return 0.0
        rows = player_df[player_df["player_display_name"] == name]
        if rows.empty or stat not in rows.columns:
            return 0.0
        vals = pd.to_numeric(rows[stat], errors="coerce").dropna()
        vals = vals[vals > 0]
        return float(vals.mean()) if len(vals) >= 1 else 0.0

    # Target share: use historical targets; fall back to positional defaults
    POS_DEFAULT_TARGETS = {"WR": 7.0, "TE": 4.5, "RB": 2.5, "FB": 1.0}
    rec_target_weights: dict[str, float] = {}
    for name in receivers:
        pos = pos_map.get(name, "WR")
        hist = _hist_mean(name, "targets")
        rec_target_weights[name] = hist if hist > 0 else POS_DEFAULT_TARGETS.get(pos, 2.0)

    total_weight = sum(rec_target_weights.values()) or 1.0

    # ── 3. Distribute completions → receptions; derive targets and rec yards ──
    if total_completions > 0 and receivers:
        # Spread total completions by target-share weight
        raw_recs: dict[str, float] = {n: (rec_target_weights[n] / total_weight) * total_completions
                                       for n in receivers}

        # Derive each receiver's yards from their historical YPR (or positional default)
        POS_DEFAULT_YPR = {"WR": 12.0, "TE": 9.0, "RB": 6.0, "FB": 5.0}
        raw_rec_yds: dict[str, float] = {}
        for name in receivers:
            pos = pos_map.get(name, "WR")
            hist_rec = _hist_mean(name, "receptions")
            hist_yds = _hist_mean(name, "receiving_yards")
            if hist_rec > 1:
                ypr = hist_yds / hist_rec
            else:
                ypr = POS_DEFAULT_YPR.get(pos, 10.0)
            raw_rec_yds[name] = raw_recs[name] * ypr

        # Rescale rec yards so total matches QB pass yards
        total_raw_rec_yds = sum(raw_rec_yds.values()) or 1.0
        scale_yds = total_pass_yds / total_raw_rec_yds

        for name in receivers:
            if name not in game:
                game[name] = {}
            recs = max(0.0, raw_recs[name])
            rec_yds = max(0.0, raw_rec_yds[name] * scale_yds)
            # targets >= receptions; use historical catch rate or 70%
            hist_rec = _hist_mean(name, "receptions")
            hist_tgt = _hist_mean(name, "targets")
            catch_rate = (hist_rec / hist_tgt) if hist_tgt > 1 else 0.70
            catch_rate = max(0.40, min(catch_rate, 0.90))
            targets = recs / catch_rate
            game[name]["receptions"]     = recs
            game[name]["receiving_yards"]= rec_yds
            game[name]["targets"]        = targets
            # preserve existing receiving_tds (reconciled later from td_log)

    # ── 4. Distribute rush yards across RBs by workload share ────────────────
    if rushers:
        # Use sampled rush yards per rusher as workload weight
        rush_weights: dict[str, float] = {}
        for name in rushers:
            sampled = float(game.get(name, {}).get("rushing_yards", 0))
            pos = pos_map.get(name, "RB")
            if sampled <= 0:
                # give a small default so they still show
                sampled = 20.0 if pos == "RB" else 5.0
            rush_weights[name] = sampled

        total_rush_weight = sum(rush_weights.values()) or 1.0

        # Total team rush yards: sum of what was sampled (or QB had some too)
        total_rush_yds = sum(
            float(game.get(name, {}).get("rushing_yards", 0)) for name in rushers
        )
        if total_rush_yds < 30 and rushers:
            total_rush_yds = 80.0  # floor: at minimum 80 team rush yards

        # Add QB rush yards on top (they're separate)
        if qb_name and qb_name in game:
            total_rush_yds += float(game[qb_name].get("rushing_yards", 0))

        for name in rushers:
            share = rush_weights[name] / total_rush_weight
            rush_yds = total_rush_yds * share
            # Implied carries: use historical YPC or positional default
            hist_carries = _hist_mean(name, "carries")
            hist_rush_yds = _hist_mean(name, "rushing_yards")
            if hist_carries > 1:
                ypc = hist_rush_yds / hist_carries
            else:
                ypc = 4.2  # NFL average YPC
            ypc = max(2.5, min(ypc, 7.0))
            carries = rush_yds / ypc
            if name not in game:
                game[name] = {}
            game[name]["rushing_yards"] = rush_yds
            game[name]["carries"] = carries

    return game


def compute_score(game: dict) -> int:
    pass_yds = sum(v.get("passing_yards", 0) for v in game.values())
    rush_yds = sum(v.get("rushing_yards", 0) for v in game.values())
    fg = sum(v.get("fg_made", 0) for v in game.values())
    pts = (pass_yds + rush_yds) / 10 * 1.15 + fg * 3
    return int(max(0, round(pts)))


_PLAYS = {
    "passing_td": [
        "{qb} drops back, fires a bullet to {receiver}... TOUCHDOWN! {yards}-yard score!",
        "{qb} hits {receiver} in stride in the end zone! {yards}-yard TD pass!",
        "Beautiful back-shoulder throw from {qb} to {receiver} for a {yards}-yard TOUCHDOWN!",
        "{qb} rolls right, finds {receiver} wide open... {yards}-yard TOUCHDOWN strike!",
    ],
    "rushing_td": [
        "{rusher} takes the handoff, breaks through the line... TOUCHDOWN! {yards}-yard run!",
        "{rusher} fights through the pile and punches it in from {yards} yards!",
        "Up the gut... {rusher} finds the hole and scores from {yards} yards!",
        "{rusher} breaks a tackle and walks into the end zone from {yards} out!",
    ],
    "fg_good": [
        "{kicker} lines it up from {yards} yards... it's GOOD! 3 points.",
        "Field goal by {kicker} from {yards} yards... right down the middle!",
        "{kicker} splits the uprights from {yards}. 3 more on the board.",
    ],
    "fg_miss": [
        "{kicker} pulls it wide left from {yards}. No good.",
        "Blocked attempt! The kick is deflected and falls short.",
    ],
    "big_pass": [
        "{qb} heaves it deep... {receiver} hauls it in for {yards} yards!",
        "Bullet from {qb} finds {receiver} in stride for a {yards}-yard gain.",
        "{receiver} creates separation, {qb} delivers... {yards} yards downfield.",
        "Over the middle... {receiver} catches it and rumbles for {yards} yards.",
    ],
    "big_run": [
        "{rusher} takes the handoff, hits the hole, and races for {yards} yards!",
        "Nice cutback by {rusher}... {yards}-yard gain on the ground.",
        "{rusher} powers through contact for {yards} hard yards.",
    ],
    "sack": [
        "{defender} beats the blocker and sacks the quarterback for a big loss!",
        "Pressure up the middle... {defender} gets home for the sack!",
        "{defender} strips the ball... FUMBLE recovered by the offense.",
    ],
    "interception": [
        "{defender} reads the route perfectly... INTERCEPTION! Huge swing in momentum.",
        "Tipped at the line... {defender} comes down with the PICK!",
        "{defender} undercuts the route for the INTERCEPTION!",
    ],
    "punt": [
        "Offense goes three-and-out. Punting unit takes the field.",
        "Can't convert the third down... punt time.",
        "Forced into a punt after a tough series.",
    ],
    "opp_sack": [
        "{opp_pass_rusher} beats the blocker and sacks the quarterback for a big loss!",
        "Pressure up the middle... {opp_pass_rusher} gets home for the sack!",
        "{opp_pass_rusher} strips the ball on the sack... fumble recovered by {opponent}!",
    ],
    "opp_interception": [
        "{opp_coverage} reads the route perfectly... INTERCEPTION! Huge swing in momentum for {opponent}!",
        "Tipped at the line... {opp_coverage} comes down with the PICK for {opponent}!",
        "{opp_coverage} undercuts the route for the INTERCEPTION! {opponent} takes over.",
    ],
    "opp_fumble_recovery": [
        "{opponent} defense forces a fumble and {opp_pass_rusher} falls on it! Huge turnover.",
        "Strip sack! {opp_pass_rusher} knocks it loose and {opponent} recovers.",
    ],
    "opp_passing_td": [
        "{opp_qb} drops back, fires to {opp_receiver}... TOUCHDOWN! {yards}-yard score for {opponent}!",
        "{opp_qb} threads the needle to {opp_receiver} in the end zone! {yards}-yard TD!",
        "Beautiful throw from {opp_qb}, {opp_receiver} hauls it in for a {yards}-yard TD!",
        "{opp_qb} rolls out and finds {opp_receiver} for a {yards}-yard touchdown!",
    ],
    "opp_rushing_td": [
        "{opp_rusher} breaks through the line... TOUCHDOWN! {yards}-yard run for {opponent}!",
        "{opp_rusher} powers through contact and punches it in from {yards} yards!",
        "Up the gut for {opp_rusher}... {yards}-yard TD run!",
        "{opp_rusher} breaks a tackle and walks into the end zone from {yards} out!",
    ],
    "opp_fg": [
        "{opp_kicker} lines it up from {yards} yards... it's GOOD! 3 points for {opponent}.",
        "Field goal is good for {opponent}. {opp_kicker} splits the uprights from {yards}.",
    ],
    "opp_fg_miss": [
        "{opp_kicker} misses from {yards} yards. No good for {opponent}.",
        "Wide right! {opp_kicker}'s attempt from {yards} yards falls short.",
    ],
    "opp_punt": [
        "{opp_punter} punts it away after a three-and-out.",
        "{opponent} offense stalls... {opp_punter} comes on to punt.",
        "Three-and-out for {opponent}. {opp_punter} booms it downfield.",
    ],
    "turnover_on_downs": [
        "Fourth-and-short attempt fails... turnover on downs.",
        "Goes for it on 4th down but can't convert.",
    ],
    "kickoff_return": [
        "{returner} takes the kickoff out to the {yards}-yard line!",
        "Big return by {returner}... brings it out {yards} yards!",
    ],
}


_PLAY_WEIGHTS: dict[str, list[int]] = {
    "sack": [10, 10, 2],
    "interception": [10, 3, 10],
}

def _pick(key: str, **kw) -> str:
    templates = _PLAYS[key]
    weights = _PLAY_WEIGHTS.get(key)
    chosen = random.choices(templates, weights=weights, k=1)[0] if weights else random.choice(templates)
    return chosen.format(**kw)


def _quarter_label(q: int) -> str:
    return ["Q1", "Q2", "Q3", "Q4"][q - 1]


def generate_play_by_play(user_game: dict, opp_game: dict, user_team: dict, opp_name: str, opp_roster: list) -> tuple[list[dict], int, int, dict]:
    plays = []
    user_score = 0
    opp_score = 0

    td_log: dict[str, dict[str, int]] = {}

    def _td_add(name: str, stat: str):
        if name not in td_log:
            td_log[name] = {"passing_tds": 0, "rushing_tds": 0, "receiving_tds": 0}
        td_log[name][stat] += 1

    qb = next((p["name"] for p in user_team["players"] if p["position"] == "QB"), "QB")
    kicker = next((p["name"] for p in user_team["players"] if p["position"] == "K"), "K")
    returner = next((p["name"] for p in user_team["players"] if p["position"] == "RS"), None)
    receivers = [p["name"] for p in user_team["players"] if p["position"] in ("WR", "TE")]
    rushers = [p["name"] for p in user_team["players"] if p["position"] in ("RB", "FB")]
    
    _USER_SACK_WEIGHT = {"DE": 5, "DT": 4, "NT": 3, "OLB": 3, "LB": 1, "ILB": 1, "MLB": 1}
    _USER_INT_WEIGHT = {"CB": 4, "FS": 2, "SS": 2, "S": 2, "SAF": 2}
    user_sack_pool = [(p["name"], _USER_SACK_WEIGHT.get(p["position"], 1))
                      for p in user_team["players"] if p["position"] in _USER_SACK_WEIGHT]
    user_int_pool = [(p["name"], _USER_INT_WEIGHT.get(p["position"], 1))
                      for p in user_team["players"] if p["position"] in _USER_INT_WEIGHT]

    def rand_receiver(): return random.choice(receivers) if receivers else "WR"
    def rand_rusher(): return random.choice(rushers) if rushers else "RB"
    def rand_sacker():
        if not user_sack_pool:
            return "DEF"
        names, weights = zip(*user_sack_pool)
        return random.choices(names, weights=weights, k=1)[0]
    def rand_interceptor():
        if not user_int_pool:
            return "DEF"
        names, weights = zip(*user_int_pool)
        return random.choices(names, weights=weights, k=1)[0]

    opp_qb = next((p["name"] for p in opp_roster if p["position"] == "QB"), opp_name + " QB")
    opp_kicker = next((p["name"] for p in opp_roster if p["position"] == "K"), opp_name + " K")
    opp_punter = next((p["name"] for p in opp_roster if p["position"] == "P"), opp_name + " P")
    opp_receivers = [p["name"] for p in opp_roster if p["position"] in ("WR", "TE")]
    opp_rushers = [p["name"] for p in opp_roster if p["position"] in ("RB", "FB")]

    _SACK_WEIGHT = {"DE": 5, "DT": 4, "NT": 3, "OLB": 3, "LB": 1, "ILB": 1, "MLB": 1}
    opp_sack_pool = [(p["name"], _SACK_WEIGHT.get(p["position"], 1))
                     for p in opp_roster if p["position"] in _SACK_WEIGHT]

    _INT_WEIGHT = {"CB": 4, "FS": 2, "SS": 2, "S": 2, "SAF": 2}
    opp_int_pool = [(p["name"], _INT_WEIGHT.get(p["position"], 1))
                    for p in opp_roster if p["position"] in _INT_WEIGHT]

    def rand_opp_receiver(): return random.choice(opp_receivers) if opp_receivers else opp_name + " WR"
    def rand_opp_rusher(): return random.choice(opp_rushers) if opp_rushers else opp_name + " RB"
    def rand_opp_pass_rusher():
        if not opp_sack_pool:
            return opp_name + " DE"
        names, weights = zip(*opp_sack_pool)
        return random.choices(names, weights=weights, k=1)[0]
    def rand_opp_coverage():
        if not opp_int_pool:
            return opp_name + " CB"
        names, weights = zip(*opp_int_pool)
        return random.choices(names, weights=weights, k=1)[0]

    SCORE_ETYPES = {"passing_td", "rushing_td", "fg_good", "opp_passing_td", "opp_rushing_td", "opp_fg"}

    def add(q: int, team: str, text: str, etype: str):
        plays.append({
            "quarter": _quarter_label(q),
            "team": team,
            "play": text,
            "score": f"{user_score}-{opp_score}",
            "is_score": etype in SCORE_ETYPES,
        })

    user_pass_yds = sum(v.get("passing_yards", 0) for v in user_game.values())
    user_rush_yds = sum(v.get("rushing_yards", 0) for v in user_game.values())
    user_pass_tds = round(sum(v.get("passing_tds", 0) for v in user_game.values()))
    user_rush_tds = round(sum(v.get("rushing_tds", 0) for v in user_game.values()))
    user_fg_made = round(sum(v.get("fg_made", 0) for v in user_game.values()))
    user_fg_att = max(user_fg_made, round(sum(v.get("fg_att", 0) for v in user_game.values())))
    user_sacks = round(sum(v.get("def_sacks", 0) for v in user_game.values()))
    user_ints = round(sum(v.get("def_interceptions", 0) for v in user_game.values()))
    user_kr_yds = round(sum(v.get("kickoff_return_yards", 0) for v in user_game.values()))

    opp_pass_tds = round(sum(v.get("passing_tds", 0) for v in opp_game.values()))
    opp_rush_tds = round(sum(v.get("rushing_tds", 0) for v in opp_game.values()))
    opp_fg_made = round(sum(v.get("fg_made", 0) for v in opp_game.values()))
    opp_fg_att = max(opp_fg_made, round(sum(v.get("fg_att", 0) for v in opp_game.values())))
    opp_sacks = round(sum(v.get("def_sacks", 0) for v in opp_game.values()))
    opp_ints = round(sum(v.get("def_interceptions", 0) for v in opp_game.values()))

    events: list[tuple] = []

    def spread(etype: str, count: int, side: str, weights=(2, 3, 3, 2), **kw):
        for _ in range(count):
            q = random.choices([1, 2, 3, 4], weights=weights)[0]
            events.append((q, side, etype, kw))

    spread("passing_td", user_pass_tds, "user")
    spread("rushing_td", user_rush_tds, "user")
    user_fg_miss = max(0, user_fg_att - user_fg_made)
    spread("fg_good", user_fg_made, "user")
    spread("fg_miss", user_fg_miss, "user")

    big_pass_count = max(0, int((user_pass_yds - user_pass_tds * 12) / 18))
    spread("big_pass", min(big_pass_count, 5), "user")
    big_run_count = max(0, int((user_rush_yds - user_rush_tds * 5) / 14))
    spread("big_run", min(big_run_count, 3), "user")

    spread("sack", user_sacks, "user")
    spread("interception", user_ints, "user")

    spread("opp_passing_td", opp_pass_tds, "opp")
    spread("opp_rushing_td", opp_rush_tds, "opp")
    opp_fg_miss = max(0, opp_fg_att - opp_fg_made)
    spread("opp_fg", opp_fg_made, "opp")
    spread("opp_fg_miss", opp_fg_miss, "opp")
    spread("opp_sack", opp_sacks, "opp")
    spread("opp_interception", opp_ints, "opp")
    if random.random() < 0.4:
        spread("opp_fumble_recovery", 1, "opp")

    if returner and user_kr_yds > 20:
        events.append((1, "user", "kickoff_return", {}))

    events.append((1, "opp", "opp_punt", {}))
    events.append((2, "user", "punt", {}))
    events.append((3, "opp", "opp_punt", {}))

    events.sort(key=lambda x: x[0])

    user_name = user_team.get("team_name", "Your Team")

    for q, side, etype, _ in events:
        if side == "user":
            if etype == "passing_td":
                yds = random.randint(5, 38)
                user_score += 7
                receiver = rand_receiver()
                _td_add(qb, "passing_tds")
                _td_add(receiver, "receiving_tds")
                text = _pick("passing_td", qb=qb, receiver=receiver, yards=yds)
            elif etype == "rushing_td":
                yds = random.randint(1, 14)
                user_score += 7
                rusher = rand_rusher()
                _td_add(rusher, "rushing_tds")
                text = _pick("rushing_td", rusher=rusher, yards=yds)
            elif etype == "fg_good":
                yds = random.randint(22, 54)
                user_score += 3
                text = _pick("fg_good", kicker=kicker, yards=yds)
            elif etype == "fg_miss":
                yds = random.randint(45, 58)
                text = _pick("fg_miss", kicker=kicker, yards=yds)
            elif etype == "big_pass":
                yds = random.randint(14, 48)
                text = _pick("big_pass", qb=qb, receiver=rand_receiver(), yards=yds)
            elif etype == "big_run":
                yds = random.randint(10, 32)
                text = _pick("big_run", rusher=rand_rusher(), yards=yds)
            elif etype == "sack":
                text = _pick("sack", defender=rand_sacker())
            elif etype == "interception":
                text = _pick("interception", defender=rand_interceptor())
            elif etype == "punt":
                text = _pick("punt")
            elif etype == "kickoff_return":
                yds = random.randint(18, 42)
                text = _pick("kickoff_return", returner=returner, yards=yds)
            else:
                continue
            add(q, user_name, text, etype)
        else:
            if etype == "opp_passing_td":
                opp_score += 7
                yds = random.randint(5, 38)
                text = _pick("opp_passing_td", opponent=opp_name, opp_qb=opp_qb, opp_receiver=rand_opp_receiver(), yards=yds)
            elif etype == "opp_rushing_td":
                opp_score += 7
                yds = random.randint(1, 14)
                text = _pick("opp_rushing_td", opponent=opp_name, opp_rusher=rand_opp_rusher(), yards=yds)
            elif etype == "opp_fg":
                opp_score += 3
                yds = random.randint(22, 54)
                text = _pick("opp_fg", opponent=opp_name, opp_kicker=opp_kicker, yards=yds)
            elif etype == "opp_fg_miss":
                yds = random.randint(45, 58)
                text = _pick("opp_fg_miss", opponent=opp_name, opp_kicker=opp_kicker, yards=yds)
            elif etype == "opp_punt":
                text = _pick("opp_punt", opponent=opp_name, opp_punter=opp_punter)
            elif etype == "opp_sack":
                text = _pick("opp_sack", opponent=opp_name, opp_pass_rusher=rand_opp_pass_rusher())
            elif etype == "opp_interception":
                text = _pick("opp_interception", opponent=opp_name, opp_coverage=rand_opp_coverage())
            elif etype == "opp_fumble_recovery":
                text = _pick("opp_fumble_recovery", opponent=opp_name, opp_pass_rusher=rand_opp_pass_rusher())
            else:
                continue
            add(q, opp_name, text, etype)

    return plays, user_score, opp_score, td_log

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
        "fg_made", "fg_att",
        "kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards",
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
        "def_pass_defended": "PD", "fg_made": "FG", "fg_att": "FGA",
        "kickoff_return_yards": "KR Yds", "kickoff_returns": "KR",
        "punt_return_yards": "PR Yds", "punt_returns": "PR",
    }

    box = []
    sorted_players = sorted(
        team_players,
        key=lambda p: (POS_ORDER.index(p["position"]) if p["position"] in POS_ORDER else 99, p["name"])
    )
    for p in sorted_players:
        name = p["name"]
        pos = p["position"]
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
            k_order = ["fg_made", "fg_att"]
            for k in k_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "P":
            p_order = ["punt_returns", "punt_return_yards"]
            for k in p_order:
                v = raw.get(k, 0)
                label = STAT_DISPLAY.get(k, k)
                stat_lines[label] = round(v) if k in INT_STATS else round(v, 1)
        elif pos == "RS":
            rs_order = ["kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards"]
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
    user_dists = build_all_dists(team, user_player_df)
    user_flat_keys, user_flat_corr = build_flat_corr(user_dists, team["players"])
    if user_flat_corr is None:
        raise ValueError("Could not build user team correlation matrix")

    opp_roster = fetch_nfl_roster(nfl_opponent, season)
    if not opp_roster:
        raise ValueError(f"No roster data found for {nfl_opponent} in {season}")
    opp_team_obj = {"players": opp_roster, "team_name": nfl_opponent}
    opp_player_names = [p["name"] for p in opp_roster]
    opp_player_df = fetch_player_stats(opp_player_names)
    opp_dists = build_all_dists(opp_team_obj, opp_player_df)
    opp_flat_keys, opp_flat_corr = build_flat_corr(opp_dists, opp_roster)

    user_game = sample_one_game(user_dists, user_flat_keys, user_flat_corr)
    opp_game: dict = {}
    if opp_flat_corr is not None:
        opp_game = sample_one_game(opp_dists, opp_flat_keys, opp_flat_corr)

    opp_team_stats = fetch_team_season_stats(nfl_opponent, season)
    opp_def_factor = 1.0
    if not opp_team_stats.empty:
        avg_pass = float(opp_team_stats["passing_yards"].mean()) if "passing_yards" in opp_team_stats else 230
        avg_rush = float(opp_team_stats["rushing_yards"].mean()) if "rushing_yards" in opp_team_stats else 115
        opp_off_rating = (avg_pass / 230 + avg_rush / 115) / 2
        opp_def_factor = float(np.clip(1.0 / opp_off_rating, 0.78, 1.22))

    location_mult = 1.05 if is_home else 0.97
    opp_location_mult = 0.97 if is_home else 1.05
    combined_user_mult = opp_def_factor * location_mult
    combined_opp_mult = opp_location_mult

    def scale_game(game: dict, mult: float) -> dict:
        SCALE_STATS = {"passing_yards", "rushing_yards", "passing_tds", "rushing_tds",
                       "receiving_tds", "fg_made", "fg_att", "carries"}
        return {
            name: {k: v * mult if k in SCALE_STATS else v for k, v in stats.items()}
            for name, stats in game.items()
        }

    user_game = scale_game(user_game, combined_user_mult)
    opp_game = scale_game(opp_game, combined_opp_mult)

    user_name = team.get("team_name", "Your Team")

    plays, user_score, opp_score, td_log = generate_play_by_play(user_game, opp_game, team, nfl_opponent, opp_roster)

    # Game-script adjustment: winning team ran more, losing team threw more to catch up
    score_margin = user_score - opp_score
    if abs(score_margin) >= 7:
        winning_game = user_game if score_margin > 0 else opp_game
        losing_game = opp_game if score_margin > 0 else user_game
        margin_factor = min(abs(score_margin) / 14.0, 1.0)  # 0.0 at 7pts, 1.0 at 21+pts
        rush_boost = 1.0 + 0.35 * margin_factor          # up to +35% more carries/rush yds for winner
        pass_cut = 1.0 - 0.15 * margin_factor             # up to -15% fewer pass yds for winner (ran clock)
        pass_boost = 1.0 + 0.20 * margin_factor           # up to +20% more pass yds for loser (desperation)
        rush_cut = 1.0 - 0.25 * margin_factor             # up to -25% fewer carries for loser
        for pstats in winning_game.values():
            for stat in ("carries", "rushing_yards"):
                if stat in pstats:
                    pstats[stat] *= rush_boost
            if "passing_yards" in pstats:
                pstats["passing_yards"] *= pass_cut
        for pstats in losing_game.values():
            for stat in ("carries", "rushing_yards"):
                if stat in pstats:
                    pstats[stat] *= rush_cut
            if "passing_yards" in pstats:
                pstats["passing_yards"] *= pass_boost
    winner = user_name if user_score > opp_score else (nfl_opponent if opp_score > user_score else "TIE")

    for pname, pstats in user_game.items():
        for td_key in ("passing_tds", "rushing_tds", "receiving_tds"):
            if td_key in pstats:
                pstats[td_key] = 0
    for pname, scored in td_log.items():
        if pname not in user_game:
            user_game[pname] = {}
        for td_key, count in scored.items():
            if count > 0:
                user_game[pname][td_key] = count

    box = build_box_score(user_game, team["players"])

    return {
        "user_team": user_name,
        "opponent": nfl_opponent,
        "season": season,
        "is_home": is_home,
        "final_score": {"user": user_score, "opponent": opp_score},
        "winner": winner,
        "play_by_play": plays,
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
