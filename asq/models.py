# L:\NT_Course\example\model\models.py
from sklearn.linear_model import LinearRegression 
from sklearn.ensemble import RandomForestRegressor 
import lightgbm as lgb
import numpy as np

def get_ols(X_train, y_train, X_test, y_test):
    ols = LinearRegression()
    ols.fit(X_train, y_train)
    y_pred = ols.predict(X_test)
    return ols, y_pred

def get_rf(X_train, y_train, X_test, y_test):
    rf = RandomForestRegressor(
        n_estimators=100, 
        max_depth=5, 
        min_samples_leaf=0.01, 
        random_state=0,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    return rf, y_pred

def get_lgbm(X_train, y_train, X_test, y_test):
    """训练LightGBM模型（CPU版本）- 兼容所有版本"""
    try:
        # 尝试带early_stopping的版本
        lgbm = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.01,
            num_leaves=16,
            random_state=0,
            n_jobs=-1,
            verbose=-1
        )
        
        lgbm.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            eval_metric='l2',
            early_stopping_rounds=10
        )
    except TypeError:
        # 如果不支持early_stopping，使用简单版本
        print("   使用简单版本（无early stopping）")
        lgbm = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.01,
            num_leaves=16,
            random_state=0,
            n_jobs=-1,
            verbose=-1
        )
        lgbm.fit(X_train, y_train)
    
    y_pred = lgbm.predict(X_test)
    return lgbm, y_pred