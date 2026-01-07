"""
支撑阻力突破策略 - 关键价位突破
Support Resistance Breakout Strategy

策略原理：
识别历史重要价位（支撑/阻力），价格突破后顺势交易
市场记忆理论：历史价位会影响未来走势

经典理论：
- 道氏理论
- 波浪理论的关键点位
- 江恩理论的价格支撑

适用场景：
- 横盘整理后突破
- 前期高点/低点突破
- 重要心理价位
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class SupportResistanceStrategy(StrategyMixin, bt.Strategy):
    """
    支撑阻力突破策略
    
    策略逻辑：
    1. 识别近期高点（阻力位）和低点（支撑位）
    2. 价格突破阻力 + 成交量确认 = 买入
    3. 价格跌破支撑 = 卖出
    4. 假突破快速止损
    
    关键要素：
    - 价格历史极值
    - 成交量确认真突破
    - 假突破识别
    """
    
    params = (
        ('lookback_period', 20),       # 回看周期（寻找支撑阻力）
        ('breakout_threshold', 0.01),  # 突破确认阈值（1%）
        ('volume_factor', 1.5),        # 成交量放大倍数
        ('stop_loss', 0.05),           # 止损比例
        ('trailing_stop', 0.12),       # 移动止损
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "支撑阻力突破策略"
        self.description = "识别关键价位，突破后顺势交易"
        
        # 最高价和最低价
        self.highest = bt.indicators.Highest(
            self.data.high,
            period=self.params.lookback_period
        )
        
        self.lowest = bt.indicators.Lowest(
            self.data.low,
            period=self.params.lookback_period
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SMA(
            self.data.volume,
            period=20
        )
        
        # ATR（波动率）
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # RSI
        self.rsi = bt.indicators.RSI(self.data, period=14)
        
        # 均线（趋势）
        self.sma50 = bt.indicators.SMA(self.data.close, period=50)
        
        # 交易状态
        self.buy_price = None
        self.resistance_level = None  # 阻力位
        self.highest_price = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: 回看周期={self.params.lookback_period}天")
    
    def next(self):
        """策略主逻辑"""
        if len(self) < self.params.lookback_period:
            return
        
        current_price = self.data.close[0]
        current_volume = self.data.volume[0]
        
        # 计算当前支撑阻力位
        resistance = self.highest[-1]  # 前期高点
        support = self.lowest[-1]      # 前期低点
        
        # 如果没有持仓
        if not self.position:
            # 突破阻力位买入
            # 条件1: 价格突破阻力位
            breakout = current_price > resistance * (1 + self.params.breakout_threshold)
            
            # 条件2: 成交量放大（真突破）
            volume_confirm = current_volume > self.volume_ma[0] * self.params.volume_factor
            
            # 条件3: 收盘价确认突破（不是假突破）
            close_confirm = current_price > resistance
            
            # 条件4: 趋势向上
            uptrend = current_price > self.sma50[0]
            
            # 条件5: RSI不超买
            not_overbought = self.rsi[0] < 75
            
            # 条件6: 价格在合理区间（不是极端突破）
            reasonable_range = (current_price - resistance) / resistance < 0.05
            
            # 综合判断
            if breakout and volume_confirm and close_confirm and uptrend and not_overbought and reasonable_range:
                size = int(self.broker.get_cash() * 0.95 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    self.resistance_level = resistance
                    self.highest_price = current_price
                    
                    # 计算支撑阻力比率（技术分析指标）
                    sr_ratio = (resistance - support) / support
                    
                    logger.info(
                        f"[{self.data.datetime.date()}] 突破阻力位买入"
                        f" | 价格={current_price:.2f}"
                        f" | 阻力={resistance:.2f}"
                        f" | 支撑={support:.2f}"
                        f" | 突破幅度={(current_price/resistance-1)*100:.2f}%"
                        f" | 成交量={current_volume/self.volume_ma[0]:.2f}x"
                        f" | 箱体高度={sr_ratio*100:.2f}%"
                    )
        
        # 如果有持仓
        else:
            # 更新最高价
            if current_price > self.highest_price:
                self.highest_price = current_price
            
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            drawdown = (self.highest_price - current_price) / self.highest_price
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. 移动止损（从最高点回撤）
            if drawdown > self.params.trailing_stop:
                should_sell = True
                sell_reason = f"移动止损(回撤{drawdown*100:.2f}%)"
            
            # 2. 固定止损（跌破买入价）
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 3. 跌破原阻力位（假突破确认）
            elif self.resistance_level and current_price < self.resistance_level * 0.99:
                should_sell = True
                sell_reason = "跌破阻力转支撑"
            
            # 4. 创新高后RSI超买
            elif profit_ratio > 0.05 and self.rsi[0] > 80:
                should_sell = True
                sell_reason = "RSI超买"
            
            # 5. 成交量萎缩且价格滞涨
            elif (profit_ratio > 0.03 and 
                  current_volume < self.volume_ma[0] * 0.7 and
                  current_price < self.data.close[-1]):
                should_sell = True
                sell_reason = "缩量滞涨"
            
            # 6. 跌破50日均线
            elif current_price < self.sma50[0] * 0.98:
                should_sell = True
                sell_reason = "跌破50日均线"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] 支撑阻力卖出"
                    f" | 价格={current_price:.2f}"
                    f" | 最高价={self.highest_price:.2f}"
                    f" | 原因={sell_reason}"
                    f" | 收益率={profit_ratio*100:.2f}%"
                )
                self.buy_price = None
                self.resistance_level = None
                self.highest_price = None
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"买入成交: 价格={order.executed.price:.2f}")
            elif order.issell():
                logger.info(f"卖出成交: 价格={order.executed.price:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"支撑阻力策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'lookback_period': {
                'name': '回看周期',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 60,
                'description': '寻找支撑阻力的历史周期'
            },
            'breakout_threshold': {
                'name': '突破确认阈值',
                'type': 'float',
                'default': 0.01,
                'min': 0.005,
                'max': 0.03,
                'step': 0.005,
                'description': '突破阻力位的最小幅度'
            },
            'volume_factor': {
                'name': '成交量倍数',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.1,
                'description': '突破时成交量放大倍数'
            }
        }
