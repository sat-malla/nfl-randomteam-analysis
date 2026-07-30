CREATE OR REPLACE VIEW v_player_pool AS
SELECT
    player_display_name,
    position,
    (array_agg(team ORDER BY season DESC))[1] AS team,
    COUNT(DISTINCT season) AS n_seasons,
    SUM(passing_yards) AS passing_yards,
    SUM(passing_tds) AS passing_tds,
    SUM(passing_interceptions) AS passing_interceptions,
    SUM(carries) AS carries,
    SUM(rushing_yards) AS rushing_yards,
    SUM(rushing_tds) AS rushing_tds,
    SUM(receptions) AS receptions,
    SUM(targets) AS targets,
    SUM(receiving_yards) AS receiving_yards,
    SUM(receiving_tds) AS receiving_tds,
    SUM(def_sacks) AS def_sacks,
    SUM(def_tackles_solo) AS def_tackles_solo,
    SUM(def_interceptions) AS def_interceptions,
    SUM(def_pass_defended) AS def_pass_defended,
    SUM(fg_made) AS fg_made,
    SUM(fg_att) AS fg_att
FROM player_stats
WHERE season >= 2023
GROUP BY player_display_name, position
HAVING
    SUM(passing_yards) + SUM(rushing_yards) + SUM(receiving_yards) > 50
    OR SUM(def_tackles_solo) + SUM(def_sacks) * 5 > 0
    OR SUM(def_interceptions) > 0
    OR SUM(def_pass_defended) > 0
    OR SUM(fg_made) > 0
    OR position IN (
        'K', 'P',
        'DE', 'DT', 'NT', 'DL',
        'LB', 'OLB', 'ILB', 'MLB', 'SLB', 'WLB',
        'CB', 'FS', 'SS', 'S', 'SAF', 'DB'
    );


CREATE OR REPLACE VIEW v_punt_pool AS
SELECT
    player_display_name,
    (array_agg(team ORDER BY season DESC))[1] AS team,
    SUM(punt_yards_season) AS punt_yards_season,
    SUM(punt_attempts_season) AS punt_attempts_season
FROM punt_stats
WHERE season >= 2023
GROUP BY player_display_name
HAVING SUM(punt_attempts_season) > 0;


CREATE OR REPLACE VIEW v_return_pool AS
SELECT
    player_display_name,
    (array_agg(team ORDER BY season DESC))[1] AS team,
    SUM(kickoff_return_yards)                 AS kickoff_return_yards,
    SUM(kickoff_returns)                      AS kickoff_returns,
    SUM(punt_return_yards)                    AS punt_return_yards,
    SUM(punt_returns)                         AS punt_returns
FROM return_stats
WHERE season >= 2023
GROUP BY player_display_name
HAVING SUM(kickoff_returns) + SUM(punt_returns) >= 10;
