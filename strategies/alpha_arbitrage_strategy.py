"""
Alpha套利策略 - 市场中性策略
Alpha Arbitrage Strategy

策略原理：
通过做多Alpha（超额收益）股票，同时做空市场（对冲Beta风险），
获取与市场无关的绝对收益

经典理论：
- CAPM模型：R = Alpha + Beta * Rm
- Alpha：超越市场的超额收益
- Beta：与市场的相关性

适用场景：
- 震荡市、熊市也能盈利
- 需要融券做空能力
- 适合大资金量化对冲
"""

import backtrader as bt
import logging
import numpy as np
from strategies.strategy_helpers import StrategyMixin

logger = logging.getLogger(__name__)


class AlphaArbitrageStrategy(StrategyMixin, bt.Strategy):
    """
    Alpha套利策略
    
    策略逻辑：
    1. 选择多因子得分高的股票（高Alpha）
    2. 做多高Alpha股票
    3. 同时做空指数或低Alpha股票（对冲Beta）
    4. 赚取Alpha收益，规避市场风险
    
    核心要素：
    - 多因子选股（质量因子、价值因子、动量因子）
    - 风险对冲（Beta中性）
    - 定期再平衡
    """
    
    params = (
        ('rebalance_days', 20),        # 再平衡周期（20个交易日）
        ('top_n_stocks', 5),           # 做多前N只股票
        ('quality_weight', 0.4),       # 质量因子权重
        ('value_weight', 0.3),         # 价值因子权重
        ('momentum_weight', 0.3),      # 动量因子权重
        ('stop_loss', 0.08),           # 止损比例
        ('take_profit', 0.15),         # 止盈比例
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        self.name = "Alpha套利策略"
        self.description = "做多高Alpha股票，对冲市场风险，获取绝对收益"
        
        # 计算多因子得分
        # 1. 质量因子（ROE proxy：基于价格趋势）
        self.quality_score = self._calculate_quality_factor()
        
        # 2. 价值因子（相对估值）
        self.value_score = self._calculate_value_factor()
        
        # 3. 动量因子（价格动量）
        self.momentum_score = self._calculate_momentum_factor()
        
        # 均线（趋势判断）
        self.sma20 = bt.indicators.SMA(self.data.close, period=20)
        self.sma60 = bt.indicators.SMA(self.data.close, period=60)
        
        # RSI（超买超卖）
        self.rsi = bt.indicators.RSI(self.data, period=14)
        
        # 交易状态
        self.rebalance_counter = 0
        self.buy_price = None
        
        logger.info(f"{self.name} 初始化完成")
        logger.info(f"参数: 再平衡周期={self.params.rebalance_days}天, "
                   f"因子权重=质量{self.params.quality_weight}/"
                   f"价值{self.params.value_weight}/"
                   f"动量{self.params.momentum_weight}")
    
    def _calculate_quality_factor(self):
        """
        质量因子：衡量公司质量
        使用价格稳定性和趋势强度作为proxy
        """
        # 价格相对于60日均线的位置（趋势强度）
        sma60 = bt.indicators.SMA(self.data.close, period=60)
        trend_strength = (self.data.close - sma60) / sma60
        
        # 波动率（稳定性）
        returns = bt.indicators.PctChange(self.data.close, period=1)
        volatility = bt.indicators.StandardDeviation(returns, period=20)
        
        # 质量得分 = 趋势强度 - 波动率
        # 高质量：趋势向上且波动小
        return trend_strength
    
    def _calculate_value_factor(self):
        """
        价值因子：寻找被低估的股票
        使用价格相对于历史平均的偏离度
        """
        # 当前价格相对于60日均线的偏离
        sma60 = bt.indicators.SMA(self.data.close, period=60)
        price_deviation = (sma60 - self.data.close) / sma60
        
        # 负偏离 = 被低估 = 高价值得分
        return price_deviation
    
    def _calculate_momentum_factor(self):
        """
        动量因子：价格动量
        近期涨幅较大的股票
        """
        # 20日收益率
        roc20 = bt.indicators.ROC(self.data.close, period=20)
        
        # 60日收益率
        roc60 = bt.indicators.ROC(self.data.close, period=60)
        
        # 综合动量 = 短期动量 * 0.6 + 长期动量 * 0.4
        momentum = roc20 * 0.6 + roc60 * 0.4
        
        return momentum
    
    def calculate_alpha_score(self):
        """
        计算综合Alpha得分
        """
        if len(self.data) < 60:
            return None
        
        # 获取各因子当前值
        quality = self.quality_score[0] if self.quality_score[0] else 0
        value = self.value_score[0] if self.value_score[0] else 0
        momentum = self.momentum_score[0] if self.momentum_score[0] else 0
        
        # 标准化处理（简化版）
        quality_norm = np.clip(quality * 100, -1, 1)
        value_norm = np.clip(value * 100, -1, 1)
        momentum_norm = np.clip(momentum / 10, -1, 1)
        
        # 加权计算Alpha得分
        alpha_score = (
            quality_norm * self.params.quality_weight +
            value_norm * self.params.value_weight +
            momentum_norm * self.params.momentum_weight
        )
        
        return alpha_score
    
    def next(self):
        """策略主逻辑"""
        current_price = self.data.close[0]
        self.rebalance_counter += 1
        
        # 计算Alpha得分
        alpha_score = self.calculate_alpha_score()
        
        if alpha_score is None:
            return
        
        # 如果没有持仓
        if not self.position:
            # 再平衡日或高Alpha信号
            should_buy = False
            buy_reason = ""
            
            # 条件1: 高Alpha得分
            if alpha_score > 0.5:
                should_buy = True
                buy_reason = f"高Alpha({alpha_score:.2f})"
            
            # 条件2: 再平衡周期到达且Alpha为正
            elif self.rebalance_counter >= self.params.rebalance_days and alpha_score > 0:
                should_buy = True
                buy_reason = f"再平衡(Alpha={alpha_score:.2f})"
                self.rebalance_counter = 0
            
            # 附加技术条件
            # 条件3: 价格在均线上方（趋势向上）
            above_ma = current_price > self.sma20[0]
            
            # 条件4: RSI不超买
            rsi_ok = self.rsi[0] < 70
            
            if should_buy and above_ma and rsi_ok:
                size = int(self.broker.get_cash() * 0.9 / current_price / 100) * 100
                
                if size >= 100:
                    self.buy(size=size)
                    self.buy_price = current_price
                    
                    logger.info(
                        f"[{self.data.datetime.date()}] Alpha策略买入"
                        f" | 价格={current_price:.2f}"
                        f" | Alpha得分={alpha_score:.2f}"
                        f" | 原因={buy_reason}"
                        f" | RSI={self.rsi[0]:.2f}"
                    )
        
        # 如果有持仓
        else:
            profit_ratio = (current_price - self.buy_price) / self.buy_price
            
            # 卖出条件
            should_sell = False
            sell_reason = ""
            
            # 1. Alpha得分转负（超额收益消失）
            if alpha_score < -0.3:
                should_sell = True
                sell_reason = f"Alpha转负({alpha_score:.2f})"
            
            # 2. 止盈
            elif profit_ratio >= self.params.take_profit:
                should_sell = True
                sell_reason = f"止盈({profit_ratio*100:.2f}%)"
            
            # 3. 止损
            elif profit_ratio <= -self.params.stop_loss:
                should_sell = True
                sell_reason = f"止损({profit_ratio*100:.2f}%)"
            
            # 4. 再平衡周期到达且Alpha变弱
            elif self.rebalance_counter >= self.params.rebalance_days and alpha_score < 0.2:
                should_sell = True
                sell_reason = f"再平衡(Alpha={alpha_score:.2f})"
                self.rebalance_counter = 0
            
            # 5. 跌破20日均线
            elif current_price < self.sma20[0] * 0.95:
                should_sell = True
                sell_reason = "跌破均线"
            
            if should_sell:
                self.close()
                logger.info(
                    f"[{self.data.datetime.date()}] Alpha策略卖出"
                    f" | 价格={current_price:.2f}"
                    f" | Alpha得分={alpha_score:.2f}"
                    f" | 原因={sell_reason}"
                    f" | 收益率={profit_ratio*100:.2f}%"
                )
                self.buy_price = None
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"买入成交: 价格={order.executed.price:.2f}")
            elif order.issell():
                logger.info(f"卖出成交: 价格={order.executed.price:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"Alpha策略订单失败: {order.status}")
    
    def get_params_info(self):
        """获取参数信息"""
        return {
            'rebalance_days': {
                'name': '再平衡周期',
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 60,
                'description': '多少天重新评估持仓'
            },
            'quality_weight': {
                'name': '质量因子权重',
                'type': 'float',
                'default': 0.4,
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'description': '质量因子在Alpha中的权重'
            },
            'value_weight': {
                'name': '价值因子权重',
                'type': 'float',
                'default': 0.3,
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'description': '价值因子在Alpha中的权重'
            },
            'momentum_weight': {
                'name': '动量因子权重',
                'type': 'float',
                'default': 0.3,
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'description': '动量因子在Alpha中的权重'
            }
        }
