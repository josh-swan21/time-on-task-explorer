-- Report 1: Rank drill categories within each player's team and season.
WITH category_totals AS (
    SELECT season, team_id, team, player_id, player, drill_category,
           COUNT(DISTINCT session_id) AS sessions,
           SUM(active_seconds) AS seconds
    FROM activity_detail
    GROUP BY season, team_id, team, player_id, player, drill_category
), scored AS (
    SELECT *,
           SUM(seconds) OVER player_season AS season_seconds,
           DENSE_RANK() OVER (
               PARTITION BY season, team_id, player_id ORDER BY seconds DESC
           ) AS category_rank
    FROM category_totals
    WINDOW player_season AS (PARTITION BY season, team_id, player_id)
)
SELECT season, team, player, drill_category, sessions,
       ROUND(seconds / 60.0, 1) AS minutes,
       ROUND(100.0 * seconds / NULLIF(season_seconds, 0), 1) AS percent_of_player_minutes,
       category_rank
FROM scored
WHERE category_rank <= 5
ORDER BY season, team, player, category_rank, drill_category;

-- Report 2: Compare weekly minutes with the previous active week and a
-- trailing four-active-week average. Weeks start on Monday.
WITH weekly AS (
    SELECT season, team_id, team, player_id, player,
           DATE(date, '-6 days', 'weekday 1') AS week_start,
           SUM(active_seconds) / 60.0 AS minutes,
           SUM(CASE WHEN venue = 'Home' THEN active_seconds ELSE 0 END) / 60.0 AS home_game_minutes,
           SUM(CASE WHEN venue = 'Away' THEN active_seconds ELSE 0 END) / 60.0 AS away_game_minutes,
           COUNT(DISTINCT session_id) AS sessions
    FROM activity_detail
    GROUP BY season, team_id, team, player_id, player, week_start
), trends AS (
    SELECT *,
           LAG(minutes) OVER player_weeks AS previous_active_week,
           AVG(minutes) OVER (
               player_weeks ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
           ) AS trailing_average
    FROM weekly
    WINDOW player_weeks AS (PARTITION BY season, team_id, player_id ORDER BY week_start)
)
SELECT season, team, player, week_start, sessions, minutes,
       home_game_minutes, away_game_minutes,
       ROUND(minutes - previous_active_week, 1) AS change_in_minutes,
       ROUND(trailing_average, 1) AS average_minutes_last_four_active_weeks
FROM trends
ORDER BY season, team, player, week_start;
