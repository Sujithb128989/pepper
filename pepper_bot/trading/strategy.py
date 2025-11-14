from twisted.internet.defer import Deferred, gatherResults

from pepper_bot.core.config import get_all_settings
from pepper_bot.ctrader.client import CTraderApiClient
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide

def place_straddle_trade(client1: CTraderApiClient, client2: CTraderApiClient, symbol_id: int, symbol_name: str) -> Deferred:
    """
    Places a straddle trade (simultaneous BUY and SELL orders) on the given symbol.
    """
    settings = get_all_settings()
    volume = settings["volume"][symbol_name]
    stop_loss = settings["stop_loss"][symbol_name]

    print(f"Placing straddle trade for symbol {symbol_name} with volume {volume} and stop loss {stop_loss} ticks...")

    # We need to convert the volume and stop loss to the correct format for the API.
    # For now, we'll just pass them as is.

    buy_order_deferred = client1.place_order(
        symbol_id=symbol_id,
        order_type=ProtoOAOrderType.MARKET,
        trade_side=ProtoOATradeSide.BUY,
        volume=volume,
        stop_loss=stop_loss
    )

    sell_order_deferred = client2.place_order(
        symbol_id=symbol_id,
        order_type=ProtoOAOrderType.MARKET,
        trade_side=ProtoOATradeSide.SELL,
        volume=volume,
        stop_loss=stop_loss
    )

    d = gatherResults([buy_order_deferred, sell_order_deferred])

    def on_orders_placed(results):
        buy_order, sell_order = results
        print(f"Straddle trade placed successfully:")
        print(f"  BUY order: {buy_order}")
        print(f"  SELL order: {sell_order}")
        return buy_order, sell_order

    d.addCallback(on_orders_placed)
    return d
