"""
Optimal Team Builder: Genetic Algorithm with salary cap constraints.

Framing: Each "chromosome" is a 25-player roster drawn from an available player
pool. Fitness = fast analytically-derived Super Bowl probability estimate
(mirrors the math in team_analysis.py without running 300 full simulations).
The GA evolves better rosters over about 60 generations, respecting a hard salary cap.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import scipy.stats as stats_dist
import random
import os
import nflreadpy as nfl

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="NFL Team Optimizer")

SALARY_CAP = 301_200_000
LEAGUE_MIN = 790_000

_POS_SALARY_RANGE = {
    "QB": (LEAGUE_MIN, 55_000_000),
    "RB": (LEAGUE_MIN, 16_000_000),
    "WR": (LEAGUE_MIN, 30_000_000),
    "TE": (LEAGUE_MIN, 20_000_000),
    "OT": (LEAGUE_MIN, 25_000_000),
    "G": (LEAGUE_MIN, 14_000_000),
    "C": (LEAGUE_MIN, 13_000_000),
    "DE": (LEAGUE_MIN, 25_000_000),
    "DT": (LEAGUE_MIN, 22_000_000),
    "NT": (LEAGUE_MIN, 15_000_000),
    "LB": (LEAGUE_MIN, 20_000_000),
    "OLB": (LEAGUE_MIN, 20_000_000),
    "ILB": (LEAGUE_MIN, 18_000_000),
    "MLB": (LEAGUE_MIN, 18_000_000),
    "CB": (LEAGUE_MIN, 22_000_000),
    "FS": (LEAGUE_MIN, 18_000_000),
    "SS": (LEAGUE_MIN, 18_000_000),
    "S": (LEAGUE_MIN, 18_000_000),
    "SAF": (LEAGUE_MIN, 18_000_000),
    "K": (LEAGUE_MIN, 6_000_000),
    "P": (LEAGUE_MIN, 4_000_000),
    "RS": (LEAGUE_MIN, 3_000_000),
    "FB": (LEAGUE_MIN, 3_000_000),
    "LS": (LEAGUE_MIN, 1_500_000),
}
_DEFAULT_SALARY_RANGE = (LEAGUE_MIN, 5_000_000)


FORMATION_ROSTERS: dict[tuple[str, str], dict[str, int]] = {
    ("3 WR 1 TE", "4-3 Defense"): {
        "QB": 1, "RB": 2, "WR": 3, "TE": 1, "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 2, "LB": 3, "CB": 2, "SAF": 1, "FS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
    ("2 WR 2 TE", "4-3 Defense"): {
        "QB": 1, "RB": 2, "WR": 2, "TE": 2, "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 2, "LB": 3, "CB": 2, "SAF": 1, "FS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
    ("3 WR 1 TE", "3-4 Defense"): {
        "QB": 1, "RB": 2, "WR": 3, "TE": 1, "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 1, "LB": 4, "CB": 2, "SAF": 1, "FS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
    ("2 WR 2 TE", "3-4 Defense"): {
        "QB": 1, "RB": 2, "WR": 2, "TE": 2, "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 1, "LB": 4, "CB": 2, "SAF": 1, "FS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
}

FORMATIONS = list(FORMATION_ROSTERS.keys())
ROSTER_SIZE = max(sum(v for v in f.values()) for f in FORMATION_ROSTERS.values())

OFFENSE_POS = {"QB", "RB", "FB", "WR", "TE"}
DEFENSE_POS = {"DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB",
               "CB", "FS", "SS", "S", "SAF"}

_NICKEL_DIME_POSITIONS = {"CB", "SS", "FS", "S", "SAF", "DB"}

_POS_STAT_KEYS = {
    "QB": ["passing_yards", "passing_tds", "passing_interceptions", "rushing_yards"],
    "RB": ["carries", "rushing_yards", "rushing_tds", "receiving_yards"],
    "FB": ["carries", "rushing_yards", "receiving_yards"],
    "WR": ["receiving_yards", "receiving_tds", "targets"],
    "TE": ["receiving_yards", "receiving_tds", "targets"],
    "DE": ["def_sacks", "def_tackles_solo"],
    "DT": ["def_sacks", "def_tackles_solo"],
    "NT": ["def_tackles_solo"],
    "DL": ["def_sacks", "def_tackles_solo"],
    "LB": ["def_tackles_solo", "def_sacks", "def_interceptions"],
    "OLB": ["def_tackles_solo", "def_sacks", "def_interceptions"],
    "ILB": ["def_tackles_solo", "def_sacks"],
    "MLB": ["def_tackles_solo"],
    "SLB": ["def_tackles_solo", "def_sacks"],
    "WLB": ["def_tackles_solo", "def_sacks"],
    "CB": ["def_interceptions", "def_pass_defended", "def_tackles_solo"],
    "FS": ["def_interceptions", "def_tackles_solo"],
    "SS": ["def_interceptions", "def_tackles_solo"],
    "S": ["def_interceptions", "def_tackles_solo"],
    "SAF": ["def_interceptions", "def_tackles_solo"],
    "K": ["fg_made", "fg_att"],
    "P": [],
    "RS": [],
    "OT": [],
    "G": [],
    "C": [],
    "LS": [],
}

_N_GAMES = 17.0 

_OFF_WEIGHTS = {
    "passing_yards": 0.025,
    "passing_tds": 1.5,
    "passing_interceptions": -2.0,
    "rushing_yards": 0.025,
    "rushing_tds": 1.0,
    "receiving_yards": 0.020,
    "receiving_tds": 0.8,
    "carries": 0.03,
    "targets": 0.08,
    "receptions": 0.06,
}
_DEF_WEIGHTS = {
    "def_sacks": 1.0,
    "def_tackles_solo": 0.15,
    "def_interceptions": 1.2,
    "def_pass_defended": 0.4,
}
_FG_WEIGHT = 0.6
_PLAYER_POOL_CACHE: list[dict] | None = None
_CONTRACTS_CACHE: pd.DataFrame | None = None


_TALENT_METRICS: dict[str, list[tuple[str, float]]] = {
    "QB": [("passing_yards", 0.4), ("passing_tds", 0.4), ("passing_interceptions", -0.2)],
    "RB": [("rushing_yards", 0.5), ("rushing_tds", 0.3), ("receiving_yards", 0.2)],
    "FB": [("rushing_yards", 0.6), ("receiving_yards", 0.4)],
    "WR": [("targets", 0.3), ("receiving_yards", 0.4), ("receiving_tds", 0.3)],
    "TE": [("targets", 0.3), ("receiving_yards", 0.4), ("receiving_tds", 0.3)],
    "DE": [("def_sacks", 0.6), ("def_tackles_solo", 0.3), ("def_pass_defended", 0.1)],
    "DT": [("def_sacks", 0.4), ("def_tackles_solo", 0.4), ("def_pass_defended", 0.2)],
    "NT": [("def_tackles_solo", 0.7), ("def_sacks", 0.3)],
    "MLB": [("def_tackles_solo", 0.5), ("def_interceptions", 0.3), ("def_sacks", 0.2)],
    "ILB": [("def_tackles_solo", 0.5), ("def_sacks", 0.3), ("def_interceptions", 0.2)],
    "OLB": [("def_sacks", 0.5), ("def_tackles_solo", 0.3), ("def_interceptions", 0.2)],
    "LB": [("def_tackles_solo", 0.4), ("def_sacks", 0.3), ("def_interceptions", 0.3)],
    "CB": [("def_pass_defended", 0.4), ("def_interceptions", 0.3), ("def_tackles_solo", 0.3)],
    "FS": [("def_interceptions", 0.6), ("def_pass_defended", 0.25), ("def_tackles_solo", 0.15)],
    "SS": [("def_tackles_solo", 0.5), ("def_interceptions", 0.3), ("def_pass_defended", 0.2)],
    "SAF": [("def_tackles_solo", 0.5), ("def_interceptions", 0.3), ("def_pass_defended", 0.2)],
    "S": [("def_interceptions", 0.6), ("def_pass_defended", 0.25), ("def_tackles_solo", 0.15)],
    "Nickel": [("def_pass_defended", 0.4), ("def_interceptions", 0.3), ("def_tackles_solo", 0.3)],
    "Dime": [("def_pass_defended", 0.34), ("def_interceptions", 0.33), ("def_tackles_solo", 0.33)],
    "K": [("fg_made", 0.7), ("fg_att", 0.3)],
    "P": [("punt_yards_season", 0.6), ("punt_attempts_season", 0.4)],
    "RS": [("kickoff_return_yards", 0.5), ("punt_return_yards", 0.5)],
}

_CONTRACT_POS_MAP = {
    "QB": "QB", "RB": "RB", "FB": "FB", "WR": "WR", "TE": "TE",
    "LT": "OT", "RT": "OT", "LG": "G", "RG": "G", "C": "C",
    "DE": "DE", "DT": "DT", "NT": "NT",
    "LB": "LB", "OLB": "OLB", "ILB": "ILB", "MLB": "MLB",
    "CB": "CB", "FS": "FS", "SS": "SS", "S": "SAF",
    "K": "K", "P": "P", "LS": "LS",
}

def _load_contracts() -> pd.DataFrame:
    global _CONTRACTS_CACHE
    if _CONTRACTS_CACHE is not None:
        return _CONTRACTS_CACHE
    try:
        df = nfl.load_contracts().to_pandas()
        df = df[df["year_signed"] >= 2018].copy()
        df["pos_key"] = df["position"].map(_CONTRACT_POS_MAP)
        df = df.dropna(subset=["pos_key", "apy"])
        df["apy"] = pd.to_numeric(df["apy"], errors="coerce").fillna(0) * 1000000
        _CONTRACTS_CACHE = df
    except Exception:
        _CONTRACTS_CACHE = pd.DataFrame()
    return _CONTRACTS_CACHE

def _talent_percentile(player_name: str, position: str, stats_df: pd.DataFrame) -> float:
    """
    Compute talent percentile z ∈ [0.01, 0.99] via composite Z-score -> Gaussian CDF.
    Uses per-season per-game normalized stats to eliminate multi-year volume bias.
    stats_df may or may not have a 'position' column. If absent, all rows are treated
    as peers (used for position-specific tables like punt_stats, return_stats).
    """
    metrics = _TALENT_METRICS.get(position, [])
    if not metrics or stats_df.empty:
        return 0.5

    player_rows = stats_df[stats_df["player_display_name"] == player_name]
    if player_rows.empty:
        return 0.2

    has_season = "season" in stats_df.columns
    n_seasons = max(player_rows["season"].nunique(), 1) if has_season else 1
    player_pg: dict[str, float] = {}
    for col, _ in metrics:
        if col in player_rows.columns:
            total = pd.to_numeric(player_rows[col], errors="coerce").fillna(0).sum()
            player_pg[col] = float(total) / (n_seasons * 17.0)
        else:
            player_pg[col] = 0.0

    if "position" in stats_df.columns:
        pos_rows = stats_df[stats_df["position"] == position]
    else:
        pos_rows = stats_df

    if len(pos_rows["player_display_name"].unique()) < 3:
        return 0.5

    peer_pg: dict[str, list[float]] = {col: [] for col, _ in metrics}
    for _, grp in pos_rows.groupby("player_display_name"):
        ns = max(grp["season"].nunique(), 1) if has_season else 1
        for col, _ in metrics:
            if col in grp.columns:
                total = pd.to_numeric(grp[col], errors="coerce").fillna(0).sum()
                peer_pg[col].append(float(total) / (ns * 17.0))

    composite_z = 0.0
    for col, weight in metrics:
        arr = np.array(peer_pg.get(col, []))
        if len(arr) < 2:
            continue
        mu, sigma = float(arr.mean()), float(arr.std())
        if sigma < 1e-6:
            continue
        z_i = (player_pg.get(col, 0.0) - mu) / sigma
        composite_z += weight * z_i

    return float(np.clip(stats_dist.norm.cdf(composite_z), 0.01, 0.99))


def _salary_from_contracts(player_name: str, position: str, contracts: pd.DataFrame) -> int | None:
    """Try to find a real APY contract for this player. Returns None if not found."""
    if contracts.empty:
        return None
    pos_key = position
    matches = contracts[
        (contracts["pos_key"] == pos_key) &
        (contracts["player"].str.lower() == player_name.lower())
    ]
    if matches.empty:
        last = player_name.split()[-1].lower()
        matches = contracts[
            (contracts["pos_key"] == pos_key) &
            (contracts["player"].str.lower().str.contains(last, na=False))
        ]
    if matches.empty:
        return None
    apy = float(matches.sort_values("year_signed", ascending=False).iloc[0]["apy"])
    lo, hi = _POS_SALARY_RANGE.get(position, _DEFAULT_SALARY_RANGE)
    return int(np.clip(apy, lo, hi))


def _salary_from_percentile(z: float, position: str) -> int:
    """
    Exponential salary curve: Salary(z) = LeagueMin + (MaxSalary - LeagueMin) * z ** gamma
    gamma=2.5 ensures flat curve near league min for backups, exponential spike for elite.
    """
    lo, hi = _POS_SALARY_RANGE.get(position, _DEFAULT_SALARY_RANGE)
    gamma = 2.5
    salary = lo + (hi - lo) * (z ** gamma)
    noise = random.uniform(0.93, 1.07)
    return int(np.clip(salary * noise, lo, hi))


def _assign_salary(player_name: str, position: str, stats_df: pd.DataFrame,
                   contracts: pd.DataFrame | None = None) -> int:
    if contracts is not None:
        real = _salary_from_contracts(player_name, position, contracts)
        if real is not None:
            return real
    z = _talent_percentile(player_name, position, stats_df)
    return _salary_from_percentile(z, position)

def _build_player_pool(n_players: int = 300) -> list[dict]:
    global _PLAYER_POOL_CACHE
    if _PLAYER_POOL_CACHE is not None:
        return _PLAYER_POOL_CACHE

    contracts = _load_contracts()

    _DEF_POSITIONS = {"DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB",
                      "CB", "FS", "SS", "S", "SAF", "DB"}
    response = supabase.table("player_stats").select(
        "player_display_name, position, team, season, "
        "passing_yards, passing_tds, passing_interceptions, carries, rushing_yards, rushing_tds, "
        "receptions, targets, receiving_yards, receiving_tds, "
        "def_sacks, def_tackles_solo, def_interceptions, def_pass_defended, "
        "fg_made, fg_att"
    ).gte("season", 2022).limit(5000).execute()

    if not response.data:
        raise RuntimeError("Failed to fetch player pool from Supabase")

    df = pd.DataFrame(response.data)
    numeric_cols = [c for c in df.columns if c not in ("player_display_name", "position", "team", "season")]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    agg = df.groupby(["player_display_name", "position", "team"])[numeric_cols].sum().reset_index()
    agg["total_yards"] = agg.get("passing_yards", 0) + agg.get("rushing_yards", 0) + agg.get("receiving_yards", 0)
    agg["total_def"] = agg.get("def_tackles_solo", 0) + agg.get("def_sacks", 0) * 5
    # Keep all defensive players (DBs have low counting stats but are still valid starters)
    # and all skill/ST players who meet the yardage threshold
    agg = agg[
        (agg["total_yards"] > 50) |
        (agg["total_def"] > 0) |
        (agg["def_interceptions"] > 0) |
        (agg["def_pass_defended"] > 0) |
        (agg["fg_made"] > 0) |
        (agg["position"].isin(["K", "P"])) |
        (agg["position"].isin(_DEF_POSITIONS))
    ]

    if len(agg) > n_players:
        agg["score"] = agg["total_yards"] + agg["total_def"] * 10
        top_half = agg.nlargest(n_players // 2, "score")
        rest = agg.drop(top_half.index).sample(min(n_players // 2, len(agg) - len(top_half)))
        agg = pd.concat([top_half, rest])

    players = []
    for _, row in agg.iterrows():
        pos = row["position"]
        salary = _assign_salary(row["player_display_name"], pos, df, contracts)
        stats = {c: float(row[c]) for c in numeric_cols if c in row}
        players.append({
            "name": row["player_display_name"],
            "position": pos,
            "nfl_team": row.get("team", ""),
            "salary": salary,
            "stats": stats,
        })

    try:
        punt_resp = supabase.table("punt_stats").select(
            "player_display_name, team, season, punt_yards_season, punt_attempts_season"
        ).gte("season", 2022).execute()
        if punt_resp.data:
            punt_df = pd.DataFrame(punt_resp.data)
            for c in ["punt_yards_season", "punt_attempts_season"]:
                if c in punt_df.columns:
                    punt_df[c] = pd.to_numeric(punt_df[c], errors="coerce").fillna(0)
            punt_agg = punt_df.groupby(["player_display_name", "team"])[
                ["punt_yards_season", "punt_attempts_season"]
            ].sum().reset_index()
            punt_agg = punt_agg[punt_agg["punt_attempts_season"] > 0]
            for _, row in punt_agg.iterrows():
                salary = _assign_salary(row["player_display_name"], "P", punt_df, contracts)
                players.append({
                    "name": row["player_display_name"],
                    "position": "P",
                    "nfl_team": row.get("team", ""),
                    "salary": salary,
                    "stats": {"punt_yards_season": float(row.get("punt_yards_season", 0)),
                              "punt_attempts_season": float(row.get("punt_attempts_season", 0))},
                })
    except Exception:
        pass

    try:
        rs_resp = supabase.table("return_stats").select(
            "player_display_name, team, season, kickoff_return_yards, kickoff_returns, punt_return_yards, punt_returns"
        ).gte("season", 2022).execute()
        if rs_resp.data:
            rs_df = pd.DataFrame(rs_resp.data)
            rs_num_cols = ["kickoff_return_yards", "kickoff_returns", "punt_return_yards", "punt_returns"]
            for c in rs_num_cols:
                if c in rs_df.columns:
                    rs_df[c] = pd.to_numeric(rs_df[c], errors="coerce").fillna(0)
            rs_agg = rs_df.groupby(["player_display_name", "team"])[rs_num_cols].sum().reset_index()
            rs_agg = rs_agg[(rs_agg["kickoff_returns"] + rs_agg["punt_returns"]) >= 10]
            for _, row in rs_agg.iterrows():
                salary = _assign_salary(row["player_display_name"], "RS", rs_df, contracts)
                players.append({
                    "name": row["player_display_name"],
                    "position": "RS",
                    "nfl_team": row.get("team", ""),
                    "salary": salary,
                    "stats": {c: float(row.get(c, 0)) for c in rs_num_cols},
                })
    except Exception:
        pass

    # nflreadpy uses coarse positions: "OL" for all linemen, "LS" for long snappers.
    # depth_chart_position has "T", "G", "C" which we use to split OL into OT/G/C.
    _DCP_MAP = {"T": "OT", "LT": "OT", "RT": "OT", "G": "G", "LG": "G", "RG": "G", "C": "C"}
    try:
        import polars as pl
        roster_pl = nfl.load_rosters(seasons=[2022, 2023, 2024])
        roster_pd = roster_pl.to_pandas()
        ol_ls_raw = roster_pd[roster_pd["position"].isin(["OL", "LS"])].copy()
        ol_ls_raw = ol_ls_raw.dropna(subset=["full_name"])

        def _map_ol_pos(row):
            if row["position"] == "LS":
                return "LS"
            dcp = str(row.get("depth_chart_position", "")).strip()
            return _DCP_MAP.get(dcp)

        ol_ls_raw["pos_key"] = ol_ls_raw.apply(_map_ol_pos, axis=1)
        ol_ls = ol_ls_raw.dropna(subset=["pos_key"])
        ol_ls = ol_ls.sort_values("season", ascending=False).drop_duplicates(subset=["full_name", "pos_key"])

        existing_names = {p["name"] for p in players}
        for _, row in ol_ls.iterrows():
            name = str(row["full_name"])
            pos = str(row["pos_key"])
            if name in existing_names:
                continue
            # Tier 1: real contract APY; Tier 2: percentile curve at UDFA/fringe level
            salary = _salary_from_contracts(name, pos, contracts)
            if salary is None:
                salary = _salary_from_percentile(0.2, pos)
            players.append({
                "name": name,
                "position": pos,
                "nfl_team": str(row.get("team", "")),
                "salary": salary,
                "stats": {},
            })
            existing_names.add(name)
    except Exception:
        pass

    _PLAYER_POOL_CACHE = players
    return players


def _per_game_stats(stats: dict) -> dict:
    """Normalize cumulative stats to per-game by dividing by estimated seasons * 17 games."""
    if not stats:
        return stats
    sample = max(
        float(stats.get("passing_yards", 0)),
        float(stats.get("rushing_yards", 0)),
        float(stats.get("receiving_yards", 0)),
        float(stats.get("def_tackles_solo", 0)),
        1.0,
    )
    if sample >= 8000:
        divisor = 4.0 * _N_GAMES
    elif sample >= 5000:
        divisor = 3.0 * _N_GAMES
    elif sample >= 2500:
        divisor = 2.0 * _N_GAMES
    else:
        divisor = 1.0 * _N_GAMES
    return {k: float(v) / divisor for k, v in stats.items()}


def _score_roster(players: list[dict]) -> float:
    """Returns estimated Super Bowl probability in [0, 100] for a given roster."""
    off_score = 0.0
    def_pts_allowed_delta = 0.0
    fg_pts = 0.0

    pos_slot_counter: dict[str, int] = {}
    for p in players:
        pos = p["position"]
        pos_slot_counter[pos] = pos_slot_counter.get(pos, 0) + 1
        depth = pos_slot_counter[pos]
        depth_scale = {1: 1.0, 2: 0.50, 3: 0.30}.get(depth, 0.20)

        pg = _per_game_stats(p["stats"])

        if pos in OFFENSE_POS:
            for stat, w in _OFF_WEIGHTS.items():
                if stat in pg:
                    off_score += float(pg[stat]) * w * depth_scale

        elif pos in DEFENSE_POS or p.get("slot_label") in ("Nickel", "Dime"):
            sacks = float(pg.get("def_sacks", 0))
            tackles = float(pg.get("def_tackles_solo", 0))
            ints = float(pg.get("def_interceptions", 0))
            pass_def = float(pg.get("def_pass_defended", 0))
            unit = (sacks * _DEF_WEIGHTS["def_sacks"]
                    + tackles * _DEF_WEIGHTS["def_tackles_solo"]
                    + ints * _DEF_WEIGHTS["def_interceptions"]
                    + pass_def * _DEF_WEIGHTS["def_pass_defended"])
            def_pts_allowed_delta += unit * depth_scale

        elif pos == "K":
            fg_per_game = float(pg.get("fg_made", 0))
            fg_pts += fg_per_game * _FG_WEIGHT

    ppg = float(np.clip(off_score + fg_pts + 10.0, 12.0, 45.0))

    NFL_AVG_PPG = 23.0
    opp_ppg = float(np.clip(NFL_AVG_PPG - def_pts_allowed_delta, 10.0, 35.0))

    margin = ppg - opp_ppg
    win_prob = 1 / (1 + np.exp(-0.12 * margin))
    expected_wins = win_prob * 17

    playoff_prob = float(1 / (1 + np.exp(-0.7 * (expected_wins - 9.5))))
    win_quality = float(np.clip((expected_wins - 7) / 6, 0.3, 1.5))
    sb_prob = playoff_prob * (1 / 14) * win_quality * 100

    return float(np.clip(sb_prob, 0.0, 25.0))

def _is_valid_roster(players: list[dict], formation: tuple[str, str]) -> bool:
    """Check that a roster meets the exact formation slot counts and salary cap."""
    total_salary = sum(p["salary"] for p in players)
    if total_salary > SALARY_CAP:
        return False

    required = FORMATION_ROSTERS[formation]
    slot_counts: dict[str, int] = {}
    pos_counts: dict[str, int] = {}
    for p in players:
        lbl = p.get("slot_label")
        if lbl in ("Nickel", "Dime"):
            slot_counts[lbl] = slot_counts.get(lbl, 0) + 1
        else:
            pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

    for slot, count in required.items():
        if slot in ("Nickel", "Dime"):
            if slot_counts.get(slot, 0) < count:
                return False
        else:
            if pos_counts.get(slot, 0) < count:
                return False

    return True


def _random_roster(pool: list[dict], formation_pool: list[tuple[str, str]] | None = None) -> tuple[list[dict], tuple[str, str]]:
    """
    Generate a random valid roster from the pool for a randomly chosen formation.
    Fills exact slot counts per the formation, position by position.
    """
    pool_by_pos: dict[str, list[dict]] = {}
    for p in pool:
        pool_by_pos.setdefault(p["position"], []).append(p)

    nd_pool = [p for p in pool if p["position"] in _NICKEL_DIME_POSITIONS]
    _formations = formation_pool if formation_pool else FORMATIONS

    for _ in range(300):
        formation = random.choice(_formations)
        required = FORMATION_ROSTERS[formation]
        selected: list[dict] = []
        used_names: set[str] = set()
        budget = SALARY_CAP
        failed = False

        for slot_label, count in required.items():
            if slot_label in ("Nickel", "Dime"):
                candidates = [p for p in nd_pool if p["name"] not in used_names and p["salary"] <= budget]
            else:
                candidates = [p for p in pool_by_pos.get(slot_label, []) if p["name"] not in used_names and p["salary"] <= budget]

            if len(candidates) < count:
                failed = True
                break

            chosen = random.sample(candidates, count)
            for c in chosen:
                c = dict(c)
                if slot_label in ("Nickel", "Dime"):
                    c["slot_label"] = slot_label
                selected.append(c)
                used_names.add(c["name"])
                budget -= c["salary"]

        if not failed and _is_valid_roster(selected, formation):
            return selected, formation

    return [], _formations[0]


def _slot_key(p: dict) -> str:
    """Returns the slot identifier used in FORMATION_ROSTERS for a given player."""
    lbl = p.get("slot_label")
    return lbl if lbl in ("Nickel", "Dime") else p["position"]


def _crossover(
    parent_a: list[dict], parent_b: list[dict], formation: tuple[str, str]
) -> list[dict]:
    """Position-aware crossover: coin-flip per slot between parent_a and parent_b."""
    required = FORMATION_ROSTERS[formation]
    a_by_slot: dict[str, list[dict]] = {}
    for p in parent_a:
        a_by_slot.setdefault(_slot_key(p), []).append(p)
    b_by_slot: dict[str, list[dict]] = {}
    for p in parent_b:
        b_by_slot.setdefault(_slot_key(p), []).append(p)

    child: list[dict] = []
    used_names: set[str] = set()
    budget = SALARY_CAP

    for slot, count in required.items():
        a_opts = a_by_slot.get(slot, [])
        b_opts = b_by_slot.get(slot, [])
        for i in range(count):
            primary = a_opts[i] if i < len(a_opts) else None
            secondary = b_opts[i] if i < len(b_opts) else None
            if random.random() < 0.5:
                primary, secondary = secondary, primary
            chosen = None
            for candidate in [primary, secondary]:
                if candidate and candidate["name"] not in used_names and candidate["salary"] <= budget:
                    chosen = candidate
                    break
            if chosen:
                child.append(chosen)
                used_names.add(chosen["name"])
                budget -= chosen["salary"]
    return child


def _mutate(
    roster: list[dict], pool: list[dict], formation: tuple[str, str], mutation_rate: float = 0.15
) -> list[dict]:
    """Randomly replace some players with pool alternatives of the same slot."""
    nd_pool = [p for p in pool if p["position"] in _NICKEL_DIME_POSITIONS]
    mutated = roster[:]
    for i in range(len(mutated)):
        if random.random() > mutation_rate:
            continue
        current = mutated[i]
        slot = _slot_key(current)
        current_names = {p["name"] for p in mutated}
        other_salary = sum(p["salary"] for j, p in enumerate(mutated) if j != i)
        budget_for_slot = SALARY_CAP - other_salary

        if slot in ("Nickel", "Dime"):
            candidates = [p for p in nd_pool if p["name"] not in current_names and p["salary"] <= budget_for_slot]
        else:
            candidates = [
                p for p in pool
                if p["position"] == slot
                and p["name"] not in current_names
                and p["salary"] <= budget_for_slot
            ]
        if candidates:
            replacement = dict(random.choice(candidates))
            if slot in ("Nickel", "Dime"):
                replacement["slot_label"] = slot
            mutated[i] = replacement

    return mutated


def run_genetic_algorithm(
    pool: list[dict],
    population_size: int = 40,
    n_generations: int = 60,
    elite_k: int = 5,
    mutation_rate: float = 0.15,
    allowed_formations: list[tuple[str, str]] | None = None,
) -> tuple[list[dict], tuple[str, str], list[float]]:
    formation_pool = allowed_formations if allowed_formations else FORMATIONS

    population_with_formations = [_random_roster(pool, formation_pool) for _ in range(population_size)]
    population_with_formations = [(r, f) for r, f in population_with_formations if len(r) >= 10]
    while len(population_with_formations) < population_size:
        population_with_formations.append(_random_roster(pool, formation_pool))

    fitness_history: list[float] = []
    best_roster: list[dict] = population_with_formations[0][0]
    best_formation: tuple[str, str] = population_with_formations[0][1]
    best_fitness = -1.0

    for gen in range(n_generations):
        scored = [(r, f, _score_roster(r)) for r, f in population_with_formations]
        scored.sort(key=lambda x: x[2], reverse=True)

        gen_best = scored[0][2]
        fitness_history.append(gen_best)

        if gen_best > best_fitness:
            best_fitness = gen_best
            best_roster = scored[0][0]
            best_formation = scored[0][1]

        new_population_with_formations = [(r, f) for r, f, _ in scored[:elite_k]]

        while len(new_population_with_formations) < population_size:
            tournament = random.sample(scored, min(4, len(scored)))
            tournament.sort(key=lambda x: x[2], reverse=True)
            parent_a, formation_a = tournament[0][0], tournament[0][1]
            parent_b = tournament[1][0]
            formation = formation_a

            child = _crossover(parent_a, parent_b, formation)
            child = _mutate(child, pool, formation, mutation_rate)

            if _is_valid_roster(child, formation):
                new_population_with_formations.append((child, formation))
            else:
                new_population_with_formations.append((parent_a, formation))

        population_with_formations = new_population_with_formations

        if gen > 10 and len(fitness_history) > 5:
            recent_improvement = fitness_history[-1] - fitness_history[-5]
            if recent_improvement < 0.01:
                mutation_rate = min(0.35, mutation_rate * 1.1)

    return best_roster, best_formation, fitness_history


class OptimizeRequest(BaseModel):
    salary_cap: int | None = None
    locked_players: list[str] = []
    excluded_players: list[str] = []
    population_size: int = 40
    n_generations: int = 60
    offense_type: str | None = None
    defense_type: str | None = None

@app.post("/optimize-team")
async def optimize_team(request: OptimizeRequest):
    global SALARY_CAP
    if request.salary_cap:
        SALARY_CAP = request.salary_cap

    try:
        pool = _build_player_pool(n_players=350)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build player pool: {e}")


    pool = [p for p in pool if p["name"] not in request.excluded_players]
    locked = [p for p in pool if p["name"] in request.locked_players]
    if locked:
        locked_salary = sum(p["salary"] for p in locked)
        if locked_salary > SALARY_CAP:
            raise HTTPException(status_code=400, detail="Locked players exceed salary cap")
        SALARY_CAP -= locked_salary
        pool = [p for p in pool if p["name"] not in request.locked_players]

    allowed_formations = [
        f for f in FORMATIONS
        if (request.offense_type is None or f[0] == request.offense_type)
        and (request.defense_type is None or f[1] == request.defense_type)
    ] or FORMATIONS

    best_roster, best_formation, fitness_history = run_genetic_algorithm(
        pool=pool,
        population_size=request.population_size,
        n_generations=request.n_generations,
        allowed_formations=allowed_formations,
    )

    if locked:
        best_roster = locked + best_roster
        SALARY_CAP += sum(p["salary"] for p in locked)

    seen: set[str] = set()
    best_roster = [p for p in best_roster if not (p["name"] in seen or seen.add(p["name"]))]  # type: ignore[func-returns-value]

    total_salary = sum(p["salary"] for p in best_roster)
    cap_space_remaining = SALARY_CAP - total_salary
    fitness = _score_roster(best_roster)

    POS_ORDER = ["QB", "RB", "FB", "WR", "TE", "OT", "G", "C", "DE", "DT", "NT", "DL",
                 "LB", "OLB", "ILB", "MLB", "CB", "FS", "SS", "S", "SAF",
                 "Nickel", "Dime", "K", "P", "RS", "LS"]

    def sort_key(p: dict) -> int:
        lbl = p.get("slot_label") or p["position"]
        return POS_ORDER.index(lbl) if lbl in POS_ORDER else 99

    best_roster.sort(key=sort_key)

    pos_counts: dict[str, int] = {}
    for p in best_roster:
        lbl = p.get("slot_label") or p["position"]
        pos_counts[lbl] = pos_counts.get(lbl, 0) + 1

    offense_type, defense_type = best_formation
    return {
        "status": "success",
        "superbowl_probability": round(fitness, 2),
        "offense_type": offense_type,
        "defense_type": defense_type,
        "total_salary": total_salary,
        "salary_cap": SALARY_CAP,
        "cap_space_remaining": cap_space_remaining,
        "roster_size": len(best_roster),
        "position_breakdown": pos_counts,
        "fitness_history": [round(f, 3) for f in fitness_history],
        "roster": [
            {
                "name": p["name"],
                "position": p.get("slot_label") or p["position"],
                "nfl_team": p["nfl_team"],
                "salary": p["salary"],
                "salary_display": f"${p['salary']:,}",
            }
            for p in best_roster
        ],
    }


@app.get("/player-pool")
async def get_player_pool():
    """Return the current player pool with salaries (for frontend display)."""
    try:
        pool = _build_player_pool(n_players=350)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build player pool: {e}")

    pos_counts: dict[str, int] = {}
    for p in pool:
        pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

    return {
        "status": "success",
        "total_players": len(pool),
        "position_breakdown": pos_counts,
        "salary_cap": SALARY_CAP,
        "players": [
            {
                "name": p["name"],
                "position": p["position"],
                "nfl_team": p["nfl_team"],
                "salary": p["salary"],
                "salary_display": f"${p['salary']:,}",
            }
            for p in pool
        ],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("optimize_team:app", host="0.0.0.0", port=8005, reload=True)
