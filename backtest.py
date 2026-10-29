"""
Cross-sectional momentum backtest with honest evaluation.

Idea: each month, rank stocks by past 12-1 month return (skip the latest month
to avoid short-term reversal), go long the top quantile and short the bottom
quantile (or long-only), hold for a month, and rebalance.

What makes this more than a tutorial:
  * Transaction costs charged on turnover
  * Out-of-sample split (parameters chosen on train, reported on test)
  * Bootstrap confidence interval on the Sharpe ratio
  * Multiple-testing awareness: we try many lookbacks, so we report how the
    best one compares to the distribution of all of them

Usage:
    python backtest.py              # downloads real data with yfinance
    python backtest.py --synthetic  # runs on simulated data (no internet)
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "JPM", "BAC", "WFC", "GS",
    "XOM", "CVX", "COP", "JNJ", "PFE", "MRK", "ABBV", "PG", "KO", "PEP",
    "WMT", "COST", "HD", "LOW", "MCD", "NKE", "DIS", "CMCSA", "VZ", "T",
    "INTC", "CSCO", "ORCL", "IBM", "QCOM", "TXN", "CAT", "DE", "BA", "HON",
    "GE", "MMM", "UNH", "CVS", "LLY", "AMGN", "GILD", "MDT", "ABT", "TMO",
]


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
    import os

    cache = "prices.csv"  # cached so every run uses identical data
    if os.path.exists(cache):
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    import yfinance as yf

    data = yf.download(TICKERS, start=start, auto_adjust=True, progress=False)["Close"]
    data = data.dropna(axis=1, how="any")
    data.to_csv(cache)
    return data


def momentum_returns(prices, lookback=12, skip=1, quantile=0.2, cost_bps=10, long_short=True):
    """Monthly strategy returns net of costs."""
    monthly = prices.resample("ME").last()
    rets = monthly.pct_change()
    signal = monthly.shift(skip) / monthly.shift(lookback) - 1  # 12-1 style
    weights = pd.DataFrame(0.0, index=monthly.index, columns=monthly.columns)

    for date, row in signal.iterrows():
        row = row.dropna()
        if len(row) < 10:
            continue
        k = max(1, int(len(row) * quantile))
        ranked = row.sort_values()
        longs, shorts = ranked.index[-k:], ranked.index[:k]
        weights.loc[date, longs] = 1.0 / k
        if long_short:
            weights.loc[date, shorts] = -1.0 / k

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
    print(f"Universe: {prices.shape[1]} stocks, {prices.index[0].date()} to {prices.index[-1].date()}")

    split = prices.index[int(len(prices) * 0.6)]
    train_prices, test_prices = prices[:split], prices[split:]

    # 1. Parameter search on TRAIN only
    lookbacks = [3, 6, 9, 12]
    train_sharpes = {lb: sharpe(momentum_returns(train_prices, lookback=lb)) for lb in lookbacks}
    best = max(train_sharpes, key=train_sharpes.get)
    print("\nTrain Sharpe by lookback:", {k: round(v, 2) for k, v in train_sharpes.items()})
    print(f"Chosen lookback (train only): {best} months")

    # 2. Evaluate on untouched TEST period (need history before split for the signal)
    full_ret = momentum_returns(prices, lookback=best)
    test_ret = full_ret[full_ret.index > split]
    bench = prices.resample("ME").last().pct_change().mean(axis=1)  # equal-weight market
    bench = bench.reindex(test_ret.index)

    rows = [
        summarise(f"Momentum L/S ({best}m, net 10bps)", test_ret),
        summarise("Equal-weight benchmark", bench.dropna()),
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

    # 3b. Sensitivity to portfolio size
    print("\nSharpe vs top/bottom bucket size (test period):")
    for q in [0.1, 0.2, 0.3, 0.4]:
        r = momentum_returns(prices, lookback=best, quantile=q)
        r = r[r.index > split]
        print(f"  top/bottom {int(q*100)}% -> Sharpe {sharpe(r):.2f}")

    # 4. Plot
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    (1 + test_ret).cumprod().plot(ax=ax[0], label="Momentum L/S")
    (1 + bench.dropna()).cumprod().plot(ax=ax[0], label="Equal-weight")
    ax[0].set_title("Out-of-sample growth of £1"); ax[0].legend()
    cum = (1 + test_ret).cumprod()
    (cum / cum.cummax() - 1).plot(ax=ax[1], color="firebrick")
    ax[1].set_title("Momentum drawdown")
    plt.tight_layout(); plt.savefig("results.png", dpi=150)
    table.to_csv("results.csv")
    print("\nSaved results.png and results.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    main(ap.parse_args().synthetic)
