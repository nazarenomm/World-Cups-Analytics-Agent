CREATE VIEW v_team_stats_by_tournament AS
WITH team_matches AS (
  SELECT home_team_id AS team_id, match_id, tournament_id,
    CASE WHEN home_team_score > away_team_score THEN 'W'
         WHEN home_team_score = away_team_score THEN 'D'
         ELSE 'L' END AS result,
    home_team_score AS goals_for, away_team_score AS goals_against
  FROM matches
  UNION ALL
  SELECT away_team_id AS team_id, match_id, tournament_id,
    CASE WHEN away_team_score > home_team_score THEN 'W'
         WHEN away_team_score = home_team_score THEN 'D'
         ELSE 'L' END AS result,
    away_team_score AS goals_for, home_team_score AS goals_against
  FROM matches
),
match_agg AS (
  SELECT team_id, tournament_id,
    COUNT(*) AS matches_played,
    COUNT(*) FILTER (WHERE result = 'W') AS wins,
    COUNT(*) FILTER (WHERE result = 'D') AS draws,
    COUNT(*) FILTER (WHERE result = 'L') AS losses,
    COALESCE(SUM(goals_for), 0) AS goals_scored,
    COALESCE(SUM(goals_against), 0) AS goals_against
  FROM team_matches
  GROUP BY team_id, tournament_id
),
standings_agg AS (
  SELECT team_id, tournament_id,
    (position = 1) AS is_champion,
    (position = 2) AS is_second,
    (position = 3) AS is_third,
    (position = 4) AS is_fourth
  FROM tournament_standings
),
performance_agg AS (
  SELECT team_id, tournament_id, performance
  FROM team_performances
)
SELECT
  t.team_id, tr.tournament_id, tr.year AS tournament_year,
  t.team_name, c.confederation_code,
  COALESCE(ma.matches_played, 0) AS matches_played,
  COALESCE(ma.wins, 0) AS wins,
  COALESCE(ma.losses, 0) AS losses,
  COALESCE(ma.draws, 0) AS draws,
  COALESCE(sa.is_champion, FALSE) AS champion,
  COALESCE(sa.is_second, FALSE) AS second_place,
  COALESCE(sa.is_third, FALSE) AS third_place,
  COALESCE(sa.is_fourth, FALSE) AS fourth_place,
  pa.performance AS furthest_stage,
  COALESCE(ma.goals_scored, 0) AS goals_scored,
  COALESCE(ma.goals_against, 0) AS goals_against
FROM team_performances base
JOIN teams t ON t.team_id = base.team_id
JOIN tournaments tr ON tr.tournament_id = base.tournament_id
LEFT JOIN confederations c ON c.confederation_id = t.confederation_id
LEFT JOIN match_agg ma ON ma.team_id = t.team_id AND ma.tournament_id = tr.tournament_id
LEFT JOIN standings_agg sa ON sa.team_id = t.team_id AND sa.tournament_id = tr.tournament_id
LEFT JOIN performance_agg pa ON pa.team_id = t.team_id AND pa.tournament_id = tr.tournament_id;