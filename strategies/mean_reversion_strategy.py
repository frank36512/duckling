"""
均值回归策略 - 经典量化策略
Mean Reversion Strategy

策略原理：
价格偏离均值后会回归均值，在超跌时买入，超涨时卖出

适用场景：
- 震荡市场
- 有支撑阻力位的股票
- 流动性好的标的

风险提示：
- 趋势市场中可能持续亏损
- 需要严格止损
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class MeanReversionStrategy(StrategyMixin, bt.Strategy):
    """
    均值回归策略
    
    策略逻辑：
    1. 计算价格相对于均线的偏离度（Z-Score）
    2. 当偏离度超过阈值时，预期价格会回归
    3. 超跌（Z-Score < -2）时买入
    4. 回归到均值或超涨时卖出
    
    核心指标：
    - 移动平均线（MA）
    - 标准差（Std）
    - Z-Score = (Price - MA) / Std
    """
    
    params = (
        ('lookback_period', 20),      # 均值回归周期
        ('entry_zscore', -2.0),        # 入场Z-Score（负值表示超跌）
        ('exit_zscore', 0.0),          # 出场Z-Score（回归均值）
        ('stop_loss', 0.05),           # 止损比例（5%）
        ('take_profit', 0.10),         # 止盈比例（10%）
        ('max_holding_days', 10),      # 最大持仓天数
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "均值回归策略"
        self.description = "价格偏离均值后会回归，在超跌时买入，超涨时卖出"
        
        # 计算移动平均线和标准差
        self.sma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.lookback_period
        )
        
        # 计算标准差
        self.std = bt.indicators.StandardDeviation(
            self.data.close,
            period=self.params.lookback_period
        )
        
        # 计算Z-Score（价格偏离度）
        self.zscore = (self.data.close - self.sma) / self.std
        
        # 布林带（辅助判断）
        self.bollinger = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.lookback_period,
            devfactor=2
        )
        
        # 交易状态
        self.buy_price = None
        self.buy_date = None
        self.holding_days = 0
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: 回看周期={self.params.lookback_period}, "
                   f"入场Z={self.params.entry_zscore}, 出场Z={self.params.exit_zscore}")
    
    def next(self):
        """策略主逻辑"""
        current_price = self.data.close[0]
        current_zscore = self.zscore[0]
        
        # 如果没有持仓
        if not self.position:
            # 判断是否超跌（买入信号）
            # 条件1: Z-Score低于入场阈值
            zscore_signal = current_zscore < self.params.entry_zscore
            
            # 条件2: 价格接近或低于布林带下轨（确认超跌）
            near_lower_band = current_price <= self.bollinger.bot[0] * 1.02
            
            # 条件3: 确保有足够数据
            has_data = len(self.data) > self.params.lookback_period
            
            if zscore_signal and near_lower_band and has_data:
                # 计算仓位（越超跌买得越多，但不超过95%资金）
                zscore_abs = abs(current_zscore)
                position_ratio = min(0.95, 0.5 + (zscore_abs - 2) * 0.15)
                
                size = int(self.broker.get_cash() * position_ratio / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    self.buy_date = len(self)
                    self.holding_days = 0
                    
                    logger.info(
                        f"[{self.data.datetime.date()}] 均值回归买入信号"
                        f" | 价格={current_price:.2f}"
                        f" | Z-Score={current_zscore:.2f}"
                        f" | 均值={self.sma[0]:.2f}"
                        f" | 偏离度={(current_price/self.sma[0]-1)*100:.2f}%"
                        f" | 仓位={position_ratio*100:.0f}%"
                    )
        
        # 如果有持仓
        else:
            self.holding_days += 1
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. 价格回归到均值（主要出场信号）
            if current_zscore >= self.params.exit_zscore:
                should_sell = True
                sell_reason = f"回归均值(Z={current_zscore:.2f})"
            
            # 2. 止盈
            elif profit_ratio >= self.params.take_profit:
                should_sell = True
                sell_reason = f"止盈({profit_ratio*100:.2f}%)"
            
            # 3. 止损
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 4. 持仓时间过长
            elif self.holding_days >= self.params.max_holding_days:
                should_sell = True
                sell_reason = f"持仓过久({self.holding_days}天)"
            
            # 5. 价格突破上轨（反转信号，可能进入趋势）
            elif current_price > self.bollinger.top[0]:
                should_sell = True
                sell_reason = "突破上轨(可能反转)"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] 均值回归卖出"
                    f" | 价格={current_price:.2f}"
                    f" | 原因={sell_reason}"
                    f" | 收益率={profit_ratio*100:.2f}%"
                    f" | Z-Score={current_zscore:.2f}"
                )
                self.buy_price = None
                self.buy_date = None
                self.holding_days = 0
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"买入成交: 价格={order.executed.price:.2f}, "
                          f"数量={order.executed.size}, "
                          f"手续费={order.executed.comm:.2f}")
            elif order.issell():
                logger.info(f"卖出成交: 价格={order.executed.price:.2f}, "
                          f"数量={order.executed.size}, "
                          f"手续费={order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"均值回归策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息（用于UI配置）"""
        return {
            'lookback_period': {
                'name': '均值回归周期',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 60,
                'description': '计算均值和标准差的周期'
            },
            'entry_zscore': {
                'name': '入场Z-Score',
                'type': 'float',
                'default': -2.0,
                'min': -3.0,
                'max': -1.0,
                'step': 0.1,
                'description': '超跌阈值，越负表示越超跌'
            },
            'exit_zscore': {
                'name': '出场Z-Score',
                'type': 'float',
                'default': 0.0,
                'min': -0.5,
                'max': 1.0,
                'step': 0.1,
                'description': '回归阈值，0表示回到均值'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.05,
                'min': 0.02,
                'max': 0.10,
                'step': 0.01,
                'description': '最大亏损比例'
            },
            'take_profit': {
                'name': '止盈比例',
                'type': 'float',
                'default': 0.10,
                'min': 0.05,
                'max': 0.20,
                'step': 0.01,
                'description': '目标盈利比例'
            }
        }
