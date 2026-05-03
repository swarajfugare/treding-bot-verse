from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import Response

from database import DB_LOCK, get_connection
from services.bot_service import dashboard
from services.market_service import chart_candles
from services.report_service import analyze_uploaded_trades, export_trades_csv
from services.strategy_service import scan_market
from utils.async_tools import run_blocking

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def read_dashboard(mode: Optional[str] = None) -> dict:
    try:
        return await run_blocking(dashboard, mode, timeout=2)
    except TimeoutError:
        return {"success": False, "error": "Dashboard request timed out safely. Try again in a moment."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/trades")
async def read_trades(mode: Optional[str] = None) -> dict:
    try:
        from database import normalize_mode

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
        scan = await run_blocking(scan_market, timeout=2)
        return {"success": True, **scan, "error": None}
    except TimeoutError:
        return {"success": False, "coins": [], "best": None, "error": "Scanner request timed out safely."}
    except Exception as exc:
        return {"success": False, "coins": [], "best": None, "error": str(exc)}


@router.get("/market/chart/{symbol}")
async def read_chart(symbol: str) -> dict:
    try:
        candles = await run_blocking(chart_candles, symbol.upper(), timeout=2)
        return {"success": True, "symbol": symbol.upper(), "candles": candles, "error": None}
    except TimeoutError:
        return {"success": False, "symbol": symbol.upper(), "candles": [], "error": "Chart request timed out safely."}
    except Exception as exc:
        return {"success": False, "symbol": symbol.upper(), "candles": [], "error": str(exc)}


@router.get("/trades/export")
async def export_trades(mode: Optional[str] = None, format: str = "csv"):
    try:
        from database import normalize_mode

        normalized_mode = normalize_mode(mode)
        csv_text = await run_blocking(export_trades_csv, mode, timeout=2)
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
async def analyze_strategy_upload(payload: Optional[dict] = Body(None)) -> dict:
    try:
        payload = payload or {}
        filename = str(payload.get("filename") or "trades.csv")
        content = str(payload.get("content") or "")
        return await run_blocking(analyze_uploaded_trades, filename, content, timeout=2)
    except Exception as exc:
        return {"success": False, "error": str(exc), "suggestions": []}
