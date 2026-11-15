# Time on Task Explorer

An interactive basketball performance analytics demo inspired by the Time On Task Tool from my Oklahoma City Thunder internship. This portfolio recreation uses independently written code and entirely fictional activity data spanning eight seasons from 2018–19 through 2025–26.

## What it answers

How did a player's recorded minutes break down during a stretch of the season? Choose a season, date range, team, and player. Refine the view by day tag or drill category, then inspect daily or weekly activity trends, the activity mix, and the records behind the totals. The three table views show category totals, player totals, and filtered activity records. The player list updates with the selected season and other filters. You can download the current records as CSV or all seasons as a ZIP of Excel-compatible CSVs, one per season.

The metric is player-minutes. If five athletes each take part in a 20-minute drill, the dashboard shows 100 player-minutes. This tool measures time allocation. It does not estimate intensity or physiological load.

## Stakeholder questions

| Stakeholder | Question | What the dashboard shows |
| --- | --- | --- |
| Performance staff | How did players spend their time? | Leading drill category by player-minutes and its share of the selected total |
| Performance staff | How has activity changed week to week? | Absolute and percentage change across the two latest complete weeks in the selected date range |
| Coaching staff | How does activity differ across day tags? | Total minutes and average player-minutes per active team-day for each day tag |
| Player development staff | Which players recorded the most activity? | Leading player by minutes and active dates, with the full ranking in Player totals |

Try selecting one team and a month-long date range, then switch between the questions. All answers use the filters currently applied in the sidebar.

## Dashboard views

- **Overview** shows stakeholder questions, the activity mix, and downloadable records.
- **Performance trends** compares daily and weekly activity and reports minutes per active player.
- **Session planning** compares mean and median player-minutes per active team-day by team and day tag.
- **Player profiles** shows an individual timeline and drill breakdown. Hover over a recorded date to see the fictional avatar and daily minutes. Avatars are illustrated locally and require no external image service.

## Run locally

Requires Python 3.10 or newer. From the project directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. The app loads the committed CSVs into an in-memory SQLite database on startup.

## Data and SQL

- `data/teams.csv` and `data/players.csv` contain fictional team and player identities.
- `data/sessions.csv` contains dated team sessions and their season and day tags.
- `data/drill_minutes.csv` records minutes for one player, session, and category per row.
- `sql/schema.sql` defines 13 tables covering source fixtures, season and calendar context, roster membership, games, and simulated athlete tracking.
- `sql/build_context.sql` derives the normalized context and tracking tables from the synthetic fixtures.
- `sql/analysis.sql` links athlete observations to tracking periods and activity, then joins session, roster, calendar, and optional game context. The dashboard reads the resulting daily aggregation.
- `sql/season_reports.sql` ranks categories by share of player minutes and compares weekly totals using conditional aggregation, CTEs, and window functions. Run both queries with `sqlite3 -header -column time_on_task.db < sql/season_reports.sql` after building the database. Weekly trends use weeks with recorded activity.

Run `python generate_data.py` to regenerate the same synthetic dataset. Run `python database.py` to build an optional on-disk SQLite database for inspecting the model or writing your own SQL.

```sql
SELECT drill_category, SUM(total_minutes) AS player_minutes
FROM time_on_task
GROUP BY drill_category
ORDER BY player_minutes DESC;
```

## Publish the demo

Upload the project directory to a GitHub repository with `app.py`, `requirements.txt`, `data/`, and `sql/` intact. Deploy the repository as a Streamlit app using `app.py` as its entry point, then link the deployed URL and repository from your portfolio.

## Portfolio case study

The internship tool turned basketball activity records into a filterable view of how players spent their time. This recreation demonstrates the same workflow from SQL aggregation through dashboard filters, charts, and reporting. It uses SQLite and generated CSVs so anyone can run it without credentials or access to the internship environment.
