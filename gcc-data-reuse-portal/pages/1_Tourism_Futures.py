import streamlit as st
import pandas as pd
import plotly.express as px
from src.ui_style import apply_global_style
apply_global_style("")
# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Tourism Futures",
    layout="wide"
)

st.title("🌍 Tourism Futures")
st.caption(
    "Demand trends, sustainability signals, and scenario-ready indicators "
    "for GCC tourism planning."
)

# --------------------------------------------------
# Load data
# --------------------------------------------------
DATA_PATH = "data/processed/tourism_futures.csv"

try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    st.error(f"Dataset not found: {DATA_PATH}")
    st.stop()

# --------------------------------------------------
# CLEAN & NORMALISE DATA  (CRITICAL FIX)
# --------------------------------------------------
df.columns = [c.strip().lower() for c in df.columns]

for col in ["country", "indicator"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

if "year" in df.columns:
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

if "value" in df.columns:
    df["value"] = (
        df["value"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

df = df.dropna(subset=["country", "year", "indicator", "value"]).copy()

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------
st.sidebar.header("Filters")

countries = sorted(df["country"].unique())
indicators = sorted(df["indicator"].unique())

selected_countries = st.sidebar.multiselect(
    "Country",
    countries,
    default=countries
)

year_min = int(df["year"].min())
year_max = int(df["year"].max())

year_range = st.sidebar.slider(
    "Year range",
    year_min,
    year_max,
    (year_min, year_max)
)

selected_indicator = st.sidebar.selectbox(
    "Indicator",
    indicators
)

# --------------------------------------------------
# Apply filters
# --------------------------------------------------
f = df[
    (df["country"].isin(selected_countries)) &
    (df["year"].between(year_range[0], year_range[1])) &
    (df["indicator"] == selected_indicator)
]

if f.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# --------------------------------------------------
# Key metrics
# --------------------------------------------------
st.subheader("Key metrics")

c1, c2, c3 = st.columns(3)

c1.metric("Countries", f["country"].nunique())
c2.metric("Years", f["year"].nunique())
c3.metric("Indicator", selected_indicator)

# --------------------------------------------------
# Trend over time
# --------------------------------------------------
st.subheader("Trend over time")

trend = (
    f.groupby(["year", "country"], as_index=False)["value"]
    .mean()
)

fig = px.line(
    trend,
    x="year",
    y="value",
    color="country",
    markers=True,
    labels={
        "year": "Year",
        "value": "Value",
        "country": "Country"
    }
)

fig.update_layout(
    height=450,
    legend_title_text="Country",
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Country comparison (latest year)
# --------------------------------------------------
st.subheader("Latest year comparison")

latest_year = trend["year"].max()

latest = trend[trend["year"] == latest_year]

bar = px.bar(
    latest,
    x="country",
    y="value",
    labels={"value": "Value", "country": "Country"},
)

bar.update_layout(
    height=400,
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(bar, use_container_width=True)

# --------------------------------------------------
# Download
# --------------------------------------------------
st.subheader("Download filtered data")

st.download_button(
    label="Download CSV",
    data=f.to_csv(index=False),
    file_name="tourism_futures_filtered.csv",
    mime="text/csv"
)

# --------------------------------------------------
# Footer
# --------------------------------------------------
st.caption(
    "Source: GCC-STAT Marsa Data Portal. "
    "Prototype analytics for educational and analytical use."
)
