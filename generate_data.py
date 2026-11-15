"""Regenerate the bundled fictional CSV data."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).parent / "data"

def write(name, columns, rows):
    DATA.mkdir(exist_ok=True)
    with (DATA / f"{name}.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

def main():
    rng = random.Random(42)
    names = ["Avery Cole", "Jordan Ellis", "Riley Brooks", "Cameron Lane",
             "Quinn Hayes", "Parker Reed", "Morgan Blake", "Casey Shaw",
             "Drew West", "Taylor Finn", "Reese Gray", "Skyler Wells"]
    schedules = {
        "Practice": [("Warm-up", 10), ("Shooting", 22), ("Team Offense", 28), ("Team Defense", 24)],
        "Game Day": [("Warm-up", 14), ("Game Play", 28)],
        "Recovery": [("Mobility", 18), ("Light Shooting", 14)],
        "Individual Work": [("Skill Development", 24), ("Conditioning", 16)],
    }
    sessions, minutes = [], []
    # Generate the original seasons first to preserve their seeded records.
    for year in (2024, 2025, *range(2018, 2024)):
        season = f"{year}–{str(year + 1)[-2:]}"
        for offset in range(0, 165, 2):
            day = date(year, 10, 1) + timedelta(days=offset)
            for team in (1, 2):
                tag = rng.choices(list(schedules), weights=[5, 3, 2, 2])[0]
                session = len(sessions) + 1
                sessions.append((session, team, day.isoformat(), season, tag))
                roster = list(range(1, 6)) if team == 1 else list(range(7, 12))
                roster.append(6 if year % 2 == 0 else 12)
                for player in roster:
                    if rng.random() < 0.1:
                        continue
                    for category, base in schedules[tag]:
                        minutes.append((session, player, category, base + rng.randint(-6, 8)))
    write("teams", ["id", "name"], [(1, "Metro Flight"), (2, "Canyon Flight")])
    write("players", ["id", "name"], enumerate(names, 1))
    write("sessions", ["id", "team_id", "date", "season", "day_tag"], sessions)
    write("drill_minutes", ["session_id", "player_id", "drill_category", "minutes"], minutes)

if __name__ == "__main__":
    main()
