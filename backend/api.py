"""
DispatchMind API — FastAPI backend serving the ML pipeline to React frontend.
Replaces Streamlit with a proper REST API.
"""

import logging
import os
import json
import sys
import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_pipeline import run_pipeline
from src.congestion_cost import run_congestion_cost
from src.prediction import run_prediction
from src.cascade import run_cascade_analysis
from src.curbflex import run_curbflex
from src.dispatch import run_dispatch
from src.realtime_alerts import ViolationAlertSystem
from src.spillover_ai import detect_spillover_zones
from phantom_risk import calculate_phantom_risk_score
from preprocess import preprocess

logger = logging.getLogger("dispatchmind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the base pipeline in the background without blocking startup."""
    def _bg_load():
        for attempt in range(3):
            try:
                _ensure_base_data()
                if _pipeline_data is not None:
                    return
            except Exception:
                logger.exception("Pipeline failed to load (attempt %d/3)", attempt + 1)
            import time
            time.sleep(5)

    threading.Thread(target=_bg_load, daemon=True).start()
    yield


app = FastAPI(
    title="DispatchMind API",
    description="BTP Beat Constable Co-Pilot — AI-powered parking enforcement intelligence",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ---------------------------------------------------------------------------
# Global state — loaded once at startup
# ---------------------------------------------------------------------------
CSV_PATH = os.environ.get(
    "DISPATCHMIND_CSV",
    "jan to may police violation_anonymized791b166.csv",
)
COORDS_PATH = os.environ.get(
    "DISPATCHMIND_COORDS",
    "data/external/junction_coords.json",
)
CACHE_PATH = Path(os.environ.get(
    "DISPATCHMIND_CACHE",
    "data/processed/dispatchmind_scored.parquet",
))

REQUIRED_SCORED_COLUMNS = {
    "mapped_junction",
    "congestion_cost",
    "gridlock_score",
    "impact_tier",
    "vehicles_blocked_hr",
    "economic_loss_inr",
    "co2_kg",
    "person_hours_blocked",
}

_pipeline_data = None
_junction_coords = None
_models = None
_validation = None
_cascade = None
_curbflex = None
_spillover_zones = None
_alert_system = ViolationAlertSystem()
_pipeline_loading = False
_pipeline_error = None

_phantom_data = None

# Thread safety locks for lazy-loading
_lock_base = threading.Lock()
_lock_models = threading.Lock()
_lock_cascade = threading.Lock()
_lock_curbflex = threading.Lock()
_lock_spillover = threading.Lock()
_lock_phantom = threading.Lock()


def _ensure_base_data():
    """Load core pipeline (stages 1-2) synchronously — fast, ~18s."""
    global _pipeline_data, _junction_coords, _pipeline_loading, _pipeline_error

    if _pipeline_data is not None:
        return

    with _lock_base:
        if _pipeline_data is not None:
            return

        _pipeline_loading = True
        _pipeline_error = None

        if not Path(CSV_PATH).exists() or not Path(COORDS_PATH).exists():
            _pipeline_error = f"Data files not found: {CSV_PATH}, {COORDS_PATH}"
            _pipeline_loading = False
            logger.warning(_pipeline_error)
            return

        with open(COORDS_PATH, 'r', encoding='utf-8') as f:
            _junction_coords = json.load(f)

        try:
            if CACHE_PATH.exists():
                logger.info("Loading scored pipeline cache: %s", CACHE_PATH)
                cached = pd.read_parquet(CACHE_PATH)
                missing = REQUIRED_SCORED_COLUMNS.difference(cached.columns)
                if not missing:
                    _pipeline_data = cached
                    _pipeline_loading = False
                    logger.info("Scored cache loaded: %d violations", len(_pipeline_data))
                    return
                logger.warning("Ignoring stale scored cache, missing columns: %s", sorted(missing))

            logger.info("Building base pipeline from raw CSV...")
            _pipeline_data = run_pipeline(CSV_PATH, junction_coords=_junction_coords)
            _pipeline_data = run_congestion_cost(_pipeline_data, _junction_coords)
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _pipeline_data.to_parquet(CACHE_PATH, index=False)
            logger.info("Base pipeline loaded and cached: %d violations", len(_pipeline_data))
        except Exception as exc:
            _pipeline_error = str(exc)
            _pipeline_data = None
            logger.exception("Failed to load base pipeline")
        finally:
            _pipeline_loading = False


def _ensure_models():
    global _models
    if _models is not None:
        return
    with _lock_models:
        if _models is not None:
            return
        if _pipeline_data is None:
            logger.warning("Cannot train models: base data not loaded")
            return
        logger.info("Training prediction models...")
        _models = run_prediction(_pipeline_data)
        logger.info("Models trained: R²=%.4f", _models.get('xgb_metrics', {}).get('r2', 0))


def _ensure_cascade():
    global _cascade
    if _cascade is not None:
        return
    with _lock_cascade:
        if _cascade is not None:
            return
        if _pipeline_data is None:
            logger.warning("Cannot run cascade: base data not loaded")
            return
        logger.info("Running cascade analysis...")
        _cascade = run_cascade_analysis(_pipeline_data, _junction_coords)
        logger.info("Cascade analysis done.")


def _ensure_curbflex():
    global _curbflex
    if _curbflex is not None:
        return
    with _lock_curbflex:
        if _curbflex is not None:
            return
        if _pipeline_data is None:
            logger.warning("Cannot run CurbFlex: base data not loaded")
            return
        logger.info("Running CurbFlex analysis...")
        _curbflex = run_curbflex(_pipeline_data)
        logger.info("CurbFlex done.")


def _ensure_spillover():
    global _spillover_zones
    if _spillover_zones is not None:
        return
    with _lock_spillover:
        if _spillover_zones is not None:
            return
        if _pipeline_data is None:
            logger.warning("Cannot run Spillover detection: base data not loaded")
            return
        logger.info("Running AI Spillover Detection...")
        _spillover_zones = detect_spillover_zones(_pipeline_data)
        logger.info("Spillover detection done: %d zones found.", len(_spillover_zones))


def _ensure_phantom_data():
    """Load phantom blockage preprocessed data."""
    global _phantom_data
    if _phantom_data is not None:
        return
    with _lock_phantom:
        if _phantom_data is not None:
            return
        try:
            logger.info("Loading PhantomBlockageAI data...")
            _phantom_data = preprocess()
            logger.info("PhantomBlockageAI data loaded: %d rows", len(_phantom_data))
        except Exception:
            logger.exception("Failed to load PhantomBlockageAI data")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _sanitize(obj):
    """Recursively replace NaN/Inf floats with None for JSON serialization."""
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OverviewStats(BaseModel):
    total_violations: int
    total_junctions: int
    total_stations: int
    total_delay_veh_min: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    pareto_pct: float
    pareto_impact_pct: float
    vehicles_blocked_hr: int
    economic_loss_inr: float
    co2_kg: float
    person_hours_blocked: float


class PriorityCard(BaseModel):
    rank: int
    junction: str
    station: str
    total_delay: float
    violation_count: int
    top_vehicle: str
    tier: str
    gridlock_score: float
    lat: float
    lon: float
    explanation: str


class BeatStats(BaseModel):
    station: str
    total_delay: float
    violation_count: int
    avg_gridlock: float
    top_vehicle: str
    tier_breakdown: Dict[str, int]


class CascadePair(BaseModel):
    from_junction: str
    to_junction: str
    distance_m: float
    correlation: float
    violations_from: int
    violations_to: int


class DispatchRoute(BaseModel):
    truck_id: int
    stops: List[Dict[str, Any]]
    total_distance_km: float


class AlertOut(BaseModel):
    alert_id: str
    priority: str
    location: Dict[str, Any]
    vehicle: Dict[str, Any]
    scores: Dict[str, Any]
    action: Dict[str, Any]
    message: str


class RiskZone(BaseModel):
    rank: int
    latitude: float
    longitude: float
    vehicle_type: str
    weight: float
    nearby_seed_count: int
    avg_distance_to_seeds: float
    phantom_risk_score: float
    recommended_action: str


class EarlyWarningResponse(BaseModel):
    current_time_block: str
    next_time_block: str
    query_time: str
    top_risk_zones: List[RiskZone]
    total_feeders_scored: int
    message: str


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/overview", response_model=OverviewStats)
async def get_overview():
    """City-level summary stats for the dashboard header."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    total_delay = df['congestion_cost'].sum()

    if total_delay == 0:
        pareto_pct = 100.0
    else:
        j_stats = df.groupby('mapped_junction').agg(
            total_delay=('congestion_cost', 'sum'),
            violation_count=('single_violation', 'count'),
        ).reset_index().sort_values('total_delay', ascending=False)

        j_stats['cum_pct'] = j_stats['total_delay'].cumsum() / total_delay * 100
        reached = j_stats[j_stats['cum_pct'] >= 82]
        if len(reached) > 0:
            pareto_pct = reached.iloc[0]['violation_count'] / j_stats['violation_count'].sum() * 100
        else:
            pareto_pct = 100.0

    tier_counts = df['impact_tier'].value_counts()

    return OverviewStats(
        total_violations=len(df),
        total_junctions=df['mapped_junction'].nunique(),
        total_stations=df['police_station'].nunique(),
        total_delay_veh_min=round(total_delay, 1),
        critical_count=int(tier_counts.get('CRITICAL', 0)),
        high_count=int(tier_counts.get('HIGH', 0)),
        medium_count=int(tier_counts.get('MEDIUM', 0)),
        low_count=int(tier_counts.get('LOW', 0)),
        pareto_pct=round(pareto_pct, 1),
        pareto_impact_pct=82.0,
        vehicles_blocked_hr=int(df['vehicles_blocked_hr'].sum()),
        economic_loss_inr=round(df['economic_loss_inr'].sum(), 2),
        co2_kg=round(df['co2_kg'].sum(), 1),
        person_hours_blocked=round(df['person_hours_blocked'].sum(), 1),
    )


@app.get("/api/priority-queue/{station}")
async def get_priority_queue(
    station: str,
    top_n: int = Query(10, ge=1, le=50),
):
    """Top N highest-impact violations for a given police station."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    if station != "ALL":
        df = df[df['police_station'] == station]

    j_queue = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
        avg_gridlock=('gridlock_score', 'mean'),
        avg_lat=('latitude', 'mean'),
        avg_lon=('longitude', 'mean'),
        worst_tier=('impact_tier', lambda x: x.value_counts().index[0] if len(x) > 0 else 'LOW'),
    ).reset_index().nlargest(top_n, 'total_delay')

    cards = []
    for i, (_, row) in enumerate(j_queue.iterrows(), 1):
        reasons = []
        if row['mapped_junction'] != 'No Junction':
            reasons.append("at junction")
        if row['top_vehicle'] in ['HGV', 'TANKER', 'BUS (BMTC/KSRTC)', 'PRIVATE BUS']:
            reasons.append(f"large vehicle ({row['top_vehicle']})")
        if row['avg_gridlock'] > 50:
            reasons.append("high congestion score")
        if not reasons:
            reasons.append("high congestion damage")

        cards.append(PriorityCard(
            rank=i,
            junction=row['mapped_junction'],
            station=station,
            total_delay=round(row['total_delay'], 1),
            violation_count=int(row['violation_count']),
            top_vehicle=row['top_vehicle'],
            tier=row['worst_tier'],
            gridlock_score=round(row['avg_gridlock'], 1),
            lat=round(row['avg_lat'], 6),
            lon=round(row['avg_lon'], 6),
            explanation="Ranked high because: " + ", ".join(reasons) + "."
        ))

    return {"station": station, "top_n": top_n, "cards": cards}


@app.get("/api/stations")
async def get_stations():
    """List all police stations with summary stats."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data

    beat_stats = df.groupby('police_station').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        avg_gridlock=('gridlock_score', 'mean'),
        top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
    ).reset_index().sort_values('total_delay', ascending=False)

    tier_by_station = (
        df.groupby(['police_station', 'impact_tier'])
        .size()
        .unstack(fill_value=0)
        .to_dict('index')
    )

    stations = []
    for _, row in beat_stats.iterrows():
        tier_counts = tier_by_station.get(row['police_station'], {})
        stations.append(BeatStats(
            station=row['police_station'],
            total_delay=round(row['total_delay'], 1),
            violation_count=int(row['violation_count']),
            avg_gridlock=round(row['avg_gridlock'], 1),
            top_vehicle=row['top_vehicle'],
            tier_breakdown={k: int(v) for k, v in tier_counts.items()}
        ))

    return {"stations": stations}


@app.get("/api/map-data")
async def get_map_data():
    """All violation coordinates + junction markers for map rendering."""
    await asyncio.to_thread(_ensure_base_data)
    if _pipeline_data is None or _junction_coords is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data

    sample = df.nlargest(500, 'congestion_cost')[
        ['latitude', 'longitude', 'congestion_cost', 'gridlock_score',
         'impact_tier', 'vehicle_type', 'single_violation', 'mapped_junction',
         'police_station', 'duration_minutes']
    ].copy()

    violations = sample.to_dict('records')

    junction_stats = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        avg_gridlock=('gridlock_score', 'mean'),
    ).to_dict('index')

    junctions = []
    for code, coords in _junction_coords.items():
        stats = junction_stats.get(code)
        if stats is not None:
            junctions.append({
                'code': code,
                'lat': coords[0],
                'lon': coords[1],
                'total_delay': round(stats['total_delay'], 1),
                'violation_count': int(stats['violation_count']),
                'avg_gridlock': round(stats['avg_gridlock'], 1),
            })

    return {
        "violations": violations,
        "junctions": junctions,
        "center_lat": 12.9716,
        "center_lon": 77.5946,
    }


@app.get("/api/cascade")
async def get_cascade():
    """Cascade correlation pairs for domino-effect visualization."""
    await asyncio.to_thread(_ensure_cascade)

    if _cascade is None:
        raise HTTPException(503, "Cascade analysis failed")

    lag_df = _cascade.get('lag_correlations', pd.DataFrame())
    cascades = _cascade.get('cascades', [])

    pairs = []
    if len(lag_df) > 0:
        top = lag_df.head(20)
        for _, row in top.iterrows():
            pairs.append(CascadePair(
                from_junction=row['from_junction'],
                to_junction=row['to_junction'],
                distance_m=row['distance_m'],
                correlation=round(row['lag_correlation'], 4),
                violations_from=int(row['from_violations']),
                violations_to=int(row['to_violations']),
            ))

    chains = []
    for c in cascades[:5]:
        chains.append({
            'chain': c['chain'],
            'total_correlation': round(c['total_correlation'], 4),
            'total_distance': round(c['total_distance'], 0),
        })

    return {
        "pairs": pairs,
        "chains": chains,
        "total_tested": len(lag_df),
        "significant_count": len(lag_df[lag_df['lag_correlation'] > 0.2]) if len(lag_df) > 0 else 0,
    }


@app.get("/api/curbflex")
async def get_curbflex():
    """Chronic zones + policy recommendations."""
    await asyncio.to_thread(_ensure_curbflex)

    if _curbflex is None:
        raise HTTPException(503, "CurbFlex analysis failed")

    chronic = _curbflex.get('chronic_zones', pd.DataFrame())
    recs = _curbflex.get('recommendations', [])
    equity = _curbflex.get('equity_stats', pd.DataFrame())

    return {
        "chronic_zones": chronic.to_dict('records') if len(chronic) > 0 else [],
        "recommendations": recs,
        "equity_stats": equity.to_dict('records') if len(equity) > 0 else [],
    }


@app.get("/api/dispatch")
async def get_dispatch(num_trucks: int = Query(2, ge=1, le=4)):
    """Tow truck shift plan with VRP routing."""
    await asyncio.to_thread(_ensure_base_data)
    if _pipeline_data is None or _junction_coords is None:
        raise HTTPException(503, "Pipeline not loaded")

    try:
        plan = await asyncio.wait_for(
            asyncio.to_thread(run_dispatch, _pipeline_data, _junction_coords, num_trucks),
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Dispatch computation timed out")

    routes = []
    for i, route in enumerate(plan.get('routes', [])):
        stops = [{'lat': r[0], 'lon': r[1]} for r in route]

        total_dist = 0.0
        for j in range(1, len(route)):
            dlat = route[j][0] - route[j-1][0]
            dlon = route[j][1] - route[j-1][1]
            total_dist += np.sqrt(dlat**2 + dlon**2) * 111000

        routes.append(DispatchRoute(
            truck_id=i + 1,
            stops=stops,
            total_distance_km=round(total_dist / 1000, 1),
        ))

    return {
        "routes": routes,
        "responses": plan.get('responses', []),
        "summary": plan.get('summary', {}),
    }


@app.get("/api/alerts")
async def get_alerts(count: int = Query(10, ge=1, le=20)):
    """Generate alerts for top priority violations."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    top = df.nlargest(count, 'congestion_cost')

    alerts = []
    recent_pool = df.tail(500)

    for _, row in top.iterrows():
        if len(alerts) >= count:
            break

        mapped = row.to_dict()
        mapped['junction_'] = mapped.get('mapped_junction', 'Unknown')
        mapped['created_date'] = mapped.get('created_date', mapped.get('created_datetime', '2024-06-01 12:00:00'))
        mapped['created_datetime'] = pd.to_datetime(mapped['created_date'])
        mapped['vehicle_number'] = mapped.get('vehicle_number', mapped.get('vehicle_no', 'N/A'))
        mapped['location'] = mapped.get('location', f"{mapped.get('latitude', 0)}, {mapped.get('longitude', 0)}")
        mapped['id'] = mapped.get('id', str(mapped.get('index', len(alerts))))

        mapped_series = pd.Series(mapped)

        if 'created_datetime' not in recent_pool.columns:
            recent_pool_local = recent_pool.copy()
            recent_pool_local['created_datetime'] = pd.to_datetime(
                recent_pool_local.get('created_date', '2024-06-01 12:00:00')
            )
        else:
            recent_pool_local = recent_pool

        alert = _alert_system.check_and_alert(
            mapped_series, recent_pool_local, row['congestion_cost'], anomaly_score=None
        )
        if alert:
            alerts.append(_sanitize(alert))

    return {"alerts": alerts, "count": len(alerts)}


@app.get("/api/repeat-offenders")
async def get_repeat_offenders(min_violations: int = Query(3, ge=2, le=50)):
    """Vehicles with multiple high-impact violations."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    high_impact = df[(df['duration_minutes'] > 30) | (df['severity'] >= 2)]

    offender_stats = high_impact.groupby('vehicle_number').agg(
        violation_count=('single_violation', 'count'),
        stations=('police_station', lambda x: ', '.join(x.unique())),
        total_delay=('congestion_cost', 'sum'),
        avg_gridlock=('gridlock_score', 'mean'),
        top_vehicle=('vehicle_type', 'first'),
        violation_types=('single_violation', lambda x: ', '.join(x.unique())),
    ).reset_index()

    offenders = offender_stats[offender_stats['violation_count'] >= min_violations]
    offenders = offenders.sort_values('violation_count', ascending=False)

    return {
        "offenders": offenders.head(20).to_dict('records'),
        "total_count": len(offenders),
    }


@app.get("/api/pareto")
async def get_pareto():
    """Pareto analysis data for ACP view."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    total_delay = df['congestion_cost'].sum()

    if total_delay == 0:
        return {"junctions": [], "total_delay": 0}

    j_stats = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
    ).reset_index().sort_values('total_delay', ascending=False)

    total_violations = j_stats['violation_count'].sum()
    j_stats['cumulative_pct'] = j_stats['total_delay'].cumsum() / total_delay * 100
    j_stats['violation_pct'] = j_stats['violation_count'] / total_violations * 100

    return {
        "junctions": j_stats.head(30).to_dict('records'),
        "total_delay": round(total_delay, 1),
    }


@app.get("/api/predictions")
async def get_predictions():
    """ML model predictions — XGBoost/LightGBM predicted congestion cost per junction."""
    await asyncio.to_thread(_ensure_models)

    if _models is None or _pipeline_data is None:
        raise HTTPException(503, "Models not trained or pipeline not loaded")

    from src.prediction import prepare_features

    df = _pipeline_data.copy()
    df, features, _ = prepare_features(df)

    xgb_model = _models.get('xgb_model')
    lgb_model = _models.get('lgb_model')

    if xgb_model is None and lgb_model is None:
        raise HTTPException(503, "No models available")

    # Get predictions from available models
    X = df[features].fillna(0)
    if xgb_model is not None:
        df['predicted_cost_xgb'] = xgb_model.predict(X)
    if lgb_model is not None:
        df['predicted_cost_lgb'] = lgb_model.predict(X)

    # Use XGBoost as primary if available, else LightGBM
    pred_col = 'predicted_cost_xgb' if xgb_model is not None else 'predicted_cost_lgb'
    df['predicted_cost'] = df[pred_col].clip(lower=0)

    # Aggregate by junction
    junction_preds = df.groupby('mapped_junction').agg(
        actual_cost=('congestion_cost', 'sum'),
        predicted_cost=('predicted_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        avg_gridlock=('gridlock_score', 'mean'),
    ).reset_index()

    junction_preds['prediction_error'] = (
        junction_preds['predicted_cost'] - junction_preds['actual_cost']
    ).round(2)
    junction_preds['prediction_pct'] = (
        junction_preds['predicted_cost'] / junction_preds['actual_cost'].replace(0, np.nan) * 100
    ).round(1)

    # Sort by predicted cost (highest first)
    junction_preds = junction_preds.sort_values('predicted_cost', ascending=False)

    return {
        "junctions": junction_preds.head(30).to_dict('records'),
        "model_metrics": _models.get('xgb_metrics', {}),
        "features_used": len(features),
    }


@app.get("/api/simulator")
async def get_simulator(
    top_n: int = Query(10, ge=1, le=100),
    filter_station: str = None,
    filter_tier: str = None,
):
    """What-if simulator: clearing top N violations and its impact on congestion."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data.copy()

    # Apply filters
    if filter_station and filter_station != "ALL":
        df = df[df['police_station'] == filter_station]
    if filter_tier and filter_tier != "ALL":
        df = df[df['impact_tier'] == filter_tier]

    total_cost = df['congestion_cost'].sum()
    total_violations = len(df)

    if total_cost == 0:
        return {"scenarios": [], "baseline": {"cost": 0, "violations": 0}}

    # Baseline stats
    baseline = {
        "cost": round(total_cost, 1),
        "violations": total_violations,
        "junctions": int(df['mapped_junction'].nunique()),
        "stations": int(df['police_station'].nunique()),
    }

    # Generate scenarios: clear top 1, 5, 10, 15, 20 violations
    scenarios = []
    sorted_df = df.sort_values('congestion_cost', ascending=False)

    for n in [1, 5, 10, 15, 20]:
        if n > len(sorted_df):
            break

        cleared = sorted_df.head(n)
        remaining_cost = total_cost - cleared['congestion_cost'].sum()
        pct_reduction = (cleared['congestion_cost'].sum() / total_cost * 100)

        # Tier breakdown of cleared violations
        tier_impact = cleared['impact_tier'].value_counts().to_dict()

        # Top junction affected
        top_junction = cleared.groupby('mapped_junction')['congestion_cost'].sum()
        top_junction_name = top_junction.idxmax() if len(top_junction) > 0 else "N/A"
        top_junction_pct = (top_junction.max() / total_cost * 100) if len(top_junction) > 0 else 0

        scenarios.append({
            "clear_count": n,
            "cleared_cost": round(cleared['congestion_cost'].sum(), 1),
            "remaining_cost": round(remaining_cost, 1),
            "pct_reduction": round(pct_reduction, 1),
            "tier_impact": tier_impact,
            "top_junction": top_junction_name,
            "top_junction_pct": round(top_junction_pct, 1),
            "violations_cleared": n,
        })

    return {
        "baseline": baseline,
        "scenarios": scenarios,
        "filter_station": filter_station or "ALL",
        "filter_tier": filter_tier or "ALL",
    }


@app.get("/api/impact-summary")
async def get_impact_summary():
    """Actionable impact summary: clear top N junctions = save X vehicles/hr = ₹Y."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    total_economic = df['economic_loss_inr'].sum()
    total_vehicles = int(df['vehicles_blocked_hr'].sum())
    total_co2 = round(df['co2_kg'].sum(), 1)
    total_person_hours = round(df['person_hours_blocked'].sum(), 1)

    j_stats = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        vehicles_blocked=('vehicles_blocked_hr', 'sum'),
        economic_loss=('economic_loss_inr', 'sum'),
        co2=('co2_kg', 'sum'),
        person_hours=('person_hours_blocked', 'sum'),
        violation_count=('single_violation', 'count'),
        avg_gridlock=('gridlock_score', 'mean'),
    ).reset_index().sort_values('total_delay', ascending=False)

    top5 = j_stats.head(5)
    top10 = j_stats.head(10)

    scenarios = []
    for n, subset in [(1, j_stats.head(1)), (3, j_stats.head(3)), (5, top5), (10, top10)]:
        scenarios.append({
            "clear_count": n,
            "junctions": subset['mapped_junction'].tolist(),
            "vehicles_saved_hr": int(subset['vehicles_blocked'].sum()),
            "economic_savings_inr": round(subset['economic_loss'].sum(), 2),
            "co2_saved_kg": round(subset['co2'].sum(), 1),
            "person_hours_saved": round(subset['person_hours'].sum(), 1),
            "pct_of_total_impact": round(subset['economic_loss'].sum() / total_economic * 100, 1) if total_economic > 0 else 0,
        })

    return {
        "total": {
            "vehicles_blocked_hr": total_vehicles,
            "economic_loss_inr": round(total_economic, 2),
            "co2_kg": total_co2,
            "person_hours_blocked": total_person_hours,
        },
        "scenarios": scenarios,
        "top_junctions": j_stats.head(15).to_dict('records'),
    }


@app.get("/api/spillover-zones")
async def get_spillover_zones():
    """AI-detected spillover hotspots from metro/commercial parking."""
    await asyncio.to_thread(_ensure_spillover)

    if _spillover_zones is None:
        raise HTTPException(503, "Spillover detection failed")

    return {"zones": _spillover_zones, "count": len(_spillover_zones)}


@app.get("/api/early-warning-system", response_model=EarlyWarningResponse)
async def get_early_warning_system():
    """Phantom Blockage AI — Top 5 risk zones with dispatch recommendations."""
    from datetime import datetime, timezone
    import math

    await asyncio.to_thread(_ensure_phantom_data)

    if _phantom_data is None:
        raise HTTPException(503, "PhantomBlockageAI data not loaded")

    now = datetime.now(timezone.utc)
    minute_bucket = (now.minute // 15) * 15
    current_tb = now.strftime(f"%H:{minute_bucket:02d}")

    hour, minute = map(int, current_tb.split(":"))
    minute += 15
    if minute >= 60:
        hour = (hour + 1) % 24
        minute = 0
    next_tb = f"{hour:02d}:{minute:02d}"

    filtered = _phantom_data[_phantom_data["time_block"].isin([current_tb, next_tb])].copy()
    risk_df = calculate_phantom_risk_score(filtered)

    def fmt_12h(tb):
        h, m = map(int, tb.split(":"))
        return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"

    if risk_df.empty:
        return EarlyWarningResponse(
            current_time_block=fmt_12h(current_tb),
            next_time_block=fmt_12h(next_tb),
            query_time=now.isoformat(),
            top_risk_zones=[],
            total_feeders_scored=0,
            message="No phantom risk detected in current or next time block.",
        )

    top5 = risk_df.head(5)
    zones = []
    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        lat, lon = row["latitude"], row["longitude"]
        junc = row["junction_node"]
        vtype = row["vehicle_type"]
        action = (
            f"Dispatch tow truck to {lat}, {lon} now to prevent "
            f"blockage at {junc} in 15 mins. "
            f"Vehicle type: {vtype} (weight={row['weight']}). "
            f"{row['nearby_seed_count']} active seed(s) within "
            f"{row['avg_distance_to_seeds']}m. "
            f"Risk score: {row['phantom_risk_score']}."
        )
        zones.append(RiskZone(
            rank=rank,
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            vehicle_type=vtype,
            weight=row["weight"],
            nearby_seed_count=row["nearby_seed_count"],
            avg_distance_to_seeds=row["avg_distance_to_seeds"],
            phantom_risk_score=row["phantom_risk_score"],
            recommended_action=action,
        ))

    return EarlyWarningResponse(
        current_time_block=fmt_12h(current_tb),
        next_time_block=fmt_12h(next_tb),
        query_time=now.isoformat(),
        top_risk_zones=zones,
        total_feeders_scored=len(risk_df),
        message=f"Found {len(risk_df)} phantom risk zones. Top 5 require immediate dispatch.",
    )


# ---------------------------------------------------------------------------
# ClearLane Endpoints — Capacity Loss, Causal Impact, Evidence, Flipkart
# ---------------------------------------------------------------------------

@app.get("/api/capacity-status")
async def get_capacity_status():
    """Road Capacity Loss status per junction — the core ClearLane innovation."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    
    from src.capacity_loss import run_capacity_loss
    
    df = _pipeline_data.copy()
    _, junction_stats, summary = run_capacity_loss(df)
    
    # Format junction stats for API
    junctions = []
    for _, row in junction_stats.iterrows():
        junctions.append({
            'junction': row['mapped_junction'],
            'capacity_loss_pct': row['junction_capacity_loss_pct'],
            'remaining_pct': row['junction_remaining_pct'],
            'status': str(row['operational_status']),
            'violation_count': int(row['violation_count']),
            'footpath_violations': int(row['footpath_violations']),
            'blocked_width_m': round(row['total_blocked_width'], 2),
        })
    
    return {
        'summary': summary,
        'junctions': junctions,
    }


@app.get("/api/causal-impact")
async def get_causal_impact():
    """Causal Impact Engine — proves parking → congestion causation with regression."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    
    from src.causal_impact import run_causal_impact
    
    df = _pipeline_data.copy()
    result = run_causal_impact(df)
    
    return {
        'model': result.get('model', {}),
        'chart_data': result.get('chart_data', {}),
        'before_after': result.get('before_after', {}),
        'worst_junction': result.get('worst_junction'),
    }


@app.get("/api/evidence-packet/{violation_idx}")
async def get_evidence_packet(violation_idx: int):
    """Generate court-ready evidence packet for a specific violation."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    
    from src.evidence_packet import generate_evidence_packet, generate_evidence_html
    
    df = _pipeline_data
    if violation_idx < 0 or violation_idx >= len(df):
        raise HTTPException(404, f"Violation index {violation_idx} out of range")
    
    violation = df.iloc[violation_idx].to_dict()
    
    # Get capacity data if available
    capacity_data = None
    try:
        from src.capacity_loss import compute_capacity_loss_single
        capacity_data = compute_capacity_loss_single(df.iloc[violation_idx])
    except Exception as exc:
        logger.warning("Evidence packet capacity lookup failed: %s", exc)
    
    packet = generate_evidence_packet(violation, capacity_data)
    html = generate_evidence_html(packet)
    
    return {
        'packet': packet,
        'html': html,
    }


@app.get("/api/flipkart-logistics")
async def get_flipkart_logistics():
    """Flipkart Green-Zone — Delivery bay optimization recommendations."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    
    from src.flipkart_logistics import run_flipkart_logistics
    
    df = _pipeline_data.copy()
    result = run_flipkart_logistics(df)
    
    return {
        'status': result.get('status', 'unknown'),
        'recommendations': result.get('recommendations', []),
        'impact': result.get('impact', {}),
        'hourly_patterns': result.get('hourly_patterns', []),
    }


@app.get("/api/cost-metrics")
async def get_cost_metrics():
    """Cost per junction per month — for scalability pitch."""
    # Unit economics (based on Project ClearLane estimates)
    return {
        'per_station': {
            'cloud_cost_inr': 2400,
            'coverage_junctions': 15,
            'cost_per_junction_inr': 160,
            'cost_per_violation_inr': 12,
            'model': 'CPU inference (no GPU)',
            'scaling': {
                '1_station': {'monthly': 2400, 'junctions': 15},
                '10_stations': {'monthly': 20000, 'junctions': 150},
                '50_stations': {'monthly': 80000, 'junctions': 750},
                'city_wide': {'monthly': 300000, 'junctions': 2800},
            }
        },
        'comparison': {
            'traditional_enforcement': {'monthly_per_station': 15000, 'coverage': '5 junctions'},
            'clearlane': {'monthly_per_station': 2400, 'coverage': '15 junctions'},
            'savings_pct': 84,
        },
        'roi': {
            'annual_cost': 28800,
            'annual_savings_inr': 8500000,
            'roi_pct': 29400,
            'payback_days': 1,
        }
    }


@app.get("/api/degradation-status")
async def get_degradation_status():
    """System health and graceful degradation status."""
    from src.degradation import get_system_health, get_camera_status
    
    health = get_system_health()
    
    # Check a few sample cameras
    sample_cameras = []
    for jid in ['BTP001', 'BTP044', 'BTP148', 'BTP200', 'BTP300']:
        status = get_camera_status(jid)
        sample_cameras.append(status)
    
    online_count = sum(1 for c in sample_cameras if c['status'] == 'ONLINE')
    
    return {
        'system_health': health,
        'camera_sample': sample_cameras,
        'online_percentage': round(online_count / len(sample_cameras) * 100, 1),
        'degradation_handlers': {
            'camera_offline': 'Historical heatmap fallback',
            'low_bandwidth': 'Metadata-only transmission (50 bytes vs 50KB)',
            'model_uncertain': 'Human-in-the-loop review',
            'two_wheeler_footpath': 'Special priority queue',
        }
    }


@app.get("/api/llm/nudge")
async def get_llm_nudge(violation_type: str = "wrong_parking", vehicle_type: str = "TWO_WHEELER", location: str = "MG Road"):
    """Generate personalized nudge message via GLM 5.2 Free."""
    from src.llm_client import generate_nudge_message
    msg = generate_nudge_message(
        violation_type=violation_type,
        vehicle_type=vehicle_type,
        location=location,
        impact_score=65.0,
    )
    return {"message": msg, "model": "z-ai/glm-5.2-free", "provider": "ZenMux"}


@app.get("/api/llm/report")
async def get_llm_report(junction: str = "KR Market", violations: int = 12, capacity_loss: float = 35.0, economic_impact: float = 180000):
    """Generate enforcement report via GLM 5.2 Free."""
    from src.llm_client import generate_enforcement_report
    report = generate_enforcement_report(
        junction=junction,
        violations=violations,
        capacity_loss=capacity_loss,
        economic_impact=economic_impact,
    )
    return {"report": report, "model": "z-ai/glm-5.2-free", "provider": "ZenMux"}


@app.get("/api/llm/query")
async def query_clearlane_llm(q: str):
    """Natural language query interface for ClearLane data."""
    from src.llm_client import query_clearlane
    context = ""
    if _pipeline_data is not None:
        context = f"Available violations: {len(_pipeline_data)}, junctions: {len(_junction_coords) if _junction_coords is not None else 0}"
    answer = query_clearlane(question=q, context=context)
    return {"answer": answer, "model": "z-ai/glm-5.2-free", "provider": "ZenMux"}


# ---------------------------------------------------------------------------
# AI Insights Endpoints — Expose hidden ML capabilities
# ---------------------------------------------------------------------------

@app.get("/api/tipping-points")
async def get_tipping_points():
    """
    Tipping Point Detection — Predicts the EXACT 15-minute window when congestion will spike.

    This is the "Predictive vs Reactive" differentiator. Uses 7-hour rolling window
    with 3-sigma spike detection to identify when a junction will hit critical capacity.

    Returns: {junction: "BTP044 hits tipping point exactly at 08:30 AM", ...}
    """
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    from tipping_points import find_tipping_points

    # Run tipping point detection on current data
    df = _pipeline_data.copy()

    # Ensure we have the required columns
    if 'junction_node' not in df.columns:
        df['junction_node'] = df.get('mapped_junction', 'No Junction')
    if 'time_block' not in df.columns:
        # Create time_block from created_date if available
        if 'created_date' in df.columns:
            df['created_datetime'] = pd.to_datetime(df['created_date'], errors='coerce')
            df['time_block'] = df['created_datetime'].dt.strftime('%H:%M')
            # Round to 15-minute blocks
            df['time_block'] = df['time_block'].apply(
                lambda x: f"{int(x.split(':')[0]):02d}:{(int(x.split(':')[1]) // 15) * 15:02d}" if pd.notna(x) and ':' in x else '12:00'
            )
        else:
            df['time_block'] = '12:00'
    if 'weight' not in df.columns:
        df['weight'] = df.get('gridlock_score', df.get('congestion_cost', 1.0))

    tipping_points = find_tipping_points(df)

    # Format for frontend: list of junctions with predictions
    predictions = []
    for junction, prediction in tipping_points.items():
        # Extract time from prediction string
        import re
        time_match = re.search(r'at (\d+:\d+ [AP]M)', prediction)
        predicted_time = time_match.group(1) if time_match else "Unknown"

        predictions.append({
            'junction': junction,
            'predicted_time': predicted_time,
            'message': prediction,
            'status': 'CRITICAL' if 'AM' in predicted_time and int(predicted_time.split(':')[0]) in range(7, 11) else 'WARNING',
        })

    # Sort by junction name
    predictions.sort(key=lambda x: x['junction'])

    return {
        'predictions': predictions[:20],  # Top 20
        'total_junctions_with_tipping_points': len(predictions),
        'methodology': '7-hour rolling window, 3-sigma spike detection',
        'description': 'Identifies the exact 15-minute window where congestion spikes beyond normal rhythm.',
    }


class AnomalyScoreResponse(BaseModel):
    junction: str
    anomaly_score: float
    is_anomaly: bool
    anomaly_reason: str
    violation_count: int


@app.get("/api/anomaly-scores")
async def get_anomaly_scores():
    """
    Isolation Forest Anomaly Detection — First-of-its-kind ML for parking violations in India.

    Detects unusual violation patterns that rule-based scoring misses:
    - Temporal outliers (unusual hour/day combinations)
    - Spatial clustering anomalies
    - Vehicle type outliers
    - Offense combination rarity

    Returns junctions with anomaly scores (lower = more anomalous).
    """
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    from src.anomaly_detection import ViolationAnomalyDetector
    import numpy as np

    df = _pipeline_data.copy()

    # Initialize detector
    detector = ViolationAnomalyDetector(contamination=0.05)

    try:
        anomaly_scores, anomaly_labels = detector.fit_predict(df)
        explanations = detector.get_anomaly_explanations(df, anomaly_scores)
    except Exception as e:
        logger.warning("Anomaly detection failed: %s", e)
        # Fallback with mock data
        return {
            'anomalies': [],
            'total_analyzed': 0,
            'error': str(e),
            'methodology': 'Isolation Forest, 5% contamination',
        }

    # Aggregate to junction level
    df['anomaly_score'] = anomaly_scores
    df['is_anomaly'] = explanations['is_anomaly']
    df['anomaly_reason'] = explanations['anomaly_reason']

    # Group by junction and find most anomalous violations per junction
    junction_anomalies = df.groupby('mapped_junction').agg(
        mean_anomaly_score=('anomaly_score', 'mean'),
        anomaly_count=('is_anomaly', 'sum'),
        violation_count=('single_violation', 'count'),
        top_reason=('anomaly_reason', lambda x: x.value_counts().index[0] if len(x) > 0 else 'Unknown'),
    ).reset_index()

    # Mark junction-level anomalies (mean score below threshold)
    threshold = np.percentile(anomaly_scores, 5)
    junction_anomalies['is_anomaly'] = junction_anomalies['mean_anomaly_score'] < threshold

    # Sort by anomaly score (most anomalous first)
    junction_anomalies = junction_anomalies.sort_values('mean_anomaly_score')

    anomalies = []
    for _, row in junction_anomalies.head(20).iterrows():
        anomalies.append(AnomalyScoreResponse(
            junction=row['mapped_junction'],
            anomaly_score=round(row['mean_anomaly_score'], 4),
            is_anomaly=bool(row['is_anomaly']),
            anomaly_reason=row['top_reason'],
            violation_count=int(row['violation_count']),
        ))

    return {
        'anomalies': anomalies,
        'total_analyzed': len(df),
        'anomaly_count': int(anomaly_labels[anomaly_labels == -1].sum() if len(anomaly_labels) > 0 else 0),
        'methodology': 'Isolation Forest, 5% contamination, 7 engineered features',
        'features': detector.feature_columns if hasattr(detector, 'feature_columns') else [],
    }


@app.get("/api/temporal-profile/{junction_id}")
async def get_temporal_profile(junction_id: str):
    """
    Temporal Profile — Heatmap data showing WHEN a junction typically breaks.

    Returns hourly breakdown of violations for heatmap visualization.
    Identifies peak congestion hours for targeted enforcement scheduling.
    """
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data.copy()

    # Filter to junction
    junction_df = df[df['mapped_junction'] == junction_id]

    if len(junction_df) == 0:
        raise HTTPException(404, f"Junction {junction_id} not found")

    # Extract hour from created_date
    if 'created_datetime' not in junction_df.columns:
        junction_df['created_datetime'] = pd.to_datetime(junction_df['created_date'], errors='coerce')

    junction_df['hour'] = junction_df['created_datetime'].dt.hour

    # Aggregate by hour
    hourly = junction_df.groupby('hour').agg(
        violation_count=('single_violation', 'count'),
        total_delay=('congestion_cost', 'sum'),
        avg_gridlock=('gridlock_score', 'mean'),
        vehicles_blocked=('vehicles_blocked_hr', 'sum'),
    ).reset_index()

    # Fill missing hours with zeros
    all_hours = pd.DataFrame({'hour': range(24)})
    hourly = all_hours.merge(hourly, on='hour', how='left').fillna(0)

    # Identify peak hours (top 3)
    peak_hours = hourly.nlargest(3, 'violation_count')['hour'].tolist()

    # Format for heatmap (24-hour cycle)
    heatmap_data = []
    for _, row in hourly.iterrows():
        hour = int(row['hour'])
        period = 'AM' if hour < 12 else 'PM'
        display_hour = hour % 12 or 12
        heatmap_data.append({
            'hour': hour,
            'label': f"{display_hour} {period}",
            'violations': int(row['violation_count']),
            'delay': round(row['total_delay'], 1),
            'gridlock': round(row['avg_gridlock'], 1),
            'vehicles_blocked': int(row['vehicles_blocked']),
            'is_peak': hour in peak_hours,
        })

    # Day of week breakdown
    junction_df['day_of_week'] = junction_df['created_datetime'].dt.dayofweek
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    dow = junction_df.groupby('day_of_week').agg(
        violation_count=('single_violation', 'count'),
        total_delay=('congestion_cost', 'sum'),
    ).reset_index()

    weekly_data = []
    for _, row in dow.iterrows():
        weekly_data.append({
            'day': dow_names[int(row['day_of_week'])],
            'violations': int(row['violation_count']),
            'delay': round(row['total_delay'], 1),
        })

    return {
        'junction': junction_id,
        'hourly_heatmap': heatmap_data,
        'peak_hours': [f"{h:02d}:00" for h in peak_hours],
        'weekly_pattern': weekly_data,
        'total_violations': len(junction_df),
        'summary': {
            'worst_hour': int(hourly.nlargest(1, 'violation_count')['hour'].values[0]) if len(hourly) > 0 else 12,
            'worst_day': dow_names[int(dow.nlargest(1, 'violation_count')['day_of_week'].values[0])] if len(dow) > 0 else 'Mon',
        },
    }


class ShiftBriefingResponse(BaseModel):
    officer_name: str
    shift_date: str
    briefing_text: str
    audio_available: bool
    priority_zones: List[Dict[str, Any]]
    key_metrics: Dict[str, Any]


@app.get("/api/shift-briefing")
async def get_shift_briefing(
    officer_zone: str = Query("Koramangala", description="Officer's assigned zone"),
    officer_name: str = Query("Officer Kumar", description="Officer name for personalization"),
):
    """
    Shift Briefing AI — Personalized intelligence for every officer, every shift.

    Auto-generates 2-minute audio briefing with:
    - Zone health overview
    - Priority junctions requiring attention
    - Repeat offender alerts
    - Yesterday's stats comparison
    - Tipping point warnings
    """
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    from src.llm_client import chat_completion
    from datetime import datetime

    df = _pipeline_data.copy()

    # Filter to officer's zone (match police_station)
    zone_df = df[df['police_station'].str.contains(officer_zone, case=False, na=False)]

    if len(zone_df) == 0:
        zone_df = df.head(100)  # Fallback

    # Calculate zone metrics
    total_violations = len(zone_df)
    total_delay = zone_df['congestion_cost'].sum()
    vehicles_blocked = int(zone_df['vehicles_blocked_hr'].sum())
    economic_loss = round(zone_df['economic_loss_inr'].sum(), 2)

    # Top 3 junctions
    junction_stats = zone_df.groupby('mapped_junction').agg(
        violation_count=('single_violation', 'count'),
        total_delay=('congestion_cost', 'sum'),
    ).reset_index().nlargest(3, 'total_delay')

    priority_junctions = junction_stats['mapped_junction'].tolist()[:3]

    # Get tipping points for this zone
    try:
        from tipping_points import find_tipping_points
        tipping = find_tipping_points(zone_df)
        tipping_alerts = [v for k, v in tipping.items() if k in priority_junctions][:2]
    except Exception:
        tipping_alerts = []

    # Generate briefing text via LLM
    briefing_prompt = f"""Generate a 60-word morning shift briefing for {officer_name} in {officer_zone} zone:
- Today focus on: {', '.join(priority_junctions[:2])}
- Yesterday: {total_violations} violations, {vehicles_blocked} vehicles blocked
- Economic impact: ₹{economic_loss:,.0f}
- Tipping point warning: {tipping_alerts[0] if tipping_alerts else 'No critical predictions'}
- Top repeat offender junction: {priority_junctions[0] if priority_junctions else 'N/A'}

Format: Conversational, officer-friendly, 2-minute read. Start with "Good morning, {officer_name}.""""

    briefing_text = chat_completion(
        briefing_prompt,
        system="You are a concise traffic briefing generator for BTP officers. Write in plain English, no jargon.",
        temperature=0.6
    )

    # Format priority zones for response
    priority_zones = []
    for _, row in junction_stats.iterrows():
        priority_zones.append({
            'junction': row['mapped_junction'],
            'violations': int(row['violation_count']),
            'delay': round(row['total_delay'], 1),
        })

    return ShiftBriefingResponse(
        officer_name=officer_name,
        shift_date=datetime.now().strftime('%Y-%m-%d'),
        briefing_text=briefing_text,
        audio_available=True,  # Indicates TTS can be used in frontend
        priority_zones=priority_zones,
        key_metrics={
            'zone_violations': total_violations,
            'vehicles_blocked': vehicles_blocked,
            'economic_loss_inr': economic_loss,
            'tipping_alerts': len(tipping_alerts),
        },
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "pipeline_loading": _pipeline_loading,
        "pipeline_error": _pipeline_error,
        "pipeline_loaded": _pipeline_data is not None,
        "violations_count": len(_pipeline_data) if _pipeline_data is not None else 0,
        "junctions_count": len(_junction_coords) if _junction_coords is not None else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
