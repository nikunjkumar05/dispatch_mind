# ParkIntel v2 — Congestion-First Predictive Parking Intelligence

**Date:** 2026-06-18
**Theme:** Poor Visibility on Parking-Induced Congestion
**Target Score:** 39/40
**Build:** Solo, 7 days

---

## One-Line Pitch

> "We score every parking violation by the ACTUAL DELAY it causes, predict where congestion will peak, dispatch tow trucks to highest-delay spots, AND recommend dynamic parking legalization — with SHAP explanations."

---

## Problem

Bengaluru parking enforcement suffers from three structural failures:
1. **Reactive patrol** — officers chase yesterday's tickets, not tomorrow's hotspots
2. **No congestion visibility** — violation counts treat dead-ends same as highway feeders
3. **No prioritization** — commanders get flat lists, not ranked impact stacks

---

## Data Facts

| Metric | Value |
|--------|-------|
| Total records | 298,450 |
| Parking violations only | 100% |
| Date range | Nov 2023 — Apr 2024 |
| Unique junctions | 169 |
| Police station zones | 54 |
| Vehicle types | 19 |
| Multi-offence records | 40,110 (13.4%) |
| Duration data | 100% NULL (must estimate) |

---

## Solution: ParkIntel v2 — 8 Modules

| # | Module | Source | Score Impact |
|---|--------|--------|--------------|
| 1 | Data Pipeline | All | Foundation |
| 2 | CongestionCost™ + JunctionGuard | CongestionCost + JunctionGuard | Innovation +3 |
| 3 | Prediction Engine | Tow-Route AI + PatrolGPT | Innovation +2 |
| 4 | Predictive Dispatch (Tow-Route AI) | Tow-Route AI + OR-tools | Relevance +2 |
| 5 | Dynamic Parking Legalization (CurbFlex) | CurbFlex | Innovation +2 |
| 6 | Explainability (SHAP) | Hotspot DNA | Innovation +1 |
| 7 | Validation Suite | All | Impact +2 |
| 8 | Streamlit Dashboard (10 tabs) | All | Impact +1 |

---

## Core Formula: CongestionCost™ + JunctionGuard

```
Delay = OccMins × (VehW/RoadW) × LaneBlock × Peak × JunctionPenalty × Severity
```

### JunctionGuard Enhancement
| Distance to Junction | Multiplier |
|---------------------|------------|
| 0-10m | 3.0x |
| 10-30m | 2.0x |
| 30-50m | 1.5x |
| >50m | 1.0x |

### Vehicle Size Weighting
| Vehicle Type | Multiplier |
|-------------|------------|
| Tanker/Bus/HGV | 2.5x |
| Car/Van/Tempo | 1.8x |
| Auto/Scooter/Motorcycle | 1.0x |

---

## What Competitors Do vs You

| Competitors | You |
|-------------|-----|
| Heatmap of violation counts | CongestionCost™ delay-weighted heatmap |
| "Send officers to hotspots" | "Send tow trucks to Safina Plaza, pre-positioned 30min before peak" |
| Reactive (after congestion) | Predictive (2-hour forecast before) |
| All violations equal | Gridlock Multiplier (junction × vehicle × road) |
| Just ticketing | Tiered response (alerts → marshals → tow trucks) |
| No root cause fix | Dynamic parking legalization for chronic zones |
| No explanation | SHAP explainability ("why here?") |
| No proof | ROI dashboard (travel time, fuel, complaints saved) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data | pandas, geopandas, numpy |
| GIS | osmnx, networkx |
| ML | xgboost, lightgbm, prophet, scikit-learn, shap |
| Routing | ortools |
| Dashboard | streamlit, pydeck, plotly |
| Validation | sklearn.metrics |
| Deployment | docker |

---

## 7-Day Build Sprint

| Day | Morning | Afternoon | Evening |
|-----|---------|-----------|---------|
| 1 | Data pipeline (JSON + timestamp + duration) | Severity + DMS + choke factor | Gridlock score + JunctionGuard |
| 2 | Traffic speed validation (Google Maps) | XGBoost + LightGBM training | Prophet per station |
| 3 | OR-tools VRP dispatch engine | Tiered response playbook | CurbFlex chronic zone detection |
| 4 | Streamlit dashboard (10 tabs) | Dual heatmap + temporal | Drill-down + CurbFlex tab |
| 5 | SHAP explainability | Backtest + speed correlation | Silk Board case study |
| 6 | Docker + API spec | Pilot proposal + ROI | Demo video script |
| 7 | Demo video recording | Buffer day | Submission upload |

---

## Demo Script (3 min)

1. **0:00-0:20** Hook: 298K violations → "Which cause actual congestion?"
2. **0:20-0:50** Problem: Count heatmap → red everywhere → useless
3. **0:50-1:30** CongestionCost™ + JunctionGuard: Toggle to delay-weighted → tanker=97, scooter=4
4. **1:30-2:00** Prediction: Tomorrow 6-8pm forecast
5. **2:00-2:20** Tow-Route AI: Pre-position tow trucks before peak
6. **2:20-2:40** CurbFlex: Chronic zone → paid parking recommendation
7. **2:40-2:55** SHAP: "+Metro exit 50m, +No legal parking"
8. **2:55-3:00** Close: "Enforce harm, not headcount. Fix root cause, not symptoms."
