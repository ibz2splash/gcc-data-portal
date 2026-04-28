import numpy as np
import pandas as pd

def linear_forecast(series_df: pd.DataFrame, year_col="year", value_col="total_value", horizon=3):
    d = series_df.dropna().sort_values(year_col).copy()
    x = d[year_col].astype(int).to_numpy()
    y = d[value_col].astype(float).to_numpy()
    if len(x) < 3:
        return None
    m, b = np.polyfit(x, y, 1)
    future_years = np.arange(x.max() + 1, x.max() + 1 + horizon)
    yhat = m * future_years + b
    return pd.DataFrame({year_col: future_years, value_col: yhat})

def apply_scenario(df: pd.DataFrame, value_col="total_value", delta_pct=0.0):
    out = df.copy()
    out[value_col] = out[value_col] * (1.0 + delta_pct / 100.0)
    return out
