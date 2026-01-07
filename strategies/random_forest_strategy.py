"""
随机森林策略 - 基于机器学习的量化交易策略
使用随机森林算法预测股票走势
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class RandomForestStrategy(StrategyMixin, bt.Strategy):
    """
    随机森林策略
    
    策略原理：
    使用随机森林机器学习模型预测股价走势
    基于技术指标特征训练模型，预测未来涨跌
    
    信号规则：
    - 买入信号：模型预测上涨概率 > 阈值
    - 卖出信号：模型预测下跌概率 > 阈值 或 持有达到最大周期
    
    注意：
    - 需要先训练模型才能使用
    - 建议在参数优化页面进行模型训练
    - 训练数据应包含至少500-1000个样本
    """
    
    # 策略参数
    params = (
        ('lookback_period', 20),      # 回看周期
        ('prediction_threshold', 0.6), # 预测阈值
        ('max_holding_period', 10),    # 最大持有周期
        ('use_pretrained_model', False), # 是否使用预训练模型
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "随机森林策略"
        self.description = "使用随机森林算法预测股票走势的机器学习策略"
        
        # 计算技术指标作为特征
        self.sma5 = bt.indicators.SMA(self.data.close, period=5)
        self.sma10 = bt.indicators.SMA(self.data.close, period=10)
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.rsi = bt.indicators.RSI(self.data, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        
        # 模型相关
        self.model = None  # 随机森林模型（需要外部训练）
        self.holding_days = 0
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.warning("⚠️ 随机森林策略需要先训练模型，请在参数优化页面训练或加载预训练模型")
    
    def next(self):
        """策略逻辑"""
        # 如果没有模型，使用简单的技术指标规则作为替代
        if self.model is None:
            self._simple_trading_logic()
            return
        
        # TODO: 实际的机器学习预测逻辑
        # 这里需要：
        # 1. 提取当前的特征值
        # 2. 使用模型进行预测
        # 3. 根据预测结果生成交易信号
        
        self._simple_trading_logic()
    
    def _simple_trading_logic(self):
        """简单交易逻辑（未训练模型时使用）"""
        current_price = self.data.close[0]
        
        # 如果没有持仓
        if not self.position:
            # 多重技术指标确认
            # 条件1：短期均线上穿长期均线
            sma_cross = self.sma5[0] > self.sma10[0] > self.sma20[0]
            
            # 条件2：RSI在合理区间（30-70）
            rsi_ok = 30 < self.rsi[0] < 70
            
            # 条件3：MACD金叉
            macd_cross = self.macd.macd[0] > self.macd.signal[0]
            
            if sma_cross and rsi_ok and macd_cross:
                # 计算仓位
                size = int(self.broker.get_cash() * 0.95 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    self.holding_days = 0
                    logger.info(f"买入信号: 价格={current_price:.2f}, 数量={size}")
        
        # 如果有持仓
        else:
            self.holding_days += 1
            
            # 卖出条件
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            
            # 条件1：达到止盈目标（5%）
            take_profit = profit_ratio >= 0.05
            
            # 条件2：触发止损（-3%）
            stop_loss = profit_ratio <= -0.03
            
            # 条件3：持有时间过长
            holding_too_long = self.holding_days >= self.params.max_holding_period
            
            # 条件4：技术指标转弱
            sma_cross_down = self.sma5[0] < self.sma10[0]
            macd_cross_down = self.macd.macd[0] < self.macd.signal[0]
            tech_weak = sma_cross_down or macd_cross_down
            
            if take_profit or stop_loss or holding_too_long or tech_weak:
                self.close()
                reason = "止盈" if take_profit else ("止损" if stop_loss else ("持有过长" if holding_too_long else "技术转弱"))
                logger.info(f"卖出信号: 价格={current_price:.2f}, 原因={reason}, 收益率={profit_ratio*100:.2f}%")
                self.holding_days = 0
                self.buy_price = None
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"买入成交: 价格={order.executed.price:.2f}, 成本={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}")
            elif order.issell():
                logger.info(f"卖出成交: 价格={order.executed.price:.2f}, 收入={order.executed.value:.2f}, 手续费={order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"RandomForest订单失败: {order.status}")
