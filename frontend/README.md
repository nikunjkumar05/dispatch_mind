# DispatchMind v2.0 — React + FastAPI

## Architecture

```
frontend/          → React + Vite + Tailwind (port 3000)
  src/
    pages/         → 7 views (Overview, Priority Queue, Map, Cascade, Dispatch, Alerts, Offenders)
    components/    → Reusable UI components
    utils/         → API hooks, formatters
  tailwind.config.js → Dark theme for BTP officers

backend/           → FastAPI REST API (port 8000)
  api.py           → 10 endpoints serving ML pipeline

src/               → ML Pipeline (unchanged)
  data_pipeline.py → Stage 1: Data cleaning
  congestion_cost.py → Stage 2: CII scoring
  prediction.py    → Stage 3: XGBoost/LightGBM
  cascade.py       → Stage 4: Lag correlation
  dispatch.py      → Stage 5: VRP routing
  curbflex.py      → Stage 6: Chronic zone detection
  realtime_alerts.py → Alert generation
```

## Quick Start

### 1. Install Backend Dependencies
```bash
pip install fastapi uvicorn
```

### 2. Install Frontend Dependencies
```bash
cd frontend
npm install
```

### 3. Start Backend (Terminal 1)
```bash
cd C:\Users\sange\traffic_prediction
python -m uvicorn backend.api:app --reload --port 8000
```

### 4. Start Frontend (Terminal 2)
```bash
cd C:\Users\sange\traffic_prediction\frontend
npm run dev
```

### 5. Open Browser
```
http://localhost:3000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/overview` | GET | City-level summary stats |
| `/api/stations` | GET | All police stations |
| `/api/priority-queue/{station}` | GET | Top N violations for station |
| `/api/map-data` | GET | Coordinates for map rendering |
| `/api/cascade` | GET | Cascade correlation pairs |
| `/api/curbflex` | GET | Chronic zones + policy recs |
| `/api/dispatch?num_trucks=2` | GET | VRP tow truck routes |
| `/api/alerts?count=10` | GET | Generated alerts |
| `/api/repeat-offenders` | GET | Serial blocker vehicles |
| `/api/pareto` | GET | Pareto analysis data |
| `/api/health` | GET | API health check |

## Role-Based Views

- **Constable**: Priority queue + map + dispatch
- **Sub-Inspector**: Station-wide stats + alerts
- **ACP/Commissioner**: Strategy view + cascade + offenders

## Design Principles

1. **Dark theme** — for night shifts
2. **Mobile-first** — constables use phones
3. **No external APIs** — all data from dataset
4. **Human-in-the-loop** — AI recommends, officer decides
