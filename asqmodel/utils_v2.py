# utils_v2.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.optimize


def agg_data(data: pd.DataFrame, time_step: int) -> pd.DataFrame:
    """
    把 1 秒 bar 数据聚合成 time_step 毫秒的 bar。
    data 需要包含 event_time（毫秒）和以下列：
      best_bid_price, best_bid_qty, best_ask_price, best_ask_qty,
      trade_volume, quantity, taker_buy_volume, taker_sell_volume,
      bid_amount, ask_amount, event_count
    输出 MultiIndex 列，和原代码兼容。
    """
    data = data.copy()

    if "event_time" not in data.columns:
        raise ValueError("data 必须包含 event_time 列（毫秒）")

    data["ms-index"] = data["event_time"] // time_step

    agg = data.groupby("ms-index").agg({
        "best_bid_price":   ["last", "max", "min"],
        "best_ask_price":   ["last", "max", "min"],
        "best_bid_qty":     ["last", "sum"],
        "best_ask_qty":     ["last", "sum"],
        "trade_volume":     ["sum"],
        "quantity":         ["sum"],
        "taker_buy_volume": ["sum"],
        "taker_sell_volume":["sum"],
        "bid_amount":       ["sum"],
        "ask_amount":       ["sum"],
        "event_count":      ["sum"],
    })

    agg.columns = [
        ("bp", "last"), ("bp", "max"), ("bp", "min"),
        ("ap", "last"), ("ap", "max"), ("ap", "min"),
        ("bv", "last"), ("bv", "sum"),
        ("av", "last"), ("av", "sum"),
        ("tv", "sum"), ("qty", "sum"),
        ("tbv", "sum"), ("tsv", "sum"),
        ("bamt", "sum"), ("aamt", "sum"), ("ecnt", "sum"),
    ]
    agg[("mid", "")] = (agg[("ap", "last")] + agg[("bp", "last")]) / 2
    agg[("ret", "")] = np.log(agg[("mid", "")]).diff()
    return agg


def get_bid_spread(sigma, A, k, gamma, q):
    """
    Avellaneda-Stoikov 买价偏移（相对 reservation price）。
    q > 0 时买价下移，抑制继续买入。
    """
    reservation_offset = -q * gamma * sigma ** 2
    optimal_spread = (1.0 / gamma) * np.log(1.0 + gamma / k)
    return max(0.0, optimal_spread / 2.0 + reservation_offset / 2.0)


def get_ask_spread(sigma, A, k, gamma, q):
    """
    Avellaneda-Stoikov 卖价偏移。
    q > 0 时卖价上移，抑制卖出。
    """
    reservation_offset = -q * gamma * sigma ** 2
    optimal_spread = (1.0 / gamma) * np.log(1.0 + gamma / k)
    return max(0.0, optimal_spread / 2.0 - reservation_offset / 2.0)


def plot_pnl(results_Q, title="PnL"):
    pnl  = np.concatenate(results_Q[0], axis=0)
    x    = np.concatenate(results_Q[1], axis=0)
    q    = np.concatenate(results_Q[2], axis=0)
    fees = np.concatenate(results_Q[3], axis=0)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    axes[0].plot(pnl - fees, label="PnL (with fee)")
    axes[0].plot(pnl, label="PnL (without fee)")
    axes[0].set_title(f"{title} — PnL")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(q, label="Inventory q", color="orange")
    axes[1].set_title("Inventory")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(fees, label="Fees", color="red")
    axes[2].set_title("Cumulative Fees")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()