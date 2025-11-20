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
import asyncio
from twisted.internet import defer, reactor


from pepper_bot.core.config import get_all_settings, set_setting
from pepper_bot.core.database import get_all_trades
from pepper_bot.ctrader.auth import get_credentials
from pepper_bot.telegram.menus import main_menu, settings_menu, pair_selection_menu

# Authorized chat ID - only this user can use the bot
AUTHORIZED_CHAT_ID = 5705498219

# States for conversation
SELECTING_ACTION, SELECTING_PAIR_SL, SETTING_SL, SELECTING_PAIR_TS, SETTING_TS, SELECTING_PAIR_VOL, SETTING_VOL, SELECTING_ACCOUNTS = range(8)

def check_authorized(func):
    """Decorator to check if user is authorized"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != AUTHORIZED_CHAT_ID:
            try:
                await update.message.reply_text("⛔ Unauthorized access denied.")
            except:
                await update.callback_query.message.reply_text("⛔ Unauthorized access denied.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper

@check_authorized
async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu."""
    await update.message.reply_text(
        "🚀 *Pepper Trading Bot*\n\n"
        "Ready to execute straddle strategies!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    return SELECTING_ACTION

@check_authorized
async def select_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the account selection process."""
    global _ctrader_manager
    ctrader_manager = _ctrader_manager
    accounts = await ctrader_manager.get_trader_accounts()

    account_details = []
    for account in accounts:
        balance = await ctrader_manager.get_account_balance(account.ctidTraderAccountId)
        account_details.append((account, balance / 100.0))

    if len(account_details) < 2:
        await update.message.reply_text(
            "❌ *Error*\n\n"
            "At least two trading accounts are required for the straddle strategy.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    elif len(account_details) == 2:
        await update.message.reply_text(
            "✅ *Accounts Auto-Selected*\n\n"
            "Found exactly 2 accounts. Automatically configured for straddle strategy.",
            parse_mode="Markdown"
        )
        account1 = account_details[0][0]
        account2 = account_details[1][0]
    else:
        # Get user selection
        message = "📊 *Available Trading Accounts*\n\n"
        for i, (account, balance) in enumerate(account_details):
            message += f"{i+1}. ID: `{account.ctidTraderAccountId}`\n"
            message += f"   Balance: {balance:.2f} {getattr(account, 'currency', 'USD')}\n\n"
        message += "Reply with two numbers (BUY SELL):\n"
        message += "Example: `1 2`"
        await update.message.reply_text(message, parse_mode="Markdown")
        context.application.user_data["account_details"] = account_details
        return SELECTING_ACCOUNTS

    context.application.user_data["account1"] = account1
    context.application.user_data["account2"] = account2
    await update.message.reply_text(
        "✅ *Accounts Selected*\n\n"
        "Configuration complete. Use /start to trade.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

@check_authorized
async def set_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets the selected accounts."""
    selection = update.message.text
    try:
        index1, index2 = [int(i) - 1 for i in selection.split()]
        account_details = context.application.user_data["account_details"]
        account1 = account_details[index1][0]
        account2 = account_details[index2][0]
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ *Invalid Selection*\n\n"
            "Please enter two valid numbers separated by a space.\n"
            "Example: `1 2`",
            parse_mode="Markdown"
        )
        return SELECTING_ACCOUNTS

    context.application.user_data["account1"] = account1
    context.application.user_data["account2"] = account2
    await update.message.reply_text(
        "✅ *Accounts Selected*\n\n"
        "Configuration complete. Use /start to trade.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Placeholder handler functions
@check_authorized
async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for main menu buttons."""
    pass

@check_authorized
async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for settings button."""
    pass

@check_authorized
async def select_pair_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for selecting pair for stop loss."""
    pass

@check_authorized
async def set_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for setting stop loss."""
    pass

@check_authorized
async def select_pair_ts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for selecting pair for take profit."""
    pass

@check_authorized
async def set_ts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for setting take profit."""
    pass

@check_authorized
async def select_pair_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for selecting pair for volume."""
    pass

@check_authorized
async def set_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for setting volume."""
    pass

async def run_bot(token: str, ctrader_manager):
    """Runs the Telegram bot."""
    # Store ctrader_manager in a module-level variable so handlers can access it
    global _ctrader_manager
    _ctrader_manager = ctrader_manager
    
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", _start), CommandHandler("select_accounts", select_accounts)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(main_menu_button, pattern="^(?!settings).*$"), CallbackQueryHandler(settings_button)],
            SELECTING_PAIR_SL: [CallbackQueryHandler(select_pair_sl)],
            SETTING_SL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_sl)],
            SELECTING_PAIR_TS: [CallbackQueryHandler(select_pair_ts)],
            SETTING_TS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_ts)],
            SELECTING_PAIR_VOL: [CallbackQueryHandler(select_pair_vol)],
            SETTING_VOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_vol)],
            SELECTING_ACCOUNTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_accounts)],
        },
        fallbacks=[CommandHandler("start", _start)],
    )

    application.add_handler(conv_handler)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
