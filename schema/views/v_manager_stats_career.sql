CREATE VIEW v_manager_stats_career AS
WITH manager_matches AS (
  SELECT ma.manager_id, ma.match_id, ma.team_id,
         m.home_team_id, m.away_team_id, m.home_team_score, m.away_team_score
  FROM manager_appearances ma
  JOIN matches m ON ma.match_id = m.match_id
),
results AS (
  SELECT manager_id, match_id,
    CASE
      WHEN team_id = home_team_id AND home_team_score > away_team_score THEN 'W'
      WHEN team_id = away_team_id AND away_team_score > home_team_score THEN 'W'
      WHEN home_team_score = away_team_score THEN 'D'
      ELSE 'L'
    END AS result,
    CASE WHEN team_id = home_team_id THEN home_team_score ELSE away_team_score END AS goals_for,
    CASE WHEN team_id = home_team_id THEN away_team_score ELSE home_team_score END AS goals_against
  FROM manager_matches
),
-- Torneos donde el DT dirigió a un equipo (vía manager_appointments)
manager_tournaments AS (
  SELECT DISTINCT manager_id, tournament_id, team_id
  FROM manager_appointments
),
-- Fase alcanzada por el DT en cada torneo (heredada del team_performances de su equipo en ese torneo)
performance_agg AS (
  SELECT mt.manager_id,
    COUNT(DISTINCT mt.tournament_id) AS tournament_count,
    COUNT(DISTINCT mt.tournament_id) FILTER (
      WHERE tp.performance IN ('final','winner')) AS times_final,
    COUNT(DISTINCT mt.tournament_id) FILTER (
      WHERE tp.performance IN ('semi-finals','final','winner')) AS times_semifinals,
    COUNT(DISTINCT mt.tournament_id) FILTER (
      WHERE tp.performance IN ('quarter-finals','semi-finals','final','winner')) AS times_quarterfinals,
    COUNT(DISTINCT mt.tournament_id) FILTER (
      WHERE tp.performance IN ('round of 16','quarter-finals','semi-finals','final','winner')) AS times_round_of_16
  FROM manager_tournaments mt
  LEFT JOIN team_performances tp
    ON tp.team_id = mt.team_id AND tp.tournament_id = mt.tournament_id
  GROUP BY mt.manager_id
),
-- Títulos y podios (vía tournament_standings del equipo dirigido)
standings_agg AS (
  SELECT mt.manager_id,
    COUNT(*) FILTER (WHERE ts.position = 1) AS titles_won,
    COUNT(*) FILTER (WHERE ts.position = 2) AS second_place,
    COUNT(*) FILTER (WHERE ts.position = 3) AS third_place,
    COUNT(*) FILTER (WHERE ts.position = 4) AS fourth_place
  FROM manager_tournaments mt
  LEFT JOIN tournament_standings ts
    ON ts.team_id = mt.team_id AND ts.tournament_id = mt.tournament_id
  GROUP BY mt.manager_id
)
SELECT
  mgr.manager_id,
  mgr.given_name  AS manager_given_name,
  mgr.family_name AS manager_family_name,
  COUNT(DISTINCT r.match_id) AS matches_managed,
  COUNT(*) FILTER (WHERE r.result = 'W') AS wins,
  COUNT(*) FILTER (WHERE r.result = 'D') AS draws,
  COUNT(*) FILTER (WHERE r.result = 'L') AS losses,
  COALESCE(SUM(r.goals_for), 0) AS goals,
  COALESCE(SUM(r.goals_against), 0) AS goals_against,
  COALESCE(pa.tournament_count, 0) AS tournament_count,
  COALESCE(pa.times_final, 0) AS times_final,
  COALESCE(pa.times_semifinals, 0) AS times_semifinals,
  COALESCE(pa.times_quarterfinals, 0) AS times_quarterfinals,
  COALESCE(pa.times_round_of_16, 0) AS times_round_of_16,
  COALESCE(sa.titles_won, 0) AS titles_won,
  COALESCE(sa.second_place, 0) AS second_place,
  COALESCE(sa.third_place, 0) AS third_place,
  COALESCE(sa.fourth_place, 0) AS fourth_place
FROM managers mgr
LEFT JOIN results r ON r.manager_id = mgr.manager_id
LEFT JOIN performance_agg pa ON pa.manager_id = mgr.manager_id
LEFT JOIN standings_agg sa ON sa.manager_id = mgr.manager_id
GROUP BY mgr.manager_id, mgr.given_name, mgr.family_name,
         pa.tournament_count, pa.times_final, pa.times_semifinals,
         pa.times_quarterfinals, pa.times_round_of_16,
         sa.titles_won, sa.second_place, sa.third_place, sa.fourth_place;