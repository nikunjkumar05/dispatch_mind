"""
Stage 6: AI Spillover Detection — DBSCAN clustering of metro/commercial parking spillover.

Identifies "Hidden Hotspots" where spillover parking from metro stations, malls,
hospitals, stadiums, and tech parks creates congestion not captured by junction-based analysis.
"""

from typing import Dict, List, Any
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_value

_SPILLOVER_KEYWORDS: List[str] = [
    "metro", "mall", "hospital", "stadium", "park", "market", "tech",
]

_LABEL_MAP: Dict[str, str] = {
    "metro": "Metro Spillover",
    "mall": "Mall Spillover",
    "hospital": "Hospital Spillover",
    "stadium": "Stadium Spillover",
    "park": "Park Spillover",
    "market": "Market Spillover",
    "tech": "Tech Park Spillover",
}


def _location_matches_keyword(location: str, keyword: str) -> bool:
    return keyword in location.lower()


def _filter_spillover_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """NLP Filter: keep rows whose location contains a spillover keyword."""
    loc = df["location"].fillna("").str.lower()
    mask = pd.Series(False, index=df.index)
    for kw in _SPILLOVER_KEYWORDS:
        mask |= loc.str.contains(kw, regex=False)
    return df[mask].copy()


def _detect_clusters(
    coords: np.ndarray, eps: float = 0.002, min_samples: int = 5
) -> np.ndarray:
    """DBSCAN clustering on lat/lon. Returns cluster labels per point."""
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean")
    return clustering.fit_predict(coords)


def _dominant_keyword(locations: pd.Series) -> str:
    """Return the keyword that appears most often across the cluster's location strings."""
    keyword_counts: Dict[str, int] = {kw: 0 for kw in _SPILLOVER_KEYWORDS}
    for loc in locations:
        if pd.isna(loc):
            continue
        loc_lower = loc.lower()
        for kw in _SPILLOVER_KEYWORDS:
            if kw in loc_lower:
                keyword_counts[kw] += 1
    if not any(keyword_counts.values()):
        return "unknown"
    return max(keyword_counts, key=keyword_counts.get)


def detect_spillover_zones(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect hidden spillover hotspots using NLP filtering + DBSCAN clustering.

    Args:
        df: Processed violations DataFrame (must contain columns:
            latitude, longitude, location, vehicle_type).

    Returns:
        List of dicts, one per detected cluster::

            [
                {
                    "cluster_id": 0,
                    "label": "Metro Spillover",
                    "center_lat": 12.9721,
                    "center_lon": 77.5946,
                    "severity": 42.5,
                    "vehicle_count": 12,
                },
                ...
            ]
    """
    required_cols = {"latitude", "longitude", "location", "vehicle_type"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    # Step 1: NLP filter
    candidates = _filter_spillover_candidates(df)
    if candidates.empty:
        return []

    coords = candidates[["latitude", "longitude"]].to_numpy()

    # Step 2: DBSCAN clustering
    eps = get_config_value("spillover", "dbscan_eps", 0.002)
    min_samples = get_config_value("spillover", "dbscan_min_samples", 5)
    labels = _detect_clusters(coords, eps=eps, min_samples=min_samples)

    candidates = candidates.copy()
    candidates["cluster_id"] = labels

    # Step 3: Zone generation — skip noise (cluster_id == -1)
    zones: List[Dict[str, Any]] = []
    for cid in sorted(candidates["cluster_id"].unique()):
        if cid == -1:
            continue

        cluster = candidates[candidates["cluster_id"] == cid]

        center_lat = float(cluster["latitude"].mean())
        center_lon = float(cluster["longitude"].mean())

        keyword = _dominant_keyword(cluster["location"])
        label = _LABEL_MAP.get(keyword, f"{keyword.title()} Spillover")

        weight_map = get_config_value("formula", "congestion", {}).get("vehicle_size_mult", {})
        severity = float(cluster["vehicle_type"].map(weight_map).fillna(1.0).sum() * 1.5)

        zones.append(
            {
                "cluster_id": int(cid),
                "label": label,
                "center_lat": round(center_lat, 6),
                "center_lon": round(center_lon, 6),
                "severity": round(severity, 2),
                "vehicle_count": int(len(cluster)),
            }
        )

    zones.sort(key=lambda z: z["severity"], reverse=True)
    return zones
