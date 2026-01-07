"""
VWAP策略 - 基于成交量加权平均价的均值回归策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class VWAPStrategy(StrategyMixin, bt.Strategy):
    """
    VWAP策略 (Volume Weighted Average Price)
    
    策略原理：
    VWAP是成交量加权平均价，代表市场的"公允价值"
    - 价格低于VWAP：相对便宜，可能被低估
    - 价格高于VWAP：相对昂贵，可能被高估
    
    信号规则：
    - 买入信号：价格向下偏离VWAP超过阈值（如2%），认为超卖
    - 卖出信号：价格回归VWAP或向上偏离超过阈值
    
    适用场景：日内交易、大额订单执行
    """
    
    # 策略参数
    params = (
        ('period', 20),              # VWAP计算周期
        ('deviation_buy', 0.02),     # 买入偏离度（2%）
        ('deviation_sell', 0.02),    # 卖出偏离度（2%）
        ('stop_loss', 0.05),         # 止损比例（5%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "VWAP策略"
        self.description = "成交量加权平均价策略，基于价格偏离VWAP的程度进行交易"
        
        # 计算VWAP
        # VWAP = Σ(价格 × 成交量) / Σ成交量
        # 使用典型价格 (High + Low + Close) / 3
        typical_price = (self.data.high + self.data.low + self.data.close) / 3
        
        # 成交量加权的典型价格
        pv = typical_price * self.data.volume
        
        # 计算移动VWAP
        # 使用SumN或替代方案
        try:
            self.vwap = bt.indicators.SumN(pv, period=self.params.period) / \
                        bt.indicators.SumN(self.data.volume, period=self.params.period)
        except (AttributeError, TypeError):
            # 如果SumN不可用，使用SimpleMovingAverage的变体
            # SumN(x, n) ≈ SMA(x, n) * n
            sum_pv = bt.indicators.SMA(pv, period=self.params.period) * self.params.period
            sum_vol = bt.indicators.SMA(self.data.volume, period=self.params.period) * self.params.period
            self.vwap = sum_pv / sum_vol
        
        # 计算价格偏离度
        self.deviation = (self.data.close - self.vwap) / self.vwap
        
        # 记录买入价格
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成 - VWAP周期={self.params.period}, "
                   f"买入偏离={self.params.deviation_buy*100}%, 卖出偏离={self.params.deviation_sell*100}%")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_vwap = self.vwap[0]
        current_deviation = self.deviation[0]
        
        # 如果没有持仓
        if not self.position:
            # 价格低于VWAP且偏离超过阈值 - 买入信号（价格被低估）
            if current_deviation < -self.params.deviation_buy:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                logger.info(f"[{self.data.datetime.date()}] 价格低于VWAP - 买入 {size} 股 @ {current_price:.2f} "
                          f"(VWAP: {current_vwap:.2f}, 偏离: {current_deviation*100:.2f}%)")
        
        # 如果持有仓位
        else:
            # 价格回归VWAP或向上偏离 - 卖出信号
            if current_deviation > self.params.deviation_sell:
                self.sell(size=self.position.size)
                profit_pct = (current_price / self.buy_price - 1) * 100 if self.buy_price else 0
                logger.info(f"[{self.data.datetime.date()}] 价格回归/高于VWAP - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(VWAP: {current_vwap:.2f}, 偏离: {current_deviation*100:.2f}%, 盈亏: {profit_pct:.2f}%)")
            
            # 止损检查
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss_pct = (current_price / self.buy_price - 1) * 100
                logger.info(f"[{self.data.datetime.date()}] 触发止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(亏损: {loss_pct:.2f}%)")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'period': {
                'name': 'VWAP周期',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 60,
                'description': 'VWAP的计算周期'
            },
            'deviation_buy': {
                'name': '买入偏离度',
                'type': 'float',
                'default': 0.02,
                'min': 0.01,
                'max': 0.10,
                'description': '价格低于VWAP的偏离度阈值（例如0.02表示2%）'
            },
            'deviation_sell': {
                'name': '卖出偏离度',
                'type': 'float',
                'default': 0.02,
                'min': 0.01,
                'max': 0.10,
                'description': '价格高于VWAP的偏离度阈值（例如0.02表示2%）'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.05,
                'min': 0.02,
                'max': 0.15,
                'description': '止损比例（例如0.05表示5%）'
            }
        }
