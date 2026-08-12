"""
build_wide_table.py  —  Data Preparation / Reshaping Layer

Architecture note
-----------------
This file is ONLY a data pipeline. It contains zero simulation math.
It extracts raw data from Supabase + nflreadpy, reshapes it into one
wide row per team-season, and writes the result to:
  - wide_team_seasons.csv   (input to TabSyn training on Colab)
  - Supabase table `team_seasons_wide`  (optional persistence)

The Generative Matrix Sampling Layer (team_analysis.py) is a separate
concern and never imports from this file. Swapping out the old
multivariate-normal sampler for TabSyn inference requires only changes
to team_analysis.py — this file is untouched.

Wide row schema (one row = one complete team-season):
  Offense: QB, WR1-3, RB1-2, TE1-2 + team passing/rushing totals
  Defense: edge1-2, dt1-2, lb1-2, cb1-2, s1
  Spec. Tm.: K (fg+pat), P (punts), RS1 (returns)
  OL/LS: unit-level sacks/hits/ypc proxies + per-slot snap shares from nflreadpy.load_snap_counts (Tx2, Gx2, Cx1, LS)
"""

import os
import pandas as pd
import numpy as np
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

START_SEASON = 2015
END_SEASON = 2025
SEASON_TYPE = "REG"

TEAM_MAPPING = {
    "ARI": "Arizona Cardinals", "ARZ": "Arizona Cardinals",
    "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BLT": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "CLV": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions",
    "GB":  "Green Bay Packers", "HOU": "Houston Texans",
    "HST": "Houston Texans", "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LAR": "Los Angeles Rams", "LA": "Los Angeles Rams",
    "SL":  "Los Angeles Rams", "STL": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers","SD": "Los Angeles Chargers",
    "LV":  "Las Vegas Raiders", "OAK": "Las Vegas Raiders",
    "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE":  "New England Patriots","NO": "New Orleans Saints",
    "NYG": "New York Giants", "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF":  "San Francisco 49ers", "SEA": "Seattle Seahawks",
    "TB":  "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

def normalise_team(col: pd.Series) -> pd.Series:
    return col.map(lambda t: TEAM_MAPPING.get(t, t) if isinstance(t, str) else t)


def fetch_supabase_pages(table: str, filters: dict) -> pd.DataFrame:
    """Page through Supabase (1 000-row limit per request)."""
    rows, start, page_size = [], 0, 1000
    while True:
        q = supabase.table(table).select("*")
        for col, val in filters.items():
            q = q.in_(col, val) if isinstance(val, list) else q.eq(col, val)
        batch = (q.range(start, start + page_size - 1).execute().data or [])
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return pd.DataFrame(rows)


def rank_group(df: pd.DataFrame, rank_col: str, n: int, prefix: str, stat_cols: list) -> dict:
    # Sum weekly rows per player into season totals before ranking
    agg_cols = list({rank_col} | set(stat_cols))
    numeric  = [c for c in agg_cols if c in df.columns]
    if not df.empty and "player_id" in df.columns:
        df = df.groupby("player_id")[numeric].sum().reset_index()
    df = df.sort_values(rank_col, ascending=False).head(n).reset_index(drop=True)
    out = {}
    for slot in range(1, n + 1):
        label = f"{prefix}{slot}"
        for sc in stat_cols:
            out[f"{label}_{sc}"] = (
                float(df.loc[slot - 1, sc])  # type: ignore
                if slot - 1 < len(df) and sc in df.columns
                else 0.0
            )
    return out


def extract_player_stats() -> pd.DataFrame:
    ps = fetch_supabase_pages("player_stats", {"season_type": SEASON_TYPE})
    ps = ps[ps["season"].between(START_SEASON, END_SEASON)].copy()

    if "interceptions" in ps.columns and "passing_interceptions" not in ps.columns:
        ps = ps.rename(columns={"interceptions": "passing_interceptions"}) # type: ignore

    numeric_cols = [
        "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions",
        "carries", "rushing_yards", "rushing_tds",
        "targets", "receptions", "receiving_yards", "receiving_tds",
        "def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended",
        "fg_made", "fg_att", "fg_pct",
        "kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards",
    ]
    for c in numeric_cols:
        ps[c] = pd.to_numeric(ps.get(c, 0), errors="coerce").fillna(0.0)

    ps["team"] = normalise_team(ps["team"])
    return ps


def extract_team_stats() -> pd.DataFrame:
    """Pull team_stats from Supabase — weekly rows, REG season only."""
    ts = fetch_supabase_pages("team_stats", {"season_type": SEASON_TYPE})
    ts = ts[ts["season"].between(START_SEASON, END_SEASON)].copy()

    for c in ["passing_yards", "passing_tds", "rushing_yards", "rushing_tds",
              "carries", "def_sacks", "def_interceptions",
              "sacks_suffered", "def_qb_hits",
              "pt_att", "pt_yards", "pt_inside_20", "pt_net_yards",
              "pat_made", "pat_att"]:
        ts[c] = pd.to_numeric(ts.get(c, 0), errors="coerce").fillna(0.0)

    ts["team"] = normalise_team(ts["team"])
    return ts


def extract_snap_counts() -> pd.DataFrame:
    """Pull snap_counts from Supabase (OL + LS only, stored by nfl_data_fetch_and_store.py)."""
    print("  Fetching snap_counts from Supabase...")
    sc = fetch_supabase_pages("snap_counts", {})
    sc = sc[sc["season"].between(START_SEASON, END_SEASON)].copy()
    sc["offense_pct"] = pd.to_numeric(sc["offense_pct"], errors="coerce").fillna(0.0)
    sc["st_pct"] = pd.to_numeric(sc["st_pct"], errors="coerce").fillna(0.0)
    sc["team"] = normalise_team(sc["team"])
    return sc


def build_ol_ls_features(ts: pd.DataFrame, sc: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-team-season OL/LS feature block from already-extracted
    team_stats (ts) and snap_counts (sc) DataFrames.
    Both inputs come purely from Supabase — no nflreadpy calls here.
    """
    seasons = list(range(START_SEASON, END_SEASON + 1))
    rows = []

    for season in seasons:
        ts_s = ts[ts["season"] == season]
        sc_s = sc[sc["season"] == season]
        teams = sorted(
            set(ts_s["team"].dropna().unique()) |
            set(sc_s["team"].dropna().unique())
        )

        for team in teams:
            row = {"team": team, "season": int(season)}

            # ── OL unit proxies (summed from weekly team_stats rows) ───────
            ts_t = ts_s[ts_s["team"] == team]
            if not ts_t.empty:
                row["ol_sacks_allowed"]        = float(ts_t["sacks_suffered"].sum())
                row["ol_qb_hits_allowed"]      = float(ts_t["def_qb_hits"].sum())
                total_rush_yds = float(ts_t["rushing_yards"].sum())
                total_carries  = float(ts_t["carries"].sum())
                row["ol_rush_yards_per_carry"] = round(
                    total_rush_yds / max(total_carries, 1), 2
                )
            else:
                row["ol_sacks_allowed"]        = 0.0
                row["ol_qb_hits_allowed"]      = 0.0
                row["ol_rush_yards_per_carry"] = 0.0

            # ── OL slot snap shares ────────────────────────────────────────
            sc_t = sc_s[sc_s["team"] == team]

            def ol_slots(position_code: str, n_slots: int, col_prefix: str):
                players = sc_t[sc_t["position"] == position_code].copy()
                if players.empty:
                    for slot in range(1, n_slots + 1):
                        row[f"{col_prefix}{slot}_snap_share"] = 0.0
                        row[f"{col_prefix}{slot}_games"]      = 0
                    return
                agg = (
                    players.groupby("player")
                    .agg(season_snap_share=("offense_pct", "mean"),
                         games_played=("offense_pct", "count"))
                    .reset_index()
                    .sort_values("season_snap_share", ascending=False)
                    .head(n_slots)
                    .reset_index(drop=True)
                )
                for slot in range(1, n_slots + 1):
                    if slot - 1 < len(agg):
                        row[f"{col_prefix}{slot}_snap_share"] = round(float(agg.loc[slot - 1, "season_snap_share"]), 3)
                        row[f"{col_prefix}{slot}_games"]      = int(agg.loc[slot - 1, "games_played"])
                    else:
                        row[f"{col_prefix}{slot}_snap_share"] = 0.0
                        row[f"{col_prefix}{slot}_games"]      = 0

            ol_slots("T", 2, "ot")
            ol_slots("G", 2, "og")
            ol_slots("C", 1, "c")

            # ── Long snapper ──────────────────────────────────────────────
            ls_players = sc_t[sc_t["position"] == "LS"].copy()
            if not ls_players.empty:
                ls_agg = (
                    ls_players.groupby("player")
                    .agg(season_snap_share=("st_pct", "mean"),
                         games_played=("st_pct", "count"))
                    .reset_index()
                    .sort_values("season_snap_share", ascending=False)
                    .reset_index(drop=True)
                )
                row["ls_primary_snap_share"] = round(float(ls_agg.loc[0, "season_snap_share"]), 3)
                row["ls_roster_churn"]       = int(len(ls_agg))
            else:
                row["ls_primary_snap_share"] = 0.0
                row["ls_roster_churn"]       = 0

            rows.append(row)

    return pd.DataFrame(rows)


def reshape_to_wide(ps: pd.DataFrame, ts: pd.DataFrame,
                    ol_ls: pd.DataFrame) -> pd.DataFrame:
    """
    Merge player_stats + team_stats + ol_ls features into one wide row
    per team-season.
    """
    seasons = list(range(START_SEASON, END_SEASON + 1))
    wide_rows = []

    for season in seasons:
        ps_s = ps[ps["season"] == season]
        ts_s = ts[ts["season"] == season]
        teams = sorted(
            set(ps_s["team"].dropna().unique()) |
            set(ts_s["team"].dropna().unique())
        )

        for team in teams:
            row: dict = {"team": team, "season": int(season)}
            ps_t = ps_s[ps_s["team"] == team].copy()
            ts_t = ts_s[ts_s["team"] == team]

            for dc in ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"]:
                ps_t[dc] = pd.to_numeric(ps_t.get(dc, 0), errors="coerce").fillna(0.0)

            qbs = ps_t[ps_t["position"] == "QB"].copy()
            if not qbs.empty and "player_id" in qbs.columns:
                qb_sum = qbs.groupby("player_id")[[
                    "attempts", "completions", "passing_yards", "passing_tds",
                    "passing_interceptions", "carries", "rushing_yards", "rushing_tds",
                ]].sum().reset_index()
                qb = qb_sum.sort_values("attempts", ascending=False).iloc[0]
                row.update({
                    "qb_attempts":      float(qb.get("attempts", 0)),
                    "qb_completions":   float(qb.get("completions", 0)),
                    "qb_passing_yards": float(qb.get("passing_yards", 0)),
                    "qb_passing_tds":   float(qb.get("passing_tds", 0)),
                    "qb_interceptions": float(qb.get("passing_interceptions", 0)),
                    "qb_carries":       float(qb.get("carries", 0)),
                    "qb_rushing_yards": float(qb.get("rushing_yards", 0)),
                    "qb_rushing_tds":   float(qb.get("rushing_tds", 0)),
                })
            else:
                for k in ["qb_attempts", "qb_completions", "qb_passing_yards", "qb_passing_tds",
                          "qb_interceptions", "qb_carries", "qb_rushing_yards", "qb_rushing_tds"]:
                    row[k] = 0.0

            row.update(rank_group(
                ps_t[ps_t["position"] == "WR"], rank_col="targets", n=3, prefix="wr",
                stat_cols=["targets", "receptions", "receiving_yards", "receiving_tds"],
            ))

            row.update(rank_group(
                ps_t[ps_t["position"] == "RB"], rank_col="carries", n=2, prefix="rb",
                stat_cols=["carries", "rushing_yards", "rushing_tds",
                           "targets", "receptions", "receiving_yards", "receiving_tds"],
            ))

            row.update(rank_group(
                ps_t[ps_t["position"] == "TE"], rank_col="targets", n=2, prefix="te",
                stat_cols=["targets", "receptions", "receiving_yards", "receiving_tds"],
            ))

            if not ts_t.empty:
                row.update({
                    "team_passing_yards":     float(ts_t["passing_yards"].sum()),
                    "team_passing_tds":       float(ts_t["passing_tds"].sum()),
                    "team_rushing_yards":     float(ts_t["rushing_yards"].sum()),
                    "team_rushing_tds":       float(ts_t["rushing_tds"].sum()),
                    "team_def_sacks":         float(ts_t["def_sacks"].sum()),
                    "team_def_interceptions": float(ts_t["def_interceptions"].sum()),
                })
            else:
                for k in ["team_passing_yards", "team_passing_tds", "team_rushing_yards",
                          "team_rushing_tds", "team_def_sacks", "team_def_interceptions"]:
                    row[k] = 0.0

            def def_rank(positions, rank_col, n, prefix, stat_cols):
                df = ps_t[ps_t["position"].isin(positions)].copy()
                result = rank_group(df, rank_col=rank_col, n=n, prefix=prefix, stat_cols=stat_cols)
                rename = {
                    "def_sacks": "sacks", "def_tackles_solo": "tackles",
                    "def_pass_defended": "pass_defended", "def_interceptions": "interceptions",
                }
                return {
                    f"{prefix}{slot}_{rename.get(sc, sc)}": result[f"{prefix}{slot}_{sc}"]
                    for slot in range(1, n + 1)
                    for sc in stat_cols
                }

            row.update(def_rank(["DE", "OLB"], "def_sacks", 2, "edge",
                                ["def_sacks", "def_tackles_solo", "def_pass_defended"]))
            row.update(def_rank(["DT", "NT", "DL"], "def_tackles_solo", 2, "dt",
                                ["def_tackles_solo", "def_sacks", "def_pass_defended"]))
            row.update(def_rank(["LB", "ILB", "MLB"], "def_tackles_solo", 2, "lb",
                                ["def_tackles_solo", "def_sacks", "def_interceptions", "def_pass_defended"]))
            row.update(def_rank(["CB"], "def_pass_defended", 2, "cb",
                                ["def_interceptions", "def_pass_defended", "def_tackles_solo"]))
            row.update(def_rank(["FS", "SS", "S", "SAF"], "def_tackles_solo", 1, "s",
                                ["def_tackles_solo", "def_interceptions", "def_pass_defended"]))

            ks = ps_t[ps_t["position"] == "K"].copy()
            for kc in ["fg_made", "fg_att", "fg_pct"]:
                ks[kc] = pd.to_numeric(ks.get(kc, 0), errors="coerce").fillna(0.0)
            if not ks.empty and "player_id" in ks.columns:
                ks_sum = ks.groupby("player_id")[["fg_made", "fg_att"]].sum().reset_index()
                k = ks_sum.sort_values("fg_made", ascending=False).iloc[0]
                row["k_fg_made"] = float(k.get("fg_made", 0))
                row["k_fg_att"]  = float(k.get("fg_att", 0))
                row["k_fg_pct"]  = round(row["k_fg_made"] / max(row["k_fg_att"], 1), 3)
            else:
                row["k_fg_made"] = 0.0
                row["k_fg_att"]  = 0.0
                row["k_fg_pct"]  = 0.0
            row["k_pat_made"] = float(ts_t["pat_made"].sum()) if not ts_t.empty and "pat_made" in ts_t.columns else 0.0
            row["k_pat_att"]  = float(ts_t["pat_att"].sum())  if not ts_t.empty and "pat_att"  in ts_t.columns else 0.0

            if not ts_t.empty and "pt_att" in ts_t.columns:
                row["p_punt_attempts"] = float(ts_t["pt_att"].sum())
                row["p_punt_yards"]    = float(ts_t["pt_yards"].sum() if "pt_yards" in ts_t.columns else 0)
                row["p_punt_inside_20"]= float(ts_t["pt_inside_20"].sum() if "pt_inside_20" in ts_t.columns else 0)
                row["p_punt_net_yards"]= float(ts_t["pt_net_yards"].sum() if "pt_net_yards" in ts_t.columns else 0)
            else:
                pass_tds = row.get("team_passing_tds", 35.0) or 35.0
                punt_scale = max(0.5, min(1.5, (35.0 - pass_tds) / 35.0 + 1.0))
                row["p_punt_attempts"] = round(70.0 * punt_scale, 1)
                row["p_punt_yards"]    = round(3100.0 * punt_scale, 0)
                row["p_punt_inside_20"]= round(22.0 * punt_scale, 1)
                row["p_punt_net_yards"]= round(2500.0 * punt_scale, 0)

            rs = ps_t[ps_t["position"] == "RS"].copy()
            for rc in ["kickoff_returns", "kickoff_return_yards", "punt_returns", "punt_return_yards"]:
                rs[rc] = pd.to_numeric(rs.get(rc, 0), errors="coerce").fillna(0.0)
            if not rs.empty:
                r1 = rs.sort_values("kickoff_return_yards", ascending=False).iloc[0]
                row["rs1_kr_att"] = float(r1.get("kickoff_returns", 0))
                row["rs1_kr_yds"] = float(r1.get("kickoff_return_yards", 0))
                row["rs1_pr_att"] = float(r1.get("punt_returns", 0))
                row["rs1_pr_yds"] = float(r1.get("punt_return_yards", 0))
            else:
                row["rs1_kr_att"] = 0.0
                row["rs1_kr_yds"] = 0.0
                row["rs1_pr_att"] = 0.0
                row["rs1_pr_yds"] = 0.0

            wide_rows.append(row)

    df_wide = pd.DataFrame(wide_rows)

    ol_ls_clean = ol_ls.drop_duplicates(subset=["team", "season"])
    df_wide = df_wide.merge(ol_ls_clean, on=["team", "season"], how="left")

    ol_ls_cols = [c for c in df_wide.columns if c.startswith(("ot", "og", "c1_", "ls_", "ol_"))]
    for c in ol_ls_cols:
        df_wide[c] = df_wide[c].fillna(0.0)

    return df_wide


def save_csv(df_wide: pd.DataFrame) -> str:
    out_path = os.path.join(os.path.dirname(__file__), "wide_team_seasons.csv")
    df_wide.to_csv(out_path, index=False)
    print(f"  Saved CSV → {out_path}  ({df_wide.shape[0]} rows × {df_wide.shape[1]} cols)")
    return out_path


def upsert_supabase(df_wide: pd.DataFrame):
    records = df_wide.to_dict(orient="records")
    clean = [
        {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()}
        for r in records
    ]
    batch_size = 200
    for i in range(0, len(clean), batch_size):
        batch = clean[i: i + batch_size]
        supabase.table("team_seasons_wide").upsert(batch, on_conflict="team,season").execute()
        print(f"  Upserted rows {i}–{i + len(batch) - 1}")
    print("  Supabase upsert complete.")


def validate(df_wide: pd.DataFrame):
    wr_td_sum = df_wide["wr1_receiving_tds"] + df_wide["wr2_receiving_tds"] + df_wide["wr3_receiving_tds"]
    violations = (wr_td_sum > df_wide["team_passing_tds"] + 5).sum()
    print(f"\n  WR TD sum > team_passing_tds + 5 (data noise): {violations} rows")
    print(f"  Median WR TD sum       : {wr_td_sum.median():.1f}")
    print(f"  Median team_passing_tds: {df_wide['team_passing_tds'].median():.1f}")
    print(f"  Median ol_sacks_allowed: {df_wide['ol_sacks_allowed'].median():.1f}")
    print(f"  Median ot1_snap_share  : {df_wide['ot1_snap_share'].median():.3f}")
    print(f"  Median ls_primary_snap : {df_wide['ls_primary_snap_share'].median():.3f}")
    print(f"  Mean ls_roster_churn   : {df_wide['ls_roster_churn'].mean():.2f}")
    print(f"  Median p_punt_attempts : {df_wide['p_punt_attempts'].median():.1f}")
    print(f"  Median k_fg_made       : {df_wide['k_fg_made'].median():.1f}")
    seasons_per_team = df_wide.groupby("season").size()
    print(f"\n  Teams per season (sample):\n{seasons_per_team.to_string()}")


if __name__ == "__main__":
    print("── EXTRACT ────────────────────────────────────────────────────────")
    print("  Fetching player_stats from Supabase...")
    ps = extract_player_stats()
    print(f"  player_stats: {ps.shape}")

    print("  Fetching team_stats from Supabase...")
    ts = extract_team_stats()
    print(f"  team_stats:   {ts.shape}")

    sc = extract_snap_counts()
    print(f"  snap_counts:  {sc.shape}")

    print("\n── BUILD OL/LS FEATURES ───────────────────────────────────────────")
    ol_ls = build_ol_ls_features(ts, sc)
    print(f"  ol_ls:        {ol_ls.shape}")

    print("\n── RESHAPE ────────────────────────────────────────────────────────")
    df_wide = reshape_to_wide(ps, ts, ol_ls)
    print(f"  Wide table:   {df_wide.shape}")

    print("\n── VALIDATE ───────────────────────────────────────────────────────")
    validate(df_wide)

    print("\n── LOAD ───────────────────────────────────────────────────────────")
    save_csv(df_wide)
    upsert_supabase(df_wide)

    print("\nDone. wide_team_seasons.csv is ready for TabSyn training.")
