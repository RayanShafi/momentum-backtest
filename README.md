# Does Momentum Survive Honest Testing?

A cross-sectional momentum backtest on 50 large-cap US stocks, built to answer one question:
**if you test a strategy properly, does the edge survive?**

Most backtests on the internet overstate performance. This project deliberately includes the
checks that expose that.

## Strategy
Each month-end:
1. Rank stocks by trailing return over the past *L* months, **skipping the most recent month**
   (to avoid the short-term reversal effect, as in Jegadeesh & Titman, 1993).
2. Go long the top 20%, short the bottom 20%, equal-weighted.
3. Hold for one month, then rebalance.

## What makes the evaluation honest
| Check | Why it matters |
|---|---|
| **Train/test split (60/40)** | The lookback is chosen on training data only; results are reported on untouched data. |
| **Transaction costs** | 10 bps charged on turnover; sensitivity shown at 0/10/25/50 bps. |
| **No look-ahead** | Weights set at month-end *t* earn returns over month *t+1*. |
| **Bootstrap CI on Sharpe** | A Sharpe ratio is an estimate, not a fact. 95% interval reported. |
| **Benchmark** | Compared to an equal-weight portfolio of the same stocks. |

## Run it
```bash
pip install -r requirements.txt
python backtest.py              # real data via yfinance
python backtest.py --synthetic  # simulated data, no internet needed
```
Outputs `results.png` and `results.csv`.

## Results
Out-of-sample period: February 2020 to October 2026 (the final 40% of the data).
Lookback chosen on training data only: 3 months.

| Strategy | Ann. return | Ann. vol | Sharpe | 95% CI (Sharpe) | Max drawdown |
|---|---|---|---|---|---|
| Momentum L/S (3m, net 10bps) | -5.7% | 20.8% | -0.18 | [-0.93, 0.61] | -50.9% |
| Equal-weight benchmark | 16.8% | 15.9% | 1.06 | [0.30, 1.91] | -18.6% |

![Results](results.png)

**Findings**
- Momentum did not beat the benchmark out-of-sample. The Sharpe confidence interval includes zero, so the result is statistically indistinguishable from no edge.
- Costs worsened it (Sharpe -0.05 at 0bps, -0.70 at 50bps), but the signal was already negative before costs.
- No portfolio size tested (top/bottom 10-40%) produced a positive Sharpe.
- The training scores for the 3, 9 and 12 month lookbacks were nearly identical (0.18, 0.15, 0.17), so the selected lookback is fragile. Adding one stock to the universe changed the selection from 12 to 3 months.
- Data is cached in prices.csv so results are reproducible.

These results apply to this small universe and period only and do not show that momentum fails in general.

## Known limitations (read these)
- **Survivorship bias**: the stock list is today's large caps, so it excludes companies that
  failed or were dropped. This flatters any long-biased strategy. Fix: use point-in-time index
  constituents.
- **Only 4 lookbacks tested**, but the more you test, the more likely the "best" is luck.
  A proper treatment would apply a deflated Sharpe ratio or White's reality check.
- **Costs are a flat assumption**; real costs depend on liquidity, spread and borrow fees
  (shorting is not free).
- **Short sample / single market regime.**

## Ideas for extension
- Point-in-time universe to remove survivorship bias
- Add value or quality factors and test a combined signal
- Regress returns on Fama-French factors to see if "momentum alpha" is just market beta
- Volatility-scaled momentum (Barroso & Santa-Clara, 2015)

## Stack
Python, pandas, NumPy, matplotlib, yfinance.
