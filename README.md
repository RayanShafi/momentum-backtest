# Shariah-Aware Momentum Backtest

This project tests a simple momentum strategy on 46 US stocks that a screening service has marked as Shariah compliant. The strategy is long-only, uses no leverage, and is tested on data that was not used to choose its settings.

## Aim

I wanted to find out whether a simple momentum strategy could beat an equal-weight portfolio of the same stocks without short selling or borrowing, and how much of any difference could be put down to chance.

## Disclaimer

This is a student research project. It is not investment advice or a fatwa. Compliance status was taken from a third-party screener (SP Funds, checked on 29 October 2026) and can change over time. Anyone who wants to invest on this basis should speak to a qualified scholar first.

## Method

At the end of each month, I:

1. ranked every stock by its return over the previous L months, leaving out the most recent month. The latest month is skipped because stock prices tend to partly reverse over short horizons, which can distort a momentum signal (Jegadeesh and Titman, 1993);
2. bought the top 30% of stocks (about 13) in equal amounts; and
3. held them for one month before repeating the process.

The strategy never sells short or borrows. I fixed the 30% figure before running the test rather than adjusting it afterwards. The lookback length L (3, 6, 9 or 12 months) was chosen using only the first 60% of the data.

## Universe

The universe is 46 US-listed stocks, listed in `universe.txt`. All were marked compliant by SP Funds on 29 October 2026. I selected US large and mid-cap companies from the screener's list without looking at their past performance.

Six of the stocks (CHWY, FIVE, GEV, NOW, PANW and SNDR) began trading after January 2010. I include each of them from the point at which it has enough price history, because leaving them out would have favoured companies that were already successful.

## Checks used

| Check | What I did |
|---|---|
| Train/test split | The lookback was chosen on the first 60% of the data. The results below use only the remaining 40%. |
| Transaction costs | A cost of 10 basis points is charged on turnover. I also tested 0, 25 and 50. |
| Timing | Positions chosen at the end of one month earn the following month's return, so the strategy never uses information it would not have had. |
| Confidence interval | I resampled the monthly returns 5,000 times to estimate a 95% interval for the Sharpe ratio. |
| Benchmark | An equal-weight portfolio of the same stocks. |
| Saved data | Prices are stored in `prices.csv`, so the results can be reproduced exactly. |

## Running the code

Install the requirements and then run the script. The second command uses randomly generated prices and is only there to check that the code runs.

```bash
pip install -r requirements.txt
python backtest.py
python backtest.py --synthetic
```

The script saves `results.png`, `results.csv` and `universe.txt`. If the ticker list is changed, `prices.csv` needs to be deleted first so that new data is downloaded.

## Results

The data runs from January 2010 to October 2026. The out-of-sample period is February 2020 to October 2026, which is the final 40% of the data. The lookback chosen in training was 9 months.

| Strategy | Annual return | Annual volatility | Sharpe ratio | 95% interval (Sharpe) | Maximum drawdown |
|---|---|---|---|---|---|
| Long-only momentum (9 months, after 10bp costs) | 22.2% | 19.2% | 1.15 | [0.39, 1.96] | -16.6% |
| Equal-weight universe | 19.6% | 18.1% | 1.08 | [0.35, 1.86] | -22.7% |

![Results](results.png)

Momentum returned about 2.6 percentage points a year more than the benchmark and had a smaller worst drawdown. However, the 95% intervals for the two Sharpe ratios overlap almost completely, so I cannot say the difference is more than chance.

Transaction costs had little effect. The Sharpe ratio was 1.18 with no costs and 1.02 with costs of 50 basis points.

The four lookbacks scored almost the same in training (1.35, 1.41, 1.43 and 1.42 for 3, 6, 9 and 12 months), so the choice of 9 months is not well supported by the data.

## Limitations

- **Survivorship bias.** The universe contains stocks that are compliant and listed today, so it leaves out companies that failed, were delisted or lost their compliance. This flatters both the strategy and the benchmark, and I think it is the largest weakness of the project.
- **Compliance applied to the past.** Today's screening result is applied to earlier years, when a company may not have qualified.
- **A favourable test period.** From 2020 onwards, large technology and growth stocks performed strongly, and they make up a good part of the universe.
- **One screener.** The compliance status comes from a single service, and screeners and scholars can disagree about individual companies.
- **A small universe.** With 46 stocks and about 13 held at a time, the results are quite noisy.
- **Simple costs.** Trading costs are a fixed assumption, whereas real costs depend on liquidity and spreads.
- **Dividends.** An investor would also need to think about purifying any non-compliant income. I have not modelled this.

## Tools

Python (pandas, NumPy and matplotlib), with price data downloaded using yfinance.

## Reference

Jegadeesh, N. and Titman, S. (1993) 'Returns to buying winners and selling losers: implications for stock market efficiency', *Journal of Finance*, 48(1), pp. 65-91.
