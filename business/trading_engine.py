"""
实盘交易模块
支持模拟交易和真实交易（通过券商接口）
包含完整的风险控制系统
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """订单方向"""
    BUY = "买入"
    SELL = "卖出"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待成交"
    FILLED = "已成交"
    PARTIALLY_FILLED = "部分成交"
    CANCELLED = "已撤销"
    REJECTED = "已拒绝"


class OrderType(Enum):
    """订单类型"""
    MARKET = "市价单"
    LIMIT = "限价单"


class Order:
    """订单类"""
    
    def __init__(
        self,
        order_id: str,
        stock_code: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: int,
        price: Optional[float] = None
    ):
        self.order_id = order_id
        self.stock_code = stock_code
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.filled_quantity = 0
        self.average_price = 0.0
        self.status = OrderStatus.PENDING
        self.create_time = datetime.now()
        self.update_time = datetime.now()
        self.message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'status': self.status.value,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': self.message
        }


class Position:
    """持仓类"""
    
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.quantity = 0
        self.available_quantity = 0
        self.average_cost = 0.0
        self.market_value = 0.0
        self.profit_loss = 0.0
        self.profit_loss_ratio = 0.0
    
    def update_market_value(self, current_price: float):
        """更新市值"""
        self.market_value = self.quantity * current_price
        
        if self.quantity > 0 and self.average_cost > 0:
            self.profit_loss = self.market_value - (self.quantity * self.average_cost)
            self.profit_loss_ratio = self.profit_loss / (self.quantity * self.average_cost) * 100
        else:
            self.profit_loss = 0.0
            self.profit_loss_ratio = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'quantity': self.quantity,
            'available_quantity': self.available_quantity,
            'average_cost': self.average_cost,
            'market_value': self.market_value,
            'profit_loss': self.profit_loss,
            'profit_loss_ratio': self.profit_loss_ratio
        }


class BrokerInterface(ABC):
    """券商接口基类"""
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """获取持仓列表"""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> bool:
        """下单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass
    
    @abstractmethod
    def get_orders(self) -> List[Order]:
        """获取订单列表"""
        pass


class SimulatedBroker(BrokerInterface):
    """
    模拟券商
    用于模拟交易测试
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        初始化模拟券商
        :param initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trades = []
        
        # 费用配置
        self.commission_rate = 0.0003  # 佣金率
        self.stamp_duty_rate = 0.001   # 印花税率（仅卖出）
        
        logger.info(f"模拟券商初始化完成，初始资金: {initial_capital}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        # 计算总资产
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        total_assets = self.cash + total_market_value
        
        # 计算收益
        total_profit = total_assets - self.initial_capital
        total_profit_ratio = (total_profit / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        return {
            'cash': self.cash,
            'market_value': total_market_value,
            'total_assets': total_assets,
            'initial_capital': self.initial_capital,
            'total_profit': total_profit,
            'total_profit_ratio': total_profit_ratio,
            'positions_count': len(self.positions)
        }
    
    def get_positions(self) -> List[Position]:
        """获取持仓列表"""
        return list(self.positions.values())
    
    def place_order(self, order: Order) -> bool:
        """
        下单
        :param order: 订单对象
        :return: 是否成功
        """
        try:
            # 验证订单
            if order.quantity <= 0:
                order.status = OrderStatus.REJECTED
                order.message = "数量必须大于0"
                logger.error(f"订单被拒绝: {order.message}")
                return False
            
            # 市价单立即成交（使用当前价格）
            if order.order_type == OrderType.MARKET:
                if order.price is None:
                    order.status = OrderStatus.REJECTED
                    order.message = "市价单必须提供当前价格"
                    logger.error(f"订单被拒绝: {order.message}")
                    return False
                
                return self._execute_order(order, order.price)
            
            # 限价单（简化处理：立即按限价成交）
            elif order.order_type == OrderType.LIMIT:
                if order.price is None or order.price <= 0:
                    order.status = OrderStatus.REJECTED
                    order.message = "限价单必须提供有效价格"
                    logger.error(f"订单被拒绝: {order.message}")
                    return False
                
                return self._execute_order(order, order.price)
            
            return False
        
        except Exception as e:
            logger.error(f"下单失败: {e}", exc_info=True)
            order.status = OrderStatus.REJECTED
            order.message = str(e)
            return False
    
    def _execute_order(self, order: Order, execution_price: float) -> bool:
        """
        执行订单
        :param order: 订单对象
        :param execution_price: 成交价格
        :return: 是否成功
        """
        # 计算费用
        trade_amount = order.quantity * execution_price
        commission = trade_amount * self.commission_rate
        stamp_duty = trade_amount * self.stamp_duty_rate if order.side == OrderSide.SELL else 0
        total_fee = commission + stamp_duty
        
        if order.side == OrderSide.BUY:
            # 买入
            total_cost = trade_amount + total_fee
            
            # 检查资金是否足够
            if self.cash < total_cost:
                order.status = OrderStatus.REJECTED
                order.message = f"资金不足: 需要{total_cost:.2f}, 可用{self.cash:.2f}"
                logger.error(f"订单被拒绝: {order.message}")
                return False
            
            # 扣除资金
            self.cash -= total_cost
            
            # 更新持仓
            if order.stock_code not in self.positions:
                self.positions[order.stock_code] = Position(order.stock_code)
            
            position = self.positions[order.stock_code]
            
            # 计算新的平均成本
            total_quantity = position.quantity + order.quantity
            total_cost_value = (position.quantity * position.average_cost) + total_cost
            position.average_cost = total_cost_value / total_quantity if total_quantity > 0 else 0
            
            position.quantity = total_quantity
            position.available_quantity = total_quantity  # 简化处理：T+0
            
            logger.info(f"买入成交: {order.stock_code} x {order.quantity} @ {execution_price:.2f}, 费用: {total_fee:.2f}")
        
        elif order.side == OrderSide.SELL:
            # 卖出
            # 检查持仓是否足够
            if order.stock_code not in self.positions:
                order.status = OrderStatus.REJECTED
                order.message = f"无持仓"
                logger.error(f"订单被拒绝: {order.message}")
                return False
            
            position = self.positions[order.stock_code]
            
            if position.available_quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                order.message = f"可用数量不足: 需要{order.quantity}, 可用{position.available_quantity}"
                logger.error(f"订单被拒绝: {order.message}")
                return False
            
            # 增加资金
            net_amount = trade_amount - total_fee
            self.cash += net_amount
            
            # 更新持仓
            position.quantity -= order.quantity
            position.available_quantity -= order.quantity
            
            # 如果持仓清空，删除持仓记录
            if position.quantity == 0:
                del self.positions[order.stock_code]
            
            logger.info(f"卖出成交: {order.stock_code} x {order.quantity} @ {execution_price:.2f}, 费用: {total_fee:.2f}")
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = execution_price
        order.update_time = datetime.now()
        order.message = f"成交价: {execution_price:.2f}, 费用: {total_fee:.2f}"
        
        # 保存订单
        self.orders[order.order_id] = order
        
        # 记录交易
        trade_record = {
            'order_id': order.order_id,
            'stock_code': order.stock_code,
            'side': order.side.value,
            'quantity': order.quantity,
            'price': execution_price,
            'amount': trade_amount,
            'commission': commission,
            'stamp_duty': stamp_duty,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.trades.append(trade_record)
        
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if order_id not in self.orders:
            logger.error(f"订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.PENDING:
            logger.error(f"订单状态不允许撤销: {order.status}")
            return False
        
        order.status = OrderStatus.CANCELLED
        order.update_time = datetime.now()
        order.message = "用户撤销"
        
        logger.info(f"订单已撤销: {order_id}")
        return True
    
    def get_orders(self) -> List[Order]:
        """获取订单列表"""
        return list(self.orders.values())
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """获取成交记录"""
        return self.trades


class RiskController:
    """
    风险控制器
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化风控系统
        :param config: 风控配置
        """
        self.config = config
        
        # 风控参数
        self.max_position_ratio = config.get('max_position_ratio', 0.3)  # 单只股票最大持仓比例
        self.max_loss_ratio = config.get('max_loss_ratio', 0.1)  # 单笔最大亏损比例
        self.max_daily_loss = config.get('max_daily_loss', 0.05)  # 单日最大亏损
        self.max_drawdown = config.get('max_drawdown', 0.2)  # 最大回撤
        
        # 止损止盈
        self.stop_loss_ratio = config.get('stop_loss_ratio', 0.05)  # 止损比例
        self.take_profit_ratio = config.get('take_profit_ratio', 0.10)  # 止盈比例
        
        # 交易限制
        self.min_trade_amount = config.get('min_trade_amount', 1000)  # 最小交易金额
        self.max_trade_amount = config.get('max_trade_amount', 50000)  # 最大交易金额
        
        # 统计数据
        self.daily_profit = 0.0
        self.peak_value = 0.0
        
        logger.info("风控系统初始化完成")
    
    def check_order(self, order: Order, account_info: Dict[str, Any], positions: List[Position]) -> tuple[bool, str]:
        """
        检查订单是否符合风控要求
        :param order: 订单
        :param account_info: 账户信息
        :param positions: 持仓列表
        :return: (是否通过, 原因)
        """
        try:
            trade_amount = order.quantity * order.price if order.price else 0
            
            # 1. 检查交易金额
            if trade_amount < self.min_trade_amount:
                return False, f"交易金额过小: {trade_amount:.2f} < {self.min_trade_amount}"
            
            if trade_amount > self.max_trade_amount:
                return False, f"交易金额过大: {trade_amount:.2f} > {self.max_trade_amount}"
            
            # 2. 买入时检查仓位
            if order.side == OrderSide.BUY:
                total_assets = account_info['total_assets']
                position_value = trade_amount
                position_ratio = position_value / total_assets if total_assets > 0 else 0
                
                if position_ratio > self.max_position_ratio:
                    return False, f"单只股票仓位过大: {position_ratio:.1%} > {self.max_position_ratio:.1%}"
            
            # 3. 卖出时检查止损止盈
            if order.side == OrderSide.SELL:
                position = next((p for p in positions if p.stock_code == order.stock_code), None)
                if position:
                    # 检查是否触发止损
                    if position.profit_loss_ratio < -self.stop_loss_ratio * 100:
                        logger.warning(f"触发止损: {position.profit_loss_ratio:.2f}%")
                    
                    # 检查是否触发止盈
                    if position.profit_loss_ratio > self.take_profit_ratio * 100:
                        logger.info(f"触发止盈: {position.profit_loss_ratio:.2f}%")
            
            # 4. 检查单日亏损
            if self.daily_profit < -account_info['initial_capital'] * self.max_daily_loss:
                return False, f"触发单日最大亏损限制: {self.daily_profit:.2f}"
            
            # 5. 检查最大回撤
            current_value = account_info['total_assets']
            if self.peak_value < current_value:
                self.peak_value = current_value
            
            if self.peak_value > 0:
                drawdown = (self.peak_value - current_value) / self.peak_value
                if drawdown > self.max_drawdown:
                    return False, f"触发最大回撤限制: {drawdown:.1%} > {self.max_drawdown:.1%}"
            
            return True, "风控检查通过"
        
        except Exception as e:
            logger.error(f"风控检查失败: {e}", exc_info=True)
            return False, f"风控检查异常: {e}"
    
    def update_daily_profit(self, profit: float):
        """更新当日收益"""
        self.daily_profit = profit
    
    def reset_daily_statistics(self):
        """重置每日统计"""
        self.daily_profit = 0.0


class TradingEngine:
    """
    交易引擎
    整合券商接口和风控系统
    """
    
    def __init__(self, config: Dict[str, Any], broker: Optional[BrokerInterface] = None):
        """
        初始化交易引擎
        :param config: 配置字典
        :param broker: 券商接口（默认使用模拟券商）
        """
        self.config = config
        
        # 使用模拟券商或真实券商
        if broker is None:
            initial_capital = config.get('initial_capital', 100000)
            self.broker = SimulatedBroker(initial_capital)
        else:
            self.broker = broker
        
        # 风控系统
        self.risk_controller = RiskController(config)
        
        # 订单ID生成器
        self.order_counter = 0
        
        logger.info("交易引擎初始化完成")
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return self.broker.get_account_info()
    
    def get_positions(self) -> List[Position]:
        """获取持仓列表"""
        return self.broker.get_positions()
    
    def get_orders(self) -> List[Order]:
        """获取订单列表"""
        return self.broker.get_orders()
    
    def buy(self, stock_code: str, quantity: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> tuple[bool, str, Optional[Order]]:
        """
        买入
        :param stock_code: 股票代码
        :param quantity: 数量
        :param price: 价格（市价单为当前价，限价单为限价）
        :param order_type: 订单类型
        :return: (是否成功, 消息, 订单对象)
        """
        try:
            # 生成订单ID
            self.order_counter += 1
            order_id = f"BUY_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.order_counter}"
            
            # 创建订单
            order = Order(
                order_id=order_id,
                stock_code=stock_code,
                side=OrderSide.BUY,
                order_type=order_type,
                quantity=quantity,
                price=price
            )
            
            # 风控检查
            account_info = self.get_account_info()
            positions = self.get_positions()
            
            passed, reason = self.risk_controller.check_order(order, account_info, positions)
            if not passed:
                logger.warning(f"风控拒绝: {reason}")
                return False, f"风控拒绝: {reason}", order
            
            # 下单
            success = self.broker.place_order(order)
            
            if success:
                logger.info(f"买入成功: {stock_code} x {quantity} @ {price}")
                return True, "买入成功", order
            else:
                logger.error(f"买入失败: {order.message}")
                return False, order.message, order
        
        except Exception as e:
            logger.error(f"买入异常: {e}", exc_info=True)
            return False, str(e), None
    
    def sell(self, stock_code: str, quantity: int, price: Optional[float] = None, order_type: OrderType = OrderType.MARKET) -> tuple[bool, str, Optional[Order]]:
        """
        卖出
        :param stock_code: 股票代码
        :param quantity: 数量
        :param price: 价格
        :param order_type: 订单类型
        :return: (是否成功, 消息, 订单对象)
        """
        try:
            # 生成订单ID
            self.order_counter += 1
            order_id = f"SELL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.order_counter}"
            
            # 创建订单
            order = Order(
                order_id=order_id,
                stock_code=stock_code,
                side=OrderSide.SELL,
                order_type=order_type,
                quantity=quantity,
                price=price
            )
            
            # 风控检查
            account_info = self.get_account_info()
            positions = self.get_positions()
            
            passed, reason = self.risk_controller.check_order(order, account_info, positions)
            if not passed:
                logger.warning(f"风控拒绝: {reason}")
                return False, f"风控拒绝: {reason}", order
            
            # 下单
            success = self.broker.place_order(order)
            
            if success:
                logger.info(f"卖出成功: {stock_code} x {quantity} @ {price}")
                return True, "卖出成功", order
            else:
                logger.error(f"卖出失败: {order.message}")
                return False, order.message, order
        
        except Exception as e:
            logger.error(f"卖出异常: {e}", exc_info=True)
            return False, str(e), None
    
    def cancel_order(self, order_id: str) -> tuple[bool, str]:
        """
        撤单
        :param order_id: 订单ID
        :return: (是否成功, 消息)
        """
        success = self.broker.cancel_order(order_id)
        if success:
            return True, "撤单成功"
        else:
            return False, "撤单失败"
    
    def update_positions_market_value(self, prices: Dict[str, float]):
        """
        更新持仓市值
        :param prices: 股票代码->当前价格
        """
        positions = self.get_positions()
        for position in positions:
            if position.stock_code in prices:
                position.update_market_value(prices[position.stock_code])
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """获取成交记录"""
        if isinstance(self.broker, SimulatedBroker):
            return self.broker.get_trades()
        return []
