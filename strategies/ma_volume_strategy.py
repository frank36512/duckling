"""
双均线+成交量策略 - 结合均线和成交量的趋势策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class MAVolumeStrategy(StrategyMixin, bt.Strategy):
    """
    双均线+成交量策略
    
    信号规则：
    - 买入信号：短期均线上穿长期均线 + 成交量放大
    - 卖出信号：短期均线下穿长期均线 或 止损
    """
    
    # 策略参数
    params = (
        ('short_period', 5),      # 短期均线周期
        ('long_period', 20),      # 长期均线周期
        ('volume_period', 20),    # 成交量均线周期
        ('volume_factor', 1.5),   # 成交量放大倍数
        ('stop_loss', 0.05),      # 止损比例（5%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "双均线+成交量策略"
        self.description = "结合价格均线和成交量的趋势跟踪策略，要求成交量配合确认信号"
        
        # 计算短期和长期均线
        self.sma_short = bt.indicators.SMA(self.data.close, period=self.params.short_period)
        self.sma_long = bt.indicators.SMA(self.data.close, period=self.params.long_period)
        
        # 均线交叉
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)
        
        # 成交量均线
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=self.params.volume_period)
        
        # 记录买入价格
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成 - 参数: short={self.params.short_period}, long={self.params.long_period}, vol_factor={self.params.volume_factor}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_volume = self.data.volume[0]
        avg_volume = self.volume_sma[0]
        
        # 如果没有持仓
        if not self.position:
            # 金叉 + 成交量放大 - 买入
            if self.crossover > 0 and current_volume > avg_volume * self.params.volume_factor:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                logger.info(f"[{self.data.datetime.date()}] 金叉+放量 - 买入 {size} 股 @ {current_price:.2f} (成交量: {current_volume/avg_volume:.2f}倍)")
        
        # 如果持有仓位
        else:
            # 死叉 - 卖出
            if self.crossover < 0:
                self.sell(size=self.position.size)
                profit = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] 死叉 - 卖出 {self.position.size} 股 @ {current_price:.2f} (收益: {profit:.2f}%)")
                self.buy_price = None
            
            # 止损
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] 止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} (亏损: {loss:.2f}%)")
                self.buy_price = None
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'short_period': {
                'name': '短期均线',
                'type': 'int',
                'default': 5,
                'range': (3, 15),
                'description': '短期移动平均线周期'
            },
            'long_period': {
                'name': '长期均线',
                'type': 'int',
                'default': 20,
                'range': (15, 60),
                'description': '长期移动平均线周期'
            },
            'volume_period': {
                'name': '成交量周期',
                'type': 'int',
                'default': 20,
                'range': (10, 30),
                'description': '成交量移动平均线周期'
            },
            'volume_factor': {
                'name': '放量倍数',
                'type': 'float',
                'default': 1.5,
                'range': (1.2, 3.0),
                'description': '成交量需要达到均值的倍数'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.05,
                'range': (0.03, 0.15),
                'description': '止损比例（小数形式，如0.05表示5%）'
            }
        }
