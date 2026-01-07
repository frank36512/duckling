"""
布林带策略 - 基于布林带的突破策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class BollingerBandsStrategy(StrategyMixin, bt.Strategy):
    """
    布林带策略
    
    信号规则：
    - 买入信号：价格触及下轨并反弹
    - 卖出信号：价格触及上轨
    """
    
    # 策略参数
    params = (
        ('period', 20),           # 均线周期
        ('devfactor', 2.0),       # 标准差倍数
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "布林带策略"
        self.description = "基于布林带的均值回归策略，价格触及下轨买入，触及上轨卖出"
        
        # 计算布林带
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor
        )
        
        # 上轨、中轨、下轨
        self.top_band = self.boll.top
        self.mid_band = self.boll.mid
        self.bot_band = self.boll.bot
        
        logger.info(f"{self.name} 初始化完成 - 参数: period={self.params.period}, dev={self.params.devfactor}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        
        # 如果没有持仓
        if not self.position:
            # 价格触及或跌破下轨 - 买入
            if current_price <= self.bot_band[0]:
                size = self.calculate_position_size()
                self.buy(size=size)
                logger.info(f"[{self.data.datetime.date()}] 价格触及下轨 - 买入 {size} 股 @ {current_price:.2f}")
        
        # 如果持有仓位
        else:
            # 价格触及或突破上轨 - 卖出
            if current_price >= self.top_band[0]:
                self.sell(size=self.position.size)
                logger.info(f"[{self.data.datetime.date()}] 价格触及上轨 - 卖出 {self.position.size} 股 @ {current_price:.2f}")
            
            # 或者价格回到中轨以上 - 部分获利
            elif current_price >= self.mid_band[0] and len(self) > 10:
                sell_size = int(self.position.size * 0.5)
                if sell_size > 0:
                    self.sell(size=sell_size)
                    logger.info(f"[{self.data.datetime.date()}] 回到中轨 - 卖出一半 {sell_size} 股 @ {current_price:.2f}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'period': {
                'name': '均线周期',
                'type': 'int',
                'default': 20,
                'range': (10, 50),
                'description': '布林带中轨（移动平均线）周期'
            },
            'devfactor': {
                'name': '标准差倍数',
                'type': 'float',
                'default': 2.0,
                'range': (1.0, 3.0),
                'description': '上下轨距离中轨的标准差倍数'
            }
        }
