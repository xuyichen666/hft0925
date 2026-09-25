"""CLI helpers: generate synthetic ticks or download Binance aggTrades."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_tick.data_binance import download_agg_trades, save_downloaded
from crypto_tick.data_l2 import L2Options, replay_to_tob, save_tob
from crypto_tick.data_synth import generate_pair_ticks, save_pair_csv

DATA_DIR = Path(__file__).resolve().parent / "data"
REPO_ROOT = Path(__file__).resolve().parent.parent


def cmd_synth(n_ticks: int) -> None:
    from crypto_tick.data_synth import SynthConfig

    btc, eth = generate_pair_ticks(SynthConfig(n_ticks=n_ticks))
    save_pair_csv(btc, eth, DATA_DIR)
    print(f"Wrote synthetic ticks to {DATA_DIR}")


def cmd_download(minutes: int) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    for symbol, filename_src in (("BTCUSDT", "btc"), ("ETHUSDT", "eth")):
        frame = download_agg_trades(symbol, start_ms, end_ms)
        path = save_downloaded(filename_src + "usdt", frame, DATA_DIR)
        # Normalize names expected by backtest --source csv
        if symbol == "BTCUSDT":
            target = DATA_DIR / "btcusdt_perp_ticks.csv"
        else:
            target = DATA_DIR / "ethusdt_perp_ticks.csv"
        if path != target:
            frame.to_csv(target, index=False)
        print(f"{symbol}: {len(frame)} trades -> {target}")


def cmd_l2(btc_path: Path, eth_path: Path, options: L2Options, out_dir: Path = DATA_DIR) -> None:
    for label, src, out_name in (
        ("BTC", btc_path, "btcusdt_perp_tob.csv"),
        ("ETH", eth_path, "ethusdt_perp_tob.csv"),
    ):
        if not src.exists():
            raise FileNotFoundError(f"{label} L2 file not found: {src}")
        print(f"{label}: replaying {src.name} ...", flush=True)
        frame = replay_to_tob(src, options)
        path = save_tob(frame, out_dir / out_name)
        if frame.empty:
            print(f"{label}: no top-of-book rows produced")
            continue
        span_s = (frame.timestamp_ns.iloc[-1] - frame.timestamp_ns.iloc[0]) / 1e9
        print(f"{label}: {len(frame):,} rows covering {span_s / 60:.1f} min -> {path}")


def _default_l2_path(pattern: str) -> Path:
    matches = sorted(REPO_ROOT.glob(pattern))
    return matches[-1] if matches else REPO_ROOT / pattern


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare tick data for crypto_tick")
    sub = parser.add_subparsers(dest="cmd", required=True)
    synth = sub.add_parser("synth")
    synth.add_argument("--n-ticks", type=int, default=12_000)
    down = sub.add_parser("download")
    down.add_argument("--minutes", type=int, default=15)
    l2 = sub.add_parser("l2", help="convert incremental L2 dumps to top-of-book")
    l2.add_argument("--btc", default=str(_default_l2_path("incremental_book_L2_*btc.csv")))
    l2.add_argument("--eth", default=str(_default_l2_path("incremental_book_L2_*eth.csv")))
    l2.add_argument("--minutes", type=float, default=None, help="window length, default whole file")
    l2.add_argument("--skip-minutes", type=float, default=0.0)
    l2.add_argument("--throttle-ms", type=int, default=100)
    l2.add_argument("--out-dir", default=str(DATA_DIR))
    args = parser.parse_args()
    if args.cmd == "synth":
        cmd_synth(args.n_ticks)
    elif args.cmd == "download":
        cmd_download(args.minutes)
    else:
        cmd_l2(
            Path(args.btc),
            Path(args.eth),
            L2Options(
                throttle_ms=args.throttle_ms,
                skip_minutes=args.skip_minutes,
                minutes=args.minutes,
            ),
            Path(args.out_dir),
        )


if __name__ == "__main__":
    main()
