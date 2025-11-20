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
from urllib.parse import urlparse, parse_qs
from twisted.internet import defer, reactor


from pepper_bot.core.config import get_all_settings, set_setting
from pepper_bot.core.database import get_all_trades
from pepper_bot.ctrader.auth import get_access_token, get_credentials
from pepper_bot.telegram.menus import main_menu, settings_menu, pair_selection_menu

# States for conversation
SELECTING_ACTION, SELECTING_PAIR_SL, SETTING_SL, SELECTING_PAIR_TS, SETTING_TS, SELECTING_PAIR_VOL, SETTING_VOL, AWAITING_AUTH, SELECTING_ACCOUNTS = range(9)

async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu."""
    credentials = get_credentials()
    if not credentials.get("accessToken"):
        await update.message.reply_text(
            "🤖 *Welcome to Pepper Trading Bot*\n\n"
            "Your automated cTrader straddle strategy assistant.\n\n"
            "⚠️ You need to authorize first.\n"
            "Use /authorize to connect your cTrader account.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🚀 *Pepper Trading Bot*\n\n"
        "Ready to execute straddle strategies!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    return SELECTING_ACTION

async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the authorization conversation."""
    credentials = get_credentials()
    client_id = credentials["clientId"]
    redirect_uri = "https://spotware.com" # Must match registered redirect URI

    auth_url = f"https://id.ctrader.com/my/settings/openapi/grantingaccess/?client_id={client_id}&redirect_uri={redirect_uri}&scope=trading&product=web"

    try:
        await update.message.reply_text(
            "🔐 *Authorization Required*\n\n"
            "1️⃣ Click the link below\n"
            "2️⃣ Authorize the app in cTrader\n"
            "3️⃣ Copy the full redirect URL\n"
            "4️⃣ Paste it back here",
            parse_mode="Markdown"
        )
        await update.message.reply_text(auth_url)
    except (AttributeError, TypeError):
        # Handle case where update.message is None (callback query)
        await update.callback_query.message.reply_text(
            "🔐 *Authorization Required*\n\n"
            "1️⃣ Click the link below\n"
            "2️⃣ Authorize the app in cTrader\n"
            "3️⃣ Copy the full redirect URL\n"
            "4️⃣ Paste it back here",
            parse_mode="Markdown"
        )
        await update.callback_query.message.reply_text(auth_url)

    context.user_data["redirect_uri"] = redirect_uri
    return AWAITING_AUTH

async def awaiting_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the redirect URL."""
    redirect_uri = context.user_data["redirect_uri"]
    url = urlparse(update.message.text)
    query = parse_qs(url.query)
    auth_code = query["code"][0]

    try:
        # Convert Twisted Deferred to asyncio Future
        loop = asyncio.get_event_loop()
        d = get_access_token(auth_code, redirect_uri)
        
        future = loop.create_future()
        
        def on_success(result):
            loop.call_soon_threadsafe(future.set_result, result)
        
        def on_error(failure):
            loop.call_soon_threadsafe(future.set_exception, failure.value)
        
        d.addCallback(on_success)
        d.addErrback(on_error)
        
        await future
        
        await update.message.reply_text(
            "✅ *Authorization Successful!*\n\n"
            "Use /start to begin trading.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Authorization failed: {str(e)}")

    return ConversationHandler.END

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
        message = "Available trading accounts:\n"
        for i, (account, balance) in enumerate(account_details):
            message += f"{i+1}. Account ID: {account.ctidTraderAccountId}, Balance: {balance:.2f} {account.currency}\n"
        message += "\nPlease select two accounts for the straddle strategy (e.g., '1 2'):"
        await update.message.reply_text(message)
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
async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for main menu buttons."""
    pass

async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for settings button."""
    pass

async def select_pair_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for selecting pair for stop loss."""
    pass

async def set_sl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for setting stop loss."""
    pass

async def select_pair_ts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for selecting pair for take profit."""
    pass

async def set_ts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for setting take profit."""
    pass

async def select_pair_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for selecting pair for volume."""
    pass

async def set_vol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for setting volume."""
    pass

# ... (rest of the bot code)

async def run_bot(token: str, ctrader_manager):
    """Runs the Telegram bot."""
    # Store ctrader_manager in a module-level variable so handlers can access it
    global _ctrader_manager
    _ctrader_manager = ctrader_manager
    
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", _start), CommandHandler("authorize", authorize), CommandHandler("select_accounts", select_accounts)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(main_menu_button, pattern="^(?!settings).*$"), CallbackQueryHandler(settings_button)],
            SELECTING_PAIR_SL: [CallbackQueryHandler(select_pair_sl)],
            SETTING_SL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_sl)],
            SELECTING_PAIR_TS: [CallbackQueryHandler(select_pair_ts)],
            SETTING_TS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_ts)],
            SELECTING_PAIR_VOL: [CallbackQueryHandler(select_pair_vol)],
            SETTING_VOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_vol)],
            AWAITING_AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, awaiting_auth)],
            SELECTING_ACCOUNTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_accounts)],
        },
        fallbacks=[CommandHandler("start", _start)],
    )

    application.add_handler(conv_handler)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
