import json
from typing import Any, Dict
import threading

SETTINGS_FILE = "pepper_bot/core/settings.json"
_lock = threading.Lock()

def get_all_settings() -> Dict[str, Any]:
    """Loads all settings from the JSON file."""
    with _lock:
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


def get_setting(key: str) -> Any:
    """Loads a specific setting from the JSON file."""
    settings = get_all_settings()
    return settings.get(key)


def set_setting(key: str, value: Any) -> None:
    """Saves a specific setting to the JSON file."""
    with _lock:
        settings = get_all_settings()
        settings[key] = value
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
