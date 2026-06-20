"""
Configuration management for DispatchMind / ParkImpact AI.

This module provides a single source of truth for all configuration,
making the system city-agnostic, testable, and maintainable.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_PATH = Path(__file__).parent / "config" / "app.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file with validation."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    _validate_config(config)
    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration structure and values."""
    required_sections = ['version', 'city', 'data', 'model', 'formula', 'cascades', 'validation', 'pilot', 'deployment']
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    # Validate formula structure
    formula = config['formula']
    if 'duration' not in formula or 'congestion' not in formula:
        raise ValueError("Formula must contain 'duration' and 'congestion' sections")
    
    # Validate cascade parameters
    cascades = config['cascades']
    if cascades['adjacency_max_distance_m'] <= 0:
        raise ValueError("adjacency_max_distance_m must be positive")
    if cascades['correlation_threshold'] < 0 or cascades['correlation_threshold'] > 1:
        raise ValueError("correlation_threshold must be between 0 and 1")


def get_duration_base_by_type(violation_type: str) -> float:
    """Get base duration for violation type from config."""
    config = load_config()
    base_by_type = config['formula']['duration']['base_by_type']
    return base_by_type.get(violation_type, 35.0)


def get_vehicle_adjustment(vehicle_type: str) -> float:
    """Get vehicle adjustment factor from config."""
    config = load_config()
    vehicle_adjustment = config['formula']['duration']['vehicle_adjustment']
    return vehicle_adjustment.get(vehicle_type, 1.0)


def get_vehicle_size_mult(vehicle_type: str) -> float:
    """Get vehicle size multiplier from config."""
    config = load_config()
    vehicle_size_mult = config['formula']['congestion']['vehicle_size_mult']
    return vehicle_size_mult.get(vehicle_type, 1.0)


def get_junction_distance_threshold(tier: str) -> float:
    """Get junction distance threshold for impact tier."""
    config = load_config()
    thresholds = config['formula']['congestion']['junction_distance']
    return thresholds.get(tier, 50.0)


def get_temporal_factors(hour: int) -> Dict[str, float]:
    """Get temporal factors (peak/offpeak) for hour."""
    config = load_config()
    temporal = config['model']['temporal']
    
    if (temporal['morning_start'] <= hour <= temporal['morning_end']) or \
       (temporal['evening_start'] <= hour <= temporal['evening_end']):
        return {'multiplier': temporal['peak_multiplier'], 'type': 'peak'}
    elif (hour >= temporal['evening_end']) or (hour <= temporal['morning_start']):
        return {'multiplier': temporal['offpeak_multiplier'], 'type': 'offpeak'}
    else:
        return {'multiplier': 1.0, 'type': 'normal'}


def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """Get a specific config value."""
    config = load_config()
    return config.get(section, {}).get(key, default)


def get_severity_map() -> Dict[str, int]:
    """Get severity mapping from config."""
    config = load_config()
    return config.get('formula', {}).get('severity_map', {})


def get_curbflex_config() -> Dict[str, Any]:
    """Get curbflex configuration."""
    return get_config_value('curbflex', {}, {})


def get_validation_config() -> Dict[str, Any]:
    """Get validation configuration."""
    return get_config_value('validation', {}, {})


def get_enhanced_cascade_config() -> Dict[str, Any]:
    """Get enhanced cascade configuration."""
    return get_config_value('enhanced_cascade', {}, {})


def get_enhanced_cascade_config() -> Dict[str, Any]:
    """Get enhanced cascade configuration."""
    return get_config_value('enhanced_cascade', {}, {})


# Global config cache
_CONFIG_CACHE = None


def get_config() -> Dict[str, Any]:
    """Get global config cache."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = load_config()
    return _CONFIG_CACHE


def reset_config_cache() -> None:
    """Reset config cache (useful for testing)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
