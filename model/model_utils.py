import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 
import joblib
from example.model.models import *

def calculate_features(df) :
    # 1. calculate obi (orderbook imbalance)
    # 生成 bid 和 ask 的价格与数量列名
    bid_price_cols = [f'bids[{i}].price' for i in range (25)]
    bid_amount_cols = [f'bids[{i}].amount' for i in range (25)]
    ask_price_cols = [f'asks[{i}].price' for i in range (25)]
    ask_amount_cols = [f'asks[{i}].amount' for i in range (25)]
    
    bid_prices = df[bid_price_cols].values
    bid_amounts = df[bid_amount_cols].values
    ask_prices = df[ask_price_cols].values
    ask_amounts = df[ask_amount_cols]. values
    
    bid_sum = np.sum(bid_prices * bid_amounts, axis=1)
    ask_sum = np.sum(ask_prices * ask_amounts, axis=1)
    obi = (bid_sum - ask_sum) / (bid_sum + ask_sum)
    df[ 'obi' ] = obi
    # 计算累计委托量
    bid_cumsum = np.cumsum(bid_amounts, axis=1)
    ask_cumsum = np.cumsum(ask_amounts, axis=1)
    # 计算占比
    bid_ratio = bid_cumsum / bid_cumsum[:, [-1]] # 使用numpy 的广播
    ask_ratio = ask_cumsum / ask_cumsum[:, [-1]]
    
    # 计算斜率
    bid_slope = np.array([np.polyfit(bid_ratio[i], bid_prices[i],
    1)[0] for i in range(len(df))])
    ask_slope = np.array([np.polyfit(ask_ratio[i], ask_prices[i],
    1)[0] for i in range(len(df))])
    # 取买方斜率的负值
    bid_slope = -bid_slope
    df['slope_a'] = ask_slope
    df['slope_b'] = bid_slope
    df['slope_diff'] = df['slope_a'] - df['slope_b']
       
    # 高低档分别计算s1ope
    # 定义低档和高档的索列
    x = 5
    low_idx = slice(0, x) # python的切片是基于口的索引，1-12档实际是0-11
    high_idx = slice(x, 25) # 13-25档是12-24
    
    # 计算低档和高档斜率
    bid_low_slope = np.array([np.polyfit(bid_ratio[i, low_idx], bid_prices[i, low_idx], 1)[0] for i in range(len(df))])
    bid_high_slope = np.array([np.polyfit(bid_ratio[i, high_idx], bid_prices[i, high_idx], 1)[0] for i in range(len(df))])
    ask_low_slope = np.array([np.polyfit(ask_ratio[i, low_idx], ask_prices[i, low_idx], 1)[0] for i in range(len(df))])
    ask_high_slope = np.array([np.polyfit(ask_ratio[i, high_idx], ask_prices[i, high_idx],1)[0] for i in range(len(df))])
    
    # 取买方斜率的负值
    bid_low_slope = -bid_low_slope
    bid_high_slope = -bid_high_slope
    
    # 计算斜率失衡
    slope_imbalance_low = (ask_low_slope - bid_low_slope) / (bid_low_slope + ask_low_slope)
    slope_imbalance_high = (ask_high_slope - bid_high_slope) / (bid_high_slope + ask_high_slope)
    # 将结果存储到DataFrame
    df['slope_a_low'] = ask_low_slope
    df['slope_b_low'] = bid_low_slope
    df['slope_a_high'] = ask_high_slope
    df['slope_b_high'] = bid_high_slope
    df['slope_imbalance_low'] = slope_imbalance_low
    df['slope_imbalance_high'] = slope_imbalance_high
    df['slope_diff_low'] = df['slope_a_low'] - df['slope_b_low']
    df['slope_diff_high'] = df['slope_a_high'] - df['slope_b_high']
    # slope需要每一档的价格和到该档位累积的订单数量/金额，即y是价格，x是资金量
    return df

def agg_data_snap_25(data: pd.DataFrame, time_step: int, use_trade_data: bool = False):
    data = data.copy(deep=True)
    data = data.rename(columns={
        'bids[0].price': 'bp',
        'bids[0].amount': 'bv',
        'asks[0].price': 'ap',
        'asks[0].amount': 'av',
        'timestamp': 'time',
    })
    time_step = time_step * 1000
    data['ms-index'] = data['time'] // time_step
    # 实际上这里得到的时间是秒，不是毫秒
    if use_trade_data:
        data.drop(columns=['update_id', 'agg_trade_id', 'first_trade_id', 'last_trade_id', 'is_buyer_maker', 'transact_time'], inplace=True)
        data = data.groupby('ms-index').agg({
            'ap': ['last','max','min'],
            'bp': ['last','max','min'],
            'av': ['last','max','min','sum'],
            'bv':  ['last','max','min','sum'],
            'trade_price': ['first','last','max','min'],
            'quantity': 'sum',
            'trade_volume': 'sum',
            'taker_sell_volume': 'sum',
            'taker_buy_volume': 'sum',
            'taker_buy_quantity': 'sum',
            'taker_sell_quantity': 'sum',
            'trade_num': 'sum',
            'taker_buy_num': 'sum',
            'taker_sell_num': 'sum'
            }) # 将data按time_step的时间间隔合并分组成一个新的名为data的dataframe
    else:
        data.drop(columns=['exchange', 'symbol', 'local_timestamp', 'time'], inplace=True)
        columns_to_drop = [f'bids[{i}].price' for i in range(1,25)] + [f'bids[{i}].amount' for i in range(1,25)] + [f'asks[{i}].price' for i in range(1,25)] + [f'asks[{i}].amount' for i in range(1,25)]
        data.drop(columns=columns_to_drop, inplace=True)
        data = data.groupby('ms-index').agg({
            'ap': ['last','max','min'],
            'bp': ['last','max','min'],
            'av': ['last','max','min','sum'],
            'bv':  ['last','max','min','sum'],
            'obi': 'last',
            'slope_a': ['last', 'mean'],
            'slope_b': ['last', 'mean'],
            'slope_diff': ['last', 'mean'],
            'slope_a_low': ['last', 'mean'],
            'slope_b_low': ['last', 'mean'],
            'slope_a_high': ['last', 'mean'],
            'slope_b_high': ['last', 'mean'],
            'slope_imbalance_low': ['last', 'mean'],
            'slope_imbalance_high': ['last', 'mean'],
            'slope_diff_low': ['last', 'mean'],
            'slope_diff_high': ['last', 'mean'],
        }) # 将data按time_step的时间间隔合并分组成一个新的名为data的dataframe

    # generate prediction target
    # data['datetime"J = pd.to_datetime(data['ms-index'J, unit='s')
    data['mid_price'] = (data['ap']['last'] + data['bp']['last']) / 2
    data['ret'] = data['mid_price'].pct_change().fillna(0)
                       
    # drop columns for multiindex, first change multi index to single index
    data.columns = ['_'.join (col).strip('_') for col in data.columns.values]
    data = data.rename(columns={'obi_last': 'obi',
                                'slope_a_last': 'slope_a',
                                'slope_b_last': 'slope_b',
                                'slope_diff_last': 'slope_diff',
                                'slope_a_low_last': 'slope_a_low',
                                'slope_b_low_last': 'slope_b_low',
                                'slope_a_high_last': 'slope_a_high',
                                'slope_b_high_last': 'slope_b_high',
                                'slope_imbalance_low_last': 'slope_imbalance_low',
                                'slope_imbalance_high_last': 'slope_imbalance_high',
                                'slope_diff_low_last': 'slope_diff_low',
                                'slope_diff_high_last': 'slope_diff_high'})
    feature_names = ['obi', 'slope_a', 'slope_b','slope_diff','slope_a_low', 'slope_b_low',
    'slope_a_high','slope_b_high','slope_imbalance_low', 'slope_imbalance_high',
    'slope_diff_low','slope_diff_high','slope_a_mean', 'slope_b_mean', 'slope_diff_mean',
    'slope_a_low_mean', 'slope_b_low_mean', 'slope_a_high_mean', 'slope_b_high_mean',
    'slope_imbalance_low_mean', 'slope_imbalance_high_mean', 'slope_diff_low_mean', 'slope_diff_high_mean']
    
    return data, feature_names
    
def calculate_ret_correlations(df, columns_of_interest):
    """
    计算"ret"列与指定列的相关性。
    """
    if 'ret' not in df.columns:
        raise ValueError("DataFrame中缺少'ret'列")
        
    # 计算，ret，与感兴趣列的相关性
    correlation_matrix = df[['ret'] + columns_of_interest].corr ()
    ret_correlation = correlation_matrix['ret']
    print(ret_correlation)
    
    return ret_correlation
            
def train_model(data: pd.DataFrame, time_step: int = 1000, use_trade_data: bool = False, path: str = "/home/liyao/NT_1.190/example/model/result/lgbm_0503.pkl"):
    """
    该函数用于训练模型
    """
    data = data.copy(deep=True) # 这里的data是第一步的Load data读取的CSV文件的处理结果
    
    # 1．先计算聚合前的features，然后按照time_step的频率把数据合并起来，并且得到features
    data = calculate_features(data)
    data, feature_names = agg_data_snap_25(data, time_step=time_step, use_trade_data=use_trade_data)
    X = data[feature_names].values # feature_names is a list and data[feature_names] is a DataFrame
    y = data['ret'].values  #预测末来time_interval分钟的return
    split_idx = int(len(data) * 0.8)
    # 80%的数据用于训练，20%的数据用于测试
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    print("Shape of X_train: ", X_train.shape)
    print("Shape of X_test: ", X_test.shape)
    
    # 2. clip prediction targets, -5bps to 5bps          
    y_train = np.clip(y_train, -0.0005, 0.0005)
    y_test = np.clip(y_test, -0.0005, 0.0005)

    # 3. Train model
    # model = RandomForestRegressor (n_estimators=100, max_depth=5, random_state=0)
    model, y_pred = get_lgbm(X_train, y_train, X_test, y_test)
    # lgbm的参数先不管
    corr = np.corrcoef(y_test, y_pred)[0, 1]
    print(f'Correlation: {corr}')
    # Save model using joblib
    joblib.dump(model, path)
    
    return model, data, feature_names   
               
