"""
Main pipeline orchestrator — runs all stages in sequence:
1. Data collection (yfinance)
2. Technical analysis
3. Fundamental analysis
4. News collection
5. Adversarial analysis (DeepSeek V4 Flash)
6. HTML generation
7. Git deploy to GitHub Pages
"""
import sys
import os
import json
import glob
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import ALL_TICKERS, DATA_DIR, HTML_OUTPUT, GITHUB_REPO
from src.data_collector import fetch_all_stocks, save_data
from src.technical_engine import analyze_all as tech_analyze_all
from src.fundamental_engine import analyze_all as fund_analyze_all
from src.news_collector import fetch_all_news
from src.adversarial_analyst import analyze_all_stocks as adversarial_analyze_all
from src.html_generator import generate_html


def run_pipeline(tickers: list = None, skip_deepseek: bool = False):
    """Run the full pipeline."""
    start_time = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"  STOCK ADVISORY PIPELINE — {today}")
    print("=" * 60)
    print(f"  Tickers: {len(tickers or ALL_TICKERS)}")
    print(f"  DeepSeek: {'SKIPPED' if skip_deepseek else 'ENABLED'}")
    print("=" * 60 + "\n")
    
    # --- STAGE 1: Data Collection ---
    print("📊 STAGE 1: Data Collection (yfinance)")
    print("-" * 40)
    stock_data = fetch_all_stocks(tickers)
    data_file = save_data(stock_data)
    
    success_count = sum(1 for d in stock_data if not d.get("error"))
    print(f"✅ {success_count}/{len(stock_data)} stocks fetched\n")
    
    # --- STAGE 2: Technical Analysis ---
    print("📈 STAGE 2: Technical Analysis (pandas-ta)")
    print("-" * 40)
    tech_data = tech_analyze_all(stock_data)
    
    tech_file = os.path.join(DATA_DIR, "technical_analysis.json")
    with open(tech_file, 'w') as f:
        json.dump(tech_data, f, indent=2, default=str)
    
    bullish = sum(1 for i in tech_data if i.get("technical_summary") == "bullish")
    bearish = sum(1 for i in tech_data if i.get("technical_summary") == "bearish")
    neutral = sum(1 for i in tech_data if i.get("technical_summary") == "neutral")
    print(f"✅ Bullish: {bullish} | Bearish: {bearish} | Neutral: {neutral}\n")
    
    # --- STAGE 3: Fundamental Analysis ---
    print("💰 STAGE 3: Fundamental Analysis")
    print("-" * 40)
    fund_data = fund_analyze_all(stock_data)
    
    fund_file = os.path.join(DATA_DIR, "fundamental_analysis.json")
    with open(fund_file, 'w') as f:
        json.dump(fund_data, f, indent=2, default=str)
    
    scored = [s for s in fund_data if s.get("overall_score")]
    avg_score = sum(s["overall_score"] for s in scored) / len(scored) if scored else 0
    print(f"✅ Avg fundamental score: {avg_score:.1f}/10\n")
    
    # --- STAGE 4: News Collection ---
    print("📰 STAGE 4: News Collection")
    print("-" * 40)
    news_data = fetch_all_news(tickers, max_per_stock=3)
    
    news_file = os.path.join(DATA_DIR, f"news_{today}.json")
    with open(news_file, 'w') as f:
        json.dump(news_data, f, indent=2, default=str)
    
    total_articles = sum(len(v) for v in news_data.values())
    print(f"✅ {total_articles} articles collected\n")
    
    # --- STAGE 5: Adversarial Analysis ---
    adv_data = []
    if not skip_deepseek:
        print("⚖️ STAGE 5: Adversarial Analysis (DeepSeek V4 Flash)")
        print("-" * 40)
        adv_data = adversarial_analyze_all(stock_data, tech_data, fund_data, news_data)
        
        adv_file = os.path.join(DATA_DIR, "adversarial_analysis.json")
        with open(adv_file, 'w') as f:
            json.dump(adv_data, f, indent=2, default=str)
        
        success = sum(1 for a in adv_data if not a.get("error"))
        print(f"✅ {success}/{len(adv_data)} stocks analyzed\n")
    else:
        print("⏭️ STAGE 5: Skipped (DeepSeek)\n")
    
    # --- STAGE 6: HTML Generation ---
    print("🎨 STAGE 6: HTML Generation")
    print("-" * 40)
    html = generate_html(stock_data, tech_data, fund_data, news_data, adv_data)
    
    os.makedirs(os.path.dirname(HTML_OUTPUT), exist_ok=True)
    with open(HTML_OUTPUT, 'w') as f:
        f.write(html)
    print(f"✅ HTML written to {HTML_OUTPUT}\n")
    
    # --- STAGE 7: Deploy ---
    print("🚀 STAGE 7: Deploy to GitHub Pages")
    print("-" * 40)
    deploy_to_github()
    
    # --- Summary ---
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  PIPELINE COMPLETE — {elapsed:.0f}s")
    print(f"  Stocks: {len(stock_data)} | Articles: {total_articles} | Analysis: {len(adv_data)}")
    print(f"  Live at: https://moncacademy.github.io/stock-advisory/")
    print("=" * 60)


def deploy_to_github():
    """Git commit and push to GitHub Pages."""
    import subprocess
    
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Stage files
        subprocess.run(["git", "add", "-A"], cwd=project_dir, check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=project_dir,
            capture_output=True
        )
        
        if result.returncode == 0:
            print("No changes to commit.")
            return
        
        # Commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"Daily brief — {timestamp}"],
            cwd=project_dir,
            check=True
        )
        
        # Push
        subprocess.run(["git", "push"], cwd=project_dir, check=True)
        print("✅ Pushed to GitHub")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")
    except Exception as e:
        print(f"❌ Deploy error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Stock Advisory Pipeline")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to analyze")
    parser.add_argument("--skip-deepseek", action="store_true", help="Skip DeepSeek adversarial analysis")
    args = parser.parse_args()
    
    run_pipeline(tickers=args.tickers, skip_deepseek=args.skip_deepseek)
