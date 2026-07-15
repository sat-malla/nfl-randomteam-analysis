create table player_stats (
  id bigserial primary key,
  player_id text,
  player_display_name text,
  position text,
  season int,
  season_type text,
  team text,
  completions float,
  attempts float,
  passing_yards float,
  passing_tds float,
  passing_interceptions float,
  pacr float,
  carries float,
  rushing_yards float,
  rushing_tds float,
  rushing_fumbles float,
  receptions float,
  targets float,
  receiving_yards float,
  receiving_tds float,
  def_tackles_solo float,
  def_sacks float,
  def_interceptions float,
  def_pass_defended float,
  fg_made float,
  fg_att float,
  fg_pct float,
  punt_returns float,
  punt_return_yards float,
  kickoff_returns float,
  kickoff_return_yards float
);

create table team_stats (
  id bigserial primary key,
  team text,
  season int,
  season_type text,
  passing_yards float,
  passing_tds float,
  passing_interceptions float,
  rushing_yards float,
  rushing_tds float,
  receiving_yards float,
  receiving_tds float,
  def_tackles_solo float,
  def_sacks float,
  def_interceptions float,
  def_pass_defended float,
  fg_made float,
  fg_att float,
  fg_pct float
);

create table schedules (
  id bigserial primary key,
  game_id text,
  season int,
  game_type text,
  week int,
  away_team text,
  away_score float,
  home_team text,
  home_score float,
  result float,
  total float,
  overtime float,
  roof text,
  surface text,
  temp float,
  wind float
);

create table rosters (
  id bigserial primary key,
  season int,
  team text,
  position text,
  depth_chart_position text,
  jersey_number float,
  status text,
  full_name text,
  first_name text,
  last_name text,
  height float,
  weight float,
  college text,
  sleeper_id float,
  game_type text,
  years_exp float,
  entry_year float,
  rookie_year float,
  draft_club text,
  draft_number text
);

create table depth_charts (
  id bigserial primary key,
  season int,
  club_code text,
  week float,
  game_type text,
  full_name text,
  position text,
  depth_position text,
  team text,
  player_name text,
  pos_name text,
  pos_rank float
);

create table coaches (
  id bigserial primary key,
  season int,
  team text,
  head_coach text
);
