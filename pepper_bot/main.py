import sys
import os
import asyncio
import signal
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pepper_bot.core.database import initialize_db
from pepper_bot.ctrader.manager import CTraderManager
from pepper_bot.telegram.bot import run_bot
from pepper_bot.trading.position_manager import PositionManager

async def main():
    """
    The main entrypoint for the bot.
    Initializes and starts the CTraderManager and the Telegram bot.
    """
    initialize_db()

    with open("pepper_bot/core/credentials.json", "r") as f:
        credentials = json.load(f)

    ctrader_manager = CTraderManager()
    print("Starting CTraderManager...")
    ctrader_manager.start()

    print("Waiting for cTrader clients to be ready...")
    await ctrader_manager.ready.wait()
    print("cTrader clients are ready.")

    position_manager = PositionManager(ctrader_manager)
    position_manager.start_monitoring()

    print("Starting Telegram bot...")
    run_bot(credentials["telegram_token"])

    # We need to properly handle shutdown
    # For now, we'll just join the manager thread
    ctrader_manager.join()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught, shutting down.")
