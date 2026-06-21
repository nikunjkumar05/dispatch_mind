"""Stage 2: Congestion Damage Score — Quantifies actual congestion impact per violation."""

import numpy as np
import pandas as pd
import sys
from pathlib import Path
from scipy.spatial import KDTree

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    get_vehicle_size_mult,
    get_config_value,
    get_junction_distance_threshold,
    get_metro_construction_zones
)


def compute_spatial_density(df: pd.DataFrame, radius_m: float = 50.0) -> pd.DataFrame:
    """Compute number of violations within radius_m for each record using KDTree.
    
    This measures spatio-temporal density: how many violations are clustered
    in the same area during the same hour window. High density = choke ring.
    """
    print(f"  Computing spatial density (KDTree, radius={radius_m}m)...")
    
    coords = df[['latitude', 'longitude']].values
    
    # Convert radius from meters to degrees (approximate at Bengaluru latitude)
    # 1 degree latitude ≈ 111,000m; 1 degree longitude ≈ 108,200m at 12.97°N
    lat_rad = radius_m / 111000
    lon_rad = radius_m / 108200
    
    # Build KDTree and query for neighbors within radius
    tree = KDTree(coords)
    neighbors_in_radius = tree.query_ball_tree(tree, r=max(lat_rad, lon_rad))
    
    # Count neighbors (excluding self) per record
    df['spatial_density'] = np.array([max(0, len(n) - 1) for n in neighbors_in_radius])
    
    # Log density stats
    print(f"  Spatial density: min={df['spatial_density'].min()}, max={df['spatial_density'].max()}, mean={df['spatial_density'].mean():.1f}")
    print(f"  High-density records (>10 nearby): {(df['spatial_density'] > 10).sum():,}")
    
    return df


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
    df = compute_spatial_density(df, radius_m=50.0)

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

    # Spatial density multiplier: more violations nearby = higher congestion impact
    # log1p to dampen extreme values; normalize to [1.0, 3.0] range
    df['density_mult'] = (1 + np.log1p(df['spatial_density'])).clip(upper=3.0).round(3)

    # Metro construction spillover multiplier
    metro_zones = get_metro_construction_zones()
    df['metro_spillover_mult'] = 1.0
    for zone in metro_zones:
        if 'lat' not in zone or 'lon' not in zone:
            continue
        dist = np.sqrt(
            (df['latitude'] - zone['lat'])**2 + (df['longitude'] - zone['lon'])**2
        ) * 111000
        near = dist <= zone.get('radius_m', 500)
        df.loc[near, 'metro_spillover_mult'] = zone.get('spillover_multiplier', 1.5)

    df['congestion_cost'] = (
        df['duration_minutes'] * df['lane_block'] * df['peak']
        * df['junction_mult'] * df['vehicle_mult'] * df['severity']
        * df['density_mult'] * df['metro_spillover_mult']
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
    
    df = compute_throughput_impact(df)
    
    total_economic = df['economic_loss_inr'].sum()
    total_vehicles = df['vehicles_blocked_hr'].sum()
    total_co2 = df['co2_kg'].sum()
    
    print(f"  CongestionCost: min={df['congestion_cost'].min():.2f}, max={df['congestion_cost'].max():.2f}, mean={df['congestion_cost'].mean():.2f}")
    print(f"  Gridlock Score: min={df['gridlock_score'].min():.1f}, max={df['gridlock_score'].max():.1f}")
    print(f"  Impact Tiers: {tier_dist.to_dict()}")
    print(f"  Throughput: {total_vehicles:,} vehicles/hr blocked, INR {total_economic:,.0f} economic loss, {total_co2:,.1f} kg CO2")
    return df


def compute_throughput_impact(df: pd.DataFrame) -> pd.DataFrame:
    """Compute real-world throughput impact metrics per violation.
    
    Returns columns:
      - vehicles_blocked_hr: estimated vehicles/hour blocked by this violation
      - delay_minutes_total: total person-minutes of delay caused
      - fuel_wasted_liters: fuel wasted due to idling/detour
      - co2_kg: CO2 emissions from wasted fuel
      - economic_loss_inr: economic cost of delay + fuel
      - person_hours_blocked: person-hours of delay
    """
    tp = get_config_value('formula', 'throughput', {})
    
    road_cap = tp.get('road_capacity_veh_per_hour', {}).get('main_road', 1200)
    avg_delay = tp.get('avg_delay_minutes_per_block', 8.5)
    fuel_cost = tp.get('fuel_cost_per_liter_inr', 102.5)
    fuel_rate = tp.get('fuel_consumption_liter_per_veh_min', 0.008)
    co2_factor = tp.get('co2_kg_per_liter', 2.31)
    passengers = tp.get('avg_passengers_per_vehicle', 1.8)
    person_hour_val = tp.get('person_hour_value_inr', 150)
    
    df['vehicles_blocked_hr'] = (
        df['lane_block'] * road_cap * df['peak'] * df['density_mult']
    ).round(0).astype(int)
    
    df['delay_minutes_total'] = (
        df['vehicles_blocked_hr'] * avg_delay * df['duration_minutes'] / 60
    ).round(1)
    
    df['person_hours_blocked'] = (
        df['delay_minutes_total'] * passengers / 60
    ).round(2)
    
    df['fuel_wasted_liters'] = (
        df['vehicles_blocked_hr'] * df['duration_minutes'] * fuel_rate
    ).round(3)
    
    df['co2_kg'] = (df['fuel_wasted_liters'] * co2_factor).round(3)
    
    df['economic_loss_inr'] = (
        df['person_hours_blocked'] * person_hour_val +
        df['fuel_wasted_liters'] * fuel_cost
    ).round(2)
    
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
