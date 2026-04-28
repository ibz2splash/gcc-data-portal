from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


# -----------------------------
# Data structures
# -----------------------------
@dataclass
class ScenarioLever:
    """
    A single scenario lever.

    shock_pct: size of the policy/external shock expressed as a fraction.
              Example: +10% => 0.10, -5% => -0.05
    elasticity: how sensitive the target metric is to this lever.
                Example: 0.20 means a +10% shock produces ~ +2% effect initially.
    """
    name: str
    shock_pct: float
    elasticity: float
    notes: str = ""


# -----------------------------
# Decay helpers
# -----------------------------
def decay_weights(
    n: int,
    mode: str = "exp",
    half_life_years: float = 2.0,
    end_weight: float = 0.2,
) -> np.ndarray:
    """
    Returns an array of length n with weights that decay over time.

    mode:
      - "none": all 1.0
      - "linear": linearly decays from 1.0 to end_weight
      - "exp": exponential decay with a half-life (in years/steps)

    half_life_years: only used for "exp" mode.
    end_weight: only used for "linear" mode.
    """
    if n <= 0:
        return np.array([], dtype=float)

    mode = (mode or "exp").lower().strip()

    if mode == "none":
        return np.ones(n, dtype=float)

    if mode == "linear":
        end_weight = float(end_weight)
        end_weight = max(min(end_weight, 1.0), 0.0)
        return np.linspace(1.0, end_weight, n, dtype=float)

    # exponential (default)
    half_life_years = float(half_life_years)
    half_life_years = max(half_life_years, 0.1)  # avoid divide-by-zero
    lam = np.log(2.0) / half_life_years
    t = np.arange(n, dtype=float)
    return np.exp(-lam * t)


def _safe_float_series(s: pd.Series) -> pd.Series:
    """Convert series to float safely (handles commas / blanks)."""
    return pd.to_numeric(s, errors="coerce").astype(float)


# -----------------------------
# Scenario application
# -----------------------------
def apply_elastic_scenarios(
    forecast_df: pd.DataFrame,
    value_col: str,
    levers: List[ScenarioLever],
    year_col: str = "year",
    decay_mode: str = "exp",
    half_life_years: float = 2.0,
    linear_end_weight: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply multiple levers to a forecast series using:
      value_t * Π ( 1 + elasticity_i * shock_i * decay_t )

    Returns:
      scenario_df: same df with adjusted value_col
      breakdown_df: lever summary table (avg/end multiplier)
    """
    if forecast_df.empty:
        return forecast_df.copy(), pd.DataFrame(
            columns=["lever", "elasticity", "shock_pct", "avg_multiplier", "end_multiplier", "notes"]
        )

    df = forecast_df.sort_values(year_col).copy()
    df[value_col] = _safe_float_series(df[value_col])

    n = len(df)
    w = decay_weights(n, mode=decay_mode, half_life_years=half_life_years, end_weight=linear_end_weight)

    combined_multiplier = np.ones(n, dtype=float)
    breakdown_rows: List[Dict] = []

    for L in levers:
        e = float(L.elasticity)
        s = float(L.shock_pct)

        # lever multiplier over time
        lever_mult = 1.0 + (e * s * w)

        # multiply stacking (keeps effects from exploding too easily vs adding)
        combined_multiplier *= lever_mult

        breakdown_rows.append(
            {
                "lever": L.name,
                "elasticity": e,
                "shock_pct": s,
                "avg_multiplier": float(np.mean(lever_mult)),
                "end_multiplier": float(lever_mult[-1]),
                "notes": L.notes,
            }
        )

    df[value_col] = df[value_col] * combined_multiplier

    breakdown_df = pd.DataFrame(breakdown_rows)
    return df, breakdown_df


def impact_table(
    base_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    year_col: str = "year",
    value_col: str = "total_value",
) -> pd.DataFrame:
    """
    Merge baseline and scenario values by year and compute absolute and % changes.
    """
    if base_df.empty or scenario_df.empty:
        return pd.DataFrame(columns=[year_col, "baseline", "scenario", "abs_change", "pct_change"])

    b = base_df[[year_col, value_col]].copy()
    s = scenario_df[[year_col, value_col]].copy()

    b[value_col] = _safe_float_series(b[value_col])
    s[value_col] = _safe_float_series(s[value_col])

    b = b.rename(columns={value_col: "baseline"})
    s = s.rename(columns={value_col: "scenario"})

    m = b.merge(s, on=year_col, how="inner").sort_values(year_col)
    m["abs_change"] = m["scenario"] - m["baseline"]
    m["pct_change"] = np.where(m["baseline"] != 0, (m["abs_change"] / m["baseline"]) * 100.0, 0.0)

    return m


# -----------------------------
# Benchmarking helpers
# -----------------------------
def benchmark_countries(
    df_filtered: pd.DataFrame,
    forecast_fn,
    years_ahead: int,
    levers: List[ScenarioLever],
    value_col: str = "total_value",
    year_col: str = "year",
    decay_mode: str = "exp",
    half_life_years: float = 2.0,
    linear_end_weight: float = 0.2,
    agg: str = "end",  # "end" or "avg"
) -> pd.DataFrame:
    """
    Country-to-country scenario benchmarking.

    df_filtered should include at least: country, year, value (or whatever forecast_fn expects)
    forecast_fn(country_df, years_ahead=...) -> forecast_df with columns [year_col, value_col]

    Returns a ranked table by pct_change desc.
    """
    if df_filtered.empty:
        return pd.DataFrame(columns=["country", "baseline", "scenario", "abs_change", "pct_change"])

    rows = []
    countries = sorted(df_filtered["country"].dropna().unique().tolist())

    for c in countries:
        dfc = df_filtered[df_filtered["country"] == c].copy()
        if dfc.empty:
            continue

        base_fc = forecast_fn(dfc, years_ahead=years_ahead).copy()

        # tolerate alternative column name 'value'
        if value_col not in base_fc.columns and "value" in base_fc.columns:
            base_fc = base_fc.rename(columns={"value": value_col})

        scen_fc, _ = apply_elastic_scenarios(
            base_fc,
            value_col=value_col,
            levers=levers,
            year_col=year_col,
            decay_mode=decay_mode,
            half_life_years=half_life_years,
            linear_end_weight=linear_end_weight,
        )

        imp = impact_table(base_fc, scen_fc, year_col=year_col, value_col=value_col)
        if imp.empty:
            continue

        agg = (agg or "end").lower().strip()
        if agg == "avg":
            baseline_metric = float(imp["baseline"].mean())
            scenario_metric = float(imp["scenario"].mean())
            abs_change = float((imp["scenario"] - imp["baseline"]).mean())
            pct_change = float((abs_change / baseline_metric) * 100.0) if baseline_metric != 0 else 0.0
        else:
            baseline_metric = float(imp["baseline"].iloc[-1])
            scenario_metric = float(imp["scenario"].iloc[-1])
            abs_change = float(imp["abs_change"].iloc[-1])
            pct_change = float(imp["pct_change"].iloc[-1])

        rows.append(
            {
                "country": c,
                "baseline": baseline_metric,
                "scenario": scenario_metric,
                "abs_change": abs_change,
                "pct_change": pct_change,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    return out.sort_values("pct_change", ascending=False).reset_index(drop=True)


# -----------------------------
# Utility: quick lever builder
# -----------------------------
def make_levers(raw: List[Dict]) -> List[ScenarioLever]:
    """
    Build ScenarioLever objects from a list of dicts.

    Example dict:
      {"name":"Visa easing", "shock_pct":0.10, "elasticity":0.20, "notes":"Example lever"}
    """
    levers: List[ScenarioLever] = []
    for d in raw:
        levers.append(
            ScenarioLever(
                name=str(d.get("name", "Lever")),
                shock_pct=float(d.get("shock_pct", 0.0)),
                elasticity=float(d.get("elasticity", 0.0)),
                notes=str(d.get("notes", "")),
            )
        )
    return levers
