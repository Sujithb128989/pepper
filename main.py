import asyncio
from twisted.internet import asyncioreactor
asyncioreactor.install()

import sys
import os
import json

from pepper_bot.core.database import initialize_db
from pepper_bot.ctrader.manager import CTraderManager
from pepper_bot.telegram.bot import run_bot
from pepper_bot.trading.position_manager import PositionManager

# Build the absolute path to the credentials file
_CREDENTIALS_DIR = os.path.abspath(os.path.dirname(__file__))
CREDENTIALS_FILE = os.path.join(_CREDENTIALS_DIR, "pepper_bot", "core", "credentials.json")

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
    await ctrader_manager.ready
    print("cTrader clients are ready.")

    # Fetch all available trading accounts and their balances
    accounts = ctrader_manager.get_trader_accounts()
    account_details = []
    for account in accounts:
        balance = await ctrader_manager.client.get_account_balance(account.ctidTraderAccountId)
        account_details.append((account, balance / 100.0)) # Assuming balance is in cents

    # Display accounts and prompt for selection
    print("Available trading accounts:")
    for i, (account, balance) in enumerate(account_details):
        print(f"{i+1}. Account ID: {account.ctidTraderAccountId}, Balance: {balance:.2f} {account.currency}")

    if len(account_details) < 2:
        print("\nError: At least two trading accounts are required for the straddle strategy.")
        return

    # Get user selection
    print("\nPlease select two accounts for the straddle strategy (e.g., '1 2'):")
    selection = input("> ")
    try:
        index1, index2 = [int(i) - 1 for i in selection.split()]
        account1 = account_details[index1][0]
        account2 = account_details[index2][0]
    except (ValueError, IndexError):
        print("Invalid selection. Please enter two valid numbers separated by a space.")
        return

    # Authorize the selected accounts
    print("Authorizing selected accounts...")
    await ctrader_manager.client.authorize_trading_account(account1.ctidTraderAccountId)
    print(f"Account {account1.ctidTraderAccountId} authorized.")
    await ctrader_manager.client.authorize_trading_account(account2.ctidTraderAccountId)
    print(f"Account {account2.ctidTraderAccountId} authorized.")


    position_manager = PositionManager(
        ctrader_manager.client,
        account1.ctidTraderAccountId,
        account2.ctidTraderAccountId
    )
    position_manager.start_monitoring()
    print("PositionManager started.")

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
