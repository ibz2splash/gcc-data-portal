import streamlit as st
import pandas as pd
from pathlib import Path
import re
from src.ui_style import apply_global_style
apply_global_style("")

st.set_page_config(page_title="Trade & Logistics Explorer", layout="wide")

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "trade_by_partner.csv"

st.title("🚢 Trade & Logistics Explorer")
st.caption("Explore trade trends and (when available) partner-country breakdowns using GCC-STAT Marsa exports.")

#st.write(f"Working directory: {ROOT}")
#st.write(f"Looking for: {DATA_PATH}")

REQUIRED = ["country", "year", "indicator", "value"]
OPTIONAL = ["partner"]

def normalize_cols(cols):
    return [str(c).strip() for c in cols]

def find_col(df, candidates):
    """Return the first matching column name from candidates (case-insensitive, ignores extra spaces)."""
    cols = normalize_cols(df.columns)
    lower_map = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    # fuzzy contains match
    for c in cols:
        for cand in candidates:
            if cand.lower() in c.lower():
                return c
    return None

def extract_year(x):
    if pd.isna(x):
        return None
    s = str(x)
    m = re.search(r"(19|20)\d{2}", s)
    return int(m.group(0)) if m else None

@st.cache_data(show_spinner=False)
def load_and_clean_trade(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = normalize_cols(df.columns)

    # If already standardized
    lower_cols = {c.lower() for c in df.columns}
    if set(REQUIRED).issubset(lower_cols):
        # normalize exact casing
        rename = {}
        for c in df.columns:
            lc = c.lower()
            if lc in REQUIRED + OPTIONAL:
                rename[c] = lc
        df = df.rename(columns=rename)

        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(
            df["value"].astype(str).str.replace(",", "", regex=False).str.strip(),
            errors="coerce"
        )
        df = df.dropna(subset=["country", "year", "indicator", "value"])
        df["country"] = df["country"].astype(str).str.strip()
        df["indicator"] = df["indicator"].astype(str).str.strip()
        if "partner" in df.columns:
            df["partner"] = df["partner"].astype(str).str.strip()
        return df

    # Otherwise: try to map from Marsa-style columns (your screenshot)
    c_country = find_col(df, ["COUNTRY", "Country"])
    c_partner = find_col(df, ["PARTNER COUNTRY", "PARTENER COUNTRY", "Partner", "Partner Country"])
    c_indicator = find_col(df, ["INDICATOR", "Indicator"])
    c_time = find_col(df, ["TIME_PERIOD", "TIME PERIOD", "Year", "PERIOD"])
    c_value = find_col(df, ["OBS_VALUE", "OBS VALUE", "VALUE", "Obs Value"])

    if not (c_country and c_indicator and c_time and c_value):
        # show debug columns for you
        raise ValueError(
            f"Could not map columns. Found columns: {list(df.columns)}\n"
            f"Need something like COUNTRY, INDICATOR, TIME_PERIOD, OBS_VALUE."
        )

    out = pd.DataFrame()
    out["country"] = df[c_country].astype(str).str.strip()
    out["indicator"] = df[c_indicator].astype(str).str.strip()
    out["year"] = df[c_time].apply(extract_year).astype("Int64")

    # numeric value
    out["value"] = pd.to_numeric(
        df[c_value].astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce"
    )

    if c_partner:
        out["partner"] = df[c_partner].astype(str).str.strip()

    out = out.dropna(subset=["country", "year", "indicator", "value"])
    return out


# -------- Load
try:
    if not DATA_PATH.exists():
        st.error("Missing file: data/processed/trade_by_partner.csv")
        st.stop()

    df = load_and_clean_trade(DATA_PATH)

except Exception as e:
    st.error(str(e))
    st.stop()

# -------- Sidebar filters
st.sidebar.header("Filters")

countries = sorted(df["country"].dropna().unique().tolist())
sel_countries = st.sidebar.multiselect("Country", countries, default=countries[:3] if len(countries) >= 3 else countries)

years = df["year"].dropna().astype(int)
min_year, max_year = int(years.min()), int(years.max())
yr = st.sidebar.slider("Year range", min_year, max_year, (min_year, max_year))

indicators = sorted(df["indicator"].dropna().unique().tolist())
sel_indicator = st.sidebar.selectbox("Indicator", indicators)

use_partner = "partner" in df.columns
partner_sel = None
if use_partner:
    partners = sorted(df["partner"].dropna().unique().tolist())
    partner_sel = st.sidebar.multiselect("Partner (optional)", partners, default=[])

# Apply filters
f = df[
    (df["country"].isin(sel_countries)) &
    (df["year"].between(yr[0], yr[1])) &
    (df["indicator"] == sel_indicator)
].copy()

if use_partner and partner_sel:
    f = f[f["partner"].isin(partner_sel)].copy()

# -------- Main layout
st.subheader("Key metrics")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Countries", f["country"].nunique())
c2.metric("Years", f["year"].nunique())
c3.metric("Indicator", sel_indicator)
if use_partner:
    c4.metric("Partners", f["partner"].nunique() if "partner" in f.columns else 0)
else:
    c4.metric("Partners", "N/A")

st.divider()

st.subheader("Trend over time")
if f.empty:
    st.info("No data for the current filters.")
else:
    # aggregate for line chart
    grp_cols = ["year", "country"] + (["partner"] if (use_partner and partner_sel) else [])
    ts = (
        f.groupby(grp_cols, as_index=False)["value"]
         .mean()
         .sort_values("year")
    )

    # Streamlit line chart wants index or x/y; use altair-free default chart:
    st.line_chart(
        ts,
        x="year",
        y="value",
        color="country" if "country" in ts.columns else None
    )

st.subheader("Data preview")
st.dataframe(f.head(200), use_container_width=True)

st.subheader("Download filtered data")
csv_bytes = f.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download CSV",
    data=csv_bytes,
    file_name="trade_filtered.csv",
    mime="text/csv"
)
