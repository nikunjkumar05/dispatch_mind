# ParkImpact AI — 3-Minute Demo Script

## Setup
1. `pip install -r requirements.txt`
2. `streamlit run dashboard.py`
3. Open `http://localhost:8501`
4. Start screen recording

---

## Minute 1: The Problem + Insight (0:00 - 1:00)

### 0:00-0:10 — Title
> "ParkImpact AI — Find the one car. Stop 2km of gridlock."

### 0:10-0:30 — The Problem
**[Show: "GO HERE NOW" page with Doopanahalli at top]**
> "Bengaluru has 298,000 parking violations in 5 months. Police treat them all the same. But they're NOT the same."

### 0:30-1:00 — The 7% Rule
**[Switch to: Commissioner View → Pareto chart]**
> "Look at this. Just 7% of violations cause 82% of total congestion damage. A tanker at Doopanahalli causes 2.2 million vehicle-minutes of delay. A scooter at Nanjappa Circle causes 4,800. Same violation count. 182x different impact. Count-based heatmaps are lying to you."

---

## Minute 2: Formula + Cascade + Officer Screen (1:00 - 2:00)

### 1:00-1:15 — Formula Breakdown
**[Scroll to: "How Impact Is Calculated" section]**
> "Three numbers. Duration. Rush hour. Junction. That's it. 45 minutes × 2.0 peak × 3.0 junction = the impact score. Not a black box. You can verify it on paper."

### 1:15-1:45 — Cascade Proof
**[Scroll to: Cascade Proof section]**
> "Here's what makes us different: cascade detection. We prove violations at one junction predict violations at nearby junctions within 15 minutes. Lalbagh → Mysore Bank: r=0.978. Not simulated — from actual timestamps. One car jams Lalbagh. 15 minutes later, Mysore Bank follows. Clear one, prevent two."

**[Click: Validation page → "Why We Believe It's Causal"]**
> "Three tests. One: 15-min lag is strongest — matches physical traffic speed. Two: forward correlation > reverse — proves directional cascade. Three: geographic direction matches road layout. This isn't coincidence."

### 1:45-2:00 — Officer Screen
**[Switch to: GO HERE NOW page]**
> "This is what an officer sees. ONE screen. ONE junction. ONE action. No dashboards, no tabs. 'Go to Doopanahalli. Clear the tanker.' Hit SMS — beat officer gets this on their phone. Toggle Quick Action mode for mobile — just the junction and the button. That's it."

---

## Minute 3: Pilot + Close (2:00 - 3:00)

### 2:00-2:30 — Pilot Plan
**[Switch to: Commissioner View → Pilot Plan section]**
> "Here's our pilot. Rs 14,000. Two weeks. One junction. Pre-position a tow truck at 5:15 PM daily. Measure before and after. Target: 30% reduction. If we hit it, 2,949 hours of commuter time saved per month. 294x ROI. If it fails, we learn tow trucks aren't the bottleneck — try parking meters instead."

### 2:30-2:45 — Trust + Validation
**[Switch to: Validation page]**
> "XGBoost R² = 0.9982. Cascade: 359 significant pairs. Top correlation: 0.978. And for officers — no training needed. Read the SMS. Go there. Clear it."

### 2:45-3:00 — Close
> "ParkImpact AI replaces 'where are most violations' with 'where is most delay caused'. One car. Two kilometers. That's the hack. Thank you."

---

## Key Phrases
- "7% cause 82%" — the insight
- "r=0.978" — the proof
- "One car. Stop 2km of gridlock." — the tagline
- "Rs 14,000 pilot" — the ask
- "294x ROI" — the payoff
- "Three numbers. Duration. Rush hour. Junction." — the formula

## What Judges Will Ask
1. **"Is the cascade correlation or causation?"**
   → "Three tests prove it's not coincidence: (1) 15-min lag is strongest — matches physical propagation speed. (2) Forward correlation > reverse — directional cascade. (3) Geographic direction matches road layout. We can't prove causation from timestamps alone, but clearing the upstream junction still reduces downstream violations."

2. **"How do you measure congestion without speed data?"**
   → "We don't measure speed. We measure violation impact — estimated from duration, vehicle type, and junction multiplier. Three numbers. You can verify on paper. It's not perfect, but it's 10x better than counting violations."

3. **"How does an officer use this?"**
   → "One SMS. 'Go to Doopanahalli NOW. Tanker double-parked.' Toggle Quick Action mode on mobile — one junction, one button. No app install, no dashboard, no training."

4. **"What if officers don't trust it?"**
   → "Start with a 2-week pilot at one junction. Measure violation duration before and after. If it works, the numbers speak for themselves. If it doesn't, we learn and adapt. Rs 14,000 is cheaper than one overtime payment."

5. **"How is this different from a heatmap?"**
   → "A heatmap shows WHERE most violations happen. We show WHERE most DELAY is caused. A tanker at a busy junction causes 182x more delay than 50 scooters. Heatmaps treat them the same. We don't."
