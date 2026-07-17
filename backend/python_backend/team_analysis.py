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
    "SS": ["def_tackles_solo", "def_interceptions", "def_pass_defended"],
    "S": ["def_tackles_solo", "def_interceptions", "def_pass_defended"],
    "SAF": ["def_tackles_solo", "def_interceptions", "def_pass_defended"],
    # K: fg_made/fg_att are season totals in the DB — divided by 17 in build_player_distributions
    "K":  ["fg_made", "fg_att"],
    # P: no punter-specific stats in the schema; season punt volume derived from team drives
    "P":  ["punt_yards_season", "punt_attempts_season"],
    "OT": [],
    "G":  [],
    "C":  [],
    "LS": [],
    # RS: season totals in DB — divided by 17 to get per-game, then re-summed over 17 games
    "RS": ["kickoff_return_yards", "kickoff_returns", "punt_return_yards", "punt_returns"],
}

POSITION_PRIMARY_STAT = {
    "QB": "passing_yards",
    "RB": "rushing_yards",
    "WR": "receiving_yards",
    "TE": "receiving_yards",
    "K":  "fg_made",
    "P":  "punt_attempts_season",
    "RS": "kickoff_return_yards",
    "LB": "def_tackles_solo",
    "OLB": "def_tackles_solo",
    "ILB": "def_tackles_solo",
    "MLB": "def_tackles_solo",
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

POSITION_DEFAULTS = {
    "passing_yards": (230, 60),
    "passing_tds": (1.5, 1.0),
    "passing_interceptions": (0.8, 0.7),
    "rushing_yards": (65, 35),
    "carries": (15, 8),
    "receiving_yards": (55, 40),
    "receiving_tds": (0.4, 0.5),
    "receptions": (4, 3),
    "targets": (6, 4),
    # K: season totals (÷17 in build_player_distributions → per-game dist → ×17 in sim)
    # NFL season baseline: ~33 FG att, ~27 FG made for a starting kicker
    "fg_made": (27, 5),
    "fg_att": (33, 5),
    "fg_pct": (0.82, 0.08),
    "def_tackles_solo": (3.0, 1.5),
    "def_sacks": (0.4, 0.4),
    "def_interceptions": (0.02, 0.1),
    "def_pass_defended": (0.2, 0.3),
    # RS: season totals (÷17 in build_player_distributions → per-game dist → ×17 in sim)
    # Season baseline: ~25 KR for ~600 yds, ~20 PR for ~180 yds
    "kickoff_returns": (25, 8),
    "kickoff_return_yards": (600, 150),
    "punt_returns": (20, 6),
    "punt_return_yards": (180, 60),
    # P: synthetic season-total columns (punter stats not in schema, use team-drive estimates)
    # Season baseline: ~70 punts for ~3100 yards
    "punt_attempts_season": (70, 12),
    "punt_yards_season": (3100, 400),
}

POSITION_STAT_DEFAULTS = {
    "CB":  {"def_tackles_solo": (3.0, 1.5), "def_sacks": (0.05, 0.1),  "def_interceptions": (0.12, 0.2),  "def_pass_defended": (0.5, 0.4)},
    "FS":  {"def_tackles_solo": (3.5, 1.5), "def_sacks": (0.05, 0.1),  "def_interceptions": (0.12, 0.2),  "def_pass_defended": (0.45, 0.4)},
    "SS":  {"def_tackles_solo": (4.5, 2.0), "def_sacks": (0.08, 0.15), "def_interceptions": (0.08, 0.15), "def_pass_defended": (0.35, 0.3)},
    "S":   {"def_tackles_solo": (4.0, 2.0), "def_sacks": (0.06, 0.12), "def_interceptions": (0.10, 0.18), "def_pass_defended": (0.40, 0.35)},
    "SAF": {"def_tackles_solo": (4.0, 2.0), "def_sacks": (0.06, 0.12), "def_interceptions": (0.10, 0.18), "def_pass_defended": (0.40, 0.35)},
    "LB":  {"def_tackles_solo": (5.5, 2.0), "def_sacks": (0.25, 0.3),  "def_interceptions": (0.06, 0.12), "def_pass_defended": (0.25, 0.3)},
    "OLB": {"def_tackles_solo": (4.5, 2.0), "def_sacks": (0.35, 0.4),  "def_interceptions": (0.05, 0.1),  "def_pass_defended": (0.20, 0.25)},
    "ILB": {"def_tackles_solo": (5.5, 2.0), "def_sacks": (0.20, 0.25), "def_interceptions": (0.06, 0.12), "def_pass_defended": (0.25, 0.3)},
    "MLB": {"def_tackles_solo": (6.0, 2.5), "def_sacks": (0.18, 0.25), "def_interceptions": (0.05, 0.1),  "def_pass_defended": (0.20, 0.25)},
    "DE":  {"def_tackles_solo": (3.0, 1.5), "def_sacks": (0.42, 0.45), "def_interceptions": (0.02, 0.06), "def_pass_defended": (0.15, 0.2)},
    "DT":  {"def_tackles_solo": (3.5, 1.5), "def_sacks": (0.30, 0.4),  "def_interceptions": (0.01, 0.05), "def_pass_defended": (0.10, 0.15)},
    "NT":  {"def_tackles_solo": (4.0, 1.5), "def_sacks": (0.20, 0.3),  "def_interceptions": (0.01, 0.05), "def_pass_defended": (0.08, 0.12)},
    "DL":  {"def_tackles_solo": (3.5, 1.5), "def_sacks": (0.35, 0.4),  "def_interceptions": (0.01, 0.05), "def_pass_defended": (0.12, 0.18)},
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

# Volume stats that should be scaled down for backup/depth players
DEPTH_VOLUME_STATS = {
    "carries", "rushing_yards", "rushing_tds",
    "receptions", "targets", "receiving_yards", "receiving_tds",
    "fg_made", "fg_att",
    "kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards",
    "punt_attempts_season", "punt_yards_season",
}

# Multiplier applied to volume stat means by depth slot (1=starter, 2=backup, 3+=deep)
DEPTH_SLOT_SCALE = {1: 1.0, 2: 0.50, 3: 0.30}

# Stats stored as season totals in the DB that must be divided by N_GAMES before
# building the per-game distribution (the sim then re-sums them over N_GAMES).
SEASON_TOTAL_STATS = {
    "fg_made", "fg_att",
    "kickoff_returns", "kickoff_return_yards",
    "punt_returns", "punt_return_yards",
}
N_GAMES = 17

# Synthetic stats for positions with no real DB column — built entirely from defaults.
SYNTHETIC_STATS = {"punt_attempts_season", "punt_yards_season"}

def build_player_distributions(player_stats, player_name, player_pos, depth_slot=1):
    stat_cols = POS_STAT_MAPPING.get(player_pos, [])
    if not stat_cols:
        return {}

    player_data = player_stats[player_stats["player_display_name"] == player_name].copy()
    distributions = {}
    vol_scale = DEPTH_SLOT_SCALE.get(depth_slot, DEPTH_SLOT_SCALE[2])
    pos_defaults = POSITION_STAT_DEFAULTS.get(player_pos, {})

    for sc in stat_cols:
        fallback = pos_defaults.get(sc) or POSITION_DEFAULTS.get(sc, (10, 5))

        if sc in SYNTHETIC_STATS:
            # No real data exists — always use the season-total default directly.
            mean, std = fallback
        elif player_data.empty or sc not in player_data.columns:
            mean, std = fallback
            if sc in SEASON_TOTAL_STATS:
                mean, std = mean / N_GAMES, std / N_GAMES
        else:
            values = pd.to_numeric(player_data[sc], errors='coerce').dropna()
            if values.empty:
                mean, std = fallback
                if sc in SEASON_TOTAL_STATS:
                    mean, std = mean / N_GAMES, std / N_GAMES
            else:
                mean = float(values.mean())
                std = float(values.std()) if len(values) > 1 else fallback[1]
                # DB stores season totals for these — convert to per-game
                if sc in SEASON_TOTAL_STATS:
                    mean, std = mean / N_GAMES, std / N_GAMES

        if depth_slot > 1 and sc in DEPTH_VOLUME_STATS:
            mean = mean * vol_scale
            std = std * vol_scale

        std = max(std, 0.01)
        a = -mean / std
        distribution = stats.truncnorm(a=a, b=5, loc=mean, scale=std)
        distributions[sc] = distribution

    return distributions

def build_all_player_dists(team, player_stats):
    result = {}
    pos_slot_counter = {}
    for player in team["players"]:
        name = player["name"]
        position = player["position"]
        pos_slot_counter[position] = pos_slot_counter.get(position, 0) + 1
        depth_slot = pos_slot_counter[position]
        dists = build_player_distributions(player_stats, name, position, depth_slot=depth_slot)
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

    flat_keys, flat_corr = build_flat_corr(distributions, corr_matrix)
    if flat_corr is None:
        return {}

    all_samples = sample_all_games(distributions, flat_keys, flat_corr, n_season_sims, n_games)
    all_samples = np.maximum(all_samples, 0)

    key_to_idx = {key: i for i, key in enumerate(flat_keys)}
    stat_col_indices = {name: {} for name in all_player_stats}
    for name in all_player_stats:
        for stat in all_player_stats[name]:
            k = (name, stat)
            if k in key_to_idx:
                stat_col_indices[name][stat] = key_to_idx[k]

    opp_strengths = np.array([get_opponent_strength(g["opponent"], team_stats) for g in schedule])
    home_boosts = np.array([1.05 if g["home"] else 0.97 for g in schedule])

    passing_idx = key_to_idx.get(next((k for k in flat_keys if k[1] == "passing_yards"), (None, None)), None)
    rushing_idx = key_to_idx.get(next((k for k in flat_keys if k[1] == "rushing_yards"), (None, None)), None)
    fg_idx = key_to_idx.get(next((k for k in flat_keys if k[1] == "fg_made"), (None, None)), None)

    multipliers = opp_strengths * home_boosts * coach_multiplier

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

    for name in all_player_stats:
        for stat, col_idx in stat_col_indices[name].items():
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
            att_arr  = np.array(stats["fg_att"])
            safe_att = np.where(att_arr > 0, att_arr, 1.0)
            pct_arr  = (made_arr / safe_att) * 100
            stat_entries["fg_pct"] = {
                "projected_total": round(float(np.mean(pct_arr)), 1),
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
    Returns a multiplier (0.90-1.10) based on:
    - Coach's historical win rate from schedules (vs NFL average of ~0.5)
    - Bonus if coach has coached this QB on the same team in the same season
    """
    if not coach_name:
        return 1.0, {}

    home_games = supabase.table("schedules").select("home_score,away_score,season").execute()
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