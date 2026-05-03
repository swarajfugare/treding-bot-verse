import csv
import io
import json
from typing import Optional

from database import DB_LOCK, get_connection, normalize_mode


EXPORT_FIELDS = ["coin", "entry", "exit", "pnl", "confidence", "reason"]


def trades_for_export(mode: Optional[str] = None) -> list[dict]:
    normalized_mode = normalize_mode(mode)
    with DB_LOCK, get_connection() as conn:
        rows = conn.execute(
            """
            SELECT symbol AS coin, entry_price AS entry, exit_price AS exit,
                   pnl, confidence, reason
            FROM trades
            WHERE mode = ?
            ORDER BY opened_at DESC
            """,
            (normalized_mode,),
        ).fetchall()
    return [dict(row) for row in rows]


def export_trades_csv(mode: Optional[str] = None) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    for row in trades_for_export(mode):
        writer.writerow({field: row.get(field) for field in EXPORT_FIELDS})
    return output.getvalue()


def parse_trade_upload(filename: str, content: str) -> list[dict]:
    if filename.lower().endswith(".json"):
        payload = json.loads(content)
        return payload if isinstance(payload, list) else payload.get("trades", [])

    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader]


def analyze_uploaded_trades(filename: str, content: str) -> dict:
    trades = parse_trade_upload(filename, content)
    if not trades:
        return {"success": False, "error": "No trades found in uploaded data.", "suggestions": []}

    pnl_values = []
    wins = 0
    losses = 0
    confidence_values = []
    for trade in trades:
        try:
            pnl = float(trade.get("pnl") or 0)
            pnl_values.append(pnl)
            wins += 1 if pnl > 0 else 0
            losses += 1 if pnl < 0 else 0
        except (TypeError, ValueError):
            pass
        try:
            confidence_values.append(float(trade.get("confidence") or 0))
        except (TypeError, ValueError):
            pass

    total = len(pnl_values) or len(trades)
    win_rate = round((wins / total) * 100, 2) if total else 0
    avg_pnl = round(sum(pnl_values) / len(pnl_values), 4) if pnl_values else 0
    avg_confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0
    suggestions = []

    if win_rate < 50:
        suggestions.append("Raise the confidence threshold or tighten RSI bands before allowing entries.")
    if avg_pnl < 0:
        suggestions.append("Review stop loss placement and avoid entries when EMA distance is near the sideways filter.")
    if avg_confidence < 80:
        suggestions.append("Prioritize trades where EMA crossover, RSI quality, trend alignment, and volume all score together.")
    if losses > wins:
        suggestions.append("Increase cooldown after losing trades and block repeated same-direction entries.")
    if not suggestions:
        suggestions.append("Current sample is healthy. Keep collecting mode-separated trade data before loosening filters.")

    return {
        "success": True,
        "summary": {
            "trades": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "average_pnl": avg_pnl,
            "average_confidence": avg_confidence,
        },
        "suggestions": suggestions,
        "error": None,
    }
