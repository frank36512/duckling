"""
XGBoost策略 - 基于梯度提升树的量化交易策略
使用XGBoost算法进行特征工程和价格预测
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class XGBoostStrategy(StrategyMixin, bt.Strategy):
    """
    XGBoost策略（eXtreme Gradient Boosting）
    
    策略原理：
    使用XGBoost集成学习算法，通过多个技术指标特征预测价格走势
    XGBoost具有高效率、高精度、支持特征重要性分析等优点
    
    特征工程：
    - 价格指标：SMA、EMA、布林带
    - 动量指标：RSI、MACD、ROC
    - 成交量指标：OBV、Volume SMA
    - 波动率指标：ATR、Bollinger Width
    
    信号规则：
    - 买入信号：XGBoost预测上涨概率 > 阈值
    - 卖出信号：预测下跌概率 > 阈值 或 达到止损/止盈
    
    注意：
    - XGBoost训练速度快，适合快速迭代
    - 需要careful特征选择避免过拟合
    - 建议定期重新训练模型（如每月）
    """
    
    # 策略参数
    params = (
        ('n_estimators', 100),          # 树的数量
        ('max_depth', 5),               # 树的最大深度
        ('learning_rate', 0.1),         # 学习率
        ('prediction_threshold', 0.6),  # 预测阈值（60%概率）
        ('stop_loss', 0.03),            # 止损比例（3%）
        ('take_profit', 0.05),          # 止盈比例（5%）
        ('max_holding_days', 15),       # 最大持仓天数
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "XGBoost策略"
        self.description = "使用梯度提升树预测价格走势的机器学习策略"
        
        # 价格指标
        self.sma5 = bt.indicators.SMA(self.data.close, period=5)
        self.sma10 = bt.indicators.SMA(self.data.close, period=10)
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.ema12 = bt.indicators.EMA(self.data.close, period=12)
        
        # 布林带
        self.bollinger = bt.indicators.BollingerBands(self.data.close, period=20)
        
        # 动量指标
        self.rsi = bt.indicators.RSI(self.data, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        self.roc = bt.indicators.ROC(self.data.close, period=10)
        
        # 波动率指标
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # 成交量指标
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=20)
        
        # 模型相关
        self.model = None  # XGBoost模型（需要外部训练）
        self.feature_scaler = None  # 特征标准化器
        
        # 交易状态
        self.buy_price = None
        self.buy_date = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.warning("⚠️ XGBoost策略需要先训练模型，请在参数优化页面训练或加载预训练模型")
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        
        # 如果模型未训练，使用多因子策略
        if self.model is None:
            self._multifactor_strategy()
            return
        
        # TODO: XGBoost预测逻辑
        # 实际使用时需要：
        # 1. 提取当前特征向量
        # 2. 使用XGBoost模型预测
        # 3. 根据预测概率生成信号
        
        self._multifactor_strategy()
    
    def _multifactor_strategy(self):
        """多因子策略逻辑（未训练模型时使用）"""
        current_price = self.data.close[0]
        
        # 如果没有持仓
        if not self.position:
            # 多因子买入条件
            # 1. 趋势因子：短期均线上穿长期均线
            trend_signal = (self.sma5[0] > self.sma10[0] > self.sma20[0])
            
            # 2. 动量因子：RSI在合理区间 + MACD金叉
            momentum_signal = (30 < self.rsi[0] < 70 and 
                              self.macd.macd[0] > self.macd.signal[0] and
                              self.roc[0] > 0)
            
            # 3. 价格因子：价格在布林带中上轨附近
            price_signal = (current_price > self.bollinger.mid[0] and
                           current_price < self.bollinger.top[0])
            
            # 4. 成交量因子：成交量放大
            volume_signal = self.data.volume[0] > self.volume_sma[0] * 1.2
            
            # 综合评分（至少满足3个条件）
            signal_count = sum([trend_signal, momentum_signal, price_signal, volume_signal])
            
            if signal_count >= 3:
                size = int(self.broker.get_cash() * 0.95 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    self.buy_date = len(self)
                    logger.info(f"XGBoost多因子买入: 价格={current_price:.2f}, 信号数={signal_count}")
        
        # 如果有持仓
        else:
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            holding_days = len(self) - self.buy_date
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. 止盈
            if profit_ratio >= self.params.take_profit:
                should_sell = True
                sell_reason = f"止盈({profit_ratio*100:.2f}%)"
            
            # 2. 止损
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 3. 持仓过久
            elif holding_days >= self.params.max_holding_days:
                should_sell = True
                sell_reason = f"持仓过久({holding_days}天)"
            
            # 4. 技术面走弱（趋势反转 + MACD死叉）
            elif (self.sma5[0] < self.sma10[0] and 
                  self.macd.macd[0] < self.macd.signal[0]):
                should_sell = True
                sell_reason = "技术面走弱"
            
            # 5. 价格跌破布林带下轨
            elif current_price < self.bollinger.bot[0]:
                should_sell = True
                sell_reason = "跌破布林带下轨"
            
            if should_sell:
                self.close()
                logger.info(f"XGBoost卖出: 价格={current_price:.2f}, 原因={sell_reason}")
                self.buy_price = None
                self.buy_date = None
    
    def _extract_features(self):
        """提取特征向量（供模型预测使用）"""
        features = [
            # 价格特征
            self.sma5[0] / self.data.close[0],
            self.sma10[0] / self.data.close[0],
            self.sma20[0] / self.data.close[0],
            
            # 动量特征
            self.rsi[0] / 100,
            self.macd.macd[0],
            self.macd.signal[0],
            self.roc[0] / 100,
            
            # 波动率特征
            self.atr[0] / self.data.close[0],
            (self.bollinger.top[0] - self.bollinger.bot[0]) / self.data.close[0],
            
            # 成交量特征
            self.data.volume[0] / self.volume_sma[0],
        ]
        
        return np.array(features).reshape(1, -1)
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"XGBoost买入成交: 价格={order.executed.price:.2f}")
            elif order.issell():
                logger.info(f"XGBoost卖出成交: 价格={order.executed.price:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"XGBoost订单失败: {order.status}")
