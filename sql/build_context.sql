-- Derive fictional context and normalized tracking records from the shipped fixtures.
INSERT INTO seasons
SELECT season, MIN(date), MAX(date)
FROM sessions
GROUP BY season;

INSERT INTO activity_days (season, date)
SELECT DISTINCT season, date FROM sessions ORDER BY date;

INSERT INTO session_context
SELECT s.id, d.id
FROM sessions AS s
JOIN activity_days AS d ON d.date = s.date AND d.season = s.season;

INSERT INTO roster_memberships
SELECT DISTINCT s.season, s.team_id, d.player_id
FROM drill_minutes AS d
JOIN sessions AS s ON s.id = d.session_id;

INSERT INTO games
SELECT id, id,
       CASE id % 3 WHEN 0 THEN 'Harbor Owls'
                   WHEN 1 THEN 'Summit Foxes' ELSE 'Prairie Lynx' END,
       CASE id % 4 WHEN 0 THEN 'Home' WHEN 3 THEN 'Home' ELSE 'Away' END
FROM sessions
WHERE day_tag = 'Game Day';

INSERT INTO tracking_activities
SELECT id, id FROM sessions;

INSERT INTO tracking_periods (activity_id, category)
SELECT DISTINCT session_id, drill_category
FROM drill_minutes
ORDER BY session_id, drill_category;

INSERT INTO tracking_athletes
SELECT id + 1000, id FROM players;

INSERT INTO period_observations
SELECT p.id, a.tracking_id, d.minutes * 60
FROM drill_minutes AS d
JOIN tracking_periods AS p
  ON p.activity_id = d.session_id AND p.category = d.drill_category
JOIN tracking_athletes AS a ON a.player_id = d.player_id;
