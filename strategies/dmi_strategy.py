"""
DMI/ADX策略 - 基于方向性运动指标的趋势跟踪策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class DMIStrategy(StrategyMixin, bt.Strategy):
    """
    DMI/ADX策略
    
    策略原理：
    DMI (Directional Movement Index) 包含三条线：
    - ADX (Average Directional Index): 趋势强度指标
    - +DI (Positive Directional Indicator): 上升动能
    - -DI (Negative Directional Indicator): 下降动能
    
    ADX > 25 表示强趋势，ADX < 20 表示无趋势
    
    信号规则：
    - 买入信号：+DI上穿-DI 且 ADX > 阈值（强趋势确认）
    - 卖出信号：-DI上穿+DI 或 ADX下降（趋势减弱）
    """
    
    # 策略参数
    params = (
        ('period', 14),           # DMI计算周期
        ('adx_threshold', 25),    # ADX阈值，大于此值认为是强趋势
        ('stop_loss', 0.08),      # 止损比例（8%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "DMI/ADX策略"
        self.description = "方向性运动指标策略，结合趋势强度进行交易"
        
        # 计算DMI指标
        # 使用backtrader的标准指标
        self.adx = bt.indicators.ADX(
            self.data,
            period=self.params.period
        )
        self.plus_di = bt.indicators.PlusDI(
            self.data,
            period=self.params.period
        )
        self.minus_di = bt.indicators.MinusDI(
            self.data,
            period=self.params.period
        )
        
        # 记录买入价格
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成 - 周期={self.params.period}, "
                   f"ADX阈值={self.params.adx_threshold}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_adx = self.adx[0]
        current_plus_di = self.plus_di[0]
        current_minus_di = self.minus_di[0]
        prev_plus_di = self.plus_di[-1]
        prev_minus_di = self.minus_di[-1]
        
        # 如果没有持仓
        if not self.position:
            # +DI上穿-DI 且 ADX显示强趋势
            if (prev_plus_di <= prev_minus_di and 
                current_plus_di > current_minus_di and 
                current_adx > self.params.adx_threshold):
                
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                logger.info(f"[{self.data.datetime.date()}] DMI金叉+强趋势 - 买入 {size} 股 @ {current_price:.2f} "
                          f"(+DI: {current_plus_di:.2f}, -DI: {current_minus_di:.2f}, ADX: {current_adx:.2f})")
        
        # 如果持有仓位
        else:
            # -DI上穿+DI（趋势反转）
            if prev_minus_di <= prev_plus_di and current_minus_di > current_plus_di:
                self.sell(size=self.position.size)
                logger.info(f"[{self.data.datetime.date()}] DMI死叉 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(+DI: {current_plus_di:.2f}, -DI: {current_minus_di:.2f})")
            
            # ADX下降（趋势减弱）- 如果ADX连续下降且低于阈值
            elif current_adx < self.params.adx_threshold and self.adx[-1] > current_adx:
                self.sell(size=self.position.size)
                logger.info(f"[{self.data.datetime.date()}] 趋势减弱 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(ADX: {current_adx:.2f})")
            
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
                'name': '计算周期',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'description': 'DMI指标的计算周期'
            },
            'adx_threshold': {
                'name': 'ADX阈值',
                'type': 'float',
                'default': 25,
                'min': 15,
                'max': 40,
                'description': 'ADX强趋势阈值，大于此值认为是强趋势'
            },
            'stop_loss': {
                'name': '止损比例',
                'type': 'float',
                'default': 0.08,
                'min': 0.03,
                'max': 0.15,
                'description': '止损比例（例如0.08表示8%）'
            }
        }
