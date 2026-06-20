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
    """Robust parsing of stringified JSON arrays with multiple fallbacks."""
    import ast
    import re
    
    if pd.isna(raw) or raw == "":
        return ['UNKNOWN']
    
    # Try JSON first (handles proper JSON: ["WRONG PARKING"])
    try:
        t = json.loads(raw)
        return t if isinstance(t, list) else [t]
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Try ast.literal_eval for Python literals (handles: ['WRONG PARKING'])
    try:
        t = ast.literal_eval(raw)
        return t if isinstance(t, list) else [t]
    except (ValueError, SyntaxError):
        pass
    
    # Fallback: extract quoted strings (handles: "['WRONG PARKING']", "WRONG PARKING")
    matches = re.findall(r'["\']([^"\']+)["\']', str(raw))
    return matches if matches else [str(raw).strip()]


def load_and_parse(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df['created_datetime'] = pd.to_datetime(df['created_datetime'], format='ISO8601', utc=True).dt.tz_localize(None)
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
    """Estimate violation duration using domain-expert formula (no closed_date dependency)."""
    df = df.copy()
    
    # Base duration from config by violation type
    df['base_duration'] = df['single_violation'].apply(get_duration_base_by_type)
    
    # Vehicle size adjustment from config
    df['vehicle_adjustment'] = df['vehicle_type'].map(lambda x: get_vehicle_adjustment(x)).fillna(1.0)
    
    # Temporal multiplier (peak/off-peak/normal) from config
    df['temporal_factors'] = df['created_datetime'].dt.hour.apply(
        lambda h: get_temporal_factors(h)['multiplier']
    )
    
    # Pure formula: base × vehicle × temporal
    df['duration_minutes'] = (
        df['base_duration'] * df['vehicle_adjustment'] * df['temporal_factors']
    ).round(1)
    
    print(f"  Duration (formula-only): min={df['duration_minutes'].min()}, max={df['duration_minutes'].max()}, mean={df['duration_minutes'].mean():.1f}")
    
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
