"""
网格交易策略 - 区间震荡套利系统
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class GridTradingStrategy(StrategyMixin, bt.Strategy):
    """
    网格交易策略
    
    策略原理：
    在价格区间内设置网格线，价格下跌到网格线买入，上涨到网格线卖出
    适合震荡行情，不适合单边趋势行情
    
    信号规则：
    - 初始：计算价格中轴和网格间距
    - 买入：价格跌破下方网格线
    - 卖出：价格突破上方网格线
    """
    
    # 策略参数
    params = (
        ('lookback_period', 60),  # 回看周期（用于确定价格区间）
        ('grid_num', 5),          # 网格数量
        ('grid_spacing', 0.05),   # 网格间距（百分比，5%）
        ('max_layers', 3),        # 最大持仓层数
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "网格交易策略"
        self.description = "在震荡区间内高抛低吸，适合横盘震荡行情"
        
        # 计算价格中轴（使用SMA）
        self.price_center = bt.indicators.SMA(self.data.close, period=self.params.lookback_period)
        
        # 计算价格区间
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.lookback_period)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.lookback_period)
        
        # 网格状态
        self.grid_levels = []      # 网格价格
        self.current_layers = 0    # 当前持仓层数
        self.buy_prices = []       # 各层买入价格
        
        logger.info(f"{self.name} 初始化完成 - 网格数量={self.params.grid_num}, "
                   f"网格间距={self.params.grid_spacing*100}%, 最大层数={self.params.max_layers}")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        
        # 动态更新网格（每日更新）
        self._update_grid_levels()
        
        # 如果还没有达到最大持仓层数
        if self.current_layers < self.params.max_layers:
            # 检查是否触及买入网格
            for i, grid_price in enumerate(self.grid_levels):
                if grid_price < current_price and current_price * 0.99 <= grid_price:
                    # 价格接近网格线（允许1%误差）
                    size = self.calculate_position_size() // self.params.max_layers
                    if size > 0:
                        self.buy(size=size)
                        self.buy_prices.append(current_price)
                        self.current_layers += 1
                        
                        logger.info(f"[{self.data.datetime.date()}] 触及网格买入线 - "
                                  f"买入第{self.current_layers}层 {size} 股 @ {current_price:.2f} "
                                  f"(网格价: {grid_price:.2f})")
                        break
        
        # 如果有持仓，检查卖出信号
        if self.current_layers > 0:
            # 计算平均成本
            avg_cost = sum(self.buy_prices) / len(self.buy_prices) if self.buy_prices else current_price
            
            # 价格上涨超过网格间距 - 卖出一层
            profit_threshold = avg_cost * (1 + self.params.grid_spacing)
            if current_price >= profit_threshold:
                sell_size = self.position.size // self.current_layers
                if sell_size > 0:
                    self.sell(size=sell_size)
                    
                    if self.buy_prices:
                        sold_price = self.buy_prices.pop(0)
                        profit = (current_price - sold_price) / sold_price * 100
                    else:
                        profit = 0
                    
                    self.current_layers -= 1
                    
                    logger.info(f"[{self.data.datetime.date()}] 触及网格卖出线 - "
                              f"卖出一层 {sell_size} 股 @ {current_price:.2f} "
                              f"(收益: {profit:.2f}%, 剩余层数: {self.current_layers})")
    
    def _update_grid_levels(self):
        """更新网格价格线"""
        center = self.price_center[0]
        
        # 生成网格价格（中轴上下各grid_num/2条线）
        self.grid_levels = []
        for i in range(-self.params.grid_num // 2, self.params.grid_num // 2 + 1):
            if i == 0:
                continue
            grid_price = center * (1 + i * self.params.grid_spacing)
            self.grid_levels.append(grid_price)
        
        self.grid_levels.sort()
    
    def notify_order(self, order):
        """订单状态通知"""
        super().notify_order(order)
        
        # 如果订单被取消或拒绝，需要调整层数
        if order.status in [order.Canceled, order.Rejected]:
            if order.isbuy():
                # 买入订单失败，不增加层数（已经在买入时增加了）
                pass
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'lookback_period': {
                'name': '回看周期',
                'type': 'int',
                'default': 60,
                'range': (30, 120),
                'description': '确定价格区间的回看周期'
            },
            'grid_num': {
                'name': '网格数量',
                'type': 'int',
                'default': 5,
                'range': (3, 10),
                'description': '网格线数量（总数）'
            },
            'grid_spacing': {
                'name': '网格间距',
                'type': 'float',
                'default': 0.05,
                'range': (0.02, 0.10),
                'description': '网格间距（小数形式，如0.05表示5%）'
            },
            'max_layers': {
                'name': '最大层数',
                'type': 'int',
                'default': 3,
                'range': (2, 5),
                'description': '最大持仓层数（分批买入）'
            }
        }
