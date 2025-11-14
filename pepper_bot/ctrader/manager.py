import asyncio
import threading
from typing import Dict, Any, Callable
from twisted.internet import reactor, defer, asyncioreactor

from pepper_bot.ctrader.client import CTraderApiClient

class CTraderManager(threading.Thread):
    """
    Manages the CTrader API clients in a separate thread running the Twisted reactor.
    """
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.clients: Dict[str, CTraderApiClient] = {}
        self._loop = asyncio.get_running_loop()
        self.ready = asyncio.Event()

    def run(self):
        """This method runs in the new thread."""
        print("CTraderManager thread started.")
        # Create and set a new asyncio event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        asyncioreactor.install()

        for account_id in ["account1", "account2"]:
            client = CTraderApiClient(account_id)
            self.clients[account_id] = client
            client.websocket_client.setConnectedCallback(
                lambda _, client=client: self._on_client_connected(client)
            )
            client.connect()

        reactor.run(installSignalHandlers=False)

    def _on_client_connected(self, client: CTraderApiClient):
        """Callback for when a client connects."""
        print(f"Client for account {client.account_id} connected, authenticating...")
        # Schedule the async authentication to run in the Twisted event loop
        d = defer.ensureDeferred(client.authenticate_and_authorize())
        d.addCallback(self._check_all_clients_ready)

    def _check_all_clients_ready(self, _):
        """Checks if all clients are authorized and sets the ready event."""
        if all(client._is_authorized.is_set() for client in self.clients.values()):
            self._loop.call_soon_threadsafe(self.ready.set)

    def _execute_in_twisted(self, func: Callable, *args, **kwargs) -> asyncio.Future:
        """Schedules a function to be called in the Twisted reactor thread."""
        future = self._loop.create_future()

        def run_and_resolve():
            try:
                d = defer.ensureDeferred(func(*args, **kwargs))
                d.addCallbacks(
                    lambda result: self._loop.call_soon_threadsafe(future.set_result, result),
                    lambda failure: self._loop.call_soon_threadsafe(future.set_exception, failure.value)
                )
            except Exception as e:
                self._loop.call_soon_threadsafe(future.set_exception, e)

        reactor.callFromThread(run_and_resolve)
        return future

    async def get_symbols(self, account_id: str) -> Any:
        client = self.clients[account_id]
        return await self._execute_in_twisted(client.get_symbols)

    async def place_order(self, account_id: str, **kwargs) -> Any:
        client = self.clients[account_id]
        return await self._execute_in_twisted(client.place_order, **kwargs)

    def stop(self):
        if reactor.running:
            reactor.callFromThread(reactor.stop)
