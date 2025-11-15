import asyncio
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from twisted.internet import asyncioreactor
asyncioreactor.install()

import sys
import os
import signal
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pepper_bot.core.database import initialize_db
from pepper_bot.ctrader.manager import CTraderManager
from pepper_bot.telegram.bot import run_bot
from pepper_bot.trading.position_manager import PositionManager

# Build the absolute path to the credentials file
_CREDENTIALS_DIR = os.path.abspath(os.path.dirname(__file__))
CREDENTIALS_FILE = os.path.join(_CREDENTIALS_DIR, "pepper_bot\\core\\credentials.json")

async def main():
    """
    The main entrypoint for the bot.
    Initializes and starts the CTraderManager and the Telegram bot.
    """
    initialize_db()

    with open(CREDENTIALS_FILE, "r") as f:
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
    await run_bot(credentials["telegram_token"])

    # Keep the application alive until it is manually stopped
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    await stop_event.wait()

    # Gracefully shut down
    print("Shutting down...")
    ctrader_manager.stop()
    ctrader_manager.join()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught, shutting down.")
