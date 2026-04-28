import pandas as pd
import streamlit as st
from pathlib import Path

PROCESSED = Path("data/processed")

@st.cache_data
def load_trade_by_partner():
    return pd.read_csv(PROCESSED / "trade_by_partner.csv")
