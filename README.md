# DispatchMind

AI-powered traffic enforcement intelligence system for the Bengaluru Traffic Police (BTP). Shifts the paradigm from counting cars to measuring **road capacity loss** caused by illegal parking violations. Developed for the Gridlock 2.0 Hackathon.

---

## Architecture

```
dispatch_mind/
├── backend/              FastAPI REST API + SQLAlchemy ORM
├── src/                  ML pipeline (11 stages)
├── frontend/             React + Vite + Tailwind (20+ pages)
├── config/app.json       Master configuration (formulas, thresholds, zones)
├── data/                 Raw + processed datasets (Parquet)
├── outputs/models/       Trained XGBoost/LightGBM models
├── alembic/              Database migrations
├── pwa/                  Progressive Web App shell
├── scripts/              Utility and testing scripts
├── Dockerfile            Multi-stage production build
└── docker-compose.yml    Local dev orchestration
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic |
| **ML / Analytics** | XGBoost, LightGBM, Scikit-learn, SHAP, SciPy, OR-Tools, Statsmodels |
| **Frontend** | React 18, Vite 5, Tailwind CSS 3, Leaflet / Mappls, React Router v6 |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Infrastructure** | Docker, Docker Compose, Render.com, Railway, Vercel |
| **Monitoring** | Prometheus metrics, request tracing, graceful degradation |

---

## Multi-Stage ML Pipeline

The core analytics engine in `src/` runs 11 sequential stages:

| Stage | Module | Description |
|---|---|---|
| 1 | `data_pipeline.py` | Loads CSV, parses nested JSON violations (3-tier fallback), estimates duration, maps to junctions |
| 2 | `congestion_cost.py` | KDTree spatial density, multi-factor congestion scoring: `duration x lane_block x peak x junction_mult x vehicle_mult x severity x density_mult` |
| 2b | `traffic_sim.py` | Cell Transmission Model (Greenshields + CTM) for physics-based traffic flow simulation |
| 3 | `prediction.py` | XGBoost + LightGBM regressors with cyclical temporal features (sin/cos hour/day encoding) |
| 4 | `dispatch.py` | Google OR-Tools VRP solver for tow truck route optimization with capacity-aware priority ranking |
| 5 | `curbflex.py` | Chronic zone detection, parking policy recommendations, enforcement equity analysis |
| 6 | `spillover_ai.py` | DBSCAN clustering + NLP filtering for hidden congestion hotspots (metro stations, malls, hospitals) |
| 7 | `capacity_loss.py` | Core innovation — quantifies exact % of road capacity lost. GREEN/YELLOW/RED status + Gridlock Propagation Index (GPI) |
| 7b | `shap_explain.py` | SHAP value analysis explaining WHY junctions have high impact, generates intervention recommendations |
| 8 | `causal_impact.py` | Regression proving parking -> congestion causation using CTM-simulated speed (avoids circular reasoning) |
| 9 | `evidence_packet.py` | Auto-generates court-ready challan evidence packets with MV Act sections, impact evidence, and hashes |
| 10 | `flipkart_logistics.py` | Delivery vehicle hotspot clustering + dynamic loading bay recommendations |
| 11 | `degradation.py` | Graceful fallback for camera offline, low bandwidth, model uncertainty, two-wheeler footpath detection |

---

## Advanced Analytics

- **Cascade Detection** (`cascade.py`) — Historical lag correlation showing spatial-temporal violation propagation between junctions.
- **Enhanced Cascade** (`enhanced_cascade.py`) — Granger causality testing + directional asymmetry + confounder control.
- **GNN Cascade Predictor** (`gnn_cascade.py`) — Pure NumPy 2-layer message-passing Graph Neural Network (no PyTorch/TensorFlow dependency) predicting cascade edges between junctions.
- **Anomaly Detection** (`anomaly_detection.py`) — Isolation Forest for unsupervised detection of unusual violation patterns.
- **Phantom Blockage Risk** (`phantom_risk.py`) — Predicts congestion 15 minutes before blockage using feeder-seed proximity analysis.
- **Tipping Points** (`tipping_points.py`) — 3-sigma statistical spike detection above rolling mean.
- **Presence Model** (`presence_model.py`) — Bayesian logistic decay estimating whether a reported violation is still physically present.

---

## Backend API

FastAPI server (`backend/api.py`, ~1900 lines) with:

- **Auth**: Token-based sessions, role-based access (ACP, SI, Constable, Scout)
- **Rate Limiting**: Sliding-window in-memory limiter (120 req/min/IP)
- **Request Tracing**: Unique request IDs on every request
- **Prometheus**: `/metrics` endpoint for monitoring
- **CORS**: Configurable allowed origins
- **Background Warm-up**: Pipeline components load asynchronously on startup
- **Thread-Safe Lazy Loading**: Each pipeline stage uses its own lock

### Key Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/login` | Authentication |
| `GET /api/health` | Health check |
| `GET /api/overview` | Dashboard overview |
| `GET /api/priority-junctions` | Priority-ranked junctions |
| `GET /api/cascade-data` | Cascade detection results |
| `GET /api/dispatch-plan` | Tow truck routing plan |
| `GET /api/phantom-risk` | Phantom blockage risk zones |
| `GET /api/causal-impact` | Causal impact analysis |
| `GET /api/capacity-status` | Road capacity loss dashboard |
| `POST /api/violations` | Real-time violation ingestion |
| `POST /api/flipkart-scouts/report` | Scout crowdsource reports |
| `GET /api/command/*` | ACP Command Center endpoints |
| `GET /api/inspector/*` | Inspector dashboard endpoints |

---

## Frontend Pages

20+ role-specific views:

| Page | File | Purpose |
|---|---|---|
| Login | `Login.jsx` | Role-based authentication |
| Overview | `Overview.jsx` | Executive dashboard with key metrics |
| Map View | `MapView.jsx` | Interactive Leaflet/Mappls map |
| Priority Queue | `PriorityQueue.jsx` | Ranked junctions by congestion impact |
| Cascade | `Cascade.jsx` | Spatial-temporal cascade visualization |
| Dispatch | `Dispatch.jsx` | Tow truck routing plan |
| Command Center | `CommandCenter.jsx` | ACP-level strategic view |
| Early Warning | `EarlyWarningPanel.jsx` | Predictive warning system |
| Inspector Dashboard | `InspectorDashboard.jsx` | SI-level monitoring |
| Live Capacity Board | `LiveCapacityBoard.jsx` | Real-time capacity status |
| Evidence View | `EvidenceView.jsx` | Court-ready evidence packets |
| Simulator | `Simulator.jsx` | What-if scenario testing |
| AI Copilot | `AICopilot.jsx` | LLM-powered natural language assistant |
| Flipkart Scout | `FlipkartScout.jsx` | Crowdsourcing interface |
| Scout Leaderboard | `ScoutLeaderboard.jsx` | Community engagement rankings |

---

## Data Model

Five SQLAlchemy tables in `backend/models.py`:

| Table | Description |
|---|---|
| `violations` | Core records with computed metrics (congestion_cost, gridlock_score, impact_tier, economic_loss, CO2) |
| `camera_junctions` | Camera status tracking per junction (online/offline) |
| `flipkart_reports` | Crowdsourced reports from Flipkart Scout delivery partners |
| `users` | Multi-role users with hashed passwords |
| `user_sessions` | Token-based session management with expiry |

---

## Quick Start

### Option 1: One-Click (Windows)

Double-click `start.bat`. Installs dependencies, boots FastAPI on `:8000`, starts Vite on `:3000`.

### Option 2: Docker

```bash
docker build -t dispatchmind .
docker run -p 8000:8000 --env-file .env dispatchmind
```

Access at `http://localhost:8000`.

### Option 3: Manual Development

**Terminal 1 — Backend:**
```bash
pip install -r requirements.txt
uvicorn backend.api:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Access at `http://localhost:3000` (Vite proxies `/api` to `:8000`).

---

## Pre-Pitch Reset

```bash
python scripts/reset_demo.py
```

Clears test reports and resets offline cameras to a clean state.

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Purpose |
|---|---|
| `ZENMUX_API_KEY` | LLM API key for AI Copilot |
| `DATABASE_URL` | PostgreSQL connection string (prod) |
| `TWILIO_*` | SMS/WhatsApp webhook credentials |
| `CORS_ORIGINS` | Allowed frontend origins |
| `MAPPLS_API_KEY` | Map provider API key |

System runs in **Local Dispatch Mode** by default (no external API keys required).

---

## Deployment

| Platform | Config | Notes |
|---|---|---|
| **Docker** | `Dockerfile`, `docker-compose.yml` | Multi-stage: Python backend + Node.js frontend in single container |
| **Render** | `render.yaml` | Blueprint deployment (Singapore, free tier, PostgreSQL) |
| **Railway** | `railway.toml` | Production Docker target |
| **Vercel** | `frontend/vercel.json` | SPA rewrite rules for frontend-only deploy |

---

## Notable Technical Highlights

1. **Pure NumPy GNN** — Complete 2-layer message-passing Graph Neural Network with manual backpropagation, no PyTorch/TensorFlow dependency.
2. **Physics-Based Traffic Simulation** — Cell Transmission Model based on Greenshields fundamental diagram.
3. **Zero-Circular-Reasoning Design** — Causal impact engine uses CTM-simulated speed as target variable, not formula-based scores.
4. **Presence Probability Model** — Bayesian logistic decay filters out resolved violations to prevent wasted dispatch.
5. **Bengaluru-Specific Intelligence** — Config includes metro construction zones (Silk Board, KR Puram), IT corridor timing, narrow road zones, commercial spillover hotspots.
6. **Full PWA Support** — Service worker, manifest, offline capability for field officers.
7. **Dual Deployment** — Single-container production (Docker multi-stage) and separate-service development (Docker Compose).
