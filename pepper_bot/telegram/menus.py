from typing import Dict, Any, List

from pepper_bot.core.config import get_all_settings

def main_menu() -> Dict[str, List[List[Dict[str, str]]]]:
    """Returns the main menu keyboard."""
    return {
        "inline_keyboard": [
            [
                {"text": "⚙️ Settings", "callback_data": "settings"},
                {"text": "📊 Trade Now", "callback_data": "trade_now"},
            ],
            [
                {"text": "📈 Active Positions", "callback_data": "active_positions"},
                {"text": "📋 Trade History", "callback_data": "trade_history"},
            ],
        ]
    }

def settings_menu() -> Dict[str, List[List[Dict[str, str]]]]:
    """Returns the settings menu keyboard."""
    settings = get_all_settings()
    pairs = settings["pairs"]

    keyboard = []
    for pair, enabled in pairs.items():
        status = "✅" if enabled else "❌"
        keyboard.append([{"text": f"{status} {pair}", "callback_data": f"toggle_pair_{pair}"}])

    keyboard.append([{"text": "Set Stop Loss", "callback_data": "set_sl"}])
    keyboard.append([{"text": "Set Trailing Stop", "callback_data": "set_ts"}])
    keyboard.append([{"text": "Set Volume", "callback_data": "set_vol"}])
    keyboard.append([{"text": "⬅️ Back to Main Menu", "callback_data": "main_menu"}])

    return {"inline_keyboard": keyboard}

def pair_selection_menu(setting: str) -> Dict[str, List[List[Dict[str, str]]]]:
    """Returns a keyboard with the available pairs for a given setting."""
    settings = get_all_settings()
    pairs = settings["pairs"]

    keyboard = []
    for pair, enabled in pairs.items():
        if enabled:
            keyboard.append([{"text": pair, "callback_data": f"set_{setting}_{pair}"}])

    keyboard.append([{"text": "⬅️ Back to Settings", "callback_data": "settings"}])
    return {"inline_keyboard": keyboard}
