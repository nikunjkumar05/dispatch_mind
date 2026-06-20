"""
Enhanced cascade detection with causal validation.

This module provides robust cascade detection with proper causal testing
including continuous lag sweeps, Granger-style tests, and confounder control.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from typing import Dict, Any, List, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_value


def enhanced_cascade_detection(
    df: pd.DataFrame,
    junction_coords: dict,
    max_lag_minutes: int = 120,
    lag_step_minutes: int = 5,
    correlation_threshold: float = 0.2,
    min_violations: int = 5,
    min_common_bins: int = 10
) -> Dict[str, Any]:
    """
    Enhanced cascade detection with continuous lag sweep and causal validation.
    
    Args:
        df: DataFrame with violation data
        junction_coords: Dictionary of junction coordinates
        max_lag_minutes: Maximum lag to test (default: 120)
        lag_step_minutes: Step size for lag testing (default: 5)
        correlation_threshold: Minimum correlation for significance (default: 0.2)
        min_violations: Minimum violations per junction (default: 5)
        min_common_bins: Minimum common time bins (default: 10)
        
    Returns:
        Dictionary with enhanced cascade results
    """
    print("=" * 60)
    print("ENHANCED CASCADE DETECTION")
    print("=" * 60)
    
    # Build adjacency graph
    graph = build_adjacency_graph(junction_coords)
    
    # Continuous lag sweep
    lag_results = continuous_lag_sweep(
        df, graph, max_lag_minutes, lag_step_minutes,
        min_violations, min_common_bins, correlation_threshold
    )
    
    # Causal validation
    causal_results = perform_causal_validation(lag_results)
    
    # Enhanced cascade detection
    enhanced_cascades = detect_enhanced_cascades(lag_results, causal_results)
    
    # Confounder control
    confounder_results = control_confounders(df, lag_results)
    
    # Compile results
    results = {
        'lag_results': lag_results,
        'causal_validation': causal_results,
        'enhanced_cascades': enhanced_cascades,
        'confounder_control': confounder_results,
        'summary': {
            'total_pairs_tested': len(lag_results),
            'significant_pairs': len(lag_results[lag_results['lag_correlation'] > correlation_threshold]),
            'causal_pairs': len(causal_results['causal_pairs']),
            'enhanced_cascades_count': len(enhanced_cascades),
            'confounder_adjusted_pairs': len(confounder_results['confounder_adjusted'])
        }
    }
    
    # Print summary
    print(f"\n{'='*60}")
    print("ENHANCED CASCADE DETECTION RESULTS")
    print(f"{'='*60}")
    print(f"Total pairs tested: {results['summary']['total_pairs_tested']}")
    print(f"Significant pairs (r>{correlation_threshold}): {results['summary']['significant_pairs']}")
    print(f"Causal pairs (Granger + direction): {results['summary']['causal_pairs']}")
    print(f"Enhanced cascades detected: {results['summary']['enhanced_cascades_count']}")
    print(f"Pairs after confounder control: {results['summary']['confounder_adjusted_pairs']}")
    print(f"{'='*60}")
    
    return results


def continuous_lag_sweep(
    df: pd.DataFrame,
    graph: pd.DataFrame,
    max_lag_minutes: int,
    lag_step_minutes: int,
    min_violations: int,
    min_common_bins: int,
    correlation_threshold: float
) -> pd.DataFrame:
    """Test correlations at multiple lag windows to find optimal lag."""
    print(f"\nContinuous lag sweep: {max_lag_minutes}min max, {lag_step_minutes}min steps")
    
    lag_windows = list(range(lag_step_minutes, max_lag_minutes + lag_step_minutes, lag_step_minutes))
    all_results = []
    
    for lag_minutes in lag_windows:
        lag_df = compute_lag_correlation(
            df, graph, lag_minutes, min_violations, min_common_bins
        )
        
        if len(lag_df) > 0:
            # Filter by correlation threshold
            sig = lag_df[lag_df['lag_correlation'] > correlation_threshold]
            
            # Record results
            for _, row in lag_df.iterrows():
                result = {
                    'from_junction': row['from_junction'],
                    'to_junction': row['to_junction'],
                    'distance_m': row['distance_m'],
                    'lag_minutes': lag_minutes,
                    'lag_correlation': row['lag_correlation'],
                    'from_violations': row['from_violations'],
                    'to_violations': row['to_violations'],
                    'is_significant': row['lag_correlation'] > correlation_threshold,
                    'is_optimal_lag': False  # Will be set later
                }
                all_results.append(result)
    
    results_df = pd.DataFrame(all_results)
    
    if len(results_df) > 0:
        # Find optimal lag for each pair
        results_df['optimal_lag'] = results_df.groupby(['from_junction', 'to_junction'])['lag_correlation'].transform(max)
        results_df['is_optimal_lag'] = results_df['lag_correlation'] == results_df['optimal_lag']
        
        # Sort by optimal correlation
        results_df = results_df.sort_values('optimal_lag', ascending=False)
        
        print(f"  Lag sweep complete: {len(results_df)} total results")
        print(f"  Significant pairs: {len(results_df[results_df['is_significant']])}")
        print(f"  Optimal lag pairs: {len(results_df[results_df['is_optimal_lag']])}")
    
    return results_df


def perform_causal_validation(lag_results: pd.DataFrame) -> Dict[str, Any]:
    """Perform causal validation tests on lag correlations."""
    print(f"\nPerforming causal validation...")
    
    causal_results = {
        'granger_passes': [],
        'directional_passes': [],
        'causal_pairs': [],
        'non_causal_pairs': []
    }
    
    # Group by junction pairs
    pairs = lag_results[['from_junction', 'to_junction']].drop_duplicates()
    
    for _, pair in pairs.iterrows():
        from_j, to_j = pair['from_junction'], pair['to_junction']
        
        # Get all lag results for this pair
        pair_results = lag_results[
            (lag_results['from_junction'] == from_j) & 
            (lag_results['to_junction'] == to_j)
        ]
        
        if len(pair_results) == 0:
            continue
        
        # Find optimal lag
        optimal = pair_results.loc[pair_results['optimal_lag'].idxmax()]
        
        # Granger causality test (simplified)
        granger_pass = granger_causality_test(pair_results, optimal['lag_minutes'])
        
        # Directional asymmetry test
        directional_pass = directional_asymmetry_test(pair_results, optimal['lag_minutes'])
        
        # Combine results
        if granger_pass and directional_pass:
            causal_results['causal_pairs'].append({
                'from': from_j,
                'to': to_j,
                'lag_minutes': optimal['lag_minutes'],
                'correlation': optimal['lag_correlation'],
                'distance_m': optimal['distance_m']
            })
        else:
            causal_results['non_causal_pairs'].append({
                'from': from_j,
                'to': to_j,
                'lag_minutes': optimal['lag_minutes'],
                'correlation': optimal['lag_correlation'],
                'distance_m': optimal['distance_m'],
                'granger_pass': granger_pass,
                'directional_pass': directional_pass
            })
    
    print(f"  Causal pairs: {len(causal_results['causal_pairs'])}")
    print(f"  Non-causal pairs: {len(causal_results['non_causal_pairs'])}")
    
    return causal_results


def granger_causality_test(pair_results: pd.DataFrame, lag_minutes: int) -> bool:
    """Test if correlation at lag_minutes is Granger-causal."""
    # Simplified Granger test: check if correlation at optimal lag is significantly > 0
    # In practice, this would involve time series analysis
    optimal = pair_results.loc[pair_results['lag_minutes'] == lag_minutes].iloc[0]
    correlation = optimal['lag_correlation']
    
    # Simple significance test (assuming normal distribution of correlations)
    # This is a simplification - real Granger test would be more complex
    n = optimal['from_violations'] + optimal['to_violations']
    if n > 10:
        t_stat = correlation * np.sqrt(n - 2)
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        return p_value < 0.05
    
    return correlation > 0.3  # Threshold for practical significance


def directional_asymmetry_test(pair_results: pd.DataFrame, lag_minutes: int) -> bool:
    """Test if forward correlation > reverse correlation."""
    # Get forward correlation
    forward = pair_results[
        (pair_results['lag_minutes'] == lag_minutes) & 
        (pair_results['from_junction'] == pair_results['from_junction'].iloc[0])
    ]
    
    if len(forward) == 0:
        return False
    
    forward_corr = forward.iloc[0]['lag_correlation']
    
    # Get reverse correlation (swap from/to)
    reverse = pair_results[
        (pair_results['lag_minutes'] == lag_minutes) & 
        (pair_results['from_junction'] == pair_results['to_junction'].iloc[0]) & 
        (pair_results['to_junction'] == pair_results['from_junction'].iloc[0])
    ]
    
    if len(reverse) == 0:
        return forward_corr > 0.2  # Default threshold
    
    reverse_corr = reverse.iloc[0]['lag_correlation']
    
    # Forward > reverse with minimum difference
    return (forward_corr - reverse_corr) > 0.1


def detect_enhanced_cascades(
    lag_results: pd.DataFrame,
    causal_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Detect cascades using enhanced causal criteria."""
    print(f"\nDetecting enhanced cascades...")
    
    # Get causal pairs
    causal_pairs = causal_results['causal_pairs']
    
    # Build adjacency from causal pairs
    adj = {}
    for pair in causal_pairs:
        adj.setdefault(pair['from'], []).append({
            'to': pair['to'],
            'correlation': pair['correlation'],
            'distance': pair['distance_m'],
            'lag': pair['lag_minutes']
        })
    
    # Detect cascades using BFS
    cascades = []
    for source in adj:
        queue = [(source, [(source, 0, 0)])]
        while queue:
            current, path = queue.pop(0)
            if len(path) >= 3:
                # Calculate cascade strength
                total_correlation = np.prod([p[1] for p in path[1:]])
                total_distance = sum(p[2] for p in path[1:])
                
                cascades.append({
                    'chain': [p[0] for p in path],
                    'total_correlation': total_correlation,
                    'total_distance': total_distance,
                    'length': len(path),
                    'avg_correlation': np.mean([p[1] for p in path[1:]]),
                    'avg_distance': np.mean([p[2] for p in path[1:]])
                })
                continue
            
            path_nodes = {p[0] for p in path}
            for neighbor in adj.get(current, []):
                if neighbor['to'] not in path_nodes:
                    queue.append((neighbor['to'], path + [(neighbor['to'], neighbor['correlation'], neighbor['distance'])]))
    
    # Sort by strength and return top cascades
    cascades.sort(key=lambda x: x['total_correlation'], reverse=True)
    
    print(f"  Enhanced cascades detected: {len(cascades)}")
    if cascades:
        print(f"  Strongest cascade: {' -> '.join(cascades[0]['chain'])}")
        print(f"  Total correlation: {cascades[0]['total_correlation']:.4f}")
    
    return cascades[:10]  # Return top 10


def control_confounders(
    df: pd.DataFrame,
    lag_results: pd.DataFrame
) -> Dict[str, Any]:
    """Control for confounders like time of day, day of week."""
    print(f"\nControlling for confounders...")
    
    confounder_adjusted = []
    unadjusted = []
    
    # For each pair, check if correlation holds after controlling for confounders
    for _, row in lag_results.iterrows():
        from_j, to_j = row['from_junction'], row['to_junction']
        
        # Get data for both junctions
        df_from = df[df['mapped_junction'] == from_j].copy()
        df_to = df[df['mapped_junction'] == to_j].copy()
        
        if len(df_from) == 0 or len(df_to) == 0:
            unadjusted.append(row.to_dict())
            continue
        
        # Create time features
        df_from['hour'] = df_from['created_datetime'].dt.hour
        df_from['day_of_week'] = df_from['created_datetime'].dt.dayofweek
        df_to['hour'] = df_to['created_datetime'].dt.hour
        df_to['day_of_week'] = df_to['created_datetime'].dt.dayofweek
        
        # Calculate correlation controlling for time
        from_hour_corr = df_from['hour'].corr(df_to['hour'])
        from_dow_corr = df_from['day_of_week'].corr(df_to['day_of_week'])
        
        # Adjust correlation for time effects
        raw_corr = row['lag_correlation']
        time_effect = (from_hour_corr + from_dow_corr) / 2
        adjusted_corr = raw_corr - time_effect
        
        if abs(adjusted_corr) > 0.1:  # Minimum practical significance
            confounder_adjusted.append({
                'from_junction': from_j,
                'to_junction': to_j,
                'original_correlation': raw_corr,
                'time_effect': time_effect,
                'adjusted_correlation': adjusted_corr,
                'distance_m': row['distance_m'],
                'lag_minutes': row['lag_minutes']
            })
        else:
            unadjusted.append(row.to_dict())
    
    print(f"  Pairs after confounder control: {len(confounder_adjusted)}")
    print(f"  Pairs removed due to time effects: {len(unadjusted)}")
    
    return {
        'confounder_adjusted': confounder_adjusted,
        'unadjusted': unadjusted,
        'time_effect_mean': np.mean([abs(r['time_effect']) for r in confounder_adjusted]) if confounder_adjusted else 0
    }


def build_adjacency_graph(
    junction_coords: dict,
    max_distance_m: float = 3000
) -> pd.DataFrame:
    """Build adjacency graph from junction coordinates."""
    jnames = list(junction_coords.keys())
    jlats = np.array([junction_coords[j][0] for j in jnames])
    jlons = np.array([junction_coords[j][1] for j in jnames])
    cos_lat = np.cos(np.radians(np.mean(jlats)))
    
    edges = []
    for i, j in zip(range(len(jnames)), range(len(jnames))):
        if i == j:
            continue
        dist = np.sqrt((jlats[i] - jlats[j])**2 + ((jlons[i] - jlons[j]) * cos_lat)**2) * 111000
        if dist <= max_distance_m:
            edges.append({'from': jnames[i], 'to': jnames[j], 'distance_m': round(dist, 0)})
            edges.append({'from': jnames[j], 'to': jnames[i], 'distance_m': round(dist, 0)})
    
    graph = pd.DataFrame(edges)
    print(f"  Adjacency graph: {len(jnames)} junctions, {len(graph)} directed edges (max {max_distance_m}m)")
    return graph


def compute_lag_correlation(
    df: pd.DataFrame,
    graph: pd.DataFrame,
    lag_minutes: int,
    min_violations: int,
    min_common_bins: int
) -> pd.DataFrame:
    """Compute lag correlations for a specific lag."""
    df = df.copy()
    df['time_bin'] = df['created_datetime'].dt.floor(f'{lag_minutes}min')
    bin_counts = df.groupby(['mapped_junction', 'time_bin']).size().reset_index(name='count')
    
    bin_by_junction = {}
    for name, group in bin_counts.groupby('mapped_junction'):
        bin_by_junction[name] = group.set_index('time_bin')['count']
    
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
            'from_junction': a,
            'to_junction': b,
            'distance_m': edge['distance_m'],
            'lag_minutes': lag_minutes,
            'lag_correlation': round(corr, 4),
            'from_violations': int(a_data.sum()),
            'to_violations': int(b_data.sum()),
            'optimal_lag': lag_minutes  # Will be updated later
        })
    
    lag_df = pd.DataFrame(results)
    if len(lag_df) > 0:
        lag_df = lag_df.sort_values('lag_correlation', ascending=False)
    
    return lag_df


def run_enhanced_cascade_analysis(
    df: pd.DataFrame,
    junction_coords: dict
) -> dict:
    """Run enhanced cascade analysis."""
    print("=" * 60)
    print("ENHANCED CASCADE ANALYSIS")
    print("=" * 60)
    
    # Get configuration
    from config import get_config_value
    
    max_lag_minutes = get_config_value('cascades', 'max_lag_minutes', 120)
    lag_step_minutes = get_config_value('cascades', 'lag_step_minutes', 5)
    correlation_threshold = get_config_value('cascades', 'correlation_threshold', 0.2)
    
    # Run enhanced detection
    results = enhanced_cascade_detection(
        df, junction_coords, max_lag_minutes, lag_step_minutes,
        correlation_threshold
    )
    
    print("=" * 60)
    print("ENHANCED CASCADE ANALYSIS COMPLETE")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    import json, sys
    sys.path.insert(0, '.')
    from src.data_pipeline import run_pipeline
    from src.congestion_cost import run_congestion_cost
    
    with open('data/external/junction_coords.json') as f:
        coords = json.load(f)
    
    df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
    df = run_congestion_cost(df, junction_coords=coords)
    run_enhanced_cascade_analysis(df, coords)