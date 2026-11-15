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


def main():
    data = load_data()
    st.title("Time on Task Explorer")
    st.caption("Basketball activity minutes · Portfolio demo with synthetic data")
    with st.sidebar:
        st.header("Filters")
        seasons = sorted(data["season"].unique(), reverse=True)
        season = st.selectbox("Season", seasons)
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
        render_timeline(filtered)
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

    with st.expander("Season reports"):
        st.write("Download all activity records, with one CSV per season.")
        st.download_button("Download season reports", season_archive(data.drop(columns="player_id")),
                           "activity_by_season.zip",
                           "application/zip")

if __name__ == "__main__":
    main()
