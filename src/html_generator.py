"""
HTML Generator — produces a responsive, dark-mode daily brief HTML page.
Outputs to docs/index.html for GitHub Pages.
"""
import json
import os
from datetime import datetime
from src.config import DATA_DIR, HTML_OUTPUT, WATCHLIST


def generate_sparkline(prices: list, width: int = 100, height: int = 30) -> str:
    """Generate inline SVG sparkline from price list."""
    if not prices or len(prices) < 2:
        return ""
    
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price if max_price != min_price else 1
    
    points = []
    for i, price in enumerate(prices):
        x = (i / (len(prices) - 1)) * width
        y = height - ((price - min_price) / price_range) * height
        points.append(f"{x:.1f},{y:.1f}")
    
    # Determine color (green if last > first, red otherwise)
    color = "#00d09c" if prices[-1] >= prices[0] else "#ff5252"
    
    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <polyline points="{' '.join(points)}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
    return svg


def format_market_cap(mcap) -> str:
    """Format market cap to human readable."""
    if not mcap or mcap != mcap:
        return "N/A"
    if mcap >= 1e12:
        return f"${mcap/1e12:.1f}T"
    elif mcap >= 1e9:
        return f"${mcap/1e9:.1f}B"
    elif mcap >= 1e6:
        return f"${mcap/1e6:.1f}M"
    return f"${mcap:,.0f}"


def format_volume(vol) -> str:
    if not vol or vol != vol:
        return "N/A"
    if vol >= 1e9:
        return f"{vol/1e9:.1f}B"
    elif vol >= 1e6:
        return f"{vol/1e6:.1f}M"
    elif vol >= 1e3:
        return f"{vol/1e3:.1f}K"
    return str(vol)


def get_category_for_ticker(ticker: str) -> str:
    """Get the category name for a ticker."""
    for category, tickers in WATCHLIST.items():
        if ticker in tickers:
            return category.replace("_", " ")
    return "Discovery"


def generate_html(stock_data_list, tech_data_list, fund_data_list, news_map, adversarial_list):
    """Generate the full HTML page."""
    
    # Build lookup maps
    tech_map = {t["ticker"]: t for t in tech_data_list if t.get("ticker")}
    fund_map = {f["ticker"]: f for f in fund_data_list if f.get("ticker")}
    adv_map = {a.get("ticker", ""): a for a in adversarial_list}
    
    # Classify stocks by priority
    priority_stocks = []
    watch_stocks = []
    stable_stocks = []
    error_stocks = []
    
    for stock in stock_data_list:
        ticker = stock.get("ticker", "")
        if stock.get("error"):
            error_stocks.append(stock)
            continue
        
        tech = tech_map.get(ticker, {})
        fund = fund_map.get(ticker, {})
        adv = adv_map.get(ticker, {})
        
        # Determine priority
        tech_summary = tech.get("technical_summary", "neutral")
        volume_signal = tech.get("volume_signal", "normal")
        change_pct = stock.get("change_pct", 0)
        has_significant_news = len(news_map.get(ticker, [])) > 0
        red_flags = len(fund.get("flags", {}).get("red", []))
        green_flags = len(fund.get("flags", {}).get("green", []))
        
        is_priority = (
            tech_summary in ("bullish", "bearish") and volume_signal in ("high_volume_spike", "elevated_volume")
        ) or abs(change_pct) > 5 or green_flags > 0 or red_flags > 0
        
        is_watch = (
            tech_summary in ("bullish", "bearish")
            or volume_signal == "elevated_volume"
            or has_significant_news
        )
        
        if is_priority:
            priority_stocks.append(stock)
        elif is_watch:
            watch_stocks.append(stock)
        else:
            stable_stocks.append(stock)
    
    # Sort priority by absolute change
    priority_stocks.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
    
    today = datetime.now().strftime("%B %d, %Y")
    
    # Start building HTML
    html_parts = []
    
    # --- HEAD ---
    html_parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock Brief — {today}</title>
<style>
  :root {{
    --bg: #0d1117;
    --card-bg: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --green: #00d09c;
    --red: #ff5252;
    --yellow: #ffb74d;
    --blue: #58a6ff;
    --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.5; padding: 12px; max-width: 100%; }}
  .header {{ text-align: center; padding: 16px 0; border-bottom: 1px solid var(--border); margin-bottom: 16px; }}
  .header h1 {{ font-size: 1.5rem; font-weight: 600; }}
  .header .date {{ color: var(--text-dim); font-size: 0.9rem; margin-top: 4px; }}
  .summary {{ display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }}
  .summary-pill {{ padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 500; border: 1px solid var(--border); }}
  .pill-priority {{ background: rgba(255,82,82,0.15); border-color: var(--red); color: var(--red); }}
  .pill-watch {{ background: rgba(255,183,77,0.15); border-color: var(--yellow); color: var(--yellow); }}
  .pill-stable {{ background: rgba(0,208,156,0.15); border-color: var(--green); color: var(--green); }}
  .pill-new {{ background: rgba(88,166,255,0.15); border-color: var(--blue); color: var(--blue); }}
  .section {{ margin-bottom: 24px; }}
  .section-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
  .stock-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 10px; }}
  .stock-header {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
  .stock-name {{ font-size: 1rem; font-weight: 600; }}
  .stock-ticker {{ color: var(--text-dim); font-size: 0.85rem; }}
  .stock-price {{ font-size: 1.1rem; font-weight: 600; }}
  .price-change {{ font-size: 0.85rem; font-weight: 500; }}
  .positive {{ color: var(--green); }}
  .negative {{ color: var(--red); }}
  .stock-body {{ display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 10px; }}
  @media (min-width: 640px) {{ .stock-body {{ grid-template-columns: 1fr 1fr; }} }}
  .indicators {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .indicator {{ padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid var(--border); }}
  .ind-bullish {{ color: var(--green); border-color: rgba(0,208,156,0.3); }}
  .ind-bearish {{ color: var(--red); border-color: rgba(255,82,82,0.3); }}
  .ind-neutral {{ color: var(--text-dim); }}
  .ind-warning {{ color: var(--yellow); border-color: rgba(255,183,77,0.3); }}
  .bull-bear-grid {{ display: grid; grid-template-columns: 1fr; gap: 8px; }}
  @media (min-width: 640px) {{ .bull-bear-grid {{ grid-template-columns: 1fr 1fr; }} }}
  .case-box {{ padding: 10px; border-radius: 8px; border: 1px solid var(--border); }}
  .case-bull {{ background: rgba(0,208,156,0.05); border-color: rgba(0,208,156,0.2); }}
  .case-bear {{ background: rgba(255,82,82,0.05); border-color: rgba(255,82,82,0.2); }}
  .case-title {{ font-weight: 600; font-size: 0.85rem; margin-bottom: 6px; display: flex; justify-content: space-between; }}
  .case-arg {{ font-size: 0.8rem; margin-bottom: 6px; }}
  .case-arg-title {{ font-weight: 500; color: var(--text); }}
  .case-arg-detail {{ color: var(--text-dim); margin-top: 2px; }}
  .case-arg-source {{ font-size: 0.7rem; color: var(--blue); margin-top: 2px; }}
  .news-item {{ font-size: 0.8rem; margin-bottom: 4px; }}
  .news-item a {{ color: var(--blue); text-decoration: none; }}
  .news-item a:hover {{ text-decoration: underline; }}
  .flags {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }}
  .flag {{ padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; }}
  .flag-red {{ background: rgba(255,82,82,0.15); color: var(--red); }}
  .flag-green {{ background: rgba(0,208,156,0.15); color: var(--green); }}
  .verdict {{ font-size: 0.85rem; font-weight: 500; padding: 6px 0; border-top: 1px solid var(--border); margin-top: 8px; }}
  .penny-badge {{ background: rgba(255,82,82,0.2); color: var(--red); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
  .sparkline {{ display: inline-block; vertical-align: middle; margin-left: 8px; }}
  .category-tag {{ font-size: 0.7rem; color: var(--purple); padding: 2px 6px; border-radius: 4px; background: rgba(188,140,255,0.1); }}
  .footer {{ text-align: center; color: var(--text-dim); font-size: 0.75rem; padding: 20px 0; border-top: 1px solid var(--border); margin-top: 20px; }}
  .compact-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 6px; }}
  .compact-item {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; font-size: 0.75rem; }}
  .compact-item .ticker {{ font-weight: 600; }}
  details summary {{ cursor: pointer; color: var(--text-dim); font-size: 0.85rem; padding: 8px 0; }}
  details[open] summary {{ color: var(--text); }}
</style>
</head>
<body>

<div class="header">
  <h1>📊 Daily Stock Brief</h1>
  <div class="date">{today}</div>
</div>

<div class="summary">
  <span class="summary-pill pill-priority">🔴 Priority: {len(priority_stocks)}</span>
  <span class="summary-pill pill-watch">🟡 Watch: {len(watch_stocks)}</span>
  <span class="summary-pill pill-stable">🟢 Stable: {len(stable_stocks)}</span>
  <span class="summary-pill" style="background:rgba(139,148,158,0.1);border-color:var(--text-dim);color:var(--text-dim);">❌ Errors: {len(error_stocks)}</span>
</div>
''')

    # --- PRIORITY STOCKS ---
    if priority_stocks:
        html_parts.append('<div class="section">')
        html_parts.append('<div class="section-title">🔴 Priority — Significant Signals</div>')
        
        for stock in priority_stocks:
            html_parts.append(render_stock_card(stock, tech_map, fund_map, adv_map, news_map, full=True))
        
        html_parts.append('</div>')
    
    # --- WATCH STOCKS ---
    if watch_stocks:
        html_parts.append('<div class="section">')
        html_parts.append('<div class="section-title">🟡 Watch — Minor Signals</div>')
        
        for stock in watch_stocks:
            html_parts.append(render_stock_card(stock, tech_map, fund_map, adv_map, news_map, full=True))
        
        html_parts.append('</div>')
    
    # --- STABLE STOCKS (compact) ---
    if stable_stocks:
        html_parts.append('<div class="section">')
        html_parts.append(f'<details><summary>🟢 Stable — {len(stable_stocks)} stocks (no significant signals)</summary>')
        html_parts.append('<div class="compact-list">')
        
        for stock in stable_stocks:
            ticker = stock.get("ticker", "?")
            price = stock.get("current_price", "N/A")
            change = stock.get("change_pct", 0)
            change_class = "positive" if change >= 0 else "negative"
            sparkline = generate_sparkline(stock.get("sparkline", []))
            
            html_parts.append(f'''<div class="compact-item">
  <span class="ticker">{ticker}</span> <span class="category-tag">{get_category_for_ticker(ticker)}</span><br>
  ${price} <span class="{change_class}">{change:+.1f}%</span>
  <span class="sparkline">{sparkline}</span>
</div>''')
        
        html_parts.append('</div></details></div>')
    
    # --- ERRORS ---
    if error_stocks:
        html_parts.append('<div class="section">')
        html_parts.append(f'<details><summary>❌ Errors — {len(error_stocks)} stocks failed</summary>')
        for stock in error_stocks:
            html_parts.append(f'<div class="compact-item"><span class="ticker">{stock.get("ticker","?")}</span> — {stock.get("error","unknown")[:60]}</div>')
        html_parts.append('</details></div>')
    
    # --- FOOTER ---
    gen_time = datetime.now().strftime("%H:%M:%S")
    html_parts.append(f'''
<div class="footer">
  Generated at {gen_time} by Hermes Agent · DeepSeek V4 Flash · Data via yfinance<br>
  ⚠️ This is not financial advice. All data may be delayed 15-20 min. Do your own research.
</div>

</body>
</html>''')
    
    return "\n".join(html_parts)


def render_stock_card(stock, tech_map, fund_map, adv_map, news_map, full=True) -> str:
    """Render a single stock card."""
    ticker = stock.get("ticker", "?")
    name = stock.get("company_name", stock.get("long_name", ticker))
    long_name = stock.get("long_name", name)
    price = stock.get("current_price", "N/A")
    change = stock.get("change_pct", 0)
    change_class = "positive" if change >= 0 else "negative"
    is_penny = stock.get("is_penny_stock", False)
    category = get_category_for_ticker(ticker)
    sparkline = generate_sparkline(stock.get("sparkline", []))
    
    tech = tech_map.get(ticker, {})
    fund = fund_map.get(ticker, {})
    adv = adv_map.get(ticker, {})
    news = news_map.get(ticker, [])
    
    # Indicators
    ind_parts = []
    if tech and not tech.get("error"):
        rsi = tech.get("rsi")
        rsi_sig = tech.get("rsi_signal", "neutral")
        if rsi:
            ind_class = "ind-bullish" if rsi_sig == "oversold" else "ind-bearish" if rsi_sig == "overbought" else "ind-neutral"
            ind_parts.append(f'<span class="indicator {ind_class}">RSI {rsi} ({rsi_sig})</span>')
        
        macd_sig = tech.get("macd_signal_type", "unknown")
        if macd_sig != "unknown":
            ind_class = "ind-bullish" if macd_sig == "bullish" else "ind-bearish" if macd_sig == "bearish" else "ind-neutral"
            ind_parts.append(f'<span class="indicator {ind_class}">MACD {macd_sig}</span>')
        
        vol_sig = tech.get("volume_signal", "normal")
        if vol_sig != "normal":
            ind_class = "ind-warning" if vol_sig in ("high_volume_spike", "elevated_volume") else "ind-neutral"
            ind_parts.append(f'<span class="indicator {ind_class}">Vol {vol_sig.replace("_"," ")}</span>')
        
        tech_sum = tech.get("technical_summary", "neutral")
        if tech_sum != "neutral":
            ind_class = "ind-bullish" if tech_sum == "bullish" else "ind-bearish" if tech_sum == "bearish" else "ind-neutral"
            ind_parts.append(f'<span class="indicator {ind_class}">Overall: {tech_sum}</span>')
    
    # Flags
    flag_parts = []
    if fund and not fund.get("error"):
        for g in fund.get("flags", {}).get("green", []):
            flag_parts.append(f'<span class="flag flag-green">✅ {g}</span>')
        for r in fund.get("flags", {}).get("red", []):
            flag_parts.append(f'<span class="flag flag-red">{r}</span>')
    
    # Bull/Bear
    bull_html = ""
    bear_html = ""
    verdict_html = ""
    
    if adv and not adv.get("error"):
        bull = adv.get("bull_case", {})
        bear = adv.get("bear_case", {})
        bull_conf = bull.get("confidence", "?")
        bear_conf = bear.get("confidence", "?")
        
        bull_args = ""
        for arg in bull.get("arguments", []):
            bull_args += f'''<div class="case-arg">
  <div class="case-arg-title">📈 {arg.get("title","")}</div>
  <div class="case-arg-detail">{arg.get("detail","")}</div>
  <div class="case-arg-source">📊 {arg.get("data_source","")}</div>
</div>'''
        
        bear_args = ""
        for arg in bear.get("arguments", []):
            bear_args += f'''<div class="case-arg">
  <div class="case-arg-title">📉 {arg.get("title","")}</div>
  <div class="case-arg-detail">{arg.get("detail","")}</div>
  <div class="case-arg-source">📊 {arg.get("data_source","")}</div>
</div>'''
        
        bull_html = f'''<div class="case-box case-bull">
  <div class="case-title"><span>🐂 BULL CASE</span><span>Confidence: {bull_conf}/10</span></div>
  {bull_args}
</div>'''
        
        bear_html = f'''<div class="case-box case-bear">
  <div class="case-title"><span>🐻 BEAR CASE</span><span>Confidence: {bear_conf}/10</span></div>
  {bear_args}
</div>'''
        
        verdict = adv.get("verdict", "")
        key_risk = adv.get("key_risk", "")
        key_cat = adv.get("key_catalyst", "")
        if verdict:
            verdict_html = f'''<div class="verdict">
  <strong>Verdict:</strong> {verdict}<br>
  <strong>Key Risk:</strong> <span class="negative">{key_risk}</span><br>
  <strong>Key Catalyst:</strong> <span class="positive">{key_cat}</span>
</div>'''
    
    # News
    news_html = ""
    if news:
        news_items = ""
        for n in news[:3]:
            if n.get("title"):
                url = n.get("url", "")
                news_items += f'<div class="news-item">📰 <a href="{url}" target="_blank" rel="noopener">{n["title"]}</a> — {n.get("publisher","")}</div>\n'
        if news_items:
            news_html = f'<div class="case-box" style="margin-top:8px;"><div class="case-title">📰 Recent News</div>{news_items}</div>'
    
    # Quarterly data
    quarter_html = ""
    quarters = stock.get("quarters", [])
    if quarters:
        q_items = ""
        for q in quarters[:4]:
            rev = q.get("revenue")
            rev_str = f"${rev/1e6:.1f}M" if rev and rev > 0 else "N/A"
            ni = q.get("net_income")
            ni_str = f"${ni/1e6:.1f}M" if ni and ni != 0 else "N/A"
            q_items += f'<span class="indicator ind-neutral">{q.get("quarter","?")}: Rev {rev_str}, NI {ni_str}</span>'
        quarter_html = f'<div class="indicators" style="margin-top:6px;">{q_items}</div>'
    
    # Market cap & volume
    mcap = format_market_cap(stock.get("market_cap"))
    vol = format_volume(stock.get("volume"))
    avg_vol = format_volume(stock.get("avg_volume"))
    vol_ratio = stock.get("volume_ratio", 1.0)
    
    penny_badge = '<span class="penny-badge">⚠️ PENNY</span>' if is_penny else ''
    
    card = f'''<div class="stock-card">
  <div class="stock-header">
    <div>
      <span class="stock-name">{name}</span>
      <span class="stock-ticker">{ticker}</span>
      <span class="category-tag">{category}</span>
      {penny_badge}
      <span class="sparkline">{sparkline}</span>
    </div>
    <div style="text-align:right;">
      <div class="stock-price">${price}</div>
      <div class="price-change {change_class}">{change:+.1f}%</div>
    </div>
  </div>
  
  <div class="indicators" style="margin-top:8px;">
    <span class="indicator ind-neutral">Cap {mcap}</span>
    <span class="indicator ind-neutral">Vol {vol} ({vol_ratio}x avg)</span>
    {''.join(ind_parts)}
  </div>
  
  {quarter_html}
  
  {''.join(flag_parts) and f'<div class="flags">{"".join(flag_parts)}</div>' if flag_parts else ''}
  
  <div class="stock-body">
    <div class="bull-bear-grid">
      {bull_html}
      {bear_html}
    </div>
  </div>
  
  {news_html}
  {verdict_html}
</div>'''
    
    return card


if __name__ == "__main__":
    import glob
    
    # Load all data files
    stock_files = sorted(glob.glob(os.path.join(DATA_DIR, "stocks_*.json")))
    if not stock_files:
        print("No data files found. Run data_collector first.")
        exit(1)
    
    with open(stock_files[-1]) as f:
        stock_data = json.load(f)
    
    tech_file = os.path.join(DATA_DIR, "technical_analysis.json")
    fund_file = os.path.join(DATA_DIR, "fundamental_analysis.json")
    news_files = sorted(glob.glob(os.path.join(DATA_DIR, "news_*.json")))
    adv_file = os.path.join(DATA_DIR, "adversarial_analysis.json")
    
    tech_data = []
    fund_data = []
    news_data = {}
    adv_data = []
    
    if os.path.exists(tech_file):
        with open(tech_file) as f:
            tech_data = json.load(f)
    if os.path.exists(fund_file):
        with open(fund_file) as f:
            fund_data = json.load(f)
    if news_files:
        with open(news_files[-1]) as f:
            news_data = json.load(f)
    if os.path.exists(adv_file):
        with open(adv_file) as f:
            adv_data = json.load(f)
    
    print(f"Generating HTML from {len(stock_data)} stocks...")
    html = generate_html(stock_data, tech_data, fund_data, news_data, adv_data)
    
    os.makedirs(os.path.dirname(HTML_OUTPUT), exist_ok=True)
    with open(HTML_OUTPUT, 'w') as f:
        f.write(html)
    print(f"HTML written to {HTML_OUTPUT}")
