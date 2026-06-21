"""
PhantomBlockageAI — FastAPI Backend
Exposes the Early Warning System endpoint for the React frontend.
"""

import os
import math
import threading
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PhantomBlockageAI",
    description="Bengaluru Traffic Police — Predict phantom blockages 15 minutes early",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARQUET_PATH = "processed_data.parquet"
EARTH_RADIUS_M = 6_371_000
FEEDER_RADIUS_M = 500

VEHICLE_WEIGHTS = {
    "TANKER": 6.0, "BUS": 6.0, "TRUCK": 4.0, "CAR": 2.0,
    "PASSENGER AUTO": 1.5, "GOODS AUTO": 1.5, "AUTO": 1.5,
    "MAXI-CAB": 2.0, "SCOOTER": 1.0, "MOTOR CYCLE": 1.0, "VAN": 3.0,
}

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_df: Optional[pd.DataFrame] = None
_df_lock = threading.Lock()


def _load_data() -> pd.DataFrame:
    global _df
    if _df is not None:
        return _df
    with _df_lock:
        if _df is not None:
            return _df
        try:
            _df = pd.read_parquet(PARQUET_PATH)
            print(f"[startup] Loaded {len(_df):,} rows from {PARQUET_PATH}")
        except FileNotFoundError:
            raise RuntimeError(
                f"{PARQUET_PATH} not found. Run 'python preprocess.py' first."
            )
        return _df


# ---------------------------------------------------------------------------
# Risk score logic — imported from phantom_risk module
# ---------------------------------------------------------------------------

from phantom_risk import haversine, calculate_phantom_risk_score


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def get_current_time_block() -> str:
    now = datetime.now(timezone.utc)
    minute_bucket = (now.minute // 15) * 15
    return now.strftime(f"%H:{minute_bucket:02d}")


def get_next_time_block(current: str) -> str:
    hour, minute = map(int, current.split(":"))
    minute += 15
    if minute >= 60:
        hour = (hour + 1) % 24
        minute = 0
    return f"{hour:02d}:{minute:02d}"


def format_12h(time_block: str) -> str:
    hour, minute = map(int, time_block.split(":"))
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {period}"


# ---------------------------------------------------------------------------
# Risk score wrapper for API (filters by time blocks)
# ---------------------------------------------------------------------------

def compute_risk_scores(
    df: pd.DataFrame, time_blocks: List[str]
) -> pd.DataFrame:
    """Filter to given time blocks, then apply phantom risk score logic."""
    filtered = df[df["time_block"].isin(time_blocks)].copy()
    return calculate_phantom_risk_score(filtered)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

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
# Endpoint
# ---------------------------------------------------------------------------

@app.get("/api/early-warning-system", response_model=EarlyWarningResponse)
async def early_warning_system():
    """
    Early Warning System — Top 5 Phantom Risk Zones.

    Filters for the current and next 15-minute blocks, computes phantom
    risk scores for all Feeder Nodes near active Seeds, and returns the
    top 5 with actionable dispatch recommendations.
    """
    df = _load_data()

    current_tb = get_current_time_block()
    next_tb = get_next_time_block(current_tb)

    risk_df = compute_risk_scores(df, [current_tb, next_tb])

    if risk_df.empty:
        return EarlyWarningResponse(
            current_time_block=format_12h(current_tb),
            next_time_block=format_12h(next_tb),
            query_time=datetime.now(timezone.utc).isoformat(),
            top_risk_zones=[],
            total_feeders_scored=0,
            message="No phantom risk detected in current or next time block.",
        )

    top5 = risk_df.head(5)
    zones: List[RiskZone] = []

    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        lat, lon = row["latitude"], row["longitude"]
        junc = row["junction_node"]
        vtype = row["vehicle_type"]
        target_tb = format_12h(row["time_block"])

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
            latitude=lat,
            longitude=lon,
            vehicle_type=vtype,
            weight=row["weight"],
            nearby_seed_count=row["nearby_seed_count"],
            avg_distance_to_seeds=row["avg_distance_to_seeds"],
            phantom_risk_score=row["phantom_risk_score"],
            recommended_action=action,
        ))

    return EarlyWarningResponse(
        current_time_block=format_12h(current_tb),
        next_time_block=format_12h(next_tb),
        query_time=datetime.now(timezone.utc).isoformat(),
        top_risk_zones=zones,
        total_feeders_scored=len(risk_df),
        message=(
            f"Found {len(risk_df)} phantom risk zones. "
            f"Top 5 require immediate dispatch."
        ),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "parquet_loaded": _df is not None,
        "rows": len(_df) if _df is not None else 0,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
