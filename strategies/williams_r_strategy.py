"""
Williams %R策略 - 基于威廉指标的超买超卖策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class WilliamsRStrategy(StrategyMixin, bt.Strategy):
    """
    Williams %R策略
    
    策略原理：
    Williams %R是一个动量指标，衡量当前收盘价在过去N日价格区间中的相对位置
    数值范围：-100 到 0
    - 接近0表示超买（价格接近最高点）
    - 接近-100表示超卖（价格接近最低点）
    
    信号规则：
    - 买入信号：%R从下方上穿超卖线（例如-80）
    - 卖出信号：%R从上方下穿超买线（例如-20）或止损
    """
    
    # 策略参数
    params = (
        ('period', 14),           # Williams %R计算周期
        ('oversold', -80),        # 超卖线（-80表示价格在区间底部20%）
        ('overbought', -20),      # 超买线（-20表示价格在区间顶部20%）
        ('stop_loss', 0.05),      # 止损比例（5%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "Williams %R策略"
        self.description = "威廉指标策略，通过价格在区间中的相对位置判断超买超卖"
        
        # 计算Williams %R指标
        # Williams %R = (最高价 - 收盘价) / (最高价 - 最低价) * -100
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.period)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.period)
        
        # 计算Williams %R
        self.williams_r = -100 * (self.highest - self.data.close) / (self.highest - self.lowest)
        
        # 记录买入价格
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成 - 周期={self.params.period}, "
                   f"超卖线={self.params.oversold}, 超买线={self.params.overbought}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_wr = self.williams_r[0]
        prev_wr = self.williams_r[-1]
        
        # 如果没有持仓
        if not self.position:
            # Williams %R上穿超卖线 - 买入信号
            if prev_wr < self.params.oversold and current_wr >= self.params.oversold:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                logger.info(f"[{self.data.datetime.date()}] Williams %R超卖反弹 - 买入 {size} 股 @ {current_price:.2f} "
                          f"(WR: {current_wr:.2f})")
        
        # 如果持有仓位
        else:
            # Williams %R下穿超买线 - 卖出信号
            if prev_wr > self.params.overbought and current_wr <= self.params.overbought:
                self.sell(size=self.position.size)
                logger.info(f"[{self.data.datetime.date()}] Williams %R超买回调 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(WR: {current_wr:.2f})")
            
            # 止损检查
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss_pct = (current_price / self.buy_price - 1) * 100
                logger.info(f"[{self.data.datetime.date()}] 触发止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(亏损: {loss_pct:.2f}%)")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'period': {
                'name': '计算周期',
                'type': 'int',
                'default': 14,
                'min': 5,
                'max': 50,
                'description': 'Williams %R的计算周期'
            },
            'oversold': {
                'name': '超卖线',
                'type': 'int',
                'default': -80,
                'min': -100,
                'max': -50,
                'description': '超卖阈值，低于此值认为超卖'
            },
            'overbought': {
                'name': '超买线',
                'type': 'int',
                'default': -20,
                'min': -50,
                'max': 0,
                'description': '超买阈值，高于此值认为超买'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.05,
                'min': 0.01,
                'max': 0.20,
                'description': '止损比例（例如0.05表示5%）'
            }
        }
