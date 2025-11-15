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
        self._request_id = 1
        self._execution_event_callbacks: List[Callable] = []
        
        # Track authentication state
        self._is_app_authenticated = False
        self._is_account_authorized = False

        # Authentication deferreds
        self._app_auth_deferred = None
        self._account_list_deferred = None
        self._account_auth_deferred = None

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

    def _send_request(self, request, response_payload_type: int) -> Deferred:
        """Sends a request using requestId (correct way to match responses)"""
        d = Deferred()

        # Only use requestId for messages that support it
        if hasattr(request, 'requestId'):
            request.requestId = self._request_id
            self._pending_requests[self._request_id] = d
            self._request_id += 1
        
        # send
        self.websocket_client.send(request)
        return d

    def _on_websocket_message(self, client, message):
        msg = Protobuf.extract(message)
        
        print(f"Received message type: {message.payloadType}, content: {msg}")
        
        # First try to handle by requestId
        if hasattr(msg, 'requestId') and msg.requestId in self._pending_requests:
            d = self._pending_requests.pop(msg.requestId)
            d.callback(msg)
            return
        
        # Handle error messages
        if hasattr(msg, 'errorCode') and msg.errorCode:
            error_msg = f"Error received: {msg.errorCode} - {getattr(msg, 'description', 'No description')}"
            print(error_msg)
            
            # If there's a pending auth deferred, handle the error
            if self._app_auth_deferred is not None:
                if msg.errorCode == "ALREADY_LOGGED_IN":
                    # If already logged in, we can proceed to get account list
                    print("Application already authenticated, proceeding to get account list...")
                    self._is_app_authenticated = True
                    self._app_auth_deferred.callback(msg)
                else:
                    # For other errors, errback the deferred
                    from twisted.python.failure import Failure
                    self._app_auth_deferred.errback(Exception(error_msg))
                self._app_auth_deferred = None
            return
        
        # Handle specific message types that don't have requestId
        if message.payloadType == ProtoOAApplicationAuthRes().payloadType:
            print("Received application auth response - authentication successful")
            # Application auth successful
            self._is_app_authenticated = True
            if self._app_auth_deferred is not None:
                self._app_auth_deferred.callback(msg)
                self._app_auth_deferred = None
            return
            
        elif message.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:
            print("Received account list response")
            if self._account_list_deferred is not None:
                self._account_list_deferred.callback(msg)
                self._account_list_deferred = None
            return
            
        elif message.payloadType == ProtoOAAccountAuthRes().payloadType:
            print("Received account auth response")
            if self._account_auth_deferred is not None:
                self._account_auth_deferred.callback(msg)
                self._account_auth_deferred = None
            return
        
        # Execution events
        if message.payloadType == ProtoOAExecutionEvent().payloadType:
            for callback in self._execution_event_callbacks:
                callback(msg)
        else:
            print(f"Received unhandled message type {message.payloadType}: {msg}")

    def authenticate_and_authorize(self):
        """Authenticates the application and authorizes the trading account."""
        print(f"Starting authentication for account {self.account_id}")
        
        # Check if we have credentials
        if not self.credentials:
            raise Exception(f"No credentials found for account {self.account_id}")
        
        # Check if we have access token
        if not self.access_token:
            print(f"Warning: No access token found for account {self.account_id}")
            # We can still try application authentication, but account auth will fail
        
        # Application authentication
        auth_req = ProtoOAApplicationAuthReq()
        auth_req.clientId = self.credentials["clientId"]
        auth_req.clientSecret = self.credentials["clientSecret"]

        self._app_auth_deferred = Deferred()
        self.websocket_client.send(auth_req)
        
        # Set timeout for authentication
        from twisted.internet import reactor
        self._app_auth_deferred.addTimeout(10, reactor)
        
        self._app_auth_deferred.addCallback(self._on_app_authenticated)
        self._app_auth_deferred.addErrback(self._on_auth_error)
        return self._app_auth_deferred

    def _on_auth_error(self, failure):
        """Handle authentication errors"""
        print(f"Authentication error for account {self.account_id}: {failure.getErrorMessage()}")
        return failure

    def _on_app_authenticated(self, response):
        """Callback when application is authenticated"""
        print(f"Application for account {self.account_id} authenticated.")
        
        # Now get account list
        if not self.access_token:
            raise Exception(f"No access token available for account {self.account_id}. Cannot proceed with account authorization.")
        
        return self._get_account_list()

    def _get_account_list(self):
        """Get account list after application authentication"""
        print("Getting account list...")
        
        if not self.access_token:
            raise Exception("Cannot get account list: access token is None")
            
        acc_list_req = ProtoOAGetAccountListByAccessTokenReq()
        acc_list_req.accessToken = self.access_token

        self._account_list_deferred = Deferred()
        self.websocket_client.send(acc_list_req)
        
        # Set timeout
        from twisted.internet import reactor
        self._account_list_deferred.addTimeout(10, reactor)
        
        self._account_list_deferred.addCallback(self._on_account_list)
        self._account_list_deferred.addErrback(self._on_auth_error)
        return self._account_list_deferred

    def _on_account_list(self, response):
        """Handle account list response"""
        if not response.ctidTraderAccount:
            raise Exception(f"No trading accounts found for account {self.account_id}")
            
        # For simplicity, we'll use the first account in the list.
        self.ctid_trader_account_id = response.ctidTraderAccount[0].ctidTraderAccountId
        print(f"Found account ID: {self.ctid_trader_account_id}")

        # Authorize the trading account
        return self._authorize_account()

    def _authorize_account(self):
        """Authorize the trading account"""
        print(f"Authorizing account {self.ctid_trader_account_id}...")
        
        if not self.access_token:
            raise Exception("Cannot authorize account: access token is None")
            
        acc_auth_req = ProtoOAAccountAuthReq()
        acc_auth_req.ctidTraderAccountId = self.ctid_trader_account_id
        acc_auth_req.accessToken = self.access_token

        self._account_auth_deferred = Deferred()
        self.websocket_client.send(acc_auth_req)
        
        # Set timeout
        from twisted.internet import reactor
        self._account_auth_deferred.addTimeout(10, reactor)
        
        self._account_auth_deferred.addCallback(self._on_account_authorized)
        self._account_auth_deferred.addErrback(self._on_auth_error)
        return self._account_auth_deferred

    def _on_account_authorized(self, response):
        """Handle account authorization response"""
        self._is_account_authorized = True
        print(f"Account {self.ctid_trader_account_id} for client {self.account_id} authorized.")
        return response

    def get_symbols(self) -> Deferred:
        """Gets all available symbols for the trading account."""
        if not self._is_account_authorized:
            raise Exception("Account not authorized yet")
            
        request = ProtoOASymbolsListReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
        return self._send_request(request, ProtoOASymbolsListRes().payloadType)

    def place_order(self, symbol_id: int, order_type: ProtoOAOrderType, trade_side: ProtoOATradeSide,
                          volume: int, stop_loss: float = None, take_profit: float = None) -> Deferred:
        """Places a new trading order."""
        if not self._is_account_authorized:
            raise Exception("Account not authorized yet")
            
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

        return self._send_request(request, ProtoOANewOrderRes().payloadType)

    def modify_position(self, position_id: int, stop_loss: float = None, take_profit: float = None, trailing_stop: bool = False) -> Deferred:
        """Modifies an existing position."""
        if not self._is_account_authorized:
            raise Exception("Account not authorized yet")
            
        request = ProtoOAAmendPositionSLTPReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
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
        self.websocket_client.startService()

    def subscribe_to_ticks(self, symbol_id: int) -> Deferred:
        if not self._is_account_authorized:
            raise Exception("Account not authorized yet")
            
        request = ProtoOASubscribeSpotsReq()
        request.ctidTraderAccountId = self.ctid_trader_account_id
        request.symbolId.append(symbol_id)
        return self._send_request(request, ProtoOASubscribeSpotsRes().payloadType)

    def subscribe_to_execution_events(self, callback: Callable):
        """Subscribes to execution events."""
        self._execution_event_callbacks.append(callback)

    def is_ready(self):
        """Check if the client is fully authenticated and authorized"""
        return self._is_app_authenticated and self._is_account_authorized