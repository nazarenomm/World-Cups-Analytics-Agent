CREATE VIEW v_manager_stats_by_tournament AS
WITH manager_matches AS (
  SELECT ma.manager_id, ma.match_id, ma.team_id, m.tournament_id,
         m.home_team_id, m.away_team_id, m.home_team_score, m.away_team_score
  FROM manager_appearances ma
  JOIN matches m ON ma.match_id = m.match_id
),
results AS (
  SELECT manager_id, match_id, tournament_id,
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
manager_tournaments AS (
  SELECT DISTINCT manager_id, tournament_id, team_id
  FROM manager_appointments
),
performance_agg AS (
  SELECT mt.manager_id, mt.tournament_id, tp.performance
  FROM manager_tournaments mt
  LEFT JOIN team_performances tp
    ON tp.team_id = mt.team_id AND tp.tournament_id = mt.tournament_id
),
titles_agg AS (
  SELECT mt.manager_id, mt.tournament_id, (ts.position = 1) AS is_champion
  FROM manager_tournaments mt
  LEFT JOIN tournament_standings ts
    ON ts.team_id = mt.team_id AND ts.tournament_id = mt.tournament_id
)
SELECT
  mgr.manager_id, t.tournament_id, t.year AS tournament_year,
  mgr.given_name  AS manager_given_name,
  mgr.family_name AS manager_family_name,
  COUNT(DISTINCT r.match_id) AS matches_managed,
  COUNT(*) FILTER (WHERE r.result = 'W') AS wins,
  COUNT(*) FILTER (WHERE r.result = 'D') AS draws,
  COUNT(*) FILTER (WHERE r.result = 'L') AS losses,
  COALESCE(SUM(r.goals_for), 0) AS goals,
  COALESCE(SUM(r.goals_against), 0) AS goals_against,
  pf.performance AS furthest_stage,
  COALESCE(bool_or(ta.is_champion), FALSE) AS is_champion
FROM managers mgr
JOIN results r ON r.manager_id = mgr.manager_id
JOIN tournaments t ON t.tournament_id = r.tournament_id
LEFT JOIN performance_agg pf ON pf.manager_id = mgr.manager_id AND pf.tournament_id = t.tournament_id
LEFT JOIN titles_agg ta ON ta.manager_id = mgr.manager_id AND ta.tournament_id = t.tournament_id
GROUP BY mgr.manager_id, t.tournament_id, t.year, mgr.given_name, mgr.family_name,
         pf.performance;

