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

POSITION_MINIMUMS = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "DE": 2,
    "LB": 2,
    "CB": 2,
    "K": 1,
}

ROSTER_SIZE = 22

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

def _is_valid_roster(players: list[dict]) -> bool:
    """Check that a roster meets position minimums and the salary cap."""
    total_salary = sum(p["salary"] for p in players)
    if total_salary > SALARY_CAP:
        return False

    pos_counts: dict[str, int] = {}
    for p in players:
        pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

    for pos, minimum in POSITION_MINIMUMS.items():
        if pos_counts.get(pos, 0) < minimum:
            return False

    return True

def _random_roster(pool: list[dict]) -> list[dict]:
    """
    Generate a random valid roster from the pool.
    Uses a stratified draw: first fill position minimums, then fill remaining
    slots randomly from remaining budget.
    """
    for _ in range(200):
        selected: list[dict] = []
        used_names: set[str] = set()
        budget = SALARY_CAP

        for pos, minimum in POSITION_MINIMUMS.items():
            candidates = [p for p in pool if p["position"] == pos and p["name"] not in used_names and p["salary"] <= budget]
            if len(candidates) < minimum:
                break
            chosen = random.sample(candidates, minimum)
            selected.extend(chosen)
            for c in chosen:
                used_names.add(c["name"])
                budget -= c["salary"]
        else:
            remaining = [p for p in pool if p["name"] not in used_names and p["salary"] <= budget]
            remaining_slots = ROSTER_SIZE - len(selected)
            if remaining_slots > 0 and len(remaining) >= remaining_slots:
                extra = random.sample(remaining, remaining_slots)
                selected.extend(extra)
                for c in extra:
                    budget -= c["salary"]

            if _is_valid_roster(selected):
                return selected

    return selected[:ROSTER_SIZE] if len(selected) >= ROSTER_SIZE else selected


def _crossover(parent_a: list[dict], parent_b: list[dict]) -> list[dict]:
    """
    Single-point crossover: take positions from parent A up to a random split,
    fill remaining slots with unique players from parent B.
    """
    split = random.randint(4, len(parent_a) - 4)
    child = parent_a[:split]
    child_names = {p["name"] for p in child}
    child_budget = SALARY_CAP - sum(p["salary"] for p in child)

    for p in parent_b:
        if len(child) >= ROSTER_SIZE:
            break
        if p["name"] not in child_names and p["salary"] <= child_budget:
            child.append(p)
            child_names.add(p["name"])
            child_budget -= p["salary"]

    return child


def _mutate(roster: list[dict], pool: list[dict], mutation_rate: float = 0.15) -> list[dict]:
    """
    Mutation: randomly replace some players with pool alternatives of the same
    position that fit under the remaining budget.
    """
    mutated = roster[:]
    for i in range(len(mutated)):
        if random.random() > mutation_rate:
            continue
        current = mutated[i]
        pos = current["position"]
        current_names = {p["name"] for p in mutated}
        other_salary = sum(p["salary"] for j, p in enumerate(mutated) if j != i)
        budget_for_slot = SALARY_CAP - other_salary

        alternatives = [
            p for p in pool
            if p["position"] == pos
            and p["name"] not in current_names
            and p["salary"] <= budget_for_slot
        ]
        if alternatives:
            mutated[i] = random.choice(alternatives)

    return mutated


def run_genetic_algorithm(
    pool: list[dict],
    population_size: int = 40,
    n_generations: int = 60,
    elite_k: int = 5,
    mutation_rate: float = 0.15,
) -> tuple[list[dict], list[float]]:
    population = [_random_roster(pool) for _ in range(population_size)]
    population = [r for r in population if len(r) >= ROSTER_SIZE // 2]
    while len(population) < population_size:
        population.append(_random_roster(pool))

    fitness_history: list[float] = []
    best_roster: list[dict] = population[0]
    best_fitness = -1.0

    for gen in range(n_generations):
        scored = [(r, _score_roster(r)) for r in population]
        scored.sort(key=lambda x: x[1], reverse=True)

        gen_best = scored[0][1]
        fitness_history.append(gen_best)

        if gen_best > best_fitness:
            best_fitness = gen_best
            best_roster = scored[0][0]

        new_population = [r for r, _ in scored[:elite_k]]

        while len(new_population) < population_size:
            tournament = random.sample(scored, min(4, len(scored)))
            tournament.sort(key=lambda x: x[1], reverse=True)
            parent_a = tournament[0][0]
            parent_b = tournament[1][0]

            child = _crossover(parent_a, parent_b)
            child = _mutate(child, pool, mutation_rate)

            if _is_valid_roster(child):
                new_population.append(child)
            else:
                new_population.append(parent_a)

        population = new_population

        if gen > 10 and len(fitness_history) > 5:
            recent_improvement = fitness_history[-1] - fitness_history[-5]
            if recent_improvement < 0.01:
                mutation_rate = min(0.35, mutation_rate * 1.1)

    return best_roster, fitness_history


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

    best_roster, fitness_history = run_genetic_algorithm(
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
                 "K", "P", "RS", "LS"]
    best_roster.sort(key=lambda p: POS_ORDER.index(p["position"]) if p["position"] in POS_ORDER else 99)
    pos_counts: dict[str, int] = {}
    for p in best_roster:
        pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

    return {
        "status": "success",
        "superbowl_probability": round(fitness, 2),
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
