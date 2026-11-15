"""Load the included CSVs into SQLite and expose the SQL analysis view."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
INSERTS = {
    "teams": "INSERT INTO teams VALUES (?, ?)",
    "players": "INSERT INTO players VALUES (?, ?)",
    "sessions": "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
    "drill_minutes": "INSERT INTO drill_minutes VALUES (?, ?, ?, ?)",
}

def seed(connection):
    connection.executescript((ROOT / "sql/schema.sql").read_text())
    context_sql = (ROOT / "sql/build_context.sql").read_text()
    with connection:
        for table in (
            "period_observations", "tracking_periods", "tracking_athletes",
            "tracking_activities", "games", "roster_memberships",
            "session_context", "activity_days", "seasons", *reversed(INSERTS),
        ):
            connection.execute(f"DELETE FROM {table}")
        for table, insert in INSERTS.items():
            with (ROOT / "data" / f"{table}.csv").open(newline="", encoding="utf-8") as file:
                rows = csv.reader(file)
                next(rows)
                connection.executemany(insert, rows)
        for statement in context_sql.split(";"):
            if statement.strip():
                connection.execute(statement)
    connection.executescript((ROOT / "sql/analysis.sql").read_text())

if __name__ == "__main__":
    from contextlib import closing
    with closing(sqlite3.connect(ROOT / "time_on_task.db")) as database:
        seed(database)
    print("Created time_on_task.db")
