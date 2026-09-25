"""Convert repo-root incremental L2 dumps into top-of-book CSVs for ASQ."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asq_tick.data_l2 import L2Options, replay_to_tob, save_tob

DATA_DIR = Path(__file__).resolve().parent / "data"
TOB_NAMES = {
    "BTC": "btcusdt_perp_tob.csv",
    "ETH": "ethusdt_perp_tob.csv",
}


def _default_l2_path(symbol: str) -> Path:
    needle = "btc" if symbol.upper().startswith("BTC") else "eth"
    matches = sorted(ROOT.glob(f"incremental_book_L2_*{needle}.csv"))
    return matches[-1] if matches else ROOT / f"incremental_book_L2_*{needle}.csv"


def cmd_l2(symbol: str, src: Path, options: L2Options, out_dir: Path) -> None:
    key = "BTC" if symbol.upper().startswith("BTC") else "ETH"
    if not src.exists():
        raise FileNotFoundError(f"{key} L2 file not found: {src}")
    print(f"{key}: replaying {src.name} ...", flush=True)
    frame = replay_to_tob(src, options)
    path = save_tob(frame, out_dir / TOB_NAMES[key])
    if frame.empty:
        print(f"{key}: no top-of-book rows produced")
        return
    span_s = (frame.timestamp_ns.iloc[-1] - frame.timestamp_ns.iloc[0]) / 1e9
    print(f"{key}: {len(frame):,} rows covering {span_s / 60:.1f} min -> {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare L2 top-of-book for asq_tick")
    sub = parser.add_subparsers(dest="cmd", required=True)
    l2 = sub.add_parser("l2", help="convert an incremental L2 dump to top-of-book")
    l2.add_argument("--symbol", default="ETH", help="BTC or ETH")
    l2.add_argument("--src", default=None, help="path to incremental_book_L2_*.csv")
    l2.add_argument("--minutes", type=float, default=None, help="window length, default whole file")
    l2.add_argument("--skip-minutes", type=float, default=0.0)
    l2.add_argument("--throttle-ms", type=int, default=100)
    l2.add_argument("--out-dir", default=str(DATA_DIR))
    args = parser.parse_args()
    src = Path(args.src) if args.src else _default_l2_path(args.symbol)
    cmd_l2(
        args.symbol,
        src,
        L2Options(
            throttle_ms=args.throttle_ms,
            skip_minutes=args.skip_minutes,
            minutes=args.minutes,
        ),
        Path(args.out_dir),
    )


if __name__ == "__main__":
    main()
