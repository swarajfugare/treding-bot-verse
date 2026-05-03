from typing import Optional

from database import DB_LOCK, get_connection, normalize_mode, now_iso
from services.exchange_service import fetch_live_account
from services.market_service import usd_inr_rate


def _stored_balance(mode: str) -> dict:
    with DB_LOCK, get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM balances WHERE mode = ?",
            (mode,),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO balances (mode, inr_balance, usdt_balance, updated_at) VALUES (?, 0, ?, ?)",
                (mode, 10000.0 if mode == "PAPER" else 0.0, now_iso()),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM balances WHERE mode = ?", (mode,)).fetchone()
    return dict(row)


def _update_stored_balance(mode: str, usdt_balance: float, inr_balance: float) -> None:
    with DB_LOCK, get_connection() as conn:
        conn.execute(
            """
            INSERT INTO balances (mode, inr_balance, usdt_balance, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mode) DO UPDATE SET
                inr_balance = excluded.inr_balance,
                usdt_balance = excluded.usdt_balance,
                updated_at = excluded.updated_at
            """,
            (mode, round(inr_balance, 2), round(usdt_balance, 2), now_iso()),
        )
        conn.commit()


def get_balance(mode: Optional[str] = None) -> dict:
    normalized_mode = normalize_mode(mode)
    rate = usd_inr_rate()
    if normalized_mode == "PAPER":
        stored = _stored_balance("PAPER")
        usdt_balance = float(stored["usdt_balance"])
        inr_balance = float(stored["inr_balance"])
        starting_balance = 10000.0
        source = "paper_wallet"
        positions = []
        error = None
    else:
        live = fetch_live_account()
        if not live.get("success"):
            return {
                "mode": "LIVE",
                "inr_balance": 0.0,
                "native_usdt_balance": 0.0,
                "usdt_balance": 0.0,
                "usdt_equivalent": 0.0,
                "total_equity": 0.0,
                "positions": [],
                "usd_inr_rate": round(rate, 4),
                "source": "exchange",
                "error": live.get("error") or "API not connected",
            }
        usdt_balance = float(live["usdt_balance"])
        inr_balance = float(live["inr_balance"])
        starting_balance = usdt_balance
        source = "exchange"
        positions = live["positions"]
        error = None
        _update_stored_balance("LIVE", usdt_balance, inr_balance)

    converted_usdt = round(inr_balance / rate, 2) if inr_balance else 0.0
    total_equity = round(usdt_balance if normalized_mode == "LIVE" else usdt_balance + converted_usdt, 2)
    return {
        "mode": normalized_mode,
        "inr_balance": round(inr_balance, 2),
        "native_usdt_balance": round(usdt_balance, 2),
        "usdt_balance": round(usdt_balance, 2),
        "usdt_equivalent": total_equity,
        "total_equity": total_equity,
        "starting_balance": round(starting_balance, 2),
        "positions": positions,
        "usd_inr_rate": round(rate, 4),
        "source": source,
        "error": error,
    }


def set_balance(mode: str, usdt_balance: Optional[float] = None, inr_balance: Optional[float] = None) -> dict:
    normalized_mode = normalize_mode(mode)
    if normalized_mode == "LIVE":
        return {"success": False, "error": "LIVE balance is read from the connected exchange account."}
    stored = _stored_balance("PAPER")
    next_usdt = float(stored["usdt_balance"]) if usdt_balance is None else float(usdt_balance)
    next_inr = float(stored["inr_balance"]) if inr_balance is None else float(inr_balance)
    _update_stored_balance("PAPER", next_usdt, next_inr)
    return {"success": True, "balance": get_balance(normalized_mode), "error": None}


def adjust_paper_usdt(delta: float) -> None:
    stored = _stored_balance("PAPER")
    _update_stored_balance("PAPER", float(stored["usdt_balance"]) + delta, float(stored["inr_balance"]))
