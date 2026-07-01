"""
Stock Advisory System — Configuration
Watchlist sourced from Obsidian AI Stocks Hub
"""

# All tickers from AI Stocks Hub organized by category
WATCHLIST = {
    "Semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "MRVL", "QCOM", "TSM", "ASML", "AMAT", "LRCX", "ARM"],
    "Memory_Storage": ["MU", "STX", "WDC", "PSTG", "NET"],
    "Networking_Interconnects": ["ANET", "CSCO", "CIEN", "LITE", "COHR", "JNPR"],
    "Datacenter_Infrastructure": ["EQIX", "DLR", "VRT", "MOD", "SMCI", "DELL", "HPE"],
    "Energy_Power": ["CEG", "VST", "TLN", "GEV", "SMR", "OKLO", "BWXT"],
    "Rare_Earth_Materials": ["MP", "ALB", "SQM", "LAC", "UUUU", "PLL"],
    "Space_Satellites": ["RKLB", "ASTS", "RDW", "LUNR", "PL", "BKSY"],
    "AI_Software_Platforms": ["PLTR", "SNOW", "MDB", "DDOG", "NOW", "CRM"],
    "Quantum_Computing": ["IONQ", "RGTI", "QBTS", "QUBT"],
    "Industrial_Automation": ["TER", "PATH", "SYM", "ISRG"],
}

# Flatten for easy iteration
ALL_TICKERS = []
for tickers in WATCHLIST.values():
    ALL_TICKERS.extend(tickers)

# Penny stock threshold ($5)
PENNY_STOCK_THRESHOLD = 5.0

# DeepSeek API config
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek V4 Flash
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

# Rate limiting (ms between yfinance calls)
YFINANCE_DELAY_MS = 200

# Output paths
DATA_DIR = "data"
HTML_OUTPUT = "docs/index.html"

# GitHub Pages config
GITHUB_REPO = "Moncacademy/stock-advisory"
GITHUB_PAGES_URL = "https://moncacademy.github.io/stock-advisory/"
