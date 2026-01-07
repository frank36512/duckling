"""
趋势强度策略 - ADX+DMI组合
Trend Strength Strategy

策略原理：
使用ADX判断趋势强度，DMI判断趋势方向
只在强趋势中交易，提高胜率

经典理论：
- 威尔斯·怀尔德（Welles Wilder）发明
- 《技术分析新概念》经典指标
- ADX>25表示强趋势

适用场景：
- 趋势明显的市场
- 避免震荡市频繁交易
- 适合中长线持有
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class TrendStrengthStrategy(StrategyMixin, bt.Strategy):
    """
    趋势强度策略（ADX+DMI）
    
    策略逻辑：
    1. ADX > 阈值：确认强趋势存在
    2. +DI > -DI：上升趋势，买入
    3. -DI > +DI：下降趋势，卖出
    4. ADX转弱：趋势结束，平仓
    
    经典信号：
    - ADX > 25：强趋势
    - ADX > 50：极强趋势
    - ADX < 20：无趋势（震荡）
    """
    
    params = (
        ('dmi_period', 14),            # DMI周期
        ('adx_threshold', 25),         # ADX强趋势阈值
        ('adx_weak', 20),              # ADX弱势阈值
        ('stop_loss', 0.08),           # 止损比例
        ('take_profit', 0.20),         # 止盈比例
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "趋势强度策略"
        self.description = "ADX+DMI组合，只在强趋势中交易"
        
        # DMI指标
        self.dmi = bt.indicators.DirectionalMovement(
            self.data,
            period=self.params.dmi_period
        )
        
        # ADX（平均趋向指数）
        self.adx = bt.indicators.AverageDirectionalMovementIndex(
            self.data,
            period=self.params.dmi_period
        )
        
        # +DI和-DI
        self.plus_di = self.dmi.plusDI
        self.minus_di = self.dmi.minusDI
        
        # 辅助指标
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma60 = bt.indicators.SMA(self.data.close, period=60)
        
        # 交易状态
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: DMI周期={self.params.dmi_period}, "
                   f"ADX阈值={self.params.adx_threshold}")
    
    def next(self):
        """策略主逻辑"""
        current_price = self.data.close[0]
        
        # 获取当前ADX和DI值
        adx_value = self.adx[0]
        plus_di_value = self.plus_di[0]
        minus_di_value = self.minus_di[0]
        
        # 如果没有持仓
        if not self.position:
            # 买入条件
            # 1. ADX显示强趋势
            strong_trend = adx_value > self.params.adx_threshold
            
            # 2. +DI > -DI（上升趋势）
            uptrend = plus_di_value > minus_di_value
            
            # 3. +DI和-DI差距较大（趋势明确）
            di_gap = abs(plus_di_value - minus_di_value) > 5
            
            # 4. 价格在均线上方（趋势确认）
            above_ma = current_price > self.sma20[0] > self.sma60[0]
            
            # 5. ADX上升（趋势增强）
            adx_rising = len(self) > 1 and self.adx[0] > self.adx[-1]
            
            # 综合判断
            if strong_trend and uptrend and (di_gap or above_ma) and adx_rising:
                size = int(self.broker.get_cash() * 0.9 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    
                    logger.info(
                        f"[{self.data.datetime.date()}] 趋势强度买入"
                        f" | 价格={current_price:.2f}"
                        f" | ADX={adx_value:.2f}"
                        f" | +DI={plus_di_value:.2f}"
                        f" | -DI={minus_di_value:.2f}"
                        f" | 趋势强度={'强' if adx_value > 40 else '中'}"
                    )
        
        # 如果有持仓
        else:
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. 趋势反转（-DI上穿+DI）
            if minus_di_value > plus_di_value:
                should_sell = True
                sell_reason = "趋势反转"
            
            # 2. ADX转弱（趋势消失）
            elif adx_value < self.params.adx_weak:
                should_sell = True
                sell_reason = f"趋势转弱(ADX={adx_value:.2f})"
            
            # 3. ADX下降明显（趋势减弱）
            elif (len(self) > 5 and 
                  self.adx[0] < self.adx[-5] - 10):
                should_sell = True
                sell_reason = "趋势减弱"
            
            # 4. 止盈
            elif profit_ratio >= self.params.take_profit:
                should_sell = True
                sell_reason = f"止盈({profit_ratio*100:.2f}%)"
            
            # 5. 止损
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 6. 跌破均线支撑
            elif current_price < self.sma20[0] * 0.97:
                should_sell = True
                sell_reason = "跌破均线"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] 趋势强度卖出"
                    f" | 价格={current_price:.2f}"
                    f" | ADX={adx_value:.2f}"
                    f" | 原因={sell_reason}"
                    f" | 收益率={profit_ratio*100:.2f}%"
                )
                self.buy_price = None
    
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
            logger.warning(f"趋势强度策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'dmi_period': {
                'name': 'DMI周期',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 28,
                'description': 'DMI和ADX的计算周期'
            },
            'adx_threshold': {
                'name': 'ADX强趋势阈值',
                'type': 'float',
                'default': 25,
                'min': 20,
                'max': 40,
                'description': 'ADX超过此值才交易'
            },
            'adx_weak': {
                'name': 'ADX弱势阈值',
                'type': 'float',
                'default': 20,
                'min': 15,
                'max': 25,
                'description': 'ADX低于此值平仓'
            }
        }
