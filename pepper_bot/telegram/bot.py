import json
from typing import Dict, Any, List, Callable

import treq
from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks

class TelegramBot:
    """A Twisted-native client for the Telegram Bot API."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}/"
        self._offset = 0
        self._command_handlers: Dict[str, Callable] = {}
        self._callback_handlers: Dict[str, Callable] = {}

    def add_command_handler(self, command: str, handler: Callable):
        """Adds a command handler."""
        self._command_handlers[command] = handler

    def add_callback_handler(self, callback_data: str, handler: Callable):
        """Adds a callback query handler."""
        self._callback_handlers[callback_data] = handler

    @inlineCallbacks
    def _poll(self):
        """Polls the Telegram API for new updates."""
        try:
            response = yield treq.get(
                self.base_url + "getUpdates",
                params={"offset": self._offset + 1, "timeout": 30},
            )
            content = yield response.json()

            if content["ok"]:
                for update in content["result"]:
                    self._offset = update["update_id"]
                    self._handle_update(update)
        except Exception as e:
            print(f"Error while polling for Telegram updates: {e}")

        reactor.callLater(0.1, self._poll)

    def _handle_update(self, update: Dict[str, Any]):
        """Handles an incoming update from the Telegram API."""
        if "message" in update and "text" in update["message"]:
            message = update["message"]
            text = message["text"]
            if text.startswith("/"):
                command = text.split(" ")[0][1:]
                if command in self._command_handlers:
                    self._command_handlers[command](message)
        elif "callback_query" in update:
            callback_query = update["callback_query"]
            callback_data = callback_query["data"]
            if callback_data in self._callback_handlers:
                self._callback_handlers[callback_data](callback_query)

    def send_message(self, chat_id: int, text: str, reply_markup: Dict[str, Any] = None) -> Deferred:
        """Sends a message to a chat."""
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        return treq.post(self.base_url + "sendMessage", json=payload)

    def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup: Dict[str, Any] = None) -> Deferred:
        """Edits a message in a chat."""
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        return treq.post(self.base_url + "editMessageText", json=payload)

    def run(self):
        """Starts the bot."""
        print("Telegram bot started.")
        self._poll()
