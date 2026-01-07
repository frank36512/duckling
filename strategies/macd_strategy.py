"""
MACD策略 - 基于MACD指标的交易策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class MACDStrategy(StrategyMixin, bt.Strategy):
    """
    MACD策略
    
    信号规则：
    - 买入信号：MACD线上穿信号线（金叉）
    - 卖出信号：MACD线下穿信号线（死叉）
    """
    
    # 策略参数
    params = (
        ('fast_period', 12),      # 快线周期
        ('slow_period', 26),      # 慢线周期
        ('signal_period', 9),     # 信号线周期
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "MACD策略"
        self.description = "基于MACD指标的趋势跟踪策略，通过MACD线与信号线的交叉产生交易信号"
        
        # 计算MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # MACD线和信号线
        self.macd_line = self.macd.macd
        self.signal_line = self.macd.signal
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.macd_line, self.signal_line)
        
        logger.info(f"{self.name} 初始化完成 - 参数: fast={self.params.fast_period}, slow={self.params.slow_period}, signal={self.params.signal_period}")
    
    def next(self):
        """策略逻辑"""
        # 如果没有持仓
        if not self.position:
            # MACD金叉 - 买入
            if self.crossover > 0:
                size = self.calculate_position_size()
                self.buy(size=size)
                logger.info(f"[{self.data.datetime.date()}] MACD金叉 - 买入 {size} 股")
        
        # 如果持有仓位
        else:
            # MACD死叉 - 卖出
            if self.crossover < 0:
                self.sell(size=self.position.size)
                logger.info(f"[{self.data.datetime.date()}] MACD死叉 - 卖出 {self.position.size} 股")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'fast_period': {
                'name': '快线周期',
                'type': 'int',
                'default': 12,
                'range': (5, 30),
                'description': 'EMA快线周期，通常为12'
            },
            'slow_period': {
                'name': '慢线周期',
                'type': 'int',
                'default': 26,
                'range': (15, 50),
                'description': 'EMA慢线周期，通常为26'
            },
            'signal_period': {
                'name': '信号线周期',
                'type': 'int',
                'default': 9,
                'range': (5, 20),
                'description': '信号线周期，通常为9'
            }
        }
