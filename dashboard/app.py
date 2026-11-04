
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "dashboard" / "data"
DBT_RESULTS = PROJECT_ROOT / "exoplanet_analytics" / "target" / "run_results.json"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

st.set_page_config(
    page_title="NASA Exoplanet Data Platform",
    page_icon="🪐",
    layout="wide",
)

st.title("🪐 NASA Exoplanet Data Platform")
st.caption(
    "NASA Exoplanet Archive | AWS S3 | PostgreSQL | dbt | Prefect | Streamlit"
)


# --------------------------------------------------
# Database queries
# --------------------------------------------------


@st.cache_data(ttl=300)
def load_data():
    """
    Load published analytics snapshots.

    The files are exported from PostgreSQL after
    dbt transformations and tests.
    """
    yearly = pd.read_csv(DATA_DIR / "yearly.csv")
    methods = pd.read_csv(DATA_DIR / "methods.csv")
    characteristics = pd.read_csv(DATA_DIR / "characteristics.csv")
    planets = pd.read_csv(DATA_DIR / "planets.csv")

    return yearly, methods, characteristics, planets


try:
    yearly, methods, characteristics, planets = load_data()
except Exception as exc:
    st.error("Unable to load published analytics data.")
    st.exception(exc)
    st.stop()



# --------------------------------------------------
# Helpers
# --------------------------------------------------

def get_latest_snapshot():
    """Find the newest locally downloaded raw CSV snapshot."""
    files = list(RAW_DATA_DIR.glob("exoplanets_*.csv"))

    if not files:
        return None

    latest = max(files, key=lambda path: path.stat().st_mtime)

    return datetime.fromtimestamp(
        latest.stat().st_mtime,
        tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M UTC")


def get_dbt_test_results():
    """Read the most recent local dbt build artifact."""
    if not DBT_RESULTS.exists():
        return None

    try:
        with DBT_RESULTS.open("r", encoding="utf-8") as file:
            results = json.load(file)

        tests = [
            result
            for result in results.get("results", [])
            if result.get("unique_id", "").startswith("test.")
        ]

        passed = sum(result.get("status") == "pass" for result in tests)
        failed = sum(result.get("status") in {"fail", "error"} for result in tests)

        return {
            "passed": passed,
            "failed": failed,
            "total": len(tests),
            "generated_at": results.get("metadata", {}).get("generated_at"),
        }

    except (OSError, ValueError, TypeError):
        return None


# --------------------------------------------------
# Navigation
# --------------------------------------------------

overview_tab, explorer_tab, quality_tab, insights_tab = st.tabs(
    [
        "📊 Overview",
        "🔭 Planet Explorer",
        "🛡️ Data Quality",
        "💡 Insights",
    ]
)


# --------------------------------------------------
# Tab 1: Overview
# --------------------------------------------------

with overview_tab:

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Exoplanets", f"{len(planets):,}")
    col2.metric("Discovery Methods", planets["discoverymethod"].nunique())
    col3.metric("Years With Discoveries", planets["disc_year"].nunique())

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

    fig_methods.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(fig_methods, use_container_width=True)

    st.subheader("Planet Characteristics by Discovery Method")

    metric = st.selectbox(
        "Choose a metric",
        [
            "Average Radius (Earth radii)",
            "Average Orbital Period (days)",
        ],
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


# --------------------------------------------------
# Tab 2: Interactive Planet Explorer
# --------------------------------------------------

with explorer_tab:

    st.subheader("Explore NASA Exoplanet Records")

    st.write(
        "Filter planets by discovery method and year, "
        "compare their characteristics, and export results."
    )

    available_methods = sorted(
        planets["discoverymethod"].dropna().unique().tolist()
    )

    selected_methods = st.multiselect(
        "Discovery Methods",
        options=available_methods,
        default=available_methods,
    )

    valid_years = planets["disc_year"].dropna()

    min_year = int(valid_years.min())
    max_year = int(valid_years.max())

    selected_years = st.slider(
        "Discovery Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
    )

    search = st.text_input(
        "Search by Planet or Host Star",
        placeholder="e.g. Kepler, TRAPPIST",
    )

    filtered = planets[
        planets["discoverymethod"].isin(selected_methods)
        & planets["disc_year"].between(
            selected_years[0],
            selected_years[1],
        )
    ].copy()

    if search.strip():
        matches = (
            filtered["pl_name"].fillna("").str.contains(
                search.strip(),
                case=False,
                regex=False,
            )
            | filtered["hostname"].fillna("").str.contains(
                search.strip(),
                case=False,
                regex=False,
            )
        )

        filtered = filtered[matches]

    st.metric("Matching Planets", f"{len(filtered):,}")

    st.subheader("Planet Radius vs. Orbital Period")

    scatter_data = filtered.dropna(
        subset=["pl_rade", "pl_orbper"]
    )

    scatter_data = scatter_data[
        (scatter_data["pl_rade"] > 0)
        & (scatter_data["pl_orbper"] > 0)
    ]

    if scatter_data.empty:
        st.info("No planets match the selected chart filters.")
    else:
        fig_scatter = px.scatter(
            scatter_data,
            x="pl_orbper",
            y="pl_rade",
            color="discoverymethod",
            hover_name="pl_name",
            hover_data={
                "hostname": True,
                "disc_year": True,
                "discoverymethod": False,
            },
            log_x=True,
            log_y=True,
            labels={
                "pl_orbper": "Orbital Period (Days, Log Scale)",
                "pl_rade": "Planet Radius (Earth Radii, Log Scale)",
                "discoverymethod": "Discovery Method",
            },
        )

        fig_scatter.update_layout(height=550)

        st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Explore Individual Planet Records")

    st.dataframe(
        filtered.sort_values("pl_name"),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="⬇️ Download Filtered Dataset (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="nasa_exoplanets_filtered.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# Tab 3: Data Quality and Pipeline Health
# --------------------------------------------------

with quality_tab:

    st.subheader("Data Quality & Pipeline Health")

    total = len(planets)

    missing_radius = planets["pl_rade"].isna().sum()
    missing_orbital = planets["pl_orbper"].isna().sum()
    duplicate_names = planets["pl_name"].dropna().duplicated().sum()

    radius_pct = (missing_radius / total * 100) if total else 0
    orbital_pct = (missing_orbital / total * 100) if total else 0

    q1, q2, q3, q4 = st.columns(4)

    q1.metric("Records Loaded", f"{total:,}")
    q2.metric("Missing Radius", f"{radius_pct:.1f}%")
    q3.metric("Missing Orbital Period", f"{orbital_pct:.1f}%")
    q4.metric("Duplicate Planet Names", f"{duplicate_names:,}")

    st.divider()

    st.subheader("Column Completeness")

    quality_columns = [
        "pl_name",
        "hostname",
        "discoverymethod",
        "disc_year",
        "pl_rade",
        "pl_orbper",
    ]

    completeness = pd.DataFrame(
        {
            "Column": quality_columns,
            "Completeness (%)": [
                round(planets[col].notna().mean() * 100, 2)
                for col in quality_columns
            ],
        }
    )

    fig_completeness = px.bar(
        completeness,
        x="Column",
        y="Completeness (%)",
        range_y=[0, 100],
        text="Completeness (%)",
    )

    st.plotly_chart(fig_completeness, use_container_width=True)

    st.subheader("Pipeline Execution Evidence")

    
    metadata_path = DATA_DIR / "metadata.json"

    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    else:
        metadata = {}

    snapshot = metadata.get("exported_at_utc")
    dbt_results = metadata.get("dbt_tests")


    left, right = st.columns(2)

    with left:
        st.markdown("**Published Data Snapshot**")

        if snapshot:
            st.success(snapshot)
        else:
            st.info("No local snapshot timestamp available.")

    with right:
        st.markdown("**dbt Test Results at Export**")

        if dbt_results and dbt_results["total"] > 0:
            passed = dbt_results["passed"]
            total_tests = dbt_results["total"]

            if passed == total_tests:
                st.success(f"{passed}/{total_tests} tests passed")
            else:
                st.warning(
                    f"{passed}/{total_tests} tests passed; "
                    f"{total_tests - passed} did not pass"
                )

            if dbt_results["generated_at"]:
                st.caption(
                    f"dbt artifact generated: "
                    f"{dbt_results['generated_at']}"
                )
        else:
            st.info("No local dbt test artifact available.")

    st.caption(
        "Data and test results reflect the latest published export, "
        "not a live database or Prefect connection."
    )



# --------------------------------------------------
# Tab 4: Dynamic Observations & Insights
# --------------------------------------------------

with insights_tab:
    st.subheader("💡 Exoplanet Discovery Insights")
    st.write(
        "Automatically generated observations from the latest "
        "available NASA exoplanet dataset."
    )

    # Insight 1: Peak discovery year
    st.markdown("### 📅 Peak Discovery Year")

    if not yearly.empty:
        peak = yearly.loc[yearly["total_discoveries"].idxmax()]

        st.info(
            f"**{int(peak['disc_year'])}** had the most recorded "
            f"discoveries, with **{int(peak['total_discoveries']):,} planets**."
        )
    else:
        st.info("No discovery-year data available.")

    # Insight 2: Most common discovery method
    st.markdown("### 🔭 Most Common Discovery Method")

    if not methods.empty:
        top_method = methods.iloc[0]
        top_share = (
            top_method["total_planets"] / len(planets) * 100
            if len(planets)
            else 0
        )

        st.info(
            f"**{top_method['discoverymethod']}** is the most common "
            f"discovery method in this dataset, accounting for "
            f"**{top_share:.1f}%** of planet records."
        )
    else:
        st.info("No discovery-method data available.")

    # Insight 3: Most recent two discovery years
    st.markdown("### 📈 Year-over-Year Discovery Change")

    yearly_sorted = yearly.sort_values("disc_year")

    if len(yearly_sorted) >= 2:
        previous = yearly_sorted.iloc[-2]
        latest = yearly_sorted.iloc[-1]

        previous_count = int(previous["total_discoveries"])
        latest_count = int(latest["total_discoveries"])

        if previous_count > 0:
            change = (
                (latest_count - previous_count)
                / previous_count
                * 100
            )

            direction = "increased" if change >= 0 else "decreased"

            st.info(
                f"Recorded discoveries **{direction} by "
                f"{abs(change):.1f}%** from "
                f"**{int(previous['disc_year'])}** "
                f"({previous_count:,} planets) to "
                f"**{int(latest['disc_year'])}** "
                f"({latest_count:,} planets)."
            )
        else:
            st.info(
                "Year-over-year percentage change cannot be "
                "calculated because the previous count is zero."
            )
    else:
        st.info("At least two discovery years are needed.")

    st.caption(
        "Recent discovery years may be incomplete. "
        "These comparisons describe the current dataset, "
        "not final annual discovery totals."
    )

    st.divider()

    # Insight 4: Discovery method trends over time
    st.subheader("Discovery Methods Over Time")

    method_trends = (
        planets.dropna(subset=["disc_year", "discoverymethod"])
        .groupby(["disc_year", "discoverymethod"])
        .size()
        .reset_index(name="discoveries")
    )

    if not method_trends.empty:
        fig_trends = px.area(
            method_trends,
            x="disc_year",
            y="discoveries",
            color="discoverymethod",
            labels={
                "disc_year": "Discovery Year",
                "discoveries": "Number of Planets",
                "discoverymethod": "Discovery Method",
            },
        )

        fig_trends.update_layout(height=500)

        st.plotly_chart(fig_trends, use_container_width=True)
    else:
        st.info("No discovery trends available.")

    st.divider()

    
    # Insight 5: Planet size distribution
    st.subheader("Planet Radius Distribution")

    radius_data = planets[
        planets["pl_rade"].notna()
        & (planets["pl_rade"] > 0)
    ].copy()

    if not radius_data.empty:
        plot_radius = radius_data[
            radius_data["pl_rade"].between(0, 30)
        ].copy()

        if not plot_radius.empty:
            fig_radius = px.histogram(
                plot_radius,
                x="pl_rade",
                nbins=40,
                labels={
                    "pl_rade": "Planet Radius (Earth Radii)",
                },
            )

            fig_radius.update_layout(
                height=450,
                xaxis_title="Planet Radius (Earth Radii)",
                yaxis_title="Number of Planets",
                bargap=0.05,
            )

            st.plotly_chart(fig_radius, use_container_width=True)

            st.caption(
                "Showing planets with radii between 0 and 30 Earth radii. "
                "Extreme values are excluded from this visualization only."
            )
        else:
            st.info("No planets have radii within the displayed range.")
    else:
        st.info("No valid planet radius measurements available.")

    st.caption(
        "Insights are recalculated from the PostgreSQL dataset "
        "when the dashboard's cached data refreshes."
    )


st.divider()
st.caption(
    "NASA Exoplanet Archive | Powered by AWS S3, PostgreSQL, dbt, Prefect & Streamlit"
)
