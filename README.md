# DispatchMind

An AI system that helps Bengaluru Traffic Police find and fix traffic jams caused by illegal parking.

**Live Demo:** https://dispatchmind-production.up.railway.app/

---

## What Is This?

Bengaluru loses thousands of hours every day because illegal parking blocks roads and creates traffic jams. DispatchMind watches parking violations across the city, figures out which ones are causing the worst gridlock, and tells officers exactly where to send tow trucks.

Think of it as a **traffic doctor** — it diagnoses the problem, explains why it matters, and prescribes the fix.

---

## What Does It Do?

- **Watches cameras and reports** — collects parking violation data from traffic cameras and citizen reports
- **Ranks problem spots** — not all parking violations are equal. Some block a lane on a busy road during rush hour. Others are harmless. DispatchMind ranks them by actual impact
- **Predicts where jams will spread** — if one junction gets blocked, nearby junctions often follow. The system spots these patterns before they happen
- **Sends tow trucks efficiently** — calculates the best route for tow trucks to clear multiple violations in one trip
- **Builds court evidence** — automatically generates paperwork with the right legal sections for court cases
- **Learns from officers** — feedback from field officers improves the system over time

---

## Who Is It For?

| Role | What They See |
|---|---|
| **ACP (Command)** | Big-picture view of the whole city, strategic decisions |
| **Inspector** | Beat-level monitoring, performance tracking |
| **Constable (Field)** | Mobile-friendly view of priority violations near them |
| **Flipkart Scout** | Delivery partners report violations they spot while working |

---

## How It Works (Simple Version)

1. Parking violations come in from cameras, officers, and Flipkart delivery partners
2. The system calculates how much each violation blocks traffic (road width, time of day, nearby junctions)
3. AI models predict which violations will cause the biggest problems
4. Officers get a ranked list and optimized tow truck routes
5. Evidence packets are auto-generated for court

---

## Project Structure

```
dispatch_mind/
├── backend/          API server and database
├── src/              Analytics and prediction engine
├── frontend/         Web dashboard (20+ screens)
├── config/           Settings and thresholds
├── scripts/          Helper tools
└── Dockerfile        For deployment
```

---

## Getting Started

### Try It Online

Visit the live demo: https://dispatchmind-production.up.railway.app/

### Run It Locally

**Easy way (Windows):** Double-click `start.bat`

**Docker way:**
```bash
docker build -t dispatchmind .
docker run -p 8000:8000 --env-file .env dispatchmind
```

**Manual way:**
```bash
# Backend
pip install -r requirements.txt
uvicorn backend.api:app --reload --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

---

## Tech Details

<details>
<summary>Click to expand — for developers</summary>

### Tech Stack

| Layer | What We Used |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| ML/Analytics | XGBoost, LightGBM, SHAP, SciPy, Google OR-Tools |
| Frontend | React, Vite, Tailwind CSS, Leaflet maps |
| Database | SQLite (local), PostgreSQL (production) |
| Deployment | Docker, Railway, Render, Vercel |

### ML Pipeline (11 stages)

| Stage | What It Does |
|---|---|
| 1. Data Loading | Parses raw CSV/JSON, estimates violation duration |
| 2. Congestion Scoring | Calculates how much each violation blocks traffic |
| 3. Traffic Simulation | Physics-based model of traffic flow |
| 4. Prediction | ML models predict future congestion |
| 5. Dispatch Routing | Optimizes tow truck routes |
| 6. Zone Analysis | Finds chronic problem areas |
| 7. Spillover Detection | Spots hidden congestion from nearby landmarks |
| 8. Capacity Loss | Measures exact % of road capacity lost |
| 9. Explainability | Shows WHY a junction ranks high |
| 10. Causal Proof | Proves parking causes congestion (not just correlation) |
| 11. Evidence Generation | Builds court-ready documentation |

### Backend API

- Role-based authentication (ACP, Inspector, Constable, Scout)
- Rate limiting and request tracing
- Prometheus monitoring endpoint
- Real-time violation ingestion
- 30+ REST endpoints

### Frontend Pages

Dashboard, Map View, Priority Queue, Cascade Visualization, Dispatch Plan, Command Center, Early Warning, Inspector Dashboard, Capacity Board, Evidence View, Simulator, AI Copilot, Scout Leaderboard, and more.

### Database Tables

- `violations` — core records with impact scores
- `camera_junctions` — camera status tracking
- `flipkart_reports` — citizen/delivery partner reports
- `users` — multi-role accounts
- `user_sessions` — login sessions

### Environment Variables

Copy `.env.example` to `.env`. Works out of the box in Local Dispatch Mode (no API keys needed).

</details>

---

## Reset Before Demo

```bash
python scripts/reset_demo.py
```

Clears test data and resets cameras to a clean state.

---

## Built For

Gridlock 2.0 Hackathon — Bengaluru Traffic Police
