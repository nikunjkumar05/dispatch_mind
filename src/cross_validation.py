"""
Cross-validation utilities for DispatchMind / ParkImpact AI.

This module provides spatial cross-validation and baseline model comparisons
to ensure the model generalizes to unseen junctions and isn't overfitting.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_value


def spatial_cross_validation(
    df: pd.DataFrame,
    junction_coords: dict,
    n_folds: int = 5,
    min_junctions_per_fold: int = 3
) -> Dict[str, Any]:
    """
    Leave-one-junction-out cross-validation for spatial generalization.
    
    Args:
        df: DataFrame with features and target
        junction_coords: Dictionary of junction coordinates
        n_folds: Number of folds (default: 5)
        min_junctions_per_fold: Minimum junctions per fold
        
    Returns:
        Dictionary with CV results
    """
    junctions = list(junction_coords.keys())
    
    if len(junctions) < n_folds * min_junctions_per_fold:
        raise ValueError(
            f"Need at least {n_folds * min_junctions_per_fold} junctions "
            f"for {n_folds}-fold CV, got {len(junctions)}"
        )
    
    # Create folds by grouping junctions
    np.random.seed(42)
    shuffled_junctions = np.random.permutation(junctions)
    
    folds = []
    for i in range(n_folds):
        start = i * min_junctions_per_fold
        end = start + min_junctions_per_fold
        fold_junctions = shuffled_junctions[start:end].tolist()
        folds.append(fold_junctions)
    
    # Add remaining junctions to last fold
    remaining = shuffled_junctions[n_folds * min_junctions_per_fold:]
    if remaining:
        folds[-1].extend(remaining)
    
    # Perform CV
    cv_results = []
    
    for fold_idx, test_junctions in enumerate(folds):
        print(f"\nFold {fold_idx + 1}/{n_folds}: Testing on {len(test_junctions)} junctions")
        
        # Training data: all junctions except test
        train_junctions = [j for j in junctions if j not in test_junctions]
        
        # Filter data
        train_mask = df['mapped_junction'].isin(train_junctions)
        test_mask = df['mapped_junction'].isin(test_junctions)
        
        df_train = df[train_mask].copy()
        df_test = df[test_mask].copy()
        
        if len(df_test) == 0:
            print(f"  WARNING: No test data for fold {fold_idx + 1}")
            continue
        
        # Prepare features
        from src.prediction import prepare_features
        
        try:
            df_train_prep, features, encoders = prepare_features(df_train)
            df_test_prep, _, _ = prepare_features(df_test)
            
            # Ensure both have same features
            for f in features:
                if f not in df_test_prep.columns:
                    df_test_prep[f] = 0
                    
        except Exception as e:
            print(f"  ERROR: Feature preparation failed: {e}")
            continue
        
        # Train models
        from src.prediction import train_model
        
        xgb_model, xgb_metrics = train_model(df_train_prep, features, 'xgboost')
        lgb_model, lgb_metrics = train_model(df_train_prep, features, 'lightgbm')
        
        if xgb_model is None:
            print(f"  WARNING: XGBoost training failed for fold {fold_idx + 1}")
            continue
        
        # Evaluate
        fold_results = evaluate_models(
            xgb_model, lgb_model, df_test_prep, features, 
            fold_idx, len(test_junctions), len(df_test)
        )
        
        cv_results.append(fold_results)
    
    # Aggregate results
    if cv_results:
        aggregated = aggregate_cv_results(cv_results)
        return aggregated
    else:
        return {
            'status': 'failed',
            'message': 'All folds failed to train/evaluate'
        }


def evaluate_models(
    xgb_model, lgb_model, df_test: pd.DataFrame,
    features: list, fold_idx: int, n_test_junctions: int, 
    n_test_samples: int
) -> Dict[str, Any]:
    """Evaluate both models on test data."""
    
    results = {
        'fold': fold_idx + 1,
        'test_junctions': n_test_junctions,
        'test_samples': n_test_samples,
        'xgb': {},
        'lgb': {},
        'baseline': {}
    }
    
    # Prepare test data
    X_test = df_test[features].fillna(0)
    y_test = df_test['congestion_cost']
    
    # XGBoost evaluation
    if xgb_model is not None:
        xgb_preds = xgb_model.predict(X_test)
        xgb_r2 = calculate_r2(y_test, xgb_preds)
        xgb_mae = calculate_mae(y_test, xgb_preds)
        
        results['xgb'] = {
            'r2': round(xgb_r2, 4),
            'mae': round(xgb_mae, 4),
            'predictions': xgb_preds.tolist(),
            'actual': y_test.tolist()
        }
    
    # LightGBM evaluation
    if lgb_model is not None:
        lgb_preds = lgb_model.predict(X_test)
        lgb_r2 = calculate_r2(y_test, lgb_preds)
        lgb_mae = calculate_mae(y_test, lgb_preds)
        
        results['lgb'] = {
            'r2': round(lgb_r2, 4),
            'mae': round(lgb_mae, 4),
            'predictions': lgb_preds.tolist(),
            'actual': y_test.tolist()
        }
    
    # Baseline models
    results['baseline'] = {
        'mean': {
            'r2': round(calculate_r2(y_test, np.full(len(y_test), y_test.mean())), 4),
            'mae': round(calculate_mae(y_test, np.full(len(y_test), y_test.mean())), 4)
        },
        'median': {
            'r2': round(calculate_r2(y_test, np.full(len(y_test), y_test.median())), 4),
            'mae': round(calculate_mae(y_test, np.full(len(y_test), y_test.median())), 4)
        }
    }
    
    return results


def calculate_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate R² score."""
    if len(y_true) == 0:
        return 0.0
    
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    
    if ss_tot == 0:
        return 1.0
    
    return 1 - (ss_res / ss_tot)


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate MAE."""
    if len(y_true) == 0:
        return 0.0
    
    return np.mean(np.abs(y_true - y_pred))


def aggregate_cv_results(cv_results: List[Dict]) -> Dict[str, Any]:
    """Aggregate results from all CV folds."""
    
    # Collect metrics
    xgb_r2s = [r['xgb']['r2'] for r in cv_results if 'xgb' in r and 'r2' in r['xgb']]
    xgb_maes = [r['xgb']['mae'] for r in cv_results if 'xgb' in r and 'mae' in r['xgb']]
    
    lgb_r2s = [r['lgb']['r2'] for r in cv_results if 'lgb' in r and 'r2' in r['lgb']]
    lgb_maes = [r['lgb']['mae'] for r in cv_results if 'lgb' in r and 'mae' in r['lgb']]
    
    # Calculate statistics
    aggregated = {
        'n_folds': len(cv_results),
        'xgb': {
            'r2_mean': round(np.mean(xgb_r2s), 4) if xgb_r2s else 0,
            'r2_std': round(np.std(xgb_r2s), 4) if xgb_r2s else 0,
            'r2_median': round(np.median(xgb_r2s), 4) if xgb_r2s else 0,
            'mae_mean': round(np.mean(xgb_maes), 4) if xgb_maes else 0,
            'mae_std': round(np.std(xgb_maes), 4) if xgb_maes else 0,
        },
        'lgb': {
            'r2_mean': round(np.mean(lgb_r2s), 4) if lgb_r2s else 0,
            'r2_std': round(np.std(lgb_r2s), 4) if lgb_r2s else 0,
            'r2_median': round(np.median(lgb_r2s), 4) if lgb_r2s else 0,
            'mae_mean': round(np.mean(lgb_maes), 4) if lgb_maes else 0,
            'mae_std': round(np.std(lgb_maes), 4) if lgb_maes else 0,
        },
        'baseline': {
            'mean': {
                'r2_mean': round(np.mean([r['baseline']['mean']['r2'] for r in cv_results]), 4),
                'mae_mean': round(np.mean([r['baseline']['mean']['mae'] for r in cv_results]), 4),
            },
            'median': {
                'r2_mean': round(np.mean([r['baseline']['median']['r2'] for r in cv_results]), 4),
                'mae_mean': round(np.mean([r['baseline']['median']['mae'] for r in cv_results]), 4),
            }
        },
        'fold_details': cv_results
    }
    
    # Print summary
    print(f"\n{'='*60}")
    print("SPATIAL CROSS-VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"Folds tested: {aggregated['n_folds']}")
    print(f"\nXGBoost:")
    print(f"  R²: {aggregated['xgb']['r2_mean']:.4f} ± {aggregated['xgb']['r2_std']:.4f}")
    print(f"  MAE: {aggregated['xgb']['mae_mean']:.4f} ± {aggregated['xgb']['mae_std']:.4f}")
    print(f"\nLightGBM:")
    print(f"  R²: {aggregated['lgb']['r2_mean']:.4f} ± {aggregated['lgb']['r2_std']:.4f}")
    print(f"  MAE: {aggregated['lgb']['mae_mean']:.4f} ± {aggregated['lgb']['mae_std']:.4f}")
    print(f"\nBaseline (Mean):")
    print(f"  R²: {aggregated['baseline']['mean']['r2_mean']:.4f}")
    print(f"  MAE: {aggregated['baseline']['mean']['mae_mean']:.4f}")
    print(f"{'='*60}")
    
    return aggregated


def run_spatial_cv(
    data_path: str = 'data/processed/violations_scored.csv',
    junction_coords_path: str = 'data/external/junction_coords.json',
    n_folds: int = 5
) -> Dict[str, Any]:
    """Main function to run spatial cross-validation."""
    print("=" * 60)
    print("SPATIAL CROSS-VALIDATION")
    print("=" * 60)
    
    # Load data
    print("Loading data...")
    df = pd.read_csv(data_path)
    df['created_datetime'] = pd.to_datetime(df['created_datetime'])
    
    # Load junction coordinates
    import json
    with open(junction_coords_path) as f:
        junction_coords = json.load(f)
    
    # Run CV
    results = spatial_cross_validation(df, junction_coords, n_folds)
    
    return results


if __name__ == '__main__':
    # Run spatial CV
    results = run_spatial_cv()
    
    if results['status'] == 'failed':
        print(f"CV failed: {results['message']}")
    else:
        print(f"\nCV completed successfully!")
        print(f"Tested on {results['n_folds']} folds")
        print(f"Average XGBoost R²: {results['xgb']['r2_mean']:.4f}")
