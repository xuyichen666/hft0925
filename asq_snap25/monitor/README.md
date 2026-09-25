# ASQ Command Monitor

Institutional-style live dashboard for `asq_snap25` session logs.

## Features

- Auto-detects latest `logs/asq-snap25-testnet-*.jsonl`
- Refreshes every 5 seconds
- **Full-bleed 3D Volume Landscape** (Three.js): submit vs fill towers + particles
- Hero KPIs: 挂单额 / 成交额 / 转化率 / ETH volume
- Equity path, fees, fills, risk ops

## Quick start

```bash
cd /Users/xqm/Downloads/Nautilus_Pair_Trading_Jerry-main
python -m asq_snap25.monitor.server
```

Open: **http://127.0.0.1:8765**

## Options

```bash
python -m asq_snap25.monitor.server --log logs/asq-snap25-testnet-....jsonl
python -m asq_snap25.monitor.server --port 8888 --fx 6.77
```

## API

`GET /api/snapshot?fx=6.77` → JSON metrics from log.
