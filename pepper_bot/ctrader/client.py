import logging
from typing import Dict, Any, List, Callable

from twisted.internet.defer import Deferred
from ctrader_open_api import Client as CtraderClient, TcpProtocol, EndPoints, Protobuf
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

from pepper_bot.ctrader import auth

class CTraderApiClient:
    """A Twisted-based client for interacting with the cTrader Open API."""

    def __init__(self):
        logging.info("Initializing CTraderApiClient.")
        self.credentials = auth.get_credentials()
        self.access_token = self.credentials.get("accessToken")
        self.trader_accounts = []
        self._pending_requests: Dict[int, Deferred] = {}
        self._request_id = 1
        self._execution_event_callbacks: List[Callable] = []
        
        # Track authentication state
        self._is_app_authenticated = False

        # Authentication deferreds
        self._app_auth_deferred = None
        self._account_list_deferred = None
        self._account_auth_deferred = None

        self.account_id = None # Will be set during authorization

        self.websocket_client = CtraderClient(
            EndPoints.PROTOBUF_DEMO_HOST,
            EndPoints.PROTOBUF_PORT,
            TcpProtocol
        )
        self.websocket_client.setConnectedCallback(self._on_websocket_connected)
        self.websocket_client.setMessageReceivedCallback(self._on_websocket_message)
        logging.info("CTraderApiClient initialized.")

    def _on_websocket_connected(self, client):
        logging.info(f"WebSocket client connected.")
        self.authenticate_and_authorize()

    def _send_request(self, request, response_payload_type: int) -> Deferred:
        """Sends a request using requestId (correct way to match responses)"""
        d = Deferred()

        # Only use requestId for messages that support it
        if hasattr(request, 'requestId'):
            request.requestId = self._request_id
            self._pending_requests[self._request_id] = d
            self._request_id += 1
        
        logging.info(f"Sending request: {request}")
        self.websocket_client.send(request)
        return d

    def _on_websocket_message(self, client, message):
        msg = Protobuf.extract(message)
        
        logging.info(f"Received message type: {message.payloadType}, content: {msg}")
        
        # First try to handle by requestId
        if hasattr(msg, 'requestId') and msg.requestId in self._pending_requests:
            d = self._pending_requests.pop(msg.requestId)
            d.callback(msg)
            return
        
        # Handle error messages
        if hasattr(msg, 'errorCode') and msg.errorCode:
            error_msg = f"Error received: {msg.errorCode} - {getattr(msg, 'description', 'No description')}"
            logging.error(error_msg)
            
            # If there's a pending auth deferred, handle the error
            if self._app_auth_deferred is not None:
                if msg.errorCode == "ALREADY_LOGGED_IN":
                    logging.info("Application already authenticated, proceeding to get account list...")
                    self._is_app_authenticated = True
                    self._app_auth_deferred.callback(msg)
                else:
                    from twisted.python.failure import Failure
                    self._app_auth_deferred.errback(Exception(error_msg))
                self._app_auth_deferred = None
            return
        
        # Handle specific message types that don't have requestId
        if message.payloadType == ProtoOAApplicationAuthRes().payloadType:
            logging.info("Received application auth response - authentication successful")
            self._is_app_authenticated = True
            if self._app_auth_deferred is not None:
                self._app_auth_deferred.callback(msg)
                self._app_auth_deferred = None
            return
            
        elif message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:
            logging.info("Received account list response")
            if self._account_list_deferred is not None:
                self._account_list_deferred.callback(msg)
                self._account_list_deferred = None
            return
            
        elif message.payloadType == ProtoOAAccountAuthRes().payloadType:
            logging.info("Received account auth response")
            if self._account_auth_deferred is not None:
                self._account_auth_deferred.callback(msg)
                self._account_auth_deferred = None
            return
        
        # Execution events
        if message.payloadType == ProtoOAExecutionEvent().payloadType:
            for callback in self._execution_event_callbacks:
                callback(msg)
        else:
            logging.warning(f"Received unhandled message type {message.payloadType}: {msg}")

    def authenticate_and_authorize(self):
        """Authenticates the application."""
        logging.info(f"Starting authentication.")
        
        if not self.credentials:
            raise Exception(f"No credentials found.")
        
        auth_req = ProtoOAApplicationAuthReq()
        auth_req.clientId = self.credentials["clientId"]
        auth_req.clientSecret = self.credentials["clientSecret"]

        self._app_auth_deferred = Deferred()
        self.websocket_client.send(auth_req)
        
        from twisted.internet import reactor
        self._app_auth_deferred.addTimeout(10, reactor)
        
        self._app_auth_deferred.addErrback(self._on_auth_error)
        return self._app_auth_deferred

    def _on_auth_error(self, failure):
        """Handle authentication errors"""
        logging.error(f"Authentication error: {failure.getErrorMessage()}")
        return failure

    def get_account_list(self):
        """Get account list after application authentication"""
        logging.info("Getting account list...")
        
        self.access_token = auth.get_credentials().get("accessToken")
        if not self.access_token:
            raise Exception("Cannot get account list: access token is None")
            
        acc_list_req = ProtoOAGetAccountListByAccessTokenReq()
        acc_list_req.accessToken = self.access_token

        self._account_list_deferred = Deferred()
        self.websocket_client.send(acc_list_req)
        
        from twisted.internet import reactor
        self._account_list_deferred.addTimeout(10, reactor)
        
        self._account_list_deferred.addCallback(self._on_account_list)
        self._account_list_deferred.addErrback(self._on_auth_error)
        return self._account_list_deferred

    def _on_account_list(self, response):
        """Handle account list response"""
        if not response.ctidTraderAccount:
            raise Exception(f"No trading accounts found.")

        self.trader_accounts = list(response.ctidTraderAccount)
        logging.info(f"Found {len(self.trader_accounts)} trading accounts.")
        return self.trader_accounts

    def authorize_trading_account(self, ctid_trader_account_id: int):
        """Authorizes a specific trading account."""
        logging.info(f"Authorizing account {ctid_trader_account_id}...")
        self.account_id = ctid_trader_account_id

        if not self.access_token:
            raise Exception("Cannot authorize account: access token is None")

        acc_auth_req = ProtoOAAccountAuthReq()
        acc_auth_req.ctidTraderAccountId = ctid_trader_account_id
        acc_auth_req.accessToken = self.access_token

        d = self._send_request(acc_auth_req, ProtoOAAccountAuthRes().payloadType)

        def on_authorized(response):
            logging.info(f"Account {ctid_trader_account_id} authorized.")
            return response

        d.addCallback(on_authorized)
        return d

    def get_symbols(self, ctid_trader_account_id: int) -> Deferred:
        """Gets all available symbols for the trading account."""
        request = ProtoOASymbolsListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return self._send_request(request, ProtoOASymbolsListRes().payloadType)

    def place_order(self, ctid_trader_account_id: int, symbol_id: int, order_type: ProtoOAOrderType, trade_side: ProtoOATradeSide,
                          volume: int, stop_loss: float = None, take_profit: float = None) -> Deferred:
        """Places a new trading order."""
        request = ProtoOANewOrderReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.symbolId = symbol_id
        request.orderType = order_type
        request.tradeSide = trade_side
        request.volume = volume
        if stop_loss:
            request.stopLoss = stop_loss
        if take_profit:
            request.takeProfit = take_profit

        return self._send_request(request, ProtoOANewOrderRes().payloadType)

    def modify_position(self, ctid_trader_account_id: int, position_id: int, stop_loss: float = None, take_profit: float = None, trailing_stop: bool = False) -> Deferred:
        """Modifies an existing position."""
        request = ProtoOAAmendPositionSLTPReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.positionId = position_id
        if stop_loss:
            request.stopLoss = stop_loss
        if take_profit:
            request.takeProfit = take_profit
        if trailing_stop:
            request.trailingStopLoss = trailing_stop

        return self._send_request(request, ProtoOAAmendPositionSLTPRes().payloadType)

    def connect(self):
        """Connects to the cTrader WebSocket."""
        logging.info("Connecting to cTrader WebSocket...")
        self.websocket_client.startService()
        logging.info("cTrader WebSocket connected.")

    def subscribe_to_ticks(self, ctid_trader_account_id: int, symbol_id: int) -> Deferred:
        request = ProtoOASubscribeSpotsReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.symbolId.append(symbol_id)
        return self._send_request(request, ProtoOASubscribeSpotsRes().payloadType)

    def subscribe_to_execution_events(self, callback: Callable):
        """Subscribes to execution events."""
        self._execution_event_callbacks.append(callback)

    def is_ready(self):
        """Check if the client is fully authenticated and authorized"""
        return self._is_app_authenticated

    def get_account_balance(self, ctid_trader_account_id: int) -> Deferred:
        """Gets the balance of a trading account."""
        request = ProtoOATraderReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        d = self._send_request(request, ProtoOATraderRes().payloadType)
        d.addCallback(lambda response: response.trader.balance)
        return d
