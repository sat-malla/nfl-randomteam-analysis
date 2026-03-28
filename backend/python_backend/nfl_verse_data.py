import nflreadpy as nfl
import polars as pl

# schedules = nfl.load_schedules(seasons=list(range(2015, 2026)))
# # print(schedules)
# print(schedules.shape)
# print(schedules.columns)
# print(schedules.dtypes)
# print(schedules.head(3))
# print(schedules.null_count())


# player_stats = nfl.load_player_stats(seasons=list(range(2015, 2026)))
# # print(player_stats)

# print(player_stats.shape)
# print(player_stats.columns)
# print(player_stats.head(3))
# print(player_stats.null_count())

# print(dir(nfl))
# team_stats = nfl.load_team_stats(seasons=list(range(2015, 2026)))
# print("Team stats:")
# print(team_stats.shape)
# print(team_stats.columns)
# print(team_stats.head(3))
# print(team_stats.null_count())

rosters = nfl.load_rosters(seasons=list(range(2015, 2026)))
print("Rosters:")
print(rosters.shape)
print(rosters.columns)
print(rosters.head(3))
print(rosters.null_count())

# depth_charts = nfl.load_depth_charts(seasons=list(range(2015, 2026)))
# print("Depth charts:")
# print(depth_charts.shape)
# print(depth_charts.columns)
# print(depth_charts.head(3))
# print(depth_charts.null_count())
