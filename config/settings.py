# Configuration management for AI Contact Manager

import json
import os
from pathlib import Path

CONFIG_FILE = Path.home() / ".ai_contact_manager_config.json"

DEFAULT_SETTINGS = {
    "openai_api_key": "",
    "llm_model": "gpt-4.1",
    "prompts": {
        "target_company_validation": "",
        "icp_validation": "",
        "clients_of_contact": "",
        "area_of_business": "",
        "most_relevant_summit": "",
        "client_icp": "",
        "time_zone_lookup": "",
    },
    "timezone": {
        "utc_offset": 0,
        "morning_call": "09:00",
        "afternoon_call": "15:00",
    },
    "table_layout": {
        "order": [],
        "visibility": {},
        "widths": {},
    },
}

_settings = None


def load_settings():
    """Load settings from the config file or return defaults."""
    global _settings
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                _settings = json.load(f)
        except json.JSONDecodeError:
            _settings = DEFAULT_SETTINGS.copy()
    else:
        _settings = DEFAULT_SETTINGS.copy()
    # Ensure all keys exist
    _merge_defaults(_settings, DEFAULT_SETTINGS)
    return _settings


def save_settings():
    """Persist current settings to disk."""
    if _settings is None:
        return
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(_settings, f, indent=2)


def get_settings():
    """Return the settings dictionary, loading it if necessary."""
    if _settings is None:
        return load_settings()
    return _settings


def update_setting(path, value):
    """Update a nested setting using dot-separated path."""
    keys = path.split(".")
    settings = get_settings()
    obj = settings
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value
    save_settings()


def _merge_defaults(target, defaults):
    for key, val in defaults.items():
        if isinstance(val, dict):
            target.setdefault(key, {})
            _merge_defaults(target[key], val)
        else:
            target.setdefault(key, val)

# Load settings on import
load_settings()
