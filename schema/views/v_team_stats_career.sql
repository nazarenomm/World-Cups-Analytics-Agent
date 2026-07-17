CREATE VIEW v_team_stats_career AS
WITH team_matches AS (
  SELECT home_team_id AS team_id, match_id,
    CASE WHEN home_team_score > away_team_score THEN 'W'
         WHEN home_team_score = away_team_score THEN 'D'
         ELSE 'L' END AS result,
    home_team_score AS goals_for, away_team_score AS goals_against
  FROM matches
  UNION ALL
  SELECT away_team_id AS team_id, match_id,
    CASE WHEN away_team_score > home_team_score THEN 'W'
         WHEN away_team_score = home_team_score THEN 'D'
         ELSE 'L' END AS result,
    away_team_score AS goals_for, home_team_score AS goals_against
  FROM matches
),
match_agg AS (
  SELECT team_id,
    COUNT(*) AS matches_played,
    COUNT(*) FILTER (WHERE result = 'W') AS wins,
    COUNT(*) FILTER (WHERE result = 'D') AS draws,
    COUNT(*) FILTER (WHERE result = 'L') AS losses,
    COALESCE(SUM(goals_for), 0) AS goals_scored,
    COALESCE(SUM(goals_against), 0) AS goals_against
  FROM team_matches
  GROUP BY team_id
),
standings_agg AS (
  SELECT team_id,
    COUNT(*) FILTER (WHERE position = 1) AS titles_won,
    COUNT(*) FILTER (WHERE position = 2) AS second_place,
    COUNT(*) FILTER (WHERE position = 3) AS third_place,
    COUNT(*) FILTER (WHERE position = 4) AS fourth_place
  FROM tournament_standings
  GROUP BY team_id
),
-- Asunción: "performance" refleja la fase MÁS LEJANA alcanzada por el equipo en ese torneo.
-- 'winner' no aparece como valor real en performance (los títulos se obtienen de tournament_standings).
-- 'third-place match' implica haber llegado a semifinales (se perdió la semi previa).
-- 'second group stage' (formatos 1974/1978) no cae en ninguna fase de eliminación directa.
performance_agg AS (
  SELECT team_id,
    COUNT(DISTINCT tournament_id) AS tournament_appearances,
    COUNT(DISTINCT tournament_id) FILTER (
      WHERE performance IN ('round of 16','quarter-finals','third-place match','semi-finals','final')
    ) AS times_reached_round_of_16,
    COUNT(DISTINCT tournament_id) FILTER (
      WHERE performance IN ('quarter-finals','third-place match','semi-finals','final')
    ) AS times_reached_quarterfinals,
    COUNT(DISTINCT tournament_id) FILTER (
      WHERE performance IN ('third-place match','semi-finals','final')
    ) AS times_reached_semifinals,
    COUNT(DISTINCT tournament_id) FILTER (
      WHERE performance = 'final'
    ) AS times_reached_final
  FROM team_performances
  GROUP BY team_id
)
SELECT
  t.team_id, t.team_name, c.confederation_code,
  COALESCE(ma.matches_played, 0) AS matches_played,
  COALESCE(ma.wins, 0) AS wins,
  COALESCE(ma.losses, 0) AS losses,
  COALESCE(ma.draws, 0) AS draws,
  COALESCE(sa.titles_won, 0) AS titles_won,
  COALESCE(sa.second_place, 0) AS second_place,
  COALESCE(sa.third_place, 0) AS third_place,
  COALESCE(sa.fourth_place, 0) AS fourth_place,
  COALESCE(pa.times_reached_round_of_16, 0) AS times_reached_round_of_16,
  COALESCE(pa.times_reached_quarterfinals, 0) AS times_reached_quarterfinals,
  COALESCE(pa.times_reached_semifinals, 0) AS times_reached_semifinals,
  COALESCE(pa.times_reached_final, 0) AS times_reached_final,
  COALESCE(pa.tournament_appearances, 0) AS tournament_appearances,
  COALESCE(ma.goals_scored, 0) AS goals_scored,
  COALESCE(ma.goals_against, 0) AS goals_against
FROM teams t
LEFT JOIN confederations c ON c.confederation_id = t.confederation_id
LEFT JOIN match_agg ma ON ma.team_id = t.team_id
LEFT JOIN standings_agg sa ON sa.team_id = t.team_id
LEFT JOIN performance_agg pa ON pa.team_id = t.team_id;