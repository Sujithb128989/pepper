import os

def load_credentials():
    """
    Loads credentials from environment variables.
    Raises an exception if any required variable is missing.
    """
    client_id = os.environ.get("CTRADER_CLIENT_ID")
    client_secret = os.environ.get("CTRADER_CLIENT_SECRET")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not all([client_id, client_secret, telegram_token]):
        raise ValueError(
            "Missing one or more required environment variables: "
            "CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET, TELEGRAM_BOT_TOKEN"
        )

    return {
        "clientId": client_id,
        "clientSecret": client_secret,
        "telegram_token": telegram_token,
    }
