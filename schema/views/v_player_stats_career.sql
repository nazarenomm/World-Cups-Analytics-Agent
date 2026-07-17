CREATE VIEW v_player_stats_career AS
WITH player_matches AS (
  SELECT pa.player_id, pa.match_id, pa.team_id, m.tournament_id,
         m.home_team_id, m.away_team_id, m.home_team_score, m.away_team_score
  FROM player_appearances pa
  JOIN matches m ON pa.match_id = m.match_id
),
results AS (
  SELECT player_id, match_id,
    CASE
      WHEN team_id = home_team_id AND home_team_score > away_team_score THEN 'W'
      WHEN team_id = away_team_id AND away_team_score > home_team_score THEN 'W'
      WHEN home_team_score = away_team_score THEN 'D'
      ELSE 'L'
    END AS result
  FROM player_matches
),
goals_agg AS (
  SELECT player_id,
    COUNT(*) FILTER (WHERE own_goal IS NOT TRUE) AS total_goals,
    COUNT(*) FILTER (WHERE penalty IS TRUE) AS penalty_goals
  FROM goals
  GROUP BY player_id
),
cards_agg AS (
  SELECT player_id,
    COUNT(*) FILTER (WHERE yellow_card IS TRUE) AS total_yellow_cards,
    COUNT(*) FILTER (WHERE red_card IS TRUE OR sending_off IS TRUE) AS total_red_cards
  FROM bookings
  GROUP BY player_id
),
subs_agg AS (
  SELECT player_id,
    COUNT(*) FILTER (WHERE coming_on IS TRUE) AS subbed_in,
    COUNT(*) FILTER (WHERE going_off IS TRUE) AS subbed_out
  FROM substitutions
  GROUP BY player_id
),
has_appearance_data AS (SELECT DISTINCT player_id FROM player_appearances),
has_card_data       AS (SELECT DISTINCT player_id FROM bookings),
has_sub_data        AS (SELECT DISTINCT player_id FROM substitutions),
-- Cobertura completa 1930-presente: convocatorias, no depende de datos partido a partido
player_tournaments AS (
  SELECT DISTINCT player_id, team_id, tournament_id
  FROM player_appointments
),
performance_agg AS (
  SELECT pt.player_id,
    COUNT(DISTINCT pt.tournament_id) FILTER (
      WHERE tp.performance IN ('round of 16','quarter-finals','third-place match','semi-finals','final','winner')
    ) AS times_reached_round_of_16,
    COUNT(DISTINCT pt.tournament_id) FILTER (
      WHERE tp.performance IN ('quarter-finals','third-place match','semi-finals','final','winner')
    ) AS times_reached_quarterfinals,
    COUNT(DISTINCT pt.tournament_id) FILTER (
      WHERE tp.performance IN ('third-place match','semi-finals','final','winner')
    ) AS times_reached_semifinals,
    COUNT(DISTINCT pt.tournament_id) FILTER (
      WHERE tp.performance IN ('final','winner')
    ) AS times_reached_final
  FROM player_tournaments pt
  LEFT JOIN team_performances tp
    ON tp.team_id = pt.team_id AND tp.tournament_id = pt.tournament_id
  GROUP BY pt.player_id
),
titles_agg AS (
  SELECT pt.player_id,
    COUNT(DISTINCT pt.tournament_id) FILTER (WHERE ts.position = 1) AS titles_won
  FROM player_tournaments pt
  LEFT JOIN tournament_standings ts
    ON ts.team_id = pt.team_id AND ts.tournament_id = pt.tournament_id
  GROUP BY pt.player_id
)
SELECT
  p.player_id,
  p.given_name  AS player_given_name,
  p.family_name AS player_family_name,
  p.goal_keeper AS is_goalkeeper,
  p.defender    AS is_defender,
  p.midfielder  AS is_midfielder,
  p.forward     AS is_forward,

  CASE WHEN had.player_id IS NULL THEN NULL
       ELSE COUNT(DISTINCT pm.match_id) END AS matches_played,

  COALESCE(ga.total_goals, 0) AS total_goals,
  COALESCE(ga.penalty_goals, 0) AS penalty_goals,

  CASE WHEN hcd.player_id IS NULL THEN NULL
       ELSE COALESCE(ca.total_yellow_cards, 0) END AS total_yellow_cards,
  CASE WHEN hcd.player_id IS NULL THEN NULL
       ELSE COALESCE(ca.total_red_cards, 0) END AS total_red_cards,

  CASE WHEN had.player_id IS NULL THEN NULL
       ELSE COUNT(*) FILTER (WHERE r.result = 'W') END AS wins,
  CASE WHEN had.player_id IS NULL THEN NULL
       ELSE COUNT(*) FILTER (WHERE r.result = 'D') END AS draws,
  CASE WHEN had.player_id IS NULL THEN NULL
       ELSE COUNT(*) FILTER (WHERE r.result = 'L') END AS losses,

  CASE WHEN hsd.player_id IS NULL THEN NULL
       ELSE COALESCE(sa.subbed_in, 0) END AS subbed_in,
  CASE WHEN hsd.player_id IS NULL THEN NULL
       ELSE COALESCE(sa.subbed_out, 0) END AS subbed_out,

  -- Estas 5 columnas usan player_appointments (cobertura 1930+), sin tratamiento NULL
  COALESCE(pf.times_reached_round_of_16, 0) AS times_reached_round_of_16,
  COALESCE(pf.times_reached_quarterfinals, 0) AS times_reached_quarterfinals,
  COALESCE(pf.times_reached_semifinals, 0) AS times_reached_semifinals,
  COALESCE(pf.times_reached_final, 0) AS times_reached_final,
  COALESCE(ta.titles_won, 0) AS titles_won

FROM players p
LEFT JOIN has_appearance_data had ON had.player_id = p.player_id
LEFT JOIN has_card_data hcd       ON hcd.player_id = p.player_id
LEFT JOIN has_sub_data hsd        ON hsd.player_id = p.player_id
LEFT JOIN player_matches pm ON pm.player_id = p.player_id
LEFT JOIN results r ON r.player_id = p.player_id AND r.match_id = pm.match_id
LEFT JOIN goals_agg ga ON ga.player_id = p.player_id
LEFT JOIN cards_agg ca ON ca.player_id = p.player_id
LEFT JOIN subs_agg sa ON sa.player_id = p.player_id
LEFT JOIN performance_agg pf ON pf.player_id = p.player_id
LEFT JOIN titles_agg ta ON ta.player_id = p.player_id
GROUP BY p.player_id, p.given_name, p.family_name, p.goal_keeper, p.defender,
         p.midfielder, p.forward, ga.total_goals, ga.penalty_goals,
         ca.total_yellow_cards, ca.total_red_cards, sa.subbed_in, sa.subbed_out,
         had.player_id, hcd.player_id, hsd.player_id,
         pf.times_reached_round_of_16, pf.times_reached_quarterfinals,
         pf.times_reached_semifinals, pf.times_reached_final, ta.titles_won;