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

    st.metric("Total player-minutes", f"{filtered['total_minutes'].sum():,}")
    st.caption("Minutes are summed across players. A 20-minute drill with five players contributes 100 player-minutes.")
    if filtered.empty:
        st.info("No activity recorded for this selection. Try a wider date range.")
    else:
        breakdown = st.radio("Breakdown by", ["Drill category", "Day tag"], horizontal=True)
        column = {"Drill category": "drill_category", "Day tag": "day_tag"}[breakdown]
        totals = filtered.groupby(column)["total_minutes"].sum().sort_values(ascending=False)
        chart = totals.head(8).reset_index()
        if len(totals) > 8:
            chart.loc[len(chart)] = ["Other", totals.iloc[8:].sum()]
        chart["share"] = chart["total_minutes"] / chart["total_minutes"].sum()
        figure = alt.Chart(chart).mark_arc(innerRadius=72).encode(
            theta="total_minutes:Q",
            color=alt.Color(f"{column}:N", title=breakdown),
            tooltip=[alt.Tooltip(f"{column}:N", title=breakdown),
                     alt.Tooltip("total_minutes:Q", title="Player-minutes", format=",d"),
                     alt.Tooltip("share:Q", title="Share", format=".1%")],
        ).properties(height=330)
        st.altair_chart(figure, use_container_width=True)

        summary, records = st.tabs(["Drill category totals", "Filtered records"])
        with summary:
            by_category = (filtered.groupby("drill_category", as_index=False)["total_minutes"]
                           .sum().sort_values("total_minutes", ascending=False))
            st.dataframe(by_category, hide_index=True)
        with records:
            visible = filtered.drop(columns="player_id").copy()
            visible["date"] = visible["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(visible, hide_index=True)
            st.download_button("Download filtered CSV", visible.to_csv(index=False),
                               "filtered_activity.csv", "text/csv")

    with st.expander("Season reports"):
        st.write("Download all activity records, with one CSV per season.")
        st.download_button("Download season reports", season_archive(data.drop(columns="player_id")),
                           "activity_by_season.zip",
                           "application/zip")

if __name__ == "__main__":
    main()
