from database import get_setting, now_iso, set_setting


def get_loss_control() -> dict:
    try:
        limit_pct = float(get_setting("daily_loss_limit_pct") or 2)
    except ValueError:
        limit_pct = 2.0
    return {
        "success": True,
        "enabled": (get_setting("daily_loss_enabled") or "true").lower() == "true",
        "limit_pct": limit_pct,
        "reset_at": get_setting("daily_loss_reset_at") or None,
        "error": None,
    }


def set_loss_control(enabled: bool, limit_pct: float) -> dict:
    set_setting("daily_loss_enabled", str(bool(enabled)).lower())
    set_setting("daily_loss_limit_pct", max(0.1, float(limit_pct)))
    return get_loss_control()


def reset_daily_loss() -> dict:
    set_setting("daily_loss_reset_at", now_iso())
    return {"success": True, "message": "Daily loss counter reset.", "reset_at": get_setting("daily_loss_reset_at"), "error": None}
