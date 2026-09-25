"""Sklearn / LightGBM helpers for offline snap25 training.

`get_lgbm_asq` mirrors `asq/models.py` exactly for project restoration.
`get_lgbm` keeps a flexible API for research / optimize sweeps.
"""

from __future__ import annotations

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


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
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    return rf, y_pred


def get_lgbm_asq(X_train, y_train, X_test, y_test):
    """LightGBM hyperparams copied from `asq/models.py:get_lgbm`."""
    import lightgbm as lgb

    try:
        lgbm = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.01,
            num_leaves=16,
            random_state=0,
            n_jobs=-1,
            verbose=-1,
        )
        try:
            from lightgbm import early_stopping

            lgbm.fit(
                X_train,
                y_train,
                eval_set=[(X_test, y_test)],
                eval_metric="l2",
                callbacks=[early_stopping(10, verbose=False)],
            )
        except TypeError:
            lgbm.fit(
                X_train,
                y_train,
                eval_set=[(X_test, y_test)],
                eval_metric="l2",
                early_stopping_rounds=10,
            )
    except TypeError:
        lgbm = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.01,
            num_leaves=16,
            random_state=0,
            n_jobs=-1,
            verbose=-1,
        )
        lgbm.fit(X_train, y_train)
    y_pred = lgbm.predict(X_test)
    return lgbm, y_pred


def get_lgbm(
    X_train,
    y_train,
    X_test,
    y_test,
    *,
    n_estimators: int = 100,
    max_depth: int = 4,
    learning_rate: float = 0.01,
    num_leaves: int = 16,
    subsample: float = 1.0,
    colsample_bytree: float = 1.0,
    reg_lambda: float = 0.0,
    min_child_samples: int = 20,
    early_stopping_rounds: int | None = 10,
    verbose: int = -1,
):
    """Flexible LGBM; defaults match `asq/models.py` when called with no extras."""
    from lightgbm import LGBMRegressor

    kwargs = dict(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_lambda=reg_lambda,
        min_child_samples=min_child_samples,
        random_state=0,
        n_jobs=-1,
        verbose=verbose,
    )
    model = LGBMRegressor(**kwargs)

    fit_kwargs = {}
    if early_stopping_rounds:
        try:
            from lightgbm import early_stopping

            fit_kwargs["callbacks"] = [early_stopping(early_stopping_rounds, verbose=False)]
        except Exception:
            pass

    try:
        model.fit(X_train, y_train, eval_X=X_test, eval_y=y_test, **fit_kwargs)
    except TypeError:
        try:
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], **fit_kwargs)
        except TypeError:
            model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    return model, y_pred
