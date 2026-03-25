"""
strategy.py - Momentum strategy: score, screen, hold, go to cash.

Tune the parameters below, then run:  python strategy.py
"""

import time

import numpy as np
import pandas as pd

from prepare import (
    load_data, print_results,
    get_sector, TEST_START, RISK_FREE_RATE,
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
MIN_STOCKS = 7        # fewer qualifying → 100% cash

# Sector filter
TOP_SECTORS = 3       # pick stocks only from top N sectors by avg momentum

# Momentum threshold
MIN_MOM_SCORE = 0.0   # minimum composite score to qualify

# RSI filter
RSI_PERIOD = 14       # RSI lookback
RSI_MIN = 30          # reject oversold (below this)
RSI_MAX = 70          # reject overbought (above this)

# Regime filter
REGIME_MA = 200       # go to cash if benchmark below this MA

# Per-stock trailing stop
STOCK_STOP_PCT = 0.05 # exit stock if it drops 5% from its peak

# ═══════════════════════════════════════════════════════════════


def precompute_indicators(data):
    """Compute momentum indicators for every stock. Returns dict of DataFrames."""
    bench_cum = (1 + data["benchmark_returns"]).cumprod()
    bench_roc_126 = bench_cum.pct_change(126)

    indicators = {}
    for ticker, df in data["stocks"].items():
        close = df["Close"]
        ind = pd.DataFrame(index=df.index)
        ind["close"] = close

        for p in ROC_PERIODS:
            ind[f"roc_{p}"] = close.pct_change(p)

        ind["ma_fast"] = close.rolling(MA_FAST).mean()
        ind["ma_slow"] = close.rolling(MA_SLOW).mean()

        ind["mom_score"] = sum(
            w * ind[f"roc_{p}"] for w, p in zip(ROC_WEIGHTS, ROC_PERIODS)
        )

        ind["bench_roc_126"] = bench_roc_126.reindex(ind.index)

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(RSI_PERIOD).mean()
        loss = (-delta.clip(upper=0)).rolling(RSI_PERIOD).mean()
        rs = gain / loss.clip(lower=1e-10)
        ind["rsi"] = 100 - (100 / (1 + rs))

        indicators[ticker] = ind

    return indicators


def screen_stocks(indicators, date):
    """Screen stocks on a given date. Returns ranked list of tickers."""
    scores = {}

    for ticker, ind in indicators.items():
        if date not in ind.index:
            continue
        row = ind.loc[date]

        if row.isna().any():
            continue
        if row["close"] <= row["ma_fast"] or row["close"] <= row["ma_slow"]:
            continue
        if row[f"roc_{ROC_PERIODS[0]}"] <= 0:
            continue
        if not np.isnan(row["bench_roc_126"]) and row["roc_126"] <= row["bench_roc_126"]:
            continue
        rsi = row["rsi"]
        if not np.isnan(rsi) and (rsi < RSI_MIN or rsi > RSI_MAX):
            continue
        if row["mom_score"] <= MIN_MOM_SCORE:
            continue

        scores[ticker] = row["mom_score"]

    if not scores:
        return []

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

    ranked = sorted(filtered, key=filtered.get, reverse=True)
    return ranked[:TOP_K]


def run_backtest(data, indicators):
    """
    Full backtest with per-stock trailing stop.
    Returns metrics dict compatible with print_results.
    """
    stock_returns = data["stock_returns"]
    stocks = data["stocks"]
    bench_ret = data["benchmark_returns"]
    bench_cum = (1 + bench_ret).cumprod()
    bench_ma = bench_cum.rolling(REGIME_MA).mean()

    bench_dates = bench_ret.index
    test_start = pd.Timestamp(TEST_START)
    test_dates = sorted([d for d in bench_dates if d >= test_start])

    risk_free_daily = RISK_FREE_RATE / 252

    # State
    current_holdings = []     # list of tickers
    pending_holdings = None   # set on rebalance, applied next day
    stock_peaks = {}          # {ticker: peak_close_since_entry}
    stopped_stocks = set()    # tickers stopped out (applied with 1-day delay)
    pending_stops = set()     # stops triggered today, applied tomorrow

    portfolio_returns = []
    ret_dates = []
    cash_days = 0
    total_holdings_count = 0
    num_rebalances = 0

    for i, date in enumerate(test_dates):
        # Apply pending holdings from previous rebalance day
        if pending_holdings is not None:
            current_holdings = list(pending_holdings)
            pending_holdings = None
            stock_peaks = {}
            stopped_stocks = set()
            pending_stops = set()
            # Initialize peaks at entry
            for t in current_holdings:
                if t in stocks and date in stocks[t].index:
                    stock_peaks[t] = stocks[t].loc[date, "Close"]

        # Apply pending stops from yesterday (1-day delay, like rebalance)
        if pending_stops:
            stopped_stocks.update(pending_stops)
            pending_stops = set()

        # Check for rebalance
        if i % REBALANCE_EVERY == 0:
            if date in bench_cum.index and date in bench_ma.index:
                if bench_cum.loc[date] < bench_ma.loc[date]:
                    pending_holdings = []
                    num_rebalances += 1
                else:
                    picks = screen_stocks(indicators, date)
                    pending_holdings = picks
                    num_rebalances += 1
            else:
                picks = screen_stocks(indicators, date)
                pending_holdings = picks
                num_rebalances += 1

        # Active holdings today (exclude already-stopped stocks)
        active = [t for t in current_holdings if t not in stopped_stocks]

        # Compute daily return for ALL active stocks (including those
        # that will be stopped today — they still hold today)
        if not active:
            portfolio_returns.append(risk_free_daily)
            cash_days += 1
        else:
            rets = []
            for t in active:
                if t in stock_returns and date in stock_returns[t].index:
                    r = stock_returns[t].loc[date]
                    if not np.isnan(r):
                        rets.append(r)

                        # Check stop using today's Low (intraday breach)
                        # If Low breached stop, use stop price as exit
                        # (but return is already computed from close-to-close
                        #  so the loss is captured naturally)
            if rets:
                n_active = len(rets)
                n_stopped = len(stopped_stocks)
                n_total = n_active + n_stopped
                if n_total > 0 and n_stopped > 0:
                    daily_ret = (sum(rets) + n_stopped * risk_free_daily) / n_total
                else:
                    daily_ret = np.mean(rets)
                portfolio_returns.append(daily_ret)
                total_holdings_count += n_active
            else:
                portfolio_returns.append(risk_free_daily)
                cash_days += 1

        # Per-stock trailing stop: check AFTER computing returns
        # Uses Close price. Stop takes effect TOMORROW (1-day delay).
        if STOCK_STOP_PCT > 0:
            for t in active:
                if t in stopped_stocks or t in pending_stops:
                    continue
                if t in stocks and date in stocks[t].index:
                    close = stocks[t].loc[date, "Close"]

                    # Update peak using close
                    if t in stock_peaks:
                        stock_peaks[t] = max(stock_peaks[t], close)
                    else:
                        stock_peaks[t] = close

                    # Check if close breached stop level
                    stop_level = stock_peaks[t] * (1 - STOCK_STOP_PCT)
                    if close <= stop_level:
                        pending_stops.add(t)

        ret_dates.append(date)

    # Compute metrics
    port = pd.Series(portfolio_returns, index=pd.DatetimeIndex(ret_dates))
    bench_aligned = bench_ret.reindex(port.index).fillna(0)

    excess = port - risk_free_daily
    sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0.0

    total_return = ((1 + port).prod() - 1) * 100
    bench_prod = (1 + bench_aligned).prod()
    if hasattr(bench_prod, "__len__"):
        bench_prod = float(bench_prod.iloc[0]) if len(bench_prod) > 0 else 1.0
    bench_return = (float(bench_prod) - 1) * 100

    cum = (1 + port).cumprod()
    running_max = cum.cummax()
    dd = (cum - running_max) / running_max
    max_dd = abs(dd.min()) * 100

    win_rate = (port > 0).mean() * 100
    non_cash_days = len(port) - cash_days
    avg_holdings = total_holdings_count / non_cash_days if non_cash_days > 0 else 0

    monthly = port.resample("ME").apply(lambda x: (1 + x).prod() - 1)

    return {
        "sharpe_ratio": round(float(sharpe), 4),
        "total_return_pct": round(float(total_return), 1),
        "benchmark_return_pct": round(float(bench_return), 1),
        "alpha_pct": round(float(total_return - bench_return), 1),
        "max_drawdown_pct": round(float(max_dd), 1),
        "win_rate_pct": round(float(win_rate), 1),
        "avg_holdings": round(float(avg_holdings), 1),
        "cash_pct": round(float(cash_days / len(port) * 100), 1),
        "num_rebalances": num_rebalances,
        "trading_days": len(port),
        "best_month_pct": round(float(monthly.max() * 100), 1) if len(monthly) > 0 else 0,
        "worst_month_pct": round(float(monthly.min() * 100), 1) if len(monthly) > 0 else 0,
    }


def main():
    t0 = time.time()

    print("Loading data...")
    data = load_data()

    print("Computing momentum indicators...")
    indicators = precompute_indicators(data)

    print("Running backtest with per-stock trailing stop...")
    metrics = run_backtest(data, indicators)

    elapsed = time.time() - t0
    print_results(metrics, elapsed)


if __name__ == "__main__":
    main()
