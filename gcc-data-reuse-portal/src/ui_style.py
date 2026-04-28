import streamlit as st

def apply_global_style(app_title: str):
    st.markdown(
        """
        <style>
        .main h1 { font-size: 2.6rem !important; font-weight: 700; margin-bottom: 0.4rem; }
        .main h2 { font-size: 2.0rem !important; margin-top: 1.5rem; }
        .main h3 { font-size: 1.6rem !important; }

        .main p, .main li { font-size: 1.1rem !important; line-height: 1.6; }

        section[data-testid="stSidebar"] * { font-size: 1.05rem !important; }
        section[data-testid="stSidebar"] h1 { font-size: 1.4rem !important; }
        section[data-testid="stSidebar"] h2 { font-size: 1.25rem !important; }
        section[data-testid="stSidebar"] label { font-size: 1.05rem !important; font-weight: 600; }

        div[data-baseweb="select"] span { font-size: 1.05rem !important; }

        div[data-testid="metric-container"] { font-size: 1.2rem !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"# {app_title}")
