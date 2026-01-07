"""
海龟交易策略 - 经典趋势跟踪系统
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class TurtleTradingStrategy(StrategyMixin, bt.Strategy):
    """
    海龟交易策略
    
    策略原理：
    海龟交易法则由传奇交易员Richard Dennis设计
    使用唐奇安通道（Donchian Channel）进行突破交易
    
    信号规则：
    - 买入信号：价格突破N日最高价
    - 卖出信号：价格跌破M日最低价
    - 止损：使用ATR动态止损
    """
    
    # 策略参数
    params = (
        ('entry_period', 20),    # 入场周期（突破N日最高）
        ('exit_period', 10),     # 出场周期（跌破M日最低）
        ('atr_period', 20),      # ATR周期
        ('atr_multiplier', 2.0), # ATR止损倍数
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "海龟交易策略"
        self.description = "经典趋势跟踪系统，使用唐奇安通道突破"
        
        # 计算唐奇安通道（入场）
        self.entry_high = bt.indicators.Highest(self.data.high, period=self.params.entry_period)
        self.entry_low = bt.indicators.Lowest(self.data.low, period=self.params.entry_period)
        
        # 计算唐奇安通道（出场）
        self.exit_high = bt.indicators.Highest(self.data.high, period=self.params.exit_period)
        self.exit_low = bt.indicators.Lowest(self.data.low, period=self.params.exit_period)
        
        # 计算ATR
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # 记录买入价格和止损价
        self.buy_price = None
        self.stop_loss_price = None
        
        logger.info(f"{self.name} 初始化完成 - 入场周期={self.params.entry_period}, "
                   f"出场周期={self.params.exit_period}, ATR倍数={self.params.atr_multiplier}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_high = self.data.high[0]
        current_low = self.data.low[0]
        current_atr = self.atr[0]
        
        # 如果没有持仓
        if not self.position:
            # 价格突破N日最高 - 买入
            if current_high > self.entry_high[-1]:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                # 设置ATR止损
                self.stop_loss_price = current_price - current_atr * self.params.atr_multiplier
                
                logger.info(f"[{self.data.datetime.date()}] 突破{self.params.entry_period}日高点 - "
                          f"买入 {size} 股 @ {current_price:.2f} "
                          f"(高点: {self.entry_high[-1]:.2f}, 止损: {self.stop_loss_price:.2f})")
        
        # 如果持有仓位
        else:
            # 检查ATR止损
            if current_low < self.stop_loss_price:
                self.sell(size=self.position.size)
                profit = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] ATR止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(收益: {profit:.2f}%, 止损价: {self.stop_loss_price:.2f})")
                self.buy_price = None
                self.stop_loss_price = None
            
            # 价格跌破M日最低 - 卖出
            elif current_low < self.exit_low[-1]:
                self.sell(size=self.position.size)
                profit = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] 跌破{self.params.exit_period}日低点 - "
                          f"卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(收益: {profit:.2f}%, 低点: {self.exit_low[-1]:.2f})")
                self.buy_price = None
                self.stop_loss_price = None
            
            # 动态调整止损（跟踪止损）
            else:
                new_stop = current_price - current_atr * self.params.atr_multiplier
                if new_stop > self.stop_loss_price:
                    old_stop = self.stop_loss_price
                    self.stop_loss_price = new_stop
                    logger.debug(f"[{self.data.datetime.date()}] 止损上移: {old_stop:.2f} -> {new_stop:.2f}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'entry_period': {
                'name': '入场周期',
                'type': 'int',
                'default': 20,
                'range': (10, 55),
                'description': '突破N日最高价入场（海龟原版为20或55）'
            },
            'exit_period': {
                'name': '出场周期',
                'type': 'int',
                'default': 10,
                'range': (5, 20),
                'description': '跌破M日最低价出场（海龟原版为10或20）'
            },
            'atr_period': {
                'name': 'ATR周期',
                'type': 'int',
                'default': 20,
                'range': (10, 30),
                'description': 'ATR指标的计算周期'
            },
            'atr_multiplier': {
                'name': 'ATR倍数',
                'type': 'float',
                'default': 2.0,
                'range': (1.5, 3.0),
                'description': 'ATR止损倍数（海龟原版为2）'
            }
        }
