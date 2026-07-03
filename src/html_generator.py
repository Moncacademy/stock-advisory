"""
HTML Generator — produces a responsive, dark-mode daily brief HTML page.
Outputs to docs/index.html for GitHub Pages.
"""
import json
import os
from datetime import datetime
from src.config import DATA_DIR, HTML_OUTPUT, WATCHLIST, CATEGORY_COLORS

ACCENT_HEX = {
    "blue": "#60a5fa", "cyan": "#22d3ee", "teal": "#2dd4bf",
    "amber": "#fbbf24", "orange": "#fb923c", "green": "#34d399",
    "purple": "#a78bfa", "indigo": "#818cf8", "violet": "#c084fc",
    "rose": "#fb7185",
}


def get_category_raw(ticker: str) -> str:
    """Get the raw category key (with underscores) for a ticker."""
    for category, tickers in WATCHLIST.items():
        if ticker in tickers:
            return category
    return "Discovery"


def get_accent_color(ticker: str) -> str:
    """Get the accent color name for a ticker's category."""
    return CATEGORY_COLORS.get(get_category_raw(ticker), "blue")


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
<meta name="color-scheme" content="dark light">
<title>Stock Brief — {today}</title>
<script>if(localStorage.getItem('theme')==='light')document.documentElement.classList.add('light');</script>
<link rel="stylesheet" href="style.css">
</head>
<body>

<div class="orb-field">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
  <div class="orb orb-4"></div>
</div>

<button class="theme-toggle" id="theme-toggle" title="Wissel licht/donker">☀️</button>

<div class="header">
  <h1>📊 Daily Stock Brief</h1>
  <div class="date">{today}</div>
</div>

<div class="summary">
  <span class="summary-pill pill-priority" data-filter="priority">🔴 Priority: {len(priority_stocks)}</span>
  <span class="summary-pill pill-watch" data-filter="watch">🟡 Watch: {len(watch_stocks)}</span>
  <span class="summary-pill pill-stable" data-filter="stable">🟢 Stable: {len(stable_stocks)}</span>
  <span class="summary-pill" style="background:rgba(139,148,158,0.1);border-color:var(--text-dim);color:var(--text-dim);" data-filter="errors">❌ Errors: {len(error_stocks)}</span>
</div>
<div class="controls">
  <button class="ctrl-btn" id="expand-all">▶ Expand All</button>
  <button class="ctrl-btn" id="collapse-all">▼ Collapse All</button>
</div>
''')

    # --- PRIORITY STOCKS ---
    if priority_stocks:
        html_parts.append('<div class="section" data-section="priority">')
        html_parts.append('<div class="section-title">🔴 Priority — Significant Signals</div>')
        html_parts.append('<div class="stock-grid">')
        for stock in priority_stocks:
            html_parts.append(render_stock_card(stock, tech_map, fund_map, adv_map, news_map, full=True))
        
        html_parts.append('</div>')  # close stock-grid
        html_parts.append('</div>')
    
    # --- WATCH STOCKS ---
    if watch_stocks:
        html_parts.append('<div class="section" data-section="watch">')
        html_parts.append('<div class="section-title">🟡 Watch — Minor Signals</div>')
        html_parts.append('<div class="stock-grid">')
        for stock in watch_stocks:
            html_parts.append(render_stock_card(stock, tech_map, fund_map, adv_map, news_map, full=True))
        
        html_parts.append('</div>')  # close stock-grid
        html_parts.append('</div>')
    
    # --- STABLE STOCKS (compact) ---
    if stable_stocks:
        html_parts.append('<div class="section" data-section="stable">')
        html_parts.append(f'<details><summary>🟢 Stable — {len(stable_stocks)} stocks (no significant signals)</summary>')
        html_parts.append('<div class="compact-list">')
        
        for stock in stable_stocks:
            ticker = stock.get("ticker", "?")
            price = stock.get("current_price", "N/A")
            change = stock.get("change_pct", 0)
            change_class = "positive" if change >= 0 else "negative"
            sparkline = generate_sparkline(stock.get("sparkline", []))
            
            html_parts.append(f'''<div class="compact-item">
  <span class="ticker">{ticker}</span> <span class="sector-tag-small">{stock.get("sector","?")}</span><br>
  ${price} <span class="{change_class}">{change:+.1f}%</span>
  <span class="sparkline">{sparkline}</span>
</div>''')
        
        html_parts.append('</div></details></div>')
    
    # --- ERRORS ---
    if error_stocks:
        html_parts.append('<div class="section" data-section="errors">')
        html_parts.append(f'<details><summary>❌ Errors — {len(error_stocks)} stocks failed</summary>')
        for stock in error_stocks:
            html_parts.append(f'<div class="compact-item"><span class="ticker">{stock.get("ticker","?")}</span> — {stock.get("error","unknown")[:60]}</div>')
        html_parts.append('</details></div>')
    
    # --- JAVASCRIPT ---
    html_parts.append('''<script>
(function() {
  // Theme restore from localStorage
  if (localStorage.getItem('theme') === 'light') document.documentElement.classList.add('light');
  // Pill filtering
  var pills = document.querySelectorAll('.summary-pill[data-filter]');
  pills.forEach(function(pill) {
    pill.addEventListener('click', function() {
      var filter = this.dataset.filter;
      var wasActive = this.classList.contains('active');
      pills.forEach(function(p) { p.classList.remove('active'); });
      var sections = document.querySelectorAll('.section[data-section]');
      if (wasActive) {
        sections.forEach(function(s) { s.style.display = ''; });
      } else {
        this.classList.add('active');
        sections.forEach(function(s) {
          s.style.display = s.dataset.section === filter ? '' : 'none';
        });
      }
    });
  });

  // Stock card toggle
  document.querySelectorAll('.stock-header').forEach(function(header) {
    header.addEventListener('click', function() {
      this.closest('.stock-card').classList.toggle('collapsed');
    });
  });

  // Case-arg source toggle
  document.querySelectorAll('.case-arg-source').forEach(function(src) {
    src.addEventListener('click', function(e) {
      e.stopPropagation();
      this.closest('.case-arg').classList.toggle('arg-collapsed');
    });
  });

  // Expand all
  var expandBtn = document.getElementById('expand-all');
  if (expandBtn) {
    expandBtn.addEventListener('click', function() {
      document.querySelectorAll('.stock-card').forEach(function(c) { c.classList.remove('collapsed'); });
    });
  }

  // Collapse all
  var collapseBtn = document.getElementById('collapse-all');
  if (collapseBtn) {
    collapseBtn.addEventListener('click', function() {
      document.querySelectorAll('.stock-card').forEach(function(c) { c.classList.add('collapsed'); });
    });
  }
  // Theme toggle
  var themeBtn = document.getElementById('theme-toggle');
  function applyTheme() {
    var isLight = document.documentElement.classList.contains('light');
    themeBtn.textContent = isLight ? '🌙' : '☀️';
  }
  if (themeBtn) {
    applyTheme();
    themeBtn.addEventListener('click', function() {
      document.documentElement.classList.toggle('light');
      var isLight = document.documentElement.classList.contains('light');
      localStorage.setItem('theme', isLight ? 'light' : 'dark');
      applyTheme();
    });
  }
  // Dopamine pulse on big movers (>= 5%)
  document.querySelectorAll('.price-change').forEach(function(el) {
    var pct = parseFloat(el.textContent.replace(/[+%]/g, ''));
    if (Math.abs(pct) >= 5) el.classList.add('pulse');
  });
})();
</script>''')

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
    accent = get_accent_color(ticker)
    accent_hex = ACCENT_HEX.get(accent, "#60a5fa")
    sector = stock.get("sector", "Unknown")
    industry = stock.get("industry", "")
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
    
    card = f'''<div class="stock-card collapsed" data-accent="{accent}" style="--card-accent: {accent_hex}">
  <div class="stock-header">
    <div>
      <span class="toggle-arrow">▶</span>
      <span class="stock-name">{name}</span>
      <span class="stock-ticker">{ticker}</span><br>
      <span class="sector-tag">{sector}</span>
      <span class="category-tag">{category}</span>
      {penny_badge}
      <span class="sparkline">{sparkline}</span>
    </div>
    <div style="text-align:right;">
      <div class="stock-price">${price}</div>
      <div class="price-change {change_class}">{change:+.1f}%</div>
    </div>
  </div>
  
  <div class="stock-details">
    <div class="indicators" style="margin-top:8px;">
      <span class="indicator ind-neutral">Cap {mcap}</span>
      <span class="indicator ind-neutral">Vol {vol} ({vol_ratio}x avg)</span>
      {''.join(ind_parts)}
    </div>
    
    {quarter_html}
    
    {''.join(flag_parts) and f'<div class="flags">{" ".join(flag_parts)}</div>' if flag_parts else ''}
    
    <div class="stock-body">
      <div class="bull-bear-grid">
        {bull_html}
        {bear_html}
      </div>
    </div>
    
    {news_html}
    {verdict_html}
  </div>
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
