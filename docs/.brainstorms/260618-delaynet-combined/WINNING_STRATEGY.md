# ParkIntel v2 — The Absolute Winning Strategy

**Date:** 2026-06-18
**Theme:** Poor Visibility on Parking-Induced Congestion
**Target Score:** 39/40
**Build:** Solo, 7 days

---

## One-Line Pitch

> "We score every parking violation by the ACTUAL DELAY it causes to commuters, predict where congestion will peak in 2 hours, dispatch tow trucks to highest-delay spots first, AND recommend dynamic parking legalization for chronic zones — with SHAP explanations for every recommendation."

---

## What Makes This Win

| What Competitors Do | What You Do |
|---------------------|-------------|
| Heatmap of violation counts | CongestionCost™ delay-weighted heatmap |
| "Send officers to hotspots" | "Send 2 tow trucks to Safina Plaza, 5-7pm, pre-positioned" |
| Reactive (after congestion) | Predictive (2-hour forecast before congestion) |
| All violations equal | Gridlock Multiplier (junction × vehicle × road) |
| Just ticketing | Tiered response (alerts → marshals → officers → tow) |
| No root cause fix | Dynamic parking legalization for chronic zones |
| No explanation | SHAP explainability ("why here?") |
| No proof | ROI dashboard (travel time, fuel, complaints saved) |

---

## 6 Integrated Modules

### Module 1: CongestionCost™ Engine
**Source:** CongestionCost™ + JunctionGuard
```
Delay = OccMins × (VehW/RoadW) × LaneBlock × Peak × JunctionPenalty
```
- Gridlock Score (0-100): normalized congestion impact
- **JunctionGuard enhancement:** Junction proximity multiplier
  - 0-10m from junction: 3.0x multiplier
  - 10-30m from junction: 2.0x multiplier
  - 30-50m from junction: 1.5x multiplier
  - >50m from junction: 1.0x multiplier
- **Vehicle size weighting:**
  - Tanker/Bus/HGV: 2.5x (block turning radius)
  - Car/Van/Tempo: 1.8x
  - Auto/Scooter/Motorcycle: 1.0x

### Module 2: Prediction Engine
**Source:** Tow-Route AI + PatrolGPT
- XGBoost: violation probability per junction
- LightGBM: hex-level predictions
- Prophet: station-level hourly forecast
- **Output:** "Tomorrow 6-8pm, Safina Plaza expects 3× normal violations"

### Module 3: Predictive Dispatch Engine
**Source:** Tow-Route AI + OR-tools
- **Treat tow trucks like Uber drivers**
- OR-tools VRP with time windows
- Input: number of tow trucks, start point, shift hours
- Output: optimized GPS route with dwell times
- **Pre-positioning:** Deploy to high-risk junctions BEFORE congestion peaks
- Tiered Response Playbook:
  - 90 min: SMS alert to drivers (nearest parking)
  - 90 min: Community marshal alert (RWA/business)
  - 30 min: Pre-position tow truck at high-score junction
  - 15 min: Dispatch officer if high-impact parking remains

### Module 4: Dynamic Parking Legalization Engine
**Source:** CurbFlex
- **Chronic Violation Zone detection:** >50 violations/week at same location
- **Policy recommendations:**
  - "Convert 20m stretch to paid parking 11AM-8PM"
  - "Add 10 scooter bays here → 72% violation reduction"
  - "Install no-stopping sign 50m from junction approach"
- **Revenue projection:** Estimated parking revenue per zone
- **Infrastructure gap analysis:** Legal parking supply vs demand

### Module 5: Explainability Engine
**Source:** Hotspot DNA
- SHAP + environmental features
- "Why here? +Metro exit 50m, +No legal parking, +Restaurant cluster"
- **Intervention recommendations:** Auto-generated for each hotspot
- **Impact quantification:** "This violation caused 54.8 vehicle-minutes of delay to 47 vehicles"

### Module 6: Validation Suite
- Backtest (month 4 held-out) → R² ≥ 0.85
- Traffic speed correlation (DMS vs actual speed)
- Silk Board case study
- Synthetic validation (100 artificial violations)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PARKINTEL v2 — SYSTEM ARCHITECTURE               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DATA SOURCES                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐    │
│  │ BTP Violation  │  │ OSMnx Road     │  │ Google Maps/TomTom     │    │
│  │ CSV (298K rows)│  │ Graph          │  │ Traffic Speed (free)   │    │
│  └────────┬───────┘  └────────┬───────┘  └────────┬────────────────┘    │
│           │                   │                   │                      │
│           ▼                   ▼                   ▼                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 1: DATA PIPELINE                                         │   │
│  │  • JSON explosion (multi-offence records)                       │   │
│  │  • Timestamp parsing (ISO8601 mixed format)                     │   │
│  │  • Duration estimation (median per type × vehicle × hour)       │   │
│  │  • Severity classification (3-tier)                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 2: CONGESTIONCOST + JUNCTIONGUARD ENGINE                 │   │
│  │                                                                  │   │
│  │  Delay = OccMins × (VehW/RoadW) × LaneBlock × Peak × J_Penalty│   │
│  │                                                                  │   │
│  │  JunctionGuard:                                                 │   │
│  │  • 0-10m: 3.0x | 10-30m: 2.0x | 30-50m: 1.5x | >50m: 1.0x   │   │
│  │  • Tanker/Bus: 2.5x | Car: 1.8x | Scooter: 1.0x              │   │
│  │                                                                  │   │
│  │  + Gridlock Score (0-100)                                       │   │
│  │  + Traffic speed validation (Google Maps API)                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 3: PREDICTION ENGINE                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │
│  │  │ XGBoost      │  │ LightGBM     │  │ Prophet              │  │   │
│  │  │ (violation   │  │ (hex-level   │  │ (station-level       │  │   │
│  │  │  probability)│  │  prediction) │  │  hourly forecast)    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │
│  │                                                                  │   │
│  │  Output: "Tomorrow 6-8pm, Safina Plaza expects 3× normal"       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 4: PREDICTIVE DISPATCH ENGINE (Tow-Route AI)            │   │
│  │                                                                  │   │
│  │  OR-tools VRP with time windows                                 │   │
│  │  Input: tow trucks, start point, shift hours                    │   │
│  │  Output: optimized GPS route with dwell times                   │   │
│  │                                                                  │   │
│  │  Tiered Response Playbook:                                       │   │
│  │  • 90 min: SMS alert to drivers (nearest parking)              │   │
│  │  • 90 min: Community marshal alert (RWA/business)              │   │
│  │  • 30 min: Pre-position tow truck at high-score junction       │   │
│  │  • 15 min: Dispatch officer if high-impact parking remains     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 5: DYNAMIC PARKING LEGALIZATION (CurbFlex)              │   │
│  │                                                                  │   │
│  │  Chronic Violation Zone detection: >50 violations/week         │   │
│  │                                                                  │   │
│  │  Policy recommendations:                                        │   │
│  │  • "Convert 20m stretch to paid parking 11AM-8PM"             │   │
│  │  • "Add 10 scooter bays → 72% reduction"                      │   │
│  │  • "Install no-stopping sign 50m from junction"                │   │
│  │                                                                  │   │
│  │  Revenue projection: ₹X/month per zone                         │   │
│  │  Infrastructure gap: legal supply vs demand                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 6: EXPLAINABILITY ENGINE                                 │   │
│  │                                                                  │   │
│  │  SHAP + environmental features:                                 │   │
│  │  "Why here? +Metro exit 50m, +No legal parking, +Restaurant"   │   │
│  │                                                                  │   │
│  │  + Impact quantification:                                        │   │
│  │    "This violation caused 54.8 vehicle-minutes to 47 vehicles" │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 7: VALIDATION                                            │   │
│  │                                                                  │   │
│  │  • Backtest (month 4 held-out) → R² ≥ 0.85                     │   │
│  │  • Traffic speed correlation (DMS vs actual speed)              │   │
│  │  • Silk Board case study                                        │   │
│  │  • Synthetic validation                                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 8: STREAMLIT DASHBOARD (10 Tabs)                         │   │
│  │                                                                  │   │
│  │  1. Dual Heatmap (count vs delay-weighted)                      │   │
│  │  2. Junction Rankings (top-20 by delay)                         │   │
│  │  3. Zone Map (police station view)                              │   │
│  │  4. Temporal (hourly prediction clock)                          │   │
│  │  5. Drill-Down (click violation → delay breakdown)              │   │
│  │  6. Dispatch (tow truck shift planner with OR-tools route)      │   │
│  │  7. CurbFlex (chronic zones → policy recommendations)           │   │
│  │  8. Explainability (SHAP waterfall per hotspot)                 │   │
│  │  9. ROI Dashboard (travel time, fuel, complaints saved)         │   │
│  │ 10. Reports (exportable patrol brief PDF)                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Scoring Target

| Criterion | Score | How |
|-----------|-------|-----|
| Innovation | 10/10 | CongestionCost™ + JunctionGuard + CurbFlex + Tiered Response + SHAP |
| Feasibility | 9/10 | Standard Python + Streamlit + OSMnx + OR-tools + Docker |
| Relevance | 10/10 | 1:1 theme mapping: detect → quantify → enforce → fix root cause |
| Impact | 10/10 | Backtest + speed validation + prescriptive dispatch + policy recommendations |
| **Total** | **39/40** | |

---

## 3-Minute Demo Script

**0:00-0:20 — Hook**
> "298,450 parking violations. Every dashboard shows a red heatmap. But which violations actually CAUSE congestion?"

**0:20-0:50 — Problem**
> "Show count heatmap. Red everywhere. 'Everything is priority means nothing is priority.'"

**0:50-1:30 — CongestionCost™ + JunctionGuard Reveal**
> "Toggle to delay-weighted heatmap. Most of city goes grey. 8 zones blaze red. These 8 cause 60% of all parking-induced delay. A tanker 10m from Upparpet junction: 97/100 Gridlock Score. A scooter on a side street: 4/100. 24x difference."

**1:30-2:00 — Prediction**
> "Tomorrow 6-8pm, Safina Plaza expects 3× normal violations. Here's the predicted heatmap."

**2:00-2:20 — Tow-Route AI Dispatch**
> "Tow truck shift planner: 2 trucks, start Koramangala, 4-hour shift. OR-tools route: Safina Plaza (5-6pm) → KR Market (6-7pm) → Elite Junction (7-8pm). Pre-positioned BEFORE congestion peaks."

**2:20-2:40 — CurbFlex Root Cause**
> "Chronic zone detected: 18th Main Koramangala, 120 violations/week. Recommendation: Convert 20m stretch to paid parking 11AM-8PM. Estimated revenue: ₹45,000/month. Add 10 scooter bays → 72% violation reduction."

**2:40-2:55 — Explainability**
> "Click Safina Plaza tanker. SHAP explanation: +Metro exit 50m (+32), +No legal parking (+28), +Rush hour (+15). Intervention: Add parking bay within 200m of metro exit."

**2:55-3:00 — Close**
> "Same data. Same tow trucks. 5× the impact. **Enforce harm, not headcount. Fix root cause, not symptoms.**"
