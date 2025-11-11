from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pepper_bot.core.config import get_all_settings

def main_menu() -> InlineKeyboardMarkup:
    """Returns the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton("📊 Trade Now", callback_data="trade_now"),
        ],
        [
            InlineKeyboardButton("📈 Active Positions", callback_data="active_positions"),
            InlineKeyboardButton("📋 Trade History", callback_data="trade_history"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_menu() -> InlineKeyboardMarkup:
    """Returns the settings menu keyboard."""
    settings = get_all_settings()
    pairs = settings["pairs"]

    keyboard = []
    for pair, enabled in pairs.items():
        status = "✅" if enabled else "❌"
        keyboard.append([InlineKeyboardButton(f"{status} {pair}", callback_data=f"toggle_pair_{pair}")])

    keyboard.append([InlineKeyboardButton("Set Stop Loss", callback_data="set_sl")])
    keyboard.append([InlineKeyboardButton("Set Trailing Stop", callback_data="set_ts")])
    keyboard.append([InlineKeyboardButton("Set Volume", callback_data="set_vol")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")])

    return InlineKeyboardMarkup(keyboard)

def pair_selection_menu(setting: str) -> InlineKeyboardMarkup:
    """Returns a keyboard with the available pairs for a given setting."""
    settings = get_all_settings()
    pairs = settings["pairs"]

    keyboard = []
    for pair, enabled in pairs.items():
        if enabled:
            keyboard.append([InlineKeyboardButton(pair, callback_data=f"set_{setting}_{pair}")])

    keyboard.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")])
    return InlineKeyboardMarkup(keyboard)
