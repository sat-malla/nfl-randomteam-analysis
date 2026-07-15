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

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

mongo_client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
mongo_db = mongo_client["nfl-random-teams"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POS_STAT_MAPPING = {
    "QB": ["passing_yards", "passing_tds", "interceptions", "carries", "rushing_yards", "rushing_tds"],
    "RB": ["carries", "rushing_yards", "rushing_tds", "receptions", "targets", "receiving_yards", "receiving_tds"],
    "FB": ["carries", "rushing_yards", "rushing_tds", "receptions", "targets", "receiving_yards", "receiving_tds"],
    "WR": ["receptions", "receiving_yards", "receiving_tds", "targets", "carries", "rushing_yards", "rushing_tds"],
    "TE": ["receptions", "receiving_yards", "receiving_tds", "targets", "carries", "rushing_yards", "rushing_tds"],
    "DE": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "DT": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "NT": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "DL": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "LB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "OLB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "ILB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "MLB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "FS": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "SS": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "S": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "SAF": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "CB": ["def_tackles_solo", "def_sacks", "def_interceptions", "def_passes_defended", "def_fumbles_forced"],
    "K": ["fg_made", "fg_att", "fg_pct"],
    "P": ["punt_return_yards"],
    "OT": [],
    "G": [],
    "C": [],
    "LS": [],
    "RS": ["kickoff_return_yards", "kickoff_returns", "punt_returns", "punt_return_yards"],
}

POSITION_PRIMARY_STAT = {
    "QB":     "passing_yards",
    "RB":     "rushing_yards",
    "WR":     "receiving_yards",
    "TE":     "receiving_yards",
    "K":      "fg_made",
    "P":      "punt_return_yards",
    "RS":     "kickoff_return_yards",
    "LB":     "def_tackles_solo",
    "OLB":    "def_tackles_solo",
    "ILB":    "def_tackles_solo",
    "MLB":    "def_tackles_solo",
    "CB":     "def_interceptions",
    "FS":     "def_tackles_solo",
    "SS":     "def_tackles_solo",
    "Nickel": "def_interceptions",
    "Dime":   "def_interceptions",
    "DE":     "def_sacks",
    "DT":     "def_sacks",
    "NT":     "def_sacks",
    "DL":     "def_sacks",
    "OT":     None,
    "G":      None,
    "C":      None,
    "LS":     None,
}

POSITION_DEFAULTS = {
    "passing_yards":         (230, 60),
    "passing_tds":           (1.5, 1.0),
    "passing_interceptions": (0.8, 0.7),
    "rushing_yards":         (65, 35),
    "carries":               (15, 8),
    "receiving_yards":       (55, 40),
    "receiving_tds":         (0.4, 0.5),
    "receptions":            (4, 3),
    "targets":               (6, 4),
    "fg_made":               (2, 1),
    "fg_att":                (2.5, 1),
    "fg_pct":                (0.82, 0.15),
    "def_tackles_solo":      (4, 2),
    "def_sacks":             (0.4, 0.6),
    "def_interceptions":     (0.1, 0.3),
    "def_pass_defended":     (0.5, 0.7),
    "punt_returns":          (2, 1),
    "punt_return_yards":     (18, 10),
    "kickoff_returns":       (1.5, 1),
    "kickoff_return_yards":  (28, 12),
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

# print(fetch_player_historical_stats(["Josh Allen", "Justin Herbert"]))

def fetch_team_historical_stats(teams):
    response = supabase.table("team_stats").select("*").in_("team", teams).gte("season", 2021).execute()
    return pd.DataFrame(response.data)

# print(fetch_team_historical_stats(["Buffalo Bills"]))

def build_player_distributions(player_stats, player_name, player_pos):
    # Monte Carlo Sampling
    stat_cols = POS_STAT_MAPPING.get(player_pos, [])
    if not stat_cols:
        return {}

    player_data = player_stats[player_stats["player_display_name"] == player_name].copy()
    distributions = {}

    for sc in stat_cols:
        if player_data.empty or sc not in player_data.columns:
            mean, std = POSITION_DEFAULTS.get(sc, (10, 5))
        else:
            values = pd.to_numeric(player_data[sc], errors='coerce').dropna()
            if values.empty:
                mean, std = POSITION_DEFAULTS.get(sc, (10, 5))
            else:
                mean = float(values.mean())
                if len(values) > 1:
                    std = float(values.std())
                else:
                    _, pos_std = POSITION_DEFAULTS.get(sc, (10, 5))
                    std = pos_std
            
        std = max(std, 0.1)
        a = -mean / std
        distribution = stats.truncnorm(a=a, b=5, loc=mean, scale=std)
        distributions[sc] = distribution
    
    return distributions

def build_all_player_dists(team, player_stats):
    result = {}
    for player in team["players"]:
        name = player["name"]
        position = player["position"]
        dists = build_player_distributions(player_stats, name, position)
        result[name] = {
            "position": position,
            "distributions": dists
        }

    return result

def build_pos_correlation_mat(team_players):
    n = len(team_players)
    corr = np.eye(n)
    offense_pos = {"QB", "RB", "WR", "TE"}
    defense_pos = {"LB", "CB", "FS", "SS", "Nickel", "Dime", "DE", "DT", "NT"}
    ol_pos  = {"OT", "G", "C", "LS"}

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

# Simulation
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

    # ensure positive semidefinite — done once, not per game
    eigenvalues, eigenvectors = np.linalg.eigh(flat_corr)
    eigenvalues = np.maximum(eigenvalues, 1e-6)
    flat_corr = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    if not np.all(np.isfinite(flat_corr)):
        flat_corr = np.eye(n)

    return flat_keys, flat_corr

def sample_all_games(distributions, flat_keys, flat_corr, n_season_sims, n_games):
    # Sample all sims × all games in one multivariate_normal call
    n = len(flat_keys)
    total_samples = n_season_sims * n_games
    mv_samples = np.random.multivariate_normal(np.zeros(n), flat_corr, size=total_samples)
    uniform_samples = norm.cdf(mv_samples)

    raw = np.zeros((total_samples, n))
    for i, (name, sc) in enumerate(flat_keys):
        dist = distributions[name]["distributions"][sc]
        raw[:, i] = dist.ppf(np.clip(uniform_samples[:, i], 1e-6, 1 - 1e-6))

    # shape: (n_season_sims, n_games, n_stats)
    return raw.reshape(n_season_sims, n_games, n)

def yards_to_points(passing_yards, rushing_yards, fg_made):
    base_points = (passing_yards + rushing_yards) / 10
    td_bonus = base_points * 0.15
    fg_points = fg_made * 3
    return base_points + td_bonus + fg_points

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

    passing_factor = 230 / max(avg_passing, 1)
    rushing_factor = 115 / max(avg_rushing, 1)
    return (passing_factor + rushing_factor) / 2
    
def sim_season(team, distributions, corr_matrix, team_stats, n_season_sims=300, coach_multiplier=1.0):
    n_games = 17
    schedule = generate_schedule(n_games)

    all_player_stats = {
        p["name"]: {stat: [] for stat in distributions[p["name"]]["distributions"].keys()}
        for p in team["players"]
        if distributions[p["name"]]["distributions"]
    }

    # build corr matrix and sample ALL games for ALL sims in one shot
    flat_keys, flat_corr = build_flat_corr(distributions, corr_matrix)
    if flat_corr is None:
        return {}

    # shape: (n_season_sims, n_games, n_stats)
    all_samples = sample_all_games(distributions, flat_keys, flat_corr, n_season_sims, n_games)
    all_samples = np.maximum(all_samples, 0)

    # build lookup: stat_key -> column index
    key_to_idx = {key: i for i, key in enumerate(flat_keys)}
    stat_col_indices = {name: {} for name in all_player_stats}
    for name in all_player_stats:
        for stat in all_player_stats[name]:
            k = (name, stat)
            if k in key_to_idx:
                stat_col_indices[name][stat] = key_to_idx[k]

    # opponent strengths and home boosts per game
    opp_strengths = np.array([get_opponent_strength(g["opponent"], team_stats) for g in schedule])
    home_boosts = np.array([1.05 if g["home"] else 0.97 for g in schedule])

    # find column indices for win calculation
    passing_idx = key_to_idx.get(next((k for k in flat_keys if k[1] == "passing_yards"), (None, None)), None)
    rushing_idx = key_to_idx.get(next((k for k in flat_keys if k[1] == "rushing_yards"), (None, None)), None)
    fg_idx = key_to_idx.get(next((k for k in flat_keys if k[1] == "fg_made"), (None, None)), None)

    # vectorized win calculation across all sims and games
    # all_samples: (n_sims, n_games, n_stats)
    multipliers = opp_strengths * home_boosts * coach_multiplier  # (n_games,)

    passing_per_game = all_samples[:, :, passing_idx] * multipliers if passing_idx is not None else np.zeros((n_season_sims, n_games))
    rushing_per_game = all_samples[:, :, rushing_idx] * multipliers if rushing_idx is not None else np.zeros((n_season_sims, n_games))
    fg_per_game = all_samples[:, :, fg_idx] * multipliers if fg_idx is not None else np.zeros((n_season_sims, n_games))

    team_points = yards_to_points(passing_per_game, rushing_per_game, fg_per_game)
    opp_points = np.random.normal(
        loc=team_points * (1 / opp_strengths),
        scale=5,
        size=(n_season_sims, n_games)
    )
    wins_matrix = (team_points > opp_points)
    all_szn_wins = wins_matrix.sum(axis=1)

    # accumulate player season totals
    for name in all_player_stats:
        for stat, col_idx in stat_col_indices[name].items():
            # sum across games with multiplier, shape (n_sims,)
            season_totals = (all_samples[:, :, col_idx] * multipliers).sum(axis=1)
            all_player_stats[name][stat] = season_totals.tolist()
    
    wins_array = np.array(all_szn_wins)

    nfl_team_map = {p["name"]: TEAM_MAPPING.get(p["nfl_team"], p["nfl_team"]) for p in team["players"]}

    POS_ORDER = ["QB", "RB", "FB", "WR", "TE", "OT", "G", "C", "DE", "DT", "NT", "DL",
                 "LB", "OLB", "ILB", "MLB", "CB", "Nickel", "Dime", "FS", "SS", "S", "SAF", "DB", "K", "P", "RS", "LS"]

    player_projs_raw = {}
    for name, stats in all_player_stats.items():
        pos = distributions[name]["position"]
        primary_stat = POSITION_PRIMARY_STAT.get(pos)
        primary_arr = np.array(stats.get(primary_stat, [0])) if primary_stat else np.array([0])
        player_projs_raw[name] = {
            "position": pos,
            "nfl_team": nfl_team_map.get(name, ""),
            "_primary_proj": float(np.mean(primary_arr)),
            "stats": {
                stat: {
                    "projected_total": round(float(np.mean(arr))),
                    "floor": round(float(np.percentile(arr, 10))),
                    "ceiling": round(float(np.percentile(arr, 90))),
                }
                for stat, arr in {s: np.array(v) for s, v in stats.items()}.items()
            }
        }

    # Sort: by position group first, then by primary stat descending (stronger player first)
    sorted_names = sorted(
        player_projs_raw.keys(),
        key=lambda n: (
            POS_ORDER.index(player_projs_raw[n]["position"]) if player_projs_raw[n]["position"] in POS_ORDER else 99,
            -player_projs_raw[n]["_primary_proj"]
        )
    )
    player_projs = {}
    for name in sorted_names:
        entry = player_projs_raw[name]
        player_projs[name] = {k: v for k, v in entry.items() if k != "_primary_proj"}
    
    win_vals = wins_array.astype(float)
    playoff_prob_per_sim = 1 / (1 + np.exp(-0.7 * (win_vals - 9.5)))
    playoff_probability = round(float(np.mean(playoff_prob_per_sim)) * 100, 1)

    avg_wins = float(np.mean(wins_array))
    win_quality = np.clip((avg_wins - 7) / 6, 0.3, 1.5)
    superbowl_probability = round(playoff_probability * (1 / 14) * win_quality, 1)

    return {
        "schedule": schedule,
        "projected_wins": round(float(np.mean(wins_array)), 1),
        "win_floor": int(np.percentile(wins_array, 10)),
        "win_ceiling": int(np.percentile(wins_array, 90)),
        "playoff_probability": playoff_probability,
        "superbowl_probability": superbowl_probability,
        "player_projections": player_projs,
        "win_distribution": {str(w): int(np.sum(wins_array == w)) for w in range(18)},
    }

def fetch_coach_factor(coach_name, qb_name):
    """
    Returns a multiplier (0.90–1.10) based on:
    - Coach's historical win rate from schedules (vs NFL average of ~0.5)
    - Bonus if coach has coached this QB on the same team in the same season
    """
    if not coach_name:
        return 1.0, {}

    # Fetch all games where this coach was involved
    home_games = supabase.table("schedules").select("home_score,away_score,season").execute()
    coach_home = supabase.table("coaches").select("season,team").eq("head_coach", coach_name).execute()

    coach_teams = {row["season"]: row["team"] for row in (coach_home.data or [])}

    if not coach_teams:
        return 1.0, {"coach": coach_name, "note": "No historical data found"}

    # For each season the coach coached, check home/away win rate
    wins = 0
    losses = 0
    sched_data = supabase.table("schedules").select("season,home_team,away_team,home_score,away_score").execute()
    df = pd.DataFrame(sched_data.data or [])

    for season, team in coach_teams.items():
        home = df[(df["season"] == season) & (df["home_team"] == team)]
        wins += int((home["home_score"] > home["away_score"]).sum())
        losses += int((home["home_score"] < home["away_score"]).sum())
        away = df[(df["season"] == season) & (df["away_team"] == team)]
        wins += int((away["away_score"] > away["home_score"]).sum())
        losses += int((away["away_score"] < away["home_score"]).sum())

    total = wins + losses
    win_rate = wins / total if total > 0 else 0.5
    # Scale: 0.5 win_rate = 1.0x, 0.7 = ~1.06x, 0.3 = ~0.94x
    coach_multiplier = 0.88 + (win_rate * 0.24)
    coach_multiplier = float(np.clip(coach_multiplier, 0.90, 1.10))

    # QB–coach familiarity bonus: check if coach coached a team that had this QB
    qb_familiarity = False
    qb_data = supabase.table("player_stats").select("season,team").eq("player_display_name", qb_name).eq("position", "QB").execute()
    qb_seasons = {(row["season"], row["team"]) for row in (qb_data.data or [])}
    for season, team in coach_teams.items():
        if (season, team) in qb_seasons:
            qb_familiarity = True
            break

    if qb_familiarity:
        coach_multiplier = float(np.clip(coach_multiplier + 0.03, 0.90, 1.10))

    meta = {
        "coach": coach_name,
        "seasons_coached": len(coach_teams),
        "record": f"{wins}–{losses}",
        "win_rate": round(win_rate, 3),
        "coach_multiplier": round(coach_multiplier, 3),
        "qb_familiarity": qb_familiarity,
    }
    return coach_multiplier, meta


def run_full_analysis(team_id):
    team = get_generated_team(team_id)
    player_names = [p["name"] for p in team["players"]]
    nfl_teams = list(set(TEAM_MAPPING[p["nfl_team"]] for p in team["players"]))

    qb = next((p["name"] for p in team["players"] if p["position"] == "QB"), "")
    coach_name = team.get("head_coach", "")
    coach_multiplier, coach_meta = fetch_coach_factor(coach_name, qb)

    player_stats = fetch_player_historical_stats(player_names)
    team_stats = fetch_team_historical_stats(nfl_teams)

    dists = build_all_player_dists(team, player_stats)
    corr_matrix = build_corr_matrix(team["players"])

    results = sim_season(team, dists, corr_matrix, team_stats, coach_multiplier=coach_multiplier)
    results["coach_analysis"] = coach_meta

    return results


app = FastAPI()

class AnalyzeRequest(BaseModel):
    team_id: str

@app.post("/analyze-team")
async def analyze_team(request: AnalyzeRequest):
    try:
        results = run_full_analysis(request.team_id)

        go_url = os.getenv("GO_API_URL", "http://localhost:8000")
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{go_url}/api/analysis/{request.team_id}",
                json={"team_id": request.team_id, "analysis": results},
            )

        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))