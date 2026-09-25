# ASQ tick market making

Independent Nautilus port of the Avellaneda-Stoikov maker in `asq/`,
laid out like the original IB demo in `20220617/demo/`.

Default instrument: `ETHUSDT-PERP.BINANCE` (the notebook used ETHUSDT).

| Original | This folder |
| --- | --- |
| `asq/asq.py` GTD-on-every-tick template | `strategy.py` cancel-replace maker quotes |
| `asq/aqsmodel.py` pandas + LightGBM notebook | `model.py` rolling (A, k, σ) actor |
| `20220617/demo/backtest.py` catalog bars | `backtest.py` L2 top-of-book quotes |
| `20220617/demo/live.py` Interactive Brokers | `live.py` Binance USD-M futures |

Signal path:

1. Incremental L2 dumps are replayed to throttled BBO rows (`timestamp_ns, bid, ask, bid_size, ask_size`).
2. `ASParamActor` builds 1-second bars, fits λ(δ) = A e^{-kδ} and mid-price σ,
   then a LightGBM 1-minute return on top-of-book features (same target / clip /
   hyperparameters as `asq/aqsmodel.py`).
3. `ASQMarketMaking` quotes around the predicted fair mid `mid * (1 + pred)`
   with inventory skew, clamped to 1–5 ticks and never more aggressive than the
   live BBO (the notebook's maker clamp).
4. Inventory is NETTING qty. At ±Q only the flattening side is quoted.

Maker fee on the local instruments is a **1 bp rebate** (`-0.0001`); taker is
4 bp. These definitions are used as-is (not `TestInstrumentProvider`) so the
rebate actually hits the backtest.

The original `asq/` sources are left untouched.

## Setup

NautilusTrader needs **Python 3.11+**.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r asq_tick/requirements.txt
```

## Run

Math smoke test (no Nautilus):

```bash
python asq_tick/test_as.py
```

L2 backtest. If `crypto_tick/data/full/*_tob.csv` already exists this folder
reuses it; otherwise convert the repo-root dump first:

```bash
python asq_tick/prepare_data.py l2 --symbol eth --out-dir asq_tick/data
python asq_tick/backtest.py
```

Useful flags:

```bash
python asq_tick/backtest.py --minutes 30 --symbol ETH
python asq_tick/backtest.py --max-spread-ticks 2 --quote-interval-ms 1000
```

Live skeleton (testnet by default). Keep notionals tiny.

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
export BINANCE_TESTNET=1
python asq_tick/live.py
```

## Knobs

Set these on `ASQConfig` / `ASParamConfig`:

- `notional_trade_size_usd`: clip size per quote
- `max_inventory_usd`: inventory cap Q
- `quote_interval_ms`: cancel-replace cadence (default 1s, matching the notebook)
- `min_spread_ticks` / `max_spread_ticks`: clamp the AS distance to a tradeable band
- `gamma`: risk aversion, default 0.01
- `lookback_bars` / `refit_every_bars`: rolling intensity window
- `use_fair_mid`: quote around LightGBM fair mid (default on). `--no-fair` to disable.

Trade features from the original pickle (taker buy/sell, GBR, BCT, ...) are not
on the L2 top-of-book feed, so the live model uses the order-book subset:
imbalance, microprice/vwap, spread, MACD, RSI, momentum, slope, and TOB size
changes. Target is still the 1-minute mid return, clipped at ±5 bp.

```bash
python asq_tick/backtest.py
python asq_tick/backtest.py --no-fair
```

On the 2026-09-09 ETH L2 tape (24h, 100 ms BBO, 200 USDT clips, **−1 bp maker rebate**):

| config | net | commissions | fills |
| --- | --- | --- | --- |
| LightGBM fair mid (default) | **−0.10** | −362 (rebate) | 18,208 |
| 20-minute slice | +0.79 | −6.50 | 343 |

The rebate is doing most of the work versus the previous +2 bp maker run (−1,669). Fair mid cuts some adverse-selection fills; remaining drift is still inventory.
