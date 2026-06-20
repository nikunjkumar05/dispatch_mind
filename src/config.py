"""
Configuration management for DispatchMind / ParkImpact AI.

This module provides a single source of truth for all configuration,
making the system city-agnostic, testable, and maintainable.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_PATH = Path(__file__).parent.parent / "config" / "app.json"

# Global config cache — read once, use everywhere
_CONFIG_CACHE = None


def _load_config_from_disk() -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def get_config() -> Dict[str, Any]:
    """Get global config cache. Reads file once, then returns cached dict."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = _load_config_from_disk()
    return _CONFIG_CACHE


def reset_config_cache() -> None:
    """Reset config cache (useful for testing)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None


# Keep load_config as alias for backward compat
def load_config() -> Dict[str, Any]:
    return get_config()


def get_config_value(section: str, key: str, default: Any = None) -> Any:
    config = get_config()
    return config.get(section, {}).get(key, default)


def get_duration_base_by_type(violation_type: str) -> float:
    base_by_type = get_config()['formula']['duration']['base_by_type']
    return base_by_type.get(violation_type, 35.0)


def get_vehicle_adjustment(vehicle_type: str) -> float:
    vehicle_adjustment = get_config()['formula']['duration']['vehicle_adjustment']
    return vehicle_adjustment.get(vehicle_type, 1.0)


def get_vehicle_size_mult(vehicle_type: str) -> float:
    vehicle_size_mult = get_config()['formula']['congestion']['vehicle_size_mult']
    return vehicle_size_mult.get(vehicle_type, 1.0)


def get_junction_distance_threshold(tier: str) -> float:
    thresholds = get_config()['formula']['congestion']['junction_distance']
    return thresholds.get(tier, 50.0)


def get_temporal_factors(hour: int) -> Dict[str, float]:
    temporal = get_config()['model']['temporal']
    if (temporal['morning_start'] <= hour <= temporal['morning_end']) or \
       (temporal['evening_start'] <= hour <= temporal['evening_end']):
        return {'multiplier': temporal['peak_multiplier'], 'type': 'peak'}
    elif (hour >= temporal['evening_end']) or (hour <= temporal['morning_start']):
        return {'multiplier': temporal['offpeak_multiplier'], 'type': 'offpeak'}
    else:
        return {'multiplier': 1.0, 'type': 'normal'}


def get_severity_map() -> Dict[str, int]:
    return get_config().get('formula', {}).get('severity_map', {})


def get_curbflex_config() -> Dict[str, Any]:
    return get_config().get('curbflex', {})


def get_validation_config() -> Dict[str, Any]:
    return get_config().get('validation', {})


def get_enhanced_cascade_config() -> Dict[str, Any]:
    return get_config().get('enhanced_cascade', {})
