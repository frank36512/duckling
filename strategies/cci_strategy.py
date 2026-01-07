"""
CCI策略 - 商品通道指数策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class CCIStrategy(StrategyMixin, bt.Strategy):
    """
    CCI策略（Commodity Channel Index）
    
    策略原理：
    CCI衡量价格偏离其统计平均值的程度
    CCI > +100 表示超买，CCI < -100 表示超卖
    
    信号规则：
    - 买入信号：CCI从下方上穿-100（超卖反弹）
    - 卖出信号：CCI从上方下穿+100（超买回调）或止损
    """
    
    # 策略参数
    params = (
        ('cci_period', 20),        # CCI计算周期
        ('oversold_level', -100),  # 超卖水平
        ('overbought_level', 100), # 超买水平
        ('stop_loss', 0.05),       # 止损比例（5%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "CCI策略"
        self.description = "商品通道指数策略，捕捉超买超卖反转机会"
        
        # 计算CCI指标
        self.cci = bt.indicators.CCI(self.data, period=self.params.cci_period)
        
        # 记录买入价格
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成 - CCI周期={self.params.cci_period}, "
                   f"超卖水平={self.params.oversold_level}, 超买水平={self.params.overbought_level}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_cci = self.cci[0]
        prev_cci = self.cci[-1]
        
        # 如果没有持仓
        if not self.position:
            # CCI上穿超卖线 - 买入信号
            if prev_cci < self.params.oversold_level and current_cci >= self.params.oversold_level:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                
                logger.info(f"[{self.data.datetime.date()}] CCI超卖反弹 - 买入 {size} 股 @ {current_price:.2f} "
                          f"(CCI: {prev_cci:.2f} -> {current_cci:.2f})")
        
        # 如果持有仓位
        else:
            # CCI下穿超买线 - 卖出信号
            if prev_cci > self.params.overbought_level and current_cci <= self.params.overbought_level:
                self.sell(size=self.position.size)
                profit = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] CCI超买回调 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(收益: {profit:.2f}%, CCI: {prev_cci:.2f} -> {current_cci:.2f})")
                self.buy_price = None
            
            # 止损
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] 触及止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(亏损: {loss:.2f}%)")
                self.buy_price = None
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'cci_period': {
                'name': 'CCI周期',
                'type': 'int',
                'default': 20,
                'range': (10, 30),
                'description': 'CCI指标的计算周期'
            },
            'oversold_level': {
                'name': '超卖水平',
                'type': 'int',
                'default': -100,
                'range': (-200, -50),
                'description': 'CCI超卖阈值，越低越保守'
            },
            'overbought_level': {
                'name': '超买水平',
                'type': 'int',
                'default': 100,
                'range': (50, 200),
                'description': 'CCI超买阈值，越高越保守'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.05,
                'range': (0.03, 0.15),
                'description': '止损比例（小数形式，如0.05表示5%）'
            }
        }
