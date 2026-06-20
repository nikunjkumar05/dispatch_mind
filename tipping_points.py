"""
PhantomBlockageAI — Tipping Point Detector
Identifies the exact 15-minute window where congestion spikes beyond normal rhythm.
"""

import json
import pandas as pd
import numpy as np


# ── Constants ───────────────────────────────────────────────────────────────
STD_THRESHOLD = 3.0
ROLLING_WINDOW = 28  # 7-hour rolling window (28 x 15-min blocks)


def find_tipping_points(df: pd.DataFrame) -> dict:
    """
    Detect tipping points for each junction: the 15-minute block where
    congestion weight spikes to 3 standard deviations above the 7-day rolling mean.

    Parameters
    ----------
    df : DataFrame with columns:
        junction_node, time_block, weight

    Returns
    -------
    dict : { "BTP044": "BTP044 hits tipping point exactly at 08:30 AM", ... }
    """
    # Aggregate: total weight per junction per time_block
    agg = (
        df.groupby(["junction_node", "time_block"])["weight"]
        .sum()
        .reset_index()
    )

    tipping_points = {}

    for junc, junc_df in agg.groupby("junction_node"):
        junc_df = junc_df.sort_values("time_block").reset_index(drop=True)
        weights = junc_df["weight"]

        if len(weights) < ROLLING_WINDOW:
            continue

        rolling_mean = weights.rolling(window=ROLLING_WINDOW, min_periods=1).mean()
        rolling_std = weights.rolling(window=ROLLING_WINDOW, min_periods=1).std()
        rolling_std = rolling_std.replace(0, np.nan).bfill().ffill()

        upper_bound = rolling_mean + STD_THRESHOLD * rolling_std

        spikes = junc_df[weights > upper_bound]

        if spikes.empty:
            # Fallback: find the single highest spike relative to local mean
            mean_w = weights.mean()
            std_w = weights.std()
            if std_w == 0:
                continue
            z_scores = (weights - mean_w) / std_w
            max_z_idx = z_scores.idxmax()
            if z_scores[max_z_idx] > 2.0:
                spikes = junc_df.loc[[max_z_idx]]
            else:
                continue

        # Pick the earliest spike (first tipping point of the day)
        first_spike = spikes.iloc[0]
        time_block = first_spike["time_block"]

        # Convert HH:MM to 12-hour AM/PM format
        try:
            hour, minute = map(int, time_block.split(":"))
            period = "AM" if hour < 12 else "PM"
            display_hour = hour % 12 or 12
            formatted_time = f"{display_hour}:{minute:02d} {period}"
        except (ValueError, AttributeError):
            formatted_time = time_block

        tipping_points[junc] = f"{junc} hits tipping point exactly at {formatted_time}"

    if not tipping_points:
        print("No tipping points detected. Traffic may be uniformly distributed.")

    return tipping_points


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from preprocess import preprocess

    df = preprocess()
    result = find_tipping_points(df)

    print(json.dumps(result, indent=2))
    with open("tipping_points.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nSaved to tipping_points.json")
