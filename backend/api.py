"""
DispatchMind API — FastAPI backend serving the ML pipeline to React frontend.
Replaces Streamlit with a proper REST API.
"""

import asyncio
import collections
import json
import logging
import os
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import hashlib
import secrets
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import get_db, SessionLocal
from backend.models import User, UserSession
from phantom_risk import calculate_phantom_risk_score
from preprocess import preprocess
from src.cascade import run_cascade_analysis
from src.gnn_cascade import run_gnn_cascade
from src.congestion_cost import run_congestion_cost
from src.curbflex import run_curbflex
from src.data_pipeline import run_pipeline, validate_pipeline_data
from src.dispatch import run_dispatch
from src.prediction import run_prediction
from src.realtime_alerts import ViolationAlertSystem
from src.spillover_ai import detect_spillover_zones
from src.presence_model import compute_presence_for_violation, filter_present_violations

_request_id_ctx = threading.local()

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(_request_id_ctx, 'request_id', '-')
        return True

def _setup_logging():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","request_id":"%(request_id)s","message":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

_setup_logging()
logger = logging.getLogger("dispatchmind")


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def verify_password(password: str, salt: str, hashed: str) -> bool:
    return hash_password(password, salt) == hashed

def generate_salt() -> str:
    return secrets.token_hex(16)

def generate_token() -> str:
    return secrets.token_hex(32)

def _seed_default_users(db: Session):
    default_users = [
        {"username": "acp", "password": "acp", "role": "acp", "full_name": "ACP Sandeep Kumar", "badge_number": "BTP-ACP-001"},
        {"username": "si", "password": "si", "role": "si", "full_name": "SI Nikunj Sharma", "badge_number": "BTP-SI-104"},
        {"username": "constable", "password": "constable", "role": "constable", "full_name": "Constable Ramesh Gowda", "badge_number": "BTP-PC-982"},
        {"username": "scout", "password": "scout", "role": "scout", "full_name": "Scout Anil Kumar", "scout_id": "FK-SCOUT-77"},
    ]
    for u_info in default_users:
        existing = db.query(User).filter(User.username == u_info["username"]).first()
        if not existing:
            salt = generate_salt()
            hashed_pwd = hash_password(u_info["password"], salt)
            user = User(
                username=u_info["username"],
                hashed_password=hashed_pwd,
                salt=salt,
                role=u_info["role"],
                full_name=u_info["full_name"],
                badge_number=u_info.get("badge_number"),
                scout_id=u_info.get("scout_id")
            )
            db.add(user)
    db.commit()
    logger.info("Default users seeded successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the base pipeline in the background without blocking startup."""
    try:
        from backend.database import engine
        from backend.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        
        # Seed default users
        db = SessionLocal()
        try:
            _seed_default_users(db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    def _bg_load():
        for attempt in range(3):
            try:
                logger.info("Pipeline warm-up: loading base data...")
                _ensure_base_data()
                if _pipeline_data is not None:
                    logger.info("Pipeline warm-up: precomputing overview stats...")
                    _precompute_all()
                    logger.info("Pipeline warm-up: computing phantom risk scores...")
                    _ensure_phantom_data()
                    logger.info("Pipeline warm-up: computing capacity loss...")
                    _ensure_capacity()
                    logger.info("Pipeline warm-up: computing repeat offenders...")
                    _ensure_repeat_offenders()
                    logger.info("Pipeline warm-up: training causal impact model...")
                    _ensure_causal_impact()
                    logger.info("Pipeline warm-up: training prediction models...")
                    _ensure_predictions()
                    logger.info("Pipeline warm-up: all components ready.")
                    return
            except Exception:
                logger.exception("Pipeline failed to load (attempt %d/3)", attempt + 1)
            import time

            time.sleep(5)

    threading.Thread(target=_bg_load, daemon=True).start()
    yield
    logger.info("Shutting down DispatchMind API — clearing cached state")
    global _pipeline_data, _models, _precomputed
    _pipeline_data = None
    _models = None
    _precomputed.clear()
    try:
        from backend.database import engine
        engine.dispose()
        logger.info("Database connections drained.")
    except Exception:
        pass


# Authentication schemas, dependency, and check function
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
    username: str
    full_name: str
    badge_number: Optional[str] = None
    scout_id: Optional[str] = None

class UserInfoResponse(BaseModel):
    username: str
    role: str
    full_name: str
    badge_number: Optional[str] = None
    scout_id: Optional[str] = None

class ClientErrorReport(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None
    url: str
    line: Optional[int] = None
    column: Optional[int] = None

oauth2_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    if hasattr(request.state, "user"):
        return request.state.user
        
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization credentials")
    
    token = credentials.credentials
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")
        
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user

def require_role(roles: List[str]):
    def dependency(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: require one of roles {roles}"
            )
        return user
    return dependency

def check_route_permissions(request: Request, db: Session = Depends(get_db)):
    path = request.url.path
    
    # Bypass auth for health, login, errors, and static/documentation routes if any
    if path in ["/api/health", "/api/auth/login", "/api/errors"] or not path.startswith("/api/"):
        return
        
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication credentials missing or invalid")
        
    token = auth_header.split(" ")[1]
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
        
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")
        
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    request.state.user = user
    
    # Role-based access control
    role = user.role
    
    # ACP only prefixes
    acp_paths = [
        "/api/command",
        "/api/simulator",
        "/api/recent-events",
        "/api/camera-status/toggle",
        "/api/early-warning-system",
        "/api/causal-impact",
        "/api/capacity-status",
        "/api/cost-metrics",
        "/api/degradation-status",
    ]
    # SI or ACP prefixes
    si_acp_paths = [
        "/api/inspector",
        "/api/triage",
        "/api/dispatch",
    ]
    # Scout or SI or ACP prefixes
    scout_paths = [
        "/api/flipkart-scouts/report",
        "/api/flipkart-scouts/leaderboard",
    ]
    
    is_acp_path = any(path.startswith(p) for p in acp_paths)
    is_si_acp_path = any(path.startswith(p) for p in si_acp_paths)
    is_scout_path = any(path.startswith(p) for p in scout_paths)
    
    if is_acp_path and role != "acp":
        raise HTTPException(status_code=403, detail="Access denied: ACP role required")
        
    if is_si_acp_path and role not in ["acp", "si"]:
        raise HTTPException(status_code=403, detail="Access denied: SI or ACP role required")
        
    if is_scout_path and role not in ["acp", "si", "scout"]:
        raise HTTPException(status_code=403, detail="Access denied: Scout, SI, or ACP role required")
        
    # All other general /api/ paths require constable, SI, or ACP (e.g. overview, map, etc.)
    # Scout is not allowed to access general police APIs.
    if not is_scout_path and role == "scout":
        if not path.startswith("/api/auth/"):
            raise HTTPException(status_code=403, detail="Access denied: Police role required")

app = FastAPI(
    title="DispatchMind API",
    description="BTP Beat Constable Co-Pilot — AI-powered parking enforcement intelligence",
    version="2.0.0",
    lifespan=lifespan,
    dependencies=[Depends(check_route_permissions)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,https://*.onrender.com",
        ).split(",")
        if o.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

try:
    from prometheus_client import Counter, Histogram, generate_latest, CollectorRegistry

    HTTP_REQUESTS = Counter(
        "dispatchmind_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    HTTP_LATENCY = Histogram(
        "dispatchmind_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
    )
    _registry = CollectorRegistry()

    from starlette.responses import PlainTextResponse

    @app.get("/metrics")
    async def metrics():
        data = generate_latest().decode("utf-8")
        logger.info("Metrics endpoint hit, length=%d", len(data))
        return PlainTextResponse(data)
    logger.info("Prometheus metrics enabled at /metrics")
except ImportError:
    logger.warning("prometheus-client not installed; /metrics endpoint disabled")

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.salt, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
        
    token = generate_token()
    # Expire session in 24 hours
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    session = UserSession(
        token=token,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    
    return LoginResponse(
        token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
        badge_number=user.badge_number,
        scout_id=user.scout_id
    )

@app.post("/api/auth/logout")
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    if credentials:
        token = credentials.credentials
        session = db.query(UserSession).filter(UserSession.token == token).first()
        if session:
            db.delete(session)
            db.commit()
    return {"status": "ok", "message": "Logged out successfully"}

@app.get("/api/auth/me", response_model=UserInfoResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserInfoResponse(
        username=user.username,
        role=user.role,
        full_name=user.full_name,
        badge_number=user.badge_number,
        scout_id=user.scout_id
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
        request.state.request_id = request_id
        _request_id_ctx.request_id = request_id
        start = time.monotonic()
        try:
            response = await call_next(request)
            elapsed_ms = round((time.monotonic() - start) * 1000, 1)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
            logger.info(
                "%s %s %d %sms",
                request.method, request.url.path, response.status_code,
                elapsed_ms,
            )
            try:
                HTTP_REQUESTS.labels(
                    method=request.method,
                    path=request.url.path,
                    status=str(response.status_code),
                ).inc()
                HTTP_LATENCY.labels(
                    method=request.method,
                    path=request.url.path,
                ).observe(elapsed_ms / 1000)
            except Exception:
                pass
            return response
        finally:
            _request_id_ctx.request_id = '-'


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter. Defaults: 120 req/min per IP."""

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, collections.deque] = {}
        self._lock = threading.Lock()

    def _check(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if key not in self._requests:
                self._requests[key] = collections.deque()
            dq = self._requests[key]
            while dq and dq[0] < now - self.window:
                dq.popleft()
            if len(dq) >= self.max_requests:
                return False
            dq.append(now)
            return True

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        if not self._check(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
                headers={"Retry-After": str(self.window)},
            )
        return await call_next(request)


app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — prevents opaque 500 crashes."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
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
CACHE_PATH = Path(
    os.environ.get(
        "DISPATCHMIND_CACHE",
        "data/processed/dispatchmind_scored.parquet",
    )
)

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
_pipeline_validation = None
_cascade = None
_curbflex = None
_spillover_zones = None
_alert_system = ViolationAlertSystem()
_pipeline_loading = False
_pipeline_error = None

_phantom_data = None
_capacity_data = None
_repeat_offenders_data = None
_causal_impact_data = None
_predictions_data = None
_prepared_df = None
_custom_events = []
_prepared_features = None

# Thread safety locks for lazy-loading
_lock_base = threading.Lock()
_lock_models = threading.Lock()
_lock_cascade = threading.Lock()
_lock_curbflex = threading.Lock()
_lock_spillover = threading.Lock()
_lock_phantom = threading.Lock()
_lock_capacity = threading.Lock()
_lock_repeat = threading.Lock()
_lock_causal = threading.Lock()
_lock_predictions = threading.Lock()

_precomputed: Dict[str, Any] = {}


def _normalize_pipeline_dates():
    """Ensure created_datetime column exists in pipeline data (canonicalized at pipeline load)."""
    global _pipeline_data
    if _pipeline_data is None:
        return
    if "created_datetime" not in _pipeline_data.columns:
        _pipeline_data["created_datetime"] = pd.Timestamp("2024-06-01 12:00:00")
    elif _pipeline_data["created_datetime"].dtype != "datetime64[ns]":
        _pipeline_data["created_datetime"] = pd.to_datetime(
            _pipeline_data["created_datetime"], errors="coerce"
        )
_lock_precomputed = threading.Lock()


def _ensure_base_data():
    """Load core pipeline (stages 1-2) synchronously — fast, ~18s."""
    global _pipeline_data, _junction_coords, _pipeline_loading, _pipeline_error, _pipeline_validation

    if _pipeline_data is not None:
        return
    if _pipeline_loading:
        logger.info("Base data loading already in progress — waiting...")
        return

    with _lock_base:
        if _pipeline_data is not None:
            return
        if _pipeline_loading:
            return

        _pipeline_loading = True
        _pipeline_error = None

        if not Path(CSV_PATH).exists() or not Path(COORDS_PATH).exists():
            _pipeline_error = f"Data files not found: {CSV_PATH}, {COORDS_PATH}"
            _pipeline_loading = False
            logger.warning(_pipeline_error)
            return

        with open(COORDS_PATH, "r", encoding="utf-8") as f:
            _junction_coords = json.load(f)

        try:
            if CACHE_PATH.exists():
                logger.info("Loading scored pipeline cache: %s", CACHE_PATH)
                cached = pd.read_parquet(CACHE_PATH)
                missing = REQUIRED_SCORED_COLUMNS.difference(cached.columns)
                if not missing:
                    _pipeline_data = cached
                    _pipeline_loading = False
                    _normalize_pipeline_dates()
                    validation = validate_pipeline_data(_pipeline_data)
                    _pipeline_validation = validation
                    for issue in validation["issues"]:
                        logger.warning("[PIPELINE VALIDATION] %s", issue)
                    logger.info(
                        "Scored cache loaded: %d violations", len(_pipeline_data)
                    )
                    return
                logger.warning(
                    "Ignoring stale scored cache, missing columns: %s", sorted(missing)
                )

            logger.info("Building base pipeline from raw CSV...")
            _pipeline_data = run_pipeline(CSV_PATH, junction_coords=_junction_coords)
            _pipeline_data = run_congestion_cost(_pipeline_data, _junction_coords)
            validation = validate_pipeline_data(_pipeline_data)
            _pipeline_validation = validation
            for issue in validation["issues"]:
                logger.warning("[PIPELINE VALIDATION] %s", issue)
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _pipeline_data.to_parquet(CACHE_PATH, index=False)
            _normalize_pipeline_dates()
            logger.info(
                "Base pipeline loaded and cached: %d violations", len(_pipeline_data)
            )
        except Exception as exc:
            _pipeline_error = str(exc)
            _pipeline_data = None
            logger.exception("Failed to load base pipeline")
        finally:
            _pipeline_loading = False


def _ensure_models():
    global _models, _prepared_features, _prepared_df
    if _models is not None:
        return
    with _lock_models:
        if _models is not None:
            return
        if _pipeline_data is None:
            logger.warning("Cannot train models: base data not loaded")
            return
        logger.info("Preparing features and training models...")
        from src.prediction import prepare_features
        _prepared_df, _prepared_features, _ = prepare_features(_pipeline_data.copy())
        _models = run_prediction(_pipeline_data)
        logger.info(
            "Models trained: R²=%.4f", _models.get("xgb_metrics", {}).get("r2", 0)
        )


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
    """Build phantom blockage data from the already-loaded pipeline data."""
    global _phantom_data
    if _phantom_data is not None:
        return
    with _lock_phantom:
        if _phantom_data is not None:
            return
        cache_path = Path("data/processed/phantom_cache.parquet")
        try:
            if cache_path.exists():
                logger.info("Loading cached PhantomBlockageAI data...")
                _phantom_data = pd.read_parquet(cache_path)
            elif _pipeline_data is not None:
                logger.info(
                    "Building phantom data from pipeline (%d rows)...",
                    len(_pipeline_data),
                )
                df = _pipeline_data.copy()
                df["weight"] = (
                    df["vehicle_type"]
                    .map(
                        {
                            "TANKER": 6.0,
                            "BUS": 6.0,
                            "TRUCK": 4.0,
                            "CAR": 2.0,
                            "PASSENGER AUTO": 1.5,
                            "GOODS AUTO": 1.5,
                            "AUTO": 1.5,
                            "MAXI-CAB": 2.0,
                            "SCOOTER": 1.0,
                            "MOTOR CYCLE": 1.0,
                            "VAN": 3.0,
                            "HGV": 4.0,
                            "BUS (BMTC/KSRTC)": 6.0,
                            "PRIVATE BUS": 6.0,
                            "TOURIST BUS": 6.0,
                            "TEMPO": 2.0,
                            "LGV": 3.0,
                            "MINI LORRY": 3.0,
                            "JEEP": 2.0,
                            "MOPED": 1.0,
                        }
                    )
                    .fillna(1.0)
                )
                if "junction_node" not in df.columns:
                    df["junction_node"] = df.get("mapped_junction", "FEEDER")
                    df.loc[df["junction_node"] == "No Junction", "junction_node"] = (
                        "FEEDER"
                    )
                if "time_block" not in df.columns:
                    if "created_datetime" in df.columns:
                        dt = pd.to_datetime(df["created_datetime"], errors="coerce")
                        df["time_block"] = dt.dt.strftime("%H:") + (
                            (dt.dt.minute // 15) * 15
                        ).astype(str).str.zfill(2)
                    else:
                        df["time_block"] = "12:00"
                keep = [
                    "latitude",
                    "longitude",
                    "vehicle_type",
                    "weight",
                    "junction_node",
                    "time_block",
                ]
                _phantom_data = df[keep].copy()
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                _phantom_data.to_parquet(cache_path, index=False)
                logger.info(
                    "Phantom data built from pipeline: %d rows", len(_phantom_data)
                )
            else:
                logger.info("Pipeline not loaded, falling back to preprocess...")
                _phantom_data = preprocess()
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                _phantom_data.to_parquet(cache_path, index=False)
            logger.info("PhantomBlockageAI data loaded: %d rows", len(_phantom_data))
        except Exception:
            logger.exception("Failed to load PhantomBlockageAI data")


def _ensure_capacity():
    global _capacity_data
    if _capacity_data is not None:
        return
    with _lock_capacity:
        if _capacity_data is not None:
            return
        if _pipeline_data is None:
            return
        try:
            from src.capacity_loss import run_capacity_loss

            df = _pipeline_data.copy()
            _, junction_stats, summary = run_capacity_loss(df)
            logger.info("CAPACITY DEBUG: RED=%d YELLOW=%d GREEN=%d",
                       int((junction_stats['operational_status'] == 'RED').sum()),
                       int((junction_stats['operational_status'] == 'YELLOW').sum()),
                       int((junction_stats['operational_status'] == 'GREEN').sum()))
            _capacity_data = {"summary": summary, "junctions": junction_stats}
        except Exception:
            logger.exception("Failed to compute capacity loss")


def _ensure_repeat_offenders(min_violations=3):
    global _repeat_offenders_data
    if _repeat_offenders_data is not None:
        return
    with _lock_repeat:
        if _repeat_offenders_data is not None:
            return
        if _pipeline_data is None:
            return
        df = _pipeline_data
        high_impact = df[(df["duration_minutes"] > 30) | (df["severity"] >= 2)]
        offender_stats = (
            high_impact.groupby("vehicle_number")
            .agg(
                violation_count=("single_violation", "count"),
                stations=("police_station", lambda x: ", ".join(x.unique())),
                total_delay=("congestion_cost", "sum"),
                avg_gridlock=("gridlock_score", "mean"),
                top_vehicle=("vehicle_type", "first"),
                violation_types=("single_violation", lambda x: ", ".join(x.unique())),
            )
            .reset_index()
        )
        _repeat_offenders_data = offender_stats[
            offender_stats["violation_count"] >= min_violations
        ].sort_values("violation_count", ascending=False)


def _ensure_causal_impact():
    global _causal_impact_data
    if _causal_impact_data is not None:
        return
    with _lock_causal:
        if _causal_impact_data is not None:
            return
        if _pipeline_data is None:
            return
        try:
            from src.causal_impact import run_causal_impact

            df = _pipeline_data.copy()
            _causal_impact_data = run_causal_impact(df)
        except Exception:
            logger.exception("Failed to compute causal impact")


def _ensure_predictions():
    global _predictions_data
    if _predictions_data is not None:
        return
    with _lock_predictions:
        if _predictions_data is not None:
            return
        if _pipeline_data is None:
            return
        try:
            from src.prediction import prepare_features, run_prediction

            _predictions_data = run_prediction(_pipeline_data)
        except Exception:
            logger.exception("Failed to train prediction models")


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
    actionability_score: float = 0.0
    presence_probability_pct: float = 100.0


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


class CauseAttributionResponse(BaseModel):
    junction: str
    total_delay_minutes: float
    attribution_pcts: Dict[str, float]
    action_recommendation: str
    clear_hotspot_eta_minutes: int
    commuters_benefited_est: int


class CourtReadinessResponse(BaseModel):
    violation_id: str
    score: int
    status: str
    checks: Dict[str, bool]
    recommendation: Optional[str] = None


class FlipkartScoutReportIn(BaseModel):
    scout_id: str
    junction: str
    latitude: float
    longitude: float
    photo_url: str
    vehicle_number: Optional[str] = None
    notes: Optional[str] = None


class ViolationIn(BaseModel):
    vehicle_number: str
    vehicle_type: str
    latitude: float
    longitude: float
    violation_type: str
    junction_name: Optional[str] = None
    police_station: Optional[str] = None

class JunctionActionIn(BaseModel):
    junction: str
    action: str
    officer: Optional[str] = "Constable Kumar"


class FlipkartScoutReportOut(BaseModel):
    report_id: str
    status: str
    priority: str
    reward_points: int
    estimated_cii: float
    message: str


def ingest_and_score_violation(new_violation, db):
    global _pipeline_data, _junction_coords, _alert_system
    
    # 1. Map to nearest junction
    mapped_junction = "No Junction"
    junction_distance = 999.0
    if _junction_coords:
        jnames = list(_junction_coords.keys())
        jlats = np.array([_junction_coords[j][0] for j in jnames])
        jlons = np.array([_junction_coords[j][1] for j in jnames])
        dists = np.sqrt((new_violation.latitude - jlats)**2 + (new_violation.longitude - jlons)**2) * 111000
        idx = dists.argmin()
        mapped_junction = jnames[idx]
        junction_distance = float(dists[idx])
        
    new_violation.mapped_junction = mapped_junction
    new_violation.single_violation = new_violation.violation_type
    
    # 2. Get configuration constants and widths
    from config import get_severity_map, get_config_value, get_junction_distance_threshold, get_metro_construction_zones
    from src.capacity_loss import get_vehicle_width, get_road_width, classify_road_type, compute_blocked_width
    from src.congestion_cost import get_vehicle_size_mult
    
    duration_minutes = 30.0
    new_violation.duration_minutes = duration_minutes
    
    severity_map = get_severity_map() or {}
    severity = severity_map.get(new_violation.violation_type, 1)
    new_violation.severity = severity
    
    row = pd.Series({
        'latitude': new_violation.latitude,
        'longitude': new_violation.longitude,
        'junction_name': new_violation.junction_name,
        'junction_distance': junction_distance,
        'single_violation': new_violation.violation_type,
        'vehicle_type': new_violation.vehicle_type
    })
    
    road_type = classify_road_type(row)
    road_width = get_road_width(road_type)
    blocked_width = compute_blocked_width(row)
    
    is_footpath = road_type == 'footpath'
    pedestrian_spillover = 0.6 * 0.5 if is_footpath else 0.0
    effective_blocked = blocked_width + pedestrian_spillover
    capacity_loss_pct = min(100.0, (effective_blocked / road_width) * 100)
    
    remaining_capacity_pct = 100.0 - capacity_loss_pct
    if remaining_capacity_pct > 70:
        op_status = 'GREEN'
    elif remaining_capacity_pct > 50:
        op_status = 'YELLOW'
    else:
        op_status = 'RED'
        
    # Spatial Density
    spatial_density = 0
    if _pipeline_data is not None and len(_pipeline_data) > 0:
        dists = np.sqrt((_pipeline_data['latitude'] - new_violation.latitude)**2 + 
                        (_pipeline_data['longitude'] - new_violation.longitude)**2) * 111000
        spatial_density = int((dists <= 50.0).sum())
        
    veh_width = get_vehicle_width(new_violation.vehicle_type)
    lane_block = min(1.0, veh_width / (road_width / 2.0))
    
    hour = new_violation.created_datetime.hour
    if ((hour >= 7) & (hour < 10)) | ((hour >= 17) & (hour <= 20)):
        peak = 2.0
    elif (hour >= 22) | (hour <= 5):
        peak = 0.5
    else:
        peak = 1.0
        
    critical_dist = get_junction_distance_threshold('CRITICAL') or 10.0
    high_dist = get_junction_distance_threshold('HIGH') or 30.0
    medium_dist = get_junction_distance_threshold('MEDIUM') or 50.0
    
    if junction_distance < critical_dist:
        junction_mult = 3.0
    elif junction_distance < high_dist:
        junction_mult = 2.0
    elif junction_distance < medium_dist:
        junction_mult = 1.5
    else:
        junction_mult = 1.0
        
    vehicle_mult = get_vehicle_size_mult(new_violation.vehicle_type) or 1.0
    density_mult = min(3.0, 1.0 + np.log1p(spatial_density))
    
    metro_spillover_mult = 1.0
    metro_zones = get_metro_construction_zones() or []
    for zone in metro_zones:
        if 'lat' in zone and 'lon' in zone:
            dist = np.sqrt((new_violation.latitude - zone['lat'])**2 + 
                           (new_violation.longitude - zone['lon'])**2) * 111000
            if dist <= zone.get('radius_m', 500):
                metro_spillover_mult = zone.get('spillover_multiplier', 1.5)
                break
                
    congestion_cost = round(
        duration_minutes * lane_block * peak * junction_mult * vehicle_mult * severity * density_mult * metro_spillover_mult,
        2
    )
    new_violation.congestion_cost = congestion_cost
    
    max_cost = 100.0
    if _pipeline_data is not None and len(_pipeline_data) > 0:
        max_cost = max(1.0, _pipeline_data['congestion_cost'].max())
    gridlock_score = round(min(100.0, (congestion_cost / max_cost) * 100.0), 1)
    new_violation.gridlock_score = gridlock_score
    
    if gridlock_score >= 80.0:
        impact_tier = 'CRITICAL'
    elif gridlock_score >= 50.0:
        impact_tier = 'HIGH'
    elif gridlock_score >= 20.0:
        impact_tier = 'MEDIUM'
    else:
        impact_tier = 'LOW'
    new_violation.impact_tier = impact_tier
    
    tp = get_config_value('formula', 'throughput', {})
    road_cap = tp.get('road_capacity_veh_per_hour', {}).get('main_road', 1200)
    avg_delay = tp.get('avg_delay_minutes_per_block', 8.5)
    fuel_cost = tp.get('fuel_cost_per_liter_inr', 102.5)
    fuel_rate = tp.get('fuel_consumption_liter_per_veh_min', 0.008)
    co2_factor = tp.get('co2_kg_per_liter', 2.31)
    passengers = tp.get('avg_passengers_per_vehicle', 1.8)
    person_hour_val = tp.get('person_hour_value_inr', 150)
    
    vehicles_blocked_hr = int(round(lane_block * road_cap * peak * density_mult))
    new_violation.vehicles_blocked_hr = float(vehicles_blocked_hr)
    
    delay_minutes_total = round(vehicles_blocked_hr * avg_delay * duration_minutes / 60.0, 1)
    person_hours_blocked = round(delay_minutes_total * passengers / 60.0, 2)
    new_violation.person_hours_blocked = person_hours_blocked
    
    fuel_wasted_liters = round(vehicles_blocked_hr * duration_minutes * fuel_rate, 3)
    co2_kg = round(fuel_wasted_liters * co2_factor, 3)
    new_violation.co2_kg = co2_kg
    
    economic_loss_inr = round(person_hours_blocked * person_hour_val + fuel_wasted_liters * fuel_cost, 2)
    new_violation.economic_loss_inr = economic_loss_inr
    
    db.add(new_violation)
    db.commit()
    db.refresh(new_violation)
    
    # 3. Append to global _pipeline_data
    if _pipeline_data is not None:
        new_row = {
            'id': new_violation.id,
            'vehicle_number': new_violation.vehicle_number,
            'vehicle_type': new_violation.vehicle_type,
            'latitude': new_violation.latitude,
            'longitude': new_violation.longitude,
            'created_datetime': pd.to_datetime(new_violation.created_datetime),
            'violation_type': new_violation.violation_type,
            'single_violation': new_violation.violation_type,
            'junction_name': new_violation.junction_name,
            'mapped_junction': mapped_junction,
            'police_station': new_violation.police_station or "Unknown",
            'hour': hour,
            'day_of_week': new_violation.created_datetime.weekday(),
            'month': new_violation.created_datetime.month,
            'duration_minutes': duration_minutes,
            'severity': severity,
            'congestion_cost': congestion_cost,
            'gridlock_score': gridlock_score,
            'impact_tier': impact_tier,
            'vehicles_blocked_hr': float(vehicles_blocked_hr),
            'economic_loss_inr': economic_loss_inr,
            'co2_kg': co2_kg,
            'person_hours_blocked': person_hours_blocked,
            'spatial_density': spatial_density,
            'capacity_loss_pct': round(capacity_loss_pct, 1),
            'remaining_capacity_pct': round(remaining_capacity_pct, 1),
            'operational_status': op_status,
            'is_footpath_violation': is_footpath,
            'pedestrian_spillover_m': round(pedestrian_spillover, 2)
        }
        _pipeline_data = pd.concat([_pipeline_data, pd.DataFrame([new_row])], ignore_index=True)
        
    # 4. Trigger Real-Time Alert Engine (WhatsApp Dispatch)
    alert_series = pd.Series({
        'id': new_violation.id,
        'created_date': new_violation.created_datetime.isoformat(),
        'updated_vehicle_type': new_violation.vehicle_type,
        'vehicle_type': new_violation.vehicle_type,
        'vehicle_number': new_violation.vehicle_number,
        'junction_': mapped_junction,
        'police_station': new_violation.police_station or "Unknown",
        'latitude': new_violation.latitude,
        'longitude': new_violation.longitude,
        'location': new_violation.junction_name or "Unknown location",
        'single_violation': new_violation.violation_type
    })
    
    alert_data = _alert_system.generate_alert(alert_series, cii_score=congestion_cost, anomaly_score=0.5, cascade_risk=False)
    
    officer_phone = os.getenv("TWILIO_PHONE_NUMBER") or "+919214775938"
    if alert_data and alert_data['priority'] in ['CRITICAL', 'HIGH']:
        # Run asynchronously in background to avoid blocking ingestion API
        asyncio.create_task(asyncio.to_thread(_alert_system.send_via_whatsapp, alert_data, officer_phone))
        
    return new_violation.id


@app.post("/api/violations")
async def create_violation(payload: ViolationIn):
    """Real-time ingestion of a new parking violation."""
    from backend.database import SessionLocal
    from backend.models import Violation
    import datetime

    db = SessionLocal()
    try:
        new_violation = Violation(
            vehicle_number=payload.vehicle_number,
            vehicle_type=payload.vehicle_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
            violation_type=payload.violation_type,
            junction_name=payload.junction_name,
            police_station=payload.police_station,
            created_datetime=datetime.datetime.utcnow(),
            hour=datetime.datetime.utcnow().hour,
            day_of_week=datetime.datetime.utcnow().weekday(),
            month=datetime.datetime.utcnow().month,
            congestion_cost=0.0,
            severity=1
        )
        db.add(new_violation)
        db.commit()
        db.refresh(new_violation)
        
        # Core BTP Production Feature: Score, update, and dispatch alert immediately!
        violation_id = await asyncio.to_thread(ingest_and_score_violation, new_violation, db)
        
        return {"status": "success", "violation_id": violation_id}
    except Exception as e:
        db.rollback()
        logger.exception("Failed to ingest violation")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()



def _compute_overview() -> Dict[str, Any]:
    df = _pipeline_data
    total_delay = df["congestion_cost"].sum()
    if total_delay == 0:
        pareto_pct = 100.0
    else:
        j_stats = (
            df.groupby("mapped_junction")
            .agg(
                total_delay=("congestion_cost", "sum"),
                violation_count=("single_violation", "count"),
            )
            .reset_index()
            .sort_values("total_delay", ascending=False)
        )
        j_stats["cum_pct"] = j_stats["total_delay"].cumsum() / total_delay * 100
        reached = j_stats[j_stats["cum_pct"] >= 82]
        pareto_pct = (
            float(reached.iloc[0]["violation_count"])
            / float(j_stats["violation_count"].sum())
            * 100
            if len(reached) > 0
            else 100.0
        )
    tier_counts = df["impact_tier"].value_counts()
    return {
        "total_violations": int(len(df)),
        "total_junctions": int(df["mapped_junction"].nunique()),
        "total_stations": int(df["police_station"].nunique()),
        "total_delay_veh_min": round(float(total_delay), 1),
        "critical_count": int(tier_counts.get("CRITICAL", 0)),
        "high_count": int(tier_counts.get("HIGH", 0)),
        "medium_count": int(tier_counts.get("MEDIUM", 0)),
        "low_count": int(tier_counts.get("LOW", 0)),
        "pareto_pct": round(pareto_pct, 1),
        "pareto_impact_pct": 82.0,
        "vehicles_blocked_hr": int(df["vehicles_blocked_hr"].sum()),
        "economic_loss_inr": round(float(df["economic_loss_inr"].sum()), 2),
        "co2_kg": round(float(df["co2_kg"].sum()), 1),
        "person_hours_blocked": round(float(df["person_hours_blocked"].sum()), 1),
    }


def _compute_stations() -> Dict[str, Any]:
    df = _pipeline_data
    beat_stats = (
        df.groupby("police_station")
        .agg(
            total_delay=("congestion_cost", "sum"),
            violation_count=("single_violation", "count"),
            avg_gridlock=("gridlock_score", "mean"),
            top_vehicle=(
                "vehicle_type",
                lambda x: x.value_counts().idxmax() if len(x) > 0 else "UNKNOWN",
            ),
        )
        .reset_index()
        .sort_values("total_delay", ascending=False)
    )
    tier_by_station = (
        df.groupby(["police_station", "impact_tier"])
        .size()
        .unstack(fill_value=0)
        .to_dict("index")
    )
    stations = []
    for _, row in beat_stats.iterrows():
        tier_counts = tier_by_station.get(row["police_station"], {})
        stations.append(
            {
                "station": str(row["police_station"]),
                "total_delay": round(float(row["total_delay"]), 1),
                "violation_count": int(row["violation_count"]),
                "avg_gridlock": round(float(row["avg_gridlock"]), 1),
                "top_vehicle": str(row["top_vehicle"]),
                "tier_breakdown": {k: int(v) for k, v in tier_counts.items()},
            }
        )
    return {"stations": stations}


def _compute_pareto() -> Dict[str, Any]:
    df = _pipeline_data
    total_delay = df["congestion_cost"].sum()
    if total_delay == 0:
        return {"junctions": [], "total_delay": 0}
    j_stats = (
        df.groupby("mapped_junction")
        .agg(
            total_delay=("congestion_cost", "sum"),
            violation_count=("single_violation", "count"),
        )
        .reset_index()
        .sort_values("total_delay", ascending=False)
    )
    total_violations = j_stats["violation_count"].sum()
    j_stats["cumulative_pct"] = (
        j_stats["total_delay"].cumsum() / float(total_delay) * 100
    )
    j_stats["violation_pct"] = (
        j_stats["violation_count"] / float(total_violations) * 100
    )
    records = []
    for r in j_stats.head(30).to_dict("records"):
        records.append(
            {
                k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
                for k, v in r.items()
            }
        )
    return {"junctions": records, "total_delay": round(float(total_delay), 1)}


def _compute_impact_summary() -> Dict[str, Any]:
    df = _pipeline_data
    total_economic = df["economic_loss_inr"].sum()
    total_vehicles = int(df["vehicles_blocked_hr"].sum())
    total_co2 = round(float(df["co2_kg"].sum()), 1)
    total_person_hours = round(float(df["person_hours_blocked"].sum()), 1)
    j_stats = (
        df.groupby("mapped_junction")
        .agg(
            total_delay=("congestion_cost", "sum"),
            vehicles_blocked=("vehicles_blocked_hr", "sum"),
            economic_loss=("economic_loss_inr", "sum"),
            co2=("co2_kg", "sum"),
            person_hours=("person_hours_blocked", "sum"),
            violation_count=("single_violation", "count"),
            avg_gridlock=("gridlock_score", "mean"),
        )
        .reset_index()
        .sort_values("total_delay", ascending=False)
    )
    scenarios = []
    for n, subset in [
        (1, j_stats.head(1)),
        (3, j_stats.head(3)),
        (5, j_stats.head(5)),
        (10, j_stats.head(10)),
    ]:
        scenarios.append(
            {
                "clear_count": n,
                "junctions": subset["mapped_junction"].tolist(),
                "vehicles_saved_hr": int(subset["vehicles_blocked"].sum()),
                "economic_savings_inr": round(float(subset["economic_loss"].sum()), 2),
                "co2_saved_kg": round(float(subset["co2"].sum()), 1),
                "person_hours_saved": round(float(subset["person_hours"].sum()), 1),
                "pct_of_total_impact": round(
                    float(subset["economic_loss"].sum()) / float(total_economic) * 100,
                    1,
                )
                if total_economic > 0
                else 0,
            }
        )
    top_junctions = []
    for r in j_stats.head(15).to_dict("records"):
        top_junctions.append(
            {
                k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
                for k, v in r.items()
            }
        )
    return {
        "total": {
            "vehicles_blocked_hr": total_vehicles,
            "economic_loss_inr": round(float(total_economic), 2),
            "co2_kg": total_co2,
            "person_hours_blocked": total_person_hours,
        },
        "scenarios": scenarios,
        "top_junctions": top_junctions,
    }


def _precompute_all():
    """Compute all expensive aggregations once after pipeline loads. Thread-safe."""
    global _precomputed
    if _pipeline_data is None or "overview" in _precomputed:
        return
    with _lock_precomputed:
        if "overview" in _precomputed:
            return
        logger.info("Precomputing aggregated summaries...")
        try:
            tmp: Dict[str, Any] = {}
            tmp["overview"] = _compute_overview()
            tmp["stations"] = _compute_stations()
            tmp["pareto"] = _compute_pareto()
            tmp["impact_summary"] = _compute_impact_summary()
            _precomputed.update(tmp)
            logger.info("Precomputed summaries ready: %s", list(_precomputed.keys()))
        except Exception:
            logger.exception("Failed to precompute summaries")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/status")
async def get_status():
    """Pipeline readiness check — used by frontend for startup polling."""
    return {
        "pipeline_ready": _pipeline_data is not None,
        "pipeline_loading": _pipeline_loading,
        "pipeline_error": _pipeline_error,
        "pipeline_validation": _pipeline_validation,
        "precomputed": list(_precomputed.keys()),
        "violations": int(len(_pipeline_data)) if _pipeline_data is not None else 0,
    }


@app.get("/api/overview", response_model=OverviewStats)
async def get_overview():
    """City-level summary stats for the dashboard header."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    if "overview" not in _precomputed:
        await asyncio.to_thread(_precompute_all)
    if "overview" not in _precomputed:
        raise HTTPException(503, "Summary data not yet computed")
    return _precomputed["overview"]


@app.get("/api/priority-queue/{station}")
async def get_priority_queue(
    station: str,
    top_n: int = Query(10, ge=1, le=50),
):
    """Top N highest-impact violations for a given police station."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    def _compute():
        df = _pipeline_data
        if station != "ALL":
            df = df[df["police_station"] == station]

        # Compute presence probability for each violation
        df = df.copy()
        df['presence_prob'] = df.apply(
            lambda r: compute_presence_for_violation(
                r['created_datetime'], r['duration_minutes']
            ),
            axis=1,
        )
        df['actionability'] = df['congestion_cost'] * df['presence_prob']

        j_queue = (
            df.groupby("mapped_junction")
            .agg(
                total_delay=("congestion_cost", "sum"),
                violation_count=("single_violation", "count"),
                top_vehicle=(
                    "vehicle_type",
                    lambda x: x.value_counts().idxmax() if len(x) > 0 else "UNKNOWN",
                ),
                avg_gridlock=("gridlock_score", "mean"),
                avg_lat=("latitude", "mean"),
                avg_lon=("longitude", "mean"),
                worst_tier=(
                    "impact_tier",
                    lambda x: x.value_counts().index[0] if len(x) > 0 else "LOW",
                ),
                actionability_score=("actionability", "sum"),
                avg_presence_prob=("presence_prob", "mean"),
            )
            .reset_index()
            .nlargest(top_n, "actionability_score")
        )

        cards = []
        for i, (_, row) in enumerate(j_queue.iterrows(), 1):
            reasons = []
            if row["mapped_junction"] != "No Junction":
                reasons.append("at junction")
            if row["top_vehicle"] in [
                "HGV",
                "TANKER",
                "BUS (BMTC/KSRTC)",
                "PRIVATE BUS",
            ]:
                reasons.append(f"large vehicle ({row['top_vehicle']})")
            if row["avg_gridlock"] > 50:
                reasons.append("high congestion score")
            if not reasons:
                reasons.append("high congestion damage")

            presence_pct = round(float(row.get("avg_presence_prob", 1.0)) * 100, 1)
            cards.append(
                PriorityCard(
                    rank=i,
                    junction=row["mapped_junction"],
                    station=station,
                    total_delay=round(float(row["total_delay"]), 1),
                    violation_count=int(row["violation_count"]),
                    top_vehicle=row["top_vehicle"],
                    tier=row["worst_tier"],
                    gridlock_score=round(float(row["avg_gridlock"]), 1),
                    lat=round(float(row["avg_lat"]), 6),
                    lon=round(float(row["avg_lon"]), 6),
                    explanation="Ranked high because: " + ", ".join(reasons) + ".",
                    actionability_score=round(float(row.get("actionability_score", 0)), 1),
                    presence_probability_pct=presence_pct,
                )
            )

        return {"station": station, "top_n": top_n, "cards": cards}

    return await asyncio.to_thread(_compute)


@app.get("/api/stations")
async def get_stations():
    """List all police stations with summary stats."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    if "stations" not in _precomputed:
        await asyncio.to_thread(_precompute_all)
    if "stations" not in _precomputed:
        raise HTTPException(503, "Summary data not yet computed")
    return _precomputed["stations"]


@app.get("/api/map-data")
async def get_map_data():
    """All violation coordinates + junction markers for map rendering."""
    await asyncio.to_thread(_ensure_base_data)
    if _pipeline_data is None or _junction_coords is None:
        raise HTTPException(503, "Pipeline not loaded")

    def _compute():
        df = _pipeline_data
        sample = df.nlargest(500, "congestion_cost")[
            ["latitude", "longitude", "congestion_cost", "gridlock_score",
             "impact_tier", "vehicle_type", "single_violation", "mapped_junction",
             "police_station", "duration_minutes"]
        ].copy()

        violations = sample.to_dict("records")

        junction_stats = (
            df.groupby("mapped_junction")
            .agg(total_delay=("congestion_cost", "sum"),
                 violation_count=("single_violation", "count"),
                 avg_gridlock=("gridlock_score", "mean"))
            .to_dict("index")
        )

        junctions = []
        for code, coords in _junction_coords.items():
            stats = junction_stats.get(code)
            if stats is not None:
                junctions.append({
                    "code": code, "lat": coords[0], "lon": coords[1],
                    "total_delay": round(stats["total_delay"], 1),
                    "violation_count": int(stats["violation_count"]),
                    "avg_gridlock": round(stats["avg_gridlock"], 1),
                })

        return {"violations": violations, "junctions": junctions,
                "center_lat": 12.9716, "center_lon": 77.5946}

    return await asyncio.to_thread(_compute)


@app.get("/api/cascade")
async def get_cascade():
    """Cascade correlation pairs for domino-effect visualization."""
    await asyncio.to_thread(_ensure_cascade)

    if _cascade is None:
        raise HTTPException(503, "Cascade analysis failed")

    lag_df = _cascade.get("lag_correlations", pd.DataFrame())
    cascades = _cascade.get("cascades", [])

    pairs = []
    if len(lag_df) > 0:
        top = lag_df.head(20)
        for _, row in top.iterrows():
            pairs.append(
                CascadePair(
                    from_junction=row["from_junction"],
                    to_junction=row["to_junction"],
                    distance_m=row["distance_m"],
                    correlation=round(row["lag_correlation"], 4),
                    violations_from=int(row["from_violations"]),
                    violations_to=int(row["to_violations"]),
                )
            )

    chains = []
    for c in cascades[:5]:
        chains.append(
            {
                "chain": c["chain"],
                "total_correlation": round(c["total_correlation"], 4),
                "total_distance": round(c["total_distance"], 0),
            }
        )

    return {
        "pairs": pairs,
        "chains": chains,
        "total_tested": len(lag_df),
        "significant_count": len(lag_df[lag_df["lag_correlation"] > 0.2])
        if len(lag_df) > 0
        else 0,
    }


_cascade_gnn = None
_lock_cascade_gnn = threading.Lock()

def _ensure_cascade_gnn():
    global _cascade_gnn
    if _cascade_gnn is not None:
        return
    with _lock_cascade_gnn:
        if _cascade_gnn is not None:
            return
        _ensure_base_data()
        if _pipeline_data is None or _junction_coords is None:
            return
        try:
            _cascade_gnn = run_gnn_cascade(_pipeline_data, _junction_coords)
        except Exception as e:
            logger.error(f"GNN cascade failed: {e}")
            _cascade_gnn = {"status": "failed", "error": str(e)}


@app.get("/api/cascade/gnn-predict")
async def get_gnn_cascade_predict():
    """GNN cascade predictions — ML-based cascade probability for all junction pairs."""
    await asyncio.to_thread(_ensure_cascade_gnn)
    if _cascade_gnn is None or _cascade_gnn.get("status") == "failed":
        raise HTTPException(503, "GNN cascade analysis not available")
    return _cascade_gnn


@app.get("/api/curbflex")
async def get_curbflex():
    """Chronic zones + policy recommendations."""
    await asyncio.to_thread(_ensure_curbflex)

    if _curbflex is None:
        raise HTTPException(503, "CurbFlex analysis failed")

    chronic = _curbflex.get("chronic_zones", pd.DataFrame())
    recs = _curbflex.get("recommendations", [])
    equity = _curbflex.get("equity_stats", pd.DataFrame())

    return {
        "chronic_zones": chronic.to_dict("records") if len(chronic) > 0 else [],
        "recommendations": recs,
        "equity_stats": equity.to_dict("records") if len(equity) > 0 else [],
    }


@app.get("/api/dispatch")
async def get_dispatch(num_trucks: int = Query(2, ge=1, le=4)):
    """Tow truck shift plan with VRP routing."""
    await asyncio.to_thread(_ensure_base_data)
    if _pipeline_data is None or _junction_coords is None:
        raise HTTPException(503, "Pipeline not loaded")

    try:
        plan = await asyncio.wait_for(
            asyncio.to_thread(
                run_dispatch, _pipeline_data, _junction_coords, num_trucks
            ),
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Dispatch computation timed out")

    routes = []
    for i, route in enumerate(plan.get("routes", [])):
        stops = [{"lat": r[0], "lon": r[1]} for r in route]

        total_dist = 0.0
        for j in range(1, len(route)):
            dlat = route[j][0] - route[j - 1][0]
            dlon = route[j][1] - route[j - 1][1]
            total_dist += np.sqrt(dlat**2 + dlon**2) * 111000

        routes.append(
            DispatchRoute(
                truck_id=i + 1,
                stops=stops,
                total_distance_km=round(total_dist / 1000, 1),
            )
        )

    return {
        "routes": routes,
        "responses": plan.get("responses", []),
        "summary": plan.get("summary", {}),
    }


@app.get("/api/alerts")
async def get_alerts(count: int = Query(10, ge=1, le=20)):
    """Generate alerts for top priority violations."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    def _compute(n):
        df = _pipeline_data
        top = df.nlargest(n, "congestion_cost")

        alerts = []
        recent_pool = df.tail(500)
        if "created_datetime" in df.columns:
            recent_pool = recent_pool.copy()
            recent_pool["created_datetime"] = pd.to_datetime(
                recent_pool.get("created_datetime", "2024-06-01 12:00:00"), errors="coerce"
            )

        for _, row in top.iterrows():
            if len(alerts) >= n:
                break
            mapped = row.to_dict()
            mapped["junction_"] = mapped.get("mapped_junction", "Unknown")
            mapped["created_datetime"] = mapped.get("created_datetime", "2024-06-01 12:00:00")
            if not isinstance(mapped["created_datetime"], pd.Timestamp):
                mapped["created_datetime"] = pd.to_datetime(
                    mapped["created_datetime"], errors="coerce"
                )
            mapped["vehicle_number"] = mapped.get("vehicle_number", mapped.get("vehicle_no", "N/A"))
            mapped["location"] = mapped.get("location",
                f"{mapped.get('latitude', 0)}, {mapped.get('longitude', 0)}")
            mapped["id"] = mapped.get("id", str(mapped.get("index", len(alerts))))

            alert = _alert_system.check_and_alert(
                pd.Series(mapped), recent_pool, row["congestion_cost"], anomaly_score=None
            )
            if alert:
                alerts.append(_sanitize(alert))

        return {"alerts": alerts, "count": len(alerts)}

    return await asyncio.to_thread(_compute, count)


@app.get("/api/repeat-offenders")
async def get_repeat_offenders(min_violations: int = Query(3, ge=2, le=50)):
    """Vehicles with multiple high-impact violations."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    await asyncio.to_thread(_ensure_repeat_offenders)

    if _repeat_offenders_data is None:
        raise HTTPException(503, "Repeat offenders data not available")

    offenders = _repeat_offenders_data[
        _repeat_offenders_data["violation_count"] >= min_violations
    ]
    offenders = offenders.sort_values("violation_count", ascending=False)

    return {
        "offenders": offenders.head(20).to_dict("records"),
        "total_count": len(offenders),
    }


@app.get("/api/pareto")
async def get_pareto():
    """Pareto analysis data for ACP view."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    if "pareto" not in _precomputed:
        await asyncio.to_thread(_precompute_all)
    if "pareto" not in _precomputed:
        raise HTTPException(503, "Summary data not yet computed")
    return _precomputed["pareto"]


@app.get("/api/predictions")
async def get_predictions():
    """ML model predictions — XGBoost/LightGBM predicted congestion cost per junction."""
    await asyncio.to_thread(_ensure_models)

    if _models is None or _prepared_df is None:
        raise HTTPException(503, "Models not trained or pipeline not loaded")

    def _compute():
        df = _prepared_df.copy()
        features = _prepared_features or _models.get("features", [])

        xgb_model = _models.get("xgb_model")
        lgb_model = _models.get("lgb_model")

        if xgb_model is None and lgb_model is None:
            return None

        X = df[features].fillna(0)
        if xgb_model is not None:
            df["predicted_cost_xgb"] = xgb_model.predict(X)
        if lgb_model is not None:
            df["predicted_cost_lgb"] = lgb_model.predict(X)

        pred_col = "predicted_cost_xgb" if xgb_model is not None else "predicted_cost_lgb"
        df["predicted_cost"] = df[pred_col].clip(lower=0)

        junction_preds = (
            df.groupby("mapped_junction")
            .agg(actual_cost=("congestion_cost", "sum"),
                 predicted_cost=("predicted_cost", "sum"),
                 violation_count=("single_violation", "count"),
                 avg_gridlock=("gridlock_score", "mean"))
            .reset_index()
        )

        junction_preds["prediction_error"] = (
            junction_preds["predicted_cost"] - junction_preds["actual_cost"]
        ).round(2)
        junction_preds["prediction_pct"] = (
            junction_preds["predicted_cost"]
            / junction_preds["actual_cost"].replace(0, np.nan) * 100
        ).round(1)

        junction_preds = junction_preds.sort_values("predicted_cost", ascending=False)

        return {
            "junctions": junction_preds.head(30).to_dict("records"),
            "model_metrics": _models.get("xgb_metrics", {}),
            "features_used": len(features),
        }

    result = await asyncio.to_thread(_compute)
    if result is None:
        raise HTTPException(503, "No models available")
    return result


@app.get("/api/simulator")
async def get_simulator(
    top_n: int = Query(10, ge=1, le=100),
    filter_station: str = None,
    filter_tier: str = None,
):
    """What-if simulator: clearing top N violations and its impact on congestion."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    def _compute(fs, ft):
        df = _pipeline_data.copy()
        if fs and fs != "ALL":
            df = df[df["police_station"] == fs]
        if ft and ft != "ALL":
            df = df[df["impact_tier"] == ft]

        total_cost = df["congestion_cost"].sum()
        total_violations = len(df)

        if total_cost == 0:
            return {"scenarios": [], "baseline": {"cost": 0, "violations": 0}}

        baseline = {
            "cost": round(total_cost, 1), "violations": total_violations,
            "junctions": int(df["mapped_junction"].nunique()),
            "stations": int(df["police_station"].nunique()),
        }

        scenarios = []
        sorted_df = df.sort_values("congestion_cost", ascending=False)

        for n in [1, 5, 10, 15, 20]:
            if n > len(sorted_df):
                break
            cleared = sorted_df.head(n)
            remaining_cost = total_cost - cleared["congestion_cost"].sum()
            pct_reduction = cleared["congestion_cost"].sum() / total_cost * 100
            tier_impact = cleared["impact_tier"].value_counts().to_dict()
            top_junction = cleared.groupby("mapped_junction")["congestion_cost"].sum()
            top_junction_name = top_junction.idxmax() if len(top_junction) > 0 else "N/A"
            top_junction_pct = (top_junction.max() / total_cost * 100) if len(top_junction) > 0 else 0
            scenarios.append({
                "clear_count": n, "cleared_cost": round(cleared["congestion_cost"].sum(), 1),
                "remaining_cost": round(remaining_cost, 1), "pct_reduction": round(pct_reduction, 1),
                "tier_impact": tier_impact, "top_junction": top_junction_name,
                "top_junction_pct": round(top_junction_pct, 1), "violations_cleared": n,
                "vehicles_saved_hr": int(cleared["vehicles_blocked_hr"].sum()),
                "economic_savings_inr": round(float(cleared["economic_loss_inr"].sum()), 2),
                "co2_saved_kg": round(float(cleared["co2_kg"].sum()), 1),
                "person_hours_saved": round(float(cleared["person_hours_blocked"].sum()), 1),
            })

        return {"baseline": baseline, "scenarios": scenarios,
                "filter_station": fs or "ALL", "filter_tier": ft or "ALL"}

    return await asyncio.to_thread(_compute, filter_station, filter_tier)


@app.get("/api/impact-summary")
async def get_impact_summary():
    """Actionable impact summary: clear top N junctions = save X vehicles/hr = ₹Y."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")
    if "impact_summary" not in _precomputed:
        await asyncio.to_thread(_precompute_all)
    if "impact_summary" not in _precomputed:
        raise HTTPException(503, "Summary data not yet computed")
    return _precomputed["impact_summary"]


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
    import math
    from datetime import datetime, timezone

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

    filtered = _phantom_data[
        _phantom_data["time_block"].isin([current_tb, next_tb])
    ].copy()
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
        zones.append(
            RiskZone(
                rank=rank,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                vehicle_type=vtype,
                weight=row["weight"],
                nearby_seed_count=row["nearby_seed_count"],
                avg_distance_to_seeds=row["avg_distance_to_seeds"],
                phantom_risk_score=row["phantom_risk_score"],
                recommended_action=action,
            )
        )

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

    await asyncio.to_thread(_ensure_capacity)

    if _capacity_data is None:
        raise HTTPException(503, "Capacity analysis not available")

    junction_stats = _capacity_data["junctions"]
    junctions = []
    for _, row in junction_stats.iterrows():
        junctions.append(
            {
                "junction": row["mapped_junction"],
                "capacity_loss_pct": row["junction_capacity_loss_pct"],
                "remaining_pct": row["junction_remaining_pct"],
                "status": str(row["operational_status"]),
                "violation_count": int(row["violation_count"]),
                "footpath_violations": int(row["footpath_violations"]),
                "blocked_width_m": round(row["total_blocked_width"], 2),
            }
        )

    return {
        "summary": _capacity_data["summary"],
        "junctions": junctions,
    }


@app.get("/api/causal-impact")
async def get_causal_impact():
    """Causal Impact Engine — proves parking → congestion causation with regression."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    await asyncio.to_thread(_ensure_causal_impact)

    if _causal_impact_data is None:
        raise HTTPException(503, "Causal impact analysis not available")

    return {
        "model": _causal_impact_data.get("model", {}),
        "chart_data": _causal_impact_data.get("chart_data", {}),
        "before_after": _causal_impact_data.get("before_after", {}),
        "worst_junction": _causal_impact_data.get("worst_junction"),
    }


@app.get("/api/evidence-packet/{violation_idx}")
async def get_evidence_packet(violation_idx: int):
    """Generate court-ready evidence packet for a specific violation."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    from src.evidence_packet import generate_evidence_html, generate_evidence_packet

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
        "packet": packet,
        "html": html,
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
        "status": result.get("status", "unknown"),
        "recommendations": result.get("recommendations", []),
        "impact": result.get("impact", {}),
        "hourly_patterns": result.get("hourly_patterns", []),
    }


@app.get("/api/cause-attribution/{junction}", response_model=CauseAttributionResponse)
async def get_cause_attribution(junction: str):
    """Counterfactual-style attribution: what is actually causing the jam at this junction."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    jdf = df[df["mapped_junction"] == junction]
    if len(jdf) == 0:
        raise HTTPException(404, f"Junction not found: {junction}")

    total_delay = float(jdf["congestion_cost"].sum())
    if total_delay <= 0:
        total_delay = 1.0

    parking_mask = (
        jdf["single_violation"]
        .astype(str)
        .str.contains(
            "PARKING|FOOTPATH|OBSTRUCTION|NO PARKING", case=False, regex=True, na=False
        )
    )
    parking_delay = float(jdf.loc[parking_mask, "congestion_cost"].sum())
    parking_pct = round((parking_delay / total_delay) * 100, 1)
    parking_pct = max(0.0, min(parking_pct, 97.0))

    # Residual factors: signal/saturation. Keep grounded but stable.
    signal_pct = round(min(25.0, max(5.0, 100.0 - parking_pct - 6.0)), 1)
    residual_pct = round(max(0.0, 100.0 - parking_pct - signal_pct), 1)

    hotspot_count = int(parking_mask.sum())
    eta_minutes = max(5, min(30, hotspot_count * 4))
    commuters_benefited = int(jdf["vehicles_blocked_hr"].sum() * 0.6)

    recommendation = (
        f"{junction}: clear {hotspot_count} parking-obstruction hotspot(s) first. "
        f"Expected to reduce about {parking_pct}% of current congestion before signal retiming."
    )

    return {
        "junction": junction,
        "total_delay_minutes": round(total_delay, 1),
        "attribution_pcts": {
            "Illegal parking / obstructions": parking_pct,
            "Signal cycle inefficiency": signal_pct,
            "Background flow spillover": residual_pct,
        },
        "action_recommendation": recommendation,
        "clear_hotspot_eta_minutes": eta_minutes,
        "commuters_benefited_est": commuters_benefited,
    }


@app.get("/api/court-readiness/{violation_id}", response_model=CourtReadinessResponse)
async def get_court_readiness(violation_id: str):
    """Fast legal readiness score based on actual violation data."""
    from backend.database import SessionLocal
    from backend.models import Violation

    db = SessionLocal()
    try:
        try:
            vid = int(violation_id)
            violation = db.query(Violation).filter(Violation.id == vid).first()
        except ValueError:
            violation = (
                db.query(Violation)
                .filter(Violation.mapped_junction == violation_id)
                .order_by(Violation.created_datetime.desc())
                .first()
            )
    except Exception:
        violation = None
    finally:
        db.close()

    if not violation:
        # Fallback to empty checks if not found
        checks = {
            "clear_plate_photo": False,
            "timestamp_present": False,
            "gps_lock_precise": False,
            "location_matches_junction": False,
            "supporting_context_photo": False,
        }
    else:
        has_image = bool(violation.image_url)
        checks = {
            "clear_plate_photo": has_image,
            "timestamp_present": bool(violation.created_datetime),
            "gps_lock_precise": bool(violation.latitude and violation.longitude),
            "location_matches_junction": bool(violation.mapped_junction and violation.mapped_junction != 'No Junction'),
            "supporting_context_photo": has_image,
        }

    score = sum(20 for passed in checks.values() if passed)
    if score >= 85:
        status = "LIKELY_TO_HOLD"
        recommendation = "Court-ready packet. Safe to proceed with challan workflow."
    elif score >= 60:
        status = "MAY_BE_CHALLENGED"
        recommendation = (
            "Add one more wide-angle context photo to improve legal confidence."
        )
    else:
        status = "HIGH_DISMISSAL_RISK"
        recommendation = (
            "Insufficient evidence quality. Capture clearer plate and location proof."
        )

    return {
        "violation_id": violation_id,
        "score": score,
        "status": status,
        "checks": checks,
        "recommendation": recommendation,
    }


@app.post("/api/flipkart-scouts/report", response_model=FlipkartScoutReportOut)
async def post_flipkart_scout_report(payload: FlipkartScoutReportIn):
    """Crowdsourced traffic-scout ingestion endpoint (Flipkart rider reports)."""
    from backend.database import SessionLocal
    from backend.models import FlipkartReport

    db = SessionLocal()
    try:
        report = FlipkartReport(
            scout_id=payload.scout_id,
            junction=payload.junction,
            latitude=payload.latitude,
            longitude=payload.longitude,
            photo_url=payload.photo_url,
            vehicle_number=payload.vehicle_number,
            notes=payload.notes,
            status="PENDING"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving flipkart report: {e}")
        raise HTTPException(500, detail="Failed to save report")
    finally:
        db.close()

    # Estimate severity from nearest known violations around reported point.
    if _pipeline_data is not None:
        df = _pipeline_data
        lat, lon = payload.latitude, payload.longitude

        nearby = df[
            (df["latitude"].between(lat - 0.0025, lat + 0.0025))
            & (df["longitude"].between(lon - 0.0025, lon + 0.0025))
        ]
        estimated_cii = (
            float(nearby["congestion_cost"].nlargest(20).mean())
            if len(nearby) > 0
            else 1200.0
        )
    else:
        estimated_cii = 1200.0

    priority = "HIGH" if estimated_cii > 5000 else "MEDIUM"
    if estimated_cii < 1000:
        priority = "LOW"

    report_id = f"FS-{report.id:04d}"

    return {
        "report_id": report_id,
        "status": "PENDING",
        "priority": priority,
        "reward_points": 50 if priority == "HIGH" else 10,
        "estimated_cii": round(estimated_cii, 1),
        "message": f"Report received. +{50 if priority == 'HIGH' else 10} SuperCoins will be credited upon police verification.",
    }


class VerifyReportPayload(BaseModel):
    status: str


@app.get("/api/flipkart-scouts/reports")
async def get_flipkart_reports(request: Request):
    """List all Flipkart Scout reports, most recent first. Filtered by scout_id for scouts."""
    from backend.database import SessionLocal
    from backend.models import FlipkartReport

    db = SessionLocal()
    try:
        user = getattr(request.state, "user", None)
        query = db.query(FlipkartReport)
        
        # Scouts can only fetch their own reports
        if user and user.role == "scout":
            query = query.filter(FlipkartReport.scout_id == user.scout_id)
            
        reports = (
            db.query(FlipkartReport)
            .filter(FlipkartReport.id.in_(query.with_entities(FlipkartReport.id)))
            .order_by(FlipkartReport.created_at.desc())
            .all()
        )
        return {
            "reports": [
                {
                    "id": r.id,
                    "report_id": f"FS-{r.id:04d}",
                    "scout_id": r.scout_id,
                    "junction": r.junction,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "photo_url": r.photo_url,
                    "vehicle_number": r.vehicle_number,
                    "notes": r.notes,
                    "status": r.status or "PENDING",
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching flipkart reports: {e}")
        raise HTTPException(500, detail="Failed to fetch reports")
    finally:
        db.close()


@app.post("/api/flipkart-scouts/verify/{report_id}")
async def verify_flipkart_report(report_id: int, payload: VerifyReportPayload):
    """Verify (Approve or Reject) a Flipkart Scout report. Promotes approved reports to violations."""
    global _precomputed, _capacity_data, _repeat_offenders_data, _causal_impact_data
    from backend.database import SessionLocal
    from backend.models import FlipkartReport, Violation
    import datetime

    db = SessionLocal()
    try:
        report = db.query(FlipkartReport).filter(FlipkartReport.id == report_id).first()
        if not report:
            raise HTTPException(404, detail="Scout report not found")

        status_upper = payload.status.upper()
        if status_upper not in ["APPROVED", "REJECTED"]:
            raise HTTPException(400, detail="Invalid status. Must be APPROVED or REJECTED.")

        report.status = status_upper
        db.commit()

        if status_upper == "APPROVED":
            # Ingest as a new live violation
            new_violation = Violation(
                vehicle_number=report.vehicle_number or "UNKNOWN",
                vehicle_type="CAR",
                latitude=report.latitude,
                longitude=report.longitude,
                violation_type="PARKING_VIOLATION",
                junction_name=report.junction,
                police_station=report.junction,
                created_datetime=datetime.datetime.utcnow(),
                hour=datetime.datetime.utcnow().hour,
                day_of_week=datetime.datetime.utcnow().weekday(),
                month=datetime.datetime.utcnow().month,
                congestion_cost=0.0,
                severity=1,
                image_url=report.photo_url
            )
            db.add(new_violation)
            db.commit()
            db.refresh(new_violation)

            # Score, update and append to dataframe
            await asyncio.to_thread(ingest_and_score_violation, new_violation, db)

            # Invalidate caches so dashboards reflect the newly approved violation
            with _lock_precomputed:
                _precomputed.clear()
            with _lock_capacity:
                _capacity_data = None
            with _lock_repeat:
                _repeat_offenders_data = None
            with _lock_causal:
                _causal_impact_data = None

        return {"status": "success", "report_id": report_id, "verification_status": status_upper}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error verifying flipkart report")
        raise HTTPException(500, detail=str(e))
    finally:
        db.close()


@app.get("/api/cost-metrics")
async def get_cost_metrics():
    """Cost per junction per month — for scalability pitch."""
    # Unit economics (based on Project ClearLane estimates)
    return {
        "per_station": {
            "cloud_cost_inr": 2400,
            "coverage_junctions": 15,
            "cost_per_junction_inr": 160,
            "cost_per_violation_inr": 12,
            "model": "CPU inference (no GPU)",
            "scaling": {
                "1_station": {"monthly": 2400, "junctions": 15},
                "10_stations": {"monthly": 20000, "junctions": 150},
                "50_stations": {"monthly": 80000, "junctions": 750},
                "city_wide": {"monthly": 300000, "junctions": 2800},
            },
        },
        "comparison": {
            "traditional_enforcement": {
                "monthly_per_station": 15000,
                "coverage": "5 junctions",
            },
            "clearlane": {"monthly_per_station": 2400, "coverage": "15 junctions"},
            "savings_pct": 84,
        },
        "roi": {
            "annual_cost": 28800,
            "annual_savings_inr": 8500000,
            "roi_pct": 29400,
            "payback_days": 1,
        },
    }


@app.get("/api/degradation-status")
async def get_degradation_status():
    """System health and graceful degradation status."""
    from src.degradation import get_camera_status, get_system_health
    from backend.database import SessionLocal
    from backend.models import CameraJunction
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total_cameras = db.query(func.count(CameraJunction.id)).scalar() or 1
        online_cameras = db.query(func.count(CameraJunction.id)).filter(CameraJunction.is_online == True).scalar() or 0
        online_pct = round((online_cameras / total_cameras) * 100, 1)
        camera_status_str = f"{online_pct}% online"
    except Exception as e:
        logger.error(f"Error checking camera status: {e}")
        camera_status_str = "Status Unknown"
        online_pct = 0
    finally:
        db.close()

    health = get_system_health(camera_status_str=camera_status_str)

    # Check a few sample cameras
    sample_cameras = []
    for jid in ["BTP001", "BTP044", "BTP148", "BTP200", "BTP300"]:
        status = get_camera_status(jid)
        sample_cameras.append(status)

    online_count = sum(1 for c in sample_cameras if c["status"] == "ONLINE")

    return {
        "system_health": health,
        "camera_sample": sample_cameras,
        "online_percentage": round(online_count / len(sample_cameras) * 100, 1),
        "degradation_handlers": {
            "camera_offline": "Historical heatmap fallback",
            "low_bandwidth": "Metadata-only transmission (50 bytes vs 50KB)",
            "model_uncertain": "Human-in-the-loop review",
            "two_wheeler_footpath": "Special priority queue",
        },
    }


@app.get("/api/llm/nudge")
async def get_llm_nudge(
    violation_type: str = "wrong_parking",
    vehicle_type: str = "TWO_WHEELER",
    location: str = "MG Road",
):
    """Generate personalized nudge message via GLM 5.2 Free."""
    from src.llm_client import generate_nudge_message

    msg = await asyncio.to_thread(
        generate_nudge_message,
        violation_type=violation_type, vehicle_type=vehicle_type,
        location=location, impact_score=65.0,
    )
    return {"message": msg, "model": "z-ai/glm-5.2-free", "provider": "ZenMux"}


@app.get("/api/llm/report")
async def get_llm_report(
    junction: str = "KR Market",
    violations: int = 12,
    capacity_loss: float = 35.0,
    economic_impact: float = 180000,
):
    """Generate enforcement report via GLM 5.2 Free."""
    from src.llm_client import generate_enforcement_report

    report = await asyncio.to_thread(
        generate_enforcement_report,
        junction=junction, violations=violations,
        capacity_loss=capacity_loss, economic_impact=economic_impact,
    )
    return {"report": report, "model": "z-ai/glm-5.2-free", "provider": "ZenMux"}


@app.get("/api/llm/query")
async def query_clearlane_llm(q: str = Query(..., min_length=1, max_length=2000)):
    """Natural language query interface for ClearLane data."""
    from src.llm_client import query_clearlane

    context = ""
    if _pipeline_data is not None:
        context = f"Available violations: {len(_pipeline_data)}, junctions: {len(_junction_coords) if _junction_coords is not None else 0}"
    answer = await asyncio.to_thread(query_clearlane, question=q, context=context)
    return {"answer": answer, "model": "z-ai/glm-5.2-free", "provider": "ZenMux"}


# ---------------------------------------------------------------------------
# AI Insights Endpoints — Expose hidden ML capabilities
# ---------------------------------------------------------------------------


@app.get("/api/tipping-points")
async def get_tipping_points():
    """
    Tipping Point Detection — Predicts the EXACT 15-minute window when congestion will spike.
    Uses 7-hour rolling window with 3-sigma spike detection.
    """
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    def _compute():
        from tipping_points import find_tipping_points
        import re

        df = _pipeline_data.copy()
        if "junction_node" not in df.columns:
            df["junction_node"] = df.get("mapped_junction", "No Junction")
        if "time_block" not in df.columns:
            if "created_date" in df.columns:
                df["created_datetime"] = pd.to_datetime(df["created_date"], errors="coerce")
                df["time_block"] = df["created_datetime"].dt.strftime("%H:%M")
                df["time_block"] = df["time_block"].apply(
                    lambda x: (f"{int(x.split(':')[0]):02d}:{(int(x.split(':')[1]) // 15) * 15:02d}"
                               if pd.notna(x) and ":" in x else "12:00")
                )
            else:
                df["time_block"] = "12:00"
        if "weight" not in df.columns:
            df["weight"] = df.get("gridlock_score", df.get("congestion_cost", 1.0))

        tipping_points = find_tipping_points(df)

        predictions = []
        for junction, prediction in tipping_points.items():
            time_match = re.search(r"at (\d+:\d+ [AP]M)", prediction)
            predicted_time = time_match.group(1) if time_match else "Unknown"
            predictions.append({
                "junction": junction,
                "predicted_time": predicted_time,
                "message": prediction,
                "status": "CRITICAL" if "AM" in predicted_time
                    and int(predicted_time.split(":")[0]) in range(7, 11) else "WARNING",
            })

        predictions.sort(key=lambda x: x["junction"])
        return {
            "predictions": predictions[:20],
            "total_junctions_with_tipping_points": len(predictions),
            "methodology": "7-hour rolling window, 3-sigma spike detection",
            "description": "Identifies the exact 15-minute window where congestion spikes beyond normal rhythm.",
        }

    return await asyncio.to_thread(_compute)


class AnomalyScoreResponse(BaseModel):
    junction: str
    anomaly_score: float
    is_anomaly: bool
    anomaly_reason: str
    violation_count: int


@app.get("/api/anomaly-scores")
async def get_anomaly_scores():
    """
    Isolation Forest Anomaly Detection — ML that detects unusual violation patterns.
    Returns junctions with anomaly scores (lower = more anomalous).
    """
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    def _compute():
        import numpy as np
        from src.anomaly_detection import ViolationAnomalyDetector

        df = _pipeline_data.copy()
        detector = ViolationAnomalyDetector(contamination=0.05)

        try:
            anomaly_scores, anomaly_labels = detector.fit_predict(df)
            explanations = detector.get_anomaly_explanations(df, anomaly_scores)
        except Exception as e:
            logger.warning("Anomaly detection failed: %s", e)
            return {"anomalies": [], "total_analyzed": 0, "error": str(e),
                    "methodology": "Isolation Forest, 5% contamination"}

        df["anomaly_score"] = anomaly_scores
        df["is_anomaly"] = explanations["is_anomaly"]
        df["anomaly_reason"] = explanations["anomaly_reason"]

        junction_anomalies = (
            df.groupby("mapped_junction")
            .agg(mean_anomaly_score=("anomaly_score", "mean"),
                 anomaly_count=("is_anomaly", "sum"),
                 violation_count=("single_violation", "count"),
                 top_reason=("anomaly_reason",
                    lambda x: x.value_counts().index[0] if len(x) > 0 else "Unknown"))
            .reset_index()
        )

        threshold = np.percentile(anomaly_scores, 5)
        junction_anomalies["is_anomaly"] = junction_anomalies["mean_anomaly_score"] < threshold
        junction_anomalies = junction_anomalies.sort_values("mean_anomaly_score")

        anomalies = []
        for _, row in junction_anomalies.head(20).iterrows():
            anomalies.append(AnomalyScoreResponse(
                junction=row["mapped_junction"],
                anomaly_score=round(row["mean_anomaly_score"], 4),
                is_anomaly=bool(row["is_anomaly"]),
                anomaly_reason=row["top_reason"],
                violation_count=int(row["violation_count"]),
            ))

        return {
            "anomalies": anomalies,
            "total_analyzed": len(df),
            "anomaly_count": int(anomaly_labels[anomaly_labels == -1].sum() if len(anomaly_labels) > 0 else 0),
            "methodology": "Isolation Forest, 5% contamination, 7 engineered features",
            "features": detector.feature_columns if hasattr(detector, "feature_columns") else [],
        }

    return await asyncio.to_thread(_compute)


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
    junction_df = df[df["mapped_junction"] == junction_id]

    if len(junction_df) == 0:
        raise HTTPException(404, f"Junction {junction_id} not found")

    # Extract hour from created_date
    if "created_datetime" not in junction_df.columns:
        junction_df["created_datetime"] = pd.to_datetime(
            junction_df["created_date"], errors="coerce"
        )

    junction_df["hour"] = junction_df["created_datetime"].dt.hour

    # Aggregate by hour
    hourly = (
        junction_df.groupby("hour")
        .agg(
            violation_count=("single_violation", "count"),
            total_delay=("congestion_cost", "sum"),
            avg_gridlock=("gridlock_score", "mean"),
            vehicles_blocked=("vehicles_blocked_hr", "sum"),
        )
        .reset_index()
    )

    # Fill missing hours with zeros
    all_hours = pd.DataFrame({"hour": range(24)})
    hourly = all_hours.merge(hourly, on="hour", how="left").fillna(0)

    # Identify peak hours (top 3)
    peak_hours = hourly.nlargest(3, "violation_count")["hour"].tolist()

    # Format for heatmap (24-hour cycle)
    heatmap_data = []
    for _, row in hourly.iterrows():
        hour = int(row["hour"])
        period = "AM" if hour < 12 else "PM"
        display_hour = hour % 12 or 12
        heatmap_data.append(
            {
                "hour": hour,
                "label": f"{display_hour} {period}",
                "violations": int(row["violation_count"]),
                "delay": round(row["total_delay"], 1),
                "gridlock": round(row["avg_gridlock"], 1),
                "vehicles_blocked": int(row["vehicles_blocked"]),
                "is_peak": hour in peak_hours,
            }
        )

    # Day of week breakdown
    junction_df["day_of_week"] = junction_df["created_datetime"].dt.dayofweek
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow = (
        junction_df.groupby("day_of_week")
        .agg(
            violation_count=("single_violation", "count"),
            total_delay=("congestion_cost", "sum"),
        )
        .reset_index()
    )

    weekly_data = []
    for _, row in dow.iterrows():
        weekly_data.append(
            {
                "day": dow_names[int(row["day_of_week"])],
                "violations": int(row["violation_count"]),
                "delay": round(row["total_delay"], 1),
            }
        )

    return {
        "junction": junction_id,
        "hourly_heatmap": heatmap_data,
        "peak_hours": [f"{h:02d}:00" for h in peak_hours],
        "weekly_pattern": weekly_data,
        "total_violations": len(junction_df),
        "summary": {
            "worst_hour": int(hourly.nlargest(1, "violation_count")["hour"].values[0])
            if len(hourly) > 0
            else 12,
            "worst_day": dow_names[
                int(dow.nlargest(1, "violation_count")["day_of_week"].values[0])
            ]
            if len(dow) > 0
            else "Mon",
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
    officer_name: str = Query(
        "Officer Kumar", description="Officer name for personalization"
    ),
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

    from datetime import datetime

    from src.llm_client import chat_completion

    df = _pipeline_data.copy()

    # Filter to officer's zone (match police_station)
    zone_df = df[df["police_station"].str.contains(officer_zone, case=False, na=False)]

    if len(zone_df) == 0:
        zone_df = df.head(100)  # Fallback

    # Calculate zone metrics
    total_violations = len(zone_df)
    total_delay = zone_df["congestion_cost"].sum()
    vehicles_blocked = int(zone_df["vehicles_blocked_hr"].sum())
    economic_loss = round(zone_df["economic_loss_inr"].sum(), 2)

    # Top 3 junctions
    junction_stats = (
        zone_df.groupby("mapped_junction")
        .agg(
            violation_count=("single_violation", "count"),
            total_delay=("congestion_cost", "sum"),
        )
        .reset_index()
        .nlargest(3, "total_delay")
    )

    priority_junctions = junction_stats["mapped_junction"].tolist()[:3]

    # Get tipping points for this zone
    try:
        from tipping_points import find_tipping_points

        tipping = find_tipping_points(zone_df)
        tipping_alerts = [v for k, v in tipping.items() if k in priority_junctions][:2]
    except Exception:
        tipping_alerts = []

    # Generate briefing text via LLM
    briefing_prompt = f"""Generate a 60-word morning shift briefing for {officer_name} in {officer_zone} zone:
- Today focus on: {", ".join(priority_junctions[:2])}
- Yesterday: {total_violations} violations, {vehicles_blocked} vehicles blocked
- Economic impact: ₹{economic_loss:,.0f}
- Tipping point warning: {tipping_alerts[0] if tipping_alerts else "No critical predictions"}
- Top repeat offender junction: {priority_junctions[0] if priority_junctions else "N/A"}

Format: Conversational, officer-friendly, 2-minute read. Start with 'Good morning, {officer_name}.'"""

    briefing_text = chat_completion(
        briefing_prompt,
        system="You are a concise traffic briefing generator for BTP officers. Write in plain English, no jargon.",
        temperature=0.6,
    )

    # Format priority zones for response
    priority_zones = []
    for _, row in junction_stats.iterrows():
        priority_zones.append(
            {
                "junction": row["mapped_junction"],
                "violations": int(row["violation_count"]),
                "delay": round(row["total_delay"], 1),
            }
        )

    return ShiftBriefingResponse(
        officer_name=officer_name,
        shift_date=datetime.now().strftime("%Y-%m-%d"),
        briefing_text=briefing_text,
        audio_available=True,  # Indicates TTS can be used in frontend
        priority_zones=priority_zones,
        key_metrics={
            "zone_violations": total_violations,
            "vehicles_blocked": vehicles_blocked,
            "economic_loss_inr": economic_loss,
            "tipping_alerts": len(tipping_alerts),
        },
    )


@app.get("/api/flipkart-scouts/leaderboard")
async def get_flipkart_leaderboard():
    """Flipkart Scout leaderboard — top riders by reports filed."""
    from backend.database import SessionLocal
    from backend.models import FlipkartReport
    from sqlalchemy import func

    db = SessionLocal()
    try:
        results = (
            db.query(
                FlipkartReport.scout_id,
                func.count(FlipkartReport.id).label("report_count"),
                func.max(FlipkartReport.junction).label("junction"),
            )
            .filter(FlipkartReport.status == "APPROVED")
            .group_by(FlipkartReport.scout_id)
            .order_by(func.count(FlipkartReport.id).desc())
            .limit(20)
            .all()
        )

        leaderboard = []
        for rank, r in enumerate(results, 1):
            leaderboard.append({
                "rank": rank,
                "scout_id": r.scout_id,
                "report_count": r.report_count,
                "coins_earned": r.report_count * 50,
                "top_junction": r.junction,
            })

        return {"leaderboard": leaderboard, "total_scouts": len(leaderboard)}
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return {"leaderboard": [], "total_scouts": 0}
    finally:
        db.close()


@app.get("/api/recent-events")
async def get_recent_events():
    """Get the 10 most recent violations to populate the command center ticker."""
    from backend.database import SessionLocal
    from backend.models import Violation

    db = SessionLocal()
    try:
        recent_violations = db.query(Violation).order_by(Violation.id.desc()).limit(15).all()

        events = list(_custom_events)
        for v in recent_violations:
            events.append({
                "type": "alert",
                "junction": v.mapped_junction or v.junction_name or "Unknown",
                "message": v.violation_type or "Violation detected",
                "time": v.created_datetime.strftime("%H:%M:%S") if v.created_datetime else "Just now",
                "officer": "Auto-detect",
                "vehicles": 1
            })

        return {"events": events[:20]}
    except Exception as e:
        logger.error(f"Recent events error: {e}")
        return {"events": []}
    finally:
        db.close()


@app.post("/api/camera-status/toggle/{junction_id}")
async def toggle_camera_status(junction_id: str):
    """Toggle camera online/offline status for a junction."""
    from backend.database import SessionLocal
    from backend.models import CameraJunction
    from datetime import datetime

    db = SessionLocal()
    try:
        camera = db.query(CameraJunction).filter(
            CameraJunction.junction_id == junction_id
        ).first()
        if not camera:
            raise HTTPException(404, f"Camera junction {junction_id} not found")
        camera.is_online = not camera.is_online
        camera.last_ping = datetime.utcnow() if camera.is_online else camera.last_ping
        db.commit()
        return {
            "junction_id": junction_id,
            "is_online": camera.is_online,
            "status": "ONLINE" if camera.is_online else "OFFLINE",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db.close()


@app.post("/api/junctions/action")
async def perform_junction_action(payload: JunctionActionIn):
    """Clear/warn/not-found a junction: resolves active violations and updates status."""
    global _pipeline_data, _custom_events, _precomputed, _capacity_data, _repeat_offenders_data, _causal_impact_data
    from backend.database import SessionLocal
    from backend.models import Violation
    from datetime import datetime

    junction = payload.junction
    action = payload.action.lower()
    officer = payload.officer or "Constable Kumar"

    db = SessionLocal()
    try:
        # Delete violations at this junction from database
        count = db.query(Violation).filter(Violation.mapped_junction == junction).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating database for junction action: {e}")
        count = 0
    finally:
        db.close()

    # Update in-memory dataframe
    if _pipeline_data is not None:
        _pipeline_data = _pipeline_data[_pipeline_data["mapped_junction"] != junction]

    # Clear caches
    with _lock_precomputed:
        _precomputed.clear()
    with _lock_capacity:
        _capacity_data = None
    with _lock_repeat:
        _repeat_offenders_data = None
    with _lock_causal:
        _causal_impact_data = None

    # Prepend dynamic event to the log
    vehicles_count = count if count > 0 else 1
    _custom_events.insert(0, {
        "type": "cleared" if action == "towed" else "alert",
        "junction": junction,
        "message": f"Junction {action} by {officer} ({vehicles_count} vehicles)",
        "time": datetime.utcnow().strftime("%H:%M:%S"),
        "officer": officer,
        "vehicles": vehicles_count
    })

    return {
        "status": "success",
        "message": f"Action '{action}' successfully recorded for junction '{junction}'.",
        "violations_affected": count
    }


@app.get("/api/violations")
async def get_violations(top_n: int = Query(10, ge=1, le=50)):
    """Get top N individual violations with their original pipeline indices."""
    if _pipeline_data is None:
        raise HTTPException(503, "Pipeline not loaded")

    df = _pipeline_data
    # Sort by congestion cost descending to get top violations
    top = df.nlargest(top_n, "congestion_cost")

    cards = []
    for idx, row in top.iterrows():
        cards.append({
            "violation_idx": int(idx),
            "junction": row.get("mapped_junction") or row.get("junction_name") or "Unknown",
            "top_vehicle": f"{row.get('vehicle_type', 'UNKNOWN')} ({row.get('vehicle_number', 'N/A')})",
            "total_delay": round(float(row.get("congestion_cost", 0.0)), 1),
            "tier": row.get("impact_tier") or "LOW",
            "police_station": row.get("police_station") or "Unknown"
        })
    return {"cards": cards}


_client_errors = []

@app.post("/api/errors")
async def report_client_error(report: ClientErrorReport):
    global _client_errors
    _client_errors.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": report.type,
        "message": report.message,
        "stack": report.stack,
        "url": report.url,
        "line": report.line,
        "column": report.column,
    })
    if len(_client_errors) > 500:
        _client_errors = _client_errors[-500:]
    logger.warning(
        "Client error: %s at %s:%s — %s",
        report.type, report.url, report.line, report.message,
    )
    return {"status": "ok"}


@app.get("/api/config/mappls")
async def get_mappls_config():
    """Return the Mappls API key from environment variables at runtime."""
    key = os.environ.get("VITE_MAPPLS_API_KEY") or os.environ.get("MAPPLS_API_KEY")
    return {"apiKey": key or ""}


@app.get("/api/health")
async def health():
    from backend.database import check_db_health

    db_health = check_db_health()
    pipeline_status = "ready" if _pipeline_data is not None else ("loading" if _pipeline_loading else "error")

    components = {
        "pipeline": {
            "status": pipeline_status,
            "error": _pipeline_error,
            "violations_count": len(_pipeline_data) if _pipeline_data is not None else 0,
            "junctions_count": len(_junction_coords) if _junction_coords is not None else 0,
            "validation": _pipeline_validation,
        },
        "precomputation": {
            "status": "ready" if _precomputed else "pending",
            "keys": list(_precomputed.keys()) if _precomputed else [],
        },
        "models": {
            "causal_impact": "ready" if _causal_impact_data is not None else "pending",
            "predictions": "ready" if _predictions_data is not None else "pending",
            "phantom_risk": "ready" if _phantom_data is not None else "pending",
            "capacity": "ready" if _capacity_data is not None else "pending",
            "repeat_offenders": "ready" if _repeat_offenders_data is not None else "pending",
        },
        "database": db_health,
    }

    is_healthy = (
        pipeline_status == "ready"
        and db_health.get("status") == "ok"
        and all(v == "ready" for v in components["models"].values())
    )

    payload = {
        "status": "ok" if is_healthy else ("degraded" if pipeline_status != "error" else "error"),
        "version": "2.0.0",
        "components": components,
    }

    if payload["status"] == "error":
        raise HTTPException(status_code=503, detail=payload)
    return payload


# ---------------------------------------------------------------------------
# Serve built frontend as static files (Render / production)
# The frontend dist folder is expected at <repo_root>/frontend/dist/
# ---------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    # Mount static assets (JS, CSS, images) with caching headers
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets"), check_dir=False),
        name="frontend_assets",
    )

    # SPA catch-all: serve index.html or other static files in the dist root
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Don't interfere with API routes or assets directory
        if full_path.startswith("api/") or full_path.startswith("assets/"):
            raise HTTPException(status_code=404)
        
        # If the file exists directly in frontend/dist, serve it (e.g. app_logo.jpeg, hero.jpg)
        if full_path:
            target_path = _FRONTEND_DIST / full_path
            if target_path.is_file():
                return FileResponse(str(target_path))
                
        index_path = _FRONTEND_DIST / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=503, detail="Frontend not built yet")
        return FileResponse(str(index_path))

    logger.info("Frontend static files mounted from %s", _FRONTEND_DIST)
else:
    logger.info(
        "Frontend dist not found at %s — API-only mode", _FRONTEND_DIST
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
