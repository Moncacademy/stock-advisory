"""
News Collector — fetches recent news for each stock via yfinance news API
and web search for catalysts.
"""
import yfinance as yf
import time
import json
import os
from src.config import ALL_TICKERS, YFINANCE_DELAY_MS, DATA_DIR


def fetch_stock_news(ticker_symbol: str, max_items: int = 5) -> list:
    """Fetch recent news for a single ticker via yfinance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news
        
        if not news:
            return []
        
        items = []
        for item in news[:max_items]:
            # yfinance news format varies; handle both old and new
            title = item.get("title", "")
            publisher = item.get("publisher", item.get("source", {}).get("title", "Unknown"))
            link = item.get("link", item.get("url", ""))
            publish_time = item.get("providerPublishTime", item.get("publish_time", ""))
            
            # Convert timestamp if numeric
            if isinstance(publish_time, (int, float)):
                from datetime import datetime
                publish_time = datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M")
            
            # Extract thumbnail if available
            thumbnail = None
            if "thumbnail" in item:
                thumb = item["thumbnail"]
                if isinstance(thumb, dict):
                    resolutions = thumb.get("resolutions", [])
                    if resolutions:
                        thumbnail = resolutions[0].get("url")
            elif "content" in item and isinstance(item["content"], dict):
                # New yfinance format
                content = item["content"]
                title = content.get("title", title)
                publisher = content.get("provider", {}).get("displayName", publisher)
                link = content.get("canonicalUrl", {}).get("url", link)
                publish_time = content.get("pubDate", publish_time)
                
            items.append({
                "title": title,
                "publisher": publisher,
                "url": link,
                "date": str(publish_time),
                "thumbnail": thumbnail,
            })
        
        return items
        
    except Exception as e:
        return [{"error": str(e), "ticker": ticker_symbol}]


def fetch_all_news(tickers: list = None, max_per_stock: int = 3) -> dict:
    """Fetch news for all tickers with rate limiting."""
    if tickers is None:
        tickers = ALL_TICKERS
    
    news_map = {}
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        print(f"  [{i+1}/{total}] News for {ticker}...", end="", flush=True)
        news = fetch_stock_news(ticker, max_items=max_per_stock)
        news_map[ticker] = news
        
        if news:
            print(f" ✅ {len(news)} articles")
        else:
            print(f" ⚪ no news")
        
        time.sleep(YFINANCE_DELAY_MS / 1000)
    
    return news_map


if __name__ == "__main__":
    print("=== Stock Advisory News Collector ===")
    print(f"Fetching news for {len(ALL_TICKERS)} tickers...\n")
    news = fetch_all_news(max_per_stock=3)
    
    from datetime import datetime
    filename = f"news_{datetime.now().strftime('%Y-%m-%d')}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(news, f, indent=2, default=str)
    print(f"\nSaved to {filepath}")
    
    total_articles = sum(len(v) for v in news.values())
    print(f"Total articles: {total_articles}")
