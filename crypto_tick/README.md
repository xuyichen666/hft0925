# Crypto tick pair trading

Independent continuation of the original IB 10-second-bar demo in `20220617/`.
This folder trades **Binance USDT-M perpetuals** on **trade ticks**, not 10s bars.

Default pair:

- Source / hedge: `BTCUSDT-PERP.BINANCE`
- Target / alpha: `ETHUSDT-PERP.BINANCE`

## What changed from the equity demo

| Original (`20220617`) | This folder |
| --- | --- |
| SMH / SOXX on NASDAQ | BTC / ETH USDT-M perps on Binance |
| External 10-second bars | Trade ticks + internal 50-tick bars |
| Fit OLS once per day | Rolling log-log OLS, refit every 25 bars |
| Integer share lots | Decimal crypto quantities |
| Edge stored as an absolute value (sell side never fired) | Signed edge, both sides can trade |
| Custom `PositionId` hedging | NETTING qty hedge on the source leg |
| IB live adapter | Binance futures live adapter |

Signal path:

1. `PredictedPriceActor` builds 50-tick bars from trades, fits `log(ETH) = a + b log(BTC)`.
2. Every BTC trade publishes a fair ETH price.
3. `PairTrader` buys ETH and shorts BTC when ETH is cheap vs that fair value (and the reverse when ETH is rich).
4. Positions flatten when the residual falls back inside `0.25 * entry threshold`, or after 30 seconds.

## Setup

NautilusTrader needs **Python 3.11+**. The OLS / synthetic-data tests run on 3.9.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r crypto_tick/requirements.txt
```

## Run

Math smoke test (no Nautilus):

```bash
python crypto_tick/test_ols.py
```

Synthetic-tick backtest:

```bash
python crypto_tick/backtest.py --source synth
```

### Real Binance L2 dumps

The repo root holds Tardis-style incremental L2 dumps
(`incremental_book_L2_<date><symbol>.csv`, columns
`exchange, symbol, timestamp, local_timestamp, is_snapshot, side, price, amount`).
`prepare_data.py l2` replays every level update in order and writes throttled
top-of-book rows (`timestamp_ns, bid, ask, bid_size, ask_size`):

```bash
# whole day into crypto_tick/data/full, one row per 100 ms of change
python crypto_tick/prepare_data.py l2 --out-dir crypto_tick/data/full --throttle-ms 100
python crypto_tick/backtest.py
```

Note that `nautilus_trader` must be installed for the interpreter you use;
the system `python3` on macOS is not it.

Useful flags: `--skip-minutes` to start later in the tape, `--minutes` to bound
the window (omit it for the whole file), `--throttle-ms` to trade fidelity for
speed. A full 24-hour file takes roughly 8 minutes per symbol to replay.

In `l2` mode there are no trades, so the strategy runs quote-driven: bars are
aggregated as `MID` from the top of book and entries trigger on ETH quote
updates (`signal_source="quote"`).

Optional: persist ticks, then replay the CSV:

```bash
python crypto_tick/prepare_data.py synth --n-ticks 12000
python crypto_tick/backtest.py --source csv --data-dir crypto_tick/data
```

Download a short Binance futures tape (public REST, no API key):

```bash
python crypto_tick/prepare_data.py download --minutes 15
python crypto_tick/backtest.py --source csv --data-dir crypto_tick/data
```

Live skeleton (testnet by default). Keep `notional_trade_size_usd` tiny.

```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
export BINANCE_TESTNET=1
python crypto_tick/live.py
```

## What the real data says

`analyze.py` measures the spread before any backtest:

```bash
python crypto_tick/analyze.py --data-dir crypto_tick/data/full --hold-s 1200
```

On the full 2026-09-09 day the BTC/ETH log-price spread has a **half-life of
23–32 minutes**, and the BTC/ETH return correlation shows a textbook Epps
effect — 0.39 at 100 ms rising to 0.93 at 5 minutes. The consequences:

- There is no exploitable spread at HFT horizons. What looks like a wide sigma
  at 100 ms is unhedged directional risk (beta is only 0.53 there), not edge.
- Breaking even on fees needs a hold of roughly 20 minutes or more.
- The regression window must be **much longer than the half-life**. A rolling
  1-hour fit absorbs the dislocation into the model and leaves nothing to trade.

## Results on the 24h L2 tape

5,000 USDT on the ETH leg, dollar-neutral BTC hedge, Binance perp fees
(2 bp maker / 4 bp taker):

| config | net | fees | gross/trip | fees/trip | trips |
| --- | --- | --- | --- | --- | --- |
| HFT defaults (2s bars, taker, 30s hold) | -2,997 | 3,280 | +0.5 bp | 5.9 bp | 1113 |
| 5s bars, 1h lookback, 3σ, maker entry | -182 | 278 | +1.9 bp | 5.4 bp | 104 |
| 30s bars, 12h lookback, 2σ, maker entry | **-16** | 35 | **+6.3 bp** | 11.6 bp | 6 |

That last row is the default, so running the backtest with no arguments
reproduces it:

```bash
python crypto_tick/backtest.py
```

Every parameter falls back to a per-source preset in `PRESETS`, so
`--source synth` restores the tick-bar settings and any individual flag
(`--std-dev`, `--bar-spec`, ...) overrides just that one value.

Tuning cut the loss by 99% and turned the per-trade economics from noise into a
real +6.3 bp capture, but that still loses to 11.6 bp of execution cost. The
remaining gap is entirely fees: the ETH entry is passive, while the ETH exit and
both BTC hedge legs still cross the spread. Closing it needs all-maker execution
(passive exits and a passive hedge with a market fallback) or a better fee tier —
not a different signal.

## Useful knobs

Set these on `PairTraderConfig` / `PredictedPriceConfig`:

- `bar_spec`: tick-bar size, default `50-TICK-LAST`
- `lookback_bars` / `refit_every_bars`: rolling regression window
- `trade_width_std_dev`: entry z-score, default `2.0`
- `exit_std_frac`: flatten when `|edge| < 0.25 * required`
- `notional_trade_size_usd`: ETH leg size
- `max_hold_ns`: HFT timeout, default 30s
- `signal_source`: `"trade"` for tick tapes, `"quote"` for L2 top-of-book
- `entry_style`: `"taker"`, `"maker"` (post-only at the touch), or `"ioc_limit"`
- `entry_ttl_ns`: how long an unfilled passive entry may rest before it is pulled

Rule of thumb from the analysis: keep `lookback_bars × bar_seconds` well above
the spread half-life, and `max_hold_ns` at least as long as the half-life.

The original 10s IB strategy is untouched under `20220617/`.
