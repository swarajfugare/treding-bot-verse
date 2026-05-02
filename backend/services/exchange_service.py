import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.services.credentials_service import get_credentials
from backend.services.market_service import usd_inr_rate

BINANCE_API_URL = "https://api.binance.com"


def _signed_request(method: str, path: str, params: Optional[dict] = None) -> dict:
    credentials = get_credentials(masked=False)
    if not credentials.get("connected"):
        return {"success": False, "error": "API not connected"}

    api_key = credentials.get("api_key")
    api_secret = credentials.get("api_secret")
    if not api_key or not api_secret:
        return {"success": False, "error": "API not connected"}

    query = {"timestamp": int(time.time() * 1000), "recvWindow": 5000}
    if params:
        query.update(params)
    query_string = urlencode(query)
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    url = f"{BINANCE_API_URL}{path}?{query_string}&signature={signature}"
    data = None if method.upper() == "GET" else b""
    request = Request(url, data=data, headers={"X-MBX-APIKEY": api_key}, method=method.upper())

    try:
        with urlopen(request, timeout=5) as response:
            return {"success": True, "data": json.loads(response.read().decode()), "error": None}
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode())
            message = payload.get("msg") or str(exc)
        except Exception:
            message = str(exc)
        return {"success": False, "error": f"Exchange API error: {message}"}
    except (OSError, URLError, ValueError) as exc:
        return {"success": False, "error": f"Exchange API unavailable: {exc}"}


def _signed_get(path: str, params: Optional[dict] = None) -> dict:
    return _signed_request("GET", path, params)


def fetch_live_account() -> dict:
    account = _signed_get("/api/v3/account")
    if not account.get("success"):
        return {"success": False, "error": account.get("error") or "API not connected"}

    balances = account["data"].get("balances", [])
    positions = []
    usdt_balance = 0.0
    inr_balance = 0.0
    for item in balances:
        asset = item.get("asset")
        free = float(item.get("free") or 0)
        locked = float(item.get("locked") or 0)
        total = free + locked
        if total <= 0:
            continue
        positions.append({"asset": asset, "free": free, "locked": locked, "total": total})
        if asset == "USDT":
            usdt_balance = total
        if asset == "INR":
            inr_balance = total

    rate = usd_inr_rate()
    total_equity = round(usdt_balance + (inr_balance / rate if inr_balance else 0), 2)
    return {
        "success": True,
        "inr_balance": round(inr_balance, 2),
        "usdt_balance": round(usdt_balance, 2),
        "total_equity": total_equity,
        "positions": positions,
        "error": None,
    }


def fetch_open_orders(symbol: Optional[str] = None) -> dict:
    params = {"symbol": symbol} if symbol else None
    result = _signed_get("/api/v3/openOrders", params)
    if not result.get("success"):
        return {"success": False, "orders": [], "error": result.get("error") or "API not connected"}
    return {"success": True, "orders": result.get("data") or [], "error": None}


def place_market_order(symbol: str, side: str, quote_order_qty: float) -> dict:
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quoteOrderQty": round(float(quote_order_qty), 2),
    }
    result = _signed_request("POST", "/api/v3/order", params)
    if not result.get("success"):
        return {"success": False, "error": result.get("error") or "Order failed"}
    return {"success": True, "order": result.get("data"), "error": None}
