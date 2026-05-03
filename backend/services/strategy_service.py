import os
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from typing import Optional

from database import DB_LOCK, get_connection, normalize_mode, now_iso
from services.market_service import SYMBOLS, candles

def _env_float(name: str, fallback: float) -> float:
    try:
        return float(os.getenv(name, fallback))
    except (TypeError, ValueError):
        return fallback


MIN_CONFIDENCE = _env_float("STRATEGY_MIN_CONFIDENCE", 75)
MIN_VOLUME = _env_float("STRATEGY_MIN_VOLUME", 900)
MIN_EMA_DISTANCE_PCT = _env_float("STRATEGY_MIN_EMA_DISTANCE_PCT", 0.05)
STOP_LOSS_PCT = _env_float("STRATEGY_STOP_LOSS_PCT", 1.5)
TAKE_PROFIT_PCT = _env_float("STRATEGY_TAKE_PROFIT_PCT", 3.0)


def _analyze_symbol(symbol: str) -> dict:
    frame_1m = candles(symbol, "1m", 260)
    frame_5m = candles(symbol, "5m", 260)

    for frame in (frame_1m, frame_5m):
        frame["ema20"] = EMAIndicator(close=frame["close"], window=20).ema_indicator()
        frame["ema50"] = EMAIndicator(close=frame["close"], window=50).ema_indicator()
        frame["ema200"] = EMAIndicator(close=frame["close"], window=200).ema_indicator()
        frame["rsi"] = RSIIndicator(close=frame["close"], window=14).rsi()
        macd = MACD(close=frame["close"], window_slow=26, window_fast=12, window_sign=9)
        frame["macd"] = macd.macd()
        frame["macd_signal"] = macd.macd_signal()
        frame["macd_hist"] = macd.macd_diff()

    last = frame_1m.iloc[-1]
    previous = frame_1m.iloc[-2]
    last_5m = frame_5m.iloc[-1]

    price = float(last["close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    ema200 = float(last["ema200"])
    rsi = float(last["rsi"])
    macd_value = float(last["macd"])
    macd_signal = float(last["macd_signal"])
    macd_hist = float(last["macd_hist"])
    previous_macd = float(previous["macd"])
    previous_macd_signal = float(previous["macd_signal"])
    ema_distance_pct = abs(ema50 - ema200) / price * 100
    avg_volume = float(frame_1m["volume"].tail(20).mean())
    current_volume = float(last["volume"])
    trend_1m = "UP" if ema50 > ema200 and price > ema50 else "DOWN" if ema50 < ema200 and price < ema50 else "SIDEWAYS"
    trend_5m = "UP" if float(last_5m["ema50"]) > float(last_5m["ema200"]) else "DOWN" if float(last_5m["ema50"]) < float(last_5m["ema200"]) else "SIDEWAYS"
    trend = trend_1m if trend_1m == trend_5m else "MIXED"
    signal = "HOLD"
    reasons = []
    components = {
        "trend_filter": 0,
        "macd_confirmation": 0,
        "rsi_quality": 0,
        "trend_alignment": 0,
        "volume": 0,
        "risk_filter": 0,
    }

    if ema_distance_pct < MIN_EMA_DISTANCE_PCT:
        reasons.append("EMA50/EMA200 distance is too small, sideways market avoided")
    elif current_volume < MIN_VOLUME:
        reasons.append("Volume is below the minimum liquidity filter")
    elif trend_1m == "UP" and 45 <= rsi <= 70:
        signal = "BUY"
        components["trend_filter"] = 25
        reasons.append("Price is above EMA50 and EMA50 is above EMA200")
        components["rsi_quality"] = 20
        reasons.append("RSI is in the 45-70 trend-entry band")
    elif trend_1m == "DOWN" and 30 <= rsi <= 55:
        signal = "SELL"
        components["trend_filter"] = 25
        reasons.append("Price is below EMA50 and EMA50 is below EMA200")
        components["rsi_quality"] = 20
        reasons.append("RSI is in the 30-55 downtrend-entry band")
    else:
        reasons.append("Trend and RSI are not aligned for a high-quality entry")

    bullish_macd_cross = previous_macd <= previous_macd_signal and macd_value > macd_signal
    bearish_macd_cross = previous_macd >= previous_macd_signal and macd_value < macd_signal
    bullish_macd_momentum = macd_value > macd_signal and macd_hist > 0
    bearish_macd_momentum = macd_value < macd_signal and macd_hist < 0
    if signal == "BUY" and (bullish_macd_cross or bullish_macd_momentum):
        components["macd_confirmation"] = 25
        reasons.append("MACD confirms bullish momentum")
    elif signal == "SELL" and (bearish_macd_cross or bearish_macd_momentum):
        components["macd_confirmation"] = 25
        reasons.append("MACD confirms bearish momentum")
    elif signal != "HOLD":
        reasons.append("MACD has not confirmed momentum")

    if signal == "BUY" and trend == "UP":
        components["trend_alignment"] = 15
        reasons.append("1m and 5m trends match")
    elif signal == "SELL" and trend == "DOWN":
        components["trend_alignment"] = 15
        reasons.append("1m and 5m trends match")
    elif signal != "HOLD":
        reasons.append("1m and 5m trends are not aligned")

    if signal != "HOLD" and current_volume >= max(MIN_VOLUME, avg_volume):
        components["volume"] = 10
        reasons.append("Volume is above the 20-candle average")

    if signal != "HOLD":
        components["risk_filter"] = 5
        reasons.append(f"Risk plan: {STOP_LOSS_PCT}% stop loss and {TAKE_PROFIT_PCT}% take profit")

    score = sum(components.values())
    if score < MIN_CONFIDENCE:
        signal = "HOLD"
        reasons.append("Confidence is below the 75 threshold")

    stop_loss = None
    take_profit = None
    if signal == "BUY":
        stop_loss = round(price * (1 - STOP_LOSS_PCT / 100), 4)
        take_profit = round(price * (1 + TAKE_PROFIT_PCT / 100), 4)
    elif signal == "SELL":
        stop_loss = round(price * (1 + STOP_LOSS_PCT / 100), 4)
        take_profit = round(price * (1 - TAKE_PROFIT_PCT / 100), 4)

    return {
        "coin": symbol,
        "symbol": symbol,
        "price": round(price, 4),
        "signal": signal,
        "ema9": round(ema20, 4),
        "ema21": round(ema50, 4),
        "ema20": round(ema20, 4),
        "ema50": round(ema50, 4),
        "ema200": round(ema200, 4),
        "macd": round(macd_value, 4),
        "macd_signal": round(macd_signal, 4),
        "macd_hist": round(macd_hist, 4),
        "rsi": round(rsi, 2),
        "volume": round(current_volume, 2),
        "avg_volume": round(avg_volume, 2),
        "ema_distance_pct": round(ema_distance_pct, 4),
        "trend": trend,
        "confidence": min(score, 100),
        "components": components,
        "indicators_used": ["EMA50/EMA200 trend filter", "MACD(12,26,9)", "RSI(14)", "Volume 20-candle average", "1m + 5m trend alignment"],
        "stop_loss": stop_loss,
        "take_profit": take_profit,
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
