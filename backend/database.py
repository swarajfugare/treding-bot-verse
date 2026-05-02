import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

DB_LOCK = threading.RLock()
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "pulsex.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BASE_DIR / DATABASE_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_LOCK, get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                api_key_encrypted TEXT NOT NULL,
                api_secret_encrypted TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS balances (
                mode TEXT PRIMARY KEY,
                inr_balance REAL NOT NULL DEFAULT 0,
                usdt_balance REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL DEFAULT 'PAPER',
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                allocated_balance REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                status TEXT NOT NULL,
                pnl REAL NOT NULL DEFAULT 0,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                reason TEXT NOT NULL,
                confidence INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL DEFAULT 'PAPER',
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                ema9 REAL NOT NULL,
                ema21 REAL NOT NULL,
                rsi REAL NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                trend TEXT NOT NULL DEFAULT 'SIDEWAYS',
                confidence INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL DEFAULT 'PAPER',
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(conn, "trades", "mode", "TEXT NOT NULL DEFAULT 'PAPER'")
        _ensure_column(conn, "decisions", "mode", "TEXT NOT NULL DEFAULT 'PAPER'")
        _ensure_column(conn, "decisions", "price", "REAL NOT NULL DEFAULT 0")
        _ensure_column(conn, "decisions", "trend", "TEXT NOT NULL DEFAULT 'SIDEWAYS'")
        _ensure_column(conn, "bot_events", "mode", "TEXT NOT NULL DEFAULT 'PAPER'")
        if get_setting("mode") is None:
            existing_mode = get_setting("current_mode") or "PAPER"
            set_setting("mode", normalize_mode(existing_mode))
        set_setting("current_mode", get_setting("mode") or "PAPER")
        if get_setting("paper_trading") is None:
            set_setting("paper_trading", str(get_setting("mode") != "LIVE").lower())
        if get_setting("paper_balance") is None:
            set_setting("paper_balance", os.getenv("PAPER_BALANCE", "10000"))
        if get_setting("paper_inr_balance") is None:
            set_setting("paper_inr_balance", os.getenv("PAPER_INR_BALANCE", "0"))
        if get_setting("live_inr_balance") is None:
            set_setting("live_inr_balance", os.getenv("LIVE_INR_BALANCE", "0"))
        if get_setting("live_usdt_balance") is None:
            set_setting("live_usdt_balance", os.getenv("LIVE_USDT_BALANCE", "0"))
        _seed_balance_row(
            conn,
            "PAPER",
            float(get_setting("paper_inr_balance") or 0),
            float(get_setting("paper_balance") or 10000),
        )
        _seed_balance_row(
            conn,
            "LIVE",
            float(get_setting("live_inr_balance") or 0),
            float(get_setting("live_usdt_balance") or 0),
        )
        conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_balance_row(conn: sqlite3.Connection, mode: str, inr_balance: float, usdt_balance: float) -> None:
    conn.execute(
        """
        INSERT INTO balances (mode, inr_balance, usdt_balance, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(mode) DO NOTHING
        """,
        (mode, inr_balance, usdt_balance, now_iso()),
    )


def dict_row(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


def get_setting(key: str) -> Optional[str]:
    with DB_LOCK, get_connection() as conn:
        table = "app_settings" if key in {"mode"} else "settings"
        try:
            row = conn.execute(f"SELECT value FROM {table} WHERE key = ?", (key,)).fetchone()
        except sqlite3.OperationalError:
            return None
        return row["value"] if row else None


def set_setting(key: str, value: Any) -> None:
    with DB_LOCK, get_connection() as conn:
        table = "app_settings" if key in {"mode"} else "settings"
        conn.execute(
            f"""
            INSERT INTO {table} (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, str(value), now_iso()),
        )
        conn.commit()


def normalize_mode(mode: Optional[str] = None) -> str:
    candidate = (mode or get_setting("current_mode") or "PAPER").upper()
    return "LIVE" if candidate == "LIVE" else "PAPER"


def get_current_mode() -> str:
    return normalize_mode(get_setting("mode") or get_setting("current_mode"))


def set_current_mode(mode: str) -> str:
    normalized = normalize_mode(mode)
    set_setting("mode", normalized)
    set_setting("current_mode", normalized)
    return normalized


def log_event(message: str, level: str = "info", mode: Optional[str] = None) -> None:
    with DB_LOCK, get_connection() as conn:
        conn.execute(
            "INSERT INTO bot_events (mode, level, message, created_at) VALUES (?, ?, ?, ?)",
            (normalize_mode(mode), level, message, now_iso()),
        )
        conn.commit()
