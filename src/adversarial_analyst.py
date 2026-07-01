"""
Adversarial Analyst — generates balanced bull/bear analysis per stock using DeepSeek V4 Flash.
Each argument MUST reference data from the pipeline. No fabricated sources.
"""
import json
import os
import requests
import time
from src.config import (
    DEEPSEEK_API_KEY_ENV, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL, DATA_DIR
)


def get_api_key() -> str:
    """Get DeepSeek API key from environment."""
    key = os.environ.get(DEEPSEEK_API_KEY_ENV)
    if not key:
        # Try reading from Hermes .env
        import pathlib
        env_path = pathlib.Path.home() / ".hermes" / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.strip().startswith(DEEPSEEK_API_KEY_ENV):
                        key = line.strip().split("=", 1)[1]
                        break
    if not key:
        raise RuntimeError(f"{DEEPSEEK_API_KEY_ENV} not found in environment or ~/.hermes/.env")
    return key


def build_analysis_prompt(stock_data: dict, tech_data: dict, fund_data: dict, news: list) -> str:
    """Build the adversarial analysis prompt for one stock."""
    ticker = stock_data.get("ticker", "UNKNOWN")
    name = stock_data.get("long_name", stock_data.get("company_name", ticker))
    sector = stock_data.get("sector", "Unknown")
    industry = stock_data.get("industry", "Unknown")
    price = stock_data.get("current_price", "N/A")
    change = stock_data.get("change_pct", 0)
    is_penny = stock_data.get("is_penny_stock", False)
    
    # Technical summary
    tech_lines = []
    if tech_data and not tech_data.get("error"):
        tech_lines.append(f"RSI: {tech_data.get('rsi', 'N/A')} ({tech_data.get('rsi_signal', 'N/A')})")
        tech_lines.append(f"MACD: {tech_data.get('macd_signal_type', 'N/A')}")
        tech_lines.append(f"MA50: {tech_data.get('ma50', 'N/A')} (price {tech_data.get('price_vs_ma50', 'N/A')})")
        tech_lines.append(f"MA200: {tech_data.get('ma200', 'N/A')} (price {tech_data.get('price_vs_ma200', 'N/A')})")
        tech_lines.append(f"Bollinger: {tech_data.get('bb_signal', 'N/A')}")
        tech_lines.append(f"Volume: {tech_data.get('volume_signal', 'N/A')} ({stock_data.get('volume_ratio', 1)}x avg)")
        tech_lines.append(f"Technical summary: {tech_data.get('technical_summary', 'N/A')} (bull={tech_data.get('bullish_count', 0)}, bear={tech_data.get('bearish_count', 0)})")
    
    # Fundamental summary
    fund_lines = []
    if fund_data and not fund_data.get("error"):
        fund_lines.append(f"P/E: {stock_data.get('pe_ratio', 'N/A')}")
        fund_lines.append(f"Forward P/E: {stock_data.get('forward_pe', 'N/A')}")
        fund_lines.append(f"P/B: {stock_data.get('pb_ratio', 'N/A')}")
        fund_lines.append(f"Debt/Equity: {stock_data.get('debt_to_equity', 'N/A')}")
        fund_lines.append(f"Current Ratio: {stock_data.get('current_ratio', 'N/A')}")
        fund_lines.append(f"Revenue Growth: {stock_data.get('revenue_growth', 'N/A')}")
        fund_lines.append(f"Profit Margins: {stock_data.get('profit_margins', 'N/A')}")
        fund_lines.append(f"Market Cap: {stock_data.get('market_cap', 'N/A')}")
        fund_lines.append(f"Fundamental Score: {fund_data.get('overall_score', 'N/A')}/10")
        
        if fund_data.get("flags", {}).get("green"):
            fund_lines.append(f"Green flags: {'; '.join(fund_data['flags']['green'])}")
        if fund_data.get("flags", {}).get("red"):
            fund_lines.append(f"Red flags: {'; '.join(fund_data['flags']['red'])}")
    
    # Quarterly data
    quarter_lines = []
    for q in stock_data.get("quarters", [])[:4]:
        rev = q.get("revenue")
        rev_str = f"${rev/1e6:.1f}M" if rev and rev > 0 else "N/A"
        ni = q.get("net_income")
        ni_str = f"${ni/1e6:.1f}M" if ni and ni != 0 else "N/A"
        quarter_lines.append(f"  {q.get('quarter', '?')}: Revenue={rev_str}, Net Income={ni_str}")
    
    # News summary
    news_lines = []
    for n in news[:3]:
        if n.get("title"):
            news_lines.append(f"- {n['title']} ({n.get('publisher', '?')}) [{n.get('url', '')}]")
    
    prompt = f"""You are a ruthlessly objective financial analyst. Your job is to analyze {ticker} ({name}) and produce BOTH a bull case and a bear case. You must be equally persuasive on both sides — do not favor one direction.

## Stock: {ticker} — {name}
- Sector: {sector} / {industry}
- Price: ${price} ({change:+.1f}% today)
- Penny stock: {"YES ⚠️" if is_penny else "No"}

## Technical Indicators:
{chr(10).join(tech_lines) if tech_lines else "No data available"}

## Fundamentals:
{chr(10).join(fund_lines) if fund_lines else "No data available"}

## Quarterly Data (most recent first):
{chr(10).join(quarter_lines) if quarter_lines else "No quarterly data available"}

## Recent News:
{chr(10).join(news_lines) if news_lines else "No recent news"}

---

## Your Task:

Produce a JSON object with EXACTLY this structure. Each argument must reference specific data from above. Do NOT invent numbers or sources. If data is missing, say "data not available".

```json
{{
  "ticker": "{ticker}",
  "bull_case": {{
    "confidence": <1-10>,
    "arguments": [
      {{
        "title": "<short title>",
        "detail": "<2-3 sentences referencing specific data>",
        "data_source": "<which metric/news/quarterly data this is based on>"
      }},
      {{
        "title": "<short title>",
        "detail": "<2-3 sentences>",
        "data_source": "<source>"
      }},
      {{
        "title": "<short title>",
        "detail": "<2-3 sentences>",
        "data_source": "<source>"
      }}
    ]
  }},
  "bear_case": {{
    "confidence": <1-10>,
    "arguments": [
      {{
        "title": "<short title>",
        "detail": "<2-3 sentences referencing specific data>",
        "data_source": "<which metric/news/quarterly data this is based on>"
      }},
      {{
        "title": "<short title>",
        "detail": "<2-3 sentences>",
        "data_source": "<source>"
      }},
      {{
        "title": "<short title>",
        "detail": "<2-3 sentences>",
        "data_source": "<source>"
      }}
    ]
  }},
  "verdict": "<one sentence: net bullish, net bearish, or balanced — with the key reason>",
  "key_risk": "<the single biggest risk in one sentence>",
  "key_catalyst": "<the single biggest potential catalyst in one sentence>"
}}
```

Rules:
1. Be SPECIFIC — reference actual numbers from the data above
2. Be HONEST — if the bear case is stronger, give it a higher confidence
3. Be CRITICAL — don't just repeat bullish narratives; find genuine weaknesses
4. For penny stocks: the bear case MUST address manipulation/delisting risk
5. Return ONLY valid JSON — no markdown, no explanation outside the JSON"""

    return prompt


def analyze_stock(stock_data: dict, tech_data: dict, fund_data: dict, news: list, api_key: str) -> dict:
    """Run adversarial analysis for a single stock via DeepSeek API."""
    ticker = stock_data.get("ticker", "UNKNOWN")
    
    if stock_data.get("error"):
        return {"ticker": ticker, "error": stock_data["error"]}
    
    prompt = build_analysis_prompt(stock_data, tech_data, fund_data, news)
    
    try:
        response = requests.post(
            DEEPSEEK_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a ruthlessly objective financial analyst. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1500,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        
        if response.status_code != 200:
            return {"ticker": ticker, "error": f"API error {response.status_code}: {response.text[:200]}"}
        
        content = response.json()["choices"][0]["message"]["content"]
        
        # Parse JSON response
        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                analysis = json.loads(match.group())
            else:
                return {"ticker": ticker, "error": "Could not parse JSON response"}
        
        return analysis
        
    except requests.exceptions.Timeout:
        return {"ticker": ticker, "error": "API timeout (30s)"}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def analyze_all_stocks(stock_data_list: list, tech_data_list: list, fund_data_list: list, news_map: dict) -> list:
    """Run adversarial analysis for all stocks."""
    api_key = get_api_key()
    
    # Build lookup maps
    tech_map = {t["ticker"]: t for t in tech_data_list if t.get("ticker")}
    fund_map = {f["ticker"]: f for f in fund_data_list if f.get("ticker")}
    
    results = []
    total = len(stock_data_list)
    
    for i, stock in enumerate(stock_data_list):
        ticker = stock.get("ticker", f"UNKNOWN_{i}")
        print(f"  [{i+1}/{total}] Analyzing {ticker}...", end="", flush=True)
        
        tech = tech_map.get(ticker, {})
        fund = fund_map.get(ticker, {})
        news = news_map.get(ticker, [])
        
        analysis = analyze_stock(stock, tech, fund, news, api_key)
        results.append(analysis)
        
        if analysis.get("error"):
            print(f" ❌ {analysis['error']}")
        else:
            bull_conf = analysis.get("bull_case", {}).get("confidence", "?")
            bear_conf = analysis.get("bear_case", {}).get("confidence", "?")
            print(f" ✅ Bull:{bull_conf}/10 Bear:{bear_conf}/10")
        
        time.sleep(0.5)  # Rate limit DeepSeek API
    
    return results


if __name__ == "__main__":
    import glob
    
    # Load all data
    stock_files = sorted(glob.glob(os.path.join(DATA_DIR, "stocks_*.json")))
    if not stock_files:
        print("No stock data found. Run data_collector first.")
        exit(1)
    
    with open(stock_files[-1]) as f:
        stock_data = json.load(f)
    
    tech_file = os.path.join(DATA_DIR, "technical_analysis.json")
    fund_file = os.path.join(DATA_DIR, "fundamental_analysis.json")
    news_file = sorted(glob.glob(os.path.join(DATA_DIR, "news_*.json")))
    
    tech_data = []
    fund_data = []
    news_data = {}
    
    if os.path.exists(tech_file):
        with open(tech_file) as f:
            tech_data = json.load(f)
    if os.path.exists(fund_file):
        with open(fund_file) as f:
            fund_data = json.load(f)
    if news_file:
        with open(news_file[-1]) as f:
            news_data = json.load(f)
    
    print(f"=== Adversarial Analysis ===")
    print(f"Stocks: {len(stock_data)} | Tech: {len(tech_data)} | Fund: {len(fund_data)} | News: {len(news_data)}\n")
    
    results = analyze_all_stocks(stock_data, tech_data, fund_data, news_data)
    
    out_file = os.path.join(DATA_DIR, "adversarial_analysis.json")
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved to {out_file}")
