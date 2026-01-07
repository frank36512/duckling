"""
KDJ策略 - 基于KDJ指标的超买超卖策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class KDJStrategy(StrategyMixin, bt.Strategy):
    """
    KDJ策略
    
    信号规则：
    - 买入信号：K值和D值都小于超卖线，且K线上穿D线
    - 卖出信号：K值和D值都大于超买线，且K线下穿D线
    """
    
    # 策略参数
    params = (
        ('period', 9),            # KDJ周期
        ('period_dfast', 3),      # K值平滑周期
        ('period_dslow', 3),      # D值平滑周期
        ('oversold', 20),         # 超卖线
        ('overbought', 80),       # 超买线
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "KDJ策略"
        self.description = "基于KDJ指标的超买超卖策略，利用KD交叉和超买超卖区域产生交易信号"
        
        # 计算Stochastic指标（KDJ的基础）
        self.stoch = bt.indicators.Stochastic(
            self.data,
            period=self.params.period,
            period_dfast=self.params.period_dfast,
            period_dslow=self.params.period_dslow
        )
        
        # K线和D线
        self.k_line = self.stoch.percK
        self.d_line = self.stoch.percD
        
        # KD交叉
        self.crossover = bt.indicators.CrossOver(self.k_line, self.d_line)
        
        logger.info(f"{self.name} 初始化完成 - 参数: period={self.params.period}, oversold={self.params.oversold}, overbought={self.params.overbought}")
    
    def next(self):
        """策略逻辑"""
        k_value = self.k_line[0]
        d_value = self.d_line[0]
        
        # 如果没有持仓
        if not self.position:
            # 超卖区域 + K线上穿D线 - 买入
            if k_value < self.params.oversold and d_value < self.params.oversold:
                if self.crossover > 0:
                    size = self.calculate_position_size()
                    self.buy(size=size)
                    logger.info(f"[{self.data.datetime.date()}] KDJ超卖金叉 - 买入 {size} 股 (K={k_value:.2f}, D={d_value:.2f})")
        
        # 如果持有仓位
        else:
            # 超买区域 + K线下穿D线 - 卖出
            if k_value > self.params.overbought and d_value > self.params.overbought:
                if self.crossover < 0:
                    self.sell(size=self.position.size)
                    logger.info(f"[{self.data.datetime.date()}] KDJ超买死叉 - 卖出 {self.position.size} 股 (K={k_value:.2f}, D={d_value:.2f})")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'period': {
                'name': 'KDJ周期',
                'type': 'int',
                'default': 9,
                'range': (5, 20),
                'description': 'KDJ指标计算周期'
            },
            'period_dfast': {
                'name': 'K值平滑',
                'type': 'int',
                'default': 3,
                'range': (2, 5),
                'description': 'K值平滑周期'
            },
            'period_dslow': {
                'name': 'D值平滑',
                'type': 'int',
                'default': 3,
                'range': (2, 5),
                'description': 'D值平滑周期'
            },
            'oversold': {
                'name': '超卖线',
                'type': 'int',
                'default': 20,
                'range': (10, 30),
                'description': '超卖阈值，低于此值为超卖'
            },
            'overbought': {
                'name': '超买线',
                'type': 'int',
                'default': 80,
                'range': (70, 90),
                'description': '超买阈值，高于此值为超买'
            }
        }
