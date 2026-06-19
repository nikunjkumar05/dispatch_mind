"""
ParkIntel — Stage 3: Prediction Engine
XGBoost + LightGBM violation prediction with cyclical temporal features.
Replaces Prophet for faster training and simpler deployment.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import LabelEncoder
import pickle
from pathlib import Path


# --- Feature Engineering ----------------------------------------------------

FEATURES = [
    'latitude', 'longitude', 'hour', 'day_of_week', 'month',
    'duration_minutes', 'severity', 'vehicle_type_encoded',
    'violation_type_encoded', 'is_junction', 'junction_distance',
    # Cyclical temporal features (replaces Prophet)
    'is_morning_rush', 'is_evening_rush', 'is_weekend',
    'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
]


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add cyclical temporal features to capture daily/weekly patterns.

    Why cyclical? Hour 23 and hour 0 are 1 hour apart, not 23 hours apart.
    sin/cos encoding preserves this continuity.

    Replaces Prophet: same pattern capture, 100x faster training.
    """
    df = df.copy()
    df['is_morning_rush'] = df['hour'].between(7, 10).astype(int)
    df['is_evening_rush'] = df['hour'].between(17, 20).astype(int)
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Label-encode vehicle_type and violation_type for model input."""
    df = df.copy()
    le_vehicle = LabelEncoder()
    le_violation = LabelEncoder()
    df['vehicle_type_encoded'] = le_vehicle.fit_transform(df['vehicle_type'].astype(str))
    df['violation_type_encoded'] = le_violation.fit_transform(df['single_violation'].astype(str))
    return df, le_vehicle, le_violation


def prepare_features(df: pd.DataFrame):
    """
    Full feature preparation: temporal + categorical encoding.

    Returns: (df_with_features, feature_names, encoders)
    """
    df = add_temporal_features(df)
    df, le_vehicle, le_violation = encode_categoricals(df)

    # Binary: is this a named junction (vs "No Junction" or "Unknown")?
    df['is_junction'] = (~df['mapped_junction'].isin(['No Junction', 'Unknown'])).astype(int)

    encoders = {'vehicle': le_vehicle, 'violation': le_violation}
    return df, FEATURES, encoders


# --- Model Training ---------------------------------------------------------

def train_model(df: pd.DataFrame, features: list = None, model_type: str = 'xgboost', params: dict = None):
    """
    Generic model training on months 1-3, test on month 4.

    Target: congestion_cost (vehicle-minutes of delay)
    Split: temporal (not random) to simulate real forecasting.

    Args:
        df: DataFrame with features and 'congestion_cost' column
        features: list of feature column names
        model_type: 'xgboost' or 'lightgbm'
        params: model hyperparameters (uses defaults if None)

    Returns: (model, metrics_dict)
    """
    if features is None:
        features = FEATURES

    train = df[df['month'].isin([11, 12, 1])]
    test = df[df['month'] == 2]

    if len(train) == 0 or len(test) == 0:
        print(f"  WARNING: Insufficient data for {model_type} train/test split")
        return None, {}

    X_train = train[features].fillna(0)
    y_train = train['congestion_cost']
    X_test = test[features].fillna(0)
    y_test = test['congestion_cost']

    if model_type == 'xgboost':
        default_params = {'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.05,
                          'subsample': 0.8, 'colsample_bytree': 0.8, 'random_state': 42, 'n_jobs': -1}
        model = xgb.XGBRegressor(**(params or default_params))
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    else:
        default_params = {'n_estimators': 500, 'max_depth': 6, 'learning_rate': 0.05,
                          'random_state': 42, 'n_jobs': -1, 'verbose': -1}
        model = lgb.LGBMRegressor(**(params or default_params))
        model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    r2 = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)

    metrics = {'r2': round(r2, 4), 'mae': round(mae, 4), 'train_size': len(train), 'test_size': len(test)}
    print(f"  {model_type}: R2={r2:.4f}, MAE={mae:.4f}")
    return model, metrics


def train_xgboost(df: pd.DataFrame, features: list = None):
    """Train XGBoost model. Wrapper around train_model."""
    return train_model(df, features, model_type='xgboost')


def train_lightgbm(df: pd.DataFrame, features: list = None):
    """Train LightGBM model. Wrapper around train_model."""
    return train_model(df, features, model_type='lightgbm')


# --- Feature Importance -----------------------------------------------------

def get_feature_importance(model, features: list) -> pd.DataFrame:
    """Extract and rank feature importance from trained model."""
    importance = model.feature_importances_
    df_imp = pd.DataFrame({
        'feature': features,
        'importance': importance
    }).sort_values('importance', ascending=False)
    return df_imp


# --- Prediction for Future Periods ------------------------------------------

def predict_next_period(model, df: pd.DataFrame, target_hour: int, target_day: int = None):
    """
    Predict congestion cost for a specific future hour.

    Args:
        model: trained XGBoost or LightGBM model
        df: historical data (used to compute median values for unknowns)
        target_hour: hour to predict (0-23)
        target_day: day of week (0=Monday). If None, uses median.

    Returns: DataFrame with predictions per junction
    """
    # Aggregate historical data by junction
    junction_stats = df.groupby('mapped_junction').agg(
        avg_lat=('latitude', 'mean'),
        avg_lon=('longitude', 'mean'),
        avg_duration=('duration_minutes', 'median'),
        avg_severity=('severity', 'median'),
        avg_distance=('junction_distance', 'median'),
        top_vehicle=('vehicle_type', lambda x: x.mode()[0] if len(x) > 0 else 'CAR'),
        top_violation=('single_violation', lambda x: x.mode()[0] if len(x) > 0 else 'WRONG PARKING'),
    ).reset_index()

    # Build prediction rows
    day = target_day if target_day is not None else df['day_of_week'].median()
    month = df['month'].mode()[0]

    pred_df = junction_stats.copy()
    pred_df['hour'] = target_hour
    pred_df['day_of_week'] = int(day)
    pred_df['month'] = int(month)
    pred_df['duration_minutes'] = pred_df['avg_duration']
    pred_df['severity'] = pred_df['avg_severity'].astype(int)
    pred_df['junction_distance'] = pred_df['avg_distance']
    pred_df['latitude'] = pred_df['avg_lat']
    pred_df['longitude'] = pred_df['avg_lon']
    pred_df['vehicle_type'] = pred_df['top_vehicle']
    pred_df['single_violation'] = pred_df['top_violation']

    # Prepare features
    pred_df = add_temporal_features(pred_df)
    le_v = LabelEncoder()
    le_v.fit(df['vehicle_type'].astype(str))
    pred_df['vehicle_type_encoded'] = le_v.transform(pred_df['vehicle_type'].astype(str))
    le_vio = LabelEncoder()
    le_vio.fit(df['single_violation'].astype(str))
    pred_df['violation_type_encoded'] = le_vio.transform(pred_df['single_violation'].astype(str))
    pred_df['is_junction'] = (~pred_df['mapped_junction'].isin(['No Junction', 'Unknown'])).astype(int)

    # Predict
    pred_df['predicted_cost'] = model.predict(pred_df[FEATURES].fillna(0)).round(2)
    max_cost = pred_df['predicted_cost'].max()
    pred_df['gridlock_score'] = (pred_df['predicted_cost'] / max_cost * 100).clip(0, 100).round(1) if max_cost > 0 else 0.0

    return pred_df[['mapped_junction', 'avg_lat', 'avg_lon', 'predicted_cost', 'gridlock_score']].sort_values('predicted_cost', ascending=False)


# --- Save/Load Models -------------------------------------------------------

def save_model(model, filepath: str):
    """Save trained model to disk."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump(model, f)
    print(f"  Model saved: {filepath}")


def load_model(filepath: str):
    """Load trained model from disk."""
    with open(filepath, 'rb') as f:
        model = pickle.load(f)
    return model


# --- Run Full Stage 3 -------------------------------------------------------

def run_prediction(df: pd.DataFrame, output_dir: str = 'outputs/models'):
    """
    Run Stage 3: Train XGBoost + LightGBM, save models.
    """
    print("=" * 60)
    print("Stage 3: Prediction Engine")
    print("=" * 60)

    print("\n[1/4] Preparing features...")
    df, features, encoders = prepare_features(df)

    print("\n[2/4] Training XGBoost...")
    xgb_model, xgb_metrics = train_xgboost(df, features)

    print("\n[3/4] Training LightGBM...")
    lgb_model, lgb_metrics = train_lightgbm(df, features)

    print("\n[4/4] Feature importance (XGBoost):")
    if xgb_model:
        imp = get_feature_importance(xgb_model, features)
        for _, row in imp.head(5).iterrows():
            print(f"    {row['feature']}: {row['importance']:.4f}")

    # Save models
    if xgb_model:
        save_model(xgb_model, f'{output_dir}/xgboost_violation_predictor.pkl')
    if lgb_model:
        save_model(lgb_model, f'{output_dir}/lightgbm_violation_predictor.pkl')

    print("=" * 60)
    print("Stage 3 complete.")
    print("=" * 60)

    return {
        'xgb_model': xgb_model,
        'lgb_model': lgb_model,
        'xgb_metrics': xgb_metrics,
        'lgb_metrics': lgb_metrics,
        'features': features,
        'encoders': encoders,
    }


if __name__ == '__main__':
    # Run full pipeline
    import json
    from src.data_pipeline import run_pipeline
    from src.congestion_cost import run_congestion_cost

    with open('data/external/junction_coords.json') as f:
        coords = json.load(f)

    df = run_pipeline('data/raw/violations.csv', junction_coords=coords)
    df = run_congestion_cost(df, junction_coords=coords)
    results = run_prediction(df)

    # Test prediction for 6 PM
    if results['xgb_model']:
        print("\nPredicted hotspots for 6 PM (today):")
        pred = predict_next_period(results['xgb_model'], df, target_hour=18)
        print(pred.head(10).to_string())
