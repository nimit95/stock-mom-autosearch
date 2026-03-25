"""
prepare.py - Data fetching, universe, sectors, and backtest harness
for Indian stock momentum strategy.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Config ─────────────────────────────────────────────────────
DATA_START = "2015-01-01"
TEST_START = "2023-01-01"
TEST_END = "2026-03-25"
BENCHMARK_TICKER = "^NSEI"
CACHE_DIR = Path.home() / ".cache" / "mom-autosearch"
RISK_FREE_RATE = 0.07  # 7% annual (India)

# ── Stock Universe ─────────────────────────────────────────────

NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "HCLTECH.NS",
    "SUNPHARMA.NS", "TITAN.NS", "TATAMOTORS.NS", "NTPC.NS", "ADANIENT.NS",
    "POWERGRID.NS", "M&M.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "BAJAJFINSV.NS",
    "ONGC.NS", "WIPRO.NS", "NESTLEIND.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "ADANIPORTS.NS", "COALINDIA.NS", "GRASIM.NS", "BPCL.NS", "TECHM.NS",
    "DRREDDY.NS", "DIVISLAB.NS", "CIPLA.NS", "BRITANNIA.NS", "EICHERMOT.NS",
    "HEROMOTOCO.NS", "APOLLOHOSP.NS", "INDUSINDBK.NS", "SBILIFE.NS",
    "HDFCLIFE.NS", "TATACONSUM.NS", "BAJAJ-AUTO.NS", "HINDALCO.NS",
    "TRENT.NS", "SHREECEM.NS",
]

NIFTY_NEXT_50 = [
    "DMART.NS", "VEDL.NS", "GODREJCP.NS", "PIDILITIND.NS", "DABUR.NS",
    "BERGEPAINT.NS", "HAVELLS.NS", "SIEMENS.NS", "BOSCHLTD.NS",
    "AMBUJACEM.NS", "ACC.NS", "DLF.NS", "BANKBARODA.NS", "PNB.NS",
    "INDIGO.NS", "NAUKRI.NS", "ICICIPRULI.NS", "MARICO.NS", "COLPAL.NS",
    "TORNTPHARM.NS", "LUPIN.NS", "AUROPHARMA.NS", "BIOCON.NS",
    "MUTHOOTFIN.NS", "CHOLAFIN.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS",
    "PERSISTENT.NS", "LTIM.NS", "PIIND.NS", "SBICARD.NS",
    "HDFCAMC.NS", "ICICIGI.NS", "CANBK.NS", "IOC.NS", "GAIL.NS",
    "PETRONET.NS", "TATAPOWER.NS", "ABB.NS", "MOTHERSON.NS", "ZOMATO.NS",
    "LICI.NS", "IRCTC.NS", "PAGEIND.NS", "MPHASIS.NS", "MAXHEALTH.NS",
    "JUBLFOOD.NS", "INDUSTOWER.NS", "JSWENERGY.NS",
]

NIFTY_MIDCAP_100 = [
    "COFORGE.NS", "POLYCAB.NS", "TATACOMM.NS", "CUMMINSIND.NS",
    "BHARATFORG.NS", "ESCORTS.NS", "LICHSGFIN.NS", "OBEROIRLTY.NS",
    "AUBANK.NS", "SAIL.NS", "NMDC.NS", "RECLTD.NS", "PFC.NS",
    "NHPC.NS", "HINDPETRO.NS", "CONCOR.NS", "VOLTAS.NS", "CROMPTON.NS",
    "KPITTECH.NS", "COROMANDEL.NS", "ASTRAL.NS", "SUNDARMFIN.NS",
    "IDEA.NS", "PRESTIGE.NS", "SUNTV.NS", "BALKRISIND.NS",
    "MFSL.NS", "APLAPOLLO.NS", "DEEPAKNTR.NS", "ATUL.NS",
    "GLAXO.NS", "HONAUT.NS", "LINDEINDIA.NS", "PHOENIXLTD.NS",
    "RELAXO.NS", "ABCAPITAL.NS", "TATACHEM.NS", "ALKEM.NS",
    "IPCALAB.NS", "NATCOPHARM.NS", "LAURUSLABS.NS", "GLENMARK.NS",
    "EMAMILTD.NS", "TATAELXSI.NS", "LTTS.NS", "MINDTREE.NS",
    "OFSS.NS", "NAVINFLUOR.NS", "SYNGENE.NS", "SONACOMS.NS",
    "FORTIS.NS", "STARHEALTH.NS", "MANAPPURAM.NS", "L&TFH.NS",
    "ABFRL.NS", "TVSMOTOR.NS", "ASHOKLEY.NS", "MRF.NS",
    "BATAINDIA.NS", "WHIRLPOOL.NS", "BLUESTARLT.NS", "CENTURYTEX.NS",
    "RAMCOCEM.NS", "JKCEMENT.NS", "DALBHARAT.NS", "INDHOTEL.NS",
    "LALPATHLAB.NS", "METROPOLIS.NS", "SOLARINDS.NS", "GRINDWELL.NS",
    "SUMICHEM.NS", "UBL.NS", "GUJGASLTD.NS", "MGL.NS",
    "IGL.NS", "CESC.NS", "SJVN.NS", "IREDA.NS",
    "FACT.NS", "GMDCLTD.NS", "HAL.NS", "BEL.NS",
    "BDL.NS", "COCHINSHIP.NS", "MAZAGONDOCK.NS", "GRSE.NS",
    "PAYTM.NS", "NYKAA.NS", "POLICYBZR.NS", "DELHIVERY.NS",
    "LODHA.NS", "GODREJPROP.NS", "BRIGADE.NS", "SOBHA.NS",
    "SUZLON.NS", "NHPC.NS", "UNIONBANK.NS", "INDIANB.NS",
    "BANDHANBNK.NS", "IDBI.NS",
]

NIFTY_100 = NIFTY_50 + NIFTY_NEXT_50
NIFTY_200 = NIFTY_100 + NIFTY_MIDCAP_100

UNIVERSE = NIFTY_200

# ── Sector Mapping ─────────────────────────────────────────────

SECTOR_MAP = {
    # IT
    "TCS.NS": "IT", "INFY.NS": "IT", "HCLTECH.NS": "IT",
    "WIPRO.NS": "IT", "TECHM.NS": "IT", "LTIM.NS": "IT",
    "MPHASIS.NS": "IT", "COFORGE.NS": "IT", "PERSISTENT.NS": "IT",
    "LTTS.NS": "IT", "TATAELXSI.NS": "IT", "KPITTECH.NS": "IT",
    "MINDTREE.NS": "IT", "OFSS.NS": "IT", "NAUKRI.NS": "IT",
    # Banking
    "HDFCBANK.NS": "Banking", "ICICIBANK.NS": "Banking",
    "KOTAKBANK.NS": "Banking", "SBIN.NS": "Banking",
    "AXISBANK.NS": "Banking", "INDUSINDBK.NS": "Banking",
    "BANKBARODA.NS": "Banking", "PNB.NS": "Banking",
    "FEDERALBNK.NS": "Banking", "IDFCFIRSTB.NS": "Banking",
    "CANBK.NS": "Banking", "AUBANK.NS": "Banking",
    "BANDHANBNK.NS": "Banking", "UNIONBANK.NS": "Banking",
    "INDIANB.NS": "Banking", "IDBI.NS": "Banking",
    # NBFC / Finance
    "BAJFINANCE.NS": "Finance", "BAJAJFINSV.NS": "Finance",
    "CHOLAFIN.NS": "Finance", "MUTHOOTFIN.NS": "Finance",
    "MANAPPURAM.NS": "Finance", "LICHSGFIN.NS": "Finance",
    "RECLTD.NS": "Finance", "PFC.NS": "Finance",
    "ABCAPITAL.NS": "Finance", "SUNDARMFIN.NS": "Finance",
    "MFSL.NS": "Finance", "HDFCAMC.NS": "Finance",
    "SBICARD.NS": "Finance", "L&TFH.NS": "Finance",
    "IREDA.NS": "Finance",
    # Insurance
    "SBILIFE.NS": "Insurance", "HDFCLIFE.NS": "Insurance",
    "ICICIPRULI.NS": "Insurance", "ICICIGI.NS": "Insurance",
    "STARHEALTH.NS": "Insurance", "LICI.NS": "Insurance",
    # Pharma / Healthcare
    "SUNPHARMA.NS": "Pharma", "DRREDDY.NS": "Pharma",
    "CIPLA.NS": "Pharma", "DIVISLAB.NS": "Pharma",
    "LUPIN.NS": "Pharma", "AUROPHARMA.NS": "Pharma",
    "TORNTPHARM.NS": "Pharma", "BIOCON.NS": "Pharma",
    "ALKEM.NS": "Pharma", "IPCALAB.NS": "Pharma",
    "NATCOPHARM.NS": "Pharma", "LAURUSLABS.NS": "Pharma",
    "GLENMARK.NS": "Pharma", "SYNGENE.NS": "Pharma",
    "APOLLOHOSP.NS": "Healthcare", "MAXHEALTH.NS": "Healthcare",
    "FORTIS.NS": "Healthcare", "LALPATHLAB.NS": "Healthcare",
    "METROPOLIS.NS": "Healthcare",
    # Auto
    "MARUTI.NS": "Auto", "TATAMOTORS.NS": "Auto",
    "M&M.NS": "Auto", "BAJAJ-AUTO.NS": "Auto",
    "HEROMOTOCO.NS": "Auto", "EICHERMOT.NS": "Auto",
    "ASHOKLEY.NS": "Auto", "TVSMOTOR.NS": "Auto",
    "MOTHERSON.NS": "Auto", "BALKRISIND.NS": "Auto",
    "BHARATFORG.NS": "Auto", "ESCORTS.NS": "Auto",
    "MRF.NS": "Auto", "BOSCHLTD.NS": "Auto", "SONACOMS.NS": "Auto",
    # FMCG
    "HINDUNILVR.NS": "FMCG", "ITC.NS": "FMCG",
    "NESTLEIND.NS": "FMCG", "TATACONSUM.NS": "FMCG",
    "BRITANNIA.NS": "FMCG", "DABUR.NS": "FMCG",
    "GODREJCP.NS": "FMCG", "MARICO.NS": "FMCG",
    "COLPAL.NS": "FMCG", "EMAMILTD.NS": "FMCG", "UBL.NS": "FMCG",
    # Consumer Discretionary
    "TITAN.NS": "Consumer", "ASIANPAINT.NS": "Consumer",
    "PIDILITIND.NS": "Consumer", "DMART.NS": "Consumer",
    "TRENT.NS": "Consumer", "PAGEIND.NS": "Consumer",
    "HAVELLS.NS": "Consumer", "VOLTAS.NS": "Consumer",
    "CROMPTON.NS": "Consumer", "BERGEPAINT.NS": "Consumer",
    "BATAINDIA.NS": "Consumer", "WHIRLPOOL.NS": "Consumer",
    "JUBLFOOD.NS": "Consumer", "INDHOTEL.NS": "Consumer",
    "ZOMATO.NS": "Consumer", "NYKAA.NS": "Consumer",
    "ASTRAL.NS": "Consumer", "RELAXO.NS": "Consumer",
    "POLYCAB.NS": "Consumer", "BLUESTARLT.NS": "Consumer",
    # Energy / Oil & Gas
    "RELIANCE.NS": "Energy", "ONGC.NS": "Energy",
    "BPCL.NS": "Energy", "IOC.NS": "Energy",
    "GAIL.NS": "Energy", "HINDPETRO.NS": "Energy",
    "PETRONET.NS": "Energy", "IGL.NS": "Energy",
    "MGL.NS": "Energy", "GUJGASLTD.NS": "Energy",
    "ADANIENT.NS": "Energy",
    # Power / Utilities
    "NTPC.NS": "Power", "POWERGRID.NS": "Power",
    "TATAPOWER.NS": "Power", "NHPC.NS": "Power",
    "SJVN.NS": "Power", "CESC.NS": "Power",
    "JSWENERGY.NS": "Power", "SUZLON.NS": "Power",
    # Metals / Mining
    "JSWSTEEL.NS": "Metals", "TATASTEEL.NS": "Metals",
    "HINDALCO.NS": "Metals", "COALINDIA.NS": "Metals",
    "VEDL.NS": "Metals", "NMDC.NS": "Metals", "SAIL.NS": "Metals",
    "APLAPOLLO.NS": "Metals",
    # Telecom
    "BHARTIARTL.NS": "Telecom", "IDEA.NS": "Telecom",
    "INDUSTOWER.NS": "Telecom", "TATACOMM.NS": "Telecom",
    # Cement
    "ULTRACEMCO.NS": "Cement", "GRASIM.NS": "Cement",
    "SHREECEM.NS": "Cement", "AMBUJACEM.NS": "Cement",
    "ACC.NS": "Cement", "RAMCOCEM.NS": "Cement",
    "JKCEMENT.NS": "Cement", "DALBHARAT.NS": "Cement",
    # Infrastructure / Realty
    "LT.NS": "Infra", "ADANIPORTS.NS": "Infra",
    "IRCTC.NS": "Infra", "CONCOR.NS": "Infra",
    "DLF.NS": "Realty", "OBEROIRLTY.NS": "Realty",
    "PRESTIGE.NS": "Realty", "GODREJPROP.NS": "Realty",
    "PHOENIXLTD.NS": "Realty", "BRIGADE.NS": "Realty",
    "SOBHA.NS": "Realty", "LODHA.NS": "Realty",
    # Industrials / Defence
    "SIEMENS.NS": "Industrials", "ABB.NS": "Industrials",
    "CUMMINSIND.NS": "Industrials", "HAL.NS": "Defence",
    "BEL.NS": "Defence", "BDL.NS": "Defence",
    "COCHINSHIP.NS": "Defence", "MAZAGONDOCK.NS": "Defence",
    "GRSE.NS": "Defence",
    # Chemicals
    "PIIND.NS": "Chemicals", "COROMANDEL.NS": "Chemicals",
    "DEEPAKNTR.NS": "Chemicals", "ATUL.NS": "Chemicals",
    "NAVINFLUOR.NS": "Chemicals", "SUMICHEM.NS": "Chemicals",
    "TATACHEM.NS": "Chemicals",
    # Others
    "SUNTV.NS": "Media", "INDIGO.NS": "Travel",
    "DELHIVERY.NS": "Logistics", "PAYTM.NS": "Fintech",
    "POLICYBZR.NS": "Fintech", "CENTURYTEX.NS": "Textiles",
    "ABFRL.NS": "Textiles", "SOLARINDS.NS": "Industrials",
    "GRINDWELL.NS": "Industrials", "HONAUT.NS": "Industrials",
    "LINDEINDIA.NS": "Industrials", "GLAXO.NS": "Pharma",
    "FACT.NS": "Chemicals", "GMDCLTD.NS": "Metals",
    "IREDA.NS": "Finance",
}


def get_sector(ticker):
    return SECTOR_MAP.get(ticker, "Other")


# ── Data Fetching ──────────────────────────────────────────────


def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_data():
    """Download OHLCV for universe + benchmark. Cache to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "market_data.pkl"

    if cache_file.exists():
        print(f"Loading cached data from {cache_file}")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    print("Fetching data from Yahoo Finance...")
    all_data = {}
    failed = []
    all_tickers = list(dict.fromkeys(UNIVERSE))

    for ticker in all_tickers:
        try:
            df = yf.download(ticker, start=DATA_START, end=TEST_END, progress=False)
            df = _flatten_columns(df)
            if len(df) >= 252:
                all_data[ticker] = df
                print(f"  OK: {ticker} ({len(df)} rows)")
            else:
                failed.append(ticker)
                print(f"  SKIP: {ticker} (only {len(df)} rows)")
        except Exception as e:
            failed.append(ticker)
            print(f"  FAIL: {ticker} ({e})")

    print(f"Fetching benchmark {BENCHMARK_TICKER}...")
    benchmark = yf.download(BENCHMARK_TICKER, start=DATA_START, end=TEST_END, progress=False)
    benchmark = _flatten_columns(benchmark)

    data = {"stocks": all_data, "benchmark": benchmark}
    with open(cache_file, "wb") as f:
        pickle.dump(data, f)

    print(f"\nFetched {len(all_data)} stocks ({len(failed)} failed)")
    return data


def load_data():
    """Load cached data, return stocks dict + benchmark returns."""
    raw = fetch_data()
    bench = raw["benchmark"]
    bench_ret = bench["Close"].pct_change().dropna()

    # Precompute daily returns for all stocks
    stock_returns = {}
    for ticker, df in raw["stocks"].items():
        stock_returns[ticker] = df["Close"].pct_change()

    print(f"Loaded {len(raw['stocks'])} stocks")
    return {
        "stocks": raw["stocks"],
        "stock_returns": stock_returns,
        "benchmark_returns": bench_ret,
    }


# ── Backtest ───────────────────────────────────────────────────


def evaluate_strategy(holdings_schedule, data):
    """
    Backtest a momentum strategy from a holdings schedule.

    holdings_schedule: list of (pd.Timestamp, list[str])
        Each entry = (rebalance_date, tickers_to_hold).
        Empty list = cash.
    data: output of load_data()

    Returns dict of performance metrics.
    """
    stock_returns = data["stock_returns"]
    bench = data["benchmark_returns"]

    # Build list of all test trading days from benchmark index
    test_start = pd.Timestamp(TEST_START)
    test_dates = sorted([d for d in bench.index if d >= test_start])

    if not test_dates or not holdings_schedule:
        return _empty_metrics()

    risk_free_daily = RISK_FREE_RATE / 252

    # Sort schedule by date
    schedule = sorted(holdings_schedule, key=lambda x: x[0])

    # Walk through each day
    portfolio_returns = []
    ret_dates = []
    current_holdings = []
    sched_idx = 0
    cash_days = 0
    total_holdings_count = 0
    num_rebalances = 0

    for date in test_dates:
        # Check if we need to update holdings
        while sched_idx < len(schedule) and schedule[sched_idx][0] <= date:
            current_holdings = schedule[sched_idx][1]
            sched_idx += 1
            num_rebalances += 1

        if not current_holdings:
            portfolio_returns.append(risk_free_daily)
            cash_days += 1
        else:
            rets = []
            for t in current_holdings:
                if t in stock_returns and date in stock_returns[t].index:
                    r = stock_returns[t].loc[date]
                    if not np.isnan(r):
                        rets.append(r)
            if rets:
                portfolio_returns.append(np.mean(rets))
                total_holdings_count += len(rets)
            else:
                portfolio_returns.append(risk_free_daily)
                cash_days += 1

        ret_dates.append(date)

    port = pd.Series(portfolio_returns, index=pd.DatetimeIndex(ret_dates))
    bench_aligned = bench.reindex(port.index).fillna(0)

    # Sharpe (annualised, 7% risk-free)
    excess = port - risk_free_daily
    sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0.0

    # Returns
    total_return = ((1 + port).prod() - 1) * 100
    bench_prod = (1 + bench_aligned).prod()
    if hasattr(bench_prod, "__len__"):
        bench_prod = float(bench_prod.iloc[0]) if len(bench_prod) > 0 else 1.0
    bench_return = (float(bench_prod) - 1) * 100

    # Drawdown
    cum = (1 + port).cumprod()
    running_max = cum.cummax()
    dd = (cum - running_max) / running_max
    max_dd = abs(dd.min()) * 100

    # Win rate
    win_rate = (port > 0).mean() * 100

    # Average holdings
    non_cash_days = len(port) - cash_days
    avg_holdings = total_holdings_count / non_cash_days if non_cash_days > 0 else 0

    # Monthly returns for best/worst
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


def _empty_metrics():
    return {k: 0 for k in [
        "sharpe_ratio", "total_return_pct", "benchmark_return_pct",
        "alpha_pct", "max_drawdown_pct", "win_rate_pct", "avg_holdings",
        "cash_pct", "num_rebalances", "trading_days", "best_month_pct",
        "worst_month_pct",
    ]}


def print_results(metrics, elapsed=0):
    """Pretty-print backtest results."""
    print()
    print("=" * 60)
    print("  MOMENTUM STRATEGY RESULTS")
    print("=" * 60)
    print(f"  Sharpe ratio (ann.):   {metrics['sharpe_ratio']:.4f}")
    print(f"  Total return:          {metrics['total_return_pct']:.1f}%")
    print(f"  Benchmark (Nifty 50):  {metrics['benchmark_return_pct']:.1f}%")
    print(f"  Alpha:                 {metrics['alpha_pct']:.1f}%")
    print(f"  Max drawdown:          {metrics['max_drawdown_pct']:.1f}%")
    print(f"  Win rate (daily):      {metrics['win_rate_pct']:.1f}%")
    print(f"  Avg stocks held:       {metrics['avg_holdings']:.1f}")
    print(f"  Cash %:                {metrics['cash_pct']:.1f}%")
    print(f"  Rebalances:            {metrics['num_rebalances']}")
    print(f"  Trading days:          {metrics['trading_days']}")
    print(f"  Best month:            {metrics['best_month_pct']:.1f}%")
    print(f"  Worst month:           {metrics['worst_month_pct']:.1f}%")
    if elapsed:
        print(f"  Runtime:               {elapsed:.1f}s")
    print("=" * 60)

    # Machine-readable block
    print("\n---")
    for k, v in metrics.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    print("Fetching and caching data...")
    fetch_data()
    print("Done. Run: python strategy.py")
