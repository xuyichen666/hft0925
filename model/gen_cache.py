"""
生成 1 秒因子 cache（ETHUSDT snap25 + trades）
- 从 book_snapshot_25/*.csv 和 trades/*.csv 生成
- 输出到 model/cache/eth_1s_v5_YYYY-MM-DD.parquet
- 支持 --limit N 只处理前 N 天
- 支持跳过已存在的 cache
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import pandas as pd

# 项目根目录（gen_cache.py 在 model/ 下，所以 parent.parent）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.features_snap25 import feature_frame  # noqa: E402

DATA_DIR = ROOT / "book_snapshot_25"
TRADE_DIR = DATA_DIR / "trades"
CACHE_DIR = ROOT / "model" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PREDICT_SECS = 60
FEATURE_VERSION = "v5"


def process_one_day(snap_path: Path, trade_path: Path, date: str) -> None:
    cache_path = CACHE_DIR / f"eth_1s_{FEATURE_VERSION}_{date}.parquet"
    if cache_path.exists():
        print(f"跳过 {date}: cache 已存在 -> {cache_path.name}", flush=True)
        return

    print(f"\n处理 {date}...", flush=True)
    print(f"  snapshot: {snap_path.name} ({snap_path.stat().st_size / 1e9:.2f} GB)", flush=True)
    print(f"  trades:   {trade_path.name} ({trade_path.stat().st_size / 1e6:.2f} MB)", flush=True)

    # ---- 读 snapshot ----
    print("  读取 snapshot...", flush=True)
    snap = pd.read_csv(snap_path)
    print(f"  snapshot 读取完成: {len(snap):,} 行, {len(snap.columns)} 列", flush=True)

    if "symbol" in snap.columns:
        print(f"  symbol: {snap['symbol'].iloc[0]}", flush=True)

    # ---- 读 trades ----
    print("  读取 trades...", flush=True)
    trades = pd.read_csv(trade_path)
    print(f"  trades 读取完成: {len(trades):,} 行", flush=True)

    # ---- 生成因子 ----
    print("  生成因子...", flush=True)
    bars = feature_frame(snap, predict_secs=PREDICT_SECS, trades=trades)
    bars["trade_date"] = date
    print(f"  因子生成完成: {len(bars):,} 行, {len(bars.columns)} 列", flush=True)

    # ---- 保存 ----
    print(f"  保存到 {cache_path.name}...", flush=True)
    bars.to_parquet(cache_path, compression="snappy")
    print(f"  -> {cache_path.name} ({cache_path.stat().st_size / 1e6:.1f} MB)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 1 秒因子 cache")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 天")
    parser.add_argument("--force", action="store_true", help="强制重新生成（覆盖已有 cache）")
    args = parser.parse_args()

    print("=" * 70, flush=True)
    print("  生成 1 秒因子 cache", flush=True)
    print("=" * 70, flush=True)
    print(f"DATA_DIR:  {DATA_DIR}", flush=True)
    print(f"TRADE_DIR: {TRADE_DIR}", flush=True)
    print(f"CACHE_DIR: {CACHE_DIR}", flush=True)
    print(f"PREDICT_SECS: {PREDICT_SECS}", flush=True)
    print(f"FEATURE_VERSION: {FEATURE_VERSION}", flush=True)
    print(f"LIMIT: {args.limit}", flush=True)
    print(f"FORCE: {args.force}", flush=True)
    print(flush=True)

    if not DATA_DIR.exists():
        raise SystemExit(f"数据目录不存在: {DATA_DIR}")

    snap_files = sorted(DATA_DIR.glob("book_snapshot_25_*.csv"))
    if not snap_files:
        raise SystemExit(f"没有找到 snapshot 文件: {DATA_DIR}")

    if args.limit:
        snap_files = snap_files[: args.limit]

    print(f"找到 {len(snap_files)} 天 snapshot\n", flush=True)

    success = 0
    failed = 0

    for snap_path in snap_files:
        date = snap_path.stem.replace("book_snapshot_25_", "")
        trade_path = TRADE_DIR / f"trades_{date}.csv"

        if not trade_path.exists():
            print(f"跳过 {date}: 没有 trades 文件 ({trade_path.name})", flush=True)
            continue

        # force 模式：删掉旧 cache
        cache_path = CACHE_DIR / f"eth_1s_{FEATURE_VERSION}_{date}.parquet"
        if args.force and cache_path.exists():
            cache_path.unlink()
            print(f"删除旧 cache: {cache_path.name}", flush=True)

        try:
            process_one_day(snap_path, trade_path, date)
            success += 1
        except Exception as e:
            print(f"\n处理 {date} 失败: {e}", flush=True)
            print("完整 traceback:", flush=True)
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70, flush=True)
    print("  完成", flush=True)
    print("=" * 70, flush=True)
    print(f"成功: {success} 天", flush=True)
    print(f"失败: {failed} 天", flush=True)

    caches = sorted(CACHE_DIR.glob(f"eth_1s_{FEATURE_VERSION}_*.parquet"))
    print(f"\ncache 文件: {len(caches)} 个", flush=True)
    for c in caches:
        print(f"  {c.name} ({c.stat().st_size / 1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()