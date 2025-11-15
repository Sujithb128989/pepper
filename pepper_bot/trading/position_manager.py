from typing import Dict, Any

from pepper_bot.core.config import get_all_settings
from pepper_bot.core.database import log_trade
from pepper_bot.ctrader.client import CTraderApiClient
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAExecutionType, ProtoOATradeSide

class PositionManager:
    """
    Manages the open positions and the state machine for the straddle trade.
    """
    def __init__(self, client: CTraderApiClient, account1_id: int, account2_id: int):
        self.client = client
        self.account1_id = account1_id
        self.account2_id = account2_id
        self.active_straddles: Dict[str, Any] = {}

    def start_monitoring(self):
        """Starts monitoring the execution events."""
        self.client.subscribe_to_execution_events(self.handle_execution_event)

    def handle_execution_event(self, event: Any):
        """Handles an execution event from the cTrader API."""
        if event.executionType != ProtoOAExecutionType.ORDER_FILLED and event.executionType != ProtoOAExecutionType.ORDER_CLOSED:
            return

        position_id = event.order.positionId

        for symbol, straddle in self.active_straddles.items():
            if straddle["buy"].order.positionId == position_id:
                self.handle_straddle_event(symbol, "buy", event)
            elif straddle["sell"].order.positionId == position_id:
                self.handle_straddle_event(symbol, "sell", event)

    def handle_straddle_event(self, symbol: str, side: str, event: Any):
        """Handles an execution event for a straddle trade."""
        straddle = self.active_straddles[symbol]

        if straddle["state"] == "OPEN" and event.executionType == ProtoOAExecutionType.ORDER_CLOSED:
            # One leg of the straddle has closed, so the other is the winner
            winner_side = "buy" if side == "sell" else "sell"
            winner = straddle[winner_side]

            # Move the winner's stop loss to break-even and activate the trailing stop
            settings = get_all_settings()
            trailing_stop = settings["trailing_stop"][symbol]

            self.client.modify_position(
                ctid_trader_account_id=winner.order.ctidTraderAccountId,
                position_id=winner.order.positionId,
                stop_loss=winner.order.openPrice,
                trailing_stop=trailing_stop
            )

            straddle["state"] = "ONE_LEG_CLOSED"
        elif straddle["state"] == "ONE_LEG_CLOSED" and event.executionType == ProtoOAExecutionType.ORDER_CLOSED:
            # The second leg of the straddle has closed, so the trade is complete
            # Log the trade to the database
            # This is a placeholder for the actual logic
            print(f"Straddle trade for {symbol} is complete.")

            del self.active_straddles[symbol]


    def add_straddle(self, symbol: str, buy_order: Any, sell_order: Any):
        """Adds a new straddle trade to the position manager."""
        self.active_straddles[symbol] = {
            "buy": buy_order,
            "sell": sell_order,
            "state": "OPEN",  # Can be OPEN, ONE_LEG_CLOSED
        }
