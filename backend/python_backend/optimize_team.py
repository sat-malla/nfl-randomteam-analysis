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
import random
import os
import certifi
import httpx

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="NFL Team Optimizer")

SALARY_CAP = 200_000_000

_POS_SALARY_RANGE = {
    "QB": (5_000_000, 55_000_000),
    "RB": (800_000, 16_000_000),
    "WR": (900_000, 30_000_000),
    "TE": (800_000, 20_000_000),
    "OT": (1_000_000, 22_000_000),
    "G": (1_000_000, 18_000_000),
    "C": (1_000_000, 15_000_000),
    "DE": (1_000_000, 25_000_000),
    "DT": (900_000, 22_000_000),
    "NT": (900_000, 15_000_000),
    "DL": (900_000, 18_000_000),
    "LB": (900_000, 20_000_000),
    "OLB": (900_000, 20_000_000),
    "ILB": (900_000, 18_000_000),
    "MLB": (900_000, 18_000_000),
    "SLB": (900_000, 18_000_000),
    "WLB": (900_000, 18_000_000),
    "CB": (900_000, 22_000_000),
    "FS": (900_000, 18_000_000),
    "SS": (900_000, 18_000_000),
    "S": (900_000, 18_000_000),
    "SAF": (900_000, 18_000_000),
    "K": (700_000, 6_000_000),
    "P": (700_000, 4_000_000),
    "RS": (700_000, 3_000_000),
    "FB": (700_000, 3_000_000),
    "LS": (700_000, 1_500_000),
}
_DEFAULT_SALARY_RANGE = (700_000, 5_000_000)

# Exact slot counts per formation, mirroring generate-team.tsx exactly.
# Each formation tuple: (offense_type, defense_type) -> {position: count}
FORMATION_ROSTERS: dict[tuple[str, str], dict[str, int]] = {
    ("3 WR 1 TE", "4-3 Base Defense"): {
        "QB": 1, "RB": 2, "WR": 3, "TE": 1,
        "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 2, "LB": 3, "CB": 2, "FS": 1, "SS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
    ("2 WR 2 TE", "4-3 Base Defense"): {
        "QB": 1, "RB": 2, "WR": 2, "TE": 2,
        "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 2, "LB": 3, "CB": 2, "FS": 1, "SS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
    ("3 WR 1 TE", "3-4 Base Defense"): {
        "QB": 1, "RB": 2, "WR": 3, "TE": 1,
        "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 1, "LB": 4, "CB": 2, "FS": 1, "SS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
    ("2 WR 2 TE", "3-4 Base Defense"): {
        "QB": 1, "RB": 2, "WR": 2, "TE": 2,
        "OT": 2, "G": 2, "C": 1,
        "DE": 2, "DT": 1, "LB": 4, "CB": 2, "FS": 1, "SS": 1,
        "Nickel": 1, "Dime": 1,
        "K": 1, "P": 1, "RS": 1, "LS": 1,
    },
}

FORMATIONS = list(FORMATION_ROSTERS.keys())

# Hard minimums that must hold across ALL formations (used for pool validation)
POSITION_MINIMUMS = {
    "QB": 1, "RB": 2, "WR": 2, "TE": 1,
    "OT": 2, "G": 2, "C": 1,
    "DE": 2, "DT": 1, "LB": 3, "CB": 2, "FS": 1, "SS": 1,
    "Nickel": 1, "Dime": 1,
    "K": 1, "P": 1, "RS": 1, "LS": 1,
}

ROSTER_SIZE = 29  # max across all formations (4-3 gives 29, 3-4 gives 28)

OFFENSE_POS = {"QB", "RB", "FB", "WR", "TE"}
DEFENSE_POS = {"DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB",
               "CB", "FS", "SS", "S", "SAF"}

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

_OFF_WEIGHTS = {
    "passing_yards": 0.0015,
    "passing_tds": 0.06,
    "passing_interceptions": -0.10,
    "rushing_yards": 0.0018,
    "rushing_tds": 0.05,
    "receiving_yards": 0.0016,
    "receiving_tds": 0.05,
    "carries": 0.002,
    "targets": 0.003,
    "receptions": 0.003,
}
_DEF_WEIGHTS = {
    "def_sacks": 0.04,
    "def_tackles_solo": 0.008,
    "def_interceptions": 0.05,
    "def_pass_defended": 0.02,
}
_FG_WEIGHT = 0.025
_PLAYER_POOL_CACHE: list[dict] | None = None

def _assign_salary(player_name: str, position: str, historical_df: pd.DataFrame) -> int:
    """
    Assign a synthetic salary based on the player's historical stats relative
    to position peers. Better historical performers get higher salaries,
    creating realistic optimization pressure.
    """
    lo, hi = _POS_SALARY_RANGE.get(position, _DEFAULT_SALARY_RANGE)
    stat_keys = _POS_STAT_KEYS.get(position, [])
    if not stat_keys or historical_df.empty:
        return int(random.uniform(lo, (lo + hi) / 2))

    player_data = historical_df[historical_df["player_display_name"] == player_name]
    if player_data.empty:
        return int(lo * random.uniform(1.0, 1.8))

    score = 0.0
    count = 0
    for sk in stat_keys[:2]:
        if sk in player_data.columns:
            val = pd.to_numeric(player_data[sk], errors="coerce").fillna(0).sum()
            if val > 0:
                score += float(val)
                count += 1
    if count == 0:
        return int(lo * random.uniform(1.0, 2.0))

    pos_df = historical_df[historical_df["position"] == position] if "position" in historical_df.columns else pd.DataFrame()
    if pos_df.empty:
        percentile = 0.5
    else:
        all_scores = []
        for p_name in pos_df["player_display_name"].unique():
            p_data = pos_df[pos_df["player_display_name"] == p_name]
            p_score = 0.0
            for sk in stat_keys[:2]:
                if sk in p_data.columns:
                    v = pd.to_numeric(p_data[sk], errors="coerce").fillna(0).sum()
                    p_score += float(v)
            all_scores.append(p_score)
        if len(all_scores) < 2:
            percentile = 0.5
        else:
            arr = np.array(all_scores)
            percentile = float(np.mean(arr <= score))

    percentile = np.clip(percentile, 0.0, 1.0)
    salary = lo + (hi - lo) * (percentile ** 1.6)
    noise = random.uniform(0.90, 1.10)
    return int(np.clip(salary * noise, lo, hi))

def _build_player_pool(n_players: int = 300) -> list[dict]:
    """
    Fetch a diverse pool of real NFL players from Supabase and annotate each
    with a synthetic salary.
    """
    global _PLAYER_POOL_CACHE
    if _PLAYER_POOL_CACHE is not None:
        return _PLAYER_POOL_CACHE

    response = supabase.table("player_stats").select(
        "player_display_name, position, recent_team, season, "
        "passing_yards, passing_tds, passing_interceptions, carries, rushing_yards, rushing_tds, "
        "receptions, targets, receiving_yards, receiving_tds, "
        "def_sacks, def_tackles_solo, def_interceptions, def_pass_defended, "
        "fg_made, fg_att"
    ).gte("season", 2022).execute()

    if not response.data:
        raise RuntimeError("Failed to fetch player pool from Supabase")

    df = pd.DataFrame(response.data)
    numeric_cols = [c for c in df.columns if c not in ("player_display_name", "position", "recent_team", "season")]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    agg = df.groupby(["player_display_name", "position", "recent_team"])[numeric_cols].sum().reset_index()
    agg["total_yards"] = agg.get("passing_yards", 0) + agg.get("rushing_yards", 0) + agg.get("receiving_yards", 0)
    agg["total_def"] = agg.get("def_tackles_solo", 0) + agg.get("def_sacks", 0) * 5
    agg = agg[(agg["total_yards"] > 50) | (agg["total_def"] > 5) |
              (agg["fg_made"] > 0) | (agg["position"].isin(["K", "P"]))]

    if len(agg) > n_players:
        agg["score"] = agg["total_yards"] + agg["total_def"] * 10
        top_half = agg.nlargest(n_players // 2, "score")
        rest = agg.drop(top_half.index).sample(min(n_players // 2, len(agg) - len(top_half)))
        agg = pd.concat([top_half, rest])

    players = []
    for _, row in agg.iterrows():
        pos = row["position"]
        salary = _assign_salary(row["player_display_name"], pos, df)
        stats = {c: float(row[c]) for c in numeric_cols if c in row}
        players.append({
            "name": row["player_display_name"],
            "position": pos,
            "nfl_team": row.get("recent_team", ""),
            "salary": salary,
            "stats": stats,
        })

    # Fetch punters from separate table
    try:
        punt_resp = supabase.table("punt_stats").select(
            "player_display_name, recent_team, season, punt_yards_season, punt_attempts_season"
        ).gte("season", 2022).execute()
        if punt_resp.data:
            punt_df = pd.DataFrame(punt_resp.data)
            for c in ["punt_yards_season", "punt_attempts_season"]:
                if c in punt_df.columns:
                    punt_df[c] = pd.to_numeric(punt_df[c], errors="coerce").fillna(0)
            punt_agg = punt_df.groupby(["player_display_name", "recent_team"])[
                ["punt_yards_season", "punt_attempts_season"]
            ].sum().reset_index()
            punt_agg = punt_agg[punt_agg["punt_attempts_season"] > 0]
            for _, row in punt_agg.iterrows():
                salary = _assign_salary(row["player_display_name"], "P", df)
                players.append({
                    "name": row["player_display_name"],
                    "position": "P",
                    "nfl_team": row.get("recent_team", ""),
                    "salary": salary,
                    "stats": {"punt_yards_season": float(row.get("punt_yards_season", 0)),
                              "punt_attempts_season": float(row.get("punt_attempts_season", 0))},
                })
    except Exception:
        pass

    # Fetch return specialists from separate table
    try:
        rs_resp = supabase.table("return_stats").select(
            "player_display_name, recent_team, season, kickoff_return_yards, kickoff_returns, punt_return_yards, punt_returns"
        ).gte("season", 2022).execute()
        if rs_resp.data:
            rs_df = pd.DataFrame(rs_resp.data)
            rs_num_cols = ["kickoff_return_yards", "kickoff_returns", "punt_return_yards", "punt_returns"]
            for c in rs_num_cols:
                if c in rs_df.columns:
                    rs_df[c] = pd.to_numeric(rs_df[c], errors="coerce").fillna(0)
            rs_agg = rs_df.groupby(["player_display_name", "recent_team"])[rs_num_cols].sum().reset_index()
            # Only genuine returners (≥10 returns total)
            rs_agg = rs_agg[(rs_agg["kickoff_returns"] + rs_agg["punt_returns"]) >= 10]
            for _, row in rs_agg.iterrows():
                salary = _assign_salary(row["player_display_name"], "RS", df)
                players.append({
                    "name": row["player_display_name"],
                    "position": "RS",
                    "nfl_team": row.get("recent_team", ""),
                    "salary": salary,
                    "stats": {c: float(row.get(c, 0)) for c in rs_num_cols},
                })
    except Exception:
        pass

    # Add LS (long snappers) as a synthetic position — use minimum salary, no stats
    # We create a small pool of generic LS entries since they're not tracked in Supabase
    for i in range(15):
        lo, _ = _POS_SALARY_RANGE.get("LS", _DEFAULT_SALARY_RANGE)
        players.append({
            "name": f"Long Snapper {i + 1}",
            "position": "LS",
            "nfl_team": "",
            "salary": int(random.uniform(lo, lo * 1.5)),
            "stats": {},
        })

    _PLAYER_POOL_CACHE = players
    return players


def _score_roster(players: list[dict]) -> float:
    """
    Returns estimated Super Bowl probability in [0, 100] for a given roster.
    """
    off_score = 0.0
    def_sacks = 0.0
    def_tackles = 0.0
    def_ints = 0.0
    fg_made = 0.0

    pos_slot_counter: dict[str, int] = {}
    for p in players:
        pos = p["position"]
        pos_slot_counter[pos] = pos_slot_counter.get(pos, 0) + 1
        depth = pos_slot_counter[pos]

        depth_scale = {1: 1.0, 2: 0.50, 3: 0.30}.get(depth, 0.20)
        stats = p["stats"]

        if pos in OFFENSE_POS:
            for stat, w in _OFF_WEIGHTS.items():
                if stat in stats:
                    off_score += float(stats[stat]) * w * depth_scale
        elif pos in DEFENSE_POS:
            def_sacks += float(stats.get("def_sacks", 0)) * depth_scale
            def_tackles += float(stats.get("def_tackles_solo", 0)) * depth_scale
            def_ints += float(stats.get("def_interceptions", 0)) * depth_scale
        elif pos == "K":
            fg_made += float(stats.get("fg_made", 0)) * _FG_WEIGHT


    ppg = np.clip(off_score + fg_made, 12.0, 45.0)

    sack_score = np.clip(def_sacks / max(2.5, 0.01), 0.7, 1.4)
    tackle_score = np.clip(def_tackles / max(25.0, 0.01), 0.7, 1.4)
    def_quality = float(np.clip((sack_score + tackle_score) / 2, 0.82, 1.18))

    NFL_AVG_PPG = 23.0
    opp_ppg = NFL_AVG_PPG / def_quality

    margin = ppg - opp_ppg
    win_prob_per_game = 1 / (1 + np.exp(-0.12 * margin))
    expected_wins = win_prob_per_game * 17

    playoff_prob = 1 / (1 + np.exp(-0.7 * (expected_wins - 9.5)))
    win_quality = np.clip((expected_wins - 7) / 6, 0.3, 1.5)
    sb_prob = playoff_prob * (1 / 14) * win_quality * 100

    return float(np.clip(sb_prob, 0.0, 25.0))

def _is_valid_roster(players: list[dict], formation: tuple[str, str]) -> bool:
    """Check that a roster meets the exact formation slot counts and salary cap."""
    total_salary = sum(p["salary"] for p in players)
    if total_salary > SALARY_CAP:
        return False

    required = FORMATION_ROSTERS[formation]
    pos_counts: dict[str, int] = {}
    for p in players:
        pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

    for pos, count in required.items():
        if pos_counts.get(pos, 0) < count:
            return False

    return True


def _random_roster(pool: list[dict]) -> tuple[list[dict], tuple[str, str]]:
    """
    Generate a random valid roster from the pool for a randomly chosen formation.
    Fills exact slot counts per the formation, position by position.
    Returns (roster, formation).
    """
    # Pool lookup by position for speed
    pool_by_pos: dict[str, list[dict]] = {}
    for p in pool:
        pool_by_pos.setdefault(p["position"], []).append(p)

    # Nickel and Dime use CB/SS/DB/S players — build a combined pool for them
    nickel_dime_pool = [
        p for p in pool if p["position"] in ("CB", "SS", "S", "SAF", "FS")
    ]

    for _ in range(300):
        formation = random.choice(FORMATIONS)
        required = FORMATION_ROSTERS[formation]
        selected: list[dict] = []
        used_names: set[str] = set()
        budget = SALARY_CAP
        failed = False

        for pos, count in required.items():
            if pos in ("Nickel", "Dime"):
                candidates = [p for p in nickel_dime_pool if p["name"] not in used_names and p["salary"] <= budget]
            else:
                candidates = [p for p in pool_by_pos.get(pos, []) if p["name"] not in used_names and p["salary"] <= budget]

            if len(candidates) < count:
                failed = True
                break

            chosen = random.sample(candidates, count)
            selected.extend(chosen)
            for c in chosen:
                used_names.add(c["name"])
                budget -= c["salary"]

        if not failed and _is_valid_roster(selected, formation):
            return selected, formation

    # Fallback with first formation
    formation = FORMATIONS[0]
    return selected, formation


def _crossover(
    parent_a: list[dict], parent_b: list[dict], formation: tuple[str, str]
) -> list[dict]:
    """
    Position-aware crossover: for each position slot in the formation, randomly
    pick the player from parent_a or parent_b (coin flip per slot).
    Falls back to the other parent's player if there's a name collision.
    """
    required = FORMATION_ROSTERS[formation]
    # Group each parent by position (ordered)
    a_by_pos: dict[str, list[dict]] = {}
    for p in parent_a:
        a_by_pos.setdefault(p["position"], []).append(p)
    b_by_pos: dict[str, list[dict]] = {}
    for p in parent_b:
        b_by_pos.setdefault(p["position"], []).append(p)

    child: list[dict] = []
    used_names: set[str] = set()
    budget = SALARY_CAP

    for pos, count in required.items():
        a_opts = a_by_pos.get(pos, [])
        b_opts = b_by_pos.get(pos, [])
        for slot in range(count):
            # Coin flip: prefer parent_a or parent_b for this slot
            primary = a_opts[slot] if slot < len(a_opts) else None
            secondary = b_opts[slot] if slot < len(b_opts) else None
            if random.random() < 0.5:
                primary, secondary = secondary, primary

            chosen = None
            for candidate in [primary, secondary]:
                if (candidate is not None
                        and candidate["name"] not in used_names
                        and candidate["salary"] <= budget):
                    chosen = candidate
                    break

            if chosen is None:
                # Pick any available pool player of this position
                chosen = primary or secondary
            if chosen:
                child.append(chosen)
                used_names.add(chosen["name"])
                budget -= chosen["salary"]

    return child


def _mutate(
    roster: list[dict], pool: list[dict], formation: tuple[str, str], mutation_rate: float = 0.15
) -> list[dict]:
    """
    Mutation: randomly replace some players with pool alternatives of the same
    position that fit under the remaining budget.
    """
    nickel_dime_pool = [p for p in pool if p["position"] in ("CB", "SS", "S", "SAF", "FS")]
    mutated = roster[:]
    for i in range(len(mutated)):
        if random.random() > mutation_rate:
            continue
        current = mutated[i]
        pos = current["position"]
        current_names = {p["name"] for p in mutated}
        other_salary = sum(p["salary"] for j, p in enumerate(mutated) if j != i)
        budget_for_slot = SALARY_CAP - other_salary

        if pos in ("Nickel", "Dime"):
            candidates = [p for p in nickel_dime_pool if p["name"] not in current_names and p["salary"] <= budget_for_slot]
        else:
            candidates = [
                p for p in pool
                if p["position"] == pos
                and p["name"] not in current_names
                and p["salary"] <= budget_for_slot
            ]
        if candidates:
            mutated[i] = random.choice(candidates)

    return mutated


def run_genetic_algorithm(
    pool: list[dict],
    population_size: int = 40,
    n_generations: int = 60,
    elite_k: int = 5,
    mutation_rate: float = 0.15,
) -> tuple[list[dict], tuple[str, str], list[float]]:
    population_with_formations = [_random_roster(pool) for _ in range(population_size)]
    # Filter out empty fallbacks
    population_with_formations = [(r, f) for r, f in population_with_formations if len(r) >= 10]
    while len(population_with_formations) < population_size:
        population_with_formations.append(_random_roster(pool))

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
            # Use the formation from the better parent
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

    best_roster, best_formation, fitness_history = run_genetic_algorithm(
        pool=pool,
        population_size=request.population_size,
        n_generations=request.n_generations,
    )

    if locked:
        best_roster = locked + best_roster
        SALARY_CAP += sum(p["salary"] for p in locked)

    total_salary = sum(p["salary"] for p in best_roster)
    cap_space_remaining = SALARY_CAP - total_salary
    fitness = _score_roster(best_roster)

    POS_ORDER = ["QB", "RB", "FB", "WR", "TE", "OT", "G", "C", "DE", "DT", "NT", "DL",
                 "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "FS", "SS", "S", "SAF",
                 "Nickel", "Dime", "K", "P", "RS", "LS"]
    best_roster.sort(key=lambda p: POS_ORDER.index(p["position"]) if p["position"] in POS_ORDER else 99)
    pos_counts: dict[str, int] = {}
    for p in best_roster:
        pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

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
                "position": p["position"],
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
