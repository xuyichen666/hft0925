# features.py
import numpy as np
import pandas as pd
import scipy.optimize
from models import get_lgbm
from utils_v2 import agg_data


def get_market_speed(data, price_int):
    deltalist = np.linspace(price_int, price_int * 10, 10)
    lambdas = []
    for delta in deltalist:
        ask_hit = data[("ap", "max")].shift(-1) > (data[("ap", "last")] + delta)
        bid_hit = data[("bp", "min")].shift(-1) < (data[("bp", "last")] - delta)
        n_hit = (ask_hit | bid_hit).sum()
        lambdas.append(n_hit / len(data))
    lambdas = np.array(lambdas)
    valid = lambdas > 0
    if valid.sum() < 2:
        return 1.0, 0.1
    x = deltalist[valid]
    y = lambdas[valid]
    k, log_A = np.polyfit(x, np.log(y), 1)
    k = -k
    A = np.exp(log_A)
    if k <= 0 or not np.isfinite(A) or not np.isfinite(k):
        return 1.0, 0.1
    return float(A), float(k)


def get_params(data, price_int, time_step):
    data = data.copy(deep=True)
    prices = data

    min_index, max_index = prices.index[0], prices.index[-1]
    ave_time = (max_index - min_index) / max(len(prices), 1)
    if ave_time <= 0:
        ave_time = time_step

    log_ret = np.log(prices[("mid", "")]).diff().dropna()
    if len(log_ret) < 2:
        sigma = 0.01
    else:
        sigma = float(log_ret.std() * np.sqrt(24 * 60 * 1000 / ave_time))
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = 0.01

    midprices = prices[("mid", "")].values
    midprice_diff = np.diff(midprices, prepend=midprices[0])
    midprice_ratio = midprice_diff / midprices
    return_mean = float(np.mean(midprice_ratio))
    return_median = float(np.median(midprice_ratio))
    values, counts = np.unique(midprice_ratio, return_counts=True)
    return_mode = float(values[np.argmax(counts)])

    A, k = get_market_speed(prices, price_int)
    return sigma, A, k, midprice_ratio, return_mean, return_median, return_mode


def get_features(data):
    data = data.copy(deep=True)

    data["mid_price_1min"] = data[("mid", "")].shift(-60).ffill()
    data["ret_1min"] = data["mid_price_1min"] / data[("mid", "")] - 1

    feature_names = [
        "depth_imbalance", "book_slope_bid", "spread_bps",
        "depth_ratio_5_25_b",
        "ret_autocov_60", "net_add_imbalance", "amihud_60",
        "vpin_60", "ofi_norm_b", "buy_trade_ratio_b",
        "minute_of_day",
    ]

    # 兼容 MultiIndex 和字符串列名
    flat_cols = set()
    for c in data.columns:
        if isinstance(c, tuple):
            flat_cols.add(c[0])
        else:
            flat_cols.add(c)
    feature_names = [c for c in feature_names if c in flat_cols]
    print("可用因子:", feature_names)

    # 每列 NaN 数
    print("每列 NaN 数:")
    for c in feature_names:
        n_nan = data[c].isna().sum()
        print(f"  {c}: {n_nan}")

    # 只对 ret_1min dropna，因子列填 0
    if "ret_1min" in data.columns:
        data = data.dropna(subset=["ret_1min"])
    for c in feature_names:
        data[c] = data[c].fillna(0)

    print("处理完 shape:", data.shape)
    return data, feature_names


def train_model(data, time_step):
    data, feature_names = get_features(data)

    X = data[feature_names].values
    y = data["ret_1min"].values

    split_idx = int(len(data) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print("Shape of X_train:", X_train.shape)
    print("Shape of X_test :", X_test.shape)

    y_train = np.clip(y_train, -0.0005, 0.0005)
    y_test = np.clip(y_test, -0.0005, 0.0005)

    model, y_pred = get_lgbm(X_train, y_train, X_test, y_test)
    corr = np.corrcoef(y_test, y_pred)[0, 1]
    print(f"Correlation: {corr}")
    return model

