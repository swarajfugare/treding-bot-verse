from typing import Optional

from fastapi import APIRouter, Body

from models import BotControlRequest
from services.bot_service import bot_manager
from services.strategy_service import evaluate_market

router = APIRouter(prefix="/api/bot", tags=["bot"])


@router.post("")
async def control_bot(payload: Optional[BotControlRequest] = Body(None)) -> dict:
    try:
        payload = payload or BotControlRequest()
        action = (payload.action or "").lower()
        if payload.running is True or action == "start":
            return await bot_manager.start(payload.paper_trading, payload.mode)
        if payload.running is False or action == "stop":
            return await bot_manager.stop()
        return {"success": False, "running": bot_manager.running, "error": "Use action=start, action=stop, running=true, or running=false."}
    except Exception as exc:
        return {"success": False, "running": bot_manager.running, "error": str(exc)}


@router.get("/status")
async def bot_status() -> dict:
    try:
        return bot_manager.status()
    except Exception as exc:
        return {"success": False, "running": False, "error": str(exc)}


@router.get("/decision")
async def bot_decision(mode: Optional[str] = None) -> dict:
    try:
        decision = evaluate_market(mode)
        return {"success": True, **decision, "error": None}
    except Exception as exc:
        return {
            "success": False,
            "coin": None,
            "signal": "HOLD",
            "ema9": 0,
            "ema21": 0,
            "rsi": 0,
            "confidence": 0,
            "reason": "Decision engine failed safely.",
            "error": str(exc),
        }
