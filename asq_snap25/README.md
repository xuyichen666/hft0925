# asq_snap25 — ASQ restored on snap25 (ETH)

尽量对齐 `asq/aqsmodel.py` + `asq/models.py`，用币安 depth25+trades 训练冻结 fair，报价复用 `asq_tick.strategy`。

## 与原版 `asq` 对齐点

| 项 | `asq/aqsmodel.py` | 本包 |
|----|-------------------|------|
| bar | `trade_interval=1000` ms | 1s book snapshot |
| 标签 | `mid.shift(-60)` → `ret_1min` | `predict_secs=60` |
| clip | ±0.0005 | 同 |
| LGBM | `asq/models.py` | `get_lgbm_asq` |
| fair | `mid * (1 + pred)` | 同（`signal_threshold=0`） |
| AS γ | 0.01 | 同 |
| 报价 | fair ± AS，maker clamp | `ASQMarketMaking` |

差异：原版因子来自 bookTicker 聚合；这里用 snap25+trades 因子（同交易所 ETH）。语义对齐，特征集合不同。

## 训练（对齐版）

```bash
python -m model.train_asq_align
```

产出：`model/result/lgbm_eth_snap25.pkl`（meta 含 `asq_align: true`, `predict_secs: 60`）

研究用短 horizon 扫参仍可用：`python -m model.optimize_eth_snap25`（会覆盖 pkl，对齐实盘前请再跑 `train_asq_align`）。

## 本地 testnet

```bash
# 先停掉 asq_tick，避免抢同一 keys/IP
ASQ_INSTRUMENTS=ETHUSDT-PERP.BINANCE \
  caffeinate -dims python -m asq_snap25
```

Warmup ~360s（覆盖 aqsmodel 的 5min 成交滚动窗口）。

热更新：`asq_snap25/live_hot.json`（spread / requote / max_hold / clip）。
AS 默认已改为 `A=1.5,k=80,σ=0.005`（旧 `0.1/0.1` 会算出 ~900 tick 价差）；
intensity 稀疏时跳过空 δ、OLS 回退，并仍刷新 σ。

## 东京 mainnet

```bash
BINANCE_TESTNET=0 ASQ_INSTRUMENTS=ETHUSDT-PERP.BINANCE \
  python -m asq_snap25
```

不要把 API key 推进 Git。
