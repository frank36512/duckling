"""
三重滤网策略 - Elder博士的多时间框架交易系统
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class TripleScreenStrategy(StrategyMixin, bt.Strategy):
    """
    三重滤网策略 (Triple Screen Trading System)
    
    策略原理：
    由Alexander Elder博士提出的多重时间框架分析方法
    使用三层滤网过滤交易信号，提高成功率
    
    第一重滤网（长期趋势）：
    - 使用周线级别的趋势指标（如MACD、均线）
    - 确定大趋势方向，只做顺势交易
    
    第二重滤网（短期振荡）：
    - 使用日线级别的振荡指标（如随机指标）
    - 寻找回调机会
    
    第三重滤网（入场时机）：
    - 使用价格突破或其他触发信号
    - 确定精确入场点
    
    简化实现（在日线上模拟多时间框架）：
    - 第一重：长期EMA（趋势）
    - 第二重：RSI（振荡）
    - 第三重：价格突破短期高点
    """
    
    # 策略参数
    params = (
        ('long_ema_period', 50),   # 长期趋势均线周期
        ('short_ema_period', 13),  # 短期趋势均线周期
        ('rsi_period', 14),        # RSI周期
        ('rsi_oversold', 30),      # RSI超卖线
        ('rsi_overbought', 70),    # RSI超买线
        ('breakout_period', 3),    # 突破周期（N日最高价）
        ('stop_loss', 0.06),       # 止损比例（6%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "三重滤网策略"
        self.description = "Elder博士的多时间框架交易系统，三重过滤提高成功率"
        
        # 第一重滤网：长期趋势（EMA）
        self.long_ema = bt.indicators.EMA(
            self.data.close,
            period=self.params.long_ema_period
        )
        
        self.short_ema = bt.indicators.EMA(
            self.data.close,
            period=self.params.short_ema_period
        )
        
        # 第二重滤网：短期振荡（RSI）
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
        # 第三重滤网：突破信号
        self.highest = bt.indicators.Highest(
            self.data.high,
            period=self.params.breakout_period
        )
        
        # 记录买入价格
        self.buy_price = None
        
        # 记录滤网状态
        self.screen1_pass = False  # 第一重滤网通过
        self.screen2_pass = False  # 第二重滤网通过
        
        logger.info(f"{self.name} 初始化完成 - 长期EMA={self.params.long_ema_period}, "
                   f"RSI周期={self.params.rsi_period}, 突破周期={self.params.breakout_period}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_high = self.data.high[0]
        
        # 第一重滤网：检查长期趋势
        # 趋势向上：短期EMA > 长期EMA
        self.screen1_pass = self.short_ema[0] > self.long_ema[0]
        
        # 第二重滤网：检查短期回调
        # 在上升趋势中，等待RSI回调到超卖区
        self.screen2_pass = (self.screen1_pass and 
                            self.rsi[0] < self.params.rsi_oversold)
        
        # 如果没有持仓
        if not self.position:
            # 第三重滤网：价格突破
            # 当前价格突破N日最高价
            if (self.screen1_pass and  # 趋势向上
                self.screen2_pass and  # RSI超卖
                current_high > self.highest[-1]):  # 价格突破
                
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                logger.info(f"[{self.data.datetime.date()}] 三重滤网通过 - 买入 {size} 股 @ {current_price:.2f} "
                          f"(EMA趋势向上, RSI: {self.rsi[0]:.2f}, 价格突破)")
        
        # 如果持有仓位
        else:
            # 卖出条件：趋势反转或RSI超买
            if (self.short_ema[0] < self.long_ema[0] or  # 趋势反转
                self.rsi[0] > self.params.rsi_overbought):  # RSI超买
                
                self.sell(size=self.position.size)
                profit_pct = (current_price / self.buy_price - 1) * 100 if self.buy_price else 0
                reason = "趋势反转" if self.short_ema[0] < self.long_ema[0] else "RSI超买"
                logger.info(f"[{self.data.datetime.date()}] {reason} - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(RSI: {self.rsi[0]:.2f}, 盈亏: {profit_pct:.2f}%)")
            
            # 止损检查
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss_pct = (current_price / self.buy_price - 1) * 100
                logger.info(f"[{self.data.datetime.date()}] 触发止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(亏损: {loss_pct:.2f}%)")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'long_ema_period': {
                'name': '长期EMA周期',
                'type': 'int',
                'default': 50,
                'min': 30,
                'max': 100,
                'description': '第一重滤网：长期趋势均线周期'
            },
            'short_ema_period': {
                'name': '短期EMA周期',
                'type': 'int',
                'default': 13,
                'min': 5,
                'max': 30,
                'description': '第一重滤网：短期趋势均线周期'
            },
            'rsi_period': {
                'name': 'RSI周期',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'description': '第二重滤网：RSI指标周期'
            },
            'rsi_oversold': {
                'name': 'RSI超卖线',
                'type': 'int',
                'default': 30,
                'min': 20,
                'max': 40,
                'description': '第二重滤网：RSI超卖阈值'
            },
            'rsi_overbought': {
                'name': 'RSI超买线',
                'type': 'int',
                'default': 70,
                'min': 60,
                'max': 80,
                'description': '卖出信号：RSI超买阈值'
            },
            'breakout_period': {
                'name': '突破周期',
                'type': 'int',
                'default': 3,
                'min': 2,
                'max': 10,
                'description': '第三重滤网：价格突破的参考周期'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.06,
                'min': 0.03,
                'max': 0.15,
                'description': '止损比例（例如0.06表示6%）'
            }
        }
