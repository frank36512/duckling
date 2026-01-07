"""
动量突破策略 - 追踪强势股
Momentum Breakout Strategy

策略原理：
强者恒强，弱者恒弱。在价格突破关键阻力位时顺势而为

经典应用：
- 理查德·丹尼斯的海龟交易法则
- 威廉·欧奈尔的CANSLIM系统
- 趋势跟踪策略

适用场景：
- 趋势明显的市场
- 成交量放大的突破
- 板块轮动行情
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class MomentumBreakoutStrategy(StrategyMixin, bt.Strategy):
    """
    动量突破策略
    
    策略逻辑：
    1. 识别近期高点（阻力位）
    2. 价格突破 + 成交量放大 = 买入信号
    3. 动量减弱或跌破支撑位 = 卖出信号
    
    核心要素：
    - 价格创新高（突破）
    - 成交量确认（放量）
    - 动量指标（ROC、RSI）
    - 移动止损（保护利润）
    """
    
    params = (
        ('breakout_period', 20),       # 突破周期（20日新高）
        ('volume_threshold', 1.5),     # 成交量放大倍数
        ('roc_threshold', 5),          # ROC阈值（5%以上）
        ('rsi_min', 50),               # RSI最小值（强势区间）
        ('rsi_max', 80),               # RSI最大值（避免超买）
        ('trailing_stop', 0.10),       # 移动止损（10%）
        ('initial_stop', 0.05),        # 初始止损（5%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "动量突破策略"
        self.description = "强者恒强，在价格突破阻力位时顺势买入"
        
        # 价格指标
        self.highest = bt.indicators.Highest(
            self.data.high,
            period=self.params.breakout_period
        )
        
        # 成交量均线
        self.volume_sma = bt.indicators.SMA(
            self.data.volume,
            period=self.params.breakout_period
        )
        
        # 动量指标
        self.roc = bt.indicators.ROC(
            self.data.close,
            period=10
        )
        
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=14
        )
        
        # 移动平均线（趋势判断）
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma60 = bt.indicators.SMA(self.data.close, period=60)
        
        # ATR（波动率，用于止损）
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # 交易状态
        self.buy_price = None
        self.highest_price = None  # 持仓期间的最高价
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: 突破周期={self.params.breakout_period}天, "
                   f"成交量倍数={self.params.volume_threshold}x")
    
    def next(self):
        """策略主逻辑"""
        current_price = self.data.close[0]
        current_volume = self.data.volume[0]
        
        # 如果没有持仓
        if not self.position:
            # 突破买入信号
            # 条件1: 价格创新高（突破阻力）
            is_breakout = current_price >= self.highest[-1]  # 等于或超过前期最高
            
            # 条件2: 成交量放大（确认真突破）
            volume_surge = current_volume > self.volume_sma[0] * self.params.volume_threshold
            
            # 条件3: ROC动量强劲
            strong_momentum = self.roc[0] > self.params.roc_threshold
            
            # 条件4: RSI在强势区间（不过度超买）
            rsi_ok = self.params.rsi_min < self.rsi[0] < self.params.rsi_max
            
            # 条件5: 均线多头排列（趋势向上）
            trend_up = self.sma20[0] > self.sma60[0]
            
            # 条件6: 收盘价在均线上方（趋势确认）
            above_ma = current_price > self.sma20[0]
            
            # 综合判断（至少满足4个条件）
            signals = [is_breakout, volume_surge, strong_momentum, rsi_ok, trend_up, above_ma]
            signal_count = sum(signals)
            
            if signal_count >= 4:
                # 激进策略：高仓位
                size = int(self.broker.get_cash() * 0.95 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    self.highest_price = current_price
                    
                    logger.info(
                        f"[{self.data.datetime.date()}] 动量突破买入"
                        f" | 价格={current_price:.2f}"
                        f" | 前高={self.highest[-1]:.2f}"
                        f" | ROC={self.roc[0]:.2f}%"
                        f" | RSI={self.rsi[0]:.2f}"
                        f" | 成交量={current_volume/self.volume_sma[0]:.2f}x"
                        f" | 信号={signal_count}/6"
                    )
        
        # 如果有持仓
        else:
            # 更新最高价（用于移动止损）
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. 移动止损（从最高点回撤）
            drawdown = (self.highest_price - current_price) / self.highest_price
            if drawdown > self.params.trailing_stop:
                should_sell = True
                sell_reason = f"移动止损(回撤{drawdown*100:.2f}%)"
            
            # 2. 初始止损（保护本金）
            elif profit_ratio <= -self.params.initial_stop:
                should_sell = True
                sell_reason = f"初始止损({profit_ratio*100:.2f}%)"
            
            # 3. 动量衰竭（ROC转负）
            elif self.roc[0] < -3:
                should_sell = True
                sell_reason = f"动量衰竭(ROC={self.roc[0]:.2f}%)"
            
            # 4. RSI超买后回落
            elif self.rsi[0] > 80 or (self.rsi[-1] > 75 and self.rsi[0] < self.rsi[-1] - 5):
                should_sell = True
                sell_reason = f"RSI超买回落({self.rsi[0]:.2f})"
            
            # 5. 跌破20日均线（趋势转弱）
            elif current_price < self.sma20[0] * 0.97:  # 跌破3%
                should_sell = True
                sell_reason = "跌破20日均线"
            
            # 6. 成交量萎缩（上涨动能不足）
            elif (profit_ratio > 0.05 and 
                  current_volume < self.volume_sma[0] * 0.7 and
                  current_price < self.data.close[-1]):  # 缩量下跌
                should_sell = True
                sell_reason = "缩量下跌"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] 动量突破卖出"
                    f" | 价格={current_price:.2f}"
                    f" | 买入价={self.buy_price:.2f}"
                    f" | 最高价={self.highest_price:.2f}"
                    f" | 原因={sell_reason}"
                    f" | 收益率={profit_ratio*100:.2f}%"
                )
                self.buy_price = None
                self.highest_price = None
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"买入成交: 价格={order.executed.price:.2f}, "
                          f"数量={order.executed.size}")
            elif order.issell():
                logger.info(f"卖出成交: 价格={order.executed.price:.2f}, "
                          f"数量={order.executed.size}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"动量突破策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'breakout_period': {
                'name': '突破周期',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 60,
                'description': '多少天的新高算突破'
            },
            'volume_threshold': {
                'name': '成交量倍数',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.1,
                'description': '突破时成交量应放大的倍数'
            },
            'roc_threshold': {
                'name': 'ROC阈值',
                'type': 'float',
                'default': 5,
                'min': 0,
                'max': 15,
                'step': 1,
                'description': '动量指标最小值（%）'
            },
            'trailing_stop': {
                'name': '移动止损',
                'type': 'float',
                'default': 0.10,
                'min': 0.05,
                'max': 0.20,
                'step': 0.01,
                'description': '从最高点回撤多少止损'
            }
        }
