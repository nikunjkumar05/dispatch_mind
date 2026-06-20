"""
PhantomBlockageAI — Preprocessing Pipeline
Cleans and transforms BTP violation data into a graph-ready dataset.
"""

import ast
import pandas as pd
import numpy as np
from pathlib import Path


# ── Constants ───────────────────────────────────────────────────────────────
VEHICLE_WEIGHTS = {
    "TANKER": 6.0,
    "BUS": 6.0,
    "TRUCK": 4.0,
    "CAR": 2.0,
    "AUTO": 1.5,
    "PASSENGER AUTO": 1.5,
    "GOODS AUTO": 1.5,
    "MAXI-CAB": 2.0,
    "SCOOTER": 1.0,
    "MOTOR CYCLE": 1.0,
    "VAN": 3.0,
}
DEFAULT_WEIGHT = 1.0

INPUT_CSV = "jan to may police violation_anonymized791b166.csv"
OUTPUT_PARQUET = "processed_data.parquet"


# ── Helpers ─────────────────────────────────────────────────────────────────
def parse_json_column(series: pd.Series) -> list:
    """Safely parse a column containing stringified JSON lists."""
    results = []
    for val in series:
        if pd.isna(val):
            results.append([])
            continue
        try:
            parsed = ast.literal_eval(str(val))
            if isinstance(parsed, list):
                results.append(parsed)
            else:
                results.append([parsed])
        except (ValueError, SyntaxError):
            results.append([])
    return results


def assign_weight(vehicle_type: str) -> float:
    """Map vehicle_type to a blocking weight."""
    if pd.isna(vehicle_type):
        return DEFAULT_WEIGHT
    return VEHICLE_WEIGHTS.get(vehicle_type.upper().strip(), DEFAULT_WEIGHT)


def extract_junction_id(junction_name: str) -> str:
    """Extract BTP junction ID or return FEEDER."""
    if pd.isna(junction_name):
        return "FEEDER"
    jstr = str(junction_name)
    if "BTP" in jstr:
        parts = jstr.split(" - ")[0].split()[-1]
        return parts
    return "FEEDER"


def bucket_time_block(timestamp_str: str) -> str:
    """Bucket a timestamp into a 15-minute interval string."""
    try:
        dt = pd.to_datetime(timestamp_str, utc=True)
        minute_bucket = (dt.minute // 15) * 15
        return dt.strftime(f"%H:{minute_bucket:02d}")
    except Exception:
        return "UNK:00"


# ── Main pipeline ──────────────────────────────────────────────────────────
def preprocess(csv_path: str = INPUT_CSV) -> pd.DataFrame:
    print(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Loaded {len(df):,} rows")

    # Keep only required columns
    keep_cols = [
        "latitude", "longitude", "location", "vehicle_type",
        "validation_timestamp", "junction_name",
        "offence_code", "violation_type",
    ]
    df = df[keep_cols].copy()

    # Parse JSON columns
    print("Parsing offence_code ...")
    df["offence_codes"] = parse_json_column(df["offence_code"])

    print("Parsing violation_type ...")
    df["violations"] = parse_json_column(df["violation_type"])

    # Drop rows with no valid data
    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "vehicle_type"])
    print(f"  Dropped {before - len(df)} rows with missing lat/lon/vehicle_type")

    # Assign weights
    df["weight"] = df["vehicle_type"].apply(assign_weight)

    # Extract junction node
    df["junction_node"] = df["junction_name"].apply(extract_junction_id)

    # Compute time blocks
    df["time_block"] = df["validation_timestamp"].apply(bucket_time_block)

    # Drop original JSON columns (we have parsed versions)
    df = df.drop(columns=["offence_code", "violation_type"])

    n_violations = len(df)
    n_time_blocks = df["time_block"].nunique()
    print(f"Processed {n_violations:,} violations into {n_time_blocks} time blocks")

    return df


if __name__ == "__main__":
    df = preprocess()
    df.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"Saved to {OUTPUT_PARQUET}")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(df.head())
