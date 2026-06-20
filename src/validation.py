"""Stage 6: Validation — Backtest, cascade evidence, case study, one-deployment impact numbers."""

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_value
from cross_validation import run_spatial_cv
from enhanced_cascade import run_enhanced_cascade_analysis


def run_backtest(model, df: pd.DataFrame, features: list) -> Dict[str, Any]:
    if model is None:
        return {'r2': 0, 'mae': 0, 'test_size': 0}

    test = df[df['month'] == 2]
    if len(test) == 0:
        return {'r2': 0, 'mae': 0, 'test_size': 0}

    preds = model.predict(test[features].fillna(0))
    y_test = test['congestion_cost']
    result = {'r2': round(r2_score(y_test, preds), 4), 'mae': round(mean_absolute_error(y_test, preds), 4), 'test_size': len(test)}
    print(f"  Backtest R2: {result['r2']}, MAE: {result['mae']}, Test size: {result['test_size']:,}")
    return result


def run_cascade_validation(df: pd.DataFrame, junction_coords: dict) -> Dict[str, Any]:
    from src.cascade import build_adjacency_graph, compute_lag_correlation, detect_cascades

    graph = build_adjacency_graph(junction_coords)
    lag_15 = compute_lag_correlation(df, graph, lag_minutes=15)
    lag_30 = compute_lag_correlation(df, graph, lag_minutes=30)
    correlation_threshold = get_config_value('cascades', 'correlation_threshold', 0.2)
    cascades = detect_cascades(lag_15, threshold_r=correlation_threshold)

    sig_15 = lag_15[lag_15['lag_correlation'] > correlation_threshold] if len(lag_15) > 0 else pd.DataFrame()
    sig_30 = lag_30[lag_30['lag_correlation'] > correlation_threshold] if len(lag_30) > 0 else pd.DataFrame()

    avg_r_15 = sig_15['lag_correlation'].mean() if len(sig_15) > 0 else 0
    max_r_15 = sig_15['lag_correlation'].max() if len(sig_15) > 0 else 0
    top_pair = sig_15.iloc[0] if len(sig_15) > 0 else None

    result = {
        'total_pairs_tested': len(lag_15),
        'significant_pairs_15min': len(sig_15),
        'significant_pairs_30min': len(sig_30),
        'avg_correlation_15min': round(avg_r_15, 4),
        'max_correlation_15min': round(max_r_15, 4),
        'top_from': top_pair['from_junction'] if top_pair is not None else 'N/A',
        'top_to': top_pair['to_junction'] if top_pair is not None else 'N/A',
        'top_distance': top_pair['distance_m'] if top_pair is not None else 0,
        'cascade_chains': len(cascades),
        'longest_chain': ' -> '.join(cascades[0]['chain']) if cascades else 'N/A',
    }

    print(f"  Cascade: {result['significant_pairs_15min']} significant pairs (15min lag)")
    print(f"  Top pair: {result['top_from']} -> {result['top_to']} (r={result['max_correlation_15min']}, {result['top_distance']:.0f}m)")
    return result


def run_silk_board_case_study(df: pd.DataFrame) -> Dict[str, Any]:
    from config import get_validation_config
    
    validation_config = get_validation_config()
    silk_board_junctions = validation_config.get('silk_board_junctions', ['Silk Board', 'Bommanahalli', 'HSR'])
    
    silk = df[df['mapped_junction'].str.contains('|'.join(silk_board_junctions), case=False, na=False)]
    if len(silk) == 0:
        top_junction = df.groupby('mapped_junction')['congestion_cost'].sum().idxmax()
        silk = df[df['mapped_junction'] == top_junction]

    result = {
        'junction': silk['mapped_junction'].iloc[0],
        'total_violations': len(silk),
        'total_delay_minutes': round(silk['congestion_cost'].sum(), 2),
        'avg_delay_per_violation': round(silk['congestion_cost'].mean(), 2),
        'peak_hour': int(silk['created_datetime'].dt.hour.mode().iloc[0]) if len(silk) > 0 else 17,
        'gridlock_score': round(silk['gridlock_score'].mean(), 1),
    }
    print(f"  Case study: {result['junction']} | {result['total_violations']:,} violations | {result['total_delay_minutes']:,.0f} veh-min")
    return result


def generate_one_deployment_example(df: pd.DataFrame) -> Dict[str, Any]:
    from config import get_validation_config
    
    validation_config = get_validation_config()
    WEEKS_IN_DATASET = validation_config.get('weeks_in_dataset', 20)
    ASSUMED_ENFORCEMENT_REDUCTION = validation_config.get('assumed_enforcement_reduction', 0.40)
    FUEL_SAVINGS_PER_VEH_MIN = validation_config.get('fuel_savings_per_veh_min', 0.5)
    
    agg = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'), violation_count=('single_violation', 'count'),
    ).reset_index()
    top = agg.loc[agg['total_delay'].idxmax()]

    vpw = top['violation_count'] / WEEKS_IN_DATASET
    dpw = top['total_delay'] / WEEKS_IN_DATASET
    monthly_saved = dpw * ASSUMED_ENFORCEMENT_REDUCTION * 4
    monthly_fuel = monthly_saved * FUEL_SAVINGS_PER_VEH_MIN

    example = {
        'junction': top['mapped_junction'],
        'violations_per_week': round(vpw),
        'delay_per_week_vehicle_min': round(dpw),
        'if_enforced': {
            'violations_reduction': f"{int(ASSUMED_ENFORCEMENT_REDUCTION * 100)}%",
            'commuter_time_saved': f"{int(monthly_saved / 60)} hours/month",
            'fuel_saved': f"Rs {int(monthly_fuel)}/month",
            'patrol_hours_optimized': f"{int(ASSUMED_ENFORCEMENT_REDUCTION * 100)}% reduction",
        },
    }
    print(f"  One deployment: {example['junction']} | {example['if_enforced']['commuter_time_saved']}")
    return example


def run_validation(df: pd.DataFrame, models: dict = None, junction_coords: dict = None) -> dict:
    print("=" * 60)
    print("Stage 6: Validation")
    print("=" * 60)

    results = {}

    if models and models.get('xgb_model'):
        features = models.get('features', [])
        if features and not all(f in df.columns for f in features):
            from src.prediction import prepare_features
            df, features, _ = prepare_features(df)
        results['backtest'] = run_backtest(models['xgb_model'], df, features)
    else:
        results['backtest'] = {'r2': 0, 'mae': 0}

    if junction_coords:
        results['cascade'] = run_cascade_validation(df, junction_coords)
    else:
        results['cascade'] = {'significant_pairs_15min': 0, 'max_correlation_15min': 0}

    results['case_study'] = run_silk_board_case_study(df)
    results['one_deployment'] = generate_one_deployment_example(df)

    # Run enhanced cascade analysis
    print("\n[7/7] Enhanced cascade analysis...")
    try:
        cascade_results = run_enhanced_cascade_analysis(df, junction_coords)
        results['enhanced_cascade'] = cascade_results
    except Exception as e:
        print(f"  WARNING: Enhanced cascade analysis failed: {e}")
        results['enhanced_cascade'] = {'status': 'failed', 'message': str(e)}

    print(f"\n  XGBoost R2: {results['backtest']['r2']}")
    print(f"  Cascade pairs: {results['cascade']['significant_pairs_15min']} (max r={results['cascade']['max_correlation_15min']})")
    print(f"  Case Study: {results['case_study']['junction']}")
    print(f"  One Deploy: {results['one_deployment']['if_enforced']['commuter_time_saved']}")
    
    if 'enhanced_cascade' in results and results['enhanced_cascade'].get('status') == 'failed':
        print(f"  Enhanced Cascade: Failed - {results['enhanced_cascade']['message']}")
    elif 'enhanced_cascade' in results:
        print(f"  Enhanced Cascade: Causal pairs = {results['enhanced_cascade']['summary']['causal_pairs']}")
        print(f"  Enhanced cascades detected = {results['enhanced_cascade']['summary']['enhanced_cascades_count']}")
    
    print("Stage 6 complete.")
    print("=" * 60)
    return results


if __name__ == '__main__':
    import sys, json
    sys.path.insert(0, '.')
    from src.data_pipeline import run_pipeline
    from src.congestion_cost import run_congestion_cost
    from src.prediction import run_prediction

    # Check if we should run spatial CV
    if len(sys.argv) > 1 and sys.argv[1] == 'spatial_cv':
        print("Running spatial cross-validation...")
        run_spatial_cv()
        sys.exit(0)
    
    # Check if we should run enhanced cascade analysis
    if len(sys.argv) > 1 and sys.argv[1] == 'enhanced_cascade':
        print("Running enhanced cascade analysis...")
        run_enhanced_cascade_analysis()
        sys.exit(0)
    
    with open('data/external/junction_coords.json') as f:
        coords = json.load(f)

    df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
    df = run_congestion_cost(df, junction_coords=coords)
    models = run_prediction(df)
    run_validation(df, models, junction_coords=coords)
