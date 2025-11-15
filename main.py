import asyncio
from twisted.internet import asyncioreactor
asyncioreactor.install()

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

async def main():
    """
    The main entrypoint for the bot.
    Initializes and starts the CTraderManager and the Telegram bot.
    """
    setup_logging()
    logging.info("Application starting...")

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
    await ctrader_manager.start().asFuture(loop)
    logging.info("cTrader clients are ready.")

    # Fetch all available trading accounts and their balances
    logging.info("Fetching trader accounts...")
    accounts = ctrader_manager.get_trader_accounts()
    account_details = []
    for account in accounts:
        balance_deferred = ctrader_manager.client.get_account_balance(account.ctidTraderAccountId)
        balance = await balance_deferred.asFuture(loop)
        account_details.append((account, balance / 100.0))
    logging.info(f"Found {len(account_details)} accounts.")

    # Display accounts and handle selection based on the number of accounts
    print("Available trading accounts:")
    for i, (account, balance) in enumerate(account_details):
        print(f"{i+1}. Account ID: {account.ctidTraderAccountId}, Balance: {balance:.2f} {account.currency}")

    if len(account_details) < 2:
        logging.error("Not enough trading accounts for the straddle strategy.")
        return
    elif len(account_details) == 2:
        logging.info("Exactly two accounts found. Automatically selecting them.")
        account1 = account_details[0][0]
        account2 = account_details[1][0]
    else:
        # Get user selection
        logging.info("Multiple accounts found. Prompting for selection.")
        print("\nPlease select two accounts for the straddle strategy (e.g., '1 2'):")
        selection = input("> ")
        try:
            index1, index2 = [int(i) - 1 for i in selection.split()]
            account1 = account_details[index1][0]
            account2 = account_details[index2][0]
        except (ValueError, IndexError):
            logging.error("Invalid account selection.")
            return

    # Authorize the selected accounts
    logging.info("Authorizing selected accounts...")
    auth1_deferred = ctrader_manager.client.authorize_trading_account(account1.ctidTraderAccountId)
    await auth1_deferred.asFuture(loop)
    logging.info(f"Account {account1.ctidTraderAccountId} authorized.")
    auth2_deferred = ctrader_manager.client.authorize_trading_account(account2.ctidTraderAccountId)
    await auth2_deferred.asFuture(loop)
    logging.info(f"Account {account2.ctidTraderAccountId} authorized.")


    position_manager = PositionManager(
        ctrader_manager.client,
        account1.ctidTraderAccountId,
        account2.ctidTraderAccountId
    )
    position_manager.start_monitoring()
    logging.info("PositionManager started.")

    logging.info("Starting Telegram bot...")
    await run_bot(credentials["telegram_token"])
    logging.info("Telegram bot started.")

    # Keep the application alive until it is manually stopped
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    logging.info("Application running. Press Ctrl+C to exit.")
    await stop_event.wait()

    # Gracefully shut down
    logging.info("Shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt caught, shutting down.")
