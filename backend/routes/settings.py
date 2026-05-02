from typing import Any, Optional

from fastapi import APIRouter, Body

from backend.models import BalanceRequest, ModeRequest, PaperModeRequest
from backend.services.balance_service import get_balance, set_balance
from backend.services.bot_service import set_paper_trading, set_trading_mode
from backend.services.credentials_service import get_credentials, normalize_credentials, save_credentials, test_credentials

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/credentials")
async def read_credentials() -> dict:
    try:
        return get_credentials(masked=True)
    except Exception as exc:
        return {"success": False, "connected": False, "error": str(exc)}


@router.post("/credentials")
async def write_credentials(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    try:
        api_key, api_secret, error = normalize_credentials(payload or {})
        if error:
            return {"success": False, "connected": False, "error": error}
        return save_credentials(api_key, api_secret)
    except Exception as exc:
        return {"success": False, "connected": False, "error": str(exc)}


@router.post("/credentials/test")
async def check_credentials(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    try:
        return test_credentials(payload or {})
    except Exception as exc:
        return {"success": False, "connected": False, "error": str(exc)}


@router.post("/paper")
async def update_paper_mode(payload: PaperModeRequest) -> dict:
    try:
        return set_paper_trading(payload.enabled)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/mode")
async def update_mode(payload: ModeRequest) -> dict:
    try:
        return set_trading_mode(payload.mode)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/mode")
async def read_mode() -> dict:
    try:
        from backend.database import get_current_mode

        return {"success": True, "mode": get_current_mode(), "error": None}
    except Exception as exc:
        return {"success": False, "mode": "PAPER", "error": str(exc)}


@router.get("/balance")
async def read_balance(mode: Optional[str] = None) -> dict:
    try:
        balance = get_balance(mode)
        if balance.get("error"):
            return {"success": False, "balance": balance, "error": balance["error"]}
        return {"success": True, "balance": balance, "error": None}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/balance")
async def write_balance(payload: BalanceRequest) -> dict:
    try:
        return set_balance(payload.mode, payload.usdt_balance, payload.inr_balance)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
