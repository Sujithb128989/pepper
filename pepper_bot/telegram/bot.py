from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pepper_bot.core.config import get_all_settings, set_setting
from pepper_bot.core.database import get_all_trades
from pepper_bot.telegram.menus import main_menu, settings_menu, pair_selection_menu

# States for conversation
SELECTING_ACTION, SELECTING_PAIR_SL, SETTING_SL, SELECTING_PAIR_TS, SETTING_TS, SELECTING_PAIR_VOL, SETTING_VOL = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu."""
    await update.message.reply_text(
        "Welcome to Pepper, your cTrader trading bot!",
        reply_markup=main_menu(),
    )
    return SELECTING_ACTION

async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    if query.data == "settings":
        await query.edit_message_text(text="Settings Menu", reply_markup=settings_menu())
        return SELECTING_ACTION
    else:
        await query.edit_message_text(text=f"Selected option: {query.data}", reply_markup=main_menu())
        return ConversationHandler.END

async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        await query.edit_message_text(text="Main Menu", reply_markup=main_menu())
        return ConversationHandler.END
    elif query.data.startswith("toggle_pair_"):
        pair = query.data.split("_")[-1]
        pairs = get_all_settings()["pairs"]
        pairs[pair] = not pairs[pair]
        set_setting("pairs", pairs)
        await query.edit_message_text(text="Settings Menu", reply_markup=settings_menu())
        return SELECTING_ACTION
    elif query.data == "set_sl":
        await query.edit_message_text(text="Select a pair to set the stop loss for:", reply_markup=pair_selection_menu("sl"))
        return SELECTING_PAIR_SL
    elif query.data == "set_ts":
        await query.edit_message_text(text="Select a pair to set the trailing stop for:", reply_markup=pair_selection_menu("ts"))
        return SELECTING_PAIR_TS
    elif query.data == "set_vol":
        await query.edit_message_text(text="Select a pair to set the volume for:", reply_markup=pair_selection_menu("vol"))
        return SELECTING_PAIR_VOL

async def select_pair_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the selected pair and asks for the stop loss value."""
    query = update.callback_query
    await query.answer()

    context.user_data["pair_to_set"] = query.data.split("_")[-1]
    await query.edit_message_text(text=f"Enter the stop loss in ticks for {context.user_data['pair_to_set']}:")
    return SETTING_SL

async def set_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the stop loss value."""
    pair = context.user_data["pair_to_set"]
    sl = int(update.message.text)

    settings = get_all_settings()
    settings["stop_loss"][pair] = sl
    set_setting("stop_loss", settings["stop_loss"])

    await update.message.reply_text(f"Stop loss for {pair} set to {sl} ticks.")
    await update.message.reply_text("Settings Menu", reply_markup=settings_menu())
    return SELECTING_ACTION

async def select_pair_ts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the selected pair and asks for the trailing stop value."""
    query = update.callback_query
    await query.answer()

    context.user_data["pair_to_set"] = query.data.split("_")[-1]
    await query.edit_message_text(text=f"Enter the trailing stop in ticks for {context.user_data['pair_to_set']}:")
    return SETTING_TS

async def set_ts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the trailing stop value."""
    pair = context.user_data["pair_to_set"]
    ts = int(update.message.text)

    settings = get_all_settings()
    settings["trailing_stop"][pair] = ts
    set_setting("trailing_stop", settings["trailing_stop"])

    await update.message.reply_text(f"Trailing stop for {pair} set to {ts} ticks.")
    await update.message.reply_text("Settings Menu", reply_markup=settings_menu())
    return SELECTING_ACTION

async def select_pair_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the selected pair and asks for the volume value."""
    query = update.callback_query
    await query.answer()

    context.user_data["pair_to_set"] = query.data.split("_")[-1]
    await query.edit_message_text(text=f"Enter the volume for {context.user_data['pair_to_set']}:")
    return SETTING_VOL

async def set_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the volume value."""
    pair = context.user_data["pair_to_set"]
    vol = float(update.message.text)

    settings = get_all_settings()
    settings["volume"][pair] = vol
    set_setting("volume", settings["volume"])

    await update.message.reply_text(f"Volume for {pair} set to {vol}.")
    await update.message.reply_text("Settings Menu", reply_markup=settings_menu())
    return SELECTING_ACTION

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the bot's trading statistics."""
    trades = get_all_trades()

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    win_rate = len(wins) / len(trades) * 100 if trades else 0
    total_pnl = sum(t["pnl"] for t in trades)

    # We'll need to get the initial balance from somewhere,
    # but for now, we'll just show the total PnL.

    stats_message = (
        f"📊 *Trading Statistics* 📊\n\n"
        f"Total Trades: {len(trades)}\n"
        f"Wins: {len(wins)}\n"
        f"Losses: {len(losses)}\n"
        f"Win Rate: {win_rate:.2f}%\n"
        f"Total PnL: {total_pnl:.2f}\n"
    )

    await update.message.reply_text(stats_message, parse_mode="Markdown")

def run_bot(token: str):
    """Runs the Telegram bot."""
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(main_menu_button, pattern="^(?!settings).*$"), CallbackQueryHandler(settings_button)],
            SELECTING_PAIR_SL: [CallbackQueryHandler(select_pair_sl)],
            SETTING_SL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_sl)],
            SELECTING_PAIR_TS: [CallbackQueryHandler(select_pair_ts)],
            SETTING_TS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_ts)],
            SELECTING_PAIR_VOL: [CallbackQueryHandler(select_pair_vol)],
            SETTING_VOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_vol)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", stats))

    application.run_polling()
