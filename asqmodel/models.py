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
    gpu_params = dict(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.01,
        num_leaves=16,
        random_state=0,
        n_jobs=-1,
        verbose=-1,
        device="gpu",
        gpu_platform_id=0,
        gpu_device_id=0,
        gpu_use_dp=False,
    )
    try:
        lgbm = lgb.LGBMRegressor(**gpu_params)
        lgbm.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            eval_metric="l2",
            callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)]
        )
        print("   使用 GPU 版本")
    except Exception as e:
        print(f"   GPU 失败，回退 CPU: {e}")
        lgbm = lgb.LGBMRegressor(
            n_estimators=100, max_depth=4, learning_rate=0.01,
            num_leaves=16, random_state=0, n_jobs=-1, verbose=-1, device="cpu",
        )
        try:
            lgbm.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                eval_metric="l2",
                callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)]
            )
        except TypeError:
            lgbm.fit(X_train, y_train)
    y_pred = lgbm.predict(X_test)
    return lgbm, y_pred
