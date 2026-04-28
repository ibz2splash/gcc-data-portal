import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

def ingest_trade_by_partner():
    path = RAW / "trade_by_partner_raw.csv"
    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path.resolve()}")

    df = pd.read_csv(path)

    rename_map = {
        "COUNTRY": "ref_area",
        "PARTENER COUNTRY": "partner_country",
        "INDICATOR": "indicator",
        "FREQUENCY": "frequency",
        "TIME_PERIOD": "time_period",
        "OBS_VALUE": "value",
    }

    missing = [c for c in rename_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in raw file: {missing}\nFound: {list(df.columns)}")

    df = df.rename(columns=rename_map)
    df = df[list(rename_map.values())]

    df["time_period"] = pd.to_numeric(df["time_period"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["ref_area", "partner_country", "indicator", "time_period", "value"])
    df["source"] = "GCC-STAT Marsa Data Portal"

    out_path = PROCESSED / "trade_by_partner.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved: {out_path}  | rows={len(df)}")

def main():
    ingest_trade_by_partner()

if __name__ == "__main__":
    main()
