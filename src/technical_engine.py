"""
Technical Analysis Engine — computes RSI, MACD, Bollinger Bands, MAs, and detects patterns.
Uses the 'ta' library for indicator calculation.
"""
import pandas as pd
import numpy as np
import ta
from src.config import DATA_DIR
import json
import os


def compute_indicators(stock_data: dict) -> dict:
    """Compute technical indicators from stock price history."""
    if stock_data.get("error"):
        return {"ticker": stock_data["ticker"], "error": stock_data["error"]}
    
    closes = stock_data.get("history", {}).get("closes", [])
    volumes = stock_data.get("history", {}).get("volumes", [])
    highs = stock_data.get("history", {}).get("highs", [])
    lows = stock_data.get("history", {}).get("lows", [])
    
    if len(closes) < 10:
        return {"ticker": stock_data["ticker"], "error": "Insufficient data"}
    
    df = pd.DataFrame({
        "close": closes,
        "high": highs,
        "low": lows,
        "volume": volumes,
    })
    
    indicators = {"ticker": stock_data["ticker"], "error": None}
    
    # --- RSI (14 period) ---
    try:
        rsi_series = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        rsi_val = float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]) else None
        indicators["rsi"] = round(rsi_val, 1) if rsi_val else None
        if rsi_val:
            if rsi_val < 30:
                indicators["rsi_signal"] = "oversold"
            elif rsi_val > 70:
                indicators["rsi_signal"] = "overbought"
            else:
                indicators["rsi_signal"] = "neutral"
        else:
            indicators["rsi_signal"] = "unknown"
    except Exception:
        indicators["rsi"] = None
        indicators["rsi_signal"] = "unknown"
    
    # --- MACD ---
    try:
        macd_ind = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        macd_line = float(macd_ind.macd().iloc[-1]) if not pd.isna(macd_ind.macd().iloc[-1]) else None
        signal_line = float(macd_ind.macd_signal().iloc[-1]) if not pd.isna(macd_ind.macd_signal().iloc[-1]) else None
        histogram = float(macd_ind.macd_diff().iloc[-1]) if not pd.isna(macd_ind.macd_diff().iloc[-1]) else None
        
        indicators["macd_line"] = round(macd_line, 4) if macd_line else None
        indicators["macd_signal"] = round(signal_line, 4) if signal_line else None
        indicators["macd_histogram"] = round(histogram, 4) if histogram else None
        
        if macd_line is not None and signal_line is not None:
            if macd_line > signal_line:
                indicators["macd_signal_type"] = "bullish"
            else:
                indicators["macd_signal_type"] = "bearish"
        else:
            indicators["macd_signal_type"] = "unknown"
    except Exception:
        indicators["macd_signal_type"] = "unknown"
    
    # --- Moving Averages ---
    try:
        if len(closes) >= 50:
            ma50 = df["close"].rolling(window=50).mean().iloc[-1]
            indicators["ma50"] = round(float(ma50), 2)
            indicators["price_vs_ma50"] = "above" if closes[-1] > ma50 else "below"
        else:
            indicators["ma50"] = None
            indicators["price_vs_ma50"] = "n/a"
    except Exception:
        indicators["ma50"] = None
        indicators["price_vs_ma50"] = "n/a"
    
    try:
        if len(closes) >= 200:
            ma200 = df["close"].rolling(window=200).mean().iloc[-1]
            indicators["ma200"] = round(float(ma200), 2)
            indicators["price_vs_ma200"] = "above" if closes[-1] > ma200 else "below"
            # Golden cross / Death cross
            if indicators.get("ma50") and ma200:
                if indicators["ma50"] > indicators["ma200"]:
                    indicators["ma_cross"] = "golden_cross"
                else:
                    indicators["ma_cross"] = "death_cross"
        else:
            indicators["ma200"] = None
            indicators["price_vs_ma200"] = "n/a"
            indicators["ma_cross"] = "n/a"
    except Exception:
        indicators["ma200"] = None
        indicators["price_vs_ma200"] = "n/a"
        indicators["ma_cross"] = "n/a"
    
    # --- Bollinger Bands ---
    try:
        bb_ind = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
        bb_upper = float(bb_ind.bollinger_hband().iloc[-1]) if not pd.isna(bb_ind.bollinger_hband().iloc[-1]) else None
        bb_lower = float(bb_ind.bollinger_lband().iloc[-1]) if not pd.isna(bb_ind.bollinger_lband().iloc[-1]) else None
        bb_middle = float(bb_ind.bollinger_mavg().iloc[-1]) if not pd.isna(bb_ind.bollinger_mavg().iloc[-1]) else None
        
        if bb_upper and bb_lower and bb_middle:
            indicators["bb_upper"] = round(bb_upper, 2)
            indicators["bb_lower"] = round(bb_lower, 2)
            indicators["bb_middle"] = round(bb_middle, 2)
            
            current = closes[-1]
            if current <= bb_lower:
                indicators["bb_signal"] = "near_lower_band"
            elif current >= bb_upper:
                indicators["bb_signal"] = "near_upper_band"
            else:
                indicators["bb_signal"] = "middle"
        else:
            indicators["bb_signal"] = "unknown"
    except Exception:
        indicators["bb_signal"] = "unknown"
    
    # --- Volume Analysis ---
    try:
        vol = stock_data.get("volume", 0)
        avg_vol = stock_data.get("avg_volume", 0)
        ratio = stock_data.get("volume_ratio", 1.0)
        
        if ratio >= 2.0:
            indicators["volume_signal"] = "high_volume_spike"
        elif ratio >= 1.5:
            indicators["volume_signal"] = "elevated_volume"
        elif ratio < 0.5:
            indicators["volume_signal"] = "low_volume"
        else:
            indicators["volume_signal"] = "normal"
    except Exception:
        indicators["volume_signal"] = "unknown"
    
    # --- Support/Resistance (simple: min/max of last 20 days) ---
    try:
        recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        indicators["support_20d"] = round(recent_low, 2)
        indicators["resistance_20d"] = round(recent_high, 2)
        current = closes[-1]
        
        distance_to_resistance = ((recent_high - current) / current * 100) if current else 0
        distance_to_support = ((current - recent_low) / current * 100) if current else 0
        indicators["pct_to_resistance"] = round(distance_to_resistance, 1)
        indicators["pct_to_support"] = round(distance_to_support, 1)
    except Exception:
        pass
    
    # --- Overall technical signal ---
    bullish_signals = 0
    bearish_signals = 0
    
    if indicators.get("rsi_signal") == "oversold":
        bullish_signals += 1
    elif indicators.get("rsi_signal") == "overbought":
        bearish_signals += 1
    
    if indicators.get("macd_signal_type") == "bullish":
        bullish_signals += 1
    elif indicators.get("macd_signal_type") == "bearish":
        bearish_signals += 1
    
    if indicators.get("price_vs_ma50") == "above":
        bullish_signals += 1
    elif indicators.get("price_vs_ma50") == "below":
        bearish_signals += 1
    
    if indicators.get("price_vs_ma200") == "above":
        bullish_signals += 1
    elif indicators.get("price_vs_ma200") == "below":
        bearish_signals += 1
    
    if indicators.get("ma_cross") == "golden_cross":
        bullish_signals += 1
    elif indicators.get("ma_cross") == "death_cross":
        bearish_signals += 1
    
    if indicators.get("volume_signal") in ("high_volume_spike", "elevated_volume"):
        if stock_data.get("change_pct", 0) > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
    
    if indicators.get("bb_signal") == "near_lower_band":
        bullish_signals += 1
    elif indicators.get("bb_signal") == "near_upper_band":
        bearish_signals += 1
    
    indicators["bullish_count"] = bullish_signals
    indicators["bearish_count"] = bearish_signals
    indicators["technical_summary"] = (
        "bullish" if bullish_signals > bearish_signals + 1
        else "bearish" if bearish_signals > bullish_signals + 1
        else "neutral"
    )
    
    return indicators


def analyze_all(stock_data_list: list) -> list:
    """Compute indicators for all stocks."""
    results = []
    for stock in stock_data_list:
        indicators = compute_indicators(stock)
        results.append(indicators)
    return results


if __name__ == "__main__":
    # Load latest data and analyze
    import glob
    files = sorted(glob.glob(os.path.join(DATA_DIR, "stocks_*.json")))
    if not files:
        print("No data files found. Run data_collector first.")
        exit(1)
    
    with open(files[-1]) as f:
        stock_data = json.load(f)
    
    print(f"Analyzing {len(stock_data)} stocks...")
    indicators = analyze_all(stock_data)
    
    # Save
    out_file = os.path.join(DATA_DIR, "technical_analysis.json")
    with open(out_file, 'w') as f:
        json.dump(indicators, f, indent=2, default=str)
    print(f"Saved to {out_file}")
    
    # Summary
    bullish = sum(1 for i in indicators if i.get("technical_summary") == "bullish")
    bearish = sum(1 for i in indicators if i.get("technical_summary") == "bearish")
    neutral = sum(1 for i in indicators if i.get("technical_summary") == "neutral")
    errors = sum(1 for i in indicators if i.get("error"))
    print(f"\nBullish: {bullish} | Bearish: {bearish} | Neutral: {neutral} | Errors: {errors}")
