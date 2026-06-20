"""Stage 1: Data Pipeline — Load, explode JSON, estimate duration, classify severity, map junctions."""

import json
import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    get_duration_base_by_type,
    get_vehicle_adjustment,
    get_temporal_factors,
    get_config_value
)


def _parse_violation_types(raw) -> list:
    if pd.isna(raw):
        return ['UNKNOWN']
    try:
        t = json.loads(raw)
        return t if isinstance(t, list) else [t]
    except (json.JSONDecodeError, TypeError):
        return [str(raw)]


def load_and_parse(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df['created_datetime'] = pd.to_datetime(df['created_datetime'], format='ISO8601')
    df['closed_datetime'] = pd.to_datetime(df['closed_datetime'], format='ISO8601', errors='coerce')
    df['hour'] = df['created_datetime'].dt.hour
    df['day_of_week'] = df['created_datetime'].dt.dayofweek
    df['month'] = df['created_datetime'].dt.month
    df['date'] = df['created_datetime'].dt.date

    all_types = df['violation_type'].apply(_parse_violation_types)
    df = df.loc[df.index.repeat(all_types.apply(len))].copy()
    df['single_violation'] = np.concatenate([t for t in all_types])
    print(f"  Parsed {len(df):,} violation events from {csv_path}")
    return df


def estimate_duration(df: pd.DataFrame) -> pd.DataFrame:
    # Calibrate duration using actual data where available
    df = df.copy()
    
    # Use actual duration where closed_datetime is available
    df['actual_duration'] = (df['closed_datetime'] - df['created_datetime']).dt.total_seconds() / 60
    df['actual_duration'] = df['actual_duration'].clip(lower=0, upper=180)  # Reasonable bounds
    
    # Map base duration from config
    df['base_duration'] = df['single_violation'].apply(get_duration_base_by_type)
    
    # Apply vehicle adjustment from config
    df['vehicle_adjustment'] = df['vehicle_type'].map(lambda x: get_vehicle_adjustment(x)).fillna(1.0)
    
    # Apply temporal factors from config
    df['temporal_factors'] = df['created_datetime'].dt.hour.apply(
        lambda h: get_temporal_factors(h)['multiplier']
    )
    
    # Blend actual data with formula (70% actual, 30% formula for training data)
    # This creates a "ground truth" for model calibration
    df['duration_minutes'] = (
        0.7 * df['actual_duration'].fillna(0) +
        0.3 * (df['base_duration'] * df['vehicle_adjustment'] * df['temporal_factors'])
    )
    
    # For violations without actual duration, use formula
    df.loc[df['actual_duration'].isna(), 'duration_minutes'] = (
        df.loc[df['actual_duration'].isna(), 'base_duration'] *
        df.loc[df['actual_duration'].isna(), 'vehicle_adjustment'] *
        df.loc[df['actual_duration'].isna(), 'temporal_factors']
    )
    
    df['duration_minutes'] = df['duration_minutes'].round(1)
    
    # Log calibration statistics
    actual_count = df['actual_duration'].notna().sum()
    formula_count = df['actual_duration'].isna().sum()
    print(f"  Duration calibration: {actual_count:,} actual, {formula_count:,} formula")
    print(f"  Duration: min={df['duration_minutes'].min()}, max={df['duration_minutes'].max()}, mean={df['duration_minutes'].mean():.1f}")
    
    # Save calibration data for analysis
    calibration_data = df[['single_violation', 'vehicle_type', 'created_datetime', 
                          'actual_duration', 'base_duration', 'vehicle_adjustment', 
                          'temporal_factors', 'duration_minutes']].copy()
    calibration_data.to_csv('data/processed/duration_calibration.csv', index=False)
    
    return df


def classify_severity(df: pd.DataFrame) -> pd.DataFrame:
    from config import get_severity_map
    
    # Get severity mapping from config
    severity_map = get_severity_map()
    
    # For backward compatibility, use default if not in config
    if not severity_map:
        severity_map = {
            'DOUBLE PARKING': 3, 'PARKING IN A MAIN ROAD': 3,
            'PARKING ON FOOTPATH': 2, 'PARKING NEAR ROAD CROSSING': 2,
            'PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS': 2,
            'PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC': 2,
        }
    
    df['severity'] = df['single_violation'].map(severity_map).fillna(1).astype(int)
    print(f"  Severity: {dict(df['severity'].value_counts().sort_index())}")
    return df


def map_to_nearest_junction(df: pd.DataFrame, junction_coords: dict) -> pd.DataFrame:
    df['mapped_junction'] = df['junction_name']
    if not junction_coords:
        return df

    jnames = list(junction_coords.keys())
    jlats = np.array([junction_coords[j][0] for j in jnames])
    jlons = np.array([junction_coords[j][1] for j in jnames])
    needs_map = (df['junction_name'] == 'No Junction') | df['junction_name'].isna()

    if needs_map.any():
        lats = df.loc[needs_map, 'latitude'].values[:, None]
        lons = df.loc[needs_map, 'longitude'].values[:, None]
        batch_size = 50_000
        nearest = []
        for i in range(0, len(lats), batch_size):
            dists = np.sqrt((lats[i:i+batch_size] - jlats)**2 + (lons[i:i+batch_size] - jlons)**2) * 111000
            nearest.extend([jnames[j] for j in dists.argmin(axis=1)])
        df.loc[needs_map, 'mapped_junction'] = nearest

    print(f"  Junction mapping: {(df['mapped_junction'] != 'No Junction').sum():,}/{len(df):,} mapped")
    return df


def run_pipeline(csv_path: str, junction_coords: dict = None, output_dir: str = None) -> pd.DataFrame:
    print("=" * 60)
    print("Stage 1: Data Pipeline")
    print("=" * 60)

    df = load_and_parse(csv_path)
    df = estimate_duration(df)
    df = classify_severity(df)
    df = map_to_nearest_junction(df, junction_coords or {})

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path / "violations_scored.csv", index=False)

    print("Stage 1 complete.")
    print("=" * 60)
    return df


if __name__ == '__main__':
    df = run_pipeline(csv_path='data/raw/violations.csv', output_dir='data/processed')
    print(f"\nShape: {df.shape}")
