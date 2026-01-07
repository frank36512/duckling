"""
策略辅助类和工具函数
"""

import backtrader as bt
from datetime import datetime


class StrategyMixin:
    """策略混入类，提供通用的辅助方法"""
    
    def __init__(self):
        """初始化时添加交易记录列表"""
        super().__init__()  # 调用父类（bt.Strategy）的初始化
        self.trade_records = []
        self.order_records = {}  # 记录订单信息，用于构建完整交易
    
    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Completed]:
            # 记录订单执行信息
            if order.isbuy():
                self.order_records[order.ref] = {
                    'type': 'buy',
                    'date': bt.num2date(order.executed.dt).strftime('%Y-%m-%d'),
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value,
                    'commission': order.executed.comm
                }
            elif order.issell():
                self.order_records[order.ref] = {
                    'type': 'sell',
                    'date': bt.num2date(order.executed.dt).strftime('%Y-%m-%d'),
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value,
                    'commission': order.executed.comm
                }
    
    def notify_trade(self, trade):
        """
        交易完成通知（一次买入+卖出构成一次完整交易）
        """
        if trade.isclosed:
            # 避免除零错误
            if trade.size == 0 or trade.value == 0:
                return
            
            # 记录完整的交易信息
            trade_info = {
                'entry_date': bt.num2date(trade.dtopen).strftime('%Y-%m-%d'),
                'exit_date': bt.num2date(trade.dtclose).strftime('%Y-%m-%d'),
                'entry_price': trade.price,
                'exit_price': trade.price + trade.pnl / trade.size,
                'size': trade.size,
                'pnl': trade.pnl,
                'pnl_percent': (trade.pnl / trade.value) * 100,
                'commission': trade.commission,
                'holding_days': (trade.dtclose - trade.dtopen)
            }
            self.trade_records.append(trade_info)
    
    def calculate_position_size(self):
        """
        计算仓位大小
        使用可用资金的95%，按100股整数倍买入
        
        Returns:
            int: 购买股数
        """
        cash = self.broker.get_cash() * 0.95
        price = self.data.close[0]
        size = int(cash / price / 100) * 100  # 按100股整数倍
        return max(size, 100)  # 至少买100股
