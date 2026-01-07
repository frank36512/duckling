"""
策略基类模块
定义策略接口规范
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """策略基类"""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        初始化策略
        :param name: 策略名称
        :param params: 策略参数
        """
        self.name = name
        self.params = params or {}
        self.position = 0  # 当前持仓（0表示空仓，1表示持有）
        self.trades = []  # 交易记录
        
        logger.info(f"策略 {self.name} 初始化，参数: {self.params}")
    
    @abstractmethod
    def init(self):
        """
        策略初始化方法
        在回测开始前调用，用于初始化指标、变量等
        """
        pass
    
    @abstractmethod
    def next(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        策略信号生成方法
        在每个交易日调用，生成买入/卖出信号
        
        :param data: 当前可用的历史数据
        :return: 信号字典 {'signal': 'buy'/'sell'/'hold', 'price': 价格, 'reason': 原因}
        """
        pass
    
    def validate(self) -> bool:
        """
        策略参数校验
        :return: 校验是否通过
        """
        try:
            # 子类可以重写此方法进行自定义校验
            return True
        except Exception as e:
            logger.error(f"策略参数校验失败: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        :return: 策略信息字典
        """
        return {
            'name': self.name,
            'params': self.params,
            'position': self.position,
            'trades_count': len(self.trades)
        }
    
    def reset(self):
        """重置策略状态"""
        self.position = 0
        self.trades = []
        logger.info(f"策略 {self.name} 状态已重置")


class MAStrategy(StrategyBase):
    """均线策略 - 金叉死叉"""
    
    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'short_period': 5,   # 短期均线周期
            'long_period': 20,   # 长期均线周期
        }
        if params:
            default_params.update(params)
        super().__init__('MA_CrossOver', default_params)
        
        self.short_ma = []
        self.long_ma = []
    
    def init(self):
        """初始化"""
        self.short_ma = []
        self.long_ma = []
        logger.info(f"均线策略初始化完成: 短期{self.params['short_period']}日, "
                   f"长期{self.params['long_period']}日")
    
    def next(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        生成交易信号
        金叉（短期均线上穿长期均线）买入
        死叉（短期均线下穿长期均线）卖出
        """
        if len(data) < self.params['long_period']:
            return {'signal': 'hold', 'price': 0, 'reason': '数据不足'}
        
        # 计算均线
        short_ma = data['close'].tail(self.params['short_period']).mean()
        long_ma = data['close'].tail(self.params['long_period']).mean()
        
        current_price = data['close'].iloc[-1]
        signal = 'hold'
        reason = ''
        
        # 判断交叉
        if len(self.short_ma) > 0 and len(self.long_ma) > 0:
            prev_short = self.short_ma[-1]
            prev_long = self.long_ma[-1]
            
            # 金叉：短期均线从下向上穿过长期均线
            if prev_short <= prev_long and short_ma > long_ma:
                if self.position == 0:
                    signal = 'buy'
                    reason = f'金叉信号: MA{self.params["short_period"]}上穿MA{self.params["long_period"]}'
                    self.position = 1
            
            # 死叉：短期均线从上向下穿过长期均线
            elif prev_short >= prev_long and short_ma < long_ma:
                if self.position == 1:
                    signal = 'sell'
                    reason = f'死叉信号: MA{self.params["short_period"]}下穿MA{self.params["long_period"]}'
                    self.position = 0
        
        # 保存当前均线值
        self.short_ma.append(short_ma)
        self.long_ma.append(long_ma)
        
        return {
            'signal': signal,
            'price': current_price,
            'reason': reason,
            'short_ma': short_ma,
            'long_ma': long_ma
        }


class RSIStrategy(StrategyBase):
    """RSI策略 - 超买超卖"""
    
    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'period': 14,        # RSI周期
            'oversold': 30,      # 超卖阈值
            'overbought': 70,    # 超买阈值
        }
        if params:
            default_params.update(params)
        super().__init__('RSI_OverboughtOversold', default_params)
    
    def init(self):
        """初始化"""
        logger.info(f"RSI策略初始化完成: 周期{self.params['period']}, "
                   f"超卖{self.params['oversold']}, 超买{self.params['overbought']}")
    
    def calculate_rsi(self, data: pd.DataFrame) -> float:
        """计算RSI指标"""
        closes = data['close'].values
        deltas = pd.Series(closes).diff()
        
        gains = deltas.copy()
        losses = deltas.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_gain = gains.tail(self.params['period']).mean()
        avg_loss = losses.tail(self.params['period']).mean()
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def next(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        生成交易信号
        RSI < 超卖阈值：买入信号
        RSI > 超买阈值：卖出信号
        """
        if len(data) < self.params['period'] + 1:
            return {'signal': 'hold', 'price': 0, 'reason': '数据不足'}
        
        rsi = self.calculate_rsi(data)
        current_price = data['close'].iloc[-1]
        signal = 'hold'
        reason = ''
        
        # 超卖，买入信号
        if rsi < self.params['oversold'] and self.position == 0:
            signal = 'buy'
            reason = f'RSI超卖: {rsi:.2f} < {self.params["oversold"]}'
            self.position = 1
        
        # 超买，卖出信号
        elif rsi > self.params['overbought'] and self.position == 1:
            signal = 'sell'
            reason = f'RSI超买: {rsi:.2f} > {self.params["overbought"]}'
            self.position = 0
        
        return {
            'signal': signal,
            'price': current_price,
            'reason': reason,
            'rsi': rsi
        }


class StrategyFactory:
    """策略工厂"""
    
    # 内置策略映射
    BUILTIN_STRATEGIES = {
        'MA_CrossOver': MAStrategy,
        'RSI_OverboughtOversold': RSIStrategy,
        'MACD': None,  # 延迟加载
        'BollingerBands': None,
        'KDJ': None,
        'MA_Volume': None,
        'ATR_Breakout': None,  # ATR突破策略
        'CCI': None,  # CCI策略
        'TurtleTrading': None,  # 海龟交易策略
        'GridTrading': None,  # 网格交易策略
        'WilliamsR': None,  # Williams %R策略
        'DMI': None,  # DMI/ADX策略
        'VWAP': None,  # VWAP策略
        'OBV': None,  # OBV策略
        'TripleScreen': None,  # 三重滤网策略
        'MultiFactor': None,  # 多因子策略
        'MeanReversion': None,  # 均值回归策略
        'MomentumBreakout': None,  # 动量突破策略
        'AlphaArbitrage': None,  # Alpha套利策略
        'DualMAEnhanced': None,  # 双均线增强策略
        'TrendStrength': None,  # 趋势强度策略（ADX+DMI）
        'GapTrading': None,  # 跳空缺口策略
        'SupportResistance': None,  # 支撑阻力突破策略
        'RandomForest': None,  # 随机森林策略
        'LSTM': None,  # LSTM深度学习策略
        'XGBoost': None,  # XGBoost策略
    }
    
    @classmethod
    def _lazy_load_strategy(cls, strategy_name: str):
        """延迟加载策略类"""
        if cls.BUILTIN_STRATEGIES[strategy_name] is None:
            if strategy_name == 'MACD':
                from strategies.macd_strategy import MACDStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = MACDStrategy
            elif strategy_name == 'BollingerBands':
                from strategies.bollinger_strategy import BollingerBandsStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = BollingerBandsStrategy
            elif strategy_name == 'KDJ':
                from strategies.kdj_strategy import KDJStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = KDJStrategy
            elif strategy_name == 'MA_Volume':
                from strategies.ma_volume_strategy import MAVolumeStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = MAVolumeStrategy
            elif strategy_name == 'ATR_Breakout':
                from strategies.atr_breakout_strategy import ATRBreakoutStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = ATRBreakoutStrategy
            elif strategy_name == 'CCI':
                from strategies.cci_strategy import CCIStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = CCIStrategy
            elif strategy_name == 'TurtleTrading':
                from strategies.turtle_trading_strategy import TurtleTradingStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = TurtleTradingStrategy
            elif strategy_name == 'GridTrading':
                from strategies.grid_trading_strategy import GridTradingStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = GridTradingStrategy
            elif strategy_name == 'WilliamsR':
                from strategies.williams_r_strategy import WilliamsRStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = WilliamsRStrategy
            elif strategy_name == 'DMI':
                from strategies.dmi_strategy import DMIStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = DMIStrategy
            elif strategy_name == 'VWAP':
                from strategies.vwap_strategy import VWAPStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = VWAPStrategy
            elif strategy_name == 'OBV':
                from strategies.obv_strategy import OBVStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = OBVStrategy
            elif strategy_name == 'TripleScreen':
                from strategies.triple_screen_strategy import TripleScreenStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = TripleScreenStrategy
            elif strategy_name == 'MultiFactor':
                from strategies.multifactor_strategy import MultiFactorStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = MultiFactorStrategy
            elif strategy_name == 'RandomForest':
                from strategies.random_forest_strategy import RandomForestStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = RandomForestStrategy
            elif strategy_name == 'LSTM':
                from strategies.lstm_strategy import LSTMStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = LSTMStrategy
            elif strategy_name == 'MeanReversion':
                from strategies.mean_reversion_strategy import MeanReversionStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = MeanReversionStrategy
            elif strategy_name == 'MomentumBreakout':
                from strategies.momentum_breakout_strategy import MomentumBreakoutStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = MomentumBreakoutStrategy
            elif strategy_name == 'AlphaArbitrage':
                from strategies.alpha_arbitrage_strategy import AlphaArbitrageStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = AlphaArbitrageStrategy
            elif strategy_name == 'DualMAEnhanced':
                from strategies.dual_ma_enhanced_strategy import DualMAEnhancedStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = DualMAEnhancedStrategy
            elif strategy_name == 'TrendStrength':
                from strategies.trend_strength_strategy import TrendStrengthStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = TrendStrengthStrategy
            elif strategy_name == 'GapTrading':
                from strategies.gap_trading_strategy import GapTradingStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = GapTradingStrategy
            elif strategy_name == 'SupportResistance':
                from strategies.support_resistance_strategy import SupportResistanceStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = SupportResistanceStrategy
            elif strategy_name == 'XGBoost':
                from strategies.xgboost_strategy import XGBoostStrategy
                cls.BUILTIN_STRATEGIES[strategy_name] = XGBoostStrategy
        return cls.BUILTIN_STRATEGIES[strategy_name]
    
    @classmethod
    def create_strategy(cls, strategy_name: str, 
                       params: Dict[str, Any] = None):
        """
        创建策略实例或返回策略类
        :param strategy_name: 策略名称
        :param params: 策略参数（注意：Backtrader策略参数在cerebro.addstrategy时传递）
        :return: 策略实例（简单策略）或策略类（Backtrader策略）
        """
        if strategy_name in cls.BUILTIN_STRATEGIES:
            strategy_class = cls._lazy_load_strategy(strategy_name)
            
            # 判断是否为Backtrader原生策略
            import backtrader as bt
            import inspect
            
            # 检查是否继承自bt.Strategy（通过检查基类）
            try:
                # 尝试实例化以检查是否需要self.data
                sig = inspect.signature(strategy_class.__init__)
                if 'params' in sig.parameters:
                    # 老式策略（MAStrategy, RSIStrategy）- 需要实例化
                    return strategy_class(params)
                else:
                    # 新式策略（Backtrader策略）- 返回类，不实例化
                    # Backtrader会在运行时自动实例化
                    return strategy_class
            except:
                # 如果出现任何错误，返回策略类
                return strategy_class
        else:
            raise ValueError(f"未找到策略: {strategy_name}")
    
    @classmethod
    def get_builtin_strategies(cls) -> List[str]:
        """获取所有内置策略名称"""
        return list(cls.BUILTIN_STRATEGIES.keys())
