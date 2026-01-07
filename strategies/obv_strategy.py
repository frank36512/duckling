"""
OBV策略 - 基于能量潮指标的趋势确认策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class OBVIndicator(bt.Indicator):
    """自定义OBV指标 - 能量潮指标"""
    lines = ('obv',)
    
    def __init__(self):
        # OBV是成交量的累积，根据价格变化决定加减
        # 使用list来存储累积值
        pass
    
    def next(self):
        if len(self) == 1:
            # 第一天，OBV等于成交量
            self.lines.obv[0] = self.data.volume[0]
        else:
            # 价格上涨，OBV增加
            if self.data.close[0] > self.data.close[-1]:
                self.lines.obv[0] = self.lines.obv[-1] + self.data.volume[0]
            # 价格下跌，OBV减少
            elif self.data.close[0] < self.data.close[-1]:
                self.lines.obv[0] = self.lines.obv[-1] - self.data.volume[0]
            # 价格不变，OBV不变
            else:
                self.lines.obv[0] = self.lines.obv[-1]


class OBVStrategy(StrategyMixin, bt.Strategy):
    """
    OBV策略 (On-Balance Volume)
    
    策略原理：
    OBV是一个累积型的成交量指标：
    - 当日收盘价 > 前日收盘价：OBV += 当日成交量
    - 当日收盘价 < 前日收盘价：OBV -= 当日成交量
    - 当日收盘价 = 前日收盘价：OBV 不变
    
    OBV用于确认价格趋势：
    - 价格上涨 + OBV上涨：趋势健康，继续持有
    - 价格上涨 + OBV下跌：量价背离，可能反转
    
    信号规则：
    - 买入信号：OBV上穿其均线 且 价格上涨
    - 卖出信号：OBV下穿其均线 或 量价背离
    """
    
    # 策略参数
    params = (
        ('obv_period', 20),       # OBV均线周期
        ('price_period', 5),      # 价格短期均线周期
        ('stop_loss', 0.06),      # 止损比例（6%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "OBV策略"
        self.description = "能量潮指标策略，通过成交量变化确认价格趋势"
        
        # 计算OBV指标（使用自定义指标）
        self.obv = OBVIndicator(self.data)
        
        # OBV的移动平均
        self.obv_ma = bt.indicators.SimpleMovingAverage(
            self.obv, 
            period=self.params.obv_period
        )
        
        # 价格的短期均线
        self.price_ma = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.price_period
        )
        
        # 记录买入价格和买入时的OBV
        self.buy_price = None
        self.buy_obv = None
        
        logger.info(f"{self.name} 初始化完成 - OBV均线周期={self.params.obv_period}, "
                   f"价格均线周期={self.params.price_period}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        current_obv = self.obv[0]
        current_obv_ma = self.obv_ma[0]
        prev_obv = self.obv[-1]
        prev_obv_ma = self.obv_ma[-1]
        
        # 如果没有持仓
        if not self.position:
            # OBV上穿其均线 且 价格在均线上方（双重确认）
            if (prev_obv <= prev_obv_ma and 
                current_obv > current_obv_ma and 
                current_price > self.price_ma[0]):
                
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                self.buy_obv = current_obv
                logger.info(f"[{self.data.datetime.date()}] OBV金叉+价格走强 - 买入 {size} 股 @ {current_price:.2f} "
                          f"(OBV: {current_obv:.0f}, OBV-MA: {current_obv_ma:.0f})")
        
        # 如果持有仓位
        else:
            # OBV下穿其均线 - 卖出信号
            if prev_obv >= prev_obv_ma and current_obv < current_obv_ma:
                self.sell(size=self.position.size)
                profit_pct = (current_price / self.buy_price - 1) * 100 if self.buy_price else 0
                logger.info(f"[{self.data.datetime.date()}] OBV死叉 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(OBV: {current_obv:.0f}, 盈亏: {profit_pct:.2f}%)")
            
            # 量价背离检查：价格创新高但OBV未创新高
            elif (self.buy_price and self.buy_obv and 
                  current_price > self.buy_price * 1.05 and  # 价格上涨超过5%
                  current_obv < self.buy_obv):  # 但OBV没有同步上涨
                
                self.sell(size=self.position.size)
                profit_pct = (current_price / self.buy_price - 1) * 100
                logger.info(f"[{self.data.datetime.date()}] 量价背离 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(价格涨: {profit_pct:.2f}%, OBV降: {(current_obv/self.buy_obv-1)*100:.2f}%)")
            
            # 止损检查
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss_pct = (current_price / self.buy_price - 1) * 100
                logger.info(f"[{self.data.datetime.date()}] 触发止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(亏损: {loss_pct:.2f}%)")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'obv_period': {
                'name': 'OBV均线周期',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 50,
                'description': 'OBV移动平均线的周期'
            },
            'price_period': {
                'name': '价格均线周期',
                'type': 'int',
                'default': 5,
                'min': 3,
                'max': 20,
                'description': '价格短期移动平均线的周期'
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
