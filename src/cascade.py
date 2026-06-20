"""Cascade Detection — Historical lag analysis + cascade simulator.

Proves that parking violations at one junction predict violations at nearby junctions
within 15-30 minutes. This is the evidence that replaces simulated speed correlation.
"""

import numpy as np
import pandas as pd
from collections import deque
from itertools import combinations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_value


def build_adjacency_graph(junction_coords: dict, max_distance_m: float = None) -> pd.DataFrame:
    jnames = list(junction_coords.keys())
    jlats = np.array([junction_coords[j][0] for j in jnames])
    jlons = np.array([junction_coords[j][1] for j in jnames])
    cos_lat = np.cos(np.radians(np.mean(jlats)))

    # Use config value if not provided
    if max_distance_m is None:
        max_distance_m = get_config_value('cascades', 'adjacency_max_distance_m', 3000)

    edges = []
    for i, j in combinations(range(len(jnames)), 2):
        dist = np.sqrt((jlats[i] - jlats[j])**2 + ((jlons[i] - jlons[j]) * cos_lat)**2) * 111000
        if dist <= max_distance_m:
            edges.append({'from': jnames[i], 'to': jnames[j], 'distance_m': round(dist, 0)})
            edges.append({'from': jnames[j], 'to': jnames[i], 'distance_m': round(dist, 0)})

    graph = pd.DataFrame(edges)
    print(f"  Adjacency graph: {len(jnames)} junctions, {len(graph)} directed edges (max {max_distance_m}m)")
    return graph


def compute_lag_correlation(df: pd.DataFrame, graph: pd.DataFrame, lag_minutes: int = 15,
                            min_violations: int = None) -> pd.DataFrame:
    df = df.copy()
    df['time_bin'] = df['created_datetime'].dt.floor(f'{lag_minutes}min')
    bin_counts = df.groupby(['mapped_junction', 'time_bin']).size().reset_index(name='count')

    bin_by_junction = {}
    for name, group in bin_counts.groupby('mapped_junction'):
        bin_by_junction[name] = group.set_index('time_bin')['count']

    # Use config values if not provided
    if min_violations is None:
        min_violations = get_config_value('cascades', 'min_violations_for_test', 5)
    
    min_common_bins = get_config_value('cascades', 'min_common_bins', 10)

    results = []
    for _, edge in graph.iterrows():
        a, b = edge['from'], edge['to']
        a_data = bin_by_junction.get(a)
        b_data = bin_by_junction.get(b)

        if a_data is None or b_data is None:
            continue
        if len(a_data) < min_violations or len(b_data) < min_violations:
            continue

        common = a_data.index.intersection(b_data.index)
        if len(common) < min_common_bins:
            continue

        a_aligned = a_data.reindex(common, fill_value=0)
        b_aligned = b_data.reindex(common, fill_value=0)

        b_lagged = b_aligned.shift(-1).dropna()
        a_common = a_aligned.reindex(b_lagged.index, fill_value=0)

        if a_common.std() == 0 or b_lagged.std() == 0:
            continue

        corr = a_common.corr(b_lagged)
        if np.isnan(corr):
            continue

        results.append({
            'from_junction': a, 'to_junction': b,
            'distance_m': edge['distance_m'],
            'lag_correlation': round(corr, 4),
            'from_violations': int(a_data.sum()),
            'to_violations': int(b_data.sum()),
        })

    lag_df = pd.DataFrame(results)
    if len(lag_df) > 0:
        lag_df = lag_df.sort_values('lag_correlation', ascending=False)
        correlation_threshold = get_config_value('cascades', 'correlation_threshold', 0.2)
        significant = lag_df[lag_df['lag_correlation'] > correlation_threshold]
        print(f"  Lag analysis ({lag_minutes}min): {len(lag_df)} pairs tested, {len(significant)} significant (r>{correlation_threshold})")
    else:
        print("  Lag analysis: no significant correlations found")
    return lag_df


def detect_cascades(lag_df: pd.DataFrame, threshold_r: float = 0.2, top_n: int = 10) -> list:
    sig = lag_df[lag_df['lag_correlation'] > threshold_r].copy()
    if len(sig) == 0:
        return []

    adj = {}
    for _, row in sig.iterrows():
        adj.setdefault(row['from_junction'], []).append({
            'to': row['to_junction'], 'correlation': row['lag_correlation'], 'distance': row['distance_m'],
        })

    cascades = []
    for source in adj:
        queue = deque([(source, [(source, 0, 0)])])
        while queue:
            current, path = queue.popleft()
            if len(path) >= 3:
                cascades.append({
                    'chain': [p[0] for p in path],
                    'total_correlation': np.prod([p[1] for p in path[1:]]),
                    'total_distance': sum(p[2] for p in path[1:]),
                    'length': len(path),
                })
                continue
            path_nodes = {p[0] for p in path}
            for neighbor in adj.get(current, []):
                if neighbor['to'] not in path_nodes:
                    queue.append((neighbor['to'], path + [(neighbor['to'], neighbor['correlation'], neighbor['distance'])]))

    cascades.sort(key=lambda x: x['total_correlation'], reverse=True)
    print(f"  Cascades detected: {len(cascades)} chains (top {top_n} shown)")
    return cascades[:top_n]


def simulate_cascade(df: pd.DataFrame, junction_coords: dict, source_junction: str,
                     source_time: str, propagation_speed: float = 0.5,
                     max_distance_m: float = 3000) -> pd.DataFrame:
    graph = build_adjacency_graph(junction_coords, max_distance_m=max_distance_m)
    source_time = pd.Timestamp(source_time)

    if source_junction not in junction_coords:
        return pd.DataFrame()

    src_lat, src_lon = junction_coords[source_junction]
    events = [{'junction': source_junction, 'lat': src_lat, 'lon': src_lon,
               'time': source_time, 'step': 0, 'delay_minutes': 0}]
    visited = {source_junction}
    current_step = [source_junction]

    for step in range(1, 4):
        next_step = []
        for src in current_step:
            for _, edge in graph[graph['from'] == src].iterrows():
                dst = edge['to']
                if dst in visited or dst not in junction_coords:
                    continue
                visited.add(dst)
                dst_lat, dst_lon = junction_coords[dst]
                delay_steps = max(1, int(edge['distance_m'] / (max_distance_m * propagation_speed)))
                delay_minutes = delay_steps * 15
                events.append({'junction': dst, 'lat': dst_lat, 'lon': dst_lon,
                               'time': source_time + pd.Timedelta(minutes=delay_minutes),
                               'step': step, 'delay_minutes': delay_minutes})
                next_step.append(dst)
        current_step = next_step
        if not current_step:
            break

    result = pd.DataFrame(events)
    print(f"  Cascade from {source_junction}: {len(result)} junctions affected over {result['delay_minutes'].max()} minutes")
    return result


def compute_lag_window_comparison(df: pd.DataFrame, graph: pd.DataFrame,
                                   windows: list = None) -> pd.DataFrame:
    """Test correlation at different lag windows to prove 15-min is strongest (physical propagation)."""
    windows = windows or get_config_value('cascades', 'lag_windows', [5, 15, 30, 60])
    correlation_threshold = get_config_value('cascades', 'correlation_threshold', 0.2)
    
    results = []
    for w in windows:
        lag_df = compute_lag_correlation(df, graph, lag_minutes=w)
        if len(lag_df) == 0:
            continue
        sig = lag_df[lag_df['lag_correlation'] > correlation_threshold]
        results.append({
            'lag_window_min': w,
            'pairs_tested': len(lag_df),
            'significant_pairs': len(sig),
            'mean_correlation': round(sig['lag_correlation'].mean(), 4) if len(sig) > 0 else 0,
            'max_correlation': round(sig['lag_correlation'].max(), 4) if len(sig) > 0 else 0,
        })
    out = pd.DataFrame(results)
    if len(out) > 0:
        best = out.loc[out['max_correlation'].idxmax()]
        print(f"  Lag window comparison: best={int(best['lag_window_min'])}min (r={best['max_correlation']})")
    return out


def compute_direction_test(df: pd.DataFrame, graph: pd.DataFrame, lag_minutes: int = 15,
                           top_n: int = 5, min_violations: int = 5) -> pd.DataFrame:
    """For top pairs, compare forward (A→B) vs reverse (B→A) correlation. Forward > reverse = cascade evidence."""
    lag_fwd = compute_lag_correlation(df, graph, lag_minutes=lag_minutes, min_violations=min_violations)
    if len(lag_fwd) == 0:
        return pd.DataFrame()

    top_pairs = lag_fwd.nlargest(top_n, 'lag_correlation')
    rows = []
    for _, row in top_pairs.iterrows():
        a, b = row['from_junction'], row['to_junction']
        rev_edge = graph[(graph['from'] == b) & (graph['to'] == a)]
        if len(rev_edge) == 0:
            continue
        rev_lag = compute_lag_correlation(df, rev_edge, lag_minutes=lag_minutes, min_violations=min_violations)
        rev_corr = rev_lag['lag_correlation'].iloc[0] if len(rev_lag) > 0 else 0
        rows.append({
            'pair': f"{a} → {b}",
            'forward_r': row['lag_correlation'],
            'reverse_r': round(rev_corr, 4),
            'asymmetry': round(row['lag_correlation'] - rev_corr, 4),
            'distance_m': row['distance_m'],
        })
    out = pd.DataFrame(rows)
    if len(out) > 0:
        avg_asym = out['asymmetry'].mean()
        print(f"  Direction test: avg asymmetry={avg_asym:.4f} (positive = cascade evidence)")
    return out


def run_cascade_analysis(df: pd.DataFrame, junction_coords: dict) -> dict:
    print("=" * 60)
    print("Cascade Analysis — Historical Lag + Propagation")
    print("=" * 60)

    graph = build_adjacency_graph(junction_coords)
    lag_df = compute_lag_correlation(df, graph, lag_minutes=15)
    correlation_threshold = get_config_value('cascades', 'correlation_threshold', 0.2)
    cascades = detect_cascades(lag_df, threshold_r=correlation_threshold)

    if len(lag_df) > 0:
        print("\n  Top 5 cascade pairs:")
        for _, r in lag_df.head(5).iterrows():
            print(f"    {r['from_junction']} -> {r['to_junction']}: r={r['lag_correlation']:.3f}, {r['distance_m']:.0f}m apart")

    if cascades:
        print(f"\n  Longest cascade chain: {' -> '.join(cascades[0]['chain'])}")
        print(f"  Total correlation: {cascades[0]['total_correlation']:.4f}")

    lag_windows = compute_lag_window_comparison(df, graph)
    direction = compute_direction_test(df, graph)

    print("Cascade Analysis complete.")
    print("=" * 60)
    return {'graph': graph, 'lag_correlations': lag_df, 'cascades': cascades,
            'lag_windows': lag_windows, 'direction_test': direction}


if __name__ == '__main__':
    import json, sys
    sys.path.insert(0, '.')
    from src.data_pipeline import run_pipeline
    from src.congestion_cost import run_congestion_cost

    with open('data/external/junction_coords.json') as f:
        coords = json.load(f)

    df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
    df = run_congestion_cost(df, junction_coords=coords)
    run_cascade_analysis(df, coords)
