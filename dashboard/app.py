"""ShelterFlow dashboard.

A read-only Streamlit front end over the gold layer of the dbt pipeline.
Each tab maps to one gold model:

    gold_adoption_metrics  -> Adoption
    gold_long_stay_animals -> Long stays
    gold_capacity_trends   -> Capacity

Run from anywhere:
    streamlit run dashboard/app.py

Prerequisite: the warehouse must already be built (python pipelines/bronze_ingest.py,
then `dbt build` inside dbt_shelterflow), so the gold tables exist in the DuckDB file.
"""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
import numpy as np
import altair as alt

# Anchor to the project root (parent of dashboard/), so the app
# runs the same regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "shelterflow.duckdb"

st.set_page_config(page_title="ShelterFlow", page_icon="🐾", layout="wide")


# cache_resource: one shared, long-lived connection across reruns.
# read_only=True so the dashboard never locks the file against dbt, and a
# stray query can't mutate the warehouse.
@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        st.error(
            f"Database not found at {DB_PATH}.\n\n"
            "Build it first: run `python pipelines/bronze_ingest.py`, then "
            "`dbt build` inside dbt_shelterflow/."
        )
        st.stop()
    return duckdb.connect(str(DB_PATH), read_only=True)


# cache_data: memorize query results (a DataFrame) keyed by the SQL string,
# so flipping between tabs doesn't re-hit the warehouse every rerun.
@st.cache_data
def query(sql: str) -> pd.DataFrame:
    return get_connection().execute(sql).df()


def require_table(name: str) -> None:
    """Fail friendly if a gold model hasn't been built yet."""
    exists = query(
        f"SELECT COUNT(*) AS n FROM information_schema.tables "
        f"WHERE table_name = '{name}'"
    )["n"][0]
    if not exists:
        st.warning(f"Table `{name}` not found. Run `dbt build` to create it.")
        st.stop()


# Tabs 
st.title("🐾 ShelterFlow")
st.caption("Austin Animal Center intake & outcome analytics (through 2018)")

adoption_tab, long_stay_tab, capacity_tab = st.tabs(
    ["Adoption", "Long stays", "Capacity"]
)


# Adoption Metrics
with adoption_tab:
    require_table("gold_adoption_metrics")
    df = query("SELECT * FROM gold_adoption_metrics")

    st.subheader("Most and least adoptable breeds")

    col1, col2 = st.columns(2)
    animal_type = col1.selectbox("Animal type", ["Dog", "Cat"])
    min_stays = col2.slider("Minimum completed stays", 10, 500, 50, step=10)

    filtered = df[
        (df["animal_type"] == animal_type) & (df["total_stays"] >= min_stays)
    ].sort_values("adoption_rate", ascending=False)

    n = min(8, len(filtered) // 2)
    if n == 0:
        extremes = filtered.copy()
        extremes["group"] = "Most adoptable" 
    else:
        high = filtered.head(n).copy()
        high["group"] = "Most adoptable"
        low = filtered.tail(n).copy()
        low["group"] = "Least adoptable"
        extremes = pd.concat([high, low])

    extremes = extremes.sort_values("adoption_rate", ascending=False)
    breed_order = extremes["breed_standardized"].tolist()

    base = alt.Chart(extremes).encode(
        x=alt.X("breed_standardized:N", sort=breed_order, title="Breed"),
        y=alt.Y("adoption_rate:Q", axis=alt.Axis(format="%"), title="Adoption rate"),
        tooltip=[
            alt.Tooltip("breed_standardized:N", title="Breed"),
            alt.Tooltip("adoption_rate:Q", title="Adoption rate", format=".1%"),
            alt.Tooltip("group:N", title="Group"),
        ],

    )
    chart = base.mark_bar().encode(
        color=alt.Color(
            "group:N",
            title=None,
            scale=alt.Scale(
                domain=["Most adoptable", "Least adoptable"],
                range=["#7fb8f5", "#f56b6b"],
            ),
        ),
    ) + base.mark_text(dy=-6, color="white").encode(
        text=alt.Text("adoption_rate:Q", format=".0%")
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(
        filtered[
            ["breed_standardized", "total_stays", "adoptions",
             "adoption_rate", "avg_days_to_adoption"]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "adoption_rate": st.column_config.NumberColumn(
                "Adoption rate", format="percent"
            ),
        },
    )


# Long Stays
with long_stay_tab:
    require_table("gold_long_stay_animals")
    df = query("SELECT * FROM gold_long_stay_animals")

    st.subheader("Long-stay animals (70+ days)")
    st.caption(
        "Completed historical stays in the longest ~5% (95th percentile). "
        "Not a currently-in-shelter view; the dataset ends in 2018."
    )

    col1, col2 = st.columns(2)
    types = col1.multiselect(
        "Animal type", sorted(df["animal_type"].unique()),
        default=sorted(df["animal_type"].unique()),
    )
    outcomes = col2.multiselect(
        "Outcome", sorted(df["outcome_type"].unique()),
        default=sorted(df["outcome_type"].unique()),
    )

    filtered = df[df["animal_type"].isin(types) & df["outcome_type"].isin(outcomes)]

    counts, edges = np.histogram(filtered["length_of_stay"], bins=20)
    hist = pd.DataFrame({
        "stay_days": edges[:-1].round().astype(int),  # left edge of each bin
        "animals": counts,
    })
    st.bar_chart(
        hist, 
        x="stay_days", 
        y="animals", 
        height=300,
        x_label="Length of stay (days)",
        y_label="Animals"
    )

    st.dataframe(
        filtered.sort_values("length_of_stay", ascending=False),
        width="stretch",
        hide_index=True,
    )


# Capacity Trends
with capacity_tab:
    require_table("gold_capacity_trends")
    df = query("SELECT * FROM gold_capacity_trends ORDER BY month")

    st.subheader("Monthly shelter capacity")

    # Intakes vs. outcomes
    long = df.melt(
        id_vars="month",
        value_vars=["intakes", "outcomes"],
        var_name="series",
        value_name="animals",
    )
  
    hover = alt.selection_point(
        on="mouseover", nearest=True, fields=["month"], empty=False
    )

    line = alt.Chart(long).mark_line().encode(
        x=alt.X("month:T", title="  "),
        y=alt.Y("animals:Q", title="Animals per month"),
        color=alt.Color("series:N", title=None),
    )

    hover_layer = (
        alt.Chart(df)
        .mark_rule(strokeWidth=8, opacity=0)
        .encode(
            x="month:T",
            tooltip=[
                alt.Tooltip("month:T", title="Month", format="%b %Y"),
                alt.Tooltip("intakes:Q", title="Intakes"),
                alt.Tooltip("outcomes:Q", title="Outcomes"),
            ],
        )
        .add_params(hover)
    )
    
    points = line.mark_point(size=60, filled=True).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0))
    )

    volume = (line + hover_layer + points).properties(height=320)
    st.altair_chart(volume, width="stretch")
    st.caption("Monthly intake vs. outcome volume.")

    # Net flow
    net = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("month:T", title=None),
            y=alt.Y("net_flow:Q", title="Net flow (animals)"),
            tooltip=[
                alt.Tooltip("month:T", title="Month", format="%b %Y"),
                alt.Tooltip("net_flow:Q", title="Net flow"),
            ],
        )
        .properties(height=250)
    )
    st.altair_chart(net, width="stretch")
    st.caption("Net flow (intakes − outcomes). Positive = the shelter grew that month.")  

    # Cumulative net population
    cumulative_hover = alt.selection_point(
        on="mouseover", nearest=True, fields=["month"], empty=False
    )

    cumulative_line = alt.Chart(df).mark_line().encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("cumulative_net_population:Q", title="Cumulative net population"),
    )

    cumulative_hover_layer = (
        alt.Chart(df)
        .mark_rule(strokeWidth=8, opacity=0)
        .encode(
            x="month:T",
            tooltip=[
                alt.Tooltip("month:T", title="Month", format="%b %Y"),
                alt.Tooltip("cumulative_net_population:Q", title="Cumulative"),
            ],
        )
        .add_params(cumulative_hover)
    )

    cumulative_points = cumulative_line.mark_point(size=60, filled=True).encode(
        opacity=alt.condition(cumulative_hover, alt.value(1), alt.value(0))
    )

    cumulative = (cumulative_line + cumulative_hover_layer + cumulative_points).properties(height=250)

    st.altair_chart(cumulative, width="stretch")
    st.caption(
        "Cumulative net population. NOTE: this is change since data collection "
        "began, not a true headcount, as the source has no starting census."
    )