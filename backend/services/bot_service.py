import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.database import (
    DB_LOCK,
    dict_row,
    get_connection,
    get_current_mode,
    get_setting,
    log_event,
    normalize_mode,
    now_iso,
    set_current_mode,
    set_setting,
)
from backend.services.balance_service import adjust_paper_usdt, get_balance
from backend.services.exchange_service import fetch_open_orders, place_market_order
from backend.services.market_service import latest_price
from backend.services.strategy_service import MIN_CONFIDENCE, evaluate_market, scan_market


class BotManager:
    def __init__(self) -> None:
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()
        self.last_decision: Optional[dict] = None

    async def start(self, paper_trading: Optional[bool] = None, mode: Optional[str] = None) -> dict:
        try:
            async with self.lock:
                active_mode = normalize_mode(mode or get_current_mode())
                set_current_mode(active_mode)
                if paper_trading is not None:
                    set_current_mode("PAPER" if paper_trading else "LIVE")
                    active_mode = get_current_mode()
                bot_state["mode"] = active_mode
                if self.running:
                    bot_state["running"] = True
                    bot_state["active_trade"] = get_open_trade(active_mode)
                    return {"success": True, "running": True, "mode": active_mode, "status": "already_running", "bot_state": bot_state, "error": None}

                open_trade = get_open_trade(active_mode)
                self.running = True
                bot_state["running"] = True
                bot_state["active_trade"] = open_trade
                bot_state["trades_today"] = len(todays_closed_trades(active_mode))
                self.task = asyncio.create_task(self._loop())
                if open_trade:
                    log_event(f"Bot started and resumed open {open_trade['symbol']} trade.", mode=active_mode)
                    status = "resumed_trade"
                    first_tick = None
                else:
                    log_event("Bot started.", mode=active_mode)
                    status = "started"
                    first_tick = await self.tick()
                    open_trade = get_open_trade(active_mode)
                bot_state["active_trade"] = open_trade
                return {
                    "success": True,
                    "running": True,
                    "mode": active_mode,
                    "status": status,
                    "active_trade": open_trade,
                    "first_tick": first_tick,
                    "bot_state": bot_state,
                    "error": None,
                }
        except Exception as exc:
            log_event(f"Bot start failed: {exc}", "error", mode=get_current_mode())
            return {"success": False, "running": self.running, "error": str(exc)}

    async def stop(self) -> dict:
        try:
            async with self.lock:
                self.running = False
                bot_state["running"] = False
                if self.task and not self.task.done():
                    self.task.cancel()
                    try:
                        await self.task
                    except asyncio.CancelledError:
                        pass
                self.task = None
                log_event("Bot stopped.", mode=get_current_mode())
                bot_state["active_trade"] = get_open_trade(get_current_mode())
                return {"success": True, "running": False, "mode": get_current_mode(), "status": "stopped", "bot_state": bot_state, "error": None}
        except Exception as exc:
            log_event(f"Bot stop failed: {exc}", "error", mode=get_current_mode())
            return {"success": False, "running": self.running, "error": str(exc)}

    async def _loop(self) -> None:
        while self.running:
            try:
                await self.tick()
            except Exception as exc:
                log_event(f"Bot loop handled an error: {exc}", "error", mode=get_current_mode())
            await asyncio.sleep(3)

    async def tick(self) -> dict:
        mode = get_current_mode()
        active_trade = get_open_trade(mode)
        bot_state["mode"] = mode
        bot_state["active_trade"] = active_trade
        print("Mode:", mode)
        print("Active trade:", active_trade)
        if active_trade:
            closed = maybe_close_trade(active_trade)
            bot_state["active_trade"] = get_open_trade(mode)
            return {"active_trade": bot_state["active_trade"], "closed_trade": closed}

        exchange_positions = check_exchange_open_positions(mode)
        if exchange_positions:
            log_event("Trade skipped because an open exchange position already exists.", mode=mode)
            bot_state["active_trade"] = exchange_positions[0]
            return {"decision": None, "opened_trade": None, "active_trade": exchange_positions[0]}

        decision = evaluate_market(mode)
        self.last_decision = decision
        print("Decision:", decision)
        if decision["signal"] in ("BUY", "SELL") and decision["confidence"] >= MIN_CONFIDENCE:
            opened = open_trade_from_decision(decision, mode)
            bot_state["active_trade"] = get_open_trade(mode)
            if opened:
                bot_state["last_trade_time"] = opened.get("opened_at")
                bot_state["trades_today"] = len(todays_closed_trades(mode)) + 1
            return {"decision": decision, "opened_trade": opened}
        return {"decision": decision, "opened_trade": None}

    def status(self, mode: Optional[str] = None) -> dict:
        mode = normalize_mode(mode)
        state = {**bot_state, "mode": mode, "active_trade": get_open_trade(mode), "trades_today": len(todays_closed_trades(mode))}
        return {
            "success": True,
            "running": self.running,
            "mode": mode,
            "paper_trading": is_paper_trading(mode),
            "active_trade": get_open_trade(mode),
            "bot_state": state,
            "error": None,
        }


bot_manager = BotManager()

bot_state = {
    "running": False,
    "mode": "PAPER",
    "active_trade": None,
    "last_trade_time": None,
    "trades_today": 0,
}


def sync_bot_state_from_storage() -> None:
    mode = get_current_mode()
    bot_state["mode"] = mode
    bot_state["active_trade"] = get_open_trade(mode)
    bot_state["trades_today"] = len(todays_closed_trades(mode))


def is_paper_trading(mode: Optional[str] = None) -> bool:
    return normalize_mode(mode) == "PAPER"


def get_paper_balance() -> float:
    try:
        return float(get_setting("paper_balance") or "10000")
    except ValueError:
        set_setting("paper_balance", "10000")
        return 10000.0


def set_paper_trading(enabled: bool) -> dict:
    mode = set_current_mode("PAPER" if enabled else "LIVE")
    set_setting("paper_trading", str(enabled).lower())
    bot_state["mode"] = mode
    bot_state["active_trade"] = get_open_trade(mode)
    return {"success": True, "mode": mode, "paper_trading": enabled, "error": None}


def set_trading_mode(mode: str) -> dict:
    normalized = set_current_mode(mode)
    set_setting("paper_trading", str(normalized == "PAPER").lower())
    bot_state["mode"] = normalized
    bot_state["active_trade"] = get_open_trade(normalized)
    bot_state["trades_today"] = len(todays_closed_trades(normalized))
    log_event(f"Mode switched to {normalized}.", mode=normalized)
    return {"success": True, "mode": normalized, "paper_trading": normalized == "PAPER", "error": None}


def get_open_trade(mode: Optional[str] = None) -> Optional[dict]:
    normalized_mode = normalize_mode(mode)
    with DB_LOCK, get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trades WHERE mode = ? AND status = 'open' ORDER BY opened_at DESC LIMIT 1",
            (normalized_mode,),
        ).fetchone()
    return dict_row(row)


def todays_closed_trades(mode: Optional[str] = None) -> list[dict]:
    normalized_mode = normalize_mode(mode)
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with DB_LOCK, get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE mode = ? AND opened_at >= ? AND status = 'closed' ORDER BY opened_at DESC",
            (normalized_mode, start),
        ).fetchall()
    return [dict(row) for row in rows]


def check_exchange_open_positions(mode: Optional[str] = None) -> list[dict]:
    normalized_mode = normalize_mode(mode)
    if normalized_mode == "LIVE":
        orders = fetch_open_orders()
        if orders.get("success") and orders.get("orders"):
            return [{"mode": "LIVE", "symbol": item.get("symbol"), "status": item.get("status"), "exchange_order": item} for item in orders["orders"]]
        return []
    open_trade = get_open_trade(mode)
    return [open_trade] if open_trade else []


def last_trade(mode: Optional[str] = None) -> Optional[dict]:
    normalized_mode = normalize_mode(mode)
    with DB_LOCK, get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trades WHERE mode = ? ORDER BY opened_at DESC LIMIT 1",
            (normalized_mode,),
        ).fetchone()
    return dict_row(row)


def risk_check(decision: Optional[dict] = None, mode: Optional[str] = None) -> Optional[str]:
    normalized_mode = normalize_mode(mode)
    if bot_state.get("mode") == normalized_mode and bot_state.get("active_trade"):
        return "Bot state already has an active trade."

    if get_open_trade(normalized_mode):
        return "An open trade already exists."

    if check_exchange_open_positions(normalized_mode):
        return "An exchange open position already exists."

    trades = todays_closed_trades(normalized_mode)
    if len(trades) >= 5:
        return "Daily trade limit reached."

    if trades:
        last_closed = max(trade["closed_at"] for trade in trades if trade.get("closed_at"))
        if last_closed:
            last_time = datetime.fromisoformat(last_closed)
            if datetime.now(timezone.utc) - last_time < timedelta(minutes=10):
                return "Cooldown is active after the last trade."

    daily_pnl = sum(float(trade["pnl"] or 0) for trade in trades)
    if daily_pnl <= -(get_balance(normalized_mode)["usdt_equivalent"] * 0.02):
        return "Daily loss stop reached."

    previous = last_trade(normalized_mode)
    if decision and previous and previous.get("side") == decision.get("signal"):
        return "Repeated same-direction trade avoided."

    return None


def open_trade_from_decision(decision: dict, mode: Optional[str] = None) -> Optional[dict]:
    normalized_mode = normalize_mode(mode)
    risk_error = risk_check(decision, normalized_mode)
    if risk_error:
        log_event(f"Trade skipped for {decision['coin']}: {risk_error}", mode=normalized_mode)
        print("Trade skipped:", risk_error)
        return None

    balance_detail = get_balance(normalized_mode)
    if balance_detail.get("error"):
        log_event(f"Trade skipped because balance failed: {balance_detail['error']}", "error", mode=normalized_mode)
        print("Trade skipped:", balance_detail["error"])
        return None
    balance = balance_detail["usdt_equivalent"]
    if balance <= 0:
        log_event("Trade skipped because USDT-equivalent balance is zero.", mode=normalized_mode)
        print("Trade skipped: zero balance")
        return None

    allocated = round(balance * 0.10, 2)
    price = latest_price(decision["coin"])
    quantity = allocated / price
    side = decision["signal"]
    stop_loss = price * (0.995 if side == "BUY" else 1.005)
    take_profit = price * (1.01 if side == "BUY" else 0.99)
    timestamp = now_iso()

    if normalized_mode == "LIVE":
        live_order = place_market_order(decision["coin"], side, allocated)
        if not live_order.get("success"):
            log_event(f"LIVE order failed for {decision['coin']}: {live_order.get('error')}", "error", mode=normalized_mode)
            print("LIVE order failed:", live_order.get("error"))
            return None
        log_event(f"LIVE exchange order accepted: {live_order.get('order')}", mode=normalized_mode)

    with DB_LOCK, get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trades (
                mode, symbol, side, entry_price, quantity, allocated_balance, stop_loss,
                take_profit, status, opened_at, reason, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
            """,
            (
                normalized_mode,
                decision["coin"],
                side,
                price,
                quantity,
                allocated,
                stop_loss,
                take_profit,
                timestamp,
                decision["reason"],
                decision["confidence"],
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM trades WHERE id = ?", (cursor.lastrowid,)).fetchone()
    log_event(f"Opened {side} {normalized_mode.lower()} trade on {decision['coin']} with {decision['confidence']} confidence.", mode=normalized_mode)
    return dict_row(row)


def maybe_close_trade(trade: dict) -> Optional[dict]:
    price = latest_price(trade["symbol"])
    side = trade["side"]
    should_close = False
    reason = ""
    if side == "BUY" and price <= float(trade["stop_loss"]):
        should_close = True
        reason = "Stop loss reached."
    elif side == "BUY" and price >= float(trade["take_profit"]):
        should_close = True
        reason = "Take profit reached."
    elif side == "SELL" and price >= float(trade["stop_loss"]):
        should_close = True
        reason = "Stop loss reached."
    elif side == "SELL" and price <= float(trade["take_profit"]):
        should_close = True
        reason = "Take profit reached."

    if not should_close:
        return None

    quantity = float(trade["quantity"])
    entry = float(trade["entry_price"])
    pnl = (price - entry) * quantity if side == "BUY" else (entry - price) * quantity
    mode = normalize_mode(trade.get("mode"))
    current_balance = get_balance(mode)["native_usdt_balance"]
    if current_balance:
        setting_key = "paper_balance" if mode == "PAPER" else "live_usdt_balance"
        set_setting(setting_key, round(current_balance + pnl, 2))
    if mode == "PAPER":
        adjust_paper_usdt(pnl)
    with DB_LOCK, get_connection() as conn:
        conn.execute(
            """
            UPDATE trades
            SET status = 'closed', exit_price = ?, pnl = ?, closed_at = ?, reason = reason || '; ' || ?
            WHERE id = ?
            """,
            (price, pnl, now_iso(), reason, trade["id"]),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM trades WHERE id = ?", (trade["id"],)).fetchone()
    log_event(f"Closed {trade['symbol']} trade. {reason} PnL: {pnl:.2f}", mode=mode)
    return dict_row(row)


def dashboard(mode: Optional[str] = None) -> dict:
    normalized_mode = normalize_mode(mode)
    scan = scan_market()
    with DB_LOCK, get_connection() as conn:
        trades = conn.execute(
            "SELECT * FROM trades WHERE mode = ? ORDER BY opened_at DESC LIMIT 25",
            (normalized_mode,),
        ).fetchall()
        total_pnl = conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) AS total FROM trades WHERE mode = ? AND status = 'closed'",
            (normalized_mode,),
        ).fetchone()
        events = conn.execute(
            "SELECT * FROM bot_events WHERE mode = ? ORDER BY created_at DESC LIMIT 20",
            (normalized_mode,),
        ).fetchall()
    balance = get_balance(normalized_mode)
    return {
        "success": True,
        "mode": normalized_mode,
        "balance": balance["usdt_equivalent"],
        "balance_detail": balance,
        "pnl": round(float(total_pnl["total"]), 2),
        "bot_status": bot_manager.status(normalized_mode),
        "active_trade": get_open_trade(normalized_mode),
        "best_coin": scan["best"],
        "scanner": scan["coins"],
        "trades": [dict(row) for row in trades],
        "events": [dict(row) for row in events],
        "error": None,
    }
