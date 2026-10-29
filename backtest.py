"""
Shariah-aware momentum backtest: long-only, screened universe.

Idea: each month, rank stocks by past return over a lookback window (skipping
the latest month to avoid short-term reversal), hold the top quantile
equal-weighted for one month, then rebalance.

Design choices:
  * LONG-ONLY: no short selling and no leverage
  * Universe = tickers verified as compliant with a screening service (TICKERS)
  * Benchmark is an equal-weight portfolio of the SAME universe
  * Stocks that listed after 2010 are kept and used from when they have data
    (dropping them would add survivorship bias)

Evaluation checks:
  * Transaction costs charged on turnover
  * Out-of-sample split (lookback chosen on training data only)
  * Bootstrap confidence interval on the Sharpe ratio
  * No look-ahead: weights set at month-end t earn returns over month t+1

IMPORTANT: this is a research exercise, not a fatwa. Compliance status comes
from a third-party screener and changes over time. Verify with a qualified
scholar before relying on it.

Usage:
    python backtest.py              # real data via yfinance (cached in prices.csv)
    python backtest.py --synthetic  # simulated data, code test only

If you change TICKERS, delete prices.csv so fresh data is downloaded.
"""
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Tickers confirmed compliant by the screening service used (US listings).
TICKERS = [
    "ABT", "AMZN", "COP", "COST", "UNH", "CSCO", "CVX", "INTC", "JNJ", "MDT",
    "MSFT", "PG", "QCOM", "WMT", "XOM", "AVGO", "NOW", "ADBE", "PANW", "SNPS",
    "CDNS", "SYK", "BSX", "IDXX", "CTAS", "ODFL", "TJX", "ROST", "TSCO", "MRVL",
    "A", "RMD", "GEV", "LIN", "PH", "RBC", "WSM", "SWKS", "RVTY", "TECH",
    "GNRC", "SNDR", "DLTR", "BBY", "FIVE", "CHWY",
]

# Fixed in advance (not tuned on results): hold the top 30% of the universe,
# equal-weighted.
QUANTILE = 0.3


def load_prices(synthetic: bool, start="2010-01-01") -> pd.DataFrame:
    if synthetic:
        rng = np.random.default_rng(42)
        idx = pd.bdate_range("2005-01-03", "2024-12-31")
        n = len(TICKERS)
        market = rng.normal(0.0004, 0.01, len(idx))
        betas = rng.uniform(0.6, 1.4, n)
        # tiny persistent drift differences so momentum has *something* weak to find
        drifts = rng.normal(0.0002, 0.0002, n)
        rets = market[:, None] * betas + rng.normal(0, 0.012, (len(idx), n)) + drifts
        return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=TICKERS)

    cache = "prices.csv"  # cached so every run uses identical data
    if os.path.exists(cache):
        cached = pd.read_csv(cache, index_col=0, parse_dates=True)
        if set(cached.columns) <= set(TICKERS):
            return cached
        print("prices.csv contains tickers not in TICKERS (stale cache); re-downloading.")
    import yfinance as yf

    data = yf.download(TICKERS, start=start, auto_adjust=True, progress=False)["Close"]
    data = data.dropna(axis=1, how="all")  # drop only tickers with no data at all
    failed = [t for t in TICKERS if t not in data.columns]
    if failed:
        print(f"WARNING: no data downloaded for: {failed}")
    data.to_csv(cache)
    return data


def monthly_returns(prices):
    monthly = prices.resample("ME").last()
    return monthly, monthly / monthly.shift(1) - 1


def momentum_returns(prices, lookback=12, skip=1, quantile=QUANTILE, cost_bps=10):
    """Monthly long-only strategy returns net of costs."""
    monthly, rets = monthly_returns(prices)
    signal = monthly.shift(skip) / monthly.shift(lookback) - 1
    weights = pd.DataFrame(0.0, index=monthly.index, columns=monthly.columns)

    for date, row in signal.iterrows():
        row = row.dropna()  # only stocks with enough history have a signal
        if len(row) < 10:
            continue
        k = max(1, int(len(row) * quantile))
        longs = row.sort_values().index[-k:]
        weights.loc[date, longs] = 1.0 / k

    # weights decided at month-end t are earned over month t+1 (no look-ahead)
    gross = (weights.shift(1) * rets).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0)
    net = gross - turnover * cost_bps / 1e4
    return net.iloc[lookback + 1:]


def sharpe(r):
    return np.sqrt(12) * r.mean() / r.std(ddof=1) if r.std(ddof=1) > 0 else np.nan


def max_drawdown(r):
    cum = (1 + r).cumprod()
    return (cum / cum.cummax() - 1).min()


def bootstrap_sharpe_ci(r, n=5000, seed=0):
    rng = np.random.default_rng(seed)
    vals = r.values
    sims = [sharpe(pd.Series(rng.choice(vals, len(vals), replace=True))) for _ in range(n)]
    return np.percentile(sims, [2.5, 97.5])


def summarise(name, r):
    lo, hi = bootstrap_sharpe_ci(r)
    return {
        "strategy": name,
        "ann_return": (1 + r).prod() ** (12 / len(r)) - 1,
        "ann_vol": r.std(ddof=1) * np.sqrt(12),
        "sharpe": sharpe(r),
        "sharpe_95ci": f"[{lo:.2f}, {hi:.2f}]",
        "max_drawdown": max_drawdown(r),
    }


def main(synthetic: bool):
    prices = load_prices(synthetic)
    missing = [t for t in TICKERS if t not in prices.columns]
    if missing:
        print(f"Not in data: {missing}")
    first = prices.apply(lambda s: s.first_valid_index())
    late = first[first > pd.Timestamp(prices.index[0]) + pd.Timedelta(days=180)]
    if len(late):
        print("Tickers whose data starts later (used only from when they have data):",
              {k: str(v.date()) for k, v in late.items()})
    print(f"Universe: {prices.shape[1]} stocks, {prices.index[0].date()} to {prices.index[-1].date()}")

    split = prices.index[int(len(prices) * 0.6)]
    train_prices = prices[:split]

    # 1. Lookback chosen on TRAIN only
    lookbacks = [3, 6, 9, 12]
    train_sharpes = {lb: sharpe(momentum_returns(train_prices, lookback=lb)) for lb in lookbacks}
    best = max(train_sharpes, key=train_sharpes.get)
    print("\nTrain Sharpe by lookback:", {k: round(float(v), 2) for k, v in train_sharpes.items()})
    print(f"Chosen lookback (train only): {best} months")
    print(f"Test period starts after: {split.date()}")

    # 2. Evaluate on the untouched TEST period
    full_ret = momentum_returns(prices, lookback=best)
    test_ret = full_ret[full_ret.index > split]
    bench = monthly_returns(prices)[1].mean(axis=1).reindex(test_ret.index).dropna()

    rows = [
        summarise(f"Long-only momentum ({best}m, net 10bps)", test_ret),
        summarise("Equal-weight universe", bench),
    ]
    table = pd.DataFrame(rows).set_index("strategy")
    pd.options.display.float_format = "{:.3f}".format
    print("\nOUT-OF-SAMPLE RESULTS")
    print(table.to_string())

    # 3. Cost sensitivity
    print("\nSharpe vs transaction cost (test period):")
    for bps in [0, 10, 25, 50]:
        r = momentum_returns(prices, lookback=best, cost_bps=bps)
        r = r[r.index > split]
        print(f"  {bps:>3} bps -> Sharpe {sharpe(r):.2f}")

    # 4. Plot
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    (1 + test_ret).cumprod().plot(ax=ax[0], label="Long-only momentum")
    (1 + bench).cumprod().plot(ax=ax[0], label="Equal-weight universe")
    ax[0].set_title("Out-of-sample growth of £1"); ax[0].legend()
    cum = (1 + test_ret).cumprod()
    (cum / cum.cummax() - 1).plot(ax=ax[1], color="firebrick")
    ax[1].set_title("Long-only momentum drawdown")
    plt.tight_layout(); plt.savefig("results.png", dpi=150)
    table.to_csv("results.csv")
    with open("universe.txt", "w") as f:
        f.write("Universe used:\n" + ", ".join(prices.columns) + "\n")
        if missing:
            f.write("\nNo data for: " + ", ".join(missing) + "\n")
    print("\nSaved results.png, results.csv, universe.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    main(ap.parse_args().synthetic)
