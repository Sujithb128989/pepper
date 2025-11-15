import threading
from typing import Dict, Any
from twisted.internet import reactor, defer

from pepper_bot.ctrader.client import CTraderApiClient

class CTraderManager(threading.Thread):
    """
    Manages the CTrader API client in a separate thread running the Twisted reactor.
    """
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.client: CTraderApiClient = None
        self.ready = defer.Deferred()

    def run(self):
        """This method runs in the new thread."""
        print("CTraderManager thread started.")
        self.client = CTraderApiClient()
        self.client.websocket_client.setConnectedCallback(self._on_client_connected)
        self.client.connect()
        reactor.run(installSignalHandlers=False)

    def _on_client_connected(self, _):
        """Callback for when a client connects."""
        print("Client connected, authenticating...")
        d = self.client.authenticate_and_authorize()
        d.addCallback(self._on_client_ready)

    def _on_client_ready(self, _):
        """Callback for when the client is fully authenticated and ready."""
        reactor.callFromThread(self.ready.callback, None)

    def get_symbols(self, ctid_trader_account_id: int) -> defer.Deferred:
        return self.client.get_symbols(ctid_trader_account_id)

    def place_order(self, ctid_trader_account_id: int, **kwargs) -> defer.Deferred:
        return self.client.place_order(ctid_trader_account_id, **kwargs)

    def get_trader_accounts(self):
        """Returns the list of trader accounts for a given client."""
        return self.client.trader_accounts

    def stop(self):
        if reactor.running:
            reactor.callFromThread(reactor.stop)
