"""
双均线交叉增强策略 - 加入成交量和动量确认
Dual Moving Average Enhanced Strategy

策略原理：
在经典双均线金叉死叉基础上，加入成交量和动量确认，提高胜率

经典应用：
- 格兰威尔八大法则
- 道氏理论的趋势确认
- 葛兰碧移动平均线理论

适用场景：
- 趋势明显的市场
- 大盘股、蓝筹股
- 中长线投资
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class DualMAEnhancedStrategy(StrategyMixin, bt.Strategy):
    """
    双均线交叉增强策略
    
    策略逻辑：
    1. 快线上穿慢线（金叉）+ 成交量放大 = 买入
    2. 快线下穿慢线（死叉） = 卖出
    3. 加入ROC动量确认，避免假突破
    
    经典参数：
    - 快线5日/10日，慢线20日/60日
    - 葛兰碧经典：5日/20日
    """
    
    params = (
        ('fast_period', 10),           # 快速均线周期
        ('slow_period', 30),           # 慢速均线周期
        ('volume_factor', 1.2),        # 成交量放大倍数
        ('roc_threshold', 0),          # ROC阈值（动量确认）
        ('stop_loss', 0.08),           # 止损比例
        ('trailing_stop', 0.15),       # 移动止损
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "双均线增强策略"
        self.description = "经典双均线+成交量+动量确认，提高可靠性"
        
        # 快慢均线
        self.fast_ma = bt.indicators.SMA(
            self.data.close,
            period=self.params.fast_period
        )
        
        self.slow_ma = bt.indicators.SMA(
            self.data.close,
            period=self.params.slow_period
        )
        
        # 均线交叉信号
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # 成交量均线
        self.volume_ma = bt.indicators.SMA(
            self.data.volume,
            period=20
        )
        
        # 动量指标
        self.roc = bt.indicators.ROC(
            self.data.close,
            period=10
        )
        
        # MACD（辅助判断）
        self.macd = bt.indicators.MACD(self.data.close)
        
        # 交易状态
        self.buy_price = None
        self.highest_price = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: 快线MA{self.params.fast_period}, "
                   f"慢线MA{self.params.slow_period}")
    
    def next(self):
        """策略主逻辑"""
        current_price = self.data.close[0]
        current_volume = self.data.volume[0]
        
        # 如果没有持仓
        if not self.position:
            # 金叉买入信号
            if self.crossover[0] > 0:  # 快线上穿慢线
                # 确认条件
                # 1. 成交量放大
                volume_ok = current_volume > self.volume_ma[0] * self.params.volume_factor
                
                # 2. 动量向上
                momentum_ok = self.roc[0] > self.params.roc_threshold
                
                # 3. MACD支持
                macd_ok = self.macd.macd[0] > self.macd.signal[0]
                
                # 4. 价格在慢线上方（趋势向上）
                trend_ok = current_price > self.slow_ma[0]
                
                # 综合判断（至少满足3个条件）
                signals = [volume_ok, momentum_ok, macd_ok, trend_ok]
                signal_count = sum(signals)
                
                if signal_count >= 3:
                    size = int(self.broker.get_cash() * 0.95 / current_price / 100) * 100
                    
                    if size >= 100:
                        self.buy(size=size)
                        self.buy_price = current_price
                        self.highest_price = current_price
                        
                        logger.info(
                            f"[{self.data.datetime.date()}] 双均线金叉买入"
                            f" | 价格={current_price:.2f}"
                            f" | 快线={self.fast_ma[0]:.2f}"
                            f" | 慢线={self.slow_ma[0]:.2f}"
                            f" | 成交量={current_volume/self.volume_ma[0]:.2f}x"
                            f" | ROC={self.roc[0]:.2f}%"
                            f" | 确认信号={signal_count}/4"
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
            
            # 1. 死叉（主要出场信号）
            if self.crossover[0] < 0:  # 快线下穿慢线
                should_sell = True
                sell_reason = "死叉信号"
            
            # 2. 移动止损
            elif drawdown > self.params.trailing_stop:
                should_sell = True
                sell_reason = f"移动止损(回撤{drawdown*100:.2f}%)"
            
            # 3. 固定止损
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 4. 价格跌破慢线
            elif current_price < self.slow_ma[0] * 0.98:
                should_sell = True
                sell_reason = "跌破慢线"
            
            # 5. 动量转负
            elif self.roc[0] < -5:
                should_sell = True
                sell_reason = f"动量转负(ROC={self.roc[0]:.2f}%)"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] 双均线卖出"
                    f" | 价格={current_price:.2f}"
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
                logger.info(f"买入成交: 价格={order.executed.price:.2f}")
            elif order.issell():
                logger.info(f"卖出成交: 价格={order.executed.price:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"双均线策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'fast_period': {
                'name': '快速均线周期',
                'type': 'int',
                'default': 10,
                'min': 5,
                'max': 30,
                'description': '短期均线天数'
            },
            'slow_period': {
                'name': '慢速均线周期',
                'type': 'int',
                'default': 30,
                'min': 20,
                'max': 120,
                'description': '长期均线天数'
            },
            'volume_factor': {
                'name': '成交量倍数',
                'type': 'float',
                'default': 1.2,
                'min': 1.0,
                'max': 2.0,
                'step': 0.1,
                'description': '金叉时成交量应放大的倍数'
            }
        }
