# backtest.py
import numpy as np
import pandas as pd
from tqdm import tqdm
from utils_v2 import agg_data, get_bid_spread, get_ask_spread, plot_pnl
from features import get_params, get_features, train_model


def evaluation_Q_maker(data: pd.DataFrame, price_int: float, time_step: int, params: dict):
    """
    做市商回测。
    输入是 1 秒 bar（或 agg_data 聚合后的 bar），包含：
      ('ap','last'), ('ap','max'), ('ap','min'),
      ('bp','last'), ('bp','max'), ('bp','min'),
      ('mid','')
    """
    data = data.copy(deep=True)
    prices = data
    prices, feature_names = get_features(prices)

    model = params["model"]
    X = prices[feature_names].values
    pred = model.predict(X)
    print("Correlation out-of-sample:", np.corrcoef(prices["ret_1min"], pred)[0, 1])
    prices["mid_pred"] = prices[("mid", "")] * (pred + 1)

    N = prices.shape[0]
    q  = np.zeros(N); q[0] = params["q"]
    x  = np.zeros(N); x[0] = params["x"]
    pnl = np.zeros(N); pnl[0] = params["pnl"]
    fees = np.zeros(N); fees[0] = params["fees"]
    bid_spread_paper = np.zeros(N)
    ask_spread_paper = np.zeros(N)
    bid_spread_real  = np.zeros(N)
    ask_spread_real  = np.zeros(N)

    sigma    = params["sigma"]
    A        = params["A"]
    k        = params["k"]
    gamma    = params["gamma"]
    Q        = params["Q"]
    fee_rate = params["fee_rate"]

    for i in tqdm(range(N - 1)):
        mid_price = prices["mid_pred"].iloc[i]

        bid_spread_paper[i] = get_bid_spread(sigma, A, k, gamma, q[i])
        ask_spread_paper[i] = get_ask_spread(sigma, A, k, gamma, q[i])

        ra = mid_price + ask_spread_paper[i]
        rb = mid_price - bid_spread_paper[i]

        # 限制价格不会穿过对手价
        ra = max(prices[("ap", "last")].iloc[i], np.floor(ra / price_int) * price_int)
        rb = min(prices[("bp", "last")].iloc[i], np.ceil(rb / price_int) * price_int)

        bid_spread_real[i] = mid_price - rb
        ask_spread_real[i] = ra - mid_price

        buy = 0
        sell = 0

        if q[i] >= -Q and prices[("ap", "max")].iloc[i + 1] > ra:
            sell = 1
        if q[i] <= Q and prices[("bp", "min")].iloc[i + 1] < rb:
            buy = 1

        q[i + 1] = q[i] + buy - sell
        x[i + 1] = x[i] + sell * ra - buy * rb
        pnl[i + 1] = x[i + 1] + q[i + 1] * prices[("mid", "")].iloc[i + 1]
        fees[i + 1] = fees[i] + sell * ra * fee_rate + buy * rb * fee_rate

    total_spread_paper = bid_spread_paper + ask_spread_paper
    total_spread_real  = bid_spread_real  + ask_spread_real

    return (pnl, x, q, fees,
            bid_spread_paper, ask_spread_paper, total_spread_paper,
            bid_spread_real,  ask_spread_real,  total_spread_real)


def back_test_Q(data: pd.DataFrame, price_int: float, time_step: int,
                split_ratio: float = 0.7, gamma: float = 0.01,
                Q: int = 10, fee_rate: float = 1.4e-4):
    """
    主回测函数。
    data: 已经带 ('ap','last') 等列的 1 秒 bar。
    """
    n = len(data)
    split_idx = int(n * split_ratio)
    valid_data = data.iloc[:split_idx]
    test_data  = data.iloc[split_idx:]

    print("Valid sample:", valid_data.shape[0])
    print("Test sample :", test_data.shape[0])

    sigma, A, k, midprice_ratio, return_mean, return_median, return_mode = get_params(
        valid_data, price_int=price_int, time_step=time_step
    )
    print(f"sigma={sigma:.6f}, A={A:.4f}, k={k:.4f}")

    model = train_model(valid_data, time_step=time_step)

    params = {
        "q": 0, "x": 0, "pnl": 0,
        "sigma": sigma, "A": A, "k": k,
        "gamma": gamma, "fees": 0,
        "fee_rate": fee_rate, "Q": Q,
        "model": model,
        "bid_spread_paper": 0, "ask_spread_paper": 0, "total_spread_paper": 0,
        "bid_spread_real": 0, "ask_spread_real": 0, "total_spread_real": 0,
    }

    results = evaluation_Q_maker(test_data, price_int=price_int,
                                 time_step=time_step, params=params)

    pnl_with_fee    = results[0] + results[3]
    pnl_without_fee = results[0]
    pnl_fee         = results[3]

    print(f"pnl_with_fee   : {pnl_with_fee[-1]:.6f}")
    print(f"pnl_without_fee: {pnl_without_fee[-1]:.6f}")
    print(f"pnl_fee        : {pnl_fee[-1]:.6f}")

    plot_pnl(results, title="ETHUSDT")
    return results