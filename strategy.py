"""
strategy.py - Momentum strategy: score, screen, hold, go to cash.

Tune the parameters below, then run:  python strategy.py
"""

import time

import numpy as np
import pandas as pd

from prepare import (
    load_data, evaluate_strategy, print_results,
    get_sector, TEST_START, UNIVERSE,
)

# ═══════════════════════════════════════════════════════════════
# TUNABLE PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Momentum lookbacks (trading days) and weights
ROC_PERIODS = [21, 63, 126, 252]      # ~1m, 3m, 6m, 12m
ROC_WEIGHTS = [0.05, 0.15, 0.3, 0.5]  # heavy 12m weight

# Trend filters
MA_FAST = 50          # price must be above this MA
MA_SLOW = 200         # price must be above this MA

# Portfolio
REBALANCE_EVERY = 5   # trading days (weekly)
TOP_K = 15            # max stocks to hold
MIN_STOCKS = 3        # fewer qualifying → 100% cash

# Sector filter
TOP_SECTORS = 3       # pick stocks only from top N sectors by avg momentum

# Momentum threshold
MIN_MOM_SCORE = 0.0   # minimum composite score to qualify

# ═══════════════════════════════════════════════════════════════


def precompute_indicators(data):
    """Compute momentum indicators for every stock. Returns dict of DataFrames."""
    indicators = {}
    for ticker, df in data["stocks"].items():
        close = df["Close"]
        ind = pd.DataFrame(index=df.index)
        ind["close"] = close

        # Rate of change at each lookback
        for p in ROC_PERIODS:
            ind[f"roc_{p}"] = close.pct_change(p)

        # Moving averages
        ind["ma_fast"] = close.rolling(MA_FAST).mean()
        ind["ma_slow"] = close.rolling(MA_SLOW).mean()

        # Composite momentum score (weighted sum of ROCs)
        ind["mom_score"] = sum(
            w * ind[f"roc_{p}"] for w, p in zip(ROC_WEIGHTS, ROC_PERIODS)
        )

        indicators[ticker] = ind

    return indicators


def screen_stocks(indicators, date):
    """
    On a given date, return list of tickers to hold (ranked by momentum).
    Returns empty list if fewer than MIN_STOCKS qualify → cash signal.
    """
    scores = {}

    for ticker, ind in indicators.items():
        if date not in ind.index:
            continue
        row = ind.loc[date]

        # Skip incomplete data
        if row.isna().any():
            continue

        # Trend filter: price above both MAs
        if row["close"] <= row["ma_fast"] or row["close"] <= row["ma_slow"]:
            continue

        # Positive recent momentum (1-month ROC > 0)
        if row[f"roc_{ROC_PERIODS[0]}"] <= 0:
            continue

        # Minimum score
        if row["mom_score"] <= MIN_MOM_SCORE:
            continue

        scores[ticker] = row["mom_score"]

    if not scores:
        return []

    # Sector filter: average momentum per sector, keep top N
    sector_scores = {}
    for ticker, score in scores.items():
        sec = get_sector(ticker)
        sector_scores.setdefault(sec, []).append(score)
    sector_avg = {s: np.mean(v) for s, v in sector_scores.items()}
    top_sectors = set(
        sorted(sector_avg, key=sector_avg.get, reverse=True)[:TOP_SECTORS]
    )

    filtered = {t: s for t, s in scores.items() if get_sector(t) in top_sectors}

    if len(filtered) < MIN_STOCKS:
        return []

    # Rank by momentum score, pick top K
    ranked = sorted(filtered, key=filtered.get, reverse=True)
    return ranked[:TOP_K]


def run_strategy(data, indicators):
    """Walk through test period, screen weekly, build holdings schedule."""
    bench_dates = data["benchmark_returns"].index
    test_start = pd.Timestamp(TEST_START)
    test_dates = sorted([d for d in bench_dates if d >= test_start])

    holdings_schedule = []
    for i, date in enumerate(test_dates):
        if i % REBALANCE_EVERY == 0:
            picks = screen_stocks(indicators, date)
            holdings_schedule.append((date, picks))

    return holdings_schedule


def main():
    t0 = time.time()

    print("Loading data...")
    data = load_data()

    print("Computing momentum indicators...")
    indicators = precompute_indicators(data)

    print("Running weekly momentum screen...")
    holdings = run_strategy(data, indicators)

    # Stats
    filled = sum(1 for _, h in holdings if h)
    empty = sum(1 for _, h in holdings if not h)
    print(f"  {len(holdings)} rebalances: {filled} invested, {empty} cash")

    print("Backtesting...")
    metrics = evaluate_strategy(holdings, data)

    elapsed = time.time() - t0
    print_results(metrics, elapsed)


if __name__ == "__main__":
    main()
