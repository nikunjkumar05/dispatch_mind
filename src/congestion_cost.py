"""
ParkIntel — Stage 2: CongestionCost™ + JunctionGuard
Quantifies the actual congestion impact of each parking violation.
"""

import numpy as np
import pandas as pd


# --- Vehicle Width (meters) — for lane blockage calculation -----------------

VEHICLE_WIDTH = {
    'SCOOTER': 0.8, 'CAR': 1.8, 'MOTOR CYCLE': 0.7,
    'PASSENGER AUTO': 1.5, 'BUS (BMTC/KSRTC)': 2.5,
    'HGV': 2.5, 'LGV': 2.2, 'TEMPO': 2.0,
    'MAXI-CAB': 1.8, 'VAN': 1.8, 'GOODS AUTO': 1.8,
    'MOPED': 0.6, 'PRIVATE BUS': 2.5, 'SCHOOL VEHICLE': 2.0,
    'TOURIST BUS': 2.5, 'MINI LORRY': 2.2, 'JEEP': 2.0,
    'TANKER': 2.5, 'OTHERS': 1.8,
}

# --- JunctionGuard: Distance-Based Multipliers -----------------------------
# Closer to junction = exponentially more impact on traffic flow

JUNCTION_MULTIPLIER = {
    (0, 10): 3.0,     # 0-10m: critical — blocks turning movement
    (10, 30): 2.0,    # 10-30m: high — blocks approach lane
    (30, 50): 1.5,    # 30-50m: medium — causes merging friction
    (50, 999): 1.0,   # >50m: baseline — minimal flow impact
}

# --- Vehicle Size Multipliers -----------------------------------------------
# Larger vehicles cause disproportionately more delay

VEHICLE_SIZE_MULTIPLIER = {
    'TANKER': 2.5, 'BUS (BMTC/KSRTC)': 2.5, 'HGV': 2.5,
    'PRIVATE BUS': 2.5, 'TOURIST BUS': 2.5,
    'LGV': 2.2, 'MINI LORRY': 2.2,
    'CAR': 1.8, 'VAN': 1.8, 'MAXI-CAB': 1.8, 'JEEP': 1.8,
    'TEMPO': 1.8, 'GOODS AUTO': 1.8,
    'PASSENGER AUTO': 1.0,
    'SCOOTER': 1.0, 'MOTOR CYCLE': 1.0, 'MOPED': 1.0,
    'SCHOOL VEHICLE': 1.0, 'OTHERS': 1.0,
}

# Default lane width in Bengaluru (meters)
DEFAULT_LANE_WIDTH = 3.5


def compute_distance_to_junction(df: pd.DataFrame, junction_coords: dict) -> pd.DataFrame:
    """
    Compute distance from each violation to its mapped junction.

    For violations with a known junction: uses that junction's coordinates.
    For 'No Junction' or 'Unknown': uses the mapped_junction from Stage 1.

    Args:
        df: DataFrame with 'latitude', 'longitude', 'mapped_junction' columns
        junction_coords: dict of {junction_name: (lat, lon)}

    Returns: DataFrame with 'junction_distance' column (meters).
    """
    if not junction_coords:
        df['junction_distance'] = 50.0  # default: assume medium distance
        print("  No junction coords — defaulting to 50m")
        return df

    jnames = list(junction_coords.keys())
    jlats = np.array([junction_coords[j][0] for j in jnames])
    jlons = np.array([junction_coords[j][1] for j in jnames])

    # Map each row's mapped_junction to coordinates
    junc_lats = df['mapped_junction'].map(lambda x: junction_coords.get(x, (np.nan, np.nan))[0])
    junc_lons = df['mapped_junction'].map(lambda x: junction_coords.get(x, (np.nan, np.nan))[1])

    # Compute distance in meters (Euclidean approximation)
    df['junction_distance'] = (
        np.sqrt((df['latitude'] - junc_lats)**2 + (df['longitude'] - junc_lons)**2) * 111000
    ).round(1)

    # Fill any NaN distances with default
    df['junction_distance'] = df['junction_distance'].fillna(50.0)

    print(f"  Junction distance: min={df['junction_distance'].min():.0f}m, max={df['junction_distance'].max():.0f}m, mean={df['junction_distance'].mean():.0f}m")
    return df


def get_junction_multiplier(distance_meters: float) -> float:
    """JunctionGuard: return distance-based multiplier."""
    for (low, high), mult in JUNCTION_MULTIPLIER.items():
        if low <= distance_meters < high:
            return mult
    return 1.0


def compute_congestion_cost(df: pd.DataFrame, junction_coords: dict, road_width: float = 7.0) -> pd.DataFrame:
    """
    Compute CongestionCost™ for every violation row.

    Formula:
        delay = duration × lane_block × peak × junction_mult × vehicle_mult × severity

    This is THE core metric of ParkIntel. It replaces raw violation counts
    with actual congestion impact measured in vehicle-minutes of delay.

    Args:
        df: DataFrame from Stage 1 (with duration_minutes, severity, vehicle_type, etc.)
        junction_coords: dict of {junction_name: (lat, lon)}
        road_width: total road width in meters (default 7m = 2 lanes)

    Returns: DataFrame with congestion_cost, gridlock_score, and intermediate columns.
    """
    print("\n  Computing CongestionCost™...")

    # Step 1: Junction distance
    df = compute_distance_to_junction(df, junction_coords)

    # Step 2: Lane blockage (vehicle_width / lane_width), capped at 1.0
    veh_width = df['vehicle_type'].map(VEHICLE_WIDTH).fillna(1.8)
    lane_width = road_width / 2  # assume 2 lanes
    df['lane_block'] = (veh_width / lane_width).clip(upper=1.0).round(3)

    # Step 3: Peak hour multiplier (non-overlapping ranges)
    hour = df['created_datetime'].dt.hour
    df['peak'] = 1.0  # default: daytime
    df.loc[(hour >= 7) & (hour < 10), 'peak'] = 2.0    # 7am-9:59am = morning rush
    df.loc[(hour >= 17) & (hour <= 20), 'peak'] = 2.0   # 5pm-8pm = evening rush
    df.loc[(hour >= 22) | (hour <= 5), 'peak'] = 0.5    # 10pm-5am = night

    # Step 4: JunctionGuard multiplier
    df['junction_mult'] = df['junction_distance'].apply(get_junction_multiplier)

    # Step 5: Vehicle size multiplier
    df['vehicle_mult'] = df['vehicle_type'].map(VEHICLE_SIZE_MULTIPLIER).fillna(1.0)

    # Step 6: THE FORMULA
    df['congestion_cost'] = (
        df['duration_minutes']
        * df['lane_block']
        * df['peak']
        * df['junction_mult']
        * df['vehicle_mult']
        * df['severity']
    ).round(2)

    # Step 7: Gridlock Score (0-100 normalization)
    max_cost = df['congestion_cost'].max()
    if max_cost > 0:
        df['gridlock_score'] = (df['congestion_cost'] / max_cost * 100).clip(0, 100).round(1)
    else:
        df['gridlock_score'] = 0.0

    print(f"  CongestionCost: min={df['congestion_cost'].min():.2f}, max={df['congestion_cost'].max():.2f}, mean={df['congestion_cost'].mean():.2f}")
    print(f"  Gridlock Score: min={df['gridlock_score'].min():.1f}, max={df['gridlock_score'].max():.1f}")

    return df


def get_counter_intuitive_examples(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Finds junctions where:
    - Low violation COUNT (few tickets issued → looks unimportant)
    - High total CONGESTION_COST (massive actual delay)

    This proves that count-based heatmaps are misleading.
    """
    junction_stats = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        top_vehicle=('vehicle_type', lambda x: x.mode()[0] if len(x) > 0 else 'UNKNOWN'),
        avg_junction_dist=('junction_distance', 'mean'),
    ).reset_index()

    median_count = junction_stats['violation_count'].median()
    median_delay = junction_stats['total_delay'].median()

    # Low count, high delay — the counter-intuitive ones
    examples = junction_stats[
        (junction_stats['violation_count'] < median_count) &
        (junction_stats['total_delay'] > median_delay)
    ].nlargest(n, 'total_delay')

    # High count, low delay — the "looks bad but isn't" ones
    false_positives = junction_stats[
        (junction_stats['violation_count'] > median_count) &
        (junction_stats['total_delay'] < median_delay)
    ].nlargest(n, 'violation_count')

    return examples, false_positives, junction_stats


def run_congestion_cost(df: pd.DataFrame, junction_coords: dict, road_width: float = 7.0) -> pd.DataFrame:
    """
    Run Stage 2: Compute CongestionCost™ for all violations.
    """
    print("=" * 60)
    print("Stage 2: CongestionCost™ + JunctionGuard")
    print("=" * 60)

    df = compute_congestion_cost(df, junction_coords, road_width)

    examples, false_positives, all_stats = get_counter_intuitive_examples(df)

    print("\n  Counter-Intuitive Examples (low count, high delay):")
    for _, row in examples.head(3).iterrows():
        print(f"    {row['mapped_junction']}: {row['violation_count']:.0f} violations => {row['total_delay']:.1f} vehicle-min delay")

    print("\n  False Positives (high count, low delay):")
    for _, row in false_positives.head(3).iterrows():
        print(f"    {row['mapped_junction']}: {row['violation_count']:.0f} violations => {row['total_delay']:.1f} vehicle-min delay")

    print("=" * 60)
    print("Stage 2 complete.")
    print("=" * 60)
    return df


if __name__ == '__main__':
    # Test with processed data
    df = pd.read_csv('data/processed/violations_scored.csv')
    df['created_datetime'] = pd.to_datetime(df['created_datetime'])
    df = run_congestion_cost(df, junction_coords={})
    print(f"\nShape: {df.shape}")
