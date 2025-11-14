from typing import Dict, Any, List, Callable

from twisted.internet.defer import Deferred
from ctrader_open_api import Client as CtraderClient, TcpProtocol, EndPoints, Protobuf
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

from pepper_bot.ctrader import auth

class CTraderApiClient:
    """A Twisted-based client for interacting with the cTrader Open API."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.credentials = auth.get_credentials(account_id)
        self.access_token = self.credentials.get("accessToken")
        self.ctid_trader_account_id = None
        self._pending_requests: Dict[int, Deferred] = {}
        self._execution_event_callbacks: List[Callable] = []

        self.websocket_client = CtraderClient(
            EndPoints.PROTOBUF_DEMO_HOST,
            EndPoints.PROTOBUF_PORT,
            TcpProtocol
        )
        self.websocket_client.setConnectedCallback(self._on_websocket_connected)
        self.websocket_client.setMessageReceivedCallback(self._on_websocket_message)

    def _on_websocket_connected(self, client):
        print(f"WebSocket client for account {self.account_id} connected.")
        self.authenticate_and_authorize()

    def _on_websocket_message(self, client, message):
        msg_payload_type = message.payloadType
        if msg_payload_type == ProtoOAExecutionEvent().payloadType:
            for callback in self._execution_event_callbacks:
                callback(Protobuf.extract(message))
        elif msg_payload_type in self._pending_requests:
            deferred = self._pending_requests.pop(msg_payload_type)
            deferred.callback(Protobuf.extract(message))
        else:
            print(f"Received unhandled message: {Protobuf.extract(message)}")

    def _send_request(self, request, response_payload_type: int) -> Deferred:
        """Sends a request and returns a Deferred that will fire with the response."""
        deferred = Deferred()
        self._pending_requests[response_payload_type] = deferred
        self.websocket_client.send(request)
        return deferred

    def authenticate_and_authorize(self):
        """Authenticates the application and authorizes the trading account."""
        auth_req = ProtoOAApplicationAuthReq()
        auth_req.clientId = self.credentials["clientId"]
        auth_req.clientSecret = self.credentials["clientSecret"]

        d = self._send_request(auth_req, ProtoOAApplicationAuthRes().payloadType)
        d.addCallback(self._on_app_authenticated)
        return d

    def _on_app_authenticated(self, response):
        print(f"Application for account {self.account_id} authenticated.")
        acc_list_req = ProtoOAGetAccountListByAccessTokenReq()
        acc_list_req.accessToken = self.access_token

        d = self._send_request(acc_list_req, ProtoOAGetAccountListByAccessTokenRes().payloadType)
        d.addCallback(self._on_account_list)
        return d

    def _on_account_list(self, response):
        # For simplicity, we'll use the first account in the list.
        self.ctid_trader_account_id = response.ctidTraderAccount[0].ctidTraderAccountId

        acc_auth_req = ProtoOAAccountAuthReq()
        acc_auth_req.ctidTraderAccountId = self.ctid_trader_account_id
        acc_auth_req.accessToken = self.access_token

        d = self._send_request(acc_auth_req, ProtoOAAccountAuthRes().payloadType)
        d.addCallback(self._on_account_authorized)
        return d

    def _on_account_authorized(self, response):
        print(f"Account {self.ctid_trader_account_id} for client {self.account_id} authorized.")
        return response

    def get_symbols(self) -> Deferred:
        """Gets all available symbols for the trading account."""
        request = ProtoOASymbolsListReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
        return self._send_request(request, ProtoOASymbolsListRes().payloadType)

    def place_order(self, symbol_id: int, order_type: ProtoOAOrderType, trade_side: ProtoOATradeSide,
                          volume: int, stop_loss: float = None, take_profit: float = None) -> Deferred:
        """Places a new trading order."""
        request = ProtoOANewOrderReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
        request.symbolId = symbol_id
        request.orderType = order_type
        request.tradeSide = trade_side
        request.volume = volume
        if stop_loss:
            request.stopLoss = stop_loss
        if take_profit:
            request.takeProfit = take_profit

        return self._send_request(request, ProtoOAExecutionEvent().payloadType)

    def modify_position(self, position_id: int, stop_loss: float = None, take_profit: float = None, trailing_stop: bool = False) -> Deferred:
        """Modifies an existing position."""
        request = ProtoOAAmendPositionSLTPReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
        request.positionId = position_id
        if stop_loss:
            request.stopLoss = stop_loss
        if take_profit:
            request.takeProfit = take_profit
        if trailing_stop:
            request.trailingStopLoss = trailing_stop

        return self._send_request(request, ProtoOAExecutionEvent().payloadType)

    def connect(self):
        """Connects to the cTrader WebSocket."""
        self.websocket_client.startService()

    def subscribe_to_ticks(self, symbol_id: int):
        """Subscribes to tick data for a given symbol."""
        request = ProtoOASubscribeSpotsReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
        request.symbolId.append(symbol_id)
        self.websocket_client.send(request)

    def subscribe_to_execution_events(self, callback: Callable):
        """Subscribes to execution events."""
        self._execution_event_callbacks.append(callback)
