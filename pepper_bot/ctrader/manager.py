import asyncio
import logging
from typing import Dict, Any
from twisted.internet import defer, reactor

from pepper_bot.ctrader.client import CTraderApiClient

class CTraderManager:
    """
    Manages the CTrader API client.
    """
    def __init__(self):
        logging.info("Initializing CTraderManager.")
        self.client: CTraderApiClient = None
        self.loop = asyncio.get_event_loop()
        self.ready_future = self.loop.create_future()
        logging.info("CTraderManager initialized.")

    def start(self):
        """
        Initializes and starts the cTrader client.
        Returns a Future that completes when the client is ready.
        """
        logging.info("CTraderManager starting...")
        reactor.callFromThread(self._start_client)
        return self.ready_future

    def _start_client(self):
        self.client = CTraderApiClient()
        self.client.websocket_client.setConnectedCallback(self._on_client_connected)
        self.client.connect()

    def _on_client_connected(self, _):
        """Callback for when a client connects."""
        logging.info("Client connected, authenticating...")
        d = self.client.authenticate_and_authorize()
        d.addCallback(self._on_client_ready)

    def _on_client_ready(self, _):
        """Callback for when the client is fully authenticated and ready."""
        logging.info("Client is ready.")
        self.loop.call_soon_threadsafe(self.ready_future.set_result, None)

    def get_trader_accounts(self):
        future = asyncio.Future()
        reactor.callFromThread(self._get_trader_accounts, future)
        return future

    def _get_trader_accounts(self, future):
        d = self.client.get_account_list()
        d.addCallback(lambda result: asyncio.get_running_loop().call_soon_threadsafe(future.set_result, result.traderAccount))

    def get_account_balance(self, ctid_trader_account_id: int):
        future = asyncio.Future()
        reactor.callFromThread(self._get_account_balance, ctid_trader_account_id, future)
        return future

    def _get_account_balance(self, ctid_trader_account_id, future):
        d = self.client.get_account_balance(ctid_trader_account_id)
        d.addCallback(lambda result: asyncio.get_running_loop().call_soon_threadsafe(future.set_result, result))

    def authorize_trading_account(self, ctid_trader_account_id: int):
        future = asyncio.Future()
        reactor.callFromThread(self._authorize_trading_account, ctid_trader_account_id, future)
        return future

    def _authorize_trading_account(self, ctid_trader_account_id, future):
        d = self.client.authorize_trading__account(ctid_trader_account_id)
        d.addCallback(lambda result: asyncio.get_running_loop().call_soon_threadsafe(future.set_result, result))
