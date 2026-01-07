"""
风控规则模块
实现交易风险控制
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskController:
    """风控控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化风控控制器
        :param config: 风控配置
        """
        self.config = config
        
        # 风控参数
        self.max_daily_trades = config.get('max_daily_trades', 10)
        self.max_loss_threshold = config.get('max_loss_threshold', 0.1)
        self.price_deviation_limit = config.get('price_deviation_limit', 0.03)
        self.position_limit = config.get('position_limit', 0.3)
        
        # 运行时状态
        self.daily_trades_count = 0
        self.current_date = None
        self.total_loss = 0.0
        self.is_trading_suspended = False
        
        logger.info(f"风控控制器初始化完成，参数: {self.config}")
    
    def reset_daily_stats(self):
        """重置每日统计"""
        self.daily_trades_count = 0
        self.current_date = datetime.now().date()
        logger.info("每日风控统计已重置")
    
    def check_daily_trade_limit(self) -> tuple[bool, str]:
        """
        检查每日交易次数限制
        :return: (是否通过, 原因)
        """
        # 检查日期是否变化
        today = datetime.now().date()
        if self.current_date != today:
            self.reset_daily_stats()
        
        if self.daily_trades_count >= self.max_daily_trades:
            reason = f"已达到每日交易次数上限: {self.max_daily_trades}"
            logger.warning(reason)
            return False, reason
        
        return True, ""
    
    def check_position_limit(self, position_value: float, 
                            total_value: float) -> tuple[bool, str]:
        """
        检查单只股票持仓限制
        :param position_value: 持仓价值
        :param total_value: 总资产
        :return: (是否通过, 原因)
        """
        if total_value <= 0:
            return False, "总资产必须大于0"
        
        position_ratio = position_value / total_value
        
        if position_ratio > self.position_limit:
            reason = f"持仓比例 {position_ratio:.2%} 超过限制 {self.position_limit:.2%}"
            logger.warning(reason)
            return False, reason
        
        return True, ""
    
    def check_loss_threshold(self, current_value: float, 
                           initial_value: float) -> tuple[bool, str]:
        """
        检查总亏损阈值
        :param current_value: 当前资产
        :param initial_value: 初始资产
        :return: (是否通过, 原因)
        """
        loss_ratio = (initial_value - current_value) / initial_value
        
        if loss_ratio >= self.max_loss_threshold:
            reason = f"总亏损 {loss_ratio:.2%} 达到阈值 {self.max_loss_threshold:.2%}，暂停交易"
            logger.error(reason)
            self.is_trading_suspended = True
            return False, reason
        
        return True, ""
    
    def check_price_deviation(self, order_price: float, 
                             market_price: float) -> tuple[bool, str]:
        """
        检查价格偏离
        :param order_price: 委托价格
        :param market_price: 市场价格
        :return: (是否通过, 原因)
        """
        if market_price <= 0:
            return False, "市场价格必须大于0"
        
        deviation = abs(order_price - market_price) / market_price
        
        if deviation > self.price_deviation_limit:
            reason = (f"价格偏离 {deviation:.2%} 超过限制 "
                     f"{self.price_deviation_limit:.2%}")
            logger.warning(reason)
            return False, reason
        
        return True, ""
    
    def validate_order(self, order: Dict[str, Any], 
                      account: Dict[str, Any]) -> tuple[bool, str]:
        """
        综合校验订单
        :param order: 订单信息 {'price': 价格, 'quantity': 数量, 'type': 'buy'/'sell'}
        :param account: 账户信息 {'total_value': 总资产, 'initial_value': 初始资产, 
                                'available_cash': 可用资金}
        :return: (是否通过, 原因)
        """
        # 检查是否暂停交易
        if self.is_trading_suspended:
            return False, "交易已暂停"
        
        # 检查每日交易次数
        passed, reason = self.check_daily_trade_limit()
        if not passed:
            return False, reason
        
        # 检查总亏损阈值
        passed, reason = self.check_loss_threshold(
            account['total_value'],
            account['initial_value']
        )
        if not passed:
            return False, reason
        
        # 买入订单额外检查
        if order['type'] == 'buy':
            order_value = order['price'] * order['quantity']
            
            # 检查可用资金
            if order_value > account['available_cash']:
                return False, f"可用资金不足: 需要{order_value:.2f}, 可用{account['available_cash']:.2f}"
            
            # 检查持仓限制
            passed, reason = self.check_position_limit(
                order_value,
                account['total_value']
            )
            if not passed:
                return False, reason
        
        return True, ""
    
    def record_trade(self):
        """记录交易"""
        self.daily_trades_count += 1
        logger.info(f"记录交易，今日交易次数: {self.daily_trades_count}")
    
    def suspend_trading(self):
        """暂停交易"""
        self.is_trading_suspended = True
        logger.warning("交易已暂停")
    
    def resume_trading(self):
        """恢复交易"""
        self.is_trading_suspended = False
        logger.info("交易已恢复")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取风控状态
        :return: 状态字典
        """
        return {
            'is_suspended': self.is_trading_suspended,
            'daily_trades': self.daily_trades_count,
            'max_daily_trades': self.max_daily_trades,
            'current_date': str(self.current_date)
        }
