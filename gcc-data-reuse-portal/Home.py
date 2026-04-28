import streamlit as st
from pathlib import Path
from src.ui_style import apply_global_style


st.set_page_config(page_title="GCC Data Reuse Portal", layout="wide")
apply_global_style("")

ROOT = Path(__file__).resolve().parent
PAGES_DIR = ROOT / "pages"
ASSETS_DIR = ROOT / "assets"

# ---------- Helpers ----------
def find_page_filename(keywords: list[str]) -> str | None:
    """
    Find a page python file in /pages that matches any of the keywords.
    Returns the filename (not full path), e.g. '3_Youth_Opportunity_Radar.py'
    """
    if not PAGES_DIR.exists():
        return None

    files = sorted(PAGES_DIR.glob("*.py"))
    for f in files:
        name = f.name.lower()
        if all(k.lower() in name for k in keywords):
            return f.name

    # fallback: match if ANY keyword appears (useful when typos exist)
    for f in files:
        name = f.name.lower()
        if any(k.lower() in name for k in keywords):
            return f.name

    return None

def safe_asset(name: str) -> str | None:
    """
    Return an asset path if it exists, else None (and show warning).
    """
    p = ASSETS_DIR / name
    if p.exists():
        return str(p)
    return None

def page_ref(filename: str | None) -> str | None:
    if not filename:
        return None
    # st.page_link expects a path relative to entrypoint (Home.py)
    return f"pages/{filename}"

# ---------- Page discovery ----------
tourism_page = find_page_filename(["tourism", "future"])
smart_city_page = find_page_filename(["smart", "city"])
youth_page = find_page_filename(["youth"])  # catches Opportunity/Oppurtunity
trade_page = find_page_filename(["trade", "logistics"])

# ---------- Top header ----------
st.title("GCC Data Reuse Portal")
st.caption("Prototype decision-support portal using official GCC statistics (Marsa).")

st.divider()

st.subheader("Explore the platforms")

# ---------- Cards layout ----------
# Expect these filenames (rename your assets to match):
# assets/tourism.jpg, assets/smart_city.jpg, assets/youth.jpg, assets/trade.jpg
cards = [
    {
        "title": "Tourism Futures",
        "icon": "🌍",
        "desc": "Demand trends, scenario planning, and forecasting for GCC destinations.",
        "image": safe_asset("tourism.jpg"),
        "page": page_ref(tourism_page),
        "fallback_hint": "Check /pages contains a Tourism Futures file (e.g. 1_Tourism_Futures.py).",
    },
    {
        "title": "Smart City Readiness",
        "icon": "🏙️",
        "desc": "Digital readiness, infrastructure capacity, and benchmarking indicators.",
        "image": safe_asset("smart_city.jpg"),
        "page": page_ref(smart_city_page),
        "fallback_hint": "Check /pages contains a Smart City Readiness file (e.g. 2_Smart_City_Readiness.py).",
    },
    {
        "title": "Youth Opportunity Radar",
        "icon": "🎓",
        "desc": "Labour market signals, participation, unemployment, and future skills insights.",
        "image": safe_asset("youth.jpg"),
        "page": page_ref(youth_page),
        "fallback_hint": "Check /pages contains a Youth file (e.g. 3_Youth_Opportunity_Radar.py).",
    },
    {
        "title": "Trade & Logistics Explorer",
        "icon": "🚢",
        "desc": "Trade flows and partner breakdowns with optional scenario benchmarking.",
        "image": safe_asset("trade.jpg"),
        "page": page_ref(trade_page),
        "fallback_hint": "Check /pages contains a Trade Logistics file (e.g. 4_Trade_Logistics_Explorer.py).",
    },
]

c1, c2, c3, c4 = st.columns(4, gap="large")

for col, card in zip([c1, c2, c3, c4], cards):
    with col:
        # Image (optional)
        if card["image"]:
            st.image(card["image"], use_container_width=True)
        else:
            st.info(f"Missing image: /assets/{card['title'].split()[0].lower()}.jpg (optional)")

        st.markdown(f"### {card['icon']} {card['title']}")
        st.write(card["desc"])

        if card["page"]:
            st.page_link(card["page"], label=f"Open {card['title']} →")
        else:
            st.error("Page file not found in /pages.")
            st.caption(card["fallback_hint"])

st.divider()

# ---------- Data transparency (keep this if you want) ----------
st.subheader("Data transparency")
st.markdown(
    """
- **Primary source:** GCC-STAT Marsa exports  
- **Format:** standardized CSV (`country`, `year`, `indicator`, `value`)  
- **Prototype note:** analytics are illustrative; methodology is shown inside each platform page  
"""
)

# Optional: small footer
st.caption("Source: GCC-STAT (Marsa Data Portal). Data reused for educational and analytical purposes.")
