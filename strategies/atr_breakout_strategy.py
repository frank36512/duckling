"""
ATR突破策略 - 基于平均真实波幅的突破系统
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class ATRBreakoutStrategy(StrategyMixin, bt.Strategy):
    """
    ATR突破策略
    
    策略原理：
    ATR（Average True Range）衡量市场波动性
    当价格突破近期高点+ATR倍数时买入
    当价格跌破近期低点-ATR倍数时卖出
    
    信号规则：
    - 买入信号：收盘价 > N日最高价 + ATR * 突破系数
    - 卖出信号：收盘价 < N日最低价 - ATR * 突破系数 或 止损
    """
    
    # 策略参数
    params = (
        ('atr_period', 14),           # ATR计算周期
        ('lookback_period', 20),      # 回看周期（计算最高/最低价）
        ('breakout_multiplier', 2.0), # ATR突破倍数
        ('stop_multiplier', 3.0),     # ATR止损倍数
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述  
        self.name = "ATR突破策略"
        self.description = "基于平均真实波幅的波动率突破系统，适合趋势行情"
        
        # 计算ATR指标
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # 计算N日最高价和最低价
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.lookback_period)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.lookback_period)
        
        # 记录买入价格
        self.buy_price = None
        self.stop_loss_price = None
        
        logger.info(f"{self.name} 初始化完成 - ATR周期={self.params.atr_period}, "
                   f"回看周期={self.params.lookback_period}, 突破倍数={self.params.breakout_multiplier}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_atr = self.atr[0]
        
        # 如果没有持仓
        if not self.position:
            # 向上突破信号
            breakout_price = self.highest[-1] + current_atr * self.params.breakout_multiplier
            
            if current_price > breakout_price:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                # 设置止损价格
                self.stop_loss_price = current_price - current_atr * self.params.stop_multiplier
                
                logger.info(f"[{self.data.datetime.date()}] 向上突破 - 买入 {size} 股 @ {current_price:.2f} "
                          f"(突破价: {breakout_price:.2f}, 止损价: {self.stop_loss_price:.2f}, ATR: {current_atr:.2f})")
        
        # 如果持有仓位
        else:
            # 向下突破或止损 - 卖出
            breakdown_price = self.lowest[-1] - current_atr * self.params.breakout_multiplier
            
            # 检查止损
            if current_price < self.stop_loss_price:
                self.sell(size=self.position.size)
                profit = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] 触及止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(收益: {profit:.2f}%, 止损价: {self.stop_loss_price:.2f})")
                self.buy_price = None
                self.stop_loss_price = None
            
            # 检查向下突破
            elif current_price < breakdown_price:
                self.sell(size=self.position.size)
                profit = (current_price - self.buy_price) / self.buy_price * 100
                logger.info(f"[{self.data.datetime.date()}] 向下突破 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(收益: {profit:.2f}%, 突破价: {breakdown_price:.2f})")
                self.buy_price = None
                self.stop_loss_price = None
            
            # 动态调整止损（跟踪止损）
            else:
                new_stop = current_price - current_atr * self.params.stop_multiplier
                if new_stop > self.stop_loss_price:
                    self.stop_loss_price = new_stop
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'atr_period': {
                'name': 'ATR周期',
                'type': 'int',
                'default': 14,
                'range': (7, 30),
                'description': 'ATR指标的计算周期'
            },
            'lookback_period': {
                'name': '回看周期',
                'type': 'int',
                'default': 20,
                'range': (10, 50),
                'description': '计算最高价和最低价的回看周期'
            },
            'breakout_multiplier': {
                'name': '突破倍数',
                'type': 'float',
                'default': 2.0,
                'range': (1.0, 4.0),
                'description': 'ATR的突破倍数，越大越难突破'
            },
            'stop_multiplier': {
                'name': '止损倍数',
                'type': 'float',
                'default': 3.0,
                'range': (2.0, 5.0),
                'description': 'ATR的止损倍数，越大止损越宽'
            }
        }
