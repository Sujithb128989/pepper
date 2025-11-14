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
from urllib.parse import urlparse, parse_qs


from pepper_bot.core.config import get_all_settings, set_setting
from pepper_bot.core.database import get_all_trades
from pepper_bot.ctrader.auth import get_access_token
from pepper_bot.telegram.menus import main_menu, settings_menu, pair_selection_menu

# States for conversation
SELECTING_ACTION, SELECTING_PAIR_SL, SETTING_SL, SELECTING_PAIR_TS, SETTING_TS, SELECTING_PAIR_VOL, SETTING_VOL, AWAITING_AUTH_1, AWAITING_AUTH_2 = range(9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu."""
    await update.message.reply_text(
        "Welcome to Pepper, your cTrader trading bot!",
        reply_markup=main_menu(),
    )
    return SELECTING_ACTION

async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the authorization conversation."""
    credentials = get_all_settings()
    client_id = credentials["clientId"]
    redirect_uri = "https://example.com" # This can be any URL

    auth_url = f"https://id.ctrader.com/my/settings/openapi/grantingaccess/?client_id={client_id}&redirect_uri={redirect_uri}&scope=trading&product=web"

    await update.message.reply_text(
        "Please authorize the bot for your first sub-account by visiting the following URL. "
        "After you have authorized the bot, please paste the full redirect URL back into this chat."
    )
    await update.message.reply_text(auth_url)

    context.user_data["redirect_uri"] = redirect_uri
    return AWAITING_AUTH_1

async def awaiting_auth_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the redirect URL for the first sub-account."""
    redirect_uri = context.user_data["redirect_uri"]
    url = urlparse(update.message.text)
    query = parse_qs(url.query)
    auth_code = query["code"][0]

    await get_access_token("account1", auth_code, redirect_uri)

    await update.message.reply_text("Account 1 authorized successfully.")

    credentials = get_all_settings()
    client_id = credentials["clientId"]

    auth_url = f"https://id.ctrader.com/my/settings/openapi/grantingaccess/?client_id={client_id}&redirect_uri={redirect_uri}&scope=trading&product=web"

    await update.message.reply_text(
        "Please authorize the bot for your second sub-account by visiting the following URL. "
        "After you have authorized the bot, please paste the full redirect URL back into this chat."
    )
    await update.message.reply_text(auth_url)

    return AWAITING_AUTH_2

async def awaiting_auth_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the redirect URL for the second sub-account."""
    redirect_uri = context.user_data["redirect_uri"]
    url = urlparse(update.message.text)
    query = parse_qs(url.query)
    auth_code = query["code"][0]

    await get_access_token("account2", auth_code, redirect_uri)

    await update.message.reply_text("Account 2 authorized successfully.")

    return ConversationHandler.END

# ... (rest of the bot code)

def run_bot(token: str):
    """Runs the Telegram bot."""
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("authorize", authorize)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(main_menu_button, pattern="^(?!settings).*$"), CallbackQueryHandler(settings_button)],
            SELECTING_PAIR_SL: [CallbackQueryHandler(select_pair_sl)],
            SETTING_SL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_sl)],
            SELECTING_PAIR_TS: [CallbackQueryHandler(select_pair_ts)],
            SETTING_TS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_ts)],
            SELECTING_PAIR_VOL: [CallbackQueryHandler(select_pair_vol)],
            SETTING_VOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_vol)],
            AWAITING_AUTH_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, awaiting_auth_1)],
            AWAITING_AUTH_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, awaiting_auth_2)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", stats))

    application.run_polling()
