# ============================================================
# Crypto Tick-Level Factor Library
# FULL EXPLICIT VERSION: reports 1-78
# No expand_windows(), no compressed factor generation.
# Every factor name is written explicitly for copy/paste and audit.
# ============================================================

from __future__ import annotations

from collections import OrderedDict


# ============================================================
# 0. Global config
# ============================================================

crypto_report_factor_base = OrderedDict()
crypto_report_source_notes = OrderedDict()
priority_base_factors = []
report_block_count = 78  # numbered add_report_factors blocks, including one supplemental block with the same report name

tick_feature_stats = [
    "mean",
    "max",
    "min",
    "last",
    "std",
    "range",
    "diff",
]


# ============================================================
# 1. Utilities
# ============================================================

def add_report_factors(report_name: str, factors: list[str]) -> None:
    """
    Add or extend factors for one report.
    Duplicate factors inside the same report will be ignored.
    """
    if report_name not in crypto_report_factor_base:
        crypto_report_factor_base[report_name] = []

    existing = set(crypto_report_factor_base[report_name])
    for factor in factors:
        if factor not in existing:
            crypto_report_factor_base[report_name].append(factor)
            existing.add(factor)


def build_crypto_tick_factor_maps(
    report_factor_base: dict[str, list[str]],
    stats: list[str],
):
    factor_rename_map = {
        f"{factor}_{stat}": factor
        for report_name, factors in report_factor_base.items()
        for factor in factors
        for stat in stats
    }

    factor_meta_map = {
        f"{factor}_{stat}": {
            "base_factor": factor,
            "stat": stat,
            "report_name": report_name,
        }
        for report_name, factors in report_factor_base.items()
        for factor in factors
        for stat in stats
    }

    train_features = list(factor_rename_map.keys())
    return factor_rename_map, factor_meta_map, train_features


# ============================================================
# 2. Explicit factor blocks
# ============================================================

# ------------------------------------------------------------
# 1. 高频因子的现实与幻想
# ------------------------------------------------------------

add_report_factors(
    "高频因子的现实与幻想",
    [
        "realized_skewness",
        "downside_realized_volatility_share",
        "terminal_trade_volume_share",
        "price_volume_correlation",
        "adjusted_return_reversal",
        "downside_average_trade_size_ratio",
        "large_trade_price_impact",
        "net_bid_liquidity_inflow_ratio",
        "net_aggressor_buy_ratio",
        "net_aggressor_buy_stability",
        "large_aggressor_buy_share",
        "informed_aggressor_sell_share",
        "composite_buying_pressure_ratio",
        "composite_buying_pressure_stability",
    ],
)

# ------------------------------------------------------------
# 2. 高频因子之股票收益分布特征
# ------------------------------------------------------------

add_report_factors(
    "高频因子之股票收益分布特征",
    [
        "realized_variance_raw_w20",
        "realized_variance_raw_w60",
        "realized_variance_raw_w120",
        "realized_variance_demeaned_w20",
        "realized_variance_demeaned_w60",
        "realized_variance_demeaned_w120",
        "realized_variance_partition_avg_w20",
        "realized_variance_partition_avg_w60",
        "realized_variance_partition_avg_w120",
        "realized_skewness_raw_w20",
        "realized_skewness_raw_w60",
        "realized_skewness_raw_w120",
        "realized_skewness_demeaned_w20",
        "realized_skewness_demeaned_w60",
        "realized_skewness_demeaned_w120",
        "realized_skewness_partition_avg_w20",
        "realized_skewness_partition_avg_w60",
        "realized_skewness_partition_avg_w120",
        "realized_kurtosis_raw_w20",
        "realized_kurtosis_raw_w60",
        "realized_kurtosis_raw_w120",
        "realized_kurtosis_demeaned_w20",
        "realized_kurtosis_demeaned_w60",
        "realized_kurtosis_demeaned_w120",
        "realized_kurtosis_partition_avg_w20",
        "realized_kurtosis_partition_avg_w60",
        "realized_kurtosis_partition_avg_w120",
        "orthogonalized_realized_skewness_raw_w20",
        "orthogonalized_realized_skewness_raw_w60",
        "orthogonalized_realized_skewness_raw_w120",
        "orthogonalized_realized_skewness_demeaned_w20",
        "orthogonalized_realized_skewness_demeaned_w60",
        "orthogonalized_realized_skewness_demeaned_w120",
        "orthogonalized_realized_skewness_partition_avg_w20",
        "orthogonalized_realized_skewness_partition_avg_w60",
        "orthogonalized_realized_skewness_partition_avg_w120",
    ],
)

# ------------------------------------------------------------
# 3. 高频因子之已实现波动分解
# ------------------------------------------------------------

add_report_factors(
    "高频因子之已实现波动分解",
    [
        "realized_volatility_total_w20",
        "realized_volatility_total_w60",
        "realized_volatility_total_w120",
        "realized_volatility_market_component_w20",
        "realized_volatility_market_component_w60",
        "realized_volatility_market_component_w120",
        "realized_volatility_idiosyncratic_w20",
        "realized_volatility_idiosyncratic_w60",
        "realized_volatility_idiosyncratic_w120",
        "idiosyncratic_volatility_share_w20",
        "idiosyncratic_volatility_share_w60",
        "idiosyncratic_volatility_share_w120",
        "upside_realized_volatility_w20",
        "upside_realized_volatility_w60",
        "upside_realized_volatility_w120",
        "downside_realized_volatility_w20",
        "downside_realized_volatility_w60",
        "downside_realized_volatility_w120",
        "upside_realized_volatility_share_w20",
        "upside_realized_volatility_share_w60",
        "upside_realized_volatility_share_w120",
        "downside_realized_volatility_share_w20",
        "downside_realized_volatility_share_w60",
        "downside_realized_volatility_share_w120",
        "orthogonalized_realized_volatility_market_component_w20",
        "orthogonalized_realized_volatility_market_component_w60",
        "orthogonalized_realized_volatility_market_component_w120",
        "orthogonalized_realized_volatility_idiosyncratic_w20",
        "orthogonalized_realized_volatility_idiosyncratic_w60",
        "orthogonalized_realized_volatility_idiosyncratic_w120",
        "orthogonalized_idiosyncratic_volatility_share_w20",
        "orthogonalized_idiosyncratic_volatility_share_w60",
        "orthogonalized_idiosyncratic_volatility_share_w120",
        "orthogonalized_upside_realized_volatility_w20",
        "orthogonalized_upside_realized_volatility_w60",
        "orthogonalized_upside_realized_volatility_w120",
        "orthogonalized_downside_realized_volatility_w20",
        "orthogonalized_downside_realized_volatility_w60",
        "orthogonalized_downside_realized_volatility_w120",
        "orthogonalized_upside_realized_volatility_share_w20",
        "orthogonalized_upside_realized_volatility_share_w60",
        "orthogonalized_upside_realized_volatility_share_w120",
    ],
)

# ------------------------------------------------------------
# 4. 高频因子（二）：结构化反转因子
# ------------------------------------------------------------

add_report_factors(
    "高频因子（二）：结构化反转因子",
    [
        "return_reversal_w20",
        "return_reversal_w60",
        "return_reversal_w120",
        "volume_weighted_reversal_w20",
        "volume_weighted_reversal_w60",
        "volume_weighted_reversal_w120",
        "structured_reversal_w20",
        "structured_reversal_w60",
        "structured_reversal_w120",
        "momentum_segment_return_w20",
        "momentum_segment_return_w60",
        "momentum_segment_return_w120",
        "reversal_segment_return_w20",
        "reversal_segment_return_w60",
        "reversal_segment_return_w120",
        "reversal_momentum_spread_w20",
        "reversal_momentum_spread_w60",
        "reversal_momentum_spread_w120",
        "volatility_timed_reversal_strength_w20",
        "volatility_timed_reversal_strength_w60",
        "volatility_timed_reversal_strength_w120",
    ],
)

# ------------------------------------------------------------
# 5. 高频因子（三）：高频因子研究框架
# ------------------------------------------------------------

add_report_factors(
    "高频因子（三）：高频因子研究框架",
    [
        "liquidity_premium_anchor_w20",
        "liquidity_premium_anchor_w60",
        "liquidity_premium_anchor_w120",
        "amount_anchored_liquidity_premium_w20",
        "amount_anchored_liquidity_premium_w60",
        "amount_anchored_liquidity_premium_w120",
        "global_reversal_w20",
        "global_reversal_w60",
        "global_reversal_w120",
        "global_volume_weighted_reversal_w20",
        "global_volume_weighted_reversal_w60",
        "global_volume_weighted_reversal_w120",
        "global_structured_reversal_w20",
        "global_structured_reversal_w60",
        "global_structured_reversal_w120",
        "initial_window_reversal_w20",
        "initial_window_reversal_w60",
        "initial_window_reversal_w120",
        "initial_window_volume_weighted_reversal_w20",
        "initial_window_volume_weighted_reversal_w60",
        "initial_window_volume_weighted_reversal_w120",
        "reversal_volatility_state_w20",
        "reversal_volatility_state_w60",
        "reversal_volatility_state_w120",
    ],
)

# ------------------------------------------------------------
# 6. 高频因子（五）：高频因子和交易行为
# ------------------------------------------------------------

add_report_factors(
    "高频因子（五）：高频因子和交易行为",
    [
        "amihud_illiquidity_w20",
        "amihud_illiquidity_w60",
        "amihud_illiquidity_w120",
        "path_adjusted_illiquidity_w20",
        "path_adjusted_illiquidity_w60",
        "path_adjusted_illiquidity_w120",
        "trajectory_illiquidity_w20",
        "trajectory_illiquidity_w60",
        "trajectory_illiquidity_w120",
        "aggressor_game_factor_w20",
        "aggressor_game_factor_w60",
        "aggressor_game_factor_w120",
        "buy_sell_pressure_game_w20",
        "buy_sell_pressure_game_w60",
        "buy_sell_pressure_game_w120",
        "idiosyncratic_rate_w20",
        "idiosyncratic_rate_w60",
        "idiosyncratic_rate_w120",
        "trading_behavior_abnormality_w20",
        "trading_behavior_abnormality_w60",
        "trading_behavior_abnormality_w120",
        "hf_behavior_composite_w20",
        "hf_behavior_composite_w60",
        "hf_behavior_composite_w120",
    ],
)

# ------------------------------------------------------------
# 7. 基于日内高频数据的短周期选股因子研究
# ------------------------------------------------------------

add_report_factors(
    "基于日内高频数据的短周期选股因子研究",
    [
        "realized_distribution_residual_std_w20",
        "realized_distribution_residual_std_w60",
        "realized_distribution_residual_std_w120",
        "rvol_rskew_rkurt_residual_std_w20",
        "rvol_rskew_rkurt_residual_std_w60",
        "rvol_rskew_rkurt_residual_std_w120",
        "short_cycle_realized_distribution_score_w20",
        "short_cycle_realized_distribution_score_w60",
        "short_cycle_realized_distribution_score_w120",
    ],
)

# ------------------------------------------------------------
# 8. 高频因子（六）：特异视角下的波动率因子
# ------------------------------------------------------------

add_report_factors(
    "高频因子（六）：特异视角下的波动率因子",
    [
        "realized_volatility_w20",
        "realized_volatility_w60",
        "realized_volatility_w120",
        "idiosyncratic_volatility_w20",
        "idiosyncratic_volatility_w60",
        "idiosyncratic_volatility_w120",
        "enhanced_idiosyncratic_volatility_w20",
        "enhanced_idiosyncratic_volatility_w60",
        "enhanced_idiosyncratic_volatility_w120",
        "high_frequency_volatility_w20",
        "high_frequency_volatility_w60",
        "high_frequency_volatility_w120",
        "nonlinear_volatility_w20",
        "nonlinear_volatility_w60",
        "nonlinear_volatility_w120",
        "tail_trimmed_volatility_w20",
        "tail_trimmed_volatility_w60",
        "tail_trimmed_volatility_w120",
        "volatility_idiosyncratic_interaction_w20",
        "volatility_idiosyncratic_interaction_w60",
        "volatility_idiosyncratic_interaction_w120",
    ],
)

# ------------------------------------------------------------
# 9. 高频因子（七）：分布估计下的主动成交占比
# ------------------------------------------------------------

add_report_factors(
    "高频因子（七）：分布估计下的主动成交占比",
    [
        "naive_aggressor_buy_share_w20",
        "naive_aggressor_buy_share_w60",
        "naive_aggressor_buy_share_w120",
        "naive_aggressor_sell_share_w20",
        "naive_aggressor_sell_share_w60",
        "naive_aggressor_sell_share_w120",
        "bulk_volume_active_buy_share_w20",
        "bulk_volume_active_buy_share_w60",
        "bulk_volume_active_buy_share_w120",
        "bulk_volume_active_sell_share_w20",
        "bulk_volume_active_sell_share_w60",
        "bulk_volume_active_sell_share_w120",
        "t_distribution_active_buy_share_w20",
        "t_distribution_active_buy_share_w60",
        "t_distribution_active_buy_share_w120",
        "normal_distribution_active_buy_share_w20",
        "normal_distribution_active_buy_share_w60",
        "normal_distribution_active_buy_share_w120",
        "confidence_normal_active_buy_share_w20",
        "confidence_normal_active_buy_share_w60",
        "confidence_normal_active_buy_share_w120",
        "uniform_distribution_active_buy_share_w20",
        "uniform_distribution_active_buy_share_w60",
        "uniform_distribution_active_buy_share_w120",
        "piecewise_linear_active_buy_share_w20",
        "piecewise_linear_active_buy_share_w60",
        "piecewise_linear_active_buy_share_w120",
        "hook_shaped_active_buy_share_w20",
        "hook_shaped_active_buy_share_w60",
        "hook_shaped_active_buy_share_w120",
    ],
)

# ------------------------------------------------------------
# 10. 高频因子（八）：高位成交因子
# ------------------------------------------------------------

add_report_factors(
    "高频因子（八）：高位成交因子",
    [
        "price_volume_correlation_w20",
        "price_volume_correlation_w60",
        "price_volume_correlation_w120",
        "high_price_volume_concentration_w20",
        "high_price_volume_concentration_w60",
        "high_price_volume_concentration_w120",
        "volume_weighted_close_price_ratio_w20",
        "volume_weighted_close_price_ratio_w60",
        "volume_weighted_close_price_ratio_w120",
        "volume_weighted_price_skewness_w20",
        "volume_weighted_price_skewness_w60",
        "volume_weighted_price_skewness_w120",
        "amount_share_entropy_w20",
        "amount_share_entropy_w60",
        "amount_share_entropy_w120",
        "unit_amount_share_entropy_w20",
        "unit_amount_share_entropy_w60",
        "unit_amount_share_entropy_w120",
        "high_position_trade_composite_w20",
        "high_position_trade_composite_w60",
        "high_position_trade_composite_w120",
    ],
)

# ------------------------------------------------------------
# 11. 高频因子（九）：高频波动中的时间序列信息
# ------------------------------------------------------------

add_report_factors(
    "高频因子（九）：高频波动中的时间序列信息",
    [
        "hf_volume_volatility_w20",
        "hf_volume_volatility_w60",
        "hf_volume_volatility_w120",
        "intrawindow_volume_volatility_w20",
        "intrawindow_volume_volatility_w60",
        "intrawindow_volume_volatility_w120",
        "interwindow_volume_volatility_w20",
        "interwindow_volume_volatility_w60",
        "interwindow_volume_volatility_w120",
        "volume_diff_std_w20",
        "volume_diff_std_w60",
        "volume_diff_std_w120",
        "trade_size_diff_std_w20",
        "trade_size_diff_std_w60",
        "trade_size_diff_std_w120",
        "volume_diff_abs_mean_w20",
        "volume_diff_abs_mean_w60",
        "volume_diff_abs_mean_w120",
        "trade_size_diff_abs_mean_w20",
        "trade_size_diff_abs_mean_w60",
        "trade_size_diff_abs_mean_w120",
        "volume_peak_count_w20",
        "volume_peak_count_w60",
        "volume_peak_count_w120",
        "trade_size_peak_count_w20",
        "trade_size_peak_count_w60",
        "trade_size_peak_count_w120",
        "local_peak_intensity_w20",
        "local_peak_intensity_w60",
        "local_peak_intensity_w120",
        "peak_interval_count_w20",
        "peak_interval_count_w60",
        "peak_interval_count_w120",
    ],
)

# ------------------------------------------------------------
# 12. 买卖报单流动性因子构建
# ------------------------------------------------------------

add_report_factors(
    "买卖报单流动性因子构建",
    [
        "bid_order_liquidity_cost_w20",
        "bid_order_liquidity_cost_w60",
        "bid_order_liquidity_cost_w120",
        "ask_order_liquidity_cost_w20",
        "ask_order_liquidity_cost_w60",
        "ask_order_liquidity_cost_w120",
        "bid_market_impact_cost_w20",
        "bid_market_impact_cost_w60",
        "bid_market_impact_cost_w120",
        "ask_market_impact_cost_w20",
        "ask_market_impact_cost_w60",
        "ask_market_impact_cost_w120",
        "bid_book_liquidity_pressure_w20",
        "bid_book_liquidity_pressure_w60",
        "bid_book_liquidity_pressure_w120",
        "ask_book_liquidity_pressure_w20",
        "ask_book_liquidity_pressure_w60",
        "ask_book_liquidity_pressure_w120",
        "book_depth_adjusted_spread_w20",
        "book_depth_adjusted_spread_w60",
        "book_depth_adjusted_spread_w120",
        "marketable_cost_index_bid_w20",
        "marketable_cost_index_bid_w60",
        "marketable_cost_index_bid_w120",
        "marketable_cost_index_ask_w20",
        "marketable_cost_index_ask_w60",
        "marketable_cost_index_ask_w120",
    ],
)

# ------------------------------------------------------------
# 13. 高频因子（十）：量价关系中的反转微观结构
# ------------------------------------------------------------

add_report_factors(
    "高频因子（十）：量价关系中的反转微观结构",
    [
        "volume_filtered_local_reversal_low_w20",
        "volume_filtered_local_reversal_low_w60",
        "volume_filtered_local_reversal_low_w120",
        "volume_filtered_local_reversal_high_w20",
        "volume_filtered_local_reversal_high_w60",
        "volume_filtered_local_reversal_high_w120",
        "abs_return_filtered_local_reversal_low_w20",
        "abs_return_filtered_local_reversal_low_w60",
        "abs_return_filtered_local_reversal_low_w120",
        "abs_return_filtered_local_reversal_high_w20",
        "abs_return_filtered_local_reversal_high_w60",
        "abs_return_filtered_local_reversal_high_w120",
        "trade_size_filtered_local_reversal_low_w20",
        "trade_size_filtered_local_reversal_low_w60",
        "trade_size_filtered_local_reversal_low_w120",
        "trade_size_filtered_local_reversal_high_w20",
        "trade_size_filtered_local_reversal_high_w60",
        "trade_size_filtered_local_reversal_high_w120",
        "trade_size_weighted_reversal_w20",
        "trade_size_weighted_reversal_w60",
        "trade_size_weighted_reversal_w120",
        "standardized_trade_size_weighted_reversal_w20",
        "standardized_trade_size_weighted_reversal_w60",
        "standardized_trade_size_weighted_reversal_w120",
        "trade_size_return_correlation_w20",
        "trade_size_return_correlation_w60",
        "trade_size_return_correlation_w120",
        "price_filtered_local_volume_low_w20",
        "price_filtered_local_volume_low_w60",
        "price_filtered_local_volume_low_w120",
        "price_filtered_local_volume_high_w20",
        "price_filtered_local_volume_high_w60",
        "price_filtered_local_volume_high_w120",
        "reversal_microstructure_composite_w20",
        "reversal_microstructure_composite_w60",
        "reversal_microstructure_composite_w120",
    ],
)

# ------------------------------------------------------------
# 14. 基于事件冲击效应的高频统计套利策略
# ------------------------------------------------------------

add_report_factors(
    "基于事件冲击效应的高频统计套利策略",
    [
        "event_shock_return_w20",
        "event_shock_return_w60",
        "event_shock_return_w120",
        "event_shock_abnormal_return_w20",
        "event_shock_abnormal_return_w60",
        "event_shock_abnormal_return_w120",
        "event_shock_reversal_strength_w20",
        "event_shock_reversal_strength_w60",
        "event_shock_reversal_strength_w120",
        "pair_spread_zscore_w20",
        "pair_spread_zscore_w60",
        "pair_spread_zscore_w120",
        "cointegration_residual_zscore_w20",
        "cointegration_residual_zscore_w60",
        "cointegration_residual_zscore_w120",
        "relative_value_dislocation_w20",
        "relative_value_dislocation_w60",
        "relative_value_dislocation_w120",
        "hedged_spread_reversion_speed_w20",
        "hedged_spread_reversion_speed_w60",
        "hedged_spread_reversion_speed_w120",
    ],
)

# ------------------------------------------------------------
# 15. 从海外经验看中国高频交易的发展
# ------------------------------------------------------------

add_report_factors(
    "从海外经验看中国高频交易的发展",
    [
        "quote_update_intensity_w20",
        "quote_update_intensity_w60",
        "quote_update_intensity_w120",
        "order_cancel_intensity_w20",
        "order_cancel_intensity_w60",
        "order_cancel_intensity_w120",
        "order_to_trade_ratio_w20",
        "order_to_trade_ratio_w60",
        "order_to_trade_ratio_w120",
        "liquidity_withdrawal_intensity_w20",
        "liquidity_withdrawal_intensity_w60",
        "liquidity_withdrawal_intensity_w120",
        "market_making_spread_capture_w20",
        "market_making_spread_capture_w60",
        "market_making_spread_capture_w120",
        "cross_market_lead_lag_signal_w20",
        "cross_market_lead_lag_signal_w60",
        "cross_market_lead_lag_signal_w120",
        "latency_arbitrage_pressure_w20",
        "latency_arbitrage_pressure_w60",
        "latency_arbitrage_pressure_w120",
    ],
)

# ------------------------------------------------------------
# 16. 听海外高频交易专家讲解美国的高频交易
# ------------------------------------------------------------

add_report_factors(
    "听海外高频交易专家讲解美国的高频交易",
    [
        "incremental_order_flow_intensity_w20",
        "incremental_order_flow_intensity_w60",
        "incremental_order_flow_intensity_w120",
        "adverse_selection_pressure_w20",
        "adverse_selection_pressure_w60",
        "adverse_selection_pressure_w120",
        "queue_position_pressure_w20",
        "queue_position_pressure_w60",
        "queue_position_pressure_w120",
        "queue_ahead_liquidity_w20",
        "queue_ahead_liquidity_w60",
        "queue_ahead_liquidity_w120",
        "liquidity_provision_quality_w20",
        "liquidity_provision_quality_w60",
        "liquidity_provision_quality_w120",
        "order_flow_ripple_impact_w20",
        "order_flow_ripple_impact_w60",
        "order_flow_ripple_impact_w120",
        "cross_venue_price_dislocation_w20",
        "cross_venue_price_dislocation_w60",
        "cross_venue_price_dislocation_w120",
    ],
)

# ------------------------------------------------------------
# 17. 中高频交易策略再出发：机器学习T0
# ------------------------------------------------------------

add_report_factors(
    "中高频交易策略再出发：机器学习T0",
    [
        "pre_window_return_w20",
        "pre_window_return_w60",
        "pre_window_return_w120",
        "initial_window_return_w20",
        "initial_window_return_w60",
        "initial_window_return_w120",
        "secondary_window_return_w20",
        "secondary_window_return_w60",
        "secondary_window_return_w120",
        "initial_window_amount_share_w20",
        "initial_window_amount_share_w60",
        "initial_window_amount_share_w120",
        "secondary_window_amount_share_w20",
        "secondary_window_amount_share_w60",
        "secondary_window_amount_share_w120",
        "initial_order_imbalance_change_w20",
        "initial_order_imbalance_change_w60",
        "initial_order_imbalance_change_w120",
        "secondary_order_imbalance_change_w20",
        "secondary_order_imbalance_change_w60",
        "secondary_order_imbalance_change_w120",
        "mid_quote_mean_level_w20",
        "mid_quote_mean_level_w60",
        "mid_quote_mean_level_w120",
        "mid_quote_max_level_w20",
        "mid_quote_max_level_w60",
        "mid_quote_max_level_w120",
        "mid_quote_min_level_w20",
        "mid_quote_min_level_w60",
        "mid_quote_min_level_w120",
        "mid_quote_abs_change_w20",
        "mid_quote_abs_change_w60",
        "mid_quote_abs_change_w120",
        "mid_quote_change_ratio_w20",
        "mid_quote_change_ratio_w60",
        "mid_quote_change_ratio_w120",
        "sustained_up_move_flag_w20",
        "sustained_up_move_flag_w60",
        "sustained_up_move_flag_w120",
        "sustained_down_move_flag_w20",
        "sustained_down_move_flag_w60",
        "sustained_down_move_flag_w120",
    ],
)

# ------------------------------------------------------------
# 18. 波动性传导、市场板块差异与股票流动性
# ------------------------------------------------------------

add_report_factors(
    "波动性传导、市场板块差异与股票流动性",
    [
        "hf_information_price_w20",
        "hf_information_price_w60",
        "hf_information_price_w120",
        "idiosyncratic_volatility_transmission_w20",
        "idiosyncratic_volatility_transmission_w60",
        "idiosyncratic_volatility_transmission_w120",
        "market_component_volatility_transmission_w20",
        "market_component_volatility_transmission_w60",
        "market_component_volatility_transmission_w120",
        "peer_component_volatility_transmission_w20",
        "peer_component_volatility_transmission_w60",
        "peer_component_volatility_transmission_w120",
        "liquidity_sensitivity_to_idiosyncratic_volatility_w20",
        "liquidity_sensitivity_to_idiosyncratic_volatility_w60",
        "liquidity_sensitivity_to_idiosyncratic_volatility_w120",
        "liquidity_sensitivity_to_market_volatility_w20",
        "liquidity_sensitivity_to_market_volatility_w60",
        "liquidity_sensitivity_to_market_volatility_w120",
        "liquidity_sensitivity_to_peer_volatility_w20",
        "liquidity_sensitivity_to_peer_volatility_w60",
        "liquidity_sensitivity_to_peer_volatility_w120",
    ],
)

# ------------------------------------------------------------
# 19. 暗池：高频交易及人工智能大盗
# ------------------------------------------------------------

add_report_factors(
    "暗池：高频交易及人工智能大盗",
    [
        "hidden_liquidity_pressure_w20",
        "hidden_liquidity_pressure_w60",
        "hidden_liquidity_pressure_w120",
        "predatory_order_flow_pressure_w20",
        "predatory_order_flow_pressure_w60",
        "predatory_order_flow_pressure_w120",
        "large_order_detection_pressure_w20",
        "large_order_detection_pressure_w60",
        "large_order_detection_pressure_w120",
        "liquidity_toxicity_w20",
        "liquidity_toxicity_w60",
        "liquidity_toxicity_w120",
        "liquidity_vacuum_risk_w20",
        "liquidity_vacuum_risk_w60",
        "liquidity_vacuum_risk_w120",
        "flash_crash_feedback_pressure_w20",
        "flash_crash_feedback_pressure_w60",
        "flash_crash_feedback_pressure_w120",
    ],
)

# ------------------------------------------------------------
# 20. 从加权IC到机器学习：高频因子多头失效的修正
# ------------------------------------------------------------

add_report_factors(
    "从加权IC到机器学习：高频因子多头失效的修正",
    [
        "long_leg_effectiveness_score_w20",
        "long_leg_effectiveness_score_w60",
        "long_leg_effectiveness_score_w120",
        "short_leg_contribution_score_w20",
        "short_leg_contribution_score_w60",
        "short_leg_contribution_score_w120",
        "long_short_contribution_imbalance_w20",
        "long_short_contribution_imbalance_w60",
        "long_short_contribution_imbalance_w120",
        "weighted_ic_score_w20",
        "weighted_ic_score_w60",
        "weighted_ic_score_w120",
        "long_weighted_ic_score_w20",
        "long_weighted_ic_score_w60",
        "long_weighted_ic_score_w120",
        "tail_weighted_ic_score_w20",
        "tail_weighted_ic_score_w60",
        "tail_weighted_ic_score_w120",
        "factor_quadratic_exposure_w20",
        "factor_quadratic_exposure_w60",
        "factor_quadratic_exposure_w120",
        "factor_cubic_exposure_w20",
        "factor_cubic_exposure_w60",
        "factor_cubic_exposure_w120",
        "factor_quartic_exposure_w20",
        "factor_quartic_exposure_w60",
        "factor_quartic_exposure_w120",
        "nonlinear_factor_response_w20",
        "nonlinear_factor_response_w60",
        "nonlinear_factor_response_w120",
        "factor_monotonicity_break_score_w20",
        "factor_monotonicity_break_score_w60",
        "factor_monotonicity_break_score_w120",
        "factor_tail_failure_score_w20",
        "factor_tail_failure_score_w60",
        "factor_tail_failure_score_w120",
        "rbf_factor_exposure_low_w20",
        "rbf_factor_exposure_low_w60",
        "rbf_factor_exposure_low_w120",
        "rbf_factor_exposure_mid_w20",
        "rbf_factor_exposure_mid_w60",
        "rbf_factor_exposure_mid_w120",
        "rbf_factor_exposure_high_w20",
        "rbf_factor_exposure_high_w60",
        "rbf_factor_exposure_high_w120",
        "rbf_factor_response_score_w20",
        "rbf_factor_response_score_w60",
        "rbf_factor_response_score_w120",
    ],
)

# ------------------------------------------------------------
# 21. 高频价量相关性，意想不到的选股因子
# ------------------------------------------------------------

add_report_factors(
    "高频价量相关性，意想不到的选股因子",
    [
        "price_volume_corr_avg_w20",
        "price_volume_corr_avg_w60",
        "price_volume_corr_avg_w120",
        "price_volume_corr_std_w20",
        "price_volume_corr_std_w60",
        "price_volume_corr_std_w120",
        "price_volume_corr_trend_w20",
        "price_volume_corr_trend_w60",
        "price_volume_corr_trend_w120",
        "price_volume_corr_deret_w20",
        "price_volume_corr_deret_w60",
        "price_volume_corr_deret_w120",
        "price_volume_corr_residual_reversal_w20",
        "price_volume_corr_residual_reversal_w60",
        "price_volume_corr_residual_reversal_w120",
        "cpv_factor_w20",
        "cpv_factor_w60",
        "cpv_factor_w120",
        "pure_cpv_factor_w20",
        "pure_cpv_factor_w60",
        "pure_cpv_factor_w120",
        "volume_confirmed_reversal_w20",
        "volume_confirmed_reversal_w60",
        "volume_confirmed_reversal_w120",
        "volume_confirmed_momentum_w20",
        "volume_confirmed_momentum_w60",
        "volume_confirmed_momentum_w120",
        "price_volume_shape_stability_w20",
        "price_volume_shape_stability_w60",
        "price_volume_shape_stability_w120",
        "price_volume_shape_switching_intensity_w20",
        "price_volume_shape_switching_intensity_w60",
        "price_volume_shape_switching_intensity_w120",
    ],
)

# ------------------------------------------------------------
# 22. 高频量化因子的批量生产与集中管理
# ------------------------------------------------------------

add_report_factors(
    "高频量化因子的批量生产与集中管理",
    [
        "auto_generated_breakout_score_w20",
        "auto_generated_breakout_score_w60",
        "auto_generated_breakout_score_w120",
        "recursive_operator_factor_score_w20",
        "recursive_operator_factor_score_w60",
        "recursive_operator_factor_score_w120",
        "factor_formula_complexity_score_w20",
        "factor_formula_complexity_score_w60",
        "factor_formula_complexity_score_w120",
        "large_buy_trade_amount_share_w20",
        "large_buy_trade_amount_share_w60",
        "large_buy_trade_amount_share_w120",
        "large_buy_trade_concentration_w20",
        "large_buy_trade_concentration_w60",
        "large_buy_trade_concentration_w120",
        "large_buy_trade_flow_pressure_w20",
        "large_buy_trade_flow_pressure_w60",
        "large_buy_trade_flow_pressure_w120",
        "rolling_max_operator_score_w20",
        "rolling_max_operator_score_w60",
        "rolling_max_operator_score_w120",
        "rolling_min_operator_score_w20",
        "rolling_min_operator_score_w60",
        "rolling_min_operator_score_w120",
        "rolling_rank_operator_score_w20",
        "rolling_rank_operator_score_w60",
        "rolling_rank_operator_score_w120",
        "rolling_decay_operator_score_w20",
        "rolling_decay_operator_score_w60",
        "rolling_decay_operator_score_w120",
    ],
)

# ------------------------------------------------------------
# 23. 高频选股因子梳理与新因子探索
# ------------------------------------------------------------

add_report_factors(
    "高频选股因子梳理与新因子探索",
    [
        "abnormal_return_time_share_w20",
        "abnormal_return_time_share_w60",
        "abnormal_return_time_share_w120",
        "abnormal_volume_share_w20",
        "abnormal_volume_share_w60",
        "abnormal_volume_share_w120",
        "abnormal_abs_return_share_w20",
        "abnormal_abs_return_share_w60",
        "abnormal_abs_return_share_w120",
        "stock_market_return_ratio_w20",
        "stock_market_return_ratio_w60",
        "stock_market_return_ratio_w120",
        "market_adjusted_intraday_abnormality_w20",
        "market_adjusted_intraday_abnormality_w60",
        "market_adjusted_intraday_abnormality_w120",
        "contrarian_upward_abnormality_w20",
        "contrarian_upward_abnormality_w60",
        "contrarian_upward_abnormality_w120",
        "contrarian_downward_abnormality_w20",
        "contrarian_downward_abnormality_w60",
        "contrarian_downward_abnormality_w120",
        "intraday_price_pattern_cluster_score_w20",
        "intraday_price_pattern_cluster_score_w60",
        "intraday_price_pattern_cluster_score_w120",
        "intraday_volume_pattern_cluster_score_w20",
        "intraday_volume_pattern_cluster_score_w60",
        "intraday_volume_pattern_cluster_score_w120",
        "price_volume_pattern_similarity_w20",
        "price_volume_pattern_similarity_w60",
        "price_volume_pattern_similarity_w120",
    ],
)

# ------------------------------------------------------------
# 24. 高频因子：日内分时成交量蕴藏玄机
# ------------------------------------------------------------

add_report_factors(
    "高频因子：日内分时成交量蕴藏玄机",
    [
        "intraday_volume_profile_wshape_w20",
        "intraday_volume_profile_wshape_w60",
        "intraday_volume_profile_wshape_w120",
        "volume_share_first_window_w20",
        "volume_share_first_window_w60",
        "volume_share_first_window_w120",
        "volume_share_middle_window_w20",
        "volume_share_middle_window_w60",
        "volume_share_middle_window_w120",
        "volume_share_terminal_window_w20",
        "volume_share_terminal_window_w60",
        "volume_share_terminal_window_w120",
        "first_to_second_window_volume_ratio_w20",
        "first_to_second_window_volume_ratio_w60",
        "first_to_second_window_volume_ratio_w120",
        "first_to_middle_window_volume_ratio_w20",
        "first_to_middle_window_volume_ratio_w60",
        "first_to_middle_window_volume_ratio_w120",
        "terminal_to_middle_window_volume_ratio_w20",
        "terminal_to_middle_window_volume_ratio_w60",
        "terminal_to_middle_window_volume_ratio_w120",
        "ma_volume_ratio_w20",
        "ma_volume_ratio_w60",
        "ma_volume_ratio_w120",
        "ewma_volume_ratio_w20",
        "ewma_volume_ratio_w60",
        "ewma_volume_ratio_w120",
        "volume_profile_stability_w20",
        "volume_profile_stability_w60",
        "volume_profile_stability_w120",
        "volume_profile_shift_intensity_w20",
        "volume_profile_shift_intensity_w60",
        "volume_profile_shift_intensity_w120",
    ],
)

# ------------------------------------------------------------
# 25. 高频因子（四）：高阶矩高频因子
# ------------------------------------------------------------

add_report_factors(
    "高频因子（四）：高阶矩高频因子",
    [
        "return_mean_w20",
        "return_mean_w60",
        "return_mean_w120",
        "return_std_w20",
        "return_std_w60",
        "return_std_w120",
        "return_skewness_w20",
        "return_skewness_w60",
        "return_skewness_w120",
        "return_kurtosis_w20",
        "return_kurtosis_w60",
        "return_kurtosis_w120",
        "log_return_mean_w20",
        "log_return_mean_w60",
        "log_return_mean_w120",
        "log_return_std_w20",
        "log_return_std_w60",
        "log_return_std_w120",
        "log_return_skewness_w20",
        "log_return_skewness_w60",
        "log_return_skewness_w120",
        "log_return_kurtosis_w20",
        "log_return_kurtosis_w60",
        "log_return_kurtosis_w120",
        "residual_return_mean_w20",
        "residual_return_mean_w60",
        "residual_return_mean_w120",
        "residual_return_std_w20",
        "residual_return_std_w60",
        "residual_return_std_w120",
        "residual_return_skewness_w20",
        "residual_return_skewness_w60",
        "residual_return_skewness_w120",
        "residual_return_kurtosis_w20",
        "residual_return_kurtosis_w60",
        "residual_return_kurtosis_w120",
        "volume_share_mean_w20",
        "volume_share_mean_w60",
        "volume_share_mean_w120",
        "volume_share_std_w20",
        "volume_share_std_w60",
        "volume_share_std_w120",
        "volume_share_skewness_w20",
        "volume_share_skewness_w60",
        "volume_share_skewness_w120",
        "volume_share_kurtosis_w20",
        "volume_share_kurtosis_w60",
        "volume_share_kurtosis_w120",
        "higher_moment_abnormality_score_w20",
        "higher_moment_abnormality_score_w60",
        "higher_moment_abnormality_score_w120",
    ],
)

# ------------------------------------------------------------
# 26. 股价日内模式中蕴藏的选股因子
# ------------------------------------------------------------

add_report_factors(
    "股价日内模式中蕴藏的选股因子",
    [
        "active_passive_return_spread_w20",
        "active_passive_return_spread_w60",
        "active_passive_return_spread_w120",
        "early_late_return_residual_spread_w20",
        "early_late_return_residual_spread_w60",
        "early_late_return_residual_spread_w120",
        "informed_trading_direction_score_w20",
        "informed_trading_direction_score_w60",
        "informed_trading_direction_score_w120",
        "apm_factor_w20",
        "apm_factor_w60",
        "apm_factor_w120",
        "market_adjusted_apm_factor_w20",
        "market_adjusted_apm_factor_w60",
        "market_adjusted_apm_factor_w120",
        "residual_apm_factor_w20",
        "residual_apm_factor_w60",
        "residual_apm_factor_w120",
        "apm_smart_money_interaction_w20",
        "apm_smart_money_interaction_w60",
        "apm_smart_money_interaction_w120",
    ],
)

# ------------------------------------------------------------
# 27. 基于深度学习理念的高频交易策略
# ------------------------------------------------------------

add_report_factors(
    "基于深度学习理念的高频交易策略",
    [
        "volume_breakout_new_high_w20",
        "volume_breakout_new_high_w60",
        "volume_breakout_new_high_w120",
        "volume_breakout_new_low_w20",
        "volume_breakout_new_low_w60",
        "volume_breakout_new_low_w120",
        "price_new_high_signal_w20",
        "price_new_high_signal_w60",
        "price_new_high_signal_w120",
        "price_new_low_signal_w20",
        "price_new_low_signal_w60",
        "price_new_low_signal_w120",
        "price_volume_extreme_score_w20",
        "price_volume_extreme_score_w60",
        "price_volume_extreme_score_w120",
        "volume_expansion_extreme_score_w20",
        "volume_expansion_extreme_score_w60",
        "volume_expansion_extreme_score_w120",
        "breakout_winrate_stability_w20",
        "breakout_winrate_stability_w60",
        "breakout_winrate_stability_w120",
        "parameter_surface_stability_w20",
        "parameter_surface_stability_w60",
        "parameter_surface_stability_w120",
        "anomaly_pattern_generalization_score_w20",
        "anomaly_pattern_generalization_score_w60",
        "anomaly_pattern_generalization_score_w120",
    ],
)

# ------------------------------------------------------------
# 28. 高频量价因子在股票与期货中的表现
# ------------------------------------------------------------

add_report_factors(
    "高频量价因子在股票与期货中的表现",
    [
        "realized_skewness_momentum_w20",
        "realized_skewness_momentum_w60",
        "realized_skewness_momentum_w120",
        "realized_kurtosis_momentum_w20",
        "realized_kurtosis_momentum_w60",
        "realized_kurtosis_momentum_w120",
        "realized_skew_kurt_composite_w20",
        "realized_skew_kurt_composite_w60",
        "realized_skew_kurt_composite_w120",
        "upside_downside_volatility_spread_w20",
        "upside_downside_volatility_spread_w60",
        "upside_downside_volatility_spread_w120",
        "upside_volatility_momentum_share_w20",
        "upside_volatility_momentum_share_w60",
        "upside_volatility_momentum_share_w120",
        "mid_session_volume_share_w20",
        "mid_session_volume_share_w60",
        "mid_session_volume_share_w120",
        "terminal_volume_share_reversal_w20",
        "terminal_volume_share_reversal_w60",
        "terminal_volume_share_reversal_w120",
        "price_volume_correlation_momentum_w20",
        "price_volume_correlation_momentum_w60",
        "price_volume_correlation_momentum_w120",
        "open_interest_price_correlation_w20",
        "open_interest_price_correlation_w60",
        "open_interest_price_correlation_w120",
        "fund_flow_short_reversal_w20",
        "fund_flow_short_reversal_w60",
        "fund_flow_short_reversal_w120",
        "fund_flow_long_momentum_w20",
        "fund_flow_long_momentum_w60",
        "fund_flow_long_momentum_w120",
        "intraday_trend_strength_w20",
        "intraday_trend_strength_w60",
        "intraday_trend_strength_w120",
        "improved_reversal_ex_overnight_w20",
        "improved_reversal_ex_overnight_w60",
        "improved_reversal_ex_overnight_w120",
        "improved_reversal_ex_initial_window_w20",
        "improved_reversal_ex_initial_window_w60",
        "improved_reversal_ex_initial_window_w120",
        "crypto_futures_style_hf_composite_w20",
        "crypto_futures_style_hf_composite_w60",
        "crypto_futures_style_hf_composite_w120",
    ],
)

# ------------------------------------------------------------
# 29. 高频因子在不同周期和域下的表现及影响因素分析
# ------------------------------------------------------------

add_report_factors(
    "高频因子在不同周期和域下的表现及影响因素分析",
    [
        "multi_horizon_factor_stability_w20",
        "multi_horizon_factor_stability_w60",
        "multi_horizon_factor_stability_w120",
        "weekly_monthly_consistency_score_w20",
        "weekly_monthly_consistency_score_w60",
        "weekly_monthly_consistency_score_w120",
        "factor_domain_robustness_score_w20",
        "factor_domain_robustness_score_w60",
        "factor_domain_robustness_score_w120",
        "orthogonalized_factor_strength_w20",
        "orthogonalized_factor_strength_w60",
        "orthogonalized_factor_strength_w120",
        "late_volume_ratio_robust_w20",
        "late_volume_ratio_robust_w60",
        "late_volume_ratio_robust_w120",
        "closing_order_trade_correlation_w20",
        "closing_order_trade_correlation_w60",
        "closing_order_trade_correlation_w120",
        "order_trade_correlation_w20",
        "order_trade_correlation_w60",
        "order_trade_correlation_w120",
        "average_single_trade_outflow_ratio_w20",
        "average_single_trade_outflow_ratio_w60",
        "average_single_trade_outflow_ratio_w120",
        "large_order_net_inflow_ratio_w20",
        "large_order_net_inflow_ratio_w60",
        "large_order_net_inflow_ratio_w120",
        "large_buy_amount_concentration_w20",
        "large_buy_amount_concentration_w60",
        "large_buy_amount_concentration_w120",
        "transaction_order_correlation_composite_w20",
        "transaction_order_correlation_composite_w60",
        "transaction_order_correlation_composite_w120",
    ],
)

# ------------------------------------------------------------
# 30. 高频交易：国内证券市场的明日之星
# ------------------------------------------------------------

add_report_factors(
    "高频交易：国内证券市场的明日之星",
    [
        "short_horizon_trend_signal_w20",
        "short_horizon_trend_signal_w60",
        "short_horizon_trend_signal_w120",
        "trend_entry_strength_w20",
        "trend_entry_strength_w60",
        "trend_entry_strength_w120",
        "trend_exit_pressure_w20",
        "trend_exit_pressure_w60",
        "trend_exit_pressure_w120",
        "intraday_spread_zscore_w20",
        "intraday_spread_zscore_w60",
        "intraday_spread_zscore_w120",
        "spread_channel_breakout_w20",
        "spread_channel_breakout_w60",
        "spread_channel_breakout_w120",
        "spread_mean_reversion_signal_w20",
        "spread_mean_reversion_signal_w60",
        "spread_mean_reversion_signal_w120",
        "bid_ask_spread_cost_w20",
        "bid_ask_spread_cost_w60",
        "bid_ask_spread_cost_w120",
        "execution_speed_pressure_w20",
        "execution_speed_pressure_w60",
        "execution_speed_pressure_w120",
        "stop_loss_trigger_density_w20",
        "stop_loss_trigger_density_w60",
        "stop_loss_trigger_density_w120",
    ],
)

# ------------------------------------------------------------
# 31. 高频数据在行业轮动中的应用
# ------------------------------------------------------------

add_report_factors(
    "高频数据在行业轮动中的应用",
    [
        "sector_realized_skewness_w20",
        "sector_realized_skewness_w60",
        "sector_realized_skewness_w120",
        "sector_downside_volatility_ratio_w20",
        "sector_downside_volatility_ratio_w60",
        "sector_downside_volatility_ratio_w120",
        "sector_hf_moment_rotation_score_w20",
        "sector_hf_moment_rotation_score_w60",
        "sector_hf_moment_rotation_score_w120",
        "sector_downside_risk_rotation_score_w20",
        "sector_downside_risk_rotation_score_w60",
        "sector_downside_risk_rotation_score_w120",
        "domain_frequency_sensitivity_score_w20",
        "domain_frequency_sensitivity_score_w60",
        "domain_frequency_sensitivity_score_w120",
        "rebalance_frequency_sensitivity_score_w20",
        "rebalance_frequency_sensitivity_score_w60",
        "rebalance_frequency_sensitivity_score_w120",
        "coin_cluster_rotation_strength_w20",
        "coin_cluster_rotation_strength_w60",
        "coin_cluster_rotation_strength_w120",
        "cross_sectional_group_momentum_residual_w20",
        "cross_sectional_group_momentum_residual_w60",
        "cross_sectional_group_momentum_residual_w120",
    ],
)

# ------------------------------------------------------------
# 32. 高频选股因子周报
# ------------------------------------------------------------

add_report_factors(
    "高频选股因子周报",
    [
        "weekly_hf_skewness_return_w20",
        "weekly_hf_skewness_return_w60",
        "weekly_hf_skewness_return_w120",
        "weekly_downside_volatility_ratio_w20",
        "weekly_downside_volatility_ratio_w60",
        "weekly_downside_volatility_ratio_w120",
        "open_avg_net_bid_change_rate_w20",
        "open_avg_net_bid_change_rate_w60",
        "open_avg_net_bid_change_rate_w120",
        "weekly_late_volume_ratio_w20",
        "weekly_late_volume_ratio_w60",
        "weekly_late_volume_ratio_w120",
        "weekly_price_volume_corr_w20",
        "weekly_price_volume_corr_w60",
        "weekly_price_volume_corr_w120",
        "weekly_improved_reversal_w20",
        "weekly_improved_reversal_w60",
        "weekly_improved_reversal_w120",
        "weekly_avg_trade_outflow_amount_ratio_w20",
        "weekly_avg_trade_outflow_amount_ratio_w60",
        "weekly_avg_trade_outflow_amount_ratio_w120",
        "weekly_large_order_return_w20",
        "weekly_large_order_return_w60",
        "weekly_large_order_return_w120",
        "weekly_hf_factor_winrate_score_w20",
        "weekly_hf_factor_winrate_score_w60",
        "weekly_hf_factor_winrate_score_w120",
    ],
)

# ------------------------------------------------------------
# 33. 高频因子在不同周期和域下的表现及影响因素分析
# ------------------------------------------------------------

add_report_factors(
    "高频因子在不同周期和域下的表现及影响因素分析",
    [
        "composite_hf_factor_equal_weight_w20",
        "composite_hf_factor_equal_weight_w60",
        "composite_hf_factor_equal_weight_w120",
        "composite_hf_factor_ic_weight_w20",
        "composite_hf_factor_ic_weight_w60",
        "composite_hf_factor_ic_weight_w120",
        "composite_hf_factor_icir_weight_w20",
        "composite_hf_factor_icir_weight_w60",
        "composite_hf_factor_icir_weight_w120",
        "hf_factor_short_side_contribution_w20",
        "hf_factor_short_side_contribution_w60",
        "hf_factor_short_side_contribution_w120",
        "hf_factor_long_side_contribution_w20",
        "hf_factor_long_side_contribution_w60",
        "hf_factor_long_side_contribution_w120",
        "hf_factor_tail_return_spread_w20",
        "hf_factor_tail_return_spread_w60",
        "hf_factor_tail_return_spread_w120",
        "worst_tail_market_drop_w20",
        "worst_tail_market_drop_w60",
        "worst_tail_market_drop_w120",
        "hf_factor_regime_tree_score_w20",
        "hf_factor_regime_tree_score_w60",
        "hf_factor_regime_tree_score_w120",
        "hf_factor_environment_sensitivity_w20",
        "hf_factor_environment_sensitivity_w60",
        "hf_factor_environment_sensitivity_w120",
    ],
)

# ------------------------------------------------------------
# 34. 基于直观逻辑和机器学习的高频数据低频化应用
# ------------------------------------------------------------

add_report_factors(
    "基于直观逻辑和机器学习的高频数据低频化应用",
    [
        "open_buying_willingness_ratio_w20",
        "open_buying_willingness_ratio_w60",
        "open_buying_willingness_ratio_w120",
        "intraday_buying_willingness_ratio_w20",
        "intraday_buying_willingness_ratio_w60",
        "intraday_buying_willingness_ratio_w120",
        "midday_buying_willingness_ratio_w20",
        "midday_buying_willingness_ratio_w60",
        "midday_buying_willingness_ratio_w120",
        "open_buying_willingness_strength_w20",
        "open_buying_willingness_strength_w60",
        "open_buying_willingness_strength_w120",
        "intraday_buying_willingness_strength_w20",
        "intraday_buying_willingness_strength_w60",
        "intraday_buying_willingness_strength_w120",
        "midday_buying_willingness_strength_w20",
        "midday_buying_willingness_strength_w60",
        "midday_buying_willingness_strength_w120",
        "open_buying_willingness_minus_active_buy_w20",
        "open_buying_willingness_minus_active_buy_w60",
        "open_buying_willingness_minus_active_buy_w120",
        "buying_willingness_active_buy_interaction_w20",
        "buying_willingness_active_buy_interaction_w60",
        "buying_willingness_active_buy_interaction_w120",
        "ml_alpha_intraday_active_buy_volatility_w20",
        "ml_alpha_intraday_active_buy_volatility_w60",
        "ml_alpha_intraday_active_buy_volatility_w120",
        "ml_alpha_open_close_amount_mean_w20",
        "ml_alpha_open_close_amount_mean_w60",
        "ml_alpha_open_close_amount_mean_w120",
        "ml_alpha_open_close_to_mid_amount_ratio_w20",
        "ml_alpha_open_close_to_mid_amount_ratio_w60",
        "ml_alpha_open_close_to_mid_amount_ratio_w120",
        "ml_alpha_open_amount_weakness_w20",
        "ml_alpha_open_amount_weakness_w60",
        "ml_alpha_open_amount_weakness_w120",
        "machine_mined_hf_lowfreq_composite_w20",
        "machine_mined_hf_lowfreq_composite_w60",
        "machine_mined_hf_lowfreq_composite_w120",
    ],
)

# ------------------------------------------------------------
# 35. 买卖单数据中的Alpha
# ------------------------------------------------------------

add_report_factors(
    "买卖单数据中的Alpha",
    [
        "large_buy_order_amount_ratio_w20",
        "large_buy_order_amount_ratio_w60",
        "large_buy_order_amount_ratio_w120",
        "large_sell_order_amount_ratio_w20",
        "large_sell_order_amount_ratio_w60",
        "large_sell_order_amount_ratio_w120",
        "large_buy_sell_amount_ratio_diff_w20",
        "large_buy_sell_amount_ratio_diff_w60",
        "large_buy_sell_amount_ratio_diff_w120",
        "large_buy_sell_amount_ratio_spread_w20",
        "large_buy_sell_amount_ratio_spread_w60",
        "large_buy_sell_amount_ratio_spread_w120",
        "buy_order_concentration_w20",
        "buy_order_concentration_w60",
        "buy_order_concentration_w120",
        "sell_order_concentration_w20",
        "sell_order_concentration_w60",
        "sell_order_concentration_w120",
        "buy_sell_order_concentration_diff_w20",
        "buy_sell_order_concentration_diff_w60",
        "buy_sell_order_concentration_diff_w120",
        "order_concentration_composite_w20",
        "order_concentration_composite_w60",
        "order_concentration_composite_w120",
        "transaction_to_order_reconstruction_quality_w20",
        "transaction_to_order_reconstruction_quality_w60",
        "transaction_to_order_reconstruction_quality_w120",
    ],
)

# ------------------------------------------------------------
# 36. 日内分时成交中的玄机
# ------------------------------------------------------------

add_report_factors(
    "日内分时成交中的玄机",
    [
        "avg_trade_amount_w20",
        "avg_trade_amount_w60",
        "avg_trade_amount_w120",
        "avg_trade_inflow_amount_ratio_w20",
        "avg_trade_inflow_amount_ratio_w60",
        "avg_trade_inflow_amount_ratio_w120",
        "avg_trade_outflow_amount_ratio_w20",
        "avg_trade_outflow_amount_ratio_w60",
        "avg_trade_outflow_amount_ratio_w120",
        "avg_trade_inflow_outflow_amount_ratio_w20",
        "avg_trade_inflow_outflow_amount_ratio_w60",
        "avg_trade_inflow_outflow_amount_ratio_w120",
        "large_order_net_inflow_rate_w20",
        "large_order_net_inflow_rate_w60",
        "large_order_net_inflow_rate_w120",
        "large_order_driven_return_w20",
        "large_order_driven_return_w60",
        "large_order_driven_return_w120",
        "large_order_capital_flow_pressure_w20",
        "large_order_capital_flow_pressure_w60",
        "large_order_capital_flow_pressure_w120",
        "trade_count_adjusted_amount_pressure_w20",
        "trade_count_adjusted_amount_pressure_w60",
        "trade_count_adjusted_amount_pressure_w120",
        "large_trade_window_return_contribution_w20",
        "large_trade_window_return_contribution_w60",
        "large_trade_window_return_contribution_w120",
    ],
)

# ------------------------------------------------------------
# 37. 如何利用高频因子的空头效应
# ------------------------------------------------------------

add_report_factors(
    "如何利用高频因子的空头效应",
    [
        "hf_short_candidate_indicator_w20",
        "hf_short_candidate_indicator_w60",
        "hf_short_candidate_indicator_w120",
        "hf_short_threshold_score_w20",
        "hf_short_threshold_score_w60",
        "hf_short_threshold_score_w120",
        "hf_short_pre_exclusion_signal_w20",
        "hf_short_pre_exclusion_signal_w60",
        "hf_short_pre_exclusion_signal_w120",
        "hf_short_dummy_factor_w20",
        "hf_short_dummy_factor_w60",
        "hf_short_dummy_factor_w120",
        "hf_short_deviation_constraint_score_w20",
        "hf_short_deviation_constraint_score_w60",
        "hf_short_deviation_constraint_score_w120",
        "hf_short_post_exclusion_signal_w20",
        "hf_short_post_exclusion_signal_w60",
        "hf_short_post_exclusion_signal_w120",
        "hf_short_side_alpha_strength_w20",
        "hf_short_side_alpha_strength_w60",
        "hf_short_side_alpha_strength_w120",
        "hf_short_side_persistence_w20",
        "hf_short_side_persistence_w60",
        "hf_short_side_persistence_w120",
        "avoid_tail_risk_coin_score_w20",
        "avoid_tail_risk_coin_score_w60",
        "avoid_tail_risk_coin_score_w120",
    ],
)

# ------------------------------------------------------------
# 38. Level2行情选股因子初探
# ------------------------------------------------------------

add_report_factors(
    "Level2行情选股因子初探",
    [
        "continuous_auction_trade_ratio_w20",
        "continuous_auction_trade_ratio_w60",
        "continuous_auction_trade_ratio_w120",
        "super_large_order_trade_ratio_w20",
        "super_large_order_trade_ratio_w60",
        "super_large_order_trade_ratio_w120",
        "large_order_trade_ratio_w20",
        "large_order_trade_ratio_w60",
        "large_order_trade_ratio_w120",
        "medium_order_trade_ratio_w20",
        "medium_order_trade_ratio_w60",
        "medium_order_trade_ratio_w120",
        "small_order_trade_ratio_w20",
        "small_order_trade_ratio_w60",
        "small_order_trade_ratio_w120",
        "super_large_order_net_buy_ratio_w20",
        "super_large_order_net_buy_ratio_w60",
        "super_large_order_net_buy_ratio_w120",
        "large_order_net_buy_ratio_w20",
        "large_order_net_buy_ratio_w60",
        "large_order_net_buy_ratio_w120",
        "medium_order_net_buy_ratio_w20",
        "medium_order_net_buy_ratio_w60",
        "medium_order_net_buy_ratio_w120",
        "small_order_net_buy_ratio_w20",
        "small_order_net_buy_ratio_w60",
        "small_order_net_buy_ratio_w120",
        "late_session_net_buy_ratio_w20",
        "late_session_net_buy_ratio_w60",
        "late_session_net_buy_ratio_w120",
        "level2_trade_size_structure_score_w20",
        "level2_trade_size_structure_score_w60",
        "level2_trade_size_structure_score_w120",
    ],
)

# ------------------------------------------------------------
# 39. 基于K线最短路径构造的非流动性因子
# ------------------------------------------------------------

add_report_factors(
    "基于K线最短路径构造的非流动性因子",
    [
        "kline_shortest_path_illiquidity_w20",
        "kline_shortest_path_illiquidity_w60",
        "kline_shortest_path_illiquidity_w120",
        "classic_amihud_illiquidity_w20",
        "classic_amihud_illiquidity_w60",
        "classic_amihud_illiquidity_w120",
        "shortest_path_to_classic_illiquidity_diff_w20",
        "shortest_path_to_classic_illiquidity_diff_w60",
        "shortest_path_to_classic_illiquidity_diff_w120",
        "ts_illiquidity_w20",
        "ts_illiquidity_w60",
        "ts_illiquidity_w120",
        "kline_path_efficiency_w20",
        "kline_path_efficiency_w60",
        "kline_path_efficiency_w120",
        "kline_intrabar_oscillation_intensity_w20",
        "kline_intrabar_oscillation_intensity_w60",
        "kline_intrabar_oscillation_intensity_w120",
        "volume_adjusted_price_impact_w20",
        "volume_adjusted_price_impact_w60",
        "volume_adjusted_price_impact_w120",
        "high_frequency_illiquidity_precision_score_w20",
        "high_frequency_illiquidity_precision_score_w60",
        "high_frequency_illiquidity_precision_score_w120",
    ],
)

# ------------------------------------------------------------
# 40. 基于限价订单簿的最优高频做市商策略研究
# ------------------------------------------------------------

add_report_factors(
    "基于限价订单簿的最优高频做市商策略研究",
    [
        "market_making_spread_state_w20",
        "market_making_spread_state_w60",
        "market_making_spread_state_w120",
        "inventory_risk_pressure_w20",
        "inventory_risk_pressure_w60",
        "inventory_risk_pressure_w120",
        "inventory_penalty_score_w20",
        "inventory_penalty_score_w60",
        "inventory_penalty_score_w120",
        "execution_intensity_bid_w20",
        "execution_intensity_bid_w60",
        "execution_intensity_bid_w120",
        "execution_intensity_ask_w20",
        "execution_intensity_ask_w60",
        "execution_intensity_ask_w120",
        "bid_quote_fill_probability_w20",
        "bid_quote_fill_probability_w60",
        "bid_quote_fill_probability_w120",
        "ask_quote_fill_probability_w20",
        "ask_quote_fill_probability_w60",
        "ask_quote_fill_probability_w120",
        "optimal_bid_quote_distance_w20",
        "optimal_bid_quote_distance_w60",
        "optimal_bid_quote_distance_w120",
        "optimal_ask_quote_distance_w20",
        "optimal_ask_quote_distance_w60",
        "optimal_ask_quote_distance_w120",
        "market_making_utility_score_w20",
        "market_making_utility_score_w60",
        "market_making_utility_score_w120",
    ],
)

# ------------------------------------------------------------
# 41. 基于限价订单簿信息的交易策略
# ------------------------------------------------------------

add_report_factors(
    "基于限价订单簿信息的交易策略",
    [
        "lob_state_depth_imbalance_w20",
        "lob_state_depth_imbalance_w60",
        "lob_state_depth_imbalance_w120",
        "lob_midprice_move_probability_w20",
        "lob_midprice_move_probability_w60",
        "lob_midprice_move_probability_w120",
        "lob_limit_order_fill_probability_w20",
        "lob_limit_order_fill_probability_w60",
        "lob_limit_order_fill_probability_w120",
        "lob_bid_side_resilience_w20",
        "lob_bid_side_resilience_w60",
        "lob_bid_side_resilience_w120",
        "lob_ask_side_resilience_w20",
        "lob_ask_side_resilience_w60",
        "lob_ask_side_resilience_w120",
        "lob_order_flow_arrival_rate_w20",
        "lob_order_flow_arrival_rate_w60",
        "lob_order_flow_arrival_rate_w120",
        "lob_cancellation_intensity_w20",
        "lob_cancellation_intensity_w60",
        "lob_cancellation_intensity_w120",
        "lob_depth_decay_slope_w20",
        "lob_depth_decay_slope_w60",
        "lob_depth_decay_slope_w120",
        "lob_queue_position_advantage_w20",
        "lob_queue_position_advantage_w60",
        "lob_queue_position_advantage_w120",
    ],
)

# ------------------------------------------------------------
# 42. 基于逐笔成交数据的高频因子梳理
# ------------------------------------------------------------

add_report_factors(
    "基于逐笔成交数据的高频因子梳理",
    [
        "tick_large_buy_amount_ratio_w20",
        "tick_large_buy_amount_ratio_w60",
        "tick_large_buy_amount_ratio_w120",
        "tick_buy_order_concentration_w20",
        "tick_buy_order_concentration_w60",
        "tick_buy_order_concentration_w120",
        "intraday_active_buy_ratio_full_day_w20",
        "intraday_active_buy_ratio_full_day_w60",
        "intraday_active_buy_ratio_full_day_w120",
        "open_net_active_buy_strength_w20",
        "open_net_active_buy_strength_w60",
        "open_net_active_buy_strength_w120",
        "open_informed_active_sell_ratio_w20",
        "open_informed_active_sell_ratio_w60",
        "open_informed_active_sell_ratio_w120",
        "late_informed_active_buy_ratio_w20",
        "late_informed_active_buy_ratio_w60",
        "late_informed_active_buy_ratio_w120",
        "tick_factor_halfmonth_strength_w20",
        "tick_factor_halfmonth_strength_w60",
        "tick_factor_halfmonth_strength_w120",
        "tick_factor_weekly_strength_w20",
        "tick_factor_weekly_strength_w60",
        "tick_factor_weekly_strength_w120",
        "tick_factor_incremental_combo_score_w20",
        "tick_factor_incremental_combo_score_w60",
        "tick_factor_incremental_combo_score_w120",
    ],
)

# ------------------------------------------------------------
# 43. 结合中高频信息的指数增强策略
# ------------------------------------------------------------

add_report_factors(
    "结合中高频信息的指数增强策略",
    [
        "formula_alpha_signal_raw_w20",
        "formula_alpha_signal_raw_w60",
        "formula_alpha_signal_raw_w120",
        "formula_alpha_daily_transformed_w20",
        "formula_alpha_daily_transformed_w60",
        "formula_alpha_daily_transformed_w120",
        "formula_alpha_monthly_transformed_w20",
        "formula_alpha_monthly_transformed_w60",
        "formula_alpha_monthly_transformed_w120",
        "hf_to_lf_decay_weighted_signal_w20",
        "hf_to_lf_decay_weighted_signal_w60",
        "hf_to_lf_decay_weighted_signal_w120",
        "intraday_signal_zscore_w20",
        "intraday_signal_zscore_w60",
        "intraday_signal_zscore_w120",
        "daily_downsampled_hf_signal_w20",
        "daily_downsampled_hf_signal_w60",
        "daily_downsampled_hf_signal_w120",
        "monthly_downsampled_hf_signal_w20",
        "monthly_downsampled_hf_signal_w60",
        "monthly_downsampled_hf_signal_w120",
        "long_horizon_hf_alpha_composite_w20",
        "long_horizon_hf_alpha_composite_w60",
        "long_horizon_hf_alpha_composite_w120",
        "hf_lf_information_bridge_score_w20",
        "hf_lf_information_bridge_score_w60",
        "hf_lf_information_bridge_score_w120",
    ],
)

# ------------------------------------------------------------
# 44. 量价关系的高频乐章
# ------------------------------------------------------------

add_report_factors(
    "量价关系的高频乐章",
    [
        "copa_factor_w20",
        "copa_factor_w60",
        "copa_factor_w120",
        "cora_factor_w20",
        "cora_factor_w60",
        "cora_factor_w120",
        "cora_a_factor_w20",
        "cora_a_factor_w60",
        "cora_a_factor_w120",
        "cora_r_factor_w20",
        "cora_r_factor_w60",
        "cora_r_factor_w120",
        "adj_cora_a_factor_w20",
        "adj_cora_a_factor_w60",
        "adj_cora_a_factor_w120",
        "adj_cora_r_factor_w20",
        "adj_cora_r_factor_w60",
        "adj_cora_r_factor_w120",
        "price_volume_same_direction_break_w20",
        "price_volume_same_direction_break_w60",
        "price_volume_same_direction_break_w120",
        "price_volume_lagged_alignment_w20",
        "price_volume_lagged_alignment_w60",
        "price_volume_lagged_alignment_w120",
        "volume_leads_price_corr_w20",
        "volume_leads_price_corr_w60",
        "volume_leads_price_corr_w120",
        "price_leads_volume_corr_w20",
        "price_leads_volume_corr_w60",
        "price_leads_volume_corr_w120",
        "intraday_amount_distribution_adjusted_cora_w20",
        "intraday_amount_distribution_adjusted_cora_w60",
        "intraday_amount_distribution_adjusted_cora_w120",
        "low_liquidity_adjusted_price_volume_score_w20",
        "low_liquidity_adjusted_price_volume_score_w60",
        "low_liquidity_adjusted_price_volume_score_w120",
        "hf_price_volume_entanglement_score_w20",
        "hf_price_volume_entanglement_score_w60",
        "hf_price_volume_entanglement_score_w120",
    ],
)

# ------------------------------------------------------------
# 45. 基于机器学习的订单簿高频交易策略
# ------------------------------------------------------------

add_report_factors(
    "基于机器学习的订单簿高频交易策略",
    [
        "svm_lob_direction_score_w20",
        "svm_lob_direction_score_w60",
        "svm_lob_direction_score_w120",
        "lob_depth_feature_score_w20",
        "lob_depth_feature_score_w60",
        "lob_depth_feature_score_w120",
        "lob_slope_feature_score_w20",
        "lob_slope_feature_score_w60",
        "lob_slope_feature_score_w120",
        "lob_relative_spread_feature_w20",
        "lob_relative_spread_feature_w60",
        "lob_relative_spread_feature_w120",
        "lob_momentum_feature_w20",
        "lob_momentum_feature_w60",
        "lob_momentum_feature_w120",
        "lob_price_change_classification_confidence_w20",
        "lob_price_change_classification_confidence_w60",
        "lob_price_change_classification_confidence_w120",
        "lob_trade_opportunity_density_w20",
        "lob_trade_opportunity_density_w60",
        "lob_trade_opportunity_density_w120",
        "lob_ml_prediction_accuracy_proxy_w20",
        "lob_ml_prediction_accuracy_proxy_w60",
        "lob_ml_prediction_accuracy_proxy_w120",
    ],
)

# ------------------------------------------------------------
# 46. 日内残差高阶矩与股票收益
# ------------------------------------------------------------

add_report_factors(
    "日内残差高阶矩与股票收益",
    [
        "intraday_idiosyncratic_volatility_w20",
        "intraday_idiosyncratic_volatility_w60",
        "intraday_idiosyncratic_volatility_w120",
        "intraday_idiosyncratic_skewness_w20",
        "intraday_idiosyncratic_skewness_w60",
        "intraday_idiosyncratic_skewness_w120",
        "intraday_idiosyncratic_kurtosis_w20",
        "intraday_idiosyncratic_kurtosis_w60",
        "intraday_idiosyncratic_kurtosis_w120",
        "intraday_residual_higher_moment_composite_w20",
        "intraday_residual_higher_moment_composite_w60",
        "intraday_residual_higher_moment_composite_w120",
        "intraday_residual_moment_decay_speed_w20",
        "intraday_residual_moment_decay_speed_w60",
        "intraday_residual_moment_decay_speed_w120",
        "intraday_residual_skew_kurt_overlap_w20",
        "intraday_residual_skew_kurt_overlap_w60",
        "intraday_residual_skew_kurt_overlap_w120",
        "idiosyncratic_skewness_minus_kurtosis_score_w20",
        "idiosyncratic_skewness_minus_kurtosis_score_w60",
        "idiosyncratic_skewness_minus_kurtosis_score_w120",
    ],
)

# ------------------------------------------------------------
# 47. 订单簿上的alpha
# ------------------------------------------------------------

add_report_factors(
    "订单簿上的alpha",
    [
        "orderbook_spread_alpha_w20",
        "orderbook_spread_alpha_w60",
        "orderbook_spread_alpha_w120",
        "lob_bid_ask_order_strength_spread_w20",
        "lob_bid_ask_order_strength_spread_w60",
        "lob_bid_ask_order_strength_spread_w120",
        "lob_buyer_depth_advantage_w20",
        "lob_buyer_depth_advantage_w60",
        "lob_buyer_depth_advantage_w120",
        "lob_seller_depth_advantage_w20",
        "lob_seller_depth_advantage_w60",
        "lob_seller_depth_advantage_w120",
        "lob_buyrate_w20",
        "lob_buyrate_w60",
        "lob_buyrate_w120",
        "spread_buyrate_corr_w20",
        "spread_buyrate_corr_w60",
        "spread_buyrate_corr_w120",
        "tick_to_daily_spread_alpha_w20",
        "tick_to_daily_spread_alpha_w60",
        "tick_to_daily_spread_alpha_w120",
        "neutralized_orderbook_spread_alpha_w20",
        "neutralized_orderbook_spread_alpha_w60",
        "neutralized_orderbook_spread_alpha_w120",
        "lob_pressure_absorption_score_w20",
        "lob_pressure_absorption_score_w60",
        "lob_pressure_absorption_score_w120",
    ],
)

# ------------------------------------------------------------
# 48. 剔除高频多因子空头组合后的沪深300指数增强策略
# ------------------------------------------------------------

add_report_factors(
    "剔除高频多因子空头组合后的沪深300指数增强策略",
    [
        "multi_hf_short_zscore_composite_w20",
        "multi_hf_short_zscore_composite_w60",
        "multi_hf_short_zscore_composite_w120",
        "multi_hf_short_regression_composite_w20",
        "multi_hf_short_regression_composite_w60",
        "multi_hf_short_regression_composite_w120",
        "multi_hf_short_portfolio_composite_w20",
        "multi_hf_short_portfolio_composite_w60",
        "multi_hf_short_portfolio_composite_w120",
        "orthogonal_hf_short_composite_w20",
        "orthogonal_hf_short_composite_w60",
        "orthogonal_hf_short_composite_w120",
        "icir_weighted_hf_short_composite_w20",
        "icir_weighted_hf_short_composite_w60",
        "icir_weighted_hf_short_composite_w120",
        "equal_weighted_hf_short_composite_w20",
        "equal_weighted_hf_short_composite_w60",
        "equal_weighted_hf_short_composite_w120",
        "hf_short_exclusion_threshold_sensitivity_w20",
        "hf_short_exclusion_threshold_sensitivity_w60",
        "hf_short_exclusion_threshold_sensitivity_w120",
        "short_portfolio_membership_count_w20",
        "short_portfolio_membership_count_w60",
        "short_portfolio_membership_count_w120",
    ],
)

# ------------------------------------------------------------
# 49. 买卖压力失衡：利用高频数据拓展盘口数据
# ------------------------------------------------------------

add_report_factors(
    "买卖压力失衡：利用高频数据拓展盘口数据",
    [
        "extended_orderbook_buy_pressure_w20",
        "extended_orderbook_buy_pressure_w60",
        "extended_orderbook_buy_pressure_w120",
        "extended_orderbook_sell_pressure_w20",
        "extended_orderbook_sell_pressure_w60",
        "extended_orderbook_sell_pressure_w120",
        "buy_sell_pressure_imbalance_w20",
        "buy_sell_pressure_imbalance_w60",
        "buy_sell_pressure_imbalance_w120",
        "buy_pressure_dominance_event_w20",
        "buy_pressure_dominance_event_w60",
        "buy_pressure_dominance_event_w120",
        "sell_pressure_dominance_event_w20",
        "sell_pressure_dominance_event_w60",
        "sell_pressure_dominance_event_w120",
        "pressure_imbalance_reversal_score_w20",
        "pressure_imbalance_reversal_score_w60",
        "pressure_imbalance_reversal_score_w120",
        "tick_probe_orderbook_support_w20",
        "tick_probe_orderbook_support_w60",
        "tick_probe_orderbook_support_w120",
        "tick_probe_orderbook_resistance_w20",
        "tick_probe_orderbook_resistance_w60",
        "tick_probe_orderbook_resistance_w120",
        "orderbook_chip_distribution_score_w20",
        "orderbook_chip_distribution_score_w60",
        "orderbook_chip_distribution_score_w120",
    ],
)

# ------------------------------------------------------------
# 50. 分时K线中的alpha
# ------------------------------------------------------------

add_report_factors(
    "分时K线中的alpha",
    [
        "gp_intraday_kline_alpha_composite_w20",
        "gp_intraday_kline_alpha_composite_w60",
        "gp_intraday_kline_alpha_composite_w120",
        "gp_factor_fitness_ic_score_w20",
        "gp_factor_fitness_ic_score_w60",
        "gp_factor_fitness_ic_score_w120",
        "gp_factor_fitness_long_return_score_w20",
        "gp_factor_fitness_long_return_score_w60",
        "gp_factor_fitness_long_return_score_w120",
        "gp_factor_fitness_monotonicity_score_w20",
        "gp_factor_fitness_monotonicity_score_w60",
        "gp_factor_fitness_monotonicity_score_w120",
        "gp_expression_complexity_penalty_w20",
        "gp_expression_complexity_penalty_w60",
        "gp_expression_complexity_penalty_w120",
        "gp_expression_out_of_sample_decay_w20",
        "gp_expression_out_of_sample_decay_w60",
        "gp_expression_out_of_sample_decay_w120",
        "gp_expression_pairwise_corr_control_w20",
        "gp_expression_pairwise_corr_control_w60",
        "gp_expression_pairwise_corr_control_w120",
        "kline_amount_high_covariance_w20",
        "kline_amount_high_covariance_w60",
        "kline_amount_high_covariance_w120",
        "kline_amount_high_negative_covariance_alpha_w20",
        "kline_amount_high_negative_covariance_alpha_w60",
        "kline_amount_high_negative_covariance_alpha_w120",
        "kline_close_minus_low_mean_reversal_w20",
        "kline_close_minus_low_mean_reversal_w60",
        "kline_close_minus_low_mean_reversal_w120",
        "kline_close_low_gap_overextension_w20",
        "kline_close_low_gap_overextension_w60",
        "kline_close_low_gap_overextension_w120",
        "kline_log_volume_delta_volatility_w20",
        "kline_log_volume_delta_volatility_w60",
        "kline_log_volume_delta_volatility_w120",
        "kline_volume_change_instability_w20",
        "kline_volume_change_instability_w60",
        "kline_volume_change_instability_w120",
        "kline_correlation_operator_alpha_w20",
        "kline_correlation_operator_alpha_w60",
        "kline_correlation_operator_alpha_w120",
        "kline_covariance_operator_alpha_w20",
        "kline_covariance_operator_alpha_w60",
        "kline_covariance_operator_alpha_w120",
        "kline_regbeta_operator_alpha_w20",
        "kline_regbeta_operator_alpha_w60",
        "kline_regbeta_operator_alpha_w120",
        "kline_regresid_operator_alpha_w20",
        "kline_regresid_operator_alpha_w60",
        "kline_regresid_operator_alpha_w120",
        "kline_ts_rank_operator_alpha_w20",
        "kline_ts_rank_operator_alpha_w60",
        "kline_ts_rank_operator_alpha_w120",
        "kline_pctchange_operator_alpha_w20",
        "kline_pctchange_operator_alpha_w60",
        "kline_pctchange_operator_alpha_w120",
        "intraday_5m_formula_alpha_pool_score_w20",
        "intraday_5m_formula_alpha_pool_score_w60",
        "intraday_5m_formula_alpha_pool_score_w120",
        "intraday_15m_formula_alpha_pool_score_w20",
        "intraday_15m_formula_alpha_pool_score_w60",
        "intraday_15m_formula_alpha_pool_score_w120",
        "intraday_30m_formula_alpha_pool_score_w20",
        "intraday_30m_formula_alpha_pool_score_w60",
        "intraday_30m_formula_alpha_pool_score_w120",
        "intraday_1h_formula_alpha_pool_score_w20",
        "intraday_1h_formula_alpha_pool_score_w60",
        "intraday_1h_formula_alpha_pool_score_w120",
    ],
)

# ------------------------------------------------------------
# 51. 跳跃Beta与连续Beta
# ------------------------------------------------------------

add_report_factors(
    "跳跃Beta与连续Beta",
    [
        "continuous_beta_to_market_w20",
        "continuous_beta_to_market_w60",
        "continuous_beta_to_market_w120",
        "jump_beta_to_market_w20",
        "jump_beta_to_market_w60",
        "jump_beta_to_market_w120",
        "jump_minus_continuous_beta_w20",
        "jump_minus_continuous_beta_w60",
        "jump_minus_continuous_beta_w120",
        "jump_to_continuous_beta_ratio_w20",
        "jump_to_continuous_beta_ratio_w60",
        "jump_to_continuous_beta_ratio_w120",
        "beta_decomposition_residual_risk_w20",
        "beta_decomposition_residual_risk_w60",
        "beta_decomposition_residual_risk_w120",
        "realized_variance_rv_w20",
        "realized_variance_rv_w60",
        "realized_variance_rv_w120",
        "bipower_variation_bv_w20",
        "bipower_variation_bv_w60",
        "bipower_variation_bv_w120",
        "jump_variation_rv_minus_bv_w20",
        "jump_variation_rv_minus_bv_w60",
        "jump_variation_rv_minus_bv_w120",
        "market_jump_sensitivity_w20",
        "market_jump_sensitivity_w60",
        "market_jump_sensitivity_w120",
        "market_continuous_sensitivity_w20",
        "market_continuous_sensitivity_w60",
        "market_continuous_sensitivity_w120",
        "tod_volatility_adjusted_jump_score_w20",
        "tod_volatility_adjusted_jump_score_w60",
        "tod_volatility_adjusted_jump_score_w120",
        "bayesian_shrinked_beta_w20",
        "bayesian_shrinked_beta_w60",
        "bayesian_shrinked_beta_w120",
        "beta_estimation_error_proxy_w20",
        "beta_estimation_error_proxy_w60",
        "beta_estimation_error_proxy_w120",
        "low_jump_beta_defensive_score_w20",
        "low_jump_beta_defensive_score_w60",
        "low_jump_beta_defensive_score_w120",
        "low_continuous_beta_defensive_score_w20",
        "low_continuous_beta_defensive_score_w60",
        "low_continuous_beta_defensive_score_w120",
        "continuous_beta_to_btc_w20",
        "continuous_beta_to_btc_w60",
        "continuous_beta_to_btc_w120",
        "jump_beta_to_btc_w20",
        "jump_beta_to_btc_w60",
        "jump_beta_to_btc_w120",
        "continuous_beta_to_eth_w20",
        "continuous_beta_to_eth_w60",
        "continuous_beta_to_eth_w120",
        "jump_beta_to_eth_w20",
        "jump_beta_to_eth_w60",
        "jump_beta_to_eth_w120",
    ],
)

# ------------------------------------------------------------
# 52. 信息分布均匀度UID
# ------------------------------------------------------------

add_report_factors(
    "信息分布均匀度UID",
    [
        "uid_information_distribution_uniformity_w20",
        "uid_information_distribution_uniformity_w60",
        "uid_information_distribution_uniformity_w120",
        "daily_hf_volatility_mean_w20",
        "daily_hf_volatility_mean_w60",
        "daily_hf_volatility_mean_w120",
        "daily_hf_volatility_std_w20",
        "daily_hf_volatility_std_w60",
        "daily_hf_volatility_std_w120",
        "daily_hf_volatility_cv_w20",
        "daily_hf_volatility_cv_w60",
        "daily_hf_volatility_cv_w120",
        "uid_devolatility_residual_w20",
        "uid_devolatility_residual_w60",
        "uid_devolatility_residual_w120",
        "pure_uid_style_neutralized_w20",
        "pure_uid_style_neutralized_w60",
        "pure_uid_style_neutralized_w120",
        "information_shock_intensity_w20",
        "information_shock_intensity_w60",
        "information_shock_intensity_w120",
        "information_flow_irregularity_w20",
        "information_flow_irregularity_w60",
        "information_flow_irregularity_w120",
        "volatility_of_volatility_uid_w20",
        "volatility_of_volatility_uid_w60",
        "volatility_of_volatility_uid_w120",
        "uid_minus_traditional_volatility_w20",
        "uid_minus_traditional_volatility_w60",
        "uid_minus_traditional_volatility_w120",
        "uid_to_vol20_ratio_w20",
        "uid_to_vol20_ratio_w60",
        "uid_to_vol20_ratio_w120",
        "symmetric_information_shock_score_w20",
        "symmetric_information_shock_score_w60",
        "symmetric_information_shock_score_w120",
        "utc_day_uid_w20",
        "utc_day_uid_w60",
        "utc_day_uid_w120",
        "rolling_24h_uid_w20",
        "rolling_24h_uid_w60",
        "rolling_24h_uid_w120",
        "sessionless_information_uniformity_w20",
        "sessionless_information_uniformity_w60",
        "sessionless_information_uniformity_w120",
    ],
)

# ------------------------------------------------------------
# 53. 高频流动性溢价因子
# ------------------------------------------------------------

add_report_factors(
    "高频流动性溢价因子",
    [
        "orderbook_liquidity_premium_w20",
        "orderbook_liquidity_premium_w60",
        "orderbook_liquidity_premium_w120",
        "liquidity_premium_cap_need_w20",
        "liquidity_premium_cap_need_w60",
        "liquidity_premium_cap_need_w120",
        "liquidity_premium_cap_actual_w20",
        "liquidity_premium_cap_actual_w60",
        "liquidity_premium_cap_actual_w120",
        "simulated_depth_execution_gap_w20",
        "simulated_depth_execution_gap_w60",
        "simulated_depth_execution_gap_w120",
        "orderbook_demand_pricing_discount_w20",
        "orderbook_demand_pricing_discount_w60",
        "orderbook_demand_pricing_discount_w120",
        "fixed_notional_depth_slippage_w20",
        "fixed_notional_depth_slippage_w60",
        "fixed_notional_depth_slippage_w120",
        "virtual_level_interpolated_liquidity_w20",
        "virtual_level_interpolated_liquidity_w60",
        "virtual_level_interpolated_liquidity_w120",
        "liquidity_premium_10m_small_notional_w20",
        "liquidity_premium_10m_small_notional_w60",
        "liquidity_premium_10m_small_notional_w120",
        "liquidity_premium_30m_small_notional_w20",
        "liquidity_premium_30m_small_notional_w60",
        "liquidity_premium_30m_small_notional_w120",
        "liquidity_premium_10m_medium_notional_w20",
        "liquidity_premium_10m_medium_notional_w60",
        "liquidity_premium_10m_medium_notional_w120",
        "liquidity_premium_30m_medium_notional_w20",
        "liquidity_premium_30m_medium_notional_w60",
        "liquidity_premium_30m_medium_notional_w120",
        "liquidity_premium_10m_large_notional_w20",
        "liquidity_premium_10m_large_notional_w60",
        "liquidity_premium_10m_large_notional_w120",
        "liquidity_premium_30m_large_notional_w20",
        "liquidity_premium_30m_large_notional_w60",
        "liquidity_premium_30m_large_notional_w120",
        "time_weighted_liquidity_premium_w20",
        "time_weighted_liquidity_premium_w60",
        "time_weighted_liquidity_premium_w120",
        "volatility_weighted_liquidity_premium_w20",
        "volatility_weighted_liquidity_premium_w60",
        "volatility_weighted_liquidity_premium_w120",
        "liquidity_premium_decay_speed_w20",
        "liquidity_premium_decay_speed_w60",
        "liquidity_premium_decay_speed_w120",
        "liquidity_premium_tail_group_score_w20",
        "liquidity_premium_tail_group_score_w60",
        "liquidity_premium_tail_group_score_w120",
        "turnover_neutralized_liquidity_premium_w20",
        "turnover_neutralized_liquidity_premium_w60",
        "turnover_neutralized_liquidity_premium_w120",
        "size_turnover_neutralized_liquidity_premium_w20",
        "size_turnover_neutralized_liquidity_premium_w60",
        "size_turnover_neutralized_liquidity_premium_w120",
    ],
)

# ------------------------------------------------------------
# 54. 逐笔成交中的帕累托因子
# ------------------------------------------------------------

add_report_factors(
    "逐笔成交中的帕累托因子",
    [
        "pareto_beta_buy_order_volume_w20",
        "pareto_beta_buy_order_volume_w60",
        "pareto_beta_buy_order_volume_w120",
        "pareto_beta_sell_order_volume_w20",
        "pareto_beta_sell_order_volume_w60",
        "pareto_beta_sell_order_volume_w120",
        "pareto_beta_buy_sell_diff_w20",
        "pareto_beta_buy_sell_diff_w60",
        "pareto_beta_buy_sell_diff_w120",
        "pareto_beta_buy_sell_ratio_w20",
        "pareto_beta_buy_sell_ratio_w60",
        "pareto_beta_buy_sell_ratio_w120",
        "pareto_fit_r2_buy_volume_w20",
        "pareto_fit_r2_buy_volume_w60",
        "pareto_fit_r2_buy_volume_w120",
        "pareto_fit_r2_sell_volume_w20",
        "pareto_fit_r2_sell_volume_w60",
        "pareto_fit_r2_sell_volume_w120",
        "powerlaw_tail_slope_trade_size_w20",
        "powerlaw_tail_slope_trade_size_w60",
        "powerlaw_tail_slope_trade_size_w120",
        "powerlaw_tail_slope_order_size_w20",
        "powerlaw_tail_slope_order_size_w60",
        "powerlaw_tail_slope_order_size_w120",
        "buy_volume_quantile_ratio_7_1_w20",
        "buy_volume_quantile_ratio_7_1_w60",
        "buy_volume_quantile_ratio_7_1_w120",
        "sell_volume_quantile_ratio_7_1_w20",
        "sell_volume_quantile_ratio_7_1_w60",
        "sell_volume_quantile_ratio_7_1_w120",
        "buy_volume_quantile_ratio_6_2_w20",
        "buy_volume_quantile_ratio_6_2_w60",
        "buy_volume_quantile_ratio_6_2_w120",
        "sell_volume_quantile_ratio_6_2_w20",
        "sell_volume_quantile_ratio_6_2_w60",
        "sell_volume_quantile_ratio_6_2_w120",
        "buy_volume_quantile_ratio_5_3_w20",
        "buy_volume_quantile_ratio_5_3_w60",
        "buy_volume_quantile_ratio_5_3_w120",
        "sell_volume_quantile_ratio_5_3_w20",
        "sell_volume_quantile_ratio_5_3_w60",
        "sell_volume_quantile_ratio_5_3_w120",
        "orderbook_temperature_buy_side_w20",
        "orderbook_temperature_buy_side_w60",
        "orderbook_temperature_buy_side_w120",
        "orderbook_temperature_sell_side_w20",
        "orderbook_temperature_sell_side_w60",
        "orderbook_temperature_sell_side_w120",
        "large_order_sparsity_score_w20",
        "large_order_sparsity_score_w60",
        "large_order_sparsity_score_w120",
        "small_order_crowding_score_w20",
        "small_order_crowding_score_w60",
        "small_order_crowding_score_w120",
    ],
)

# ------------------------------------------------------------
# 55. DTrade日内算法策略介绍
# ------------------------------------------------------------

add_report_factors(
    "DTrade日内算法策略介绍",
    [
        "dtrade_intraday_enhancement_signal_w20",
        "dtrade_intraday_enhancement_signal_w60",
        "dtrade_intraday_enhancement_signal_w120",
        "inventory_neutral_reversion_signal_w20",
        "inventory_neutral_reversion_signal_w60",
        "inventory_neutral_reversion_signal_w120",
        "rnn_short_horizon_direction_score_w20",
        "rnn_short_horizon_direction_score_w60",
        "rnn_short_horizon_direction_score_w120",
        "ai_multimodal_market_data_signal_w20",
        "ai_multimodal_market_data_signal_w60",
        "ai_multimodal_market_data_signal_w120",
        "high_sell_low_buy_opportunity_score_w20",
        "high_sell_low_buy_opportunity_score_w60",
        "high_sell_low_buy_opportunity_score_w120",
        "intraday_cost_reduction_score_w20",
        "intraday_cost_reduction_score_w60",
        "intraday_cost_reduction_score_w120",
        "base_position_alpha_enhancement_w20",
        "base_position_alpha_enhancement_w60",
        "base_position_alpha_enhancement_w120",
        "daily_roundtrip_profitability_score_w20",
        "daily_roundtrip_profitability_score_w60",
        "daily_roundtrip_profitability_score_w120",
        "position_unchanged_pnl_signal_w20",
        "position_unchanged_pnl_signal_w60",
        "position_unchanged_pnl_signal_w120",
        "intraday_trade_completion_risk_w20",
        "intraday_trade_completion_risk_w60",
        "intraday_trade_completion_risk_w120",
        "buy_sell_netting_constraint_score_w20",
        "buy_sell_netting_constraint_score_w60",
        "buy_sell_netting_constraint_score_w120",
        "max_order_quantity_constraint_score_w20",
        "max_order_quantity_constraint_score_w60",
        "max_order_quantity_constraint_score_w120",
        "white_list_tradeability_score_w20",
        "white_list_tradeability_score_w60",
        "white_list_tradeability_score_w120",
        "intraday_realized_pnl_proxy_w20",
        "intraday_realized_pnl_proxy_w60",
        "intraday_realized_pnl_proxy_w120",
        "intraday_floating_pnl_risk_proxy_w20",
        "intraday_floating_pnl_risk_proxy_w60",
        "intraday_floating_pnl_risk_proxy_w120",
        "intraday_inventory_imbalance_risk_w20",
        "intraday_inventory_imbalance_risk_w60",
        "intraday_inventory_imbalance_risk_w120",
    ],
)

# ------------------------------------------------------------
# 56. 股指期货高频追杀趋势策略
# ------------------------------------------------------------

add_report_factors(
    "股指期货高频追杀趋势策略",
    [
        "spot_lead_futures_trend_signal_w20",
        "spot_lead_futures_trend_signal_w60",
        "spot_lead_futures_trend_signal_w120",
        "spot_trend_breakout_trigger_w20",
        "spot_trend_breakout_trigger_w60",
        "spot_trend_breakout_trigger_w120",
        "perp_follow_through_return_w20",
        "perp_follow_through_return_w60",
        "perp_follow_through_return_w120",
        "spot_perp_trend_alignment_w20",
        "spot_perp_trend_alignment_w60",
        "spot_perp_trend_alignment_w120",
        "spot_perp_noise_ratio_w20",
        "spot_perp_noise_ratio_w60",
        "spot_perp_noise_ratio_w120",
        "spot_turning_point_count_w20",
        "spot_turning_point_count_w60",
        "spot_turning_point_count_w120",
        "perp_turning_point_count_w20",
        "perp_turning_point_count_w60",
        "perp_turning_point_count_w120",
        "spot_vs_perp_turning_point_spread_w20",
        "spot_vs_perp_turning_point_spread_w60",
        "spot_vs_perp_turning_point_spread_w120",
        "trend_chasing_threshold_score_w20",
        "trend_chasing_threshold_score_w60",
        "trend_chasing_threshold_score_w120",
        "trend_chasing_cost_coverage_score_w20",
        "trend_chasing_cost_coverage_score_w60",
        "trend_chasing_cost_coverage_score_w120",
        "limit_order_trend_entry_fill_score_w20",
        "limit_order_trend_entry_fill_score_w60",
        "limit_order_trend_entry_fill_score_w120",
        "trend_signal_frequency_sweetspot_w20",
        "trend_signal_frequency_sweetspot_w60",
        "trend_signal_frequency_sweetspot_w120",
        "short_horizon_trend_continuation_w20",
        "short_horizon_trend_continuation_w60",
        "short_horizon_trend_continuation_w120",
    ],
)

# ------------------------------------------------------------
# 57. 基于价差交易的高频统计套利：异步价差操控模型
# ------------------------------------------------------------

add_report_factors(
    "基于价差交易的高频统计套利：异步价差操控模型",
    [
        "async_spread_dislocation_w20",
        "async_spread_dislocation_w60",
        "async_spread_dislocation_w120",
        "sync_spread_zscore_w20",
        "sync_spread_zscore_w60",
        "sync_spread_zscore_w120",
        "async_spread_zscore_w20",
        "async_spread_zscore_w60",
        "async_spread_zscore_w120",
        "spread_execution_gap_w20",
        "spread_execution_gap_w60",
        "spread_execution_gap_w120",
        "jump_limit_order_fill_opportunity_w20",
        "jump_limit_order_fill_opportunity_w60",
        "jump_limit_order_fill_opportunity_w120",
        "favorable_jump_fill_probability_w20",
        "favorable_jump_fill_probability_w60",
        "favorable_jump_fill_probability_w120",
        "adverse_jump_fill_risk_w20",
        "adverse_jump_fill_risk_w60",
        "adverse_jump_fill_risk_w120",
        "spread_leg_fill_mismatch_risk_w20",
        "spread_leg_fill_mismatch_risk_w60",
        "spread_leg_fill_mismatch_risk_w120",
        "spread_leg_quantity_mismatch_w20",
        "spread_leg_quantity_mismatch_w60",
        "spread_leg_quantity_mismatch_w120",
        "spread_control_profit_margin_w20",
        "spread_control_profit_margin_w60",
        "spread_control_profit_margin_w120",
        "safe_quote_distance_for_spread_w20",
        "safe_quote_distance_for_spread_w60",
        "safe_quote_distance_for_spread_w120",
        "passive_spread_entry_advantage_w20",
        "passive_spread_entry_advantage_w60",
        "passive_spread_entry_advantage_w120",
        "spread_stop_loss_pressure_w20",
        "spread_stop_loss_pressure_w60",
        "spread_stop_loss_pressure_w120",
        "cross_venue_async_spread_signal_w20",
        "cross_venue_async_spread_signal_w60",
        "cross_venue_async_spread_signal_w120",
        "spot_perp_async_basis_signal_w20",
        "spot_perp_async_basis_signal_w60",
        "spot_perp_async_basis_signal_w120",
        "calendar_spread_async_basis_signal_w20",
        "calendar_spread_async_basis_signal_w60",
        "calendar_spread_async_basis_signal_w120",
    ],
)

# ------------------------------------------------------------
# 58. 基于RSI的高频趋势策略研究
# ------------------------------------------------------------

add_report_factors(
    "基于RSI的高频趋势策略研究",
    [
        "rsi_trend_follow_signal_w20",
        "rsi_trend_follow_signal_w60",
        "rsi_trend_follow_signal_w120",
        "rsi_reversal_signal_w20",
        "rsi_reversal_signal_w60",
        "rsi_reversal_signal_w120",
        "rsi_buyer_seller_strength_w20",
        "rsi_buyer_seller_strength_w60",
        "rsi_buyer_seller_strength_w120",
        "rsi_overbought_pressure_w20",
        "rsi_overbought_pressure_w60",
        "rsi_overbought_pressure_w120",
        "rsi_oversold_pressure_w20",
        "rsi_oversold_pressure_w60",
        "rsi_oversold_pressure_w120",
        "rsi_long_entry_threshold_cross_w20",
        "rsi_long_entry_threshold_cross_w60",
        "rsi_long_entry_threshold_cross_w120",
        "rsi_short_entry_threshold_cross_w20",
        "rsi_short_entry_threshold_cross_w60",
        "rsi_short_entry_threshold_cross_w120",
        "rsi_long_exit_threshold_cross_w20",
        "rsi_long_exit_threshold_cross_w60",
        "rsi_long_exit_threshold_cross_w120",
        "rsi_short_exit_threshold_cross_w20",
        "rsi_short_exit_threshold_cross_w60",
        "rsi_short_exit_threshold_cross_w120",
        "rsi_threshold_band_width_w20",
        "rsi_threshold_band_width_w60",
        "rsi_threshold_band_width_w120",
        "rsi_trend_regime_score_w20",
        "rsi_trend_regime_score_w60",
        "rsi_trend_regime_score_w120",
        "rsi_rangebound_loss_risk_w20",
        "rsi_rangebound_loss_risk_w60",
        "rsi_rangebound_loss_risk_w120",
        "intraday_amplitude_filter_zf_w20",
        "intraday_amplitude_filter_zf_w60",
        "intraday_amplitude_filter_zf_w120",
        "rsi_take_profit_distance_zy_w20",
        "rsi_take_profit_distance_zy_w60",
        "rsi_take_profit_distance_zy_w120",
        "rsi_active_take_profit_signal_w20",
        "rsi_active_take_profit_signal_w60",
        "rsi_active_take_profit_signal_w120",
    ],
)

# ------------------------------------------------------------
# 59. CPV因子期货版
# ------------------------------------------------------------

add_report_factors(
    "CPV因子期货版",
    [
        "cpv_open_interest_price_corr_w20",
        "cpv_open_interest_price_corr_w60",
        "cpv_open_interest_price_corr_w120",
        "corrected_open_interest_price_corr_w20",
        "corrected_open_interest_price_corr_w60",
        "corrected_open_interest_price_corr_w120",
        "raw_open_interest_price_corr_w20",
        "raw_open_interest_price_corr_w60",
        "raw_open_interest_price_corr_w120",
        "open_interest_valley_shape_score_w20",
        "open_interest_valley_shape_score_w60",
        "open_interest_valley_shape_score_w120",
        "open_interest_peak_shape_score_w20",
        "open_interest_peak_shape_score_w60",
        "open_interest_peak_shape_score_w120",
        "open_interest_shape_correction_score_w20",
        "open_interest_shape_correction_score_w60",
        "open_interest_shape_correction_score_w120",
        "t0_trader_entry_open_interest_proxy_w20",
        "t0_trader_entry_open_interest_proxy_w60",
        "t0_trader_entry_open_interest_proxy_w120",
        "t0_trader_exit_open_interest_proxy_w20",
        "t0_trader_exit_open_interest_proxy_w60",
        "t0_trader_exit_open_interest_proxy_w120",
        "open_interest_long_short_intent_score_w20",
        "open_interest_long_short_intent_score_w60",
        "open_interest_long_short_intent_score_w120",
        "perp_open_interest_price_corr_w20",
        "perp_open_interest_price_corr_w60",
        "perp_open_interest_price_corr_w120",
        "funding_adjusted_open_interest_cpv_w20",
        "funding_adjusted_open_interest_cpv_w60",
        "funding_adjusted_open_interest_cpv_w120",
        "expiry_cycle_adjusted_cpv_w20",
        "expiry_cycle_adjusted_cpv_w60",
        "expiry_cycle_adjusted_cpv_w120",
        "holiday_gap_adjusted_cpv_w20",
        "holiday_gap_adjusted_cpv_w60",
        "holiday_gap_adjusted_cpv_w120",
        "cpv_cta_signal_strength_w20",
        "cpv_cta_signal_strength_w60",
        "cpv_cta_signal_strength_w120",
    ],
)

# ------------------------------------------------------------
# 60. 基于连续挂单的高频做市策略
# ------------------------------------------------------------

add_report_factors(
    "基于连续挂单的高频做市策略",
    [
        "continuous_quoting_profit_potential_w20",
        "continuous_quoting_profit_potential_w60",
        "continuous_quoting_profit_potential_w120",
        "market_making_absolute_price_variation_k_w20",
        "market_making_absolute_price_variation_k_w60",
        "market_making_absolute_price_variation_k_w120",
        "market_making_terminal_inventory_z_w20",
        "market_making_terminal_inventory_z_w60",
        "market_making_terminal_inventory_z_w120",
        "market_making_theoretical_profit_half_k_minus_z2_w20",
        "market_making_theoretical_profit_half_k_minus_z2_w60",
        "market_making_theoretical_profit_half_k_minus_z2_w120",
        "matched_roundtrip_count_w20",
        "matched_roundtrip_count_w60",
        "matched_roundtrip_count_w120",
        "unmatched_inventory_count_w20",
        "unmatched_inventory_count_w60",
        "unmatched_inventory_count_w120",
        "quote_queue_rank_bid_w20",
        "quote_queue_rank_bid_w60",
        "quote_queue_rank_bid_w120",
        "quote_queue_rank_ask_w20",
        "quote_queue_rank_ask_w60",
        "quote_queue_rank_ask_w120",
        "queue_adjusted_fill_probability_bid_w20",
        "queue_adjusted_fill_probability_bid_w60",
        "queue_adjusted_fill_probability_bid_w120",
        "queue_adjusted_fill_probability_ask_w20",
        "queue_adjusted_fill_probability_ask_w60",
        "queue_adjusted_fill_probability_ask_w120",
        "continuous_bid_quote_refresh_intensity_w20",
        "continuous_bid_quote_refresh_intensity_w60",
        "continuous_bid_quote_refresh_intensity_w120",
        "continuous_ask_quote_refresh_intensity_w20",
        "continuous_ask_quote_refresh_intensity_w60",
        "continuous_ask_quote_refresh_intensity_w120",
        "bid_queue_depletion_speed_w20",
        "bid_queue_depletion_speed_w60",
        "bid_queue_depletion_speed_w120",
        "ask_queue_depletion_speed_w20",
        "ask_queue_depletion_speed_w60",
        "ask_queue_depletion_speed_w120",
        "mean_reversion_market_making_score_w20",
        "mean_reversion_market_making_score_w60",
        "mean_reversion_market_making_score_w120",
        "inventory_unwind_pressure_w20",
        "inventory_unwind_pressure_w60",
        "inventory_unwind_pressure_w120",
    ],
)

# ------------------------------------------------------------
# 61. 机器学习与CTA：数据挖掘与人类对世界的认识
# ------------------------------------------------------------

add_report_factors(
    "机器学习与CTA：数据挖掘与人类对世界的认识",
    [
        "ml_cta_direction_probability_w20",
        "ml_cta_direction_probability_w60",
        "ml_cta_direction_probability_w120",
        "ml_cta_long_probability_w20",
        "ml_cta_long_probability_w60",
        "ml_cta_long_probability_w120",
        "ml_cta_short_probability_w20",
        "ml_cta_short_probability_w60",
        "ml_cta_short_probability_w120",
        "neural_network_cta_score_w20",
        "neural_network_cta_score_w60",
        "neural_network_cta_score_w120",
        "commodity_style_crypto_cta_signal_w20",
        "commodity_style_crypto_cta_signal_w60",
        "commodity_style_crypto_cta_signal_w120",
        "ml_signal_out_of_sample_tracking_score_w20",
        "ml_signal_out_of_sample_tracking_score_w60",
        "ml_signal_out_of_sample_tracking_score_w120",
        "data_mining_overfit_risk_score_w20",
        "data_mining_overfit_risk_score_w60",
        "data_mining_overfit_risk_score_w120",
        "ml_fundamental_interaction_signal_w20",
        "ml_fundamental_interaction_signal_w60",
        "ml_fundamental_interaction_signal_w120",
        "ml_strategy_drawdown_proxy_w20",
        "ml_strategy_drawdown_proxy_w60",
        "ml_strategy_drawdown_proxy_w120",
        "ml_strategy_winrate_proxy_w20",
        "ml_strategy_winrate_proxy_w60",
        "ml_strategy_winrate_proxy_w120",
    ],
)

# ------------------------------------------------------------
# 62. 基于变量选择和遗传网络规划的期货高频交易策略研究
# ------------------------------------------------------------

add_report_factors(
    "基于变量选择和遗传网络规划的期货高频交易策略研究",
    [
        "variable_selection_indicator_score_w20",
        "variable_selection_indicator_score_w60",
        "variable_selection_indicator_score_w120",
        "gnp_trading_rule_score_w20",
        "gnp_trading_rule_score_w60",
        "gnp_trading_rule_score_w120",
        "genetic_network_programming_signal_w20",
        "genetic_network_programming_signal_w60",
        "genetic_network_programming_signal_w120",
        "q_learning_reinforced_signal_w20",
        "q_learning_reinforced_signal_w60",
        "q_learning_reinforced_signal_w120",
        "technical_indicator_subset_stability_w20",
        "technical_indicator_subset_stability_w60",
        "technical_indicator_subset_stability_w120",
        "trend_indicator_selection_score_w20",
        "trend_indicator_selection_score_w60",
        "trend_indicator_selection_score_w120",
        "oscillator_indicator_selection_score_w20",
        "oscillator_indicator_selection_score_w60",
        "oscillator_indicator_selection_score_w120",
        "gnp_buy_node_activation_w20",
        "gnp_buy_node_activation_w60",
        "gnp_buy_node_activation_w120",
        "gnp_sell_node_activation_w20",
        "gnp_sell_node_activation_w60",
        "gnp_sell_node_activation_w120",
        "gnp_rule_transition_delay_w20",
        "gnp_rule_transition_delay_w60",
        "gnp_rule_transition_delay_w120",
        "evolutionary_rule_fitness_score_w20",
        "evolutionary_rule_fitness_score_w60",
        "evolutionary_rule_fitness_score_w120",
        "reinforced_trade_rule_confidence_w20",
        "reinforced_trade_rule_confidence_w60",
        "reinforced_trade_rule_confidence_w120",
    ],
)

# ------------------------------------------------------------
# 63. 解密高频交易策略黑匣子
# ------------------------------------------------------------

add_report_factors(
    "解密高频交易策略黑匣子",
    [
        "hft_trend_strategy_score_w20",
        "hft_trend_strategy_score_w60",
        "hft_trend_strategy_score_w120",
        "hft_spread_strategy_score_w20",
        "hft_spread_strategy_score_w60",
        "hft_spread_strategy_score_w120",
        "hft_market_making_strategy_score_w20",
        "hft_market_making_strategy_score_w60",
        "hft_market_making_strategy_score_w120",
        "transaction_cost_sensitivity_w20",
        "transaction_cost_sensitivity_w60",
        "transaction_cost_sensitivity_w120",
        "bid_ask_spread_sensitivity_w20",
        "bid_ask_spread_sensitivity_w60",
        "bid_ask_spread_sensitivity_w120",
        "order_submission_method_score_w20",
        "order_submission_method_score_w60",
        "order_submission_method_score_w120",
        "market_data_latency_pressure_w20",
        "market_data_latency_pressure_w60",
        "market_data_latency_pressure_w120",
        "order_routing_latency_pressure_w20",
        "order_routing_latency_pressure_w60",
        "order_routing_latency_pressure_w120",
        "hft_signal_calculation_speed_score_w20",
        "hft_signal_calculation_speed_score_w60",
        "hft_signal_calculation_speed_score_w120",
        "hft_execution_quality_score_w20",
        "hft_execution_quality_score_w60",
        "hft_execution_quality_score_w120",
        "hft_risk_control_pressure_w20",
        "hft_risk_control_pressure_w60",
        "hft_risk_control_pressure_w120",
        "hft_cost_estimation_error_w20",
        "hft_cost_estimation_error_w60",
        "hft_cost_estimation_error_w120",
        "polynomial_fit_price_alpha_w20",
        "polynomial_fit_price_alpha_w60",
        "polynomial_fit_price_alpha_w120",
        "polynomial_fit_residual_alpha_w20",
        "polynomial_fit_residual_alpha_w60",
        "polynomial_fit_residual_alpha_w120",
        "dual_moving_average_intraday_signal_w20",
        "dual_moving_average_intraday_signal_w60",
        "dual_moving_average_intraday_signal_w120",
        "dual_ma_fast_slow_spread_w20",
        "dual_ma_fast_slow_spread_w60",
        "dual_ma_fast_slow_spread_w120",
    ],
)

# ------------------------------------------------------------
# 64. 期指Level2行情的价格发现研究及高频实战体会
# ------------------------------------------------------------

add_report_factors(
    "期指Level2行情的价格发现研究及高频实战体会",
    [
        "level2_mid_information_share_w20",
        "level2_mid_information_share_w60",
        "level2_mid_information_share_w120",
        "level2_last_price_information_share_w20",
        "level2_last_price_information_share_w60",
        "level2_last_price_information_share_w120",
        "level2_weighted_price_information_share_w20",
        "level2_weighted_price_information_share_w60",
        "level2_weighted_price_information_share_w120",
        "wp2_5_price_discovery_score_w20",
        "wp2_5_price_discovery_score_w60",
        "wp2_5_price_discovery_score_w120",
        "level2_orderbook_imbalance_price_corr_w20",
        "level2_orderbook_imbalance_price_corr_w60",
        "level2_orderbook_imbalance_price_corr_w120",
        "level2_price_change_space_w20",
        "level2_price_change_space_w60",
        "level2_price_change_space_w120",
        "five_level_depth_symmetry_score_w20",
        "five_level_depth_symmetry_score_w60",
        "five_level_depth_symmetry_score_w120",
        "level1_depth_share_w20",
        "level1_depth_share_w60",
        "level1_depth_share_w120",
        "level2_depth_distribution_slope_w20",
        "level2_depth_distribution_slope_w60",
        "level2_depth_distribution_slope_w120",
        "adjacent_level_spread_structure_w20",
        "adjacent_level_spread_structure_w60",
        "adjacent_level_spread_structure_w120",
        "level2_depth_intraday_seasonality_w20",
        "level2_depth_intraday_seasonality_w60",
        "level2_depth_intraday_seasonality_w120",
        "multi_event_concurrency_risk_w20",
        "multi_event_concurrency_risk_w60",
        "multi_event_concurrency_risk_w120",
        "optimal_order_price_selection_score_w20",
        "optimal_order_price_selection_score_w60",
        "optimal_order_price_selection_score_w120",
        "active_exit_quality_score_w20",
        "active_exit_quality_score_w60",
        "active_exit_quality_score_w120",
        "passive_exit_quality_score_w20",
        "passive_exit_quality_score_w60",
        "passive_exit_quality_score_w120",
        "expected_profit_per_trade_w20",
        "expected_profit_per_trade_w60",
        "expected_profit_per_trade_w120",
    ],
)

# ------------------------------------------------------------
# 65. High Frequency Trading Measurement Detection and Response
# ------------------------------------------------------------

add_report_factors(
    "High Frequency Trading Measurement Detection and Response",
    [
        "quote_stuffing_burst_score_w20",
        "quote_stuffing_burst_score_w60",
        "quote_stuffing_burst_score_w120",
        "quote_stuffing_order_cancel_ratio_w20",
        "quote_stuffing_order_cancel_ratio_w60",
        "quote_stuffing_order_cancel_ratio_w120",
        "quote_stuffing_event_count_w20",
        "quote_stuffing_event_count_w60",
        "quote_stuffing_event_count_w120",
        "quote_stuffing_event_duration_w20",
        "quote_stuffing_event_duration_w60",
        "quote_stuffing_event_duration_w120",
        "quote_stuffing_repeat_probability_w20",
        "quote_stuffing_repeat_probability_w60",
        "quote_stuffing_repeat_probability_w120",
        "quote_stuffing_same_venue_repeat_score_w20",
        "quote_stuffing_same_venue_repeat_score_w60",
        "quote_stuffing_same_venue_repeat_score_w120",
        "quote_stuffing_post_event_spread_widening_w20",
        "quote_stuffing_post_event_spread_widening_w60",
        "quote_stuffing_post_event_spread_widening_w120",
        "quote_stuffing_post_event_volatility_w20",
        "quote_stuffing_post_event_volatility_w60",
        "quote_stuffing_post_event_volatility_w120",
        "quote_stuffing_midprice_pull_direction_w20",
        "quote_stuffing_midprice_pull_direction_w60",
        "quote_stuffing_midprice_pull_direction_w120",
        "orderbook_layering_score_w20",
        "orderbook_layering_score_w60",
        "orderbook_layering_score_w120",
        "orderbook_layering_cancel_pressure_w20",
        "orderbook_layering_cancel_pressure_w60",
        "orderbook_layering_cancel_pressure_w120",
        "orderbook_fade_score_w20",
        "orderbook_fade_score_w60",
        "orderbook_fade_score_w120",
        "same_venue_orderbook_fade_probability_w20",
        "same_venue_orderbook_fade_probability_w60",
        "same_venue_orderbook_fade_probability_w120",
        "cross_venue_orderbook_fade_probability_w20",
        "cross_venue_orderbook_fade_probability_w60",
        "cross_venue_orderbook_fade_probability_w120",
        "momentum_ignition_score_w20",
        "momentum_ignition_score_w60",
        "momentum_ignition_score_w120",
        "momentum_ignition_price_impact_w20",
        "momentum_ignition_price_impact_w60",
        "momentum_ignition_price_impact_w120",
        "momentum_ignition_reversal_risk_w20",
        "momentum_ignition_reversal_risk_w60",
        "momentum_ignition_reversal_risk_w120",
        "hft_adverse_activity_score_w20",
        "hft_adverse_activity_score_w60",
        "hft_adverse_activity_score_w120",
        "quote_filtering_required_score_w20",
        "quote_filtering_required_score_w60",
        "quote_filtering_required_score_w120",
        "microstructure_toxicity_event_score_w20",
        "microstructure_toxicity_event_score_w60",
        "microstructure_toxicity_event_score_w120",
    ],
)

# ------------------------------------------------------------
# 66. Adaptive Strategies for High Frequency Trading
# ------------------------------------------------------------

add_report_factors(
    "Adaptive Strategies for High Frequency Trading",
    [
        "bid_queue_cumulative_barrier_w20",
        "bid_queue_cumulative_barrier_w60",
        "bid_queue_cumulative_barrier_w120",
        "ask_queue_cumulative_barrier_w20",
        "ask_queue_cumulative_barrier_w60",
        "ask_queue_cumulative_barrier_w120",
        "bid_ask_barrier_imbalance_w20",
        "bid_ask_barrier_imbalance_w60",
        "bid_ask_barrier_imbalance_w120",
        "orderbook_barrier_price_impact_score_w20",
        "orderbook_barrier_price_impact_score_w60",
        "orderbook_barrier_price_impact_score_w120",
        "bid_order_inflow_rate_w20",
        "bid_order_inflow_rate_w60",
        "bid_order_inflow_rate_w120",
        "ask_order_inflow_rate_w20",
        "ask_order_inflow_rate_w60",
        "ask_order_inflow_rate_w120",
        "bid_order_outflow_rate_w20",
        "bid_order_outflow_rate_w60",
        "bid_order_outflow_rate_w120",
        "ask_order_outflow_rate_w20",
        "ask_order_outflow_rate_w60",
        "ask_order_outflow_rate_w120",
        "net_bid_ask_order_flow_rate_w20",
        "net_bid_ask_order_flow_rate_w60",
        "net_bid_ask_order_flow_rate_w120",
        "queue_centered_frame_shift_adjustment_w20",
        "queue_centered_frame_shift_adjustment_w60",
        "queue_centered_frame_shift_adjustment_w120",
        "quote_independent_queue_imbalance_w20",
        "quote_independent_queue_imbalance_w60",
        "quote_independent_queue_imbalance_w120",
        "adaptive_filter_short_term_prediction_w20",
        "adaptive_filter_short_term_prediction_w60",
        "adaptive_filter_short_term_prediction_w120",
        "svm_market_shock_probability_w20",
        "svm_market_shock_probability_w60",
        "svm_market_shock_probability_w120",
        "market_making_disable_shock_gate_w20",
        "market_making_disable_shock_gate_w60",
        "market_making_disable_shock_gate_w120",
        "shock_adjusted_market_making_signal_w20",
        "shock_adjusted_market_making_signal_w60",
        "shock_adjusted_market_making_signal_w120",
    ],
)

# ------------------------------------------------------------
# 67. AI for Trading Nanodegree Program Syllabus
# ------------------------------------------------------------

add_report_factors(
    "AI for Trading Nanodegree Program Syllabus",
    [
        "momentum_trading_signal_w20",
        "momentum_trading_signal_w60",
        "momentum_trading_signal_w120",
        "breakout_strategy_signal_w20",
        "breakout_strategy_signal_w60",
        "breakout_strategy_signal_w120",
        "breakout_outlier_filtered_signal_w20",
        "breakout_outlier_filtered_signal_w60",
        "breakout_outlier_filtered_signal_w120",
        "mean_reversion_pairs_signal_w20",
        "mean_reversion_pairs_signal_w60",
        "mean_reversion_pairs_signal_w120",
        "multi_factor_alpha_composite_w20",
        "multi_factor_alpha_composite_w60",
        "multi_factor_alpha_composite_w120",
        "risk_factor_exposure_score_w20",
        "risk_factor_exposure_score_w60",
        "risk_factor_exposure_score_w120",
        "portfolio_turnover_pressure_w20",
        "portfolio_turnover_pressure_w60",
        "portfolio_turnover_pressure_w120",
        "signal_combination_enhanced_alpha_w20",
        "signal_combination_enhanced_alpha_w60",
        "signal_combination_enhanced_alpha_w120",
        "news_sentiment_alpha_signal_w20",
        "news_sentiment_alpha_signal_w60",
        "news_sentiment_alpha_signal_w120",
        "lstm_news_sentiment_signal_w20",
        "lstm_news_sentiment_signal_w60",
        "lstm_news_sentiment_signal_w120",
    ],
)

# ------------------------------------------------------------
# 68. Algorithmic and High-frequency Trading Overview
# ------------------------------------------------------------

add_report_factors(
    "Algorithmic and High-frequency Trading Overview",
    [
        "twap_execution_deviation_w20",
        "twap_execution_deviation_w60",
        "twap_execution_deviation_w120",
        "vwap_execution_deviation_w20",
        "vwap_execution_deviation_w60",
        "vwap_execution_deviation_w120",
        "arrival_price_slippage_w20",
        "arrival_price_slippage_w60",
        "arrival_price_slippage_w120",
        "implementation_shortfall_score_w20",
        "implementation_shortfall_score_w60",
        "implementation_shortfall_score_w120",
        "daughter_order_split_intensity_w20",
        "daughter_order_split_intensity_w60",
        "daughter_order_split_intensity_w120",
        "execution_alpha_decay_score_w20",
        "execution_alpha_decay_score_w60",
        "execution_alpha_decay_score_w120",
        "microtrader_order_placement_score_w20",
        "microtrader_order_placement_score_w60",
        "microtrader_order_placement_score_w120",
        "macrotrader_execution_schedule_score_w20",
        "macrotrader_execution_schedule_score_w60",
        "macrotrader_execution_schedule_score_w120",
        "smart_routing_venue_selection_score_w20",
        "smart_routing_venue_selection_score_w60",
        "smart_routing_venue_selection_score_w120",
        "dark_pool_liquidity_opportunity_w20",
        "dark_pool_liquidity_opportunity_w60",
        "dark_pool_liquidity_opportunity_w120",
        "venue_fragmentation_liquidity_score_w20",
        "venue_fragmentation_liquidity_score_w60",
        "venue_fragmentation_liquidity_score_w120",
    ],
)

# ------------------------------------------------------------
# 69. High Frequency Trading Price Dynamics Models and Market Making Strategies
# ------------------------------------------------------------

add_report_factors(
    "High Frequency Trading Price Dynamics Models and Market Making Strategies",
    [
        "discrete_markov_queue_state_w20",
        "discrete_markov_queue_state_w60",
        "discrete_markov_queue_state_w120",
        "markovian_queue_price_transition_prob_w20",
        "markovian_queue_price_transition_prob_w60",
        "markovian_queue_price_transition_prob_w120",
        "event_arrival_rate_bid_w20",
        "event_arrival_rate_bid_w60",
        "event_arrival_rate_bid_w120",
        "event_arrival_rate_ask_w20",
        "event_arrival_rate_ask_w60",
        "event_arrival_rate_ask_w120",
        "order_size_distribution_score_w20",
        "order_size_distribution_score_w60",
        "order_size_distribution_score_w120",
        "event_correlation_score_w20",
        "event_correlation_score_w60",
        "event_correlation_score_w120",
        "queue_depletion_transition_prob_w20",
        "queue_depletion_transition_prob_w60",
        "queue_depletion_transition_prob_w120",
        "queue_replenishment_transition_prob_w20",
        "queue_replenishment_transition_prob_w60",
        "queue_replenishment_transition_prob_w120",
        "market_making_balancing_strategy_score_w20",
        "market_making_balancing_strategy_score_w60",
        "market_making_balancing_strategy_score_w120",
        "smoking_strategy_detection_score_w20",
        "smoking_strategy_detection_score_w60",
        "smoking_strategy_detection_score_w120",
        "queue_model_simulated_price_up_prob_w20",
        "queue_model_simulated_price_up_prob_w60",
        "queue_model_simulated_price_up_prob_w120",
        "queue_model_simulated_price_down_prob_w20",
        "queue_model_simulated_price_down_prob_w60",
        "queue_model_simulated_price_down_prob_w120",
    ],
)

# ------------------------------------------------------------
# 70. High-Frequency Factor Models and Regressions
# ------------------------------------------------------------

add_report_factors(
    "High-Frequency Factor Models and Regressions",
    [
        "hf_market_beta_time_varying_w20",
        "hf_market_beta_time_varying_w60",
        "hf_market_beta_time_varying_w120",
        "hf_factor_beta_time_varying_w20",
        "hf_factor_beta_time_varying_w60",
        "hf_factor_beta_time_varying_w120",
        "hf_continuous_factor_beta_w20",
        "hf_continuous_factor_beta_w60",
        "hf_continuous_factor_beta_w120",
        "hf_jump_factor_beta_w20",
        "hf_jump_factor_beta_w60",
        "hf_jump_factor_beta_w120",
        "hf_idiosyncratic_volatility_w20",
        "hf_idiosyncratic_volatility_w60",
        "hf_idiosyncratic_volatility_w120",
        "hf_idiosyncratic_jump_risk_w20",
        "hf_idiosyncratic_jump_risk_w60",
        "hf_idiosyncratic_jump_risk_w120",
        "hf_factor_residual_return_w20",
        "hf_factor_residual_return_w60",
        "hf_factor_residual_return_w120",
        "hf_factor_model_r2_w20",
        "hf_factor_model_r2_w60",
        "hf_factor_model_r2_w120",
        "hf_factor_model_residual_skew_w20",
        "hf_factor_model_residual_skew_w60",
        "hf_factor_model_residual_skew_w120",
        "hf_factor_model_residual_kurtosis_w20",
        "hf_factor_model_residual_kurtosis_w60",
        "hf_factor_model_residual_kurtosis_w120",
        "hf_momentum_factor_exposure_w20",
        "hf_momentum_factor_exposure_w60",
        "hf_momentum_factor_exposure_w120",
        "hf_size_factor_exposure_proxy_w20",
        "hf_size_factor_exposure_proxy_w60",
        "hf_size_factor_exposure_proxy_w120",
        "hf_value_factor_exposure_proxy_w20",
        "hf_value_factor_exposure_proxy_w60",
        "hf_value_factor_exposure_proxy_w120",
        "sampling_frequency_liquidity_score_w20",
        "sampling_frequency_liquidity_score_w60",
        "sampling_frequency_liquidity_score_w120",
        "microstructure_noise_hausman_score_w20",
        "microstructure_noise_hausman_score_w60",
        "microstructure_noise_hausman_score_w120",
    ],
)

# ------------------------------------------------------------
# 71. High-frequency Market-making with Inventory Constraints and Directional Bets
# ------------------------------------------------------------

add_report_factors(
    "High-frequency Market-making with Inventory Constraints and Directional Bets",
    [
        "directional_market_making_signal_w20",
        "directional_market_making_signal_w60",
        "directional_market_making_signal_w120",
        "non_symmetric_bid_ask_quote_skew_w20",
        "non_symmetric_bid_ask_quote_skew_w60",
        "non_symmetric_bid_ask_quote_skew_w120",
        "inventory_risk_aversion_parameter_w20",
        "inventory_risk_aversion_parameter_w60",
        "inventory_risk_aversion_parameter_w120",
        "inventory_penalty_adjusted_quote_w20",
        "inventory_penalty_adjusted_quote_w60",
        "inventory_penalty_adjusted_quote_w120",
        "directional_bet_quote_tilt_w20",
        "directional_bet_quote_tilt_w60",
        "directional_bet_quote_tilt_w120",
        "trend_biased_market_making_quote_w20",
        "trend_biased_market_making_quote_w60",
        "trend_biased_market_making_quote_w120",
        "mm_pnl_mean_control_w20",
        "mm_pnl_mean_control_w60",
        "mm_pnl_mean_control_w120",
        "mm_pnl_variance_control_w20",
        "mm_pnl_variance_control_w60",
        "mm_pnl_variance_control_w120",
        "mm_pnl_skewness_control_w20",
        "mm_pnl_skewness_control_w60",
        "mm_pnl_skewness_control_w120",
        "mm_pnl_kurtosis_control_w20",
        "mm_pnl_kurtosis_control_w60",
        "mm_pnl_kurtosis_control_w120",
        "mm_pnl_var_control_w20",
        "mm_pnl_var_control_w60",
        "mm_pnl_var_control_w120",
        "flat_inventory_end_of_day_pressure_w20",
        "flat_inventory_end_of_day_pressure_w60",
        "flat_inventory_end_of_day_pressure_w120",
        "inventory_constrained_sharpe_improvement_w20",
        "inventory_constrained_sharpe_improvement_w60",
        "inventory_constrained_sharpe_improvement_w120",
    ],
)

# ------------------------------------------------------------
# 72. High-frequency Trading in a Limit Order Book
# ------------------------------------------------------------

add_report_factors(
    "High-frequency Trading in a Limit Order Book",
    [
        "as_reservation_price_w20",
        "as_reservation_price_w60",
        "as_reservation_price_w120",
        "as_reservation_price_inventory_shift_w20",
        "as_reservation_price_inventory_shift_w60",
        "as_reservation_price_inventory_shift_w120",
        "as_optimal_bid_quote_w20",
        "as_optimal_bid_quote_w60",
        "as_optimal_bid_quote_w120",
        "as_optimal_ask_quote_w20",
        "as_optimal_ask_quote_w60",
        "as_optimal_ask_quote_w120",
        "as_optimal_spread_w20",
        "as_optimal_spread_w60",
        "as_optimal_spread_w120",
        "as_quote_distance_to_mid_bid_w20",
        "as_quote_distance_to_mid_bid_w60",
        "as_quote_distance_to_mid_bid_w120",
        "as_quote_distance_to_mid_ask_w20",
        "as_quote_distance_to_mid_ask_w60",
        "as_quote_distance_to_mid_ask_w120",
        "as_order_arrival_intensity_bid_w20",
        "as_order_arrival_intensity_bid_w60",
        "as_order_arrival_intensity_bid_w120",
        "as_order_arrival_intensity_ask_w20",
        "as_order_arrival_intensity_ask_w60",
        "as_order_arrival_intensity_ask_w120",
        "as_inventory_risk_adjustment_w20",
        "as_inventory_risk_adjustment_w60",
        "as_inventory_risk_adjustment_w120",
        "as_terminal_utility_score_w20",
        "as_terminal_utility_score_w60",
        "as_terminal_utility_score_w120",
        "as_limit_order_execution_probability_w20",
        "as_limit_order_execution_probability_w60",
        "as_limit_order_execution_probability_w120",
    ],
)

# ------------------------------------------------------------
# 73. Inside the Black Box
# ------------------------------------------------------------

add_report_factors(
    "Inside the Black Box",
    [
        "alpha_model_diversification_score_w20",
        "alpha_model_diversification_score_w60",
        "alpha_model_diversification_score_w120",
        "theory_driven_alpha_score_w20",
        "theory_driven_alpha_score_w60",
        "theory_driven_alpha_score_w120",
        "data_driven_alpha_score_w20",
        "data_driven_alpha_score_w60",
        "data_driven_alpha_score_w120",
        "alpha_blending_consistency_score_w20",
        "alpha_blending_consistency_score_w60",
        "alpha_blending_consistency_score_w120",
        "risk_model_exposure_control_score_w20",
        "risk_model_exposure_control_score_w60",
        "risk_model_exposure_control_score_w120",
        "transaction_cost_model_error_w20",
        "transaction_cost_model_error_w60",
        "transaction_cost_model_error_w120",
        "portfolio_construction_constraint_pressure_w20",
        "portfolio_construction_constraint_pressure_w60",
        "portfolio_construction_constraint_pressure_w120",
        "execution_algorithm_quality_score_w20",
        "execution_algorithm_quality_score_w60",
        "execution_algorithm_quality_score_w120",
        "contractual_market_making_score_w20",
        "contractual_market_making_score_w60",
        "contractual_market_making_score_w120",
        "noncontractual_market_making_score_w20",
        "noncontractual_market_making_score_w60",
        "noncontractual_market_making_score_w120",
        "hft_arbitrage_opportunity_score_w20",
        "hft_arbitrage_opportunity_score_w60",
        "hft_arbitrage_opportunity_score_w120",
        "fast_alpha_signal_score_w20",
        "fast_alpha_signal_score_w60",
        "fast_alpha_signal_score_w120",
        "hft_portfolio_risk_management_score_w20",
        "hft_portfolio_risk_management_score_w60",
        "hft_portfolio_risk_management_score_w120",
    ],
)

# ------------------------------------------------------------
# 74. Machine Learning for Market Microstructure and High Frequency Trading
# ------------------------------------------------------------

add_report_factors(
    "Machine Learning for Market Microstructure and High Frequency Trading",
    [
        "rl_optimized_execution_policy_w20",
        "rl_optimized_execution_policy_w60",
        "rl_optimized_execution_policy_w120",
        "rl_aggressive_order_action_score_w20",
        "rl_aggressive_order_action_score_w60",
        "rl_aggressive_order_action_score_w120",
        "rl_passive_order_action_score_w20",
        "rl_passive_order_action_score_w60",
        "rl_passive_order_action_score_w120",
        "orderbook_state_value_score_w20",
        "orderbook_state_value_score_w60",
        "orderbook_state_value_score_w120",
        "spread_crossing_cost_state_w20",
        "spread_crossing_cost_state_w60",
        "spread_crossing_cost_state_w120",
        "book_volume_imbalance_state_w20",
        "book_volume_imbalance_state_w60",
        "book_volume_imbalance_state_w120",
        "recent_activity_state_score_w20",
        "recent_activity_state_score_w60",
        "recent_activity_state_score_w120",
        "midpoint_direction_prediction_score_w20",
        "midpoint_direction_prediction_score_w60",
        "midpoint_direction_prediction_score_w120",
        "microstructure_feature_selection_score_w20",
        "microstructure_feature_selection_score_w60",
        "microstructure_feature_selection_score_w120",
        "dark_pool_fill_rate_prediction_w20",
        "dark_pool_fill_rate_prediction_w60",
        "dark_pool_fill_rate_prediction_w120",
        "censored_liquidity_estimation_score_w20",
        "censored_liquidity_estimation_score_w60",
        "censored_liquidity_estimation_score_w120",
        "kaplan_meier_fill_estimator_score_w20",
        "kaplan_meier_fill_estimator_score_w60",
        "kaplan_meier_fill_estimator_score_w120",
        "smart_order_routing_fill_optimization_w20",
        "smart_order_routing_fill_optimization_w60",
        "smart_order_routing_fill_optimization_w120",
    ],
)

# ------------------------------------------------------------
# 75. Machine Trading
# ------------------------------------------------------------

add_report_factors(
    "Machine Trading",
    [
        "intraday_microstructure_alpha_w20",
        "intraday_microstructure_alpha_w60",
        "intraday_microstructure_alpha_w120",
        "order_type_selection_score_w20",
        "order_type_selection_score_w60",
        "order_type_selection_score_w120",
        "routing_optimization_score_w20",
        "routing_optimization_score_w60",
        "routing_optimization_score_w120",
        "adverse_selection_risk_score_w20",
        "adverse_selection_risk_score_w60",
        "adverse_selection_risk_score_w120",
        "tick_backtest_bias_risk_w20",
        "tick_backtest_bias_risk_w60",
        "tick_backtest_bias_risk_w120",
        "arima_intraday_forecast_signal_w20",
        "arima_intraday_forecast_signal_w60",
        "arima_intraday_forecast_signal_w120",
        "var_intraday_forecast_signal_w20",
        "var_intraday_forecast_signal_w60",
        "var_intraday_forecast_signal_w120",
        "state_space_hidden_variable_signal_w20",
        "state_space_hidden_variable_signal_w60",
        "state_space_hidden_variable_signal_w120",
        "ml_overfitting_reduction_score_w20",
        "ml_overfitting_reduction_score_w60",
        "ml_overfitting_reduction_score_w120",
        "crypto_bitcoin_microstructure_signal_w20",
        "crypto_bitcoin_microstructure_signal_w60",
        "crypto_bitcoin_microstructure_signal_w120",
    ],
)

# ------------------------------------------------------------
# 76. Market Microstructure Signals Using Deep Learning
# ------------------------------------------------------------

add_report_factors(
    "Market Microstructure Signals Using Deep Learning",
    [
        "dl_price_up_probability_w20",
        "dl_price_up_probability_w60",
        "dl_price_up_probability_w120",
        "dl_price_down_probability_w20",
        "dl_price_down_probability_w60",
        "dl_price_down_probability_w120",
        "dl_price_no_change_probability_w20",
        "dl_price_no_change_probability_w60",
        "dl_price_no_change_probability_w120",
        "next_five_tick_up_class_score_w20",
        "next_five_tick_up_class_score_w60",
        "next_five_tick_up_class_score_w120",
        "next_five_tick_down_class_score_w20",
        "next_five_tick_down_class_score_w60",
        "next_five_tick_down_class_score_w120",
        "next_five_tick_nochange_class_score_w20",
        "next_five_tick_nochange_class_score_w60",
        "next_five_tick_nochange_class_score_w120",
        "minute_trade_count_intensity_w20",
        "minute_trade_count_intensity_w60",
        "minute_trade_count_intensity_w120",
        "chaikin_money_flow_intraday_w20",
        "chaikin_money_flow_intraday_w60",
        "chaikin_money_flow_intraday_w120",
        "bollinger_band_position_w20",
        "bollinger_band_position_w60",
        "bollinger_band_position_w120",
        "moving_average_gap_signal_w20",
        "moving_average_gap_signal_w60",
        "moving_average_gap_signal_w120",
    ],
)

# ------------------------------------------------------------
# 77. Optimal Strategies of High Frequency Traders
# ------------------------------------------------------------

add_report_factors(
    "Optimal Strategies of High Frequency Traders",
    [
        "pinging_activity_score_w20",
        "pinging_activity_score_w60",
        "pinging_activity_score_w120",
        "fleeting_order_inside_spread_ratio_w20",
        "fleeting_order_inside_spread_ratio_w60",
        "fleeting_order_inside_spread_ratio_w120",
        "pinging_cancel_speed_w20",
        "pinging_cancel_speed_w60",
        "pinging_cancel_speed_w120",
        "aggressive_fleeting_order_ratio_w20",
        "aggressive_fleeting_order_ratio_w60",
        "aggressive_fleeting_order_ratio_w120",
        "hidden_liquidity_probe_score_w20",
        "hidden_liquidity_probe_score_w60",
        "hidden_liquidity_probe_score_w120",
        "inside_spread_hidden_order_execution_score_w20",
        "inside_spread_hidden_order_execution_score_w60",
        "inside_spread_hidden_order_execution_score_w120",
        "pinging_inventory_control_motive_w20",
        "pinging_inventory_control_motive_w60",
        "pinging_inventory_control_motive_w120",
        "pinging_momentum_chasing_motive_w20",
        "pinging_momentum_chasing_motive_w60",
        "pinging_momentum_chasing_motive_w120",
        "depth_imbalance_momentum_signal_w20",
        "depth_imbalance_momentum_signal_w60",
        "depth_imbalance_momentum_signal_w120",
        "depth_imbalance_hidden_liquidity_signal_w20",
        "depth_imbalance_hidden_liquidity_signal_w60",
        "depth_imbalance_hidden_liquidity_signal_w120",
        "pinging_directional_bet_score_w20",
        "pinging_directional_bet_score_w60",
        "pinging_directional_bet_score_w120",
        "fleeting_order_toxicity_score_w20",
        "fleeting_order_toxicity_score_w60",
        "fleeting_order_toxicity_score_w120",
    ],
)

# ------------------------------------------------------------
# 78. Statistical Modeling of High-Frequency Financial Data
# ------------------------------------------------------------

add_report_factors(
    "Statistical Modeling of High-Frequency Financial Data",
    [
        "trade_duration_intensity_w20",
        "trade_duration_intensity_w60",
        "trade_duration_intensity_w120",
        "interevent_duration_autocorr_w20",
        "interevent_duration_autocorr_w60",
        "interevent_duration_autocorr_w120",
        "duration_exponential_deviation_score_w20",
        "duration_exponential_deviation_score_w60",
        "duration_exponential_deviation_score_w120",
        "tick_discreteness_score_w20",
        "tick_discreteness_score_w60",
        "tick_discreteness_score_w120",
        "first_lag_return_autocorr_microstructure_w20",
        "first_lag_return_autocorr_microstructure_w60",
        "first_lag_return_autocorr_microstructure_w120",
        "intraday_activity_seasonality_score_w20",
        "intraday_activity_seasonality_score_w60",
        "intraday_activity_seasonality_score_w120",
        "u_shape_volume_seasonality_w20",
        "u_shape_volume_seasonality_w60",
        "u_shape_volume_seasonality_w120",
        "u_shape_volatility_seasonality_w20",
        "u_shape_volatility_seasonality_w60",
        "u_shape_volatility_seasonality_w120",
        "deseasonalized_order_flow_w20",
        "deseasonalized_order_flow_w60",
        "deseasonalized_order_flow_w120",
        "marked_point_process_orderflow_score_w20",
        "marked_point_process_orderflow_score_w60",
        "marked_point_process_orderflow_score_w120",
        "acd_duration_model_signal_w20",
        "acd_duration_model_signal_w60",
        "acd_duration_model_signal_w120",
        "duration_conditioned_return_signal_w20",
        "duration_conditioned_return_signal_w60",
        "duration_conditioned_return_signal_w120",
        "queueing_system_lob_state_w20",
        "queueing_system_lob_state_w60",
        "queueing_system_lob_state_w120",
        "order_flow_liquidity_price_interplay_w20",
        "order_flow_liquidity_price_interplay_w60",
        "order_flow_liquidity_price_interplay_w120",
    ],
)


# ============================================================
# 3. Build final maps
# ============================================================

crypto_tick_factor_rename_map, crypto_tick_factor_meta_map, crypto_tick_train_features = (
    build_crypto_tick_factor_maps(
        crypto_report_factor_base,
        tick_feature_stats,
    )
)

priority_tick_train_features = [
    f"{factor}_{stat}"
    for factor in priority_base_factors
    for stat in tick_feature_stats
]


# ============================================================
# 4. Quick check
# ============================================================

print("Total report blocks:", report_block_count)
print("Total unique report names:", len(crypto_report_factor_base))
print("Total base factors:", sum(len(v) for v in crypto_report_factor_base.values()))
print("Unique base factors:", len({f for factors in crypto_report_factor_base.values() for f in factors}))
print("Total train features:", len(crypto_tick_train_features))
print("Unique train features:", len(set(crypto_tick_train_features)))
print("Total priority base factors:", len(priority_base_factors))
print("Total priority train features:", len(priority_tick_train_features))
