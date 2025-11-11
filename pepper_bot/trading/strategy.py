import asyncio
from typing import Dict, Any

from pepper_bot.core.config import get_all_settings
from pepper_bot.ctrader.manager import CTraderManager
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide

async def place_straddle_trade(manager: CTraderManager, symbol_id: int, symbol_name: str):
    """
    Places a straddle trade (simultaneous BUY and SELL orders) on the given symbol.
    """
    settings = get_all_settings()
    volume = settings["volume"][symbol_name]
    stop_loss = settings["stop_loss"][symbol_name]

    print(f"Placing straddle trade for symbol {symbol_name} with volume {volume} and stop loss {stop_loss} ticks...")

    # We need to convert the volume and stop loss to the correct format for the API.
    # For now, we'll just pass them as is.

    buy_order_task = manager.place_order(
        "account1",
        symbol_id=symbol_id,
        order_type=ProtoOAOrderType.MARKET,
        trade_side=ProtoOATradeSide.BUY,
        volume=volume,
        stop_loss=stop_loss
    )

    sell_order_task = manager.place_order(
        "account2",
        symbol_id=symbol_id,
        order_type=ProtoOAOrderType.MARKET,
        trade_side=ProtoOATradeSide.SELL,
        volume=volume,
        stop_loss=stop_loss
    )

    buy_order, sell_order = await asyncio.gather(buy_order_task, sell_order_task)

    print(f"Straddle trade placed successfully:")
    print(f"  BUY order: {buy_order}")
    print(f"  SELL order: {sell_order}")

    return buy_order, sell_order
