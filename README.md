# Nautilus_Pair_Trading_Jerry
This is a demo of a pair trading strategy based on Nautilus Trader for non profit purposes as research and education.

The original version is on Interactive Brokers (IB), with 10s bar / kline data specified by nautilus trader internal methods and

it's written by Brad, Nautilus core contributor and senior quant researcher with experiences in Optiver and IMC.

This version is a Modified version using high freq tick data on crypto exchanges, modified by Jerry, a quant researcher and prop trader specilized in crypto market.

The modification is in progress and will be updated aperiodically.

## Layout

- `20220617/` — original IB / 10-second-bar SMH–SOXX demo
- `crypto_tick/` — Binance BTCUSDT–ETHUSDT perpetual tick version (rolling log OLS, trade-tick execution)
- `asq/` — original Avellaneda-Stoikov research notes (pandas / LightGBM)
- `asq_tick/` — Nautilus ASQ market maker on L2 top-of-book (backtest + live skeleton)

See `crypto_tick/README.md` for the pair-trading setup, and `asq_tick/README.md` for the ASQ L2 backtest.
