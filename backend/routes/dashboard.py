from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import Response

from backend.database import DB_LOCK, get_connection
from backend.services.bot_service import dashboard
from backend.services.market_service import chart_candles
from backend.services.report_service import analyze_uploaded_trades, export_trades_csv
from backend.services.strategy_service import scan_market

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def read_dashboard(mode: Optional[str] = None) -> dict:
    try:
        return dashboard(mode)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/trades")
async def read_trades(mode: Optional[str] = None) -> dict:
    try:
        from backend.database import normalize_mode

        normalized_mode = normalize_mode(mode)
        with DB_LOCK, get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE mode = ? ORDER BY opened_at DESC LIMIT 100",
                (normalized_mode,),
            ).fetchall()
        return {"success": True, "trades": [dict(row) for row in rows], "error": None}
    except Exception as exc:
        return {"success": False, "trades": [], "error": str(exc)}


@router.get("/market/scanner")
async def read_scanner() -> dict:
    try:
        scan = scan_market()
        return {"success": True, **scan, "error": None}
    except Exception as exc:
        return {"success": False, "coins": [], "best": None, "error": str(exc)}


@router.get("/market/chart/{symbol}")
async def read_chart(symbol: str) -> dict:
    try:
        return {"success": True, "symbol": symbol.upper(), "candles": chart_candles(symbol.upper()), "error": None}
    except Exception as exc:
        return {"success": False, "symbol": symbol.upper(), "candles": [], "error": str(exc)}


@router.get("/trades/export")
async def export_trades(mode: Optional[str] = None, format: str = "csv"):
    try:
        from backend.database import normalize_mode

        normalized_mode = normalize_mode(mode)
        csv_text = export_trades_csv(mode)
        if format.lower() == "json":
            with DB_LOCK, get_connection() as conn:
                rows = conn.execute(
                    "SELECT symbol AS coin, entry_price AS entry, exit_price AS exit, pnl, confidence, reason FROM trades WHERE mode = ? ORDER BY opened_at DESC",
                    (normalized_mode,),
                ).fetchall()
            return {"success": True, "mode": normalized_mode, "trades": [dict(row) for row in rows], "error": None}
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=pulsex-{normalized_mode.lower()}-trades.csv"},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/strategy/analyze")
async def analyze_strategy_upload(payload: dict = Body(default_factory=dict)) -> dict:
    try:
        filename = str(payload.get("filename") or "trades.csv")
        content = str(payload.get("content") or "")
        return analyze_uploaded_trades(filename, content)
    except Exception as exc:
        return {"success": False, "error": str(exc), "suggestions": []}
