from typing import Dict, Any

import treq
from twisted.internet.defer import Deferred

from pepper_bot.core.env import load_credentials

TOKEN_URL = "https://openapi.ctrader.com/apps/token"


def get_access_token(authorization_code: str, redirect_uri: str) -> Deferred:
    """
    Exchanges an authorization code for an access token and refresh token.
    """
    credentials = get_credentials()

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
        # In-memory update, no saving to file
        credentials["accessToken"] = token_data["accessToken"]
        credentials["refreshToken"] = token_data["refreshToken"]
        return token_data

    d.addCallback(on_token_data)
    return d


def refresh_access_token() -> Deferred:
    """Refreshes an access token using a refresh token."""
    credentials = get_credentials()
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
        return token_data

    d.addCallback(on_token_data)
    return d


def get_credentials() -> Dict[str, Any]:
    """Gets the credentials for the application."""
    return load_credentials()
