"""
自动交易引擎
根据策略信号自动执行买卖操作
包含完整的风险控制和监控机制
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Callable
from enum import Enum
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import backtrader as bt
from business.trading_engine import TradingEngine, OrderSide, OrderType
from business.data_manager import DataManager
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)


class AutoTradingStatus(Enum):
    """自动交易状态"""
    STOPPED = "已停止"
    RUNNING = "运行中"
    PAUSED = "已暂停"
    ERROR = "错误"


class TradingSignal:
    """交易信号"""
    
    def __init__(
        self,
        stock_code: str,
        strategy_name: str,
        signal_type: str,  # 'BUY' or 'SELL'
        price: float,
        quantity: int,
        timestamp: datetime,
        reason: str = ""
    ):
        self.stock_code = stock_code
        self.strategy_name = strategy_name
        self.signal_type = signal_type
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp
        self.reason = reason
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'strategy_name': self.strategy_name,
            'signal_type': self.signal_type,
            'price': self.price,
            'quantity': self.quantity,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'reason': self.reason
        }


class StrategyMonitor:
    """策略监控器"""
    
    def __init__(self, strategy_name: str, stock_code: str, params: Dict = None):
        self.strategy_name = strategy_name
        self.stock_code = stock_code
        self.params = params or {}
        self.last_signal = None
        self.signal_count = 0
        self.is_active = True
    
    def check_signal(self, data) -> Optional[TradingSignal]:
        """检查策略信号（简化版本）"""
        # 这里需要实际运行策略来获取信号
        # 实际实现会更复杂，需要保持策略状态
        return None


class AutoTradingEngine:
    """自动交易引擎"""
    
    def __init__(
        self,
        trading_engine: TradingEngine,
        data_manager: DataManager,
        config: Dict = None
    ):
        """
        初始化自动交易引擎
        
        :param trading_engine: 交易引擎
        :param data_manager: 数据管理器
        :param config: 配置字典
        """
        self.trading_engine = trading_engine
        self.data_manager = data_manager
        self.config = config or {}
        
        # 状态管理
        self.status = AutoTradingStatus.STOPPED
        self.strategy_monitors: Dict[str, StrategyMonitor] = {}
        
        # 交易设置
        self.enabled_stocks: List[str] = []  # 允许交易的股票列表
        self.max_position_per_stock = 0.2  # 单只股票最大仓位比例
        self.max_total_position = 0.8  # 总仓位上限
        self.min_trade_amount = 1000  # 最小交易金额
        
        # 时间控制
        self.trading_start_time = time(9, 30)  # 交易开始时间
        self.trading_end_time = time(15, 0)   # 交易结束时间
        
        # 风险控制
        self.daily_loss_limit = 0.05  # 单日亏损限制（5%）
        self.max_orders_per_day = 20  # 单日最大订单数
        self.order_count_today = 0
        self.initial_balance = 0.0
        
        # 信号历史
        self.signal_history: List[TradingSignal] = []
        self.max_signal_history = 1000
        
        logger.info("自动交易引擎初始化完成")
    
    def add_strategy(
        self,
        strategy_name: str,
        stock_code: str,
        params: Dict = None
    ) -> bool:
        """
        添加策略监控
        
        :param strategy_name: 策略名称
        :param stock_code: 股票代码
        :param params: 策略参数
        :return: 是否成功
        """
        try:
            key = f"{strategy_name}_{stock_code}"
            monitor = StrategyMonitor(strategy_name, stock_code, params)
            self.strategy_monitors[key] = monitor
            
            if stock_code not in self.enabled_stocks:
                self.enabled_stocks.append(stock_code)
            
            logger.info(f"添加策略监控: {strategy_name} - {stock_code}")
            return True
            
        except Exception as e:
            logger.error(f"添加策略监控失败: {e}")
            return False
    
    def remove_strategy(self, strategy_name: str, stock_code: str) -> bool:
        """移除策略监控"""
        try:
            key = f"{strategy_name}_{stock_code}"
            if key in self.strategy_monitors:
                del self.strategy_monitors[key]
                logger.info(f"移除策略监控: {strategy_name} - {stock_code}")
                return True
            return False
        except Exception as e:
            logger.error(f"移除策略监控失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动自动交易"""
        try:
            if self.status == AutoTradingStatus.RUNNING:
                logger.warning("自动交易已在运行中")
                return False
            
            if not self.strategy_monitors:
                logger.warning("没有配置任何策略监控")
                return False
            
            # 记录初始资金
            account_info = self.trading_engine.get_account_info()
            self.initial_balance = account_info['total_assets']
            self.order_count_today = 0
            
            self.status = AutoTradingStatus.RUNNING
            logger.info("自动交易已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动自动交易失败: {e}")
            self.status = AutoTradingStatus.ERROR
            return False
    
    def stop(self) -> bool:
        """停止自动交易"""
        try:
            self.status = AutoTradingStatus.STOPPED
            logger.info("自动交易已停止")
            return True
        except Exception as e:
            logger.error(f"停止自动交易失败: {e}")
            return False
    
    def pause(self) -> bool:
        """暂停自动交易"""
        if self.status == AutoTradingStatus.RUNNING:
            self.status = AutoTradingStatus.PAUSED
            logger.info("自动交易已暂停")
            return True
        return False
    
    def resume(self) -> bool:
        """恢复自动交易"""
        if self.status == AutoTradingStatus.PAUSED:
            self.status = AutoTradingStatus.RUNNING
            logger.info("自动交易已恢复")
            return True
        return False
    
    def is_trading_time(self) -> bool:
        """检查是否在交易时间内"""
        now = datetime.now().time()
        return self.trading_start_time <= now <= self.trading_end_time
    
    def check_risk_limits(self) -> tuple[bool, str]:
        """
        检查风险限制
        
        :return: (是否通过, 失败原因)
        """
        # 检查单日订单数限制
        if self.order_count_today >= self.max_orders_per_day:
            return False, f"达到单日订单数限制 ({self.max_orders_per_day})"
        
        # 检查单日亏损限制
        account_info = self.trading_engine.get_account_info()
        current_balance = account_info['total_assets']
        daily_loss = (self.initial_balance - current_balance) / self.initial_balance
        
        if daily_loss > self.daily_loss_limit:
            return False, f"达到单日亏损限制 ({self.daily_loss_limit*100}%)"
        
        # 检查总仓位限制
        position_ratio = account_info['position_value'] / account_info['total_assets']
        if position_ratio >= self.max_total_position:
            return False, f"达到总仓位上限 ({self.max_total_position*100}%)"
        
        return True, ""
    
    def calculate_order_quantity(
        self,
        stock_code: str,
        price: float,
        signal_type: str
    ) -> int:
        """
        计算订单数量
        
        :param stock_code: 股票代码
        :param price: 价格
        :param signal_type: 信号类型
        :return: 数量（股）
        """
        account_info = self.trading_engine.get_account_info()
        available_cash = account_info['available_cash']
        
        if signal_type == 'BUY':
            # 买入：基于可用资金和仓位限制
            max_amount = available_cash * self.max_position_per_stock
            quantity = int(max_amount / price / 100) * 100  # 按手（100股）计算
            
            # 确保不低于最小交易金额
            if quantity * price < self.min_trade_amount:
                return 0
            
            return quantity
        
        elif signal_type == 'SELL':
            # 卖出：获取当前持仓
            positions = self.trading_engine.get_positions()
            for pos in positions:
                if pos['stock_code'] == stock_code:
                    return pos['available_quantity']
            return 0
        
        return 0
    
    def process_signal(self, signal: TradingSignal) -> bool:
        """
        处理交易信号
        
        :param signal: 交易信号
        :return: 是否成功执行
        """
        try:
            # 检查状态
            if self.status != AutoTradingStatus.RUNNING:
                logger.warning(f"自动交易未运行，忽略信号: {signal.signal_type} {signal.stock_code}")
                return False
            
            # 检查交易时间
            if not self.is_trading_time():
                logger.warning(f"不在交易时间内，忽略信号: {signal.signal_type} {signal.stock_code}")
                return False
            
            # 检查风险限制
            passed, reason = self.check_risk_limits()
            if not passed:
                logger.warning(f"风险控制拒绝信号: {reason}")
                return False
            
            # 计算订单数量
            quantity = self.calculate_order_quantity(
                signal.stock_code,
                signal.price,
                signal.signal_type
            )
            
            if quantity <= 0:
                logger.warning(f"订单数量为0，忽略信号: {signal.signal_type} {signal.stock_code}")
                return False
            
            # 执行交易
            if signal.signal_type == 'BUY':
                order = self.trading_engine.buy(
                    stock_code=signal.stock_code,
                    quantity=quantity,
                    price=signal.price,
                    order_type=OrderType.LIMIT
                )
            elif signal.signal_type == 'SELL':
                order = self.trading_engine.sell(
                    stock_code=signal.stock_code,
                    quantity=quantity,
                    price=signal.price,
                    order_type=OrderType.LIMIT
                )
            else:
                logger.warning(f"未知信号类型: {signal.signal_type}")
                return False
            
            if order:
                self.order_count_today += 1
                self.signal_history.append(signal)
                
                # 限制历史记录数量
                if len(self.signal_history) > self.max_signal_history:
                    self.signal_history = self.signal_history[-self.max_signal_history:]
                
                logger.info(
                    f"自动交易执行成功: {signal.signal_type} {signal.stock_code} "
                    f"{quantity}股 @ ¥{signal.price:.2f} (策略: {signal.strategy_name})"
                )
                return True
            else:
                logger.error(f"交易执行失败: {signal.signal_type} {signal.stock_code}")
                return False
        
        except Exception as e:
            logger.error(f"处理交易信号失败: {e}", exc_info=True)
            return False
    
    def get_status(self) -> Dict:
        """获取状态信息"""
        return {
            'status': self.status.value,
            'strategy_count': len(self.strategy_monitors),
            'enabled_stocks': self.enabled_stocks,
            'order_count_today': self.order_count_today,
            'signal_count': len(self.signal_history),
            'is_trading_time': self.is_trading_time()
        }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        buy_signals = sum(1 for s in self.signal_history if s.signal_type == 'BUY')
        sell_signals = sum(1 for s in self.signal_history if s.signal_type == 'SELL')
        
        return {
            'total_signals': len(self.signal_history),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'order_count_today': self.order_count_today,
            'active_strategies': len([m for m in self.strategy_monitors.values() if m.is_active])
        }


class AutoTradingThread(QThread):
    """自动交易线程"""
    
    signal_generated = pyqtSignal(object)  # 信号：生成交易信号
    order_executed = pyqtSignal(str, str, int, float)  # 信号：订单执行 (stock_code, side, quantity, price)
    error_occurred = pyqtSignal(str)  # 信号：发生错误
    status_updated = pyqtSignal(dict)  # 信号：状态更新
    
    def __init__(self, auto_trading_engine: AutoTradingEngine):
        super().__init__()
        self.engine = auto_trading_engine
        self.running = False
        self.check_interval = 60  # 检查间隔（秒）
    
    def run(self):
        """运行线程"""
        self.running = True
        logger.info("自动交易线程启动")
        
        while self.running:
            try:
                if self.engine.status == AutoTradingStatus.RUNNING:
                    # 定期发送状态更新
                    status = self.engine.get_status()
                    self.status_updated.emit(status)
                    
                    # TODO: 这里需要实际的策略信号检测逻辑
                    # 目前只是框架，实际使用时需要：
                    # 1. 获取实时数据
                    # 2. 运行策略计算
                    # 3. 生成交易信号
                    # 4. 执行交易
                
                # 休眠一段时间
                self.msleep(self.check_interval * 1000)
                
            except Exception as e:
                logger.error(f"自动交易线程错误: {e}", exc_info=True)
                self.error_occurred.emit(str(e))
    
    def stop(self):
        """停止线程"""
        self.running = False
        logger.info("自动交易线程停止")
