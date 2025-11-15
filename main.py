import asyncio
import threading
from twisted.internet import reactor

import sys
import os
import json
import signal
import logging

from pepper_bot.core.database import initialize_db
from pepper_bot.core.env import load_credentials
from pepper_bot.core.logger import setup_logging
from pepper_bot.ctrader.manager import CTraderManager
from pepper_bot.telegram.bot import run_bot
from pepper_bot.trading.position_manager import PositionManager

def run_twisted():
    """Runs the Twisted reactor in a separate thread."""
    if not reactor.running:
        reactor.run(installSignalHandlers=0)

async def main():
    """
    The main entrypoint for the bot.
    Initializes and starts the CTraderManager and the Telegram bot.
    """
    setup_logging()
    logging.info("Application starting...")

    # Start Twisted in a background thread
    twisted_thread = threading.Thread(target=run_twisted, daemon=True)
    twisted_thread.start()
    logging.info("Twisted reactor thread started.")

    loop = asyncio.get_running_loop()
    initialize_db()
    logging.info("Database initialized.")

    try:
        credentials = load_credentials()
        logging.info("Credentials loaded.")
    except ValueError as e:
        logging.error(f"Error loading credentials: {e}")
        return

    ctrader_manager = CTraderManager()
    logging.info("Starting CTraderManager...")
    await ctrader_manager.start()
    logging.info("cTrader clients are ready.")

    logging.info("Starting Telegram bot...")
    await run_bot(credentials["telegram_token"], ctrader_manager)
    logging.info("Telegram bot started.")

    # Keep the application alive until it is manually stopped
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    logging.info("Application running. Press Ctrl+C to exit.")
    await stop_event.wait()

    # Gracefully shut down
    logging.info("Shutting down...")
    reactor.callFromThread(reactor.stop)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt caught, shutting down.")
