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


def get_access_token(authorization_code: str, redirect_uri: str) -> Deferred:
    """
    Exchanges an authorization code for an access token and refresh token.
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
        credentials["accessToken"] = token_data["accessToken"]
        credentials["refreshToken"] = token_data["refreshToken"]
        _save_credentials(credentials)
        return token_data

    d.addCallback(on_token_data)
    return d


def refresh_access_token() -> Deferred:
    """Refreshes an access token using a refresh token."""
    credentials = _load_credentials()
    if not credentials.get("refreshToken"):
        raise ValueError("No refresh token found.")

    params = {
        "grant_type": b"refresh_token",
        "refresh_token": credentials["refreshToken"].encode("utf-8"),
        "client_id": credentials["clientId"].encode("utf-8"),
        "client_secret": credentials["clientSecret"].encode("utf-8"),
    }

    d = treq.post(TOKEN_URL, params=params)
    d.addCallback(treq.json_content)

    def on_token_data(token_data):
        credentials["accessToken"] = token_data["accessToken"]
        credentials["refreshToken"] = token_data["refreshToken"]
        _save_credentials(credentials)
        return token_data

    d.addCallback(on_token_data)
    return d


def get_credentials() -> Dict[str, Any]:
    """Gets the credentials for the application."""
    return _load_credentials()
