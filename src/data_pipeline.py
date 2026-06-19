"""
ParkIntel v2 — Stage 1: Data Pipeline
Parses CSV, explodes JSON violations, estimates duration, classifies severity.
Optimized with vectorized operations (no iterrows).
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path


def _parse_violation_types(raw) -> list:
    """Parse a single violation_type cell — JSON array or plain string."""
    if pd.isna(raw):
        return ['UNKNOWN']
    try:
        types = json.loads(raw)
        if isinstance(types, list):
            return types
        return [types]
    except (json.JSONDecodeError, TypeError):
        return [str(raw)]


def load_and_parse(csv_path: str) -> pd.DataFrame:
    """
    Load CSV and explode JSON violation_type arrays into individual rows.

    The raw CSV has rows like:
        violation_type = '["WRONG PARKING","PARKING NEAR ROAD CROSSING"]'
    This function splits them into two separate rows.

    Returns: DataFrame with ~348K rows (one per violation event).
    """
    df = pd.read_csv(csv_path)

    # Parse timestamps
    df['created_datetime'] = pd.to_datetime(df['created_datetime'], format='ISO8601')
    df['closed_datetime'] = pd.to_datetime(df['closed_datetime'], format='ISO8601', errors='coerce')

    # Extract time features
    df['hour'] = df['created_datetime'].dt.hour
    df['day_of_week'] = df['created_datetime'].dt.dayofweek
    df['month'] = df['created_datetime'].dt.month
    df['date'] = df['created_datetime'].dt.date

    # Explode JSON violation_type — vectorized where possible
    print(f"  Exploding {len(df):,} rows with JSON violation_type...")
    all_types = df['violation_type'].apply(_parse_violation_types)
    df = df.loc[df.index.repeat(all_types.str.len())].copy()
    df['single_violation'] = np.concatenate([t for t in all_types])

    print(f"  Result: {len(df):,} violation events")
    return df


# --- Duration Estimation ---------------------------------------------------

DURATION_BY_TYPE = {
    'WRONG PARKING': 35,
    'NO PARKING': 40,
    'DOUBLE PARKING': 55,
    'PARKING IN A MAIN ROAD': 45,
    'PARKING ON FOOTPATH': 30,
    'PARKING NEAR ROAD CROSSING': 25,
    'PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC': 20,
    'PARKING OPPOSITE TO ANOTHER PARKED VEHICLE': 50,
    'PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS': 25,
}

VEHICLE_ADJUSTMENT = {
    'SCOOTER': 0.8, 'CAR': 1.0, 'MOTOR CYCLE': 0.7,
    'PASSENGER AUTO': 0.9, 'BUS (BMTC/KSRTC)': 1.3,
    'HGV': 1.4, 'LGV': 1.2, 'TEMPO': 1.1,
    'MAXI-CAB': 1.0, 'VAN': 1.0, 'GOODS AUTO': 1.1,
    'MOPED': 0.7, 'PRIVATE BUS': 1.3, 'SCHOOL VEHICLE': 1.0,
    'TOURIST BUS': 1.3, 'MINI LORRY': 1.1, 'JEEP': 1.0,
    'TANKER': 1.4, 'OTHERS': 1.0,
}


def estimate_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimate parking duration when closed_datetime is null (100% of records).

    Formula: duration = base_duration × vehicle_factor × time_of_day_factor
    """
    # Vectorized lookups
    base = df['single_violation'].map(DURATION_BY_TYPE).fillna(35)
    v_factor = df['vehicle_type'].map(VEHICLE_ADJUSTMENT).fillna(1.0)

    # Time of day factor
    hour = df['created_datetime'].dt.hour
    t_factor = pd.Series(1.0, index=df.index)
    t_factor.loc[(hour >= 8) & (hour <= 10)] = 1.2
    t_factor.loc[(hour >= 17) & (hour <= 20)] = 1.2
    t_factor.loc[(hour >= 22) | (hour <= 5)] = 0.7

    df['duration_minutes'] = (base * v_factor * t_factor).round(1)
    print(f"  Duration: min={df['duration_minutes'].min()}, max={df['duration_minutes'].max()}, nulls={df['duration_minutes'].isna().sum()}")
    return df


# --- Severity Classification -----------------------------------------------

SEVERITY_MAP = {
    'DOUBLE PARKING': 3,
    'PARKING IN A MAIN ROAD': 3,
    'PARKING ON FOOTPATH': 2,
    'PARKING NEAR ROAD CROSSING': 2,
    'PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS': 2,
    'PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC': 2,
    'WRONG PARKING': 1,
    'NO PARKING': 1,
    'PARKING OPPOSITE TO ANOTHER PARKED VEHICLE': 1,
}


def classify_severity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each violation into severity tiers.

    Tier 3 (Critical): DOUBLE PARKING, PARKING IN A MAIN ROAD
    Tier 2 (High): blocks vulnerable users (footpath, crossing, hospital)
    Tier 1 (Standard): all others
    """
    df['severity'] = df['single_violation'].map(SEVERITY_MAP).fillna(1).astype(int)
    dist = df['severity'].value_counts().sort_index()
    print(f"  Severity: {dict(dist)}")
    return df


# --- "No Junction" Fix -----------------------------------------------------

def map_to_nearest_junction(df: pd.DataFrame, junction_coords: dict) -> pd.DataFrame:
    """
    ~50% of records have junction_name = 'No Junction'.
    Maps them to the nearest known junction using Euclidean distance (×111000 for meters).
    """
    if not junction_coords:
        df['mapped_junction'] = df['junction_name']
        print("  No junction coords provided — skipping mapping")
        return df

    jnames = list(junction_coords.keys())
    jlats = np.array([junction_coords[j][0] for j in jnames])
    jlons = np.array([junction_coords[j][1] for j in jnames])

    has_junction = df['junction_name'].notna() & (df['junction_name'] != 'No Junction')

    # For rows without junction, find nearest
    need_map = ~has_junction
    if need_map.any():
        lats = df.loc[need_map, 'latitude'].values[:, None]
        lons = df.loc[need_map, 'longitude'].values[:, None]
        dists = np.sqrt((lats - jlats) ** 2 + (lons - jlons) ** 2) * 111000
        nearest_idx = dists.argmin(axis=1)
        df.loc[need_map, 'mapped_junction'] = [jnames[i] for i in nearest_idx]

    # Rows with junction keep their name
    df.loc[has_junction, 'mapped_junction'] = df.loc[has_junction, 'junction_name']

    mapped = (df['mapped_junction'] != 'Unknown').sum()
    print(f"  Junction mapping: {mapped:,}/{len(df):,} mapped")
    return df


# --- Run Full Pipeline -----------------------------------------------------

def run_pipeline(csv_path: str, junction_coords: dict = None, output_dir: str = None) -> pd.DataFrame:
    """
    Run the full Stage 1 pipeline:
        1. Load + parse CSV + explode JSON violations
        2. Estimate duration
        3. Classify severity
        4. Map No Junction → nearest known junction
    """
    print("=" * 60)
    print("Stage 1: Data Pipeline")
    print("=" * 60)

    print("\n[1/4] Loading and parsing CSV...")
    df = load_and_parse(csv_path)

    print("\n[2/4] Estimating parking duration...")
    df = estimate_duration(df)

    print("\n[3/4] Classifying severity...")
    df = classify_severity(df)

    print("\n[4/4] Mapping 'No Junction' records...")
    df = map_to_nearest_junction(df, junction_coords or {})

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        csv_out = out_path / "violations_scored.csv"
        df.to_csv(csv_out, index=False)
        print(f"\n  Saved: {csv_out} ({len(df):,} rows)")

    print("=" * 60)
    print("Stage 1 complete.")
    print("=" * 60)
    return df


if __name__ == '__main__':
    df = run_pipeline(
        csv_path='data/raw/violations.csv',
        output_dir='data/processed',
    )
    print(f"\nShape: {df.shape}")
