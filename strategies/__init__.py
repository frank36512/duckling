"""
策略模块初始化
导入所有可用的交易策略
"""

# 导入基础策略
from strategies.macd_strategy import MACDStrategy
from strategies.bollinger_strategy import BollingerBandsStrategy
from strategies.kdj_strategy import KDJStrategy
from strategies.ma_volume_strategy import MAVolumeStrategy
from strategies.atr_breakout_strategy import ATRBreakoutStrategy
from strategies.cci_strategy import CCIStrategy
from strategies.turtle_trading_strategy import TurtleTradingStrategy
from strategies.grid_trading_strategy import GridTradingStrategy
from strategies.williams_r_strategy import WilliamsRStrategy
from strategies.dmi_strategy import DMIStrategy
from strategies.vwap_strategy import VWAPStrategy
from strategies.obv_strategy import OBVStrategy
from strategies.triple_screen_strategy import TripleScreenStrategy
from strategies.multifactor_strategy import MultiFactorStrategy

# 导入经典量化策略
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.momentum_breakout_strategy import MomentumBreakoutStrategy
from strategies.alpha_arbitrage_strategy import AlphaArbitrageStrategy
from strategies.dual_ma_enhanced_strategy import DualMAEnhancedStrategy
from strategies.trend_strength_strategy import TrendStrengthStrategy
from strategies.gap_trading_strategy import GapTradingStrategy
from strategies.support_resistance_strategy import SupportResistanceStrategy

# 导入机器学习策略
from strategies.random_forest_strategy import RandomForestStrategy
from strategies.lstm_strategy import LSTMStrategy
from strategies.xgboost_strategy import XGBoostStrategy

__all__ = [
    # 基础策略
    'MACDStrategy',
    'BollingerBandsStrategy',
    'KDJStrategy',
    'MAVolumeStrategy',
    'ATRBreakoutStrategy',
    'CCIStrategy',
    'TurtleTradingStrategy',
    'GridTradingStrategy',
    'WilliamsRStrategy',
    'DMIStrategy',
    'VWAPStrategy',
    'OBVStrategy',
    'TripleScreenStrategy',
    'MultiFactorStrategy',
    
    # 经典量化策略
    'MeanReversionStrategy',
    'MomentumBreakoutStrategy',
    'AlphaArbitrageStrategy',
    'DualMAEnhancedStrategy',
    'TrendStrengthStrategy',
    'GapTradingStrategy',
    'SupportResistanceStrategy',
    
    # 机器学习策略
    'RandomForestStrategy',
    'LSTMStrategy',
    'XGBoostStrategy',
]
