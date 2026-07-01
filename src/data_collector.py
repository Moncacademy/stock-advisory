"""
Data Collector — fetches price, volume, fundamentals, and quarterly data via yfinance.
Also fetches SEC EDGAR filings for Q1-Q4 references.
"""
import yfinance as yf
import time
import json
import os
from src.config import ALL_TICKERS, YFINANCE_DELAY_MS, DATA_DIR, PENNY_STOCK_THRESHOLD


def fetch_stock_data(ticker_symbol: str) -> dict:
    """Fetch comprehensive data for a single ticker via yfinance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        hist = ticker.history(period="3mo", interval="1d")
        
        if hist.empty:
            return {"ticker": ticker_symbol, "error": "No data", "category": None}

        # Current price data
        current_price = float(hist['Close'].iloc[-1])
        prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
        change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0
        
        # Volume data
        current_volume = int(hist['Volume'].iloc[-1])
        avg_volume_20 = int(hist['Volume'].tail(20).mean()) if len(hist) >= 20 else current_volume
        volume_ratio = round(current_volume / avg_volume_20, 2) if avg_volume_20 else 1.0

        # 52-week range
        week52_high = info.get("fiftyTwoWeekHigh", None)
        week52_low = info.get("fiftyTwoWeekLow", None)
        
        # Fundamentals
        pe_ratio = info.get("trailingPE", None)
        forward_pe = info.get("forwardPE", None)
        pb_ratio = info.get("priceToBook", None)
        debt_to_equity = info.get("debtToEquity", None)
        current_ratio = info.get("currentRatio", None)
        revenue_growth = info.get("revenueGrowth", None)
        profit_margins = info.get("profitMargins", None)
        market_cap = info.get("marketCap", None)
        
        # Quarterly financials (Q1-Q4)
        quarterly_fin = ticker.quarterly_financials
        quarterly_income = ticker.quarterly_income_stmt
        
        quarters = []
        if not quarterly_income.empty:
            for col in quarterly_income.columns[:4]:  # Last 4 quarters
                q_label = col.strftime("%Y-Q%q") if hasattr(col, 'strftime') else str(col)
                # Fix quarter labeling
                month = col.month if hasattr(col, 'month') else 0
                q_num = (month - 1) // 3 + 1 if month else 0
                q_label = f"{col.year}-Q{q_num}" if hasattr(col, 'year') else str(col)
                
                revenue = quarterly_income.loc['Total Revenue', col] if 'Total Revenue' in quarterly_income.index else None
                gross_profit = quarterly_income.loc['Gross Profit', col] if 'Gross Profit' in quarterly_income.index else None
                net_income = quarterly_income.loc['Net Income', col] if 'Net Income' in quarterly_income.index else None
                
                quarters.append({
                    "quarter": q_label,
                    "revenue": float(revenue) if revenue and revenue == revenue else None,  # NaN check
                    "gross_profit": float(gross_profit) if gross_profit and gross_profit == gross_profit else None,
                    "net_income": float(net_income) if net_income and net_income == net_income else None,
                })

        # Company info
        company_name = info.get("shortName", ticker_symbol)
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")
        long_name = info.get("longName", company_name)
        website = info.get("website", None)
        
        # Is penny stock?
        is_penny = current_price < PENNY_STOCK_THRESHOLD

        # Sparkline data (last 30 closes)
        sparkline = [round(float(x), 2) for x in hist['Close'].tail(30).tolist()]

        data = {
            "ticker": ticker_symbol,
            "company_name": company_name,
            "long_name": long_name,
            "sector": sector,
            "industry": industry,
            "website": website,
            "current_price": round(current_price, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": round(change_pct, 2),
            "volume": current_volume,
            "avg_volume": avg_volume_20,
            "volume_ratio": volume_ratio,
            "week52_high": week52_high,
            "week52_low": week52_low,
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "pb_ratio": pb_ratio,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "revenue_growth": revenue_growth,
            "profit_margins": profit_margins,
            "market_cap": market_cap,
            "is_penny_stock": is_penny,
            "quarters": quarters,
            "sparkline": sparkline,
            "history": {
                "closes": [round(float(x), 2) for x in hist['Close'].tolist()],
                "volumes": [int(x) for x in hist['Volume'].tolist()],
                "highs": [round(float(x), 2) for x in hist['High'].tolist()],
                "lows": [round(float(x), 2) for x in hist['Low'].tolist()],
            },
            "error": None,
        }
        
        return data
        
    except Exception as e:
        return {"ticker": ticker_symbol, "error": str(e), "category": None}


def fetch_all_stocks(tickers: list = None) -> list:
    """Fetch data for all tickers with rate limiting."""
    if tickers is None:
        tickers = ALL_TICKERS
    
    results = []
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        print(f"  [{i+1}/{total}] Fetching {ticker}...", end="", flush=True)
        data = fetch_stock_data(ticker)
        results.append(data)
        
        if data.get("error"):
            print(f" ❌ {data['error']}")
        else:
            print(f" ✅ ${data['current_price']} ({data['change_pct']:+.1f}%)")
        
        time.sleep(YFINANCE_DELAY_MS / 1000)
    
    return results


def save_data(data: list, filename: str = None):
    """Save collected data to JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if filename is None:
        from datetime import datetime
        filename = f"stocks_{datetime.now().strftime('%Y-%m-%d')}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Data saved to {filepath}")
    return filepath


if __name__ == "__main__":
    print("=== Stock Advisory Data Collector ===")
    print(f"Fetching data for {len(ALL_TICKERS)} tickers...\n")
    data = fetch_all_stocks()
    save_data(data)
    
    success = sum(1 for d in data if not d.get("error"))
    print(f"\nDone: {success}/{len(data)} successful")
