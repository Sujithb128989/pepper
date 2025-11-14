import sys
import os
import json
from twisted.internet import reactor

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pepper_bot.core.database import initialize_db, get_all_trades
from pepper_bot.ctrader.client import CTraderApiClient
from pepper_bot.telegram.bot import TelegramBot
from pepper_bot.trading.position_manager import PositionManager
from pepper_bot.telegram.menus import main_menu, settings_menu, pair_selection_menu
from pepper_bot.core.config import get_all_settings, set_setting
from pepper_bot.trading.strategy import place_straddle_trade

def main():
    """
    The main entrypoint for the bot.
    Initializes and starts the cTrader clients and the Telegram bot.
    """
    initialize_db()

    with open("pepper_bot/core/credentials.json", "r") as f:
        credentials = json.load(f)

    # Initialize the clients
    client1 = CTraderApiClient("account1")
    client2 = CTraderApiClient("account2")

    # Initialize the position manager
    position_manager = PositionManager(client1, client2)
    position_manager.start_monitoring()

    # Initialize the Telegram bot
    bot = TelegramBot(credentials["telegram_token"])

    # Add command handlers
    def start_command(message):
        bot.send_message(message["chat"]["id"], "Welcome to Pepper!", reply_markup=main_menu())

    def stats_command(message):
        trades = get_all_trades()
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        total_pnl = sum(t["pnl"] for t in trades)

        stats_message = (
            f"📊 *Trading Statistics* 📊\n\n"
            f"Total Trades: {len(trades)}\n"
            f"Wins: {len(wins)}\n"
            f"Losses: {len(losses)}\n"
            f"Win Rate: {win_rate:.2f}%\n"
            f"Total PnL: {total_pnl:.2f}\n"
        )
        bot.send_message(message["chat"]["id"], stats_message)

    bot.add_command_handler("start", start_command)
    bot.add_command_handler("stats", stats_command)

    # Add callback handlers
    def settings_callback(callback_query):
        bot.edit_message_text(
            chat_id=callback_query["message"]["chat"]["id"],
            message_id=callback_query["message"]["message_id"],
            text="Settings Menu",
            reply_markup=settings_menu()
        )

    def trade_now_callback(callback_query):
        bot.edit_message_text(
            chat_id=callback_query["message"]["chat"]["id"],
            message_id=callback_query["message"]["message_id"],
            text="Placing trades for all enabled pairs...",
            reply_markup=main_menu()
        )

        settings = get_all_settings()
        enabled_pairs = [pair for pair, enabled in settings["pairs"].items() if enabled]

        for pair in enabled_pairs:
            # We need to get the symbol id from the symbol name
            # This is a placeholder for the actual logic
            symbol_id = 0

            d = place_straddle_trade(client1, client2, symbol_id, pair)
            d.addCallback(lambda result: position_manager.add_straddle(pair, result[0], result[1]))


    bot.add_callback_handler("settings", settings_callback)
    bot.add_callback_handler("trade_now", trade_now_callback)

    # Connect the clients and start the bot
    client1.connect()
    client2.connect()
    bot.run()

    print("Pepper bot is running.")
    reactor.run()

if __name__ == "__main__":
    main()
