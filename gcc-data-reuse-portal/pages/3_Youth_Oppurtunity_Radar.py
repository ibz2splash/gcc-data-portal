import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path
from src.ui_style import apply_global_style
apply_global_style("")
# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(page_title="Youth Opportunity Radar", layout="wide")

# --------------------------------------------------
# Data
# --------------------------------------------------
DATA_PATH = Path(__file__).parents[1] / "data" / "processed" / "youth.csv"

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Ensure expected columns exist
    for col in ["country", "year", "indicator", "value"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in {path.name}")

    # Clean dtypes
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["country", "year", "indicator", "value"])

    df["year"] = df["year"].astype(int)
    df["country"] = df["country"].astype(str)
    df["indicator"] = df["indicator"].astype(str)

    return df

df = load_data(DATA_PATH)

# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("🎓 Youth Opportunity Radar")
st.caption(
    "Explore youth labour-market conditions and opportunity signals across GCC countries (prototype)."
)

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------
st.sidebar.header("Filters")

countries = sorted(df["country"].unique())
indicators = sorted(df["indicator"].unique())
years = sorted(df["year"].unique())

selected_countries = st.sidebar.multiselect(
    "Country",
    options=countries,
    default=countries
)

year_range = st.sidebar.slider(
    "Year range",
    min_value=min(years),
    max_value=max(years),
    value=(min(years), max(years))
)

selected_indicator = st.sidebar.selectbox(
    "Indicator",
    options=indicators,
    index=0
)

# --------------------------------------------------
# Filtered frame
# --------------------------------------------------
f = df[
    (df["country"].isin(selected_countries)) &
    (df["indicator"] == selected_indicator) &
    (df["year"].between(year_range[0], year_range[1]))
].copy()

# --------------------------------------------------
# Styles: indicator label smaller so it doesn’t truncate
# --------------------------------------------------
st.markdown(
    """
    <style>
    .indicator-label { font-size: 0.95rem; line-height: 1.2rem; opacity: 0.95; }
    .metric-label-small { font-size: 0.85rem; opacity: 0.85; margin-bottom: -6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab_overview, tab_insights, tab_download, tab_scenarios = st.tabs(
    ["Overview", "Insights", "Download", "Scenarios & Forecast"]
)

# ==================================================
# OVERVIEW
# ==================================================
with tab_overview:
    st.subheader("Key metrics")

    c1, c2, c3 = st.columns(3)
    c1.metric("Countries", f["country"].nunique())
    c2.metric("Years", f["year"].nunique())

    with c3:
        st.markdown('<div class="metric-label-small">Indicator</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="indicator-label">{selected_indicator if selected_indicator else "—"}</div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.subheader("Trend over time")

    if f.empty:
        st.warning("No data available for the selected filters.")
    else:
        line = (
            alt.Chart(f)
            .mark_line(point=True)
            .encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y("value:Q", title="Value"),
                color=alt.Color("country:N", title="Country"),
                tooltip=["country", "year", "value"]
            )
            .properties(height=420)
        )
        st.altair_chart(line, use_container_width=True)

        st.subheader("Latest year snapshot")
        latest_year = int(f["year"].max())
        snapshot = f[f["year"] == latest_year].sort_values("value", ascending=False)

        bar = (
            alt.Chart(snapshot)
            .mark_bar()
            .encode(
                x=alt.X("value:Q", title="Value"),
                y=alt.Y("country:N", sort="-x", title="Country"),
                tooltip=["country", "value"]
            )
            .properties(height=340)
        )
        st.altair_chart(bar, use_container_width=True)

# ==================================================
# INSIGHTS
# ==================================================
with tab_insights:
    st.subheader("Interpretation guide")

    st.markdown(
        """
- Use this section to compare **youth labour-market signals** across GCC countries.
- The indicator dropdown should include multiple measures (e.g., unemployment, participation).
- Use the scenario tab to simulate how interventions could shift the selected indicator over time.
"""
    )

    if not f.empty:
        st.subheader("Cross-country dispersion (latest year)")
        latest_year = int(f["year"].max())
        latest = f[f["year"] == latest_year].copy()
        stats = latest["value"].describe()

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Min", f"{stats['min']:.2f}")
        s2.metric("Median", f"{stats['50%']:.2f}")
        s3.metric("Mean", f"{stats['mean']:.2f}")
        s4.metric("Max", f"{stats['max']:.2f}")

# ==================================================
# DOWNLOAD
# ==================================================
with tab_download:
    st.subheader("Download filtered data")

    st.download_button(
        label="Download CSV",
        data=f.to_csv(index=False),
        file_name="youth_opportunity_filtered.csv",
        mime="text/csv"
    )

# ==================================================
# SCENARIOS & FORECAST
# ==================================================
with tab_scenarios:
    st.subheader("Intervention simulation (prototype)")
    st.caption(
        "Illustrative scenarios using elasticity and time-decay (not official forecasts). "
        "Useful for exploring intervention strength and persistence."
    )

    if f.empty:
        st.warning("Select data to run scenarios.")
    else:
        shock = st.slider(
            "Programme / policy shock (%)",
            min_value=-50,
            max_value=50,
            value=-10,   # default negative can be intuitive for unemployment (reductions)
            step=5
        )

        elasticity = st.slider(
            "Elasticity (strength of response)",
            0.1, 2.0, 1.0, 0.1
        )

        decay = st.slider(
            "Time-decay factor (how quickly effects fade back to baseline)",
            0.1, 1.0, 0.6, 0.1
        )

        horizon = st.slider(
            "Forecast horizon (years)",
            1, 10, 5
        )

        benchmark_mode = st.checkbox(
            "Country-to-country scenario benchmarking",
            value=True
        )

        # Smooth baseline: mean per country-year
        base_country = (
            f.groupby(["country", "year"], as_index=False)["value"]
            .mean()
            .sort_values(["country", "year"])
        )

        all_proj = []
        for country in base_country["country"].unique():
            sub = base_country[base_country["country"] == country].copy()
            sub = sub.sort_values("year")

            last_year = int(sub["year"].max())
            last_value = float(sub[sub["year"] == last_year]["value"].iloc[0])

            # Apply shock to starting point, scaled by elasticity
            current = last_value * (1 + (shock / 100.0) * elasticity)

            years_f = list(range(last_year + 1, last_year + horizon + 1))
            vals_f = []
            for _ in range(horizon):
                vals_f.append(current)
                # decay back toward baseline
                current = current + decay * (last_value - current)

            hist = sub.copy()
            hist["scenario"] = "Historical"

            proj = pd.DataFrame({
                "country": country,
                "year": years_f,
                "value": vals_f,
                "scenario": "Scenario projection"
            })

            all_proj.append(pd.concat([hist, proj], ignore_index=True))

        combined = pd.concat(all_proj, ignore_index=True)

        chart = (
            alt.Chart(combined)
            .mark_line(point=True)
            .encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y("value:Q", title="Value"),
                color=alt.Color("country:N", title="Country"),
                strokeDash=alt.StrokeDash("scenario:N", title="Series"),
                tooltip=["country", "year", "scenario", "value"]
            )
            .properties(height=430)
        )
        st.altair_chart(chart, use_container_width=True)

        if benchmark_mode:
            st.subheader("Benchmark outcome (end of forecast horizon)")
            end_year = int(combined["year"].max())

            end_vals = (
                combined[(combined["year"] == end_year) & (combined["scenario"] == "Scenario projection")]
                .sort_values("value", ascending=False)
                .rename(columns={"value": "projected_value"})
            )[["country", "projected_value"]]

            baseline_last = (
                base_country.groupby("country", as_index=False)
                .apply(lambda x: x.loc[x["year"].idxmax(), ["country", "value"]])
                .reset_index(drop=True)
                .rename(columns={"value": "baseline_last_value"})
            )

            out = end_vals.merge(baseline_last, on="country", how="left")
            out["change"] = out["projected_value"] - out["baseline_last_value"]
            out["change_pct"] = np.where(
                out["baseline_last_value"] != 0,
                (out["change"] / out["baseline_last_value"]) * 100.0,
                np.nan
            )
            st.dataframe(out, use_container_width=True)

    st.info(
        "Tip: For indicators where 'lower is better' (e.g., unemployment), use a negative shock. "
        "For 'higher is better' indicators, use a positive shock."
    )

# --------------------------------------------------
# Footer
# --------------------------------------------------
st.divider()
st.caption(
    "Source: GCC-STAT Marsa Data Portal. Prototype analytics for educational and policy-exploration purposes."
)
