"""
LSTM策略 - 基于深度学习的量化交易策略
使用长短期记忆网络（LSTM）预测股票价格序列
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class LSTMStrategy(StrategyMixin, bt.Strategy):
    """
    LSTM策略（Long Short-Term Memory）
    
    策略原理：
    使用LSTM深度学习模型捕捉股价时间序列的长期依赖关系
    通过学习历史价格模式预测未来走势
    
    信号规则：
    - 买入信号：LSTM预测价格上涨 > 阈值
    - 卖出信号：LSTM预测价格下跌 > 阈值 或 止损
    
    注意：
    - LSTM模型需要大量数据训练（建议1000+样本）
    - 训练时间较长，需要较高计算资源
    - 建议使用GPU加速训练
    - 模型容易过拟合，需要careful validation
    """
    
    # 策略参数
    params = (
        ('sequence_length', 60),       # 序列长度（输入天数）
        ('prediction_horizon', 1),     # 预测时间范围
        ('confidence_threshold', 0.02), # 置信度阈值（2%）
        ('stop_loss', 0.03),           # 止损比例（3%）
        ('take_profit', 0.05),         # 止盈比例（5%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "LSTM策略"
        self.description = "使用长短期记忆网络预测股价序列的深度学习策略"
        
        # 计算基础指标
        self.sma = bt.indicators.SMA(self.data.close, period=20)
        self.rsi = bt.indicators.RSI(self.data, period=14)
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # 价格变化率
        self.price_change = bt.indicators.ROC(self.data.close, period=1)
        
        # 模型相关
        self.model = None  # LSTM模型（需要外部训练）
        self.scaler = None  # 数据标准化器
        self.price_sequence = []  # 价格序列缓存
        
        # 交易状态
        self.buy_price = None
        self.buy_date = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.warning("⚠️ LSTM策略需要先训练深度学习模型，建议使用GPU加速")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        
        # 维护价格序列
        self.price_sequence.append(current_price)
        if len(self.price_sequence) > self.params.sequence_length:
            self.price_sequence.pop(0)
        
        # 如果模型未训练，使用简单趋势跟踪
        if self.model is None:
            self._simple_trend_following()
            return
        
        # TODO: LSTM预测逻辑
        # 实际使用时需要：
        # 1. 准备输入序列（标准化）
        # 2. 使用LSTM模型预测
        # 3. 根据预测结果生成信号
        
        self._simple_trend_following()
    
    def _simple_trend_following(self):
        """简单趋势跟踪逻辑（未训练模型时使用）"""
        current_price = self.data.close[0]
        
        # 如果没有持仓
        if not self.position:
            # 趋势确认：价格高于均线 + RSI不超买 + 价格上涨
            trend_up = current_price > self.sma[0]
            rsi_ok = self.rsi[0] < 70
            momentum_up = self.price_change[0] > 0
            
            if trend_up and rsi_ok and momentum_up:
                size = int(self.broker.get_cash() * 0.95 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    self.buy_date = len(self)
                    logger.info(f"LSTM买入: 价格={current_price:.2f}, 数量={size}")
        
        # 如果有持仓
        else:
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            holding_days = len(self) - self.buy_date
            
            # 止盈
            if profit_ratio >= self.params.take_profit:
                self.close()
                logger.info(f"LSTM止盈: 价格={current_price:.2f}, 收益={profit_ratio*100:.2f}%")
                self.buy_price = None
            
            # 止损
            elif profit_ratio <= -self.params.stop_loss:
                self.close()
                logger.info(f"LSTM止损: 价格={current_price:.2f}, 亏损={profit_ratio*100:.2f}%")
                self.buy_price = None
            
            # 趋势反转
            elif current_price < self.sma[0] and self.price_change[0] < 0:
                self.close()
                logger.info(f"LSTM趋势反转: 价格={current_price:.2f}, 持有{holding_days}天")
                self.buy_price = None
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"LSTM买入成交: 价格={order.executed.price:.2f}")
            elif order.issell():
                logger.info(f"LSTM卖出成交: 价格={order.executed.price:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"LSTM订单失败: {order.status}")
