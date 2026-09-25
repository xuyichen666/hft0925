"""Parse ASQ-snap25 Nautilus JSONL logs into a dashboard snapshot."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_GLOB = "logs/asq-snap25-testnet-*.jsonl"
FX_DEFAULT = 6.77

CST = timezone(timedelta(hours=8))
PX_RE = re.compile(
    r"LimitOrder\((BUY|SELL) ([0-9.]+) ETHUSDT-PERP\.BINANCE LIMIT @ ([0-9,_]+\.?[0-9]*)"
)


@dataclass
class DashboardSnapshot:
    generated_at: str
    log_path: str
    log_mtime: str
    fx_cny: float
    session_start_cst: str
    session_end_cst: str
    runtime_hours: float
    alive_hint: str

    equity_usdt: float
    equity_open_usdt: float
    equity_delta_usdt: float
    equity_cny: float
    equity_open_cny: float
    equity_delta_cny: float

    submit_notional_usdt: float
    fill_notional_usdt: float
    fill_notional_cny: float
    submit_notional_cny: float
    fill_rate_pct: float
    vol_eth: float
    fees_usdt: float
    fees_cny: float
    price_pnl_usdt: float
    price_pnl_cny: float
    fee_bps: float

    submit_count: int
    fill_count: int
    maker_count: int
    taker_count: int
    closed_count: int
    net_position_eth: float

    as_ok: int
    as_skip: int
    err_2011: int
    err_other: int
    spike_halts: int

    quote_both: int
    quote_sell_only: int
    quote_buy_only: int
    spread_ticks_mode: int

    med_hold_s: float
    p90_hold_s: float

    proj_fill_usdt_24h: float
    proj_fill_cny_24h: float
    proj_sub_usdt_24h: float
    proj_sub_cny_24h: float

    hours: list[str] = field(default_factory=list)
    hourly_submit_wan_cny: list[float] = field(default_factory=list)
    hourly_fill_wan_cny: list[float] = field(default_factory=list)
    hourly_fee_cny: list[float] = field(default_factory=list)
    hourly_equity_delta_cny: list[float] = field(default_factory=list)
    hourly_net_eth: list[float] = field(default_factory=list)
    hourly_submit_n: list[int] = field(default_factory=list)
    hourly_fill_n: list[int] = field(default_factory=list)

    recent_fills: list[dict[str, Any]] = field(default_factory=list)
    worst_closed: list[dict[str, Any]] = field(default_factory=list)
    ticker: list[str] = field(default_factory=list)


def _parse_ts(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def _cst(t: str) -> datetime:
    return _parse_ts(t).astimezone(CST)


def _hour_cst(t: str) -> str:
    return _cst(t).strftime("%H")


def find_latest_log(log_dir: Path | None = None) -> Path:
    base = log_dir or (ROOT / "logs")
    patterns = ("asq-snap25-testnet-*.jsonl", "asq-snap25-testnet-*.log")
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(p for p in base.glob(pat) if p.stat().st_size > 0)
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(
            f"no non-empty asq-snap25-testnet-*.jsonl/.log in {base} "
            "(ignore 0-byte stubs without an extension)"
        )
    return candidates[-1]


def _iter_log_records(path: Path):
    """Yield dict records from JSONL or plain Nautilus stdout logs."""
    import re

    plain_re = re.compile(
        r"^(?:\x1b\[[0-9;]*m)*(?P<ts>\d{4}-\d{2}-\d{2}T\S+)\s+"
        r"\[(?P<level>[A-Z]+)\]\s+(?P<trader>[^.]+)\.(?P<comp>[^:]+):\s*(?P<msg>.*)$"
    )
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                o = json.loads(line)
                if isinstance(o, dict) and (o.get("message") is not None or o.get("timestamp")):
                    yield o
                    continue
            except json.JSONDecodeError:
                pass
            m = plain_re.match(line)
            if not m:
                continue
            yield {
                "timestamp": m.group("ts"),
                "level": m.group("level"),
                "trader_id": m.group("trader"),
                "component": m.group("comp"),
                "message": m.group("msg"),
            }


def parse_log(path: Path, fx: float = FX_DEFAULT) -> DashboardSnapshot:
    submits: list[tuple[str, str, float, float, float]] = []
    fills: list[tuple[str, str, float, float, float, float, str]] = []
    bals: list[tuple[str, float]] = []
    nets: list[tuple[str, float]] = []
    closed: list[dict[str, Any]] = []

    as_ok = as_skip = err_2011 = err_other = spikes = maker = taker = 0
    first = last = None

    eq_by_hour: dict[str, float] = {}
    net_by_hour: dict[str, float] = {}
    sub_h: Counter[str] = Counter()
    fill_h: Counter[str] = Counter()
    sub_not_h: defaultdict[str, float] = defaultdict(float)
    fill_not_h: defaultdict[str, float] = defaultdict(float)
    fee_h: defaultdict[str, float] = defaultdict(float)

    for o in _iter_log_records(path):
        m = o.get("message", "")
        t = o.get("timestamp", "")
        comp = o.get("component", "")
        if not t:
            continue
        if first is None:
            first = t
        last = t

        if o.get("level") == "ERROR":
            if "-2011" in m:
                err_2011 += 1
            else:
                err_other += 1
        if "Skip AS param fit" in m:
            as_skip += 1
        if "AS params sigma=" in m and "Skip" not in m:
            as_ok += 1
        if "spike" in m.lower() and "halt" in m.lower():
            spikes += 1

        if comp == "ASQMarketMaking" and "SubmitOrder(order=LimitOrder" in m:
            x = PX_RE.search(m)
            if x:
                qty = float(x.group(2))
                px = float(x.group(3).replace("_", ""))
                n = qty * px
                submits.append((t, x.group(1), qty, px, n))
                h = _hour_cst(t)
                sub_h[h] += 1
                sub_not_h[h] += n

        if comp == "ASQMarketMaking" and "OrderFilled" in m:
            q = re.search(r"last_qty=([0-9.]+)", m)
            p = re.search(r"last_px=([0-9,_]+\.?[0-9]*)", m)
            s = re.search(r"order_side=(BUY|SELL)", m)
            c = re.search(r"commission=([0-9.]+)", m)
            liq = re.search(r"liquidity_side=(MAKER|TAKER)", m)
            if q and p and s:
                qty = float(q.group(1))
                px = float(p.group(1).replace("_", ""))
                fee = float(c.group(1)) if c else 0.0
                n = qty * px
                li = liq.group(1) if liq else "?"
                if li == "MAKER":
                    maker += 1
                elif li == "TAKER":
                    taker += 1
                fills.append((t, s.group(1), qty, px, n, fee, li))
                h = _hour_cst(t)
                fill_h[h] += 1
                fill_not_h[h] += n
                fee_h[h] += fee

        if "Updated AccountState" in m and "total=" in m:
            mm = re.search(r"total=([0-9_,.]+)", m)
            if mm:
                bal = float(mm.group(1).replace("_", ""))
                if bal > 0:
                    bals.append((t, bal))
                    eq_by_hour[_hour_cst(t)] = bal

        if "net_position=" in m:
            mm = re.search(r"net_position=([-0-9.]+)", m)
            if mm:
                v = float(mm.group(1))
                nets.append((t, v))
                net_by_hour[_hour_cst(t)] = v

        if comp == "ASQMarketMaking" and "PositionClosed" in m:
            peak = re.search(r"peak_qty=([0-9.]+)", m)
            ao = re.search(r"avg_px_open=([0-9.]+)", m)
            ac = re.search(r"avg_px_close=([0-9.]+)", m)
            rp = re.search(r"realized_pnl=([-0-9.]+) USDT", m)
            dur = re.search(r"duration_ns=([0-9]+)", m)
            entry = re.search(r"entry=(BUY|SELL)", m)
            if peak and ao and ac and rp and dur:
                peak_v = float(peak.group(1))
                ao_v = float(ao.group(1))
                ac_v = float(ac.group(1))
                ent = entry.group(1) if entry else "BUY"
                pp = (ac_v - ao_v) * peak_v if ent == "BUY" else (ao_v - ac_v) * peak_v
                closed.append(
                    {
                        "t_cst": _cst(t).strftime("%H:%M:%S"),
                        "entry": ent,
                        "peak": peak_v,
                        "open": ao_v,
                        "close": ac_v,
                        "dur_s": int(dur.group(1)) / 1e9,
                        "realized_usdt": float(rp.group(1)),
                        "price_pnl_usdt": pp,
                    }
                )

    if not first or not last or not bals:
        raise ValueError(f"insufficient data in {path}")

    h0 = _cst(first).replace(minute=0, second=0, microsecond=0)
    h1 = _cst(last).replace(minute=0, second=0, microsecond=0)
    hours: list[str] = []
    h = h0
    while h <= h1:
        hours.append(h.strftime("%H"))
        h += timedelta(hours=1)

    eq0 = next(b for _, b in bals if b > 0)
    eq1 = bals[-1][1]
    fees = sum(f[5] for f in fills)
    vol = sum(f[4] for f in fills)
    sub_n = sum(s[4] for s in submits)
    vol_eth = sum(f[2] for f in fills)
    runtime_h = (_parse_ts(last) - _parse_ts(first)).total_seconds() / 3600.0
    zero_fee = (eq1 - eq0) + fees

    def _ts(t: str) -> float:
        return _parse_ts(t).timestamp()

    cycles: list[list[tuple[str, str, float, float, float]]] = []
    cur: list[tuple[str, str, float, float, float]] = []
    for r in submits:
        if not cur:
            cur = [r]
            continue
        if _ts(r[0]) - _ts(cur[0][0]) < 0.05:
            cur.append(r)
        else:
            cycles.append(cur)
            cur = [r]
    if cur:
        cycles.append(cur)

    both = buy_o = sell_o = 0
    spreads: list[int] = []
    for c in cycles:
        buys = [x for x in c if x[1] == "BUY"]
        sells = [x for x in c if x[1] == "SELL"]
        if buys and sells:
            bid = max(x[3] for x in buys)
            ask = min(x[3] for x in sells)
            if bid < ask:
                both += 1
                spreads.append(round((ask - bid) / 0.01))
        elif buys:
            buy_o += 1
        elif sells:
            sell_o += 1

    spr_mode = Counter(spreads).most_common(1)[0][0] if spreads else 0
    durs = sorted(c["dur_s"] for c in closed)
    med = durs[len(durs) // 2] if durs else 0.0
    p90 = durs[int((len(durs) - 1) * 0.9)] if durs else 0.0

    eq_d: list[float] = []
    last_eq = eq0
    for hh in hours:
        if hh in eq_by_hour:
            last_eq = eq_by_hour[hh]
        eq_d.append((last_eq - eq0) * fx)

    net_arr: list[float] = []
    last_n = 0.0
    for hh in hours:
        if hh in net_by_hour:
            last_n = net_by_hour[hh]
        net_arr.append(last_n)

    recent = [
        {
            "t_cst": _cst(f[0]).strftime("%H:%M:%S"),
            "side": f[1],
            "qty": f[2],
            "px": f[3],
            "notional_usdt": f[4],
            "fee_usdt": f[5],
            "liq": f[6],
        }
        for f in fills[-20:]
    ][::-1]

    worst = sorted(closed, key=lambda c: c["realized_usdt"])[:8]
    for w in worst:
        w["realized_cny"] = w["realized_usdt"] * fx
        w["price_pnl_cny"] = w["price_pnl_usdt"] * fx

    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=CST).strftime("%Y-%m-%d %H:%M:%S")

    ticker = [
        f"ETHUSDT-PERP · BINANCE",
        f"SESSION {_cst(first).strftime('%m/%d %H:%M')}–{_cst(last).strftime('%H:%M')} CST",
        f"EQ {eq1 * fx:,.0f} CNY",
        f"Δ {(eq1 - eq0) * fx:+,.0f} CNY",
        f"FILL {vol * fx / 1e4:.1f}万 CNY",
        f"SUB {sub_n * fx / 1e4:.0f}万 CNY",
        f"NET {nets[-1][1] if nets else 0:+.3f} ETH",
        f"FEE {fees * fx:,.0f} CNY",
        f"FILL% {100 * vol / sub_n:.1f}%" if sub_n else "FILL% —",
        f"AS OK {as_ok}",
    ]

    return DashboardSnapshot(
        generated_at=datetime.now(tz=CST).strftime("%Y-%m-%d %H:%M:%S CST"),
        log_path=str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        log_mtime=mtime,
        fx_cny=fx,
        session_start_cst=_cst(first).strftime("%Y-%m-%d %H:%M"),
        session_end_cst=_cst(last).strftime("%Y-%m-%d %H:%M"),
        runtime_hours=round(runtime_h, 2),
        alive_hint="LIVE" if (datetime.now(tz=CST) - _cst(last)).total_seconds() < 120 else "STALE",
        equity_usdt=round(eq1, 2),
        equity_open_usdt=round(eq0, 2),
        equity_delta_usdt=round(eq1 - eq0, 2),
        equity_cny=round(eq1 * fx, 0),
        equity_open_cny=round(eq0 * fx, 0),
        equity_delta_cny=round((eq1 - eq0) * fx, 0),
        submit_notional_usdt=round(sub_n, 2),
        fill_notional_usdt=round(vol, 2),
        fill_notional_cny=round(vol * fx / 1e4, 1),
        submit_notional_cny=round(sub_n * fx / 1e4, 1),
        fill_rate_pct=round(100 * vol / sub_n, 1) if sub_n else 0.0,
        vol_eth=round(vol_eth, 2),
        fees_usdt=round(fees, 2),
        fees_cny=round(fees * fx, 0),
        price_pnl_usdt=round(zero_fee, 2),
        price_pnl_cny=round(zero_fee * fx, 0),
        fee_bps=round(fees / vol * 1e4, 2) if vol else 0.0,
        submit_count=len(submits),
        fill_count=len(fills),
        maker_count=maker,
        taker_count=taker,
        closed_count=len(closed),
        net_position_eth=round(nets[-1][1], 3) if nets else 0.0,
        as_ok=as_ok,
        as_skip=as_skip,
        err_2011=err_2011,
        err_other=err_other,
        spike_halts=spikes,
        quote_both=both,
        quote_sell_only=sell_o,
        quote_buy_only=buy_o,
        spread_ticks_mode=spr_mode,
        med_hold_s=round(med, 1),
        p90_hold_s=round(p90, 1),
        proj_fill_usdt_24h=round(vol / runtime_h * 24, 0) if runtime_h else 0,
        proj_fill_cny_24h=round(vol / runtime_h * 24 * fx / 1e4, 1) if runtime_h else 0,
        proj_sub_usdt_24h=round(sub_n / runtime_h * 24, 0) if runtime_h else 0,
        proj_sub_cny_24h=round(sub_n / runtime_h * 24 * fx / 1e4, 1) if runtime_h else 0,
        hours=hours,
        hourly_submit_wan_cny=[round(sub_not_h.get(h, 0) * fx / 1e4, 1) for h in hours],
        hourly_fill_wan_cny=[round(fill_not_h.get(h, 0) * fx / 1e4, 1) for h in hours],
        hourly_fee_cny=[round(fee_h.get(h, 0) * fx) for h in hours],
        hourly_equity_delta_cny=[round(x, 0) for x in eq_d],
        hourly_net_eth=[round(x, 3) for x in net_arr],
        hourly_submit_n=[sub_h.get(h, 0) for h in hours],
        hourly_fill_n=[fill_h.get(h, 0) for h in hours],
        recent_fills=recent,
        worst_closed=worst,
        ticker=ticker,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse ASQ-snap25 log to dashboard JSON")
    ap.add_argument("--log", type=Path, help="path to jsonl log")
    ap.add_argument("--fx", type=float, default=FX_DEFAULT)
    ap.add_argument("--out", type=Path, help="write snapshot json")
    args = ap.parse_args()
    path = args.log or find_latest_log()
    snap = parse_log(path, fx=args.fx)
    payload = asdict(snap)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
