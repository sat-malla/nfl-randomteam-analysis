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
def simulate_game_stats(distributions, corr_mat, n_sims=500):
    flat_keys = []
    for name, data in distributions.items():
        for sc in data["distributions"].keys():
            flat_keys.append((name, sc))
    
    if not flat_keys:
        return pd.DataFrame()
    
    n = len(flat_keys)
    names = list(distributions.keys())

    if corr_mat.shape[0] != len(names):
        corr_mat = np.eye(len(names))
    
    flat_corr = np.eye(n)
    for i, (p1, _) in enumerate(flat_keys):
        for j, (p2, _) in enumerate(flat_keys):
            if i == j:
                continue
            pi = names.index(p1)
            pj = names.index(p2)
            
            if pi < corr_mat.shape[0] and pj < corr_mat.shape[1]:
                if p1 == p2:
                    flat_corr[i][j] = 0.7
                else:
                    flat_corr[i][j] = corr_mat[pi][pj] * 0.8
            else:
                flat_corr[i][j] = 0.0
    
    flat_corr = np.nan_to_num(flat_corr, nan=0.0, posinf=1.0, neginf=-1.0)
    flat_corr = np.clip(flat_corr, -1.0, 1.0)
    np.fill_diagonal(flat_corr, 1.0)

    print("flat_corr stats:")
    print(f"  shape: {flat_corr.shape}")
    print(f"  min: {np.min(flat_corr)}")
    print(f"  max: {np.max(flat_corr)}")
    print(f"  has nan: {np.any(np.isnan(flat_corr))}")
    print(f"  has inf: {np.any(np.isinf(flat_corr))}")
    print(f"  diagonal: {np.diag(flat_corr)}")
    print(flat_corr)

    # positive semidefinite (x^T A x >= 0) -> all eigenvalues are nonnegative
    eigenvalues, eigenvectors = np.linalg.eigh(flat_corr)
    eigenvalues = np.maximum(eigenvalues, 1e-6)
    flat_corr = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    if not np.all(np.isfinite(flat_corr)):
        print("WARNING: flat_corr still has non-finite values, falling back to identity")
        flat_corr = np.eye(n)

    # gaussian copula
    mean = np.zeros(n)
    mv_samples = np.random.multivariate_normal(mean, flat_corr, size=n_sims)
    uniform_samples = norm.cdf(mv_samples)

    # applying distributions
    correlated_stats = np.zeros((n_sims, n))
    for i, (name, sc) in enumerate(flat_keys):
        dist = distributions[name]["distributions"][sc]
        correlated_stats[:, i] = dist.ppf(
            np.clip(uniform_samples[:, i], 1e-6, 1 - 1e-6)
        )

    columns = pd.MultiIndex.from_tuples(flat_keys, names=["player", "stat"])
    return pd.DataFrame(correlated_stats, columns=columns)

def simulate_single_game(distributions, corr_matrix):
    game_sims = simulate_game_stats(distributions, corr_matrix, n_sims=500)
    if game_sims.empty:
        return {}

    result = {}
    for name, data in distributions.items():
        if not data["distributions"]:
            continue
        result[name] = {}
        for sc in data["distributions"].keys():
            if (name, sc) in game_sims.columns:
                result[name][sc] = float(
                    game_sims[(name, sc)].median()
                )
    return result

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
    
def sim_season(team, distributions, corr_matrix, team_stats, n_season_sims=1000):
    schedule = generate_schedule(17)

    all_szn_wins = []
    all_player_stats = {
        p["name"]: {stat: [] for stat in distributions[p["name"]]["distributions"].keys()}
        for p in team["players"]
        if distributions[p["name"]]["distributions"]
    }

    for _ in range(n_season_sims):
        szn_wins = 0
        season_totals = {
            name: {stat: 0 for stat in all_player_stats[name]}
            for name in all_player_stats
        }

        for game in schedule:
            opp_strength = get_opponent_strength(game["opponent"], team_stats)
            home_boost = 1.05 if game["home"] else 0.97
            game_stats = simulate_single_game(distributions, corr_matrix)

            game_passing = 0
            game_rushing = 0
            game_fg = 0

            for player_name, stats in game_stats.items():
                if player_name not in season_totals:
                    continue
                for stat_col, value in stats.items():
                    adjusted = max(0, value * opp_strength * home_boost)
                    season_totals[player_name][stat_col] += adjusted

                    if stat_col == "passing_yards":
                        game_passing += adjusted
                    elif stat_col == "rushing_yards":
                        game_rushing += adjusted
                    elif stat_col == "fg_made":
                        game_fg += adjusted

            team_points = yards_to_points(game_passing, game_rushing, game_fg)
            opp_points = np.random.normal(
                loc=team_points * (1 / opp_strength),
                scale=5
            )

            if team_points > opp_points:
                szn_wins += 1
            
        all_szn_wins.append(szn_wins)
        for name in all_player_stats:
            for stat in all_player_stats[name]:
                all_player_stats[name][stat].append(season_totals[name][stat])
    
    wins_array = np.array(all_szn_wins)

    player_projs = {}
    for name, stats in all_player_stats.items():
        pos = distributions[name]["position"]
        player_projs[name] = {
            "position": pos,
            "stats": {
                stat: {
                    "projected_total": round(float(np.mean(arr))),
                    "floor": round(float(np.percentile(arr, 10))),
                    "ceiling": round(float(np.percentile(arr, 90))),
                }
                for stat, arr in {s: np.array(v) for s, v in stats.items()}.items()
            }
        }
    
    return {
        "schedule": schedule,
        "projected_wins": round(float(np.mean(wins_array)), 1),
        "win_floor": int(np.percentile(wins_array, 10)),
        "win_ceiling": int(np.percentile(wins_array, 90)),
        "playoff_probability": round(float(np.mean(wins_array >= 9)) * 100, 1),
        "superbowl_probability": round(float(np.mean(wins_array >= 9)) * 25, 1),
        "player_projections": player_projs,
        "win_distribution": {str(w): int(np.sum(wins_array == w)) for w in range(18)},
    }

def run_full_analysis(team_id):
    team = get_generated_team(team_id)
    player_names = [p["name"] for p in team["players"]]
    nfl_teams = list(set(TEAM_MAPPING[p["nfl_team"]] for p in team["players"]))
    
    player_stats = fetch_player_historical_stats(player_names)
    team_stats = fetch_team_historical_stats(nfl_teams)

    dists = build_all_player_dists(team, player_stats)
    corr_matrix = build_corr_matrix(team["players"])

    results = sim_season(team, dists, corr_matrix, team_stats)
    
    return results


app = FastAPI()

class AnalyzeRequest(BaseModel):
    team_id: str

@app.post("/analyze-team")
async def analyze_team(request: AnalyzeRequest):
    try:
        results = run_full_analysis(request.team_id)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))