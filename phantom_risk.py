"""
PhantomBlockageAI — Phantom Risk Score Calculator
Predicts congestion 15 minutes before blockage using parking violation logs.
"""

import math
import pandas as pd
import numpy as np


# ── Constants ───────────────────────────────────────────────────────────────
EARTH_RADIUS_M = 6_371_000  # meters
FEEDER_RADIUS_M = 500       # feeder must be within this distance of a seed


# ── Haversine ───────────────────────────────────────────────────────────────
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two lat/lon points."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


# ── Core risk score ─────────────────────────────────────────────────────────
def calculate_phantom_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Phantom Risk Score for every Feeder Node in each time_block.

    Parameters
    ----------
    df : DataFrame with columns:
        latitude, longitude, vehicle_type, weight,
        junction_node, time_block

    Returns
    -------
    DataFrame sorted by phantom_risk_score descending (Feeder Nodes only).
    """
    seed_mask = df["junction_node"] != "FEEDER"
    seeds = df[seed_mask].copy()
    feeders = df[~seed_mask].copy()

    # Pre-index seeds by time_block for fast lookup
    seed_by_block = {
        tb: group for tb, group in seeds.groupby("time_block")
    }

    results = []

    for tb, feeder_group in feeders.groupby("time_block"):
        if tb not in seed_by_block:
            continue

        seed_group = seed_by_block[tb]
        if seed_group.empty or feeder_group.empty:
            continue

        # For each feeder, find seeds within FEEDER_RADIUS_M
        for f_idx, f_row in feeder_group.iterrows():
            f_lat, f_lon = f_row["latitude"], f_row["longitude"]

            nearby_distances = []
            for s_idx, s_row in seed_group.iterrows():
                dist = haversine(f_lat, f_lon, s_row["latitude"], s_row["longitude"])
                if dist <= FEEDER_RADIUS_M:
                    nearby_distances.append(dist)

            if not nearby_distances:
                continue

            avg_dist = np.mean(nearby_distances)
            seed_count = len(nearby_distances)
            vehicle_weight = f_row["weight"]

            risk_score = (avg_dist / seed_count) * vehicle_weight

            results.append({
                "time_block": tb,
                "latitude": f_lat,
                "longitude": f_lon,
                "vehicle_type": f_row["vehicle_type"],
                "weight": vehicle_weight,
                "junction_node": f_row["junction_node"],
                "nearby_seed_count": seed_count,
                "avg_distance_to_seeds": round(avg_dist, 2),
                "phantom_risk_score": round(risk_score, 2),
            })

    if not results:
        print("No Feeder Nodes found near active Seeds. Nothing to score.")
        return pd.DataFrame()

    risk_df = pd.DataFrame(results)
    risk_df = risk_df.sort_values("phantom_risk_score", ascending=False).reset_index(drop=True)

    n_feeder = len(risk_df)
    n_blocks = risk_df["time_block"].nunique()
    print(f"Scored {n_feeder:,} Feeder Nodes across {n_blocks} time blocks")

    return risk_df


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from preprocess import preprocess

    df = preprocess()
    risk_df = calculate_phantom_risk_score(df)

    if not risk_df.empty:
        print(f"\nTop 10 Phantom Blockage Risks:")
        print(risk_df.head(10).to_string(index=False))
        risk_df.to_parquet("phantom_risk_scores.parquet", index=False)
        print(f"\nSaved to phantom_risk_scores.parquet")
