
import os

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st

st.set_page_config(
    page_title="NASA Exoplanet Analytics",
    page_icon="🪐",
    layout="wide",
)

st.title("🪐 NASA Exoplanet Analytics Dashboard")
st.caption("NASA Exoplanet Archive | AWS S3 | PostgreSQL | dbt | Prefect")


@st.cache_data(ttl=300)
def load_data():
    with psycopg.connect(
        dbname="nasa_exoplanets",
        user=os.environ.get("USER"),
        host="localhost",
    ) as conn:
        yearly = pd.read_sql_query(
            "SELECT * FROM analytics.discoveries_by_year ORDER BY disc_year",
            conn,
        )
        methods = pd.read_sql_query(
            "SELECT * FROM analytics.discoveries_by_method ORDER BY total_planets DESC",
            conn,
        )
        characteristics = pd.read_sql_query(
            "SELECT * FROM analytics.planet_characteristics ORDER BY total_planets DESC",
            conn,
        )
        total = pd.read_sql_query(
            "SELECT COUNT(*) AS total FROM public.raw_exoplanets",
            conn,
        )["total"].iloc[0]

    return yearly, methods, characteristics, total


try:
    yearly, methods, characteristics, total = load_data()
except Exception as exc:
    st.error("Could not connect to PostgreSQL or load analytics data.")
    st.exception(exc)
    st.stop()

col1, col2, col3 = st.columns(3)

col1.metric("Total Exoplanets", f"{total:,}")
col2.metric("Discovery Methods", len(methods))
col3.metric("Years With Discoveries", len(yearly))

st.divider()

st.subheader("Exoplanet Discoveries by Year")

fig_year = px.line(
    yearly,
    x="disc_year",
    y="total_discoveries",
    markers=True,
    labels={
        "disc_year": "Discovery Year",
        "total_discoveries": "Number of Discoveries",
    },
)
st.plotly_chart(fig_year, use_container_width=True)

st.subheader("Discovery Methods")

fig_methods = px.bar(
    methods,
    x="total_planets",
    y="discoverymethod",
    orientation="h",
    labels={
        "total_planets": "Number of Exoplanets",
        "discoverymethod": "Discovery Method",
    },
)
fig_methods.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_methods, use_container_width=True)

st.subheader("Planet Characteristics by Discovery Method")

metric = st.selectbox(
    "Choose a metric",
    ["Average Radius (Earth radii)", "Average Orbital Period (days)"],
)

metric_column = (
    "avg_radius_earth"
    if metric == "Average Radius (Earth radii)"
    else "avg_orbital_period_days"
)

fig_characteristics = px.bar(
    characteristics,
    x="discoverymethod",
    y=metric_column,
    labels={
        "discoverymethod": "Discovery Method",
        metric_column: metric,
    },
)
st.plotly_chart(fig_characteristics, use_container_width=True)

st.caption("Source: NASA Exoplanet Archive. Data refreshed through Prefect.")
