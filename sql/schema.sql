PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    date TEXT NOT NULL,
    season TEXT NOT NULL,
    day_tag TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drill_minutes (
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    drill_category TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK (minutes > 0),
    PRIMARY KEY (session_id, player_id, drill_category)
);
CREATE TABLE IF NOT EXISTS seasons (
    season TEXT PRIMARY KEY, starts_on TEXT NOT NULL, ends_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_days (
    id INTEGER PRIMARY KEY, season TEXT NOT NULL REFERENCES seasons(season),
    date TEXT NOT NULL, UNIQUE (season, date)
);
CREATE TABLE IF NOT EXISTS session_context (
    session_id INTEGER PRIMARY KEY REFERENCES sessions(id),
    activity_day_id INTEGER NOT NULL REFERENCES activity_days(id)
);
CREATE TABLE IF NOT EXISTS roster_memberships (
    season TEXT REFERENCES seasons(season), team_id INTEGER REFERENCES teams(id),
    player_id INTEGER REFERENCES players(id), PRIMARY KEY (season, team_id, player_id)
);
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL UNIQUE REFERENCES sessions(id),
    opponent TEXT NOT NULL, venue TEXT NOT NULL CHECK (venue IN ('Home', 'Away'))
);
CREATE TABLE IF NOT EXISTS tracking_activities (
    id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL UNIQUE REFERENCES sessions(id)
);
CREATE TABLE IF NOT EXISTS tracking_periods (
    id INTEGER PRIMARY KEY, activity_id INTEGER NOT NULL REFERENCES tracking_activities(id),
    category TEXT NOT NULL, UNIQUE (activity_id, category)
);
CREATE TABLE IF NOT EXISTS tracking_athletes (
    tracking_id INTEGER PRIMARY KEY, player_id INTEGER NOT NULL UNIQUE REFERENCES players(id)
);
CREATE TABLE IF NOT EXISTS period_observations (
    period_id INTEGER REFERENCES tracking_periods(id),
    tracking_id INTEGER REFERENCES tracking_athletes(tracking_id),
    active_seconds INTEGER NOT NULL CHECK (active_seconds > 0),
    PRIMARY KEY (period_id, tracking_id)
);
