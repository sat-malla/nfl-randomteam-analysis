create table punt_stats (
  id bigint generated always as identity primary key,
  player_display_name text not null,
  player_id text,
  position text,
  team text,
  season int not null,
  punt_attempts_season int default 0,
  punt_yards_season int default 0,
  unique (player_display_name, season)
);
