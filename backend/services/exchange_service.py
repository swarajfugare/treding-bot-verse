import hashlib
import hmac
import json
import os
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.credentials_service import get_credentials
from services.market_service import usd_inr_rate

DELTA_API_URL = os.getenv("DELTA_API_URL", "https://api.india.delta.exchange").rstrip("/")
DELTA_SYMBOLS = {"BTCUSDT": "BTCUSD", "ETHUSDT": "ETHUSD", "SOLUSDT": "SOLUSD"}
PRODUCT_CACHE: dict[str, dict] = {}


def _json_body(body: Optional[dict]) -> str:
    return json.dumps(body or {}, separators=(",", ":")) if body is not None else ""


def _auth_headers(method: str, path: str, query_string: str = "", body: Optional[dict] = None) -> dict:
    credentials = get_credentials(masked=False)
    if not credentials.get("connected"):
        raise ValueError("API not connected")

    api_key = str(credentials.get("api_key") or "").strip()
    api_secret = str(credentials.get("api_secret") or "").strip()
    if not api_key or not api_secret:
        raise ValueError("API not connected")

    timestamp = str(int(time.time()))
    body_text = _json_body(body)
    signature_payload = method.upper() + timestamp + path + query_string + body_text
    signature = hmac.new(api_secret.encode(), signature_payload.encode(), hashlib.sha256).hexdigest()
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "python-rest-client",
        "api-key": api_key,
        "timestamp": timestamp,
        "signature": signature,
    }


def _request(method: str, path: str, params: Optional[dict] = None, body: Optional[dict] = None, auth: bool = False) -> dict:
    query_string = f"?{urlencode(params)}" if params else ""
    url = f"{DELTA_API_URL}/v2{path}{query_string}"
    data = _json_body(body).encode() if body is not None else None
    try:
        headers = _auth_headers(method, f"/v2{path}", query_string, body) if auth else {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-rest-client",
        }
        request = Request(url, data=data, headers=headers, method=method.upper())
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode())
            if payload.get("success") is False:
                return {"success": False, "error": payload.get("error") or payload.get("message") or "Delta API request failed", "data": payload}
            return {"success": True, "data": payload, "error": None}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode())
            message = payload.get("message") or payload.get("error") or str(exc)
        except Exception:
            message = str(exc)
        return {"success": False, "error": f"Exchange API error: {message}"}
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"success": False, "error": f"Exchange API unavailable: {exc}"}


def delta_symbol(symbol: str) -> str:
    return DELTA_SYMBOLS.get(symbol.upper(), symbol.upper())


def get_product(symbol: str) -> dict:
    mapped = delta_symbol(symbol)
    if mapped in PRODUCT_CACHE:
        return {"success": True, "product": PRODUCT_CACHE[mapped], "error": None}
    result = _request("GET", "/products", params={"symbol": mapped})
    if not result.get("success"):
        return {"success": False, "error": result.get("error") or "Could not load product"}
    products = result["data"].get("result") or []
    product = next((item for item in products if item.get("symbol") == mapped), None)
    if not product:
        result = _request("GET", f"/products/{mapped}")
        if result.get("success"):
            product = result["data"].get("result")
    if not product:
        return {"success": False, "error": f"Delta product not found for {mapped}"}
    PRODUCT_CACHE[mapped] = product
    return {"success": True, "product": product, "error": None}


def test_connection() -> dict:
    result = _request("GET", "/wallet/balances", auth=True)
    if not result.get("success"):
        return {"success": False, "connected": False, "message": result.get("error") or "Connection failed", "error": result.get("error")}
    return {"success": True, "connected": True, "message": "Connected", "error": None}


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def fetch_live_account() -> dict:
    result = _request("GET", "/wallet/balances", auth=True)
    if not result.get("success"):
        return {"success": False, "error": result.get("error") or "API not connected"}

    wallets = result["data"].get("result") or result["data"].get("balance") or []
    positions = []
    usd_balance = 0.0
    available_usd_balance = 0.0
    inr_balance = 0.0
    explicit_inr_balance = 0.0
    meta = result["data"].get("meta") or {}
    for item in wallets:
        asset = str(item.get("asset_symbol") or item.get("asset") or item.get("symbol") or "").upper()
        balance = _to_float(item.get("balance") or item.get("available_balance"))
        available = _to_float(item.get("available_balance") or balance)
        if balance or available:
            positions.append({"asset": asset, "balance": balance, "available_balance": available})
        if asset in {"USD", "USDT"}:
            usd_balance += balance
            available_usd_balance += available
        if asset == "INR":
            explicit_inr_balance += balance

    rate = usd_inr_rate()
    meta_equity = _to_float(meta.get("net_equity") or meta.get("robo_trading_equity"))
    if usd_balance <= 0 and meta_equity > 0:
        usd_balance = meta_equity
        available_usd_balance = meta_equity
    if explicit_inr_balance > 0:
        inr_balance = explicit_inr_balance
        usd_balance = usd_balance or round(explicit_inr_balance / rate, 8)
    else:
        inr_balance = round(usd_balance * rate, 2)
    total_equity = round(usd_balance, 2)
    return {
        "success": True,
        "inr_balance": round(inr_balance, 2),
        "usdt_balance": round(usd_balance, 2),
        "usd_balance": round(usd_balance, 2),
        "available_usdt_balance": round(available_usd_balance, 2),
        "total_equity": total_equity,
        "positions": positions,
        "meta": meta,
        "error": None,
    }


def fetch_open_orders(symbol: Optional[str] = None) -> dict:
    params = {"product_symbol": delta_symbol(symbol)} if symbol else None
    result = _request("GET", "/orders", params=params, auth=True)
    if not result.get("success"):
        return {"success": False, "orders": [], "error": result.get("error") or "API not connected"}
    return {"success": True, "orders": result["data"].get("result") or [], "error": None}


def fetch_open_positions() -> dict:
    result = _request("GET", "/positions/margined", auth=True)
    if not result.get("success"):
        return {"success": False, "positions": [], "error": result.get("error") or "API not connected"}
    positions = [item for item in result["data"].get("result") or [] if float(item.get("size") or 0) != 0]
    return {"success": True, "positions": positions, "error": None}


def place_market_order(symbol: str, side: str, notional_usdt: float, price: float) -> dict:
    product_result = get_product(symbol)
    if not product_result.get("success"):
        return {"success": False, "error": product_result.get("error")}
    product = product_result["product"]
    product_id = product.get("id")
    contract_value = float(product.get("contract_value") or product.get("quoting_asset_precision") or 1)
    size = max(1, int(float(notional_usdt) / max(float(price), 1) / max(contract_value, 1e-9)))
    body = {
        "product_id": product_id,
        "size": size,
        "side": side.lower(),
        "order_type": "market_order",
        "time_in_force": "ioc",
        "reduce_only": False,
    }
    result = _request("POST", "/orders", body=body, auth=True)
    if not result.get("success"):
        return {"success": False, "error": result.get("error") or "Order failed"}
    return {"success": True, "order": result["data"].get("result"), "error": None}
