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
        self.ready = defer.Deferred()
        logging.info("CTraderManager initialized.")

    def start(self):
        """
        Initializes and starts the cTrader client.
        Returns a Deferred that fires when the client is ready.
        """
        logging.info("CTraderManager starting...")
        self.client = CTraderApiClient()
        self.client.connect()
        # Manually trigger authentication after a short delay
        reactor.callLater(1, self._on_client_connected, None)
        return self.ready

    def _on_client_connected(self, _):
        """Callback for when a client connects."""
        logging.info("Client connected, authenticating...")
        d = self.client.authenticate_and_authorize()
        d.addCallback(self._on_client_ready)

    def _on_client_ready(self, _):
        """Callback for when the client is fully authenticated and ready."""
        logging.info("Client is ready.")
        self.ready.callback(None)

    def get_symbols(self, ctid_trader_account_id: int) -> defer.Deferred:
        return self.client.get_symbols(ctid_trader_account_id)

    def place_order(self, ctid_trader_account_id: int, **kwargs) -> defer.Deferred:
        return self.client.place_order(ctid_trader_account_id, **kwargs)

    def get_trader_accounts(self):
        """Returns the list of trader accounts for a given client."""
        return self.client.trader_accounts
