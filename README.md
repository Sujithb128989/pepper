# Pepper Trading Bot

Automated straddle trading bot using Pepperstone cTrader API.

## Strategy
- Simultaneous BUY/SELL execution
- Automatic stop-loss management
- Tick-based trailing stops
- Two sub-account hedging

## Instruments
- EURUSD
- GBPUSD
- XAUUSD
- NAS100

## Configuration

This bot is configured using environment variables. You will need to set the following variables before running the bot:

- `CTRADER_CLIENT_ID`: Your cTrader application client ID.
- `CTRADER_CLIENT_SECRET`: Your cTrader application client secret.
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token.

### For Linux and macOS:

export CTRADER_CLIENT_ID="your_client_id"
export CTRADER_CLIENT_SECRET="your_client_secret"
export TELEGRAM_BOT_TOKEN="your_telegram_token"

### For Windows (PowerShell):

$env:CTRADER_CLIENT_ID="your_client_id"
$env:CTRADER_CLIENT_SECRET="your_client_secret"
$env:TELEGRAM_BOT_TOKEN="your_telegram_token"

## Status
Development in progress using demo accounts.
