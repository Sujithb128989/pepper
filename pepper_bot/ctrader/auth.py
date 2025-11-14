import json
from typing import Dict, Any

import treq
from twisted.internet.defer import Deferred

CREDENTIALS_FILE = "pepper_bot/core/credentials.json"
TOKEN_URL = "https://openapi.ctrader.com/apps/token"


def _load_credentials() -> Dict[str, Any]:
    """Loads credentials from the JSON file."""
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_credentials(credentials: Dict[str, Any]) -> None:
    """Saves credentials to the JSON file."""
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)


def get_access_token(account_id: str, authorization_code: str, redirect_uri: str) -> Deferred:
    """
    Exchanges an authorization code for an access token and refresh token.
    This is typically a one-time operation for initial setup.
    """
    credentials = _load_credentials()

    params = {
        "grant_type": b"authorization_code",
        "code": authorization_code.encode("utf-8"),
        "redirect_uri": redirect_uri.encode("utf-8"),
        "client_id": credentials["clientId"].encode("utf-8"),
        "client_secret": credentials["clientSecret"].encode("utf-8"),
    }

    d = treq.get(TOKEN_URL, params=params)
    d.addCallback(treq.json_content)

    def on_token_data(token_data):
        credentials["accounts"][account_id]["accessToken"] = token_data["accessToken"]
        credentials["accounts"][account_id]["refreshToken"] = token_data["refreshToken"]
        _save_credentials(credentials)
        return token_data

    d.addCallback(on_token_data)
    return d


def refresh_access_token(account_id: str) -> Deferred:
    """Refreshes an access token using a refresh token."""
    credentials = _load_credentials()
    account_creds = credentials.get("accounts", {}).get(account_id)
    if not account_creds or not account_creds.get("refreshToken"):
        raise ValueError(f"No refresh token found for account: {account_id}")

    params = {
        "grant_type": b"refresh_token",
        "refresh_token": account_creds["refreshToken"].encode("utf-8"),
        "client_id": credentials["clientId"].encode("utf-8"),
        "client_secret": credentials["clientSecret"].encode("utf-8"),
    }

    d = treq.post(TOKEN_URL, params=params)
    d.addCallback(treq.json_content)

    def on_token_data(token_data):
        credentials["accounts"][account_id]["accessToken"] = token_data["accessToken"]
        credentials["accounts"][account_id]["refreshToken"] = token_data["refreshToken"]
        _save_credentials(credentials)
        return token_data

    d.addCallback(on_token_data)
    return d


def get_credentials(account_id: str) -> Dict[str, Any]:
    """Gets the credentials for a specific account."""
    credentials = _load_credentials()
    return {
        "clientId": credentials.get("clientId"),
        "clientSecret": credentials.get("clientSecret"),
        **credentials.get("accounts", {}).get(account_id, {})
    }
