"""
跳空缺口策略 - 利用价格跳空获利
Gap Trading Strategy

策略原理：
利用市场心理和技术分析，交易跳空缺口
- 突破缺口：顺势跟进
- 衰竭缺口：反向操作
- 普通缺口：等待回补

经典理论：
- 日本蜡烛图技术
- 缺口理论（艾略特波浪）
- 市场心理学

适用场景：
- 重大消息公布后
- 财报季
- 市场情绪剧烈变化
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class GapTradingStrategy(StrategyMixin, bt.Strategy):
    """
    跳空缺口交易策略
    
    策略逻辑：
    1. 向上突破缺口（Gap Up > 2%）+ 成交量放大 = 买入
    2. 向下衰竭缺口（Gap Down后快速回补）= 买入
    3. 缺口回补 = 卖出
    
    缺口类型：
    - 突破缺口：新趋势开始，不回补
    - 持续缺口：趋势中途，快速回补
    - 衰竭缺口：趋势末期，必然回补
    """
    
    params = (
        ('gap_threshold', 0.02),       # 缺口阈值（2%）
        ('volume_factor', 1.5),        # 成交量放大倍数
        ('hold_days', 5),              # 最大持仓天数
        ('stop_loss', 0.05),           # 止损比例
        ('take_profit', 0.10),         # 止盈比例
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "跳空缺口策略"
        self.description = "利用价格跳空和缺口回补获利"
        
        # 成交量均线
        self.volume_ma = bt.indicators.SMA(
            self.data.volume,
            period=20
        )
        
        # RSI（判断超买超卖）
        self.rsi = bt.indicators.RSI(self.data, period=14)
        
        # ATR（波动率）
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # 均线（趋势判断）
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        
        # 交易状态
        self.buy_price = None
        self.gap_price = None  # 缺口价格
        self.holding_days = 0
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: 缺口阈值={self.params.gap_threshold*100}%, "
                   f"成交量倍数={self.params.volume_factor}x")
    
    def next(self):
        """策略主逻辑"""
        if len(self) < 2:  # 需要至少2天数据
            return
        
        current_price = self.data.close[0]
        current_open = self.data.open[0]
        prev_close = self.data.close[-1]
        current_volume = self.data.volume[0]
        
        # 计算缺口
        gap_ratio = (current_open - prev_close) / prev_close
        
        # 如果没有持仓
        if not self.position:
            # 向上突破缺口买入
            if gap_ratio > self.params.gap_threshold:
                # 确认条件
                # 1. 成交量放大
                volume_surge = current_volume > self.volume_ma[0] * self.params.volume_factor
                
                # 2. 缺口后继续上涨（突破缺口特征）
                continued_up = current_price > current_open
                
                # 3. 趋势向上
                uptrend = self.sma20[0] > self.sma20[-5]
                
                # 4. RSI不超买
                not_overbought = self.rsi[0] < 70
                
                # 综合判断
                if volume_surge and (continued_up or uptrend) and not_overbought:
                    size = int(self.broker.get_cash() * 0.9 / current_price / 100) * 100
                    
                    if size >= 100:
                        self.buy(size=size)
                        self.buy_price = current_price
                        self.gap_price = prev_close
                        self.holding_days = 0
                        
                        logger.info(
                            f"[{self.data.datetime.date()}] 向上突破缺口买入"
                            f" | 开盘={current_open:.2f}"
                            f" | 昨收={prev_close:.2f}"
                            f" | 缺口={gap_ratio*100:.2f}%"
                            f" | 成交量={current_volume/self.volume_ma[0]:.2f}x"
                        )
            
            # 向下衰竭缺口买入（反转机会）
            elif gap_ratio < -self.params.gap_threshold:
                # 确认条件
                # 1. 低开后快速拉升（衰竭缺口特征）
                quick_recovery = current_price > current_open * 1.01
                
                # 2. RSI超卖
                oversold = self.rsi[0] < 30
                
                # 3. 价格接近或高于昨日收盘（缺口回补）
                gap_filled = current_price >= prev_close * 0.98
                
                if quick_recovery and (oversold or gap_filled):
                    size = int(self.broker.get_cash() * 0.8 / current_price / 100) * 100
                    
                    if size >= 100:
                        self.buy(size=size)
                        self.buy_price = current_price
                        self.gap_price = prev_close
                        self.holding_days = 0
                        
                        logger.info(
                            f"[{self.data.datetime.date()}] 向下衰竭缺口买入"
                            f" | 开盘={current_open:.2f}"
                            f" | 现价={current_price:.2f}"
                            f" | 缺口={gap_ratio*100:.2f}%"
                            f" | RSI={self.rsi[0]:.2f}"
                        )
        
        # 如果有持仓
        else:
            self.holding_days += 1
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. 止盈
            if profit_ratio >= self.params.take_profit:
                should_sell = True
                sell_reason = f"止盈({profit_ratio*100:.2f}%)"
            
            # 2. 止损
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 3. 缺口回补（价格回到缺口价格）
            elif self.gap_price and abs(current_price - self.gap_price) < self.atr[0] * 0.5:
                should_sell = True
                sell_reason = "缺口回补"
            
            # 4. 持仓时间过长
            elif self.holding_days >= self.params.hold_days:
                should_sell = True
                sell_reason = f"持仓过久({self.holding_days}天)"
            
            # 5. 反向跳空
            elif gap_ratio < -0.01:  # 向下跳空1%
                should_sell = True
                sell_reason = "反向跳空"
            
            # 6. RSI超买
            elif self.rsi[0] > 80:
                should_sell = True
                sell_reason = "RSI超买"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] 缺口策略卖出"
                    f" | 价格={current_price:.2f}"
                    f" | 原因={sell_reason}"
                    f" | 收益率={profit_ratio*100:.2f}%"
                    f" | 持仓={self.holding_days}天"
                )
                self.buy_price = None
                self.gap_price = None
                self.holding_days = 0
    
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
            logger.warning(f"缺口策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'gap_threshold': {
                'name': '缺口阈值',
                'type': 'float',
                'default': 0.02,
                'min': 0.01,
                'max': 0.05,
                'step': 0.005,
                'description': '跳空缺口的最小幅度（比例）'
            },
            'volume_factor': {
                'name': '成交量倍数',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.1,
                'description': '突破时成交量放大倍数'
            },
            'hold_days': {
                'name': '最大持仓天数',
                'type': 'int',
                'default': 5,
                'min': 3,
                'max': 10,
                'description': '超过此天数自动平仓'
            }
        }
