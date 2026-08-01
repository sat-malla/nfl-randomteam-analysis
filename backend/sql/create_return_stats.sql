create table return_stats (
  id bigint generated always as identity primary key,
  player_display_name text not null,
  player_id text,
  position text,
  team text,
  season int not null,
  kickoff_returns int default 0,
  kickoff_return_yards int default 0,
  punt_returns int default 0,
  punt_return_yards int default 0,
  unique (player_display_name, season)
);
