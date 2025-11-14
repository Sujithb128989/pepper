import sqlite3
from typing import Dict, Any, List
import threading
import os

# Build the absolute path to the database file
_DB_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(_DB_DIR, "trades.db")

_lock = threading.Lock()

def initialize_db():
    """Initializes the database and creates the trades table if it doesn't exist."""
    with _lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    pnl REAL NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

def log_trade(trade_data: Dict[str, Any]):
    """Logs a completed trade to the database."""
    with _lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (symbol, side, entry_price, exit_price, pnl, duration_seconds)
                VALUES (:symbol, :side, :entry_price, :exit_price, :pnl, :duration_seconds)
            """, trade_data)
            conn.commit()

def get_all_trades() -> List[Dict[str, Any]]:
    """Retrieves all trades from the database."""
    with _lock:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
