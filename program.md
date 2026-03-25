# mom-autoresearch

This is an experiment to have the LLM autonomously research momentum strategy parameters for the Indian stock market.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar25`). The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `prepare.py` — fixed constants, data fetching/caching, stock universe, sector mapping, date ranges, evaluation (backtesting). Do not modify.
   - `strategy.py` — the file you modify. Momentum parameters, scoring logic, screening filters, sector filtering, portfolio construction.
4. **Verify data exists**: Check that `~/.cache/mom-autosearch/` contains cached market data. If not, tell the human to run `python prepare.py` to fetch and cache Indian stock market data.
5. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs locally. Launch it simply as: `python strategy.py`.

**What you CAN do:**
- Modify `strategy.py` — this is the only file you edit. Everything is fair game: momentum lookback periods and weights, moving average periods, number of stocks held, sector filter logic, rebalance frequency, minimum momentum thresholds, adding new indicators (RSI, ADX, volatility adjustment, volume confirmation), score normalization, risk-adjusted momentum, dual momentum (absolute + relative), etc.

**What you CANNOT do:**
- Modify `prepare.py`. It is read-only. It contains the fixed evaluation (backtesting), data fetching/caching, stock universe, sector mapping, and date ranges.
- Install new packages or add dependencies. You can only use what's already in `requirements.txt`.
- Modify the evaluation harness. The `evaluate_strategy` function in `prepare.py` is the ground truth metric.

**The goal is simple: get the highest sharpe_ratio on the test set.**

**Overfitting** is the enemy. The evaluation is on an out-of-sample test period (2023–2026). A strategy that is overfit to a specific regime is worthless. Prefer robust, generalizable approaches.

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome — that's a simplification win.

**The first run**: Your very first run should always be to establish the baseline, so you will run the strategy script as is.

## Output format

Once the script finishes it prints a summary like this:

```
---
sharpe_ratio: 1.8342
total_return_pct: 337.4
benchmark_return_pct: 26.6
alpha_pct: 310.9
max_drawdown_pct: 20.6
win_rate_pct: 61.9
avg_holdings: 13.4
cash_pct: 0.0
num_rebalances: 160
trading_days: 796
best_month_pct: 18.5
worst_month_pct: -13.5
```

You can extract the key metrics from the log file:

```
grep "^sharpe_ratio:\|^alpha_pct:\|^max_drawdown_pct:" run.log
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated — commas break in descriptions).

The TSV has a header row and 7 columns:

```
commit	sharpe_ratio	total_return_pct	alpha_pct	max_drawdown_pct	status	description
```

1. git commit hash (short, 7 chars)
2. sharpe_ratio achieved (e.g. 1.8342) — use 0.0000 for crashes
3. total_return_pct (e.g. 337.4) — use 0.0 for crashes
4. alpha_pct over Nifty 50 (e.g. 310.9) — use 0.0 for crashes
5. max_drawdown_pct (e.g. 20.6) — use 0.0 for crashes
6. status: `keep`, `discard`, or `crash`
7. short text description of what this experiment tried

Example:

```
commit	sharpe_ratio	total_return_pct	alpha_pct	max_drawdown_pct	status	description
da1f527	1.8342	337.4	310.9	20.6	keep	baseline: 12m/6m/3m/1m ROC weighted, MA50/200 filter, top 5 sectors, top 15 stocks
b2c3d4e	2.1200	412.0	385.4	18.3	keep	switch to 6m/3m only, ADX filter, top 10 stocks
c3d4e5f	1.5100	220.5	193.9	25.1	discard	remove sector filter (worse sharpe)
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/mar25`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on
2. Tune `strategy.py` with an experimental idea by directly hacking the code.
3. git commit
4. Run the experiment: `python strategy.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context)
5. Read out the results: `grep "^sharpe_ratio:\|^total_return_pct:\|^alpha_pct:\|^max_drawdown_pct:" run.log`
6. If the grep output is empty, the run crashed. Run `tail -n 50 run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after more than a few attempts, give up.
7. Record the results in the tsv (NOTE: do not commit the results.tsv file, leave it untracked by git)
8. If sharpe_ratio improved (higher), you "advance" the branch, keeping the git commit
9. If sharpe_ratio is equal or worse, you git reset back to where you started

The idea is that you are a completely autonomous researcher trying things out. If they work, keep. If they don't, discard. And you're advancing the branch so that you can iterate.

**Crashes**: If a run crashes, use your judgment: If it's something dumb and easy to fix (e.g. a typo, a missing import), fix it and re-run. If the idea itself is fundamentally broken, just skip it, log "crash" as the status in the tsv, and move on.

**NEVER STOP**: Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or gone from a computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, think harder — try different momentum definitions, dual momentum, volatility-adjusted scores, different rebalance frequencies, portfolio sizing rules, risk parity weighting, stop-loss rules, relative strength approaches, sector rotation timing, regime detection. The loop runs until the human interrupts you, period.

## Experiment ideas to explore

Here are some directions worth trying (in no particular order):

- **Lookback tuning**: Try different ROC periods (e.g. 10m+3m, or 6m+1m only). Try equal weights vs different weightings.
- **Dual momentum**: Combine absolute momentum (stock vs cash) with relative momentum (stock vs index). Only hold stocks beating both.
- **Volatility adjustment**: Divide momentum score by trailing volatility (risk-adjusted momentum). Calmer uptrends score higher.
- **ADX filter**: Add Average Directional Index to filter for trending stocks only (ADX > 25).
- **Volume confirmation**: Require volume above its moving average on positive momentum days.
- **Portfolio size**: Try TOP_K = 10, 20, 25. Fewer stocks = more concentrated bets. More = diversification.
- **Rebalance frequency**: Try every 10 days, every 20 days (monthly). Less frequent = fewer whipsaws, lower turnover.
- **Sector count**: Try TOP_SECTORS = 3 (more concentrated) or 8 (more diversified). Or remove sector filter entirely.
- **MA periods**: Try 100/200 instead of 50/200, or 20/50 for faster signals.
- **Minimum momentum threshold**: Raise MIN_MOM_SCORE above 0 to be more selective.
- **Relative strength**: Score stocks by their performance relative to Nifty 50, not absolute ROC.
- **Regime filter**: Use benchmark MA (Nifty above its 200 DMA) as a regime switch — go to cash when market is bearish.
- **Universe**: Try NIFTY_50 only (more liquid) or NIFTY_100. Smaller universes may have less noise.
