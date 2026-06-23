"""DispatchMind CLI Demo — runs all modules, prints formatted output to stdout."""
import json, sys, time, textwrap, os
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SEP = "=" * 72
SUB = "-" * 72


def header(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def subheader(title: str):
    print(f"\n{SUB}")
    print(f"  {title}")
    print(SUB)


def metric(label: str, value, indent: int = 4):
    pad = " " * indent
    print(f"{pad}{label}: {value}")


def table(headers: list, rows: list, indent: int = 4):
    pad = " " * indent
    col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    fmt = pad + "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print(pad + "-" * (sum(col_widths) + 2 * (len(headers) - 1)))
    for r in rows:
        print(fmt.format(*[str(v) for v in r]))


def load_junction_coords(path: str = "data/external/junction_coords.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()

    print(f"{SEP}")
    print(f"  DISPATCHMIND — Intelligent Traffic Violation Management System")
    print(f"  CLI Demo")
    print(f"{SEP}")

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    header("1. Loading Data")
    # Use demo sample if available, otherwise fall back to env var or full parquet
    sample_path = "data/processed/demo_sample.parquet"
    data_path = sample_path if Path(sample_path).exists() else os.environ.get("DISPATCHMIND_CACHE", sample_path)
    coords_path = os.environ.get("DISPATCHMIND_COORDS", "data/external/junction_coords.json")

    if not Path(data_path).exists():
        print(f"  [ERROR] Data not found: {data_path}")
        sys.exit(1)

    print(f"  Loading: {data_path}")
    df = pd.read_parquet(data_path)
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")

    # Check if we have the required columns; if not, try the full pipeline
    junction_coords = load_junction_coords(coords_path) if Path(coords_path).exists() else {}
    print(f"  Junctions: {len(junction_coords)}")

    # Standardise date column
    if "created_datetime" not in df.columns and "created_date" in df.columns:
        df["created_datetime"] = pd.to_datetime(df["created_date"], errors="coerce")

    date_min = df["created_datetime"].min() if "created_datetime" in df.columns else "N/A"
    date_max = df["created_datetime"].max() if "created_datetime" in df.columns else "N/A"
    metric("Date range", f"{date_min} to {date_max}")
    metric("Violation types", df["violation_type"].nunique() if "violation_type" in df.columns else "N/A")
    metric("Junctions mapped", df["mapped_junction"].nunique() if "mapped_junction" in df.columns else "N/A")

    # ------------------------------------------------------------------
    # 2. Traffic Simulation (CTM)
    # ------------------------------------------------------------------
    header("2. Traffic Simulation (Cell-Transmission Model)")
    if "simulated_speed_kmh" not in df.columns and junction_coords:
        print("  Running CTM simulation...")
        try:
            from traffic_sim import add_simulated_speed_to_pipeline
            df = add_simulated_speed_to_pipeline(df, junction_coords)
            print("  [OK] CTM simulation complete")
        except Exception as e:
            print(f"  [SKIP] CTM error: {e}")
    else:
        print("  [OK] Simulated speeds already present")

    if "simulated_speed_kmh" in df.columns:
        speeds = df["simulated_speed_kmh"].dropna()
        metric("Mean speed", f"{speeds.mean():.1f} km/h")
        metric("Min speed", f"{speeds.min():.1f} km/h")
        metric("Max speed", f"{speeds.max():.1f} km/h")
        metric("Free-flow estimate", f"{np.percentile(speeds, 85):.1f} km/h (85th %ile)")

    # ------------------------------------------------------------------
    # 3. Congestion Cost & Economic Impact
    # ------------------------------------------------------------------
    header("3. Congestion Cost & Economic Impact")
    if "congestion_cost" in df.columns:
        metric("Mean congestion cost", f"{df['congestion_cost'].mean():.2f}")
        metric("Mean gridlock score", f"{df['gridlock_score'].mean():.2f}" if "gridlock_score" in df.columns else "N/A")
        metric("Total vehicles blocked", f"{df['vehicles_blocked_hr'].sum():.0f} veh·hr" if "vehicles_blocked_hr" in df.columns else "N/A")
        metric("Total delay", f"{df['delay_minutes_total'].sum():.0f} min" if "delay_minutes_total" in df.columns else "N/A")

        if "economic_loss_inr" in df.columns:
            total_loss = df["economic_loss_inr"].sum()
            metric("Total economic loss", f"₹{total_loss:,.0f}")
            metric("Total CO₂", f"{df['co2_kg'].sum():.1f} kg" if "co2_kg" in df.columns else "N/A")

        if "impact_tier" in df.columns:
            tiers = df["impact_tier"].value_counts()
            for tier, count in tiers.items():
                metric(f"  Tier {tier}", f"{count:,} violations ({count / len(df) * 100:.1f}%)")
    else:
        print("  [SKIP] Run congestion cost pipeline first")

    # ------------------------------------------------------------------
    # 4. Causal Impact Analysis
    # ------------------------------------------------------------------
    header("4. Causal Impact Analysis")
    if "simulated_speed_kmh" in df.columns:
        try:
            from causal_impact import run_causal_impact
            causal = run_causal_impact(df)
            if causal.get("model"):
                m = causal["model"]
                metric("R² score", f"{m.get('r2_score', 'N/A'):.4f}" if isinstance(m.get('r2_score'), (int, float)) else m.get('r2_score'))
                metric("MAE", f"{m.get('mae', 'N/A'):.2f}" if isinstance(m.get('mae'), (int, float)) else m.get('mae'))
                fi = m.get("feature_importance", {})
                if fi:
                    subheader("Top factors affecting speed:")
                    sorted_fi = sorted(fi.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
                    for feat, imp in sorted_fi:
                        metric(feat, f"{imp:.4f}")
            if causal.get("worst_junction"):
                metric("Worst junction", causal["worst_junction"])
        except Exception as e:
            print(f"  [SKIP] Causal impact error: {e}")
    else:
        print("  [SKIP] Run CTM simulation first")

    # ------------------------------------------------------------------
    # 5. GNN Cascade Prediction
    # ------------------------------------------------------------------
    header("5. GNN Cascade Prediction")
    try:
        if "congestion_cost" in df.columns and junction_coords:
            from gnn_cascade import run_gnn_cascade
            gnn = run_gnn_cascade(df, junction_coords)
            metric("Status", gnn.get("status", "N/A"))
            metric("Junctions", gnn.get("n_junctions", "N/A"))
            metric("AUC", f"{gnn.get('auc', 'N/A'):.4f}" if isinstance(gnn.get('auc'), (int, float)) else gnn.get('auc'))
            metric("Avg precision", f"{gnn.get('average_precision', 'N/A'):.4f}" if isinstance(gnn.get('average_precision'), (int, float)) else gnn.get('average_precision'))
            edges = gnn.get("edge_predictions", [])
            if edges:
                subheader("Top predicted cascade edges")
                table(["Junction A", "Junction B", "Probability"],
                      [(e.get("source", ""), e.get("target", ""), f"{e.get('probability', 0):.3f}") for e in edges[:8]])
        else:
            print("  [SKIP] Missing congestion_cost or junction_coords")
    except Exception as e:
        print(f"  [SKIP] GNN error: {e}")

    # ------------------------------------------------------------------
    # 6. Gridlock Propagation Index (GPI)
    # ------------------------------------------------------------------
    header("6. Gridlock Propagation Index (GPI)")
    try:
        if "congestion_cost" in df.columns:
            from capacity_loss import run_capacity_loss
            _, junction_stats, summary = run_capacity_loss(df)
            metric("Junctions analyzed", summary.get("n_junctions", "N/A"))
            metric("High risk (GPI ≥ 70)", summary.get("n_high_risk", "N/A"))
            metric("Critical (GPI ≥ 90)", summary.get("n_critical", "N/A"))

            if junction_stats is not None and len(junction_stats) > 0:
                subheader("Top 5 highest GPI junctions")
                top = junction_stats.sort_values("gpi_score", ascending=False).head(5)
                cols = [c for c in ["junction_name", "gpi_score", "capacity_loss_pct", "cascade_risk"] if c in top.columns]
                table(cols, [tuple(row[c] for c in cols) for _, row in top.iterrows()])
        else:
            print("  [SKIP] Missing congestion_cost")
    except Exception as e:
        print(f"  [SKIP] GPI error: {e}")

    # ------------------------------------------------------------------
    # 7. Dispatch Planning (VRP)
    # ------------------------------------------------------------------
    header("7. Dispatch Planning (VRP Routing)")
    try:
        if "congestion_cost" in df.columns and junction_coords:
            from dispatch import run_dispatch
            dispatch = run_dispatch(df, junction_coords, num_trucks=2)
            summary = dispatch.get("summary", {})
            metric("Routing method", summary.get("routing_method", "N/A"))
            metric("Total stops", summary.get("total_stops", "N/A"))
            metric("Total distance", f"{summary.get('total_distance_km', 'N/A')} km")
            routes = dispatch.get("routes", [])
            metric("Trucks", len(routes))
            responses = dispatch.get("responses", [])
            tier_counts = {}
            for r in responses:
                t = r.get("tier", "unknown")
                tier_counts[t] = tier_counts.get(t, 0) + 1
            if tier_counts:
                subheader("Response breakdown")
                for tier, n in tier_counts.items():
                    metric(f"  {tier}", n)
        else:
            print("  [SKIP] Missing congestion_cost or junction_coords")
    except Exception as e:
        print(f"  [SKIP] Dispatch error: {e}")

    # ------------------------------------------------------------------
    # 8. Flipkart Logistics Impact
    # ------------------------------------------------------------------
    header("8. Flipkart Logistics Impact")
    try:
        if "congestion_cost" in df.columns:
            from flipkart_logistics import run_flipkart_logistics
            flipkart = run_flipkart_logistics(df)
            impact = flipkart.get("impact", {})
            metric("Annual savings", f"₹{impact.get('annual_savings_inr', 0):,.0f}")
            metric("Hours saved", f"{impact.get('hours_saved', 0):.1f}")
            metric("Fuel saved", f"{impact.get('fuel_liters_saved', 0):.1f} L")
            metric("CO₂ reduced", f"{impact.get('co2_kg_reduced', 0):.1f} kg")
            metric("Clusters identified", flipkart.get("cluster_count", "N/A"))

            recs = flipkart.get("recommendations", [])
            if recs:
                subheader("Green zone recommendations")
                for r in recs[:4]:
                    print(f"      Zone {r.get('zone_id', '?')}: {r.get('location', '')} — {r.get('recommendation', '')}")
            patterns = flipkart.get("hourly_patterns", {})
            if patterns:
                subheader("Hourly delivery vehicle congestion")
                for h in sorted(patterns.keys(), key=int)[:8]:
                    metric(f"  Hour {h}", f"{patterns[h]} violations")
        else:
            print("  [SKIP] Missing congestion_cost")
    except Exception as e:
        print(f"  [SKIP] Flipkart error: {e}")

    # ------------------------------------------------------------------
    # 9. Repeat Offenders
    # ------------------------------------------------------------------
    header("9. Repeat Offenders")
    if "vehicle_number" in df.columns:
        repeats = df["vehicle_number"].value_counts()
        multi = repeats[repeats > 1]
        if len(multi) > 0:
            metric("Total vehicles with repeats", len(multi))
            metric("Max offences by one vehicle", multi.max())
            subheader("Top repeat offenders")
            top_multi = multi.head(8)
            for plate, cnt in top_multi.items():
                types = df[df["vehicle_number"] == plate]["violation_type"].unique()
                metric(f"  {plate}", f"{cnt} violations — {', '.join(types[:3])}")
        else:
            print("  No repeat offenders found")
    else:
        print("  [SKIP] Missing vehicle_number column")

    # ------------------------------------------------------------------
    # 10. Presence Probability (Bayesian)
    # ------------------------------------------------------------------
    header("10. Violation Presence Probability")
    try:
        if "created_datetime" in df.columns and "duration_minutes" in df.columns:
            from presence_model import compute_presence_series
            presences = compute_presence_series(df)
            metric("Mean presence probability", f"{presences.mean():.2f}")
            active = (presences > 0.3).sum()
            metric("Currently active (P > 0.3)", f"{active:,} ({active / len(df) * 100:.1f}%)")
            high = (presences > 0.7).sum()
            metric("High confidence (P > 0.7)", f"{high:,} ({high / len(df) * 100:.1f}%)")
        else:
            print("  [SKIP] Missing created_datetime or duration_minutes")
    except Exception as e:
        print(f"  [SKIP] Presence model error: {e}")

    # ------------------------------------------------------------------
    # 11. ML Prediction Models
    # ------------------------------------------------------------------
    header("11. ML Prediction Models (XGBoost / LightGBM)")
    try:
        if "congestion_cost" in df.columns:
            from prediction import run_prediction
            pred = run_prediction(df, output_dir="/tmp/dispatchmind_models")
            xgb_m = pred.get("xgb_metrics", {})
            lgb_m = pred.get("lgb_metrics", {})
            metric("XGBoost R²", f"{xgb_m.get('r2', 'N/A'):.4f}" if isinstance(xgb_m.get('r2'), (int, float)) else xgb_m.get('r2'))
            metric("XGBoost MAE", f"{xgb_m.get('mae', 'N/A'):.2f}" if isinstance(xgb_m.get('mae'), (int, float)) else xgb_m.get('mae'))
            metric("LightGBM R²", f"{lgb_m.get('r2', 'N/A'):.4f}" if isinstance(lgb_m.get('r2'), (int, float)) else lgb_m.get('r2'))
            metric("LightGBM MAE", f"{lgb_m.get('mae', 'N/A'):.2f}" if isinstance(lgb_m.get('mae'), (int, float)) else lgb_m.get('mae'))
            features = pred.get("features", [])
            if features:
                metric("Features used", len(features))
                print(f"      {', '.join(features[:8])}{'...' if len(features) > 8 else ''}")
        else:
            print("  [SKIP] Missing congestion_cost")
    except Exception as e:
        print(f"  [SKIP] Prediction error: {e}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - t0
    print(f"\n{SEP}")
    print(f"  DEMO COMPLETE")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Peak memory: (see Render dashboard)")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
