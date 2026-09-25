import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from utils_v2 import agg_data, get_bid_spread, get_ask_spread, plot_pnl
import scipy
import seaborn as sns
from models import *


# ===== 函数：计算市价/taper订单的到达速度 =====
def get_market_speed(data: pd.DataFrame, price_int: float):
    """
    该函数用于计算市价/taper订单的到达速度，是在下一个cell的函数get_params中被调用的
    该函数中max和min是在下一个函数get_params中通过groupby计算出来的，不是数据源自带的
    如果单独使用这个函数，需要先调用groupby计算出来max和min
    """
    delatlist = np.linspace(price_int, price_int * 10, 10)
    deltatict = {}

    # 分别计算在1-10个ticksize上的市价单到达速度
    for delta in delatlist:
        price_interval = delta
        ask_limit_order_hit = data[('ap', 'max')].shift(-1) > (data[('ap', 'last')] + price_interval)
        bid_limit_order_hit = data[('bp', 'min')].shift(-1) < (data[('bp', 'last')] - price_interval)
        limit_order_hit = (ask_limit_order_hit | bid_limit_order_hit).astype(int)
        deltas = pd.Series(limit_order_hit[limit_order_hit == 1].index).diff().apply(lambda x: x / 10)
        deltatict[delta] = deltas

    # 这里的max和min是在下一个函数get_params中通过groupby计算出来的，不是数据源自带的
    lambdas = pd.DataFrame([delta / deltatict[delta].mean() for delta in deltatict.keys()],
                           columns=['lambda_delta'], index=deltatict.keys())
    lambdas.index.name = 'delta'

    # 市价单到达速度的方程是 y = A * exp(-k * x)，其中x是距离中间价的tick_size数量，范围是1-10的整数；y是在每个x的位置上的成交次数；A、k是我们
    def exp_fit(x, a, b):
        return a * np.exp(-b * x)

    paramsB, cv = scipy.optimize.curve_fit(exp_fit, np.array(lambdas.index), np.array(lambdas['lambda_delta'].values))
    A, k = paramsB
    # curve_fit(function, xdata, ydata)，其中function是拟合的函数，xdata是自变量，ydata是因变量，输出结果是function的参数
    return A, k


# ===== 函数：获取市场参数 =====
def get_params(data: pd.DataFrame, price_int: float, time_step: int):
    data = data.copy(deep=True)
    data = data.rename(columns={
        'best_bid_price': 'bp',
        'best_bid_qty': 'bv',
        'best_ask_price': 'ap',
        'best_ask_qty': 'av',
        'event_time': 'time'
    })
    # 1. 按照time_step的频率把数据采样起来（相当于订单的更新的频率不能太高）
    data['ms-index'] = data['time'] // time_step
    prices = data.groupby('ms-index').agg({
        'ap': ['last', 'max', 'min'],
        'bp': ['last', 'max', 'min']
    })

    # 2. 估计当前每条数据平均多少时间，用于估计交易时间
    min_index, max_index = prices.index[0], prices.index[prices.shape[0] - 1]
    ave_time = time_step * (max_index - min_index) / prices.shape[0]

    # 3. 波动率
    prices[('mid', '')] = (prices[('ap', 'last')] + prices[('bp', 'last')]) / 2
    # 这里可以修改，修改为计算自己的price model，加入对不均衡、成交量等因素的考虑
    sigma = np.log(prices[('mid', '')]).diff().std() * np.sqrt(24 * 60 * 1000 / ave_time)

    # 4. 计算每2个时间间隔的收益率
    midprices = prices[('mid', '')].values
    midprice_diff = np.diff(midprices, prepend=midprices[0])
    midprice_ratio = midprice_diff / midprices
    return_mean = np.mean(midprice_ratio)
    return_median = np.median(midprice_ratio)
    (values, counts) = np.unique(midprice_ratio, return_counts=True)
    return_mode = values[np.argmax(counts)]

    # 5. 中位值到达速率参数，调用上一个cell的get_market_speed函数
    A, k = get_market_speed(prices, price_int)

    return sigma, A, k, midprice_ratio, return_mean, return_median, return_mode


# ===== 函数：获取特征 =====
def get_features(data: pd.DataFrame):
    data = data.copy(deep=True)
    # 0. Generate prediction target
    data['mid_price_1min'] = data['mid_price'].shift(-60)
    data['mid_price_1min'] = data['mid_price_1min'].fillna(method='ffill')
    data['ret_1min'] = data['mid_price_1min'] / data['mid_price'] - 1
    # add constant
    data['const'] = 1

    # Orderbook features:
    # 1. Volume Imbalance
    data['vol_imb'] = (data[('bv', 'sum')] - data[('av', 'sum')]) / (data[('bv', 'sum')] + data[('av', 'sum')])
    # 2. VWAP
    data['vwap'] = (data[('ap', 'last')] * data[('av', 'sum')] + data[('bp', 'last')] * data[('bv', 'sum')]) / (
                data[('av', 'sum')] + data[('bv', 'sum')])
    # 3. Spread
    data['spread'] = data[('ap', 'last')] - data[('bp', 'last')]

    # 4. MACD
    data['ema_120'] = data['ret'].ewm(span=120).mean()
    data['ema_360'] = data['ret'].ewm(span=360).mean()
    data['macd'] = data['ema_120'] - data['ema_360']

    # 5. RSI (简化版)
    data['delta'] = data['ret'].diff()
    data['up'] = data['delta'].clip(lower=0)
    data['down'] = -data['delta'].clip(upper=0)
    data['ema_up'] = data['up'].ewm(com=13, adjust=False).mean()
    data['ema_down'] = data['down'].ewm(com=13, adjust=False).mean()
    data['rs'] = data['ema_up'] / data['ema_down']
    data['rsi'] = 100 - (100 / (1 + data['rs']))

    # 后续特征
    data['Advanced0BIT'] = (data['bid_volume_change'] - data['ask_volume_change']) / (
                data['bid_volume_change'] + data['ask_volume_change'])
    data['VolumeChangeRatio'] = data['bid_volume_change'] / data['ask_volume_change']
    data['Adv0BIRatio'] = (data['bid_volume_change'] - data['ask_volume_change']) / (
                data[('bv', 'sum')] + data[('av', 'sum')])
    data['Adv0BIRelative'] = (data['bid_volume_change'] - data['ask_volume_change']) / (
                data[('bv', 'sum')] - data[('av', 'sum')])
    data['BuyVolumeChangeRatio'] = data['bid_volume_change'] / (data[('bv', 'sum')] + data[('av', 'sum')])

    # Trade Features:
    data['AvgBuyPrice'] = data['taker_buy_volume'] / data['taker_buy_quantity']
    data['AvgSellPrice'] = data['taker_sell_volume'] / data['taker_sell_quantity']
    data['AvgTradePrice'] = data['trade_volume'] / data['quantity']

    data['TradeVolumeSum_1min'] = data['trade_volume'].rolling(window=60).sum()
    data['TradeVolumeSum_5min'] = data['trade_volume'].rolling(window=60 * 5).sum()
    data['taker_buy_volume_1min'] = data['taker_buy_volume'].rolling(window=60).sum()
    data['taker_buy_volume_5min'] = data['taker_buy_volume'].rolling(window=60 * 5).sum()
    data['taker_sell_volume_1min'] = data['taker_sell_volume'].rolling(window=60).sum()
    data['taker_sell_volume_5min'] = data['taker_sell_volume'].rolling(window=60 * 5).sum()

    data['GrossBuyRatio'] = data['taker_buy_volume'] / data['trade_volume']
    data['GBR_1min'] = data['taker_buy_volume_1min'] / data['TradeVolumeSum_1min']
    data['GBR_5min'] = data['taker_buy_volume_5min'] / data['TradeVolumeSum_5min']

    data['NetBuyRatio'] = (data['taker_buy_volume'] - data['taker_sell_volume']) / data['trade_volume']
    data['NBR_1min'] = (data['taker_buy_volume_1min'] - data['taker_sell_volume_1min']) / data['TradeVolumeSum_1min']
    data['NBR_5min'] = (data['taker_buy_volume_5min'] - data['taker_sell_volume_5min']) / data['TradeVolumeSum_5min']

    data['taker_buy_volume_squared'] = data['taker_buy_volume'] ** 2
    data['BCT_1min'] = data['taker_buy_volume_squared'].rolling(window=60).sum() / (data['TradeVolumeSum_1min'] ** 2)
    data['BCT_5min'] = data['taker_buy_volume_squared'].rolling(window=60 * 5).sum() / (
                data['TradeVolumeSum_5min'] ** 2)
    data['BCS_1min'] = data['taker_buy_volume_squared'].rolling(window=60).sum() / (data['taker_buy_volume_1min'] ** 2)
    data['BCS_5min'] = data['taker_buy_volume_squared'].rolling(window=60 * 5).sum() / (
                data['taker_buy_volume_5min'] ** 2)

    data['taker_sell_volume_squared'] = data['taker_sell_volume'] ** 2
    data['SCT_1min'] = data['taker_sell_volume_squared'].rolling(window=60).sum() / (data['TradeVolumeSum_1min'] ** 2)
    data['SCT_5min'] = data['taker_sell_volume_squared'].rolling(window=60 * 5).sum() / (
                data['TradeVolumeSum_5min'] ** 2)
    data['SCS_1min'] = data['taker_sell_volume_squared'].rolling(window=60).sum() / (
                data['taker_sell_volume_1min'] ** 2)
    data['SCS_5min'] = data['taker_sell_volume_squared'].rolling(window=60 * 5).sum() / (
                data['taker_sell_volume_5min'] ** 2)

    data['TCSum_1min'] = data['BCT_1min'] + data['SCT_1min']
    data['TCSum_5min'] = data['BCT_5min'] + data['SCT_5min']
    data['TCDiff_1min'] = data['BCT_1min'] - data['SCT_1min']
    data['TCDiff_5min'] = data['BCT_5min'] - data['SCT_5min']
    data['SCSum_1min'] = data['BCS_1min'] + data['SCS_1min']
    data['SCSum_5min'] = data['BCS_5min'] + data['SCS_5min']
    data['SCDiff_1min'] = data['BCS_1min'] - data['SCS_1min']
    data['SCDiff_5min'] = data['BCS_5min'] - data['SCS_5min']
    data['TCI_1min'] = data['TCDiff_1min'] / data['TCSum_1min']
    data['TCI_5min'] = data['TCDiff_5min'] / data['TCSum_5min']
    data['SCI_1min'] = data['SCDiff_1min'] / data['SCSum_1min']
    data['SCI_5min'] = data['SCDiff_5min'] / data['SCSum_5min']

    data['GBS_1min'] = data['taker_buy_volume'].rolling(window=60).mean() / data['taker_buy_volume'].rolling(
        window=60).std()
    data['GBS_5min'] = data['taker_buy_volume'].rolling(window=60 * 5).mean() / data['taker_buy_volume'].rolling(
        window=60 * 5).std()

    data['Net_buy_volume'] = data['taker_buy_volume'] - data['taker_sell_volume']
    data['NBS_1min'] = data['Net_buy_volume'].rolling(window=60).mean() / data['Net_buy_volume'].rolling(
        window=60).std()
    data['NBS_5min'] = data['Net_buy_volume'].rolling(window=60 * 5).mean() / data['Net_buy_volume'].rolling(
        window=60 * 5).std()

    # drop_nan
    data = data.dropna()
    data = data.drop(columns=['ema_120', 'ema_360', 'delta', 'up', 'down', 'ema_up', 'ema_down', 'rs',
                              'mp_diff_1min', 'mp_diff_5min', 'mp_ret_1min', 'mp_ret_5min',
                              'bid_sub_price', 'ask_sub_price', 'bid_sub_volume', 'ask_sub_volume',
                              'bid_volume_change', 'ask_volume_change',
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   'taker_buy_volume_1min', 'taker_buy_volume_5min',
                              'taker_sell_volume_1min', 'taker_sell_volume_5min',
                              'TradeVolumeSum_1min', 'TradeVolumeSum_5min',
                              'taker_buy_volume_squared', 'taker_sell_volume', 'Net_buy_volume'])

    feature_names = ['const', 'vol_imb', 'vwap', 'spread', 'macd', 'rsi', 'std', 'mom', 'adj1', 'slope',
                     'mp_ret_over_max_diff_1min', 'mp_ret_over_max_diff_5min', 'Advanced0BIT',
                     'VolumeChangeRatio', 'Adv0BIRatio', 'Adv0BIRelative', 'BuyVolumeChangeRatio',
                     'GrossBuyRatio', 'GBR_1min', 'GBR_5min', 'NetBuyRatio', 'NBR_1min', 'NBR_5min',
                     'BCT_1min', 'BCT_5min', 'SCT_1min', 'SCT_5min', 'BCS_1min', 'BCS_5min', 'SCS_1min',
                     'SCS_5min', 'TCSum_1min', 'TCSum_5min', 'TCDiff_1min', 'TCDiff_5min', 'SCSum_1min',
                     'SCSum_5min', 'SCDiff_1min', 'SCDiff_5min', 'TCI_1min', 'TCI_5min', 'SCI_1min',
                     'SCI_5min', 'GBS_1min', 'GBS_5min', 'NBS_1min', 'NBS_5min']

    return data, feature_names


# ===== 函数：训练模型 =====
def train_model(data: pd.DataFrame, time_step: int):
    """
    该函数用于训练模型
    """
    data = data.copy(deep=True)

    # 1. 按照time_step的频率把数据合并起来，并且计算features
    data = agg_data(data, time_step)
    data, feature_names = get_features(data)

    X = data[feature_names].values
    y = data['ret_1min'].values

    # 2. 划分训练集和测试集
    split_idx = int(len(data) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    print("Shape of X_train: ", X_train.shape)
    print("Shape of X_test: ", X_test.shape)

    # 3. clip prediction targets
    y_train = np.clip(y_train, -0.0005, 0.0005)
    y_test = np.clip(y_test, -0.0005, 0.0005)

    # 4. Train model
    model, y_pred = get_lgbm(X_train, y_train, X_test, y_test)
    corr = np.corrcoef(y_test, y_pred)[0, 1]
    print(f'Correlation: {corr}')
    return model


# ===== 函数：策略回测（evaluation_Q_maker）=====
def evaluation_Q_maker(data: pd.DataFrame, price_int: float, time_step: int, params: dict):
    """
    输入是一段历史成交的数据，来进行策略回溯
    并没有加入库存量相关的交易规则
    只使用了best bid and ask进行回溯，没有考虑订单在订单薄上的位置
    """
    data = data.copy(deep=True)

    # 1. 按照time_step的频率把数据合并起来，并且计算features
    prices = agg_data(data, time_step)
    prices, feature_names = get_features(prices)

    # 2. Import model and predict
    model = params['model']
    X = prices[feature_names].values
    pred = model.predict(X)
    print("Correlation out-of-sample:", np.corrcoef(prices['ret_1min'], pred)[0, 1])
    prices['mid_pred'] = prices['mid_price'] * (pred + 1)

    # 3. 回溯
    N = prices.shape[0]
    q = np.array([params['q']] + [0] * (N - 1))
    x = np.array([params['x']] + [0] * (N - 1), dtype=float)
    pnl = np.array([params['pnl']] + [0] * (N - 1), dtype=float)
    fees = np.array([params['fees']] + [0] * (N - 1), dtype=float)
    bid_spread_paper = np.array([params['bid_spread_paper']] + [0] * (N - 1), dtype=float)
    ask_spread_paper = np.array([params['ask_spread_paper']] + [0] * (N - 1), dtype=float)
    bid_spread_real = np.array([params['bid_spread_real']] + [0] * (N - 1), dtype=float)
    ask_spread_real = np.array([params['ask_spread_real']] + [0] * (N - 1), dtype=float)
    ra = np.zeros(N)
    rb = np.zeros(N)

    sigma = params['sigma']
    A = params['A']
    k = params['k']
    gamma = params['gamma']
    Q = params['Q']
    fee_rate = params['fee_rate']

    for i in tqdm(range(N - 1)):
        mid_price = prices['mid_pred'].iloc[i]
        bid_spread_paper[i] = get_bid_spread(sigma, A, k, gamma, q[i])
        ask_spread_paper[i] = get_ask_spread(sigma, A, k, gamma, q[i])
        ra[i] = mid_price + ask_spread_paper[i]
        rb[i] = mid_price - bid_spread_paper[i]

        # 限制了价格一定是挂单方的价格，不会变成低单
        ra[i] = max(prices[('ap', 'last')].iloc[i], np.floor(ra[i] * (1 / price_int)) * price_int)
        rb[i] = min(prices[('bp', 'last')].iloc[i], np.ceil(rb[i] * (1 / price_int)) * price_int)
        bid_spread_real[i] = mid_price - rb[i]
        ask_spread_real[i] = ra[i] - mid_price

        buy = 0
        sell = 0

        if q[i] >= -Q and prices[('ap', 'max')].iloc[i + 1] > ra[i]:
            sell = 1

        if q[i] <= Q and prices[('bp', 'min')].iloc[i + 1] < rb[i]:
            buy = 1

        q[i + 1] = q[i] + buy - sell
        x[i + 1] = x[i] + sell * ra[i] - buy * rb[i]
        pnl[i + 1] = x[i + 1] + q[i + 1] * prices['mid_price'].iloc[i + 1]
        fees[i + 1] = fees[i] + sell * ra[i] * fee_rate + buy * rb[i] * fee_rate

    total_spread_paper = bid_spread_paper + ask_spread_paper
    total_spread_real = bid_spread_real + ask_spread_real

    return pnl, x, q, fees, bid_spread_paper, ask_spread_paper, total_spread_paper, bid_spread_real, ask_spread_real, total_spread_real


# ===== 主回测函数 =====
def back_test_Q():
    fee_rate = 1.4e-4  # 1.4/10000
    trade_interval = 1000  # 毫秒
    gamma = 0.01
    split_date = '2023-10-11'  # 需要根据实际情况定义

    price_int_dict = {'LDOBUSD': 0.0001, 'LTCBUSD': 0.01, 'BTCBUSD': 0.10, 'ETHBUSD': 0.01, 'ETHUSDT': 0.01}
    price_int = price_int_dict['ETHUSDT']

    data = pd.read_pickle('ETHUSDT-bookTicker-2023-10-pickle')
    trade_dates = sorted(list(data['trade_date'].unique()))

    Q = 10

    last_q = 0
    last_x = 0
    last_pnl = 0
    last_fees = 0
    last_bid_spread_paper = 0
    last_ask_spread_paper = 0
    last_total_spread_paper = 0
    last_bid_spread_real = 0
    last_ask_spread_real = 0
    last_total_spread_real = 0

    # 注意：需要10个列表来存储10个返回值
    results_Q = [[], [], [], [], [], [], [], [], [], []]

    valid_data = data[data['trade_date'] <= split_date]
    test_data = data[data['trade_date'] > split_date]
    print("Valid sample: ", valid_data.shape[0])
    print("Test sample: ", test_data.shape[0])

    sigma, A, k, midprice_ratio, return_mean, return_median, return_mode = get_params(
        valid_data, price_int=price_int, time_step=trade_interval
    )

    params = {
        'q': last_q,
        'x': last_x,
        'pnl': last_pnl,
        'sigma': sigma,
        'A': A,
        'k': k,
        'gamma': gamma,
        'fees': last_fees,
        'fee_rate': fee_rate,
        'Q': Q,
        'bid_spread_paper': last_bid_spread_paper,
        'ask_spread_paper': last_ask_spread_paper,
        'total_spread_paper': last_total_spread_paper,
        'bid_spread_real': last_bid_spread_real,
        'ask_spread_real': last_ask_spread_real,
        'total_spread_real': last_total_spread_real
    }

    # Train and test the model
    model = train_model(valid_data, time_step=trade_interval)
    params['model'] = model

    pnl, x, q, fees, bid_spread_paper, ask_spread_paper, total_spread_paper, bid_spread_real, ask_spread_real, total_spread_real = evaluation_Q_maker(
        test_data, price_int=price_int, time_step=trade_interval, params=params
    )

    # 存储结果
    results_Q[0].append(pnl)
    results_Q[1].append(x)
    results_Q[2].append(q)
    results_Q[3].append(fees)
    results_Q[4].append(bid_spread_paper)
    results_Q[5].append(ask_spread_paper)
    results_Q[6].append(total_spread_paper)
    results_Q[7].append(bid_spread_real)
    results_Q[8].append(ask_spread_real)
    results_Q[9].append(total_spread_real)

    # 打印 PnL
    pnl_with_fee = np.concatenate(results_Q[0], axis=0) + np.concatenate(results_Q[3], axis=0)
    pnl_fee = np.concatenate(results_Q[3], axis=0)
    pnl_without_fee = np.concatenate(results_Q[0], axis=0)
    print(f'pnl_with_fee: {pnl_with_fee[-1]}, pnl_without_fee: {pnl_without_fee[-1]}, pnl_fee: {pnl_fee[-1]}')
    print(f'pnl_with_fee/pnl_fee: {pnl_with_fee[-1] / pnl_fee[-1] if pnl_fee[-1] != 0 else 0}')

    plot_pnl(results_Q, title='ETHUSDT')


if __name__ == '__main__':
    back_test_Q()