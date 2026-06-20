"""Stage 5: CurbFlex — Chronic zone detection, policy recommendations, enforcement equity analysis."""

import numpy as np
import pandas as pd
from typing import List, Dict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_value


def detect_chronic_violation_zones(df: pd.DataFrame, weekly_threshold: int = None) -> pd.DataFrame:
    """Detect junctions with consistently high violations (>threshold per week) — indicates infrastructure problem."""
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['created_datetime']):
        df['created_datetime'] = pd.to_datetime(df['created_datetime'], format='ISO8601', errors='coerce')

    # Use config value if not provided
    if weekly_threshold is None:
        weekly_threshold = get_config_value('curbflex', 'weekly_threshold', 50)

    df['week'] = df['created_datetime'].dt.isocalendar()['week'].astype(int)
    df['year'] = df['created_datetime'].dt.year

    weekly = df.groupby(['mapped_junction', 'year', 'week']).size().reset_index(name='violations')
    chronic = weekly[weekly['violations'] >= weekly_threshold].groupby('mapped_junction').agg(
        avg_weekly_violations=('violations', 'mean'),
        max_weekly_violations=('violations', 'max'),
        weeks_observed=('violations', 'count'),
        total_violations=('violations', 'sum'),
    ).reset_index().sort_values('avg_weekly_violations', ascending=False)

    print(f"  Chronic zones (>={weekly_threshold}/week): {len(chronic)}")
    return chronic


def generate_policy_recommendations(chronic_zones: pd.DataFrame) -> List[Dict]:
    """Generate parking policy recommendations: >100/wk CRITICAL, >50 HIGH, else MEDIUM."""
    recs = []
    for _, z in chronic_zones.iterrows():
        avg = z['avg_weekly_violations']
        if avg > 100:
            recs.append({'junction': z['mapped_junction'], 'severity': 'CRITICAL', 'priority': 1,
                         'recommendation': 'Convert 20m stretch to paid parking 11AM-8PM',
                         'infrastructure': f"Add {max(5, int(avg / 10))} scooter bays",
                         'estimated_reduction': '72%', 'revenue_projection': f"Rs {int(avg * 50)}/month"})
        elif avg > 50:
            recs.append({'junction': z['mapped_junction'], 'severity': 'HIGH', 'priority': 2,
                         'recommendation': 'Install no-stopping sign 50m from junction approach',
                         'infrastructure': 'Add 5 scooter bays', 'estimated_reduction': '45%',
                         'revenue_projection': 'N/A (enforcement only)'})
        else:
            recs.append({'junction': z['mapped_junction'], 'severity': 'MEDIUM', 'priority': 3,
                         'recommendation': 'Increase patrol frequency during peak hours',
                         'infrastructure': 'None required', 'estimated_reduction': '25%',
                         'revenue_projection': 'N/A'})

    recs.sort(key=lambda x: x['priority'])
    print(f"  Policy recommendations: {len(recs)}")
    return recs


def detect_enforcement_equity(df: pd.DataFrame) -> pd.DataFrame:
    """Detect under-enforced high-impact zones (high violations, low approved tickets)."""
    zone_stats = df.groupby('mapped_junction').agg(
        total_violations=('single_violation', 'count'),
        total_delay=('congestion_cost', 'sum'),
        approved_tickets=('validation_status', lambda x: (x == 'approved').sum()),
    ).reset_index()

    zone_stats['enforcement_rate'] = (zone_stats['approved_tickets'] / zone_stats['total_violations']).round(3)
    median_rate = zone_stats['enforcement_rate'].median()
    zone_stats['enforcement_gap'] = (median_rate - zone_stats['enforcement_rate']).round(3)

    median_delay = zone_stats['total_delay'].median()
    zone_stats['is_under_enforced'] = (zone_stats['enforcement_gap'] > 0.1) & (zone_stats['total_delay'] > median_delay)
    zone_stats['is_over_enforced'] = (zone_stats['enforcement_gap'] < -0.1) & (zone_stats['total_delay'] < median_delay)

    print(f"  Under-enforced zones: {zone_stats['is_under_enforced'].sum()}")
    print(f"  Over-enforced zones: {zone_stats['is_over_enforced'].sum()}")
    return zone_stats


def run_curbflex(df: pd.DataFrame, weekly_threshold: int = None) -> dict:
    """Run Stage 5: CurbFlex analysis — chronic zones + policy + equity."""
    print("=" * 60)
    print("Stage 5: CurbFlex — Chronic Zones + Enforcement Equity")
    print("=" * 60)

    # Use config value if not provided
    if weekly_threshold is None:
        curbflex_config = get_curbflex_config()
        weekly_threshold = curbflex_config.get('weekly_threshold', 50)

    print("\n[1/3] Detecting chronic violation zones...")
    chronic = detect_chronic_violation_zones(df, weekly_threshold)

    print("\n[2/3] Generating policy recommendations...")
    recs = generate_policy_recommendations(chronic)

    print("\n[3/3] Analyzing enforcement equity...")
    equity = detect_enforcement_equity(df)

    if recs:
        print("\n  Top 3 policy recommendations:")
        for r in recs[:3]:
            print(f"    [{r['severity']}] {r['junction']} -> {r['recommendation']} ({r['estimated_reduction']})")

    under = equity[equity['is_under_enforced']]
    if len(under) > 0:
        print("\n  Under-enforced high-impact zones:")
        for _, r in under.head(3).iterrows():
            print(f"    {r['mapped_junction']}: {r['total_violations']:.0f} violations, {r['enforcement_rate']:.1%} rate")

    print("=" * 60)
    print("Stage 5 complete.")
    print("=" * 60)
    return {'chronic_zones': chronic, 'recommendations': recs, 'equity_stats': equity}


if __name__ == '__main__':
    import sys, json
    sys.path.insert(0, '.')
    from src.data_pipeline import run_pipeline
    from src.congestion_cost import run_congestion_cost

    with open('data/external/junction_coords.json') as f:
        coords = json.load(f)

    df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
    df = run_congestion_cost(df, junction_coords=coords)
    results = run_curbflex(df)
