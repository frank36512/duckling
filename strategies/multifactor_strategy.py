"""
多因子策略 - 综合多个技术指标的量化选股策略
"""

import backtrader as bt
import logging
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class MultiFactorStrategy(StrategyMixin, bt.Strategy):
    """
    多因子策略
    
    策略原理：
    结合多个不同类型的技术指标，建立综合评分系统
    通过多维度分析提高交易决策的准确性
    
    因子分类：
    1. 趋势因子：MACD、均线
    2. 动量因子：RSI、ROC（变化率）
    3. 波动因子：布林带位置
    4. 成交量因子：成交量相对变化
    
    信号规则：
    - 计算每个因子的得分（-1 到 +1）
    - 综合得分 > 阈值：买入信号
    - 综合得分 < 阈值：卖出信号
    """
    
    # 策略参数
    params = (
        ('macd_fast', 12),         # MACD快线周期
        ('macd_slow', 26),         # MACD慢线周期
        ('macd_signal', 9),        # MACD信号线周期
        ('ma_period', 20),         # 均线周期
        ('rsi_period', 14),        # RSI周期
        ('roc_period', 10),        # ROC周期
        ('bb_period', 20),         # 布林带周期
        ('volume_period', 20),     # 成交量均线周期
        ('buy_threshold', 0.5),    # 买入得分阈值
        ('sell_threshold', -0.3),  # 卖出得分阈值
        ('stop_loss', 0.08),       # 止损比例（8%）
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 策略名称和描述
        self.name = "多因子策略"
        self.description = "综合多个技术指标的量化策略，多维度评分提高准确性"
        
        # 1. 趋势因子
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        self.ma = bt.indicators.SMA(self.data.close, period=self.params.ma_period)
        
        # 2. 动量因子
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.roc = bt.indicators.ROC(self.data.close, period=self.params.roc_period)
        
        # 3. 波动因子
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period
        )
        
        # 4. 成交量因子
        self.volume_ma = bt.indicators.SMA(
            self.data.volume,
            period=self.params.volume_period
        )
        
        # 记录买入价格
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成 - 买入阈值={self.params.buy_threshold}, "
                   f"卖出阈值={self.params.sell_threshold}")
    
    def calculate_factor_score(self):
        """
        计算综合因子得分
        每个因子返回 -1 到 +1 的得分
        """
        scores = []
        
        # 1. MACD因子（趋势）
        macd_score = 0
        if self.macd.macd[0] > self.macd.signal[0]:
            macd_score = min(1.0, (self.macd.macd[0] - self.macd.signal[0]) / abs(self.macd.signal[0]) * 2)
        else:
            macd_score = max(-1.0, (self.macd.macd[0] - self.macd.signal[0]) / abs(self.macd.signal[0]) * 2)
        scores.append(('MACD', macd_score, 1.0))  # 权重1.0
        
        # 2. 均线因子（趋势）
        ma_score = 0
        if self.data.close[0] > self.ma[0]:
            ma_score = min(1.0, (self.data.close[0] - self.ma[0]) / self.ma[0] * 10)
        else:
            ma_score = max(-1.0, (self.data.close[0] - self.ma[0]) / self.ma[0] * 10)
        scores.append(('MA', ma_score, 0.8))  # 权重0.8
        
        # 3. RSI因子（动量）
        rsi_score = 0
        if self.rsi[0] < 30:
            rsi_score = 1.0  # 超卖，看涨
        elif self.rsi[0] > 70:
            rsi_score = -1.0  # 超买，看跌
        else:
            rsi_score = (50 - self.rsi[0]) / 20  # 线性映射
        scores.append(('RSI', rsi_score, 0.9))  # 权重0.9
        
        # 4. ROC因子（动量）
        roc_score = 0
        if abs(self.roc[0]) > 0:
            roc_score = min(1.0, max(-1.0, self.roc[0] / 10))  # ROC归一化
        scores.append(('ROC', roc_score, 0.7))  # 权重0.7
        
        # 5. 布林带因子（波动）
        bb_score = 0
        bb_range = self.bb.top[0] - self.bb.bot[0]
        if bb_range > 0:
            bb_position = (self.data.close[0] - self.bb.bot[0]) / bb_range
            # 价格在下轨附近：看涨，上轨附近：看跌
            bb_score = 1.0 - 2 * bb_position  # 0->1, 0.5->0, 1->-1
        scores.append(('BB', bb_score, 0.6))  # 权重0.6
        
        # 6. 成交量因子
        volume_score = 0
        if self.volume_ma[0] > 0:
            volume_ratio = self.data.volume[0] / self.volume_ma[0]
            if volume_ratio > 1.5:  # 放量
                volume_score = 0.5 * (1 if macd_score > 0 else -1)  # 配合趋势方向
        scores.append(('Volume', volume_score, 0.5))  # 权重0.5
        
        # 计算加权平均得分
        total_weight = sum(weight for _, _, weight in scores)
        weighted_score = sum(score * weight for _, score, weight in scores) / total_weight
        
        return weighted_score, scores
    
    def next(self):
        """策略逻辑"""
        current_price = self.data.close[0]
        
        # 计算综合因子得分
        total_score, factor_scores = self.calculate_factor_score()
        
        # 如果没有持仓
        if not self.position:
            # 综合得分超过买入阈值
            if total_score > self.params.buy_threshold:
                size = self.calculate_position_size()
                self.buy(size=size)
                self.buy_price = current_price
                
                # 详细记录各因子得分
                factor_details = ', '.join([f"{name}: {score:.2f}" for name, score, _ in factor_scores])
                logger.info(f"[{self.data.datetime.date()}] 多因子买入信号 - 买入 {size} 股 @ {current_price:.2f}")
                logger.info(f"    综合得分: {total_score:.2f} | {factor_details}")
        
        # 如果持有仓位
        else:
            # 综合得分低于卖出阈值
            if total_score < self.params.sell_threshold:
                self.sell(size=self.position.size)
                profit_pct = (current_price / self.buy_price - 1) * 100 if self.buy_price else 0
                
                factor_details = ', '.join([f"{name}: {score:.2f}" for name, score, _ in factor_scores])
                logger.info(f"[{self.data.datetime.date()}] 多因子卖出信号 - 卖出 {self.position.size} 股 @ {current_price:.2f}")
                logger.info(f"    综合得分: {total_score:.2f} | 盈亏: {profit_pct:.2f}% | {factor_details}")
            
            # 止损检查
            elif self.buy_price and current_price < self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                loss_pct = (current_price / self.buy_price - 1) * 100
                logger.info(f"[{self.data.datetime.date()}] 触发止损 - 卖出 {self.position.size} 股 @ {current_price:.2f} "
                          f"(亏损: {loss_pct:.2f}%)")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'buy_threshold': {
                'name': '买入阈值',
                'type': 'float',
                'default': 0.5,
                'min': 0.0,
                'max': 1.0,
                'description': '综合得分超过此值时买入'
            },
            'sell_threshold': {
                'name': '卖出阈值',
                'type': 'float',
                'default': -0.3,
                'min': -1.0,
                'max': 0.0,
                'description': '综合得分低于此值时卖出'
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
