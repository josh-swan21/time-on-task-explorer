from contextlib import closing
from io import BytesIO
import sqlite3
from zipfile import ZipFile

import pandas as pd
import altair as alt
import streamlit as st

from database import seed

st.set_page_config(page_title="Time on Task Explorer", page_icon="🏀", layout="wide")

@st.cache_data
def load_data():
    with closing(sqlite3.connect(":memory:")) as database:
        seed(database)
        return pd.read_sql_query(
            "SELECT * FROM time_on_task ORDER BY date, team, player, drill_category",
            database, parse_dates=["date"],
        )

def season_archive(rows):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for season, group in rows.groupby("season"):
            archive.writestr(f"activity_{season}.csv", group.to_csv(index=False))
    return buffer.getvalue()

def render_timeline(rows):
    st.subheader("Activity over time")
    interval = st.radio("Time interval", ["Daily", "Weekly"], index=1, horizontal=True)
    period = rows["date"]
    if interval == "Weekly":
        period = period.dt.to_period("W-SUN").dt.start_time
    timeline = (rows.assign(period=period).groupby(["period", "team"], as_index=False)
                ["total_minutes"].sum())
    first, last = timeline["period"].min(), timeline["period"].max()
    calendar = pd.date_range(first, last, freq="D" if interval == "Daily" else "W-MON")
    grid = pd.MultiIndex.from_product([calendar, sorted(timeline["team"].unique())],
                                      names=["period", "team"])
    timeline = (timeline.set_index(["period", "team"]).reindex(grid, fill_value=0)
                .reset_index())
    line = alt.Chart(timeline).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("period:T", title="Date" if interval == "Daily" else "Week of",
                axis=alt.Axis(format="%b %-d", grid=False)),
        y=alt.Y("total_minutes:Q", title="Player-minutes"),
        color=alt.Color("team:N", title="Team",
                        scale=alt.Scale(range=["#007C78", "#C45A21"])),
        tooltip=[alt.Tooltip("period:T", title="Period", format="%b %d, %Y"),
                 alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("total_minutes:Q", title="Player-minutes", format=",d")],
    ).properties(height=290)
    st.altair_chart(line, use_container_width=True)


QUESTIONS = {
    "How did players spend their time?": "Performance staff · Review activity allocation",
    "How has activity changed week to week?": "Performance staff · Review changes in scheduled work",
    "How does activity differ across day tags?": "Coaching staff · Compare session contexts",
    "Which players recorded the most activity?": "Player development staff · Review individual participation",
}


def render_insights(rows, dates):
    st.subheader("Stakeholder questions")
    question = st.selectbox("Choose a question", list(QUESTIONS), key="stakeholder_question")
    st.caption(QUESTIONS[question])
    total = rows["total_minutes"].sum()
    if question == "How did players spend their time?":
        category = (rows.groupby("drill_category")["total_minutes"].sum()
                    .sort_values(ascending=False))
        name, minutes = category.index[0], category.iloc[0]
        st.write(f"**{name}** led the selection with **{minutes:,} player-minutes** "
                 f"({minutes / total:.1%} of the total).")
        st.caption("See Activity mix and Drill category totals for the full distribution.")
    elif question == "How has activity changed week to week?":
        first, last = map(pd.Timestamp, dates)
        weeks = pd.date_range(first, last - pd.Timedelta(days=6), freq="W-MON")
        if len(weeks) < 2:
            st.info("Select a date range that includes at least two full Monday–Sunday weeks.")
            return
        weekly = (rows.assign(week=rows["date"].dt.to_period("W-SUN").dt.start_time)
                  .groupby("week")["total_minutes"].sum().reindex(weeks, fill_value=0))
        previous, current = weekly.iloc[-2:]
        change = current - previous
        st.write(f"Player-minutes changed by **{change:+,}** from the week of "
                 f"**{weeks[-2]:%b %d, %Y}** ({previous:,}) to the week of "
                 f"**{weeks[-1]:%b %d, %Y}** ({current:,}).")
        if previous:
            st.caption(f"{change / previous:+.1%} change. Partial weeks are excluded.")
        else:
            st.caption("The previous week had zero recorded minutes for this selection.")
    elif question == "How does activity differ across day tags?":
        by_day = (rows.groupby(["day_tag", "team", "date"], as_index=False)
                  ["total_minutes"].sum())
        comparison = (by_day.groupby("day_tag", as_index=False)
                      .agg(team_days=("date", "size"),
                           total_minutes=("total_minutes", "sum")))
        comparison["average"] = comparison["total_minutes"] / comparison["team_days"]
        comparison = comparison.sort_values("average", ascending=False)
        st.dataframe(comparison, hide_index=True, column_config={
            "day_tag": "Day tag", "team_days": "Active team-days",
            "total_minutes": "Player-minutes",
            "average": st.column_config.NumberColumn("Minutes per active team-day", format="%.1f"),
        })
        st.caption("Each team and date with matching activity counts once per day tag. "
                   "Averages reflect the players and drills selected.")
    else:
        players = (rows.groupby(["player_id", "player"], as_index=False)
                   .agg(total_minutes=("total_minutes", "sum"), days=("date", "nunique"))
                   .sort_values(["total_minutes", "player"], ascending=[False, True]))
        leader = players.iloc[0]
        st.write(f"**{leader['player']}** recorded **{leader['total_minutes']:,} player-minutes** "
                 f"across **{leader['days']} active dates**.")
        st.caption("See Player totals for the full ranking. Minutes measure recorded activity duration.")


def render_performance(rows):
    render_timeline(rows)
    st.subheader("Weekly participation")
    weekly = (rows.assign(week=rows["date"].dt.to_period("W-SUN").dt.start_time)
              .groupby(["week", "team"], as_index=False)
              .agg(minutes=("total_minutes", "sum"), players=("player_id", "nunique"),
                   active_dates=("date", "nunique"))
              .sort_values(["week", "team"]))
    weekly["week"] = weekly["week"].dt.date
    weekly["minutes_per_player"] = weekly["minutes"] / weekly["players"]
    st.dataframe(weekly, hide_index=True, column_config={
        "week": "Week of", "team": "Team", "minutes": "Player-minutes",
        "players": "Active players", "active_dates": "Active dates",
        "minutes_per_player": st.column_config.NumberColumn("Minutes per active player", format="%.1f"),
    })
    st.caption("Weekly participation uses the dates inside your selection, including partial weeks.")


@st.cache_data
def player_portrait(player_id, name):
    import base64
    import random

    from PIL import Image, ImageDraw, ImageFont

    rng = random.Random(int(player_id))
    image = Image.new("RGB", (112, 112), rng.choice(["#E3F1ED", "#E7EFFA", "#F9EFE2"]))
    draw = ImageDraw.Draw(image)
    skin = rng.choice(["#794936", "#A6654A", "#C58A64", "#E1AA81"])
    hair = rng.choice(["#252029", "#4B3029", "#683E2C"])
    jersey = rng.choice(["#007C78", "#334F75", "#854A2D"])
    draw.ellipse((14, 73, 98, 150), fill=jersey)
    draw.rounded_rectangle((46, 62, 66, 86), radius=6, fill=skin)
    draw.ellipse((33, 23, 79, 74), fill=skin)
    draw.pieslice((31, 15, 81, 62), 180, 360, fill=hair)
    for x in (47, 64):
        draw.ellipse((x, 46, x + 4, 50), fill="#241E20")
    draw.arc((49, 52, 63, 64), 5, 175, fill="#542C2A", width=2)
    initials = "".join(part[0] for part in name.split()[:2])
    draw.text((56, 97), initials, font=ImageFont.load_default(), anchor="mm", fill="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def render_player_profile(rows):
    st.subheader("Player activity")
    names = rows[["player_id", "player"]].drop_duplicates().sort_values("player")
    labels = names.set_index("player_id")["player"].to_dict()
    player_id = st.selectbox("Player profile", list(labels), format_func=labels.__getitem__)
    player = rows[rows["player_id"].eq(player_id)]
    daily = (player.groupby("date", as_index=False)["total_minutes"].sum()
             .sort_values("date"))
    minutes = int(daily["total_minutes"].sum())
    total, days, average = st.columns(3)
    total.metric("Player-minutes", f"{minutes:,}")
    days.metric("Active dates", len(daily))
    average.metric("Minutes per active date", f"{minutes / len(daily):.1f}")
    st.caption("Hover over a recorded date to reveal the fictional player avatar and daily minutes.")
    daily["player"] = labels[player_id]
    daily["portrait"] = player_portrait(player_id, labels[player_id])
    hover = alt.selection_point(fields=["date"], nearest=True, on="pointerover",
                                empty=False, clear="pointerout")
    base = alt.Chart(daily).encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("total_minutes:Q", title="Player-minutes"),
    )
    line = base.mark_line(color="#007C78", point=True)
    targets = base.mark_point(opacity=0).encode(
        tooltip=[alt.Tooltip("player:N", title="Player"),
                 alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                 alt.Tooltip("total_minutes:Q", title="Player-minutes", format=",d")]
    ).add_params(hover)
    portrait = base.transform_filter(hover).mark_image(
        width=54, height=54, dy=-34
    ).encode(url="portrait:N")
    st.altair_chart((line + portrait + targets).properties(height=300, padding={
        "top": 65, "left": 8, "right": 30, "bottom": 5,
    }), use_container_width=True)
    categories = (player.groupby("drill_category", as_index=False)["total_minutes"]
                  .sum().sort_values("total_minutes", ascending=False))
    categories["share"] = categories["total_minutes"] / minutes
    st.dataframe(categories, hide_index=True, column_config={
        "drill_category": "Drill category", "total_minutes": "Player-minutes",
        "share": st.column_config.NumberColumn("Share of minutes", format="percent"),
    })


def main():
    data = load_data()
    st.title("Time on Task Explorer")
    st.caption("Basketball activity minutes · Portfolio demo with synthetic data")
    with st.sidebar:
        st.header("Filters")
        seasons = sorted(data["season"].unique(), reverse=True)
        season = st.selectbox("Season", seasons, key="season")
        filtered = data[data["season"].eq(season)]
        first = filtered["date"].min().date()
        last = filtered["date"].max().date()
        dates = st.date_input("Date range", (first, last), min_value=first,
                              max_value=last, key=f"dates-{season}")
        if len(dates) != 2:
            st.info("Select the end date to update the dashboard.")
            st.stop()
        filtered = filtered[filtered["date"].between(*map(pd.Timestamp, dates))]
        for column, label in [("team", "Team"), ("day_tag", "Day tag"),
                              ("drill_category", "Drill category"), ("player", "Player")]:
            choices = sorted(filtered[column].unique())
            key = f"filter-{column}"
            st.session_state[key] = [choice for choice in st.session_state.get(key, [])
                                     if choice in choices]
            selected = st.multiselect(label, choices, key=key)
            if selected:
                filtered = filtered[filtered[column].isin(selected)]

    minutes, players, days = st.columns(3)
    minutes.metric("Total player-minutes", f"{filtered['total_minutes'].sum():,}", border=True)
    players.metric("Players with activity", filtered["player_id"].nunique(), border=True)
    days.metric("Active dates", filtered["date"].nunique(), border=True)
    st.caption("Minutes are summed across players. A 20-minute drill with five players contributes 100 player-minutes.")
    if filtered.empty:
        st.info("No activity recorded for this selection. Try a wider date range.")
    else:
        overview, performance, planning, profiles = st.tabs([
            "Overview", "Performance trends", "Session planning", "Player profiles"
        ])
        with overview:
            render_insights(filtered, dates)
            st.subheader("Activity mix")
            breakdown = st.radio("Breakdown by", ["Drill category", "Day tag"], horizontal=True)
            column = {"Drill category": "drill_category", "Day tag": "day_tag"}[breakdown]
            totals = filtered.groupby(column)["total_minutes"].sum().sort_values(ascending=False)
            chart = totals.head(8).reset_index()
            if len(totals) > 8:
                chart.loc[len(chart)] = ["Other", totals.iloc[8:].sum()]
            chart["share"] = chart["total_minutes"] / chart["total_minutes"].sum()
            figure = alt.Chart(chart).mark_arc(innerRadius=72).encode(
                theta="total_minutes:Q",
                color=alt.Color(f"{column}:N", title=breakdown, scale=alt.Scale(
                    range=["#007C78", "#C45A21", "#405F8D", "#80568F", "#537843",
                           "#C59331", "#A65066", "#57777C", "#68737D"])),
                tooltip=[alt.Tooltip(f"{column}:N", title=breakdown),
                         alt.Tooltip("total_minutes:Q", title="Player-minutes", format=",d"),
                         alt.Tooltip("share:Q", title="Share", format=".1%")],
            ).properties(height=330)
            st.altair_chart(figure, use_container_width=True)

            st.subheader("Activity tables")
            minute_column = st.column_config.NumberColumn("Player-minutes", format="localized")
            summary, roster, records = st.tabs(
                ["Drill category totals", "Player totals", "Filtered records"]
            )
            with summary:
                by_category = (filtered.groupby("drill_category", as_index=False)["total_minutes"]
                               .sum().sort_values("total_minutes", ascending=False))
                by_category["share"] = by_category["total_minutes"] / by_category["total_minutes"].sum()
                st.dataframe(by_category, hide_index=True, column_config={
                    "drill_category": "Drill category",
                    "total_minutes": minute_column,
                    "share": st.column_config.NumberColumn("Share of minutes", format="percent"),
                })
            with roster:
                by_player = (filtered.groupby(["team", "player_id", "player"], as_index=False)
                             .agg(total_minutes=("total_minutes", "sum"),
                                  active_dates=("date", "nunique"))
                             .sort_values(["total_minutes", "player"], ascending=[False, True])
                             .drop(columns="player_id"))
                st.dataframe(by_player, hide_index=True, column_config={
                    "team": "Team", "player": "Player", "total_minutes": minute_column,
                    "active_dates": "Active dates",
                })
            with records:
                visible = filtered.drop(columns="player_id").copy()
                visible["date"] = visible["date"].dt.strftime("%Y-%m-%d")
                st.dataframe(visible, hide_index=True, column_config={
                    "season": "Season", "date": "Date", "day_tag": "Day tag", "team": "Team",
                    "player": "Player", "drill_category": "Drill category",
                    "total_minutes": minute_column,
                })
                st.download_button("Download filtered CSV", visible.to_csv(index=False),
                                   "filtered_activity.csv", "text/csv")

        with performance:
            render_performance(filtered)
        with planning:
            st.subheader("Minutes per active team-day")
            planning_days = (filtered.groupby(["team", "day_tag", "date"], as_index=False)
                             ["total_minutes"].sum())
            comparison = (planning_days.groupby(["team", "day_tag"], as_index=False)
                          .agg(active_days=("date", "size"),
                               minutes=("total_minutes", "sum"),
                               typical_minutes=("total_minutes", "median")))
            comparison["average_minutes"] = comparison["minutes"] / comparison["active_days"]
            comparison = comparison.sort_values(["team", "average_minutes"], ascending=[True, False])
            st.dataframe(comparison, hide_index=True, column_config={
                "team": "Team", "day_tag": "Day tag", "active_days": "Active team-days",
                "minutes": "Total player-minutes",
                "typical_minutes": st.column_config.NumberColumn("Median per team-day", format="%.1f"),
                "average_minutes": st.column_config.NumberColumn("Average per team-day", format="%.1f"),
            })
            st.caption("Each team and date with matching activity counts once per day tag.")
        with profiles:
            render_player_profile(filtered)

    with st.expander("Season reports"):
        st.write("Download all activity records, with one CSV per season.")
        st.download_button("Download season reports", season_archive(data.drop(columns="player_id")),
                           "activity_by_season.zip",
                           "application/zip")

if __name__ == "__main__":
    main()
