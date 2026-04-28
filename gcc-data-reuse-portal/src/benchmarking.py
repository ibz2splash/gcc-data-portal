import pandas as pd
from src.scenarios import apply_elastic_scenarios, impact_table

def benchmark_scenario(
    df_filtered: pd.DataFrame,
    forecast_fn,
    years_ahead: int,
    levers: list,
    decay_mode: str = "exp",
    half_life_years: float = 2.0,
    agg: str = "end",
):
    rows = []

    for c in sorted(df_filtered["country"].unique()):
        dfc = df_filtered[df_filtered["country"] == c].copy()

        base_fc = forecast_fn(dfc, years_ahead=years_ahead).copy()

        # accept either 'value' or 'total_value'
        if "total_value" not in base_fc.columns and "value" in base_fc.columns:
            base_fc = base_fc.rename(columns={"value": "total_value"})

        scen_fc, _ = apply_elastic_scenarios(
            base_fc,
            value_col="total_value",
            levers=levers,
            decay_mode=decay_mode,
            half_life_years=half_life_years,
        )

        imp = impact_table(base_fc, scen_fc, year_col="year", value_col="total_value")

        if agg == "avg":
            baseline_metric = float(imp["baseline"].mean())
            scenario_metric = float(imp["scenario"].mean())
            abs_change = float((imp["scenario"] - imp["baseline"]).mean())
            pct_change = float((abs_change / baseline_metric) * 100) if baseline_metric != 0 else 0.0
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

    return pd.DataFrame(rows).sort_values("pct_change", ascending=False).reset_index(drop=True)
