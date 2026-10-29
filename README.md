# Shariah-Aware Momentum Backtest

A long-only momentum strategy on a universe of 46 US stocks confirmed compliant by a screening
service, tested out-of-sample with transaction costs and bootstrapped confidence intervals.

**Question:** can a simple momentum strategy that avoids short selling, leverage and
non-compliant business activities add value over holding the same stocks equally, and how much of
any apparent edge is distinguishable from luck?

> This is a research exercise, not a fatwa or investment advice. Compliance status comes from a
> third-party screener (SP Funds, checked 29 October 2026) and changes over time. Verify
> with a qualified scholar before relying on it.

## Strategy
Each month-end:
1. Rank stocks by trailing return over the past *L* months, **skipping the most recent month**
   (to avoid the short-term reversal effect, as in Jegadeesh & Titman, 1993).
2. Hold the top 30% (about 13 stocks) equal-weighted. **Long-only: no short selling, no leverage.**
3. Hold for one month, then rebalance.

The 30% portfolio size was fixed in advance, not tuned on results.

## Universe
46 US-listed stocks (listed in `universe.txt`), all marked compliant by SP Funds on
29 October 2026. Selection rule: compliant US large caps from the screener's list, chosen without 
reference to past performance.

Stocks that listed after 2010 (for example A, ABT, ADBE, AMZN, AVGO, BBY, BSX, CDNS, CHWY, COP, COST, CSCO, CTAS, CVX, DLTR, FIVE, GEV, GNRC, IDXX, INTC, JNJ, LIN, MDT, MRVL, MSFT, NOW, ODFL, PANW, PG, PH, QCOM, RBC, RMD, ROST, RVTY, SNDR, SNPS, SWKS, SYK, TECH, TJX, TSCO, UNH, WMT, WSM, XOM) 
are kept and used only from
the point they have enough price history. Dropping them would have added survivorship bias.

## What makes the evaluation honest
| Check | Why it matters |
|---|---|
| **Train/test split (60/40)** | The lookback is chosen on training data only; results are reported on untouched data. |
| **Transaction costs** | 10 bps charged on turnover; sensitivity shown at 0/10/25/50 bps. |
| **No look-ahead** | Weights set at month-end *t* earn returns over month *t+1*. |
| **Bootstrap CI on Sharpe** | A Sharpe ratio is an estimate, not a fact. 95% interval reported. |
| **Like-for-like benchmark** | Compared to an equal-weight portfolio of the same stocks. |
| **Cached data** | Prices are saved to `prices.csv` so every run is reproducible. |

## Run it
```bash
pip install -r requirements.txt
python backtest.py              # real data via yfinance (cached in prices.csv)
python backtest.py --synthetic  # simulated data, code test only
```
Outputs `results.png`, `results.csv` and `universe.txt`. If you change the ticker list, delete
`prices.csv` first.

## Results
Data: January 2010 to October 2026. Out-of-sample period: February 2020 to October 2026
(the final 40% of the data). Lookback chosen on training data only: 9 months.

| Strategy | Ann. return | Ann. vol | Sharpe | 95% CI (Sharpe) | Max drawdown |
|---|---|---|---|---|---|
| Long-only momentum (9m, net 10bps) | 22.2% | 19.2% | 1.15 | [0.39, 1.96] | -16.6% |
| Equal-weight universe | 19.6% | 18.1% | 1.08 | [0.35, 1.86] | -22.7% |

![Results](results.png)

**Findings**
- Momentum returned slightly more than the benchmark with a shallower worst drawdown, but the
  Sharpe confidence intervals overlap almost entirely, so there is **no statistically significant
  edge**.
- Transaction costs barely mattered (Sharpe 1.18 at 0 bps, 1.02 at 50 bps).
- Training Sharpe ratios for the 3, 6, 9 and 12 month lookbacks (1.35, 1.41, 1.43, 1.42) were
  nearly identical, so the selected lookback is fragile.

## Known limitations (read these)
- **Survivorship bias**: the universe is built from stocks that are compliant and listed *today*,
  which excludes companies that failed, were delisted or lost compliance. This flatters returns for
  both the strategy and the benchmark, and is probably the largest limitation here.
- **Screen applied backwards in time**: today's compliance status is applied to past years, when a
  company may not have qualified.
- **Strong test period**: 2020 onwards was a very favourable market for large-cap growth and
  technology stocks, which make up much of the universe.
- **Third-party screen**: the status comes from one service; different screeners and scholars can
  disagree on individual stocks.
- **Modest universe** (46 stocks, about 13 held at a time), so results are noisy.
- **Parameter fragility**: the four lookbacks scored almost identically in training.
- **Costs are a flat assumption**; real costs depend on liquidity and spread.
- **Dividends**: real-world investing would also need to consider purification of non-compliant
  income. Not modelled here.

## Ideas for extension
- Use point-in-time compliance data and index constituents to remove survivorship bias
- Test a larger universe and other markets (e.g. FTSE, via `.L` tickers)
- Regress returns on Fama-French factors to see if the result is just market and size exposure
- Add a volatility-scaled momentum variant

## Stack
Python, pandas, NumPy, matplotlib, yfinance.
