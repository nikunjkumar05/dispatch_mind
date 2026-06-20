"""Stage 2: Congestion Damage Score — Quantifies actual congestion impact per violation."""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    get_vehicle_size_mult,
    get_config_value,
    get_junction_distance_threshold
)


def compute_distance_to_junction(df: pd.DataFrame, junction_coords: dict) -> pd.DataFrame:
    if not junction_coords:
        df['junction_distance'] = 50.0
        return df

    jnames = list(junction_coords.keys())
    jlats = np.array([junction_coords[j][0] for j in jnames])
    jlons = np.array([junction_coords[j][1] for j in jnames])

    junc_lats = df['mapped_junction'].map(dict(zip(jnames, jlats)))
    junc_lons = df['mapped_junction'].map(dict(zip(jnames, jlons)))

    df['junction_distance'] = (
        np.sqrt((df['latitude'] - junc_lats)**2 + (df['longitude'] - junc_lons)**2) * 111000
    ).fillna(50.0).round(1)

    print(f"  Junction distance: min={df['junction_distance'].min():.0f}m, max={df['junction_distance'].max():.0f}m, mean={df['junction_distance'].mean():.0f}m")
    return df


def compute_congestion_cost(df: pd.DataFrame, junction_coords: dict, road_width: float = 7.0) -> pd.DataFrame:
    print("\n  Computing Congestion Damage Score...")

    df = compute_distance_to_junction(df, junction_coords)

    # Get vehicle width from config
    vehicle_width = df['vehicle_type'].map(get_config_value('formula', 'congestion', {}).get('vehicle_width', {})).fillna(1.8)
    df['lane_block'] = (vehicle_width / (road_width / 2)).clip(upper=1.0).round(3)

    hour = df['created_datetime'].dt.hour
    df['peak'] = np.where(
        ((hour >= 7) & (hour < 10)) | ((hour >= 17) & (hour <= 20)), 2.0,
        np.where((hour >= 22) | (hour <= 5), 0.5, 1.0))

    # Get junction distance thresholds from config
    critical_dist = get_junction_distance_threshold('CRITICAL')
    high_dist = get_junction_distance_threshold('HIGH')
    medium_dist = get_junction_distance_threshold('MEDIUM')
    
    df['junction_mult'] = np.select(
        [df['junction_distance'] < critical_dist, 
         df['junction_distance'] < high_dist, 
         df['junction_distance'] < medium_dist],
        [3.0, 2.0, 1.5], default=1.0)

    # Get vehicle size multiplier from config
    df['vehicle_mult'] = df['vehicle_type'].map(get_vehicle_size_mult).fillna(1.0)

    df['congestion_cost'] = (
        df['duration_minutes'] * df['lane_block'] * df['peak']
        * df['junction_mult'] * df['vehicle_mult'] * df['severity']
    ).round(2)

    max_cost = df['congestion_cost'].max()
    df['gridlock_score'] = (df['congestion_cost'] / max_cost * 100).clip(0, 100).round(1) if max_cost > 0 else 0.0

    p50 = df['gridlock_score'].quantile(0.50)
    p80 = df['gridlock_score'].quantile(0.80)
    p95 = df['gridlock_score'].quantile(0.95)
    df['impact_tier'] = pd.cut(
        df['gridlock_score'],
        bins=[0, p50, p80, p95, 100],
        labels=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
        include_lowest=True,
    )

    tier_dist = df['impact_tier'].value_counts()
    print(f"  CongestionCost: min={df['congestion_cost'].min():.2f}, max={df['congestion_cost'].max():.2f}, mean={df['congestion_cost'].mean():.2f}")
    print(f"  Gridlock Score: min={df['gridlock_score'].min():.1f}, max={df['gridlock_score'].max():.1f}")
    print(f"  Impact Tiers: {tier_dist.to_dict()}")
    return df


def get_counter_intuitive_examples(df: pd.DataFrame, n: int = 5):
    stats = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
        avg_junction_dist=('junction_distance', 'mean'),
    ).reset_index()

    med_count = stats['violation_count'].median()
    med_delay = stats['total_delay'].median()

    examples = stats[(stats['violation_count'] < med_count) & (stats['total_delay'] > med_delay)].nlargest(n, 'total_delay')
    false_positives = stats[(stats['violation_count'] > med_count) & (stats['total_delay'] < med_delay)].nlargest(n, 'violation_count')
    return examples, false_positives, stats


def run_congestion_cost(df: pd.DataFrame, junction_coords: dict, road_width: float = 7.0) -> pd.DataFrame:
    print("=" * 60)
    print("Stage 2: Congestion Damage Score + JunctionGuard")
    print("=" * 60)

    df = compute_congestion_cost(df, junction_coords, road_width)
    examples, false_positives, _ = get_counter_intuitive_examples(df)

    print("\n  Counter-Intuitive Examples (low count, high delay):")
    for _, r in examples.head(3).iterrows():
        print(f"    {r['mapped_junction']}: {r['violation_count']:.0f} violations => {r['total_delay']:.1f} vehicle-min delay")

    print("\n  False Positives (high count, low delay):")
    for _, r in false_positives.head(3).iterrows():
        print(f"    {r['mapped_junction']}: {r['violation_count']:.0f} violations => {r['total_delay']:.1f} vehicle-min delay")

    print("Stage 2 complete.")
    print("=" * 60)
    return df


if __name__ == '__main__':
    df = pd.read_csv('data/processed/violations_scored.csv')
    df['created_datetime'] = pd.to_datetime(df['created_datetime'])
    df = run_congestion_cost(df, junction_coords={})
    print(f"\nShape: {df.shape}")
