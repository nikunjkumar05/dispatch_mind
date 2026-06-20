"""
Export all computed data to JSON for the PWA.
Run once: python export_data.py
"""
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, '.')

from src.data_pipeline import run_pipeline
from src.congestion_cost import run_congestion_cost
from src.cascade import run_cascade_analysis
from src.curbflex import run_curbflex

OUT = Path('pwa/data')
OUT.mkdir(parents=True, exist_ok=True)

print("Loading data...")
with open('data/external/junction_coords.json') as f:
    junction_coords = json.load(f)

df = run_pipeline('data/raw/violations.csv', junction_coords=junction_coords)
df = run_congestion_cost(df, junction_coords)

# --- 1. Beat-level queue ---
print("Computing beat queue...")
beat_queue = df.groupby('police_station').agg(
    total_delay=('congestion_cost', 'sum'),
    violation_count=('single_violation', 'count'),
    avg_gridlock=('gridlock_score', 'mean'),
    top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
).reset_index().sort_values('total_delay', ascending=False)

beats_data = {}
for _, beat in beat_queue.iterrows():
    beat_name = beat['police_station']
    beat_df = df[df['police_station'] == beat_name]

    j_queue = beat_df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
        avg_gridlock=('gridlock_score', 'mean'),
        avg_lat=('latitude', 'mean'),
        avg_lon=('longitude', 'mean'),
        worst_tier=('impact_tier', lambda x: x.value_counts().index[0] if len(x) > 0 else 'LOW'),
    ).reset_index().nlargest(5, 'total_delay')

    junctions = []
    for _, j in j_queue.iterrows():
        top_violations = beat_df[beat_df['mapped_junction'] == j['mapped_junction']].nlargest(3, 'congestion_cost')
        viol_list = []
        for _, v in top_violations.iterrows():
            reasons = []
            if v['vehicle_type'] in ['HGV', 'TANKER', 'BUS (BMTC/KSRTC)', 'PRIVATE BUS', 'TOURIST BUS']:
                reasons.append(f"large vehicle ({v['vehicle_type']})")
            if v['duration_minutes'] > 30:
                reasons.append(f"long duration ({v['duration_minutes']:.0f} min)")
            if v['peak'] >= 1.5:
                reasons.append("peak hours")
            if v['impact_tier'] in ['CRITICAL', 'HIGH']:
                reasons.append(f"{v['impact_tier'].title()} impact")
            if not reasons:
                reasons.append("high congestion damage")
            viol_list.append({
                'vehicle': v['vehicle_type'],
                'violation': v['single_violation'],
                'duration': round(v['duration_minutes'], 0),
                'score': round(v['gridlock_score'], 0),
                'tier': v['impact_tier'],
                'reason': 'Ranked because: ' + ', '.join(reasons) + '.',
            })

        junctions.append({
            'name': j['mapped_junction'],
            'total_delay': round(j['total_delay'], 0),
            'violation_count': int(j['violation_count']),
            'top_vehicle': j['top_vehicle'],
            'avg_gridlock': round(j['avg_gridlock'], 1),
            'lat': round(j['avg_lat'], 6),
            'lon': round(j['avg_lon'], 6),
            'tier': j['worst_tier'],
            'top_violations': viol_list,
        })

    beats_data[beat_name] = {
        'total_delay': round(beat['total_delay'], 0),
        'violation_count': int(beat['violation_count']),
        'avg_gridlock': round(beat['avg_gridlock'], 1),
        'top_vehicle': beat['top_vehicle'],
        'junctions': junctions,
    }

# --- 2. Recurrence spots ---
print("Computing recurrence...")
df_sorted = df.sort_values(['mapped_junction', 'created_datetime'])
df_sorted['prev_time'] = df_sorted.groupby('mapped_junction')['created_datetime'].shift(1)
df_sorted['gap_hours'] = (df_sorted['created_datetime'] - df_sorted['prev_time']).dt.total_seconds() / 3600
recurring = df_sorted[df_sorted['gap_hours'] < 2].groupby('mapped_junction').agg(
    recurrence_count=('gap_hours', 'count'),
    avg_gap_hours=('gap_hours', 'mean'),
    total_violations=('single_violation', 'count'),
    total_delay=('congestion_cost', 'sum'),
).reset_index()
recurring = recurring[recurring['total_violations'] >= 3]
recurring['futility_score'] = (recurring['recurrence_count'] / recurring['total_violations'] * 100).round(1)
recurrence_list = recurring.sort_values('futility_score', ascending=False).head(20).to_dict('records')

# --- 3. Repeat offenders ---
print("Computing repeat offenders...")
# Behavioral definition: same vehicle_number, same violation_type, multiple occasions
# Filter for high-impact violations based on actual duration > 30min or severity >= 2
high_impact = df[
    (df['duration_minutes'] > 30) | 
    (df['severity'] >= 2)
].copy()

offenders = high_impact.groupby('vehicle_number').agg(
    violation_count=('single_violation', 'count'),
    stations=('police_station', lambda x: ', '.join(x.unique())),
    total_delay=('congestion_cost', 'sum'),
    avg_gridlock=('gridlock_score', 'mean'),
    top_vehicle=('vehicle_type', 'first'),
    violation_types=('single_violation', lambda x: ', '.join(x.unique())),
    worst_tier=('impact_tier', lambda x: x.value_counts().index[0]),
).reset_index()

offenders = offenders[offenders['violation_count'] >= 3].sort_values('violation_count', ascending=False).head(20)
offenders_list = offenders.to_dict('records')

# --- 4. Camera ROI ---
print("Computing camera ROI...")
device_stats = df.groupby('device_id').agg(
    total_violations=('single_violation', 'count'),
    high_impact=('impact_tier', lambda x: (x.isin(['CRITICAL', 'HIGH'])).sum()),
    total_delay=('congestion_cost', 'sum'),
).reset_index()
device_stats['high_impact_pct'] = (device_stats['high_impact'] / device_stats['total_violations'] * 100).round(1)
device_stats['delay_per_violation'] = (device_stats['total_delay'] / device_stats['total_violations']).round(1)
cameras_list = device_stats.sort_values('high_impact_pct', ascending=False).head(20).to_dict('records')

# --- 5. Station scorecard ---
print("Computing station scorecard...")
station_stats = df.groupby('police_station').agg(
    total_delay=('congestion_cost', 'sum'),
    violation_count=('single_violation', 'count'),
).reset_index()
station_stats['delay_per_ticket'] = (station_stats['total_delay'] / station_stats['violation_count']).round(1)
stations_list = station_stats.sort_values('total_delay', ascending=False).to_dict('records')

# --- 6. Pareto stats ---
print("Computing pareto...")
total_delay = df['congestion_cost'].sum()
j_stats = df.groupby('mapped_junction').agg(
    total_delay=('congestion_cost', 'sum'),
    violation_count=('single_violation', 'count'),
).reset_index().sort_values('total_delay', ascending=False)
j_stats['cumulative_pct'] = (j_stats['total_delay'].cumsum() / total_delay * 100)
j_stats['violation_pct'] = (j_stats['violation_count'] / j_stats['violation_count'].sum() * 100)
pareto_list = j_stats.head(30).to_dict('records')

# --- 7. Counter-intuitive ---
print("Computing counter-intuitive...")
tanker_data = df[df['vehicle_type'] == 'TANKER']
scooter_data = df[df['vehicle_type'].isin(['SCOOTER', 'MOTOR CYCLE', 'MOPED'])]
counter_intuitive = {
    'tanker_delay': round(tanker_data['congestion_cost'].sum(), 0),
    'tanker_count': len(tanker_data),
    'scooter_delay': round(scooter_data['congestion_cost'].sum(), 0),
    'scooter_count': len(scooter_data),
    'ratio': round(tanker_data['congestion_cost'].sum() / scooter_data['congestion_cost'].sum(), 0) if scooter_data['congestion_cost'].sum() > 0 else 0,
}

# --- 8. Map data ---
print("Computing map data...")
map_bubbles = df.groupby('mapped_junction').agg(
    total_delay=('congestion_cost', 'sum'),
    avg_lat=('latitude', 'mean'),
    avg_lon=('longitude', 'mean'),
    violation_count=('single_violation', 'count'),
    top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
).reset_index()
map_bubbles = map_bubbles[map_bubbles['total_delay'] > 0]
map_bubbles['tier'] = 'LOW'
q95 = map_bubbles['total_delay'].quantile(0.95)
q80 = map_bubbles['total_delay'].quantile(0.80)
q50 = map_bubbles['total_delay'].quantile(0.50)
map_bubbles.loc[map_bubbles['total_delay'] > q50, 'tier'] = 'MEDIUM'
map_bubbles.loc[map_bubbles['total_delay'] > q80, 'tier'] = 'HIGH'
map_bubbles.loc[map_bubbles['total_delay'] > q95, 'tier'] = 'CRITICAL'
map_list = map_bubbles.round(6).to_dict('records')

# --- 9. Global stats ---
print("Computing global stats...")
global_stats = {
    'total_violations': len(df),
    'total_delay': round(total_delay, 0),
    'total_junctions': len(j_stats),
    'pareto_pct': round(j_stats[j_stats['cumulative_pct'] >= 82].iloc[0]['violation_pct'], 1) if len(j_stats[j_stats['cumulative_pct'] >= 82]) > 0 else 100,
    'pareto_count': int(j_stats[j_stats['cumulative_pct'] >= 82].index[0] + 1) if len(j_stats[j_stats['cumulative_pct'] >= 82]) > 0 else len(j_stats),
    'formula': {
        'duration_example': round(df['duration_minutes'].median(), 0),
        'peak_example': round(df['peak'].median(), 1),
        'junction_mult_example': round(df['junction_mult'].median(), 1),
        'vehicle_mult_example': round(df['vehicle_mult'].median(), 1),
        'severity_example': round(df['severity'].median(), 1),
    },
}

# --- 10. Hourly distribution ---
print("Computing hourly distribution...")
hourly = df.groupby(df['created_datetime'].dt.hour).size().reset_index(name='count')
hourly.columns = ['hour', 'count']
hourly_list = hourly.to_dict('records')

# --- 11. Cascade (quick summary) ---
print("Computing cascade...")
try:
    cascade_results = run_cascade_analysis(df, junction_coords)
    lag_df = cascade_results['lag_correlations']
    cascades = cascade_results['cascades']
    cascade_summary = {
        'pairs_tested': len(lag_df),
        'strong_pairs': int(len(lag_df[lag_df['lag_correlation'] > 0.3])) if len(lag_df) > 0 else 0,
        'cascade_chains': len(cascades),
        'top_pairs': lag_df.nlargest(5, 'lag_correlation')[['from_junction', 'to_junction', 'distance_m', 'lag_correlation']].round(3).to_dict('records') if len(lag_df) > 0 else [],
    }
except Exception as e:
    print(f"Cascade failed: {e}")
    cascade_summary = {'pairs_tested': 0, 'strong_pairs': 0, 'cascade_chains': 0, 'top_pairs': []}

# --- Write JSON ---
print("Writing JSON...")
output = {
    'global': global_stats,
    'beats': beats_data,
    'recurrence': recurrence_list,
    'offenders': offenders_list,
    'cameras': cameras_list,
    'stations': stations_list,
    'pareto': pareto_list,
    'counter_intuitive': counter_intuitive,
    'map': map_list,
    'hourly_distribution': hourly_list,
    'cascade': cascade_summary,
}

with open(OUT / 'dashboard.json', 'w') as f:
    json.dump(output, f, default=str)

print(f"Done! Written to {OUT / 'dashboard.json'}")
print(f"  Beats: {len(beats_data)}")
print(f"  Recurrence spots: {len(recurrence_list)}")
print(f"  Repeat offenders: {len(offenders_list)}")
print(f"  Cameras: {len(cameras_list)}")
print(f"  Map bubbles: {len(map_list)}")
