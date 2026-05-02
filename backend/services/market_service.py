import hashlib
import json
import math
import random
from datetime import datetime, timezone
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BASE_PRICES = {"BTCUSDT": 64000.0, "ETHUSDT": 3100.0, "SOLUSDT": 145.0}
DISPLAY_SYMBOLS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}
FALLBACK_USD_INR = 83.0


def _seed(symbol: str, interval: str) -> int:
    minute = int(datetime.now(timezone.utc).timestamp() // 60)
    bucket = minute if interval == "1m" else minute // 5
    digest = hashlib.sha256(f"{symbol}:{interval}:{bucket}".encode()).hexdigest()
    return int(digest[:12], 16)


def candles(symbol: str, interval: str = "1m", limit: int = 120) -> pd.DataFrame:
    rng = random.Random(_seed(symbol, interval))
    base = BASE_PRICES.get(symbol, 100.0)
    trend = rng.uniform(-0.0018, 0.0018)
    volatility = 0.0014 if symbol == "BTCUSDT" else 0.0024
    rows = []
    price = base * (1 + rng.uniform(-0.015, 0.015))

    for index in range(limit):
        wave = math.sin(index / 8) * volatility
        change = trend + wave + rng.uniform(-volatility, volatility)
        open_price = price
        close_price = max(0.01, open_price * (1 + change))
        high_price = max(open_price, close_price) * (1 + abs(rng.uniform(0, volatility)))
        low_price = min(open_price, close_price) * (1 - abs(rng.uniform(0, volatility)))
        volume = rng.uniform(700, 1800) * (1 + abs(change) * 120)
        rows.append(
            {
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
        )
        price = close_price

    return pd.DataFrame(rows)


def latest_price(symbol: str) -> float:
    return live_price(symbol) or float(candles(symbol, "1m", 120).iloc[-1]["close"])


def live_price(symbol: str) -> Optional[float]:
    try:
        with urlopen(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=2) as response:
            payload = json.loads(response.read().decode())
            return float(payload["price"])
    except (OSError, URLError, ValueError, KeyError):
        return None


def usd_inr_rate() -> float:
    try:
        with urlopen("https://api.exchangerate.host/latest?base=USD&symbols=INR", timeout=2) as response:
            payload = json.loads(response.read().decode())
            return float(payload["rates"]["INR"])
    except (OSError, URLError, ValueError, KeyError):
        return FALLBACK_USD_INR


def inr_to_usdt(inr_balance: float) -> float:
    return round(inr_balance / usd_inr_rate(), 2)


def chart_candles(symbol: str, limit: int = 120) -> list[dict]:
    frame = candles(symbol, "1m", limit).copy()
    start = int(datetime.now(timezone.utc).timestamp()) - (len(frame) * 60)
    rows = []
    for index, row in frame.iterrows():
        rows.append(
            {
                "time": start + int(index) * 60,
                "open": round(float(row["open"]), 4),
                "high": round(float(row["high"]), 4),
                "low": round(float(row["low"]), 4),
                "close": round(float(row["close"]), 4),
                "volume": round(float(row["volume"]), 2),
            }
        )
    return rows
