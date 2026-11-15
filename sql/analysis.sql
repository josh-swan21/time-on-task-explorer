DROP VIEW IF EXISTS time_on_task;
DROP VIEW IF EXISTS activity_detail;

-- Observation grain: one athlete in one tracking period.
-- Every contextual join matches at most one row at this grain.
CREATE VIEW activity_detail AS
SELECT
    day.season,
    day.date,
    session.id AS session_id,
    session.day_tag,
    team.id AS team_id,
    team.name AS team,
    player.id AS player_id,
    player.name AS player,
    period.category AS drill_category,
    game.opponent,
    game.venue,
    obs.active_seconds
FROM period_observations AS obs
JOIN tracking_athletes AS athlete ON athlete.tracking_id = obs.tracking_id
JOIN players AS player ON player.id = athlete.player_id
JOIN tracking_periods AS period ON period.id = obs.period_id
JOIN tracking_activities AS activity ON activity.id = period.activity_id
JOIN sessions AS session ON session.id = activity.session_id
JOIN session_context AS context ON context.session_id = session.id
JOIN activity_days AS day ON day.id = context.activity_day_id
JOIN seasons AS season ON season.season = day.season
JOIN teams AS team ON team.id = session.team_id
JOIN roster_memberships AS roster
  ON roster.season = season.season
 AND roster.team_id = team.id
 AND roster.player_id = player.id
LEFT JOIN games AS game ON game.session_id = session.id;

CREATE VIEW time_on_task AS
WITH daily_activity AS (
    SELECT season, date, day_tag, team, player_id, player, drill_category,
           SUM(active_seconds) AS total_seconds
    FROM activity_detail
    GROUP BY season, date, day_tag, team, player_id, player, drill_category
)
SELECT season, date, day_tag, team, player_id, player, drill_category,
       total_seconds / 60 AS total_minutes
FROM daily_activity;
