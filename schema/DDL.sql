-- tournaments
CREATE TABLE tournaments(
  tournament_id TEXT NOT NULL,
  tournament_name TEXT,
  year INTEGER,
  start_date DATE,
  end_date DATE,
  host_country TEXT, -- country or countries that hosted the tournament, e.g. "South Africa" or "Korea, Japan"
  winner TEXT,
  host_won BOOLEAN,
  count_teams INTEGER,
  group_stage BOOLEAN,
  second_group_stage BOOLEAN,
  final_round BOOLEAN,
  round_of_16 BOOLEAN,
  quarter_finals BOOLEAN,
  semi_finals BOOLEAN,
  third_place_match BOOLEAN,
  final BOOLEAN,
  PRIMARY KEY (tournament_id)
);

-- confederations
CREATE TABLE confederations(
  confederation_id TEXT NOT NULL,
  confederation_name TEXT, -- full name, e.g. "Union of European Football Associations"
  confederation_code TEXT, -- short name, e.g. "UEFA"
  PRIMARY KEY (confederation_id)
);

-- teams
CREATE TABLE teams(
  team_id TEXT NOT NULL,
  team_name TEXT, -- country name, e.g. "England"
  team_code TEXT, -- short name, e.g. "ENG" for England
  federation_name TEXT, -- e.g. "The Football Association"
  region_name TEXT,
  confederation_id TEXT NOT NULL,
  PRIMARY KEY (team_id),
  FOREIGN KEY (confederation_id) REFERENCES confederations (confederation_id)
);

-- players
CREATE TABLE players(
  player_id TEXT NOT NULL,
  family_name TEXT, -- last name
  given_name TEXT, -- first name
  birth_date DATE,
  goal_keeper BOOLEAN,
  defender BOOLEAN,
  midfielder BOOLEAN,
  forward BOOLEAN,
  count_tournaments INTEGER,
  list_tournaments TEXT, -- list of years of tournaments the player has participated in, e.g. "2006, 2010, 2014"
  PRIMARY KEY (player_id)
);

-- managers
CREATE TABLE managers(
  manager_id TEXT NOT NULL,
  family_name TEXT, -- last name
  given_name TEXT, -- first name
  female BOOLEAN,
  country_name TEXT, -- country the manager is from, not necessarily the country they manage
  PRIMARY KEY (manager_id)
);

-- referees
CREATE TABLE referees(
  referee_id TEXT NOT NULL,
  family_name TEXT, -- last name
  given_name TEXT, -- first name
  female BOOLEAN,
  country_name TEXT,
  confederation_id TEXT,
  PRIMARY KEY (referee_id),
  FOREIGN KEY (confederation_id) REFERENCES confederations (confederation_id)
);

-- stadiums
CREATE TABLE stadiums(
  stadium_id TEXT NOT NULL,
  stadium_name TEXT,
  city_name TEXT,
  country_name TEXT,
  stadium_capacity INTEGER,
  PRIMARY KEY (stadium_id)
);

-- groups
CREATE TABLE groups(
  group_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  stage_number INTEGER,
  stage_name TEXT, -- e.g. "group stage" 
  group_name TEXT, -- e.g. "Group A"
  count_teams INTEGER,
  PRIMARY KEY (group_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id)
);

-- matches
CREATE TABLE matches(
  match_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  group_id TEXT,
  match_name TEXT,
  stage_name TEXT,
  replay BOOLEAN,
  match_date TEXT,
  match_time TEXT,
  stadium_id TEXT NOT NULL,
  home_team_id TEXT NOT NULL,
  away_team_id TEXT NOT NULL,
  home_team_score INTEGER,
  away_team_score INTEGER,
  extra_time BOOLEAN,
  penalty_shootout BOOLEAN,
  home_team_score_penalties INTEGER,
  away_team_score_penalties INTEGER,
  PRIMARY KEY (match_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (group_id) REFERENCES groups (group_id),
  FOREIGN KEY (stadium_id) REFERENCES stadiums (stadium_id),
  FOREIGN KEY (home_team_id) REFERENCES teams (team_id),
  FOREIGN KEY (away_team_id) REFERENCES teams (team_id)
);

-- awards
CREATE TABLE awards(
  award_id TEXT NOT NULL,
  award_name TEXT,
  award_description TEXT,
  year_introduced INTEGER,
  PRIMARY KEY (award_id)
);

-- team performances
CREATE TABLE team_performances(
  team_performance_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  count_matches INTEGER,
  performance TEXT, -- e.g. "group stage", "round of 16", "quarter-finals", "semi-finals", "final", "final round", "third-place match", "winner"
  PRIMARY KEY (team_performance_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id)
);

-- player appointments: players called up to a national team for a tournament
CREATE TABLE player_appointments(
  player_appointment_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  shirt_number INTEGER,
  PRIMARY KEY (player_appointment_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id)
);

-- manager_appointments
CREATE TABLE manager_appointments(
  manager_appointment_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  manager_id TEXT NOT NULL,
  PRIMARY KEY (manager_appointment_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (manager_id) REFERENCES managers (manager_id)
);

-- referee_appointments
CREATE TABLE referee_appointments(
  referee_appointment_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  referee_id TEXT NOT NULL,
  PRIMARY KEY (referee_appointment_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (referee_id) REFERENCES referees (referee_id)
);

-- player_appearances
CREATE TABLE player_appearances(
  player_appearance_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  starter BOOLEAN,
  substitute BOOLEAN,
  shirt_number INTEGER,
  PRIMARY KEY (player_appearance_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id)
);

-- manager_appearances
CREATE TABLE manager_appearances(
  manager_appearance_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  manager_id TEXT NOT NULL,
  PRIMARY KEY (manager_appearance_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (manager_id) REFERENCES managers (manager_id)
);

-- referee_appearances
CREATE TABLE referee_appearances(
  referee_appearance_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  referee_id TEXT NOT NULL,
  PRIMARY KEY (referee_appearance_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (referee_id) REFERENCES referees (referee_id)
);

-- goals
CREATE TABLE goals(
  goal_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  minute_label TEXT,
  minute_regulation INTEGER,
  minute_stoppage INTEGER,
  match_period TEXT,
  own_goal BOOLEAN,
  penalty BOOLEAN,
  PRIMARY KEY (goal_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id)
);

-- penalty_kicks
CREATE TABLE penalty_kicks(
  penalty_kick_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  converted BOOLEAN,
  PRIMARY KEY (penalty_kick_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id)
);

-- bookings
CREATE TABLE bookings(
  booking_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  minute_label TEXT,
  minute_regulation INTEGER,
  minute_stoppage INTEGER,
  match_period TEXT,
  yellow_card BOOLEAN,
  red_card BOOLEAN,
  second_yellow_card BOOLEAN,
  sending_off BOOLEAN,
  PRIMARY KEY (booking_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id)
);

-- substitutions
CREATE TABLE substitutions(
  substitution_id TEXT NOT NULL,
  match_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  minute_label TEXT,
  minute_regulation INTEGER,
  minute_stoppage INTEGER,
  match_period TEXT,
  going_off BOOLEAN,
  coming_on BOOLEAN,
  PRIMARY KEY (substitution_id),
  FOREIGN KEY (match_id) REFERENCES matches (match_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id)
);

-- host_countries
CREATE TABLE host_countries(
  host_country_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  performance TEXT,
  PRIMARY KEY (host_country_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id)
);

-- group_standings
CREATE TABLE group_standings(
  group_standing_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  position INTEGER,
  team_id TEXT NOT NULL,
  played INTEGER,
  wins INTEGER,
  draws INTEGER,
  losses INTEGER,
  goals_for INTEGER,
  goals_against INTEGER,
  goal_difference INTEGER,
  points INTEGER,
  advanced BOOLEAN,
  PRIMARY KEY (group_standing_id),
  FOREIGN KEY (group_id) REFERENCES groups (group_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id)
);

-- tournament_standings
CREATE TABLE tournament_standings(
  tournament_standing_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  position INTEGER,
  PRIMARY KEY (tournament_standing_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id)
);

-- award_winners
CREATE TABLE award_winners(
  award_winner_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  award_id TEXT NOT NULL,
  shared BOOLEAN,
  player_id TEXT NOT NULL,
  team_id TEXT NOT NULL,
  PRIMARY KEY (award_winner_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id),
  FOREIGN KEY (award_id) REFERENCES awards (award_id),
  FOREIGN KEY (player_id) REFERENCES players (player_id),
  FOREIGN KEY (team_id) REFERENCES teams (team_id)
);

-- match_balls
CREATE TABLE match_balls(
  ball_id TEXT NOT NULL,
  tournament_id TEXT NOT NULL,
  ball_name TEXT,
  manufacturer TEXT,
  PRIMARY KEY (ball_id),
  FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id)
);