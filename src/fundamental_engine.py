"""
Fundamental Analysis Engine — evaluates financial health from yfinance fundamentals
and quarterly earnings data.
"""
import json
import os
from src.config import DATA_DIR


def compute_fundamental_score(stock_data: dict) -> dict:
    """Compute fundamental health scorecard from stock data."""
    if stock_data.get("error"):
        return {"ticker": stock_data["ticker"], "error": stock_data["error"]}
    
    ticker = stock_data["ticker"]
    scorecard = {
        "ticker": ticker,
        "error": None,
        "grades": {},
        "scores": {},
        "flags": {"green": [], "red": []},
    }
    
    # --- Valuation ---
    pe = stock_data.get("pe_ratio")
    forward_pe = stock_data.get("forward_pe")
    pb = stock_data.get("pb_ratio")
    
    if pe is not None and pe > 0:
        if pe < 15:
            scorecard["grades"]["valuation_pe"] = "A"
            scorecard["scores"]["valuation_pe"] = 5
        elif pe < 25:
            scorecard["grades"]["valuation_pe"] = "B"
            scorecard["scores"]["valuation_pe"] = 4
        elif pe < 40:
            scorecard["grades"]["valuation_pe"] = "C"
            scorecard["scores"]["valuation_pe"] = 3
        elif pe < 60:
            scorecard["grades"]["valuation_pe"] = "D"
            scorecard["scores"]["valuation_pe"] = 2
        else:
            scorecard["grades"]["valuation_pe"] = "F"
            scorecard["scores"]["valuation_pe"] = 1
    elif forward_pe is not None and forward_pe > 0:
        # Use forward PE as fallback
        if forward_pe < 15:
            scorecard["grades"]["valuation_pe"] = "B (forward)"
            scorecard["scores"]["valuation_pe"] = 4
        elif forward_pe < 30:
            scorecard["grades"]["valuation_pe"] = "C (forward)"
            scorecard["scores"]["valuation_pe"] = 3
        else:
            scorecard["grades"]["valuation_pe"] = "D (forward)"
            scorecard["scores"]["valuation_pe"] = 2
    else:
        # No PE (common for growth/loss-making companies)
        scorecard["grades"]["valuation_pe"] = "N/A"
        scorecard["scores"]["valuation_pe"] = None
    
    # --- Growth ---
    revenue_growth = stock_data.get("revenue_growth")
    if revenue_growth is not None:
        if revenue_growth > 0.30:
            scorecard["grades"]["growth"] = "A"
            scorecard["scores"]["growth"] = 5
            scorecard["flags"]["green"].append(f"Revenue growth {revenue_growth*100:.0f}% YoY")
        elif revenue_growth > 0.10:
            scorecard["grades"]["growth"] = "B"
            scorecard["scores"]["growth"] = 4
        elif revenue_growth > 0:
            scorecard["grades"]["growth"] = "C"
            scorecard["scores"]["growth"] = 3
        elif revenue_growth > -0.10:
            scorecard["grades"]["growth"] = "D"
            scorecard["scores"]["growth"] = 2
        else:
            scorecard["grades"]["growth"] = "F"
            scorecard["scores"]["growth"] = 1
            scorecard["flags"]["red"].append(f"Revenue declining {revenue_growth*100:.0f}% YoY")
    else:
        scorecard["grades"]["growth"] = "N/A"
        scorecard["scores"]["growth"] = None
    
    # --- Profitability ---
    profit_margins = stock_data.get("profit_margins")
    if profit_margins is not None:
        if profit_margins > 0.20:
            scorecard["grades"]["profitability"] = "A"
            scorecard["scores"]["profitability"] = 5
            scorecard["flags"]["green"].append(f"Profit margin {profit_margins*100:.0f}%")
        elif profit_margins > 0.10:
            scorecard["grades"]["profitability"] = "B"
            scorecard["scores"]["profitability"] = 4
        elif profit_margins > 0:
            scorecard["grades"]["profitability"] = "C"
            scorecard["scores"]["profitability"] = 3
        else:
            scorecard["grades"]["profitability"] = "D"
            scorecard["scores"]["profitability"] = 2
            if profit_margins < -0.30:
                scorecard["flags"]["red"].append(f"Negative margin {profit_margins*100:.0f}%")
    else:
        scorecard["grades"]["profitability"] = "N/A"
        scorecard["scores"]["profitability"] = None
    
    # --- Financial Health (Debt) ---
    debt_to_equity = stock_data.get("debt_to_equity")
    if debt_to_equity is not None:
        # yfinance returns as percentage sometimes; normalize
        dte = debt_to_equity / 100 if debt_to_equity > 100 else debt_to_equity
        if dte < 0.5:
            scorecard["grades"]["financial_health"] = "A"
            scorecard["scores"]["financial_health"] = 5
        elif dte < 1.0:
            scorecard["grades"]["financial_health"] = "B"
            scorecard["scores"]["financial_health"] = 4
        elif dte < 2.0:
            scorecard["grades"]["financial_health"] = "C"
            scorecard["scores"]["financial_health"] = 3
        elif dte < 4.0:
            scorecard["grades"]["financial_health"] = "D"
            scorecard["scores"]["financial_health"] = 2
            scorecard["flags"]["red"].append(f"High debt-to-equity {dte:.1f}")
        else:
            scorecard["grades"]["financial_health"] = "F"
            scorecard["scores"]["financial_health"] = 1
            scorecard["flags"]["red"].append(f"Very high debt-to-equity {dte:.1f}")
    else:
        scorecard["grades"]["financial_health"] = "N/A"
        scorecard["scores"]["financial_health"] = None
    
    # --- Liquidity ---
    current_ratio = stock_data.get("current_ratio")
    if current_ratio is not None:
        if current_ratio > 2.0:
            scorecard["grades"]["liquidity"] = "A"
            scorecard["scores"]["liquidity"] = 5
        elif current_ratio > 1.5:
            scorecard["grades"]["liquidity"] = "B"
            scorecard["scores"]["liquidity"] = 4
        elif current_ratio > 1.0:
            scorecard["grades"]["liquidity"] = "C"
            scorecard["scores"]["liquidity"] = 3
        else:
            scorecard["grades"]["liquidity"] = "D"
            scorecard["scores"]["liquidity"] = 2
            scorecard["flags"]["red"].append(f"Low current ratio {current_ratio:.1f}")
    else:
        scorecard["grades"]["liquidity"] = "N/A"
        scorecard["scores"]["liquidity"] = None
    
    # --- Quarterly Revenue Trend ---
    quarters = stock_data.get("quarters", [])
    if len(quarters) >= 2:
        revenues = [q.get("revenue") for q in quarters if q.get("revenue")]
        if len(revenues) >= 2:
            # Compare most recent quarter vs previous
            latest_rev = revenues[0]
            prev_rev = revenues[1]
            if prev_rev and prev_rev > 0:
                qoq_growth = (latest_rev - prev_rev) / prev_rev
                scorecard["quarterly_revenue_qoq"] = round(qoq_growth * 100, 1)
                if qoq_growth > 0.15:
                    scorecard["grades"]["quarterly_trend"] = "A"
                    scorecard["scores"]["quarterly_trend"] = 5
                    scorecard["flags"]["green"].append(f"QoQ revenue +{qoq_growth*100:.0f}%")
                elif qoq_growth > 0:
                    scorecard["grades"]["quarterly_trend"] = "B"
                    scorecard["scores"]["quarterly_trend"] = 4
                elif qoq_growth > -0.10:
                    scorecard["grades"]["quarterly_trend"] = "C"
                    scorecard["scores"]["quarterly_trend"] = 3
                else:
                    scorecard["grades"]["quarterly_trend"] = "D"
                    scorecard["scores"]["quarterly_trend"] = 2
                    scorecard["flags"]["red"].append(f"QoQ revenue {qoq_growth*100:.0f}%")
    
    if "quarterly_trend" not in scorecard["grades"]:
        scorecard["grades"]["quarterly_trend"] = "N/A"
        scorecard["scores"]["quarterly_trend"] = None
    
    # --- Overall fundamental score (1-10) ---
    valid_scores = [s for s in scorecard["scores"].values() if s is not None]
    if valid_scores:
        avg_score = sum(valid_scores) / len(valid_scores)
        scorecard["overall_score"] = round(avg_score * 2, 1)  # Scale to 1-10
    else:
        scorecard["overall_score"] = None
    
    # --- Penny stock flag ---
    if stock_data.get("is_penny_stock"):
        scorecard["flags"]["red"].append("⚠️ PENNY STOCK — extreme risk, potential manipulation")
    
    return scorecard


def analyze_all(stock_data_list: list) -> list:
    """Compute fundamental scores for all stocks."""
    results = []
    for stock in stock_data_list:
        scorecard = compute_fundamental_score(stock)
        results.append(scorecard)
    return results


if __name__ == "__main__":
    import glob
    files = sorted(glob.glob(os.path.join(DATA_DIR, "stocks_*.json")))
    if not files:
        print("No data files found. Run data_collector first.")
        exit(1)
    
    with open(files[-1]) as f:
        stock_data = json.load(f)
    
    print(f"Analyzing fundamentals for {len(stock_data)} stocks...")
    scorecards = analyze_all(stock_data)
    
    out_file = os.path.join(DATA_DIR, "fundamental_analysis.json")
    with open(out_file, 'w') as f:
        json.dump(scorecards, f, indent=2, default=str)
    print(f"Saved to {out_file}")
    
    scored = [s for s in scorecards if s.get("overall_score")]
    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    print(f"\nTop 5 fundamental scores:")
    for s in scored[:5]:
        print(f"  {s['ticker']}: {s['overall_score']}/10 | Green: {len(s['flags']['green'])} | Red: {len(s['flags']['red'])}")
