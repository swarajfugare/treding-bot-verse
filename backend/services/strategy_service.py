from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from typing import Optional

from backend.database import DB_LOCK, get_connection, normalize_mode, now_iso
from backend.services.market_service import SYMBOLS, candles

MIN_CONFIDENCE = 75
MIN_VOLUME = 900
MIN_EMA_DISTANCE_PCT = 0.08


def _analyze_symbol(symbol: str) -> dict:
    frame_1m = candles(symbol, "1m")
    frame_5m = candles(symbol, "5m")

    for frame in (frame_1m, frame_5m):
        frame["ema9"] = EMAIndicator(close=frame["close"], window=9).ema_indicator()
        frame["ema21"] = EMAIndicator(close=frame["close"], window=21).ema_indicator()
        frame["rsi"] = RSIIndicator(close=frame["close"], window=14).rsi()

    last = frame_1m.iloc[-1]
    last_5m = frame_5m.iloc[-1]

    price = float(last["close"])
    ema9 = float(last["ema9"])
    ema21 = float(last["ema21"])
    rsi = float(last["rsi"])
    ema_distance_pct = abs(ema9 - ema21) / price * 100
    avg_volume = float(frame_1m["volume"].tail(20).mean())
    current_volume = float(last["volume"])
    trend_1m = "UP" if ema9 > ema21 else "DOWN"
    trend_5m = "UP" if float(last_5m["ema9"]) > float(last_5m["ema21"]) else "DOWN"
    trend = trend_1m if trend_1m == trend_5m else "MIXED"
    signal = "HOLD"
    score = 0
    reasons = []
    components = {
        "ema_crossover": 0,
        "rsi_quality": 0,
        "trend_alignment": 0,
        "volume": 0,
    }

    if ema_distance_pct < MIN_EMA_DISTANCE_PCT:
        reasons.append("EMA distance is too small, sideways market avoided")
    elif current_volume < MIN_VOLUME:
        reasons.append("Volume is below the minimum liquidity filter")
    elif ema9 > ema21 and 60 <= rsi <= 75:
        signal = "BUY"
        components["ema_crossover"] = 40
        reasons.append("EMA9 is above EMA21")
        components["rsi_quality"] = 30
        reasons.append("RSI is in the 60-75 buy quality band")
    elif ema9 < ema21 and 25 <= rsi <= 40:
        signal = "SELL"
        components["ema_crossover"] = 40
        reasons.append("EMA9 is below EMA21")
        components["rsi_quality"] = 30
        reasons.append("RSI is in the 25-40 sell quality band")
    else:
        reasons.append("EMA and RSI are not inside the improved trade bands")

    if signal == "BUY" and trend == "UP":
        components["trend_alignment"] = 20
        reasons.append("1m and 5m trends match")
    elif signal == "SELL" and trend == "DOWN":
        components["trend_alignment"] = 20
        reasons.append("1m and 5m trends match")
    elif signal != "HOLD":
        reasons.append("1m and 5m trends are not aligned")

    if signal != "HOLD" and current_volume >= max(MIN_VOLUME, avg_volume):
        components["volume"] = 10
        reasons.append("Volume is above the 20-candle average")

    score = sum(components.values())
    if score < MIN_CONFIDENCE:
        signal = "HOLD"
        reasons.append("Confidence is below the 75 threshold")

    return {
        "coin": symbol,
        "symbol": symbol,
        "price": round(price, 4),
        "signal": signal,
        "ema9": round(ema9, 4),
        "ema21": round(ema21, 4),
        "rsi": round(rsi, 2),
        "volume": round(current_volume, 2),
        "avg_volume": round(avg_volume, 2),
        "ema_distance_pct": round(ema_distance_pct, 4),
        "trend": trend,
        "confidence": min(score, 100),
        "components": components,
        "reason": "; ".join(reasons),
    }


def scan_market() -> dict:
    candidates = [_analyze_symbol(symbol) for symbol in SYMBOLS]
    tradable = [candidate for candidate in candidates if candidate["signal"] != "HOLD"]
    best = max(tradable or candidates, key=lambda item: item["confidence"])
    return {"coins": candidates, "best": best}


def evaluate_market(mode: Optional[str] = None) -> dict:
    normalized_mode = normalize_mode(mode)
    scan = scan_market()
    best = scan["best"]
    with DB_LOCK, get_connection() as conn:
        conn.execute(
            """
            INSERT INTO decisions (mode, symbol, signal, ema9, ema21, rsi, price, trend, confidence, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_mode,
                best["coin"],
                best["signal"],
                best["ema9"],
                best["ema21"],
                best["rsi"],
                best["price"],
                best["trend"],
                best["confidence"],
                best["reason"],
                now_iso(),
            ),
        )
        conn.commit()
    return {**best, "scan": scan["coins"], "mode": normalized_mode}
