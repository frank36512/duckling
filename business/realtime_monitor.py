"""
实时监控模块
支持实时行情监控、策略信号监控和预警系统
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from threading import Thread, Event
from queue import Queue
import pandas as pd

from business.data_manager import DataManager
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)


class RealtimeDataSource:
    """
    实时数据源
    支持轮询模式获取实时行情
    """
    
    def __init__(self, data_manager: DataManager, interval: int = 3):
        """
        初始化实时数据源
        :param data_manager: 数据管理器
        :param interval: 更新间隔（秒）
        """
        self.data_manager = data_manager
        self.interval = interval
        self.running = False
        self.thread = None
        self.stop_event = Event()
        
        # 监控的股票列表
        self.watched_stocks = set()
        
        # 回调函数
        self.data_callback = None
        
        logger.info(f"实时数据源初始化完成，更新间隔: {interval}秒")
    
    def add_stock(self, stock_code: str):
        """添加监控股票"""
        self.watched_stocks.add(stock_code)
        logger.info(f"添加监控股票: {stock_code}")
    
    def remove_stock(self, stock_code: str):
        """移除监控股票"""
        if stock_code in self.watched_stocks:
            self.watched_stocks.remove(stock_code)
            logger.info(f"移除监控股票: {stock_code}")
    
    def set_callback(self, callback: Callable[[str, pd.DataFrame], None]):
        """设置数据回调函数"""
        self.data_callback = callback
    
    def start(self):
        """启动实时数据源"""
        if self.running:
            logger.warning("实时数据源已在运行")
            return
        
        self.running = True
        self.stop_event.clear()
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()
        
        logger.info("实时数据源已启动")
    
    def stop(self):
        """停止实时数据源"""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("实时数据源已停止")
    
    def _run(self):
        """运行循环"""
        logger.info("实时数据源开始运行")
        
        while self.running and not self.stop_event.is_set():
            try:
                # 获取当前时间
                now = datetime.now()
                
                # 检查是否在交易时间
                if not self._is_trading_time(now):
                    logger.debug("非交易时间，跳过数据更新")
                    self.stop_event.wait(timeout=self.interval)
                    continue
                
                # 更新所有监控股票的数据
                for stock_code in list(self.watched_stocks):
                    try:
                        # 获取最近的数据
                        end_date = now.strftime('%Y-%m-%d')
                        start_date = (now - timedelta(days=60)).strftime('%Y-%m-%d')
                        
                        data = self.data_manager.get_stock_data(
                            stock_code,
                            start_date,
                            end_date
                        )
                        
                        if data is not None and not data.empty:
                            # 调用回调函数
                            if self.data_callback:
                                self.data_callback(stock_code, data)
                        else:
                            logger.warning(f"{stock_code}: 数据为空")
                    
                    except Exception as e:
                        logger.error(f"{stock_code}: 数据更新失败: {e}")
                
                # 等待下一次更新
                self.stop_event.wait(timeout=self.interval)
            
            except Exception as e:
                logger.error(f"实时数据源运行异常: {e}", exc_info=True)
                self.stop_event.wait(timeout=self.interval)
        
        logger.info("实时数据源已停止运行")
    
    def _is_trading_time(self, dt: datetime) -> bool:
        """
        检查是否在交易时间
        A股交易时间: 周一至周五 9:30-11:30, 13:00-15:00
        """
        # 周末不交易
        if dt.weekday() >= 5:
            return False
        
        # 检查时间段
        time_str = dt.strftime('%H:%M')
        
        # 上午: 9:30-11:30
        if '09:30' <= time_str <= '11:30':
            return True
        
        # 下午: 13:00-15:00
        if '13:00' <= time_str <= '15:00':
            return True
        
        return False


class SignalMonitor:
    """
    信号监控器
    实时计算策略信号
    """
    
    def __init__(self):
        """初始化信号监控器"""
        self.strategies = {}  # {stock_code: {strategy_name: strategy_instance}}
        self.signal_history = []  # 信号历史记录
        self.signal_callback = None
        
        logger.info("信号监控器初始化完成")
    
    def add_strategy(self, stock_code: str, strategy_name: str, **params):
        """
        添加监控策略
        :param stock_code: 股票代码
        :param strategy_name: 策略名称
        :param params: 策略参数
        """
        if stock_code not in self.strategies:
            self.strategies[stock_code] = {}
        
        try:
            # 创建策略实例
            strategy = StrategyFactory.create_strategy(strategy_name, **params)
            self.strategies[stock_code][strategy_name] = {
                'strategy': strategy,
                'params': params,
                'last_signal': None,
                'last_check': None
            }
            
            logger.info(f"添加监控策略: {stock_code} - {strategy_name}")
        
        except Exception as e:
            logger.error(f"添加策略失败: {e}", exc_info=True)
    
    def remove_strategy(self, stock_code: str, strategy_name: str):
        """移除监控策略"""
        if stock_code in self.strategies:
            if strategy_name in self.strategies[stock_code]:
                del self.strategies[stock_code][strategy_name]
                logger.info(f"移除监控策略: {stock_code} - {strategy_name}")
    
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置信号回调函数"""
        self.signal_callback = callback
    
    def check_signals(self, stock_code: str, data: pd.DataFrame):
        """
        检查策略信号
        :param stock_code: 股票代码
        :param data: 股票数据
        """
        if stock_code not in self.strategies:
            return
        
        current_time = datetime.now()
        
        # 遍历该股票的所有策略
        for strategy_name, strategy_info in self.strategies[stock_code].items():
            try:
                strategy = strategy_info['strategy']
                
                # 检查信号
                signal = self._calculate_signal(strategy, data)
                
                # 如果信号改变，触发回调
                if signal != strategy_info['last_signal']:
                    signal_data = {
                        'stock_code': stock_code,
                        'strategy_name': strategy_name,
                        'signal': signal,
                        'price': float(data['close'].iloc[-1]) if not data.empty else 0,
                        'time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'params': strategy_info['params']
                    }
                    
                    # 记录信号历史
                    self.signal_history.append(signal_data)
                    
                    # 触发回调
                    if self.signal_callback:
                        self.signal_callback(signal_data)
                    
                    # 更新最后信号
                    strategy_info['last_signal'] = signal
                    
                    logger.info(f"信号触发: {stock_code} - {strategy_name} - {signal}")
                
                # 更新最后检查时间
                strategy_info['last_check'] = current_time
            
            except Exception as e:
                logger.error(f"检查信号失败: {stock_code} - {strategy_name}: {e}")
    
    def _calculate_signal(self, strategy, data: pd.DataFrame) -> str:
        """
        计算策略信号
        :param strategy: 策略实例
        :param data: 股票数据
        :return: 'BUY', 'SELL', 'HOLD'
        """
        if data.empty or len(data) < 2:
            return 'HOLD'
        
        try:
            # 对于简单策略
            if hasattr(strategy, 'next'):
                # 初始化策略
                if hasattr(strategy, 'init'):
                    strategy.init()
                
                # 计算最后一个数据点的信号
                signal = strategy.next(data)
                
                if signal is not None:
                    if signal > 0:
                        return 'BUY'
                    elif signal < 0:
                        return 'SELL'
            
            return 'HOLD'
        
        except Exception as e:
            logger.error(f"计算信号失败: {e}")
            return 'HOLD'
    
    def get_signal_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取信号历史"""
        return self.signal_history[-limit:]


class AlertRule:
    """预警规则基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    def check(self, data: Dict[str, Any]) -> bool:
        """检查是否触发预警"""
        raise NotImplementedError


class PriceAlertRule(AlertRule):
    """价格预警规则"""
    
    def __init__(self, stock_code: str, price: float, condition: str):
        """
        :param stock_code: 股票代码
        :param price: 目标价格
        :param condition: 条件 ('above', 'below')
        """
        super().__init__(f"价格预警-{stock_code}")
        self.stock_code = stock_code
        self.price = price
        self.condition = condition
    
    def check(self, data: Dict[str, Any]) -> bool:
        """检查价格是否触发预警"""
        if data.get('stock_code') != self.stock_code:
            return False
        
        current_price = data.get('price', 0)
        
        if self.condition == 'above':
            return current_price >= self.price
        elif self.condition == 'below':
            return current_price <= self.price
        
        return False


class SignalAlertRule(AlertRule):
    """策略信号预警规则"""
    
    def __init__(self, stock_code: str, strategy_name: str, signal_type: str):
        """
        :param stock_code: 股票代码
        :param strategy_name: 策略名称
        :param signal_type: 信号类型 ('BUY', 'SELL')
        """
        super().__init__(f"信号预警-{stock_code}-{strategy_name}")
        self.stock_code = stock_code
        self.strategy_name = strategy_name
        self.signal_type = signal_type
    
    def check(self, data: Dict[str, Any]) -> bool:
        """检查信号是否触发预警"""
        if data.get('stock_code') != self.stock_code:
            return False
        
        if data.get('strategy_name') != self.strategy_name:
            return False
        
        return data.get('signal') == self.signal_type


class AlertSystem:
    """
    预警系统
    管理预警规则和通知
    """
    
    def __init__(self):
        """初始化预警系统"""
        self.rules = []
        self.alert_history = []
        self.alert_callback = None
        
        logger.info("预警系统初始化完成")
    
    def add_rule(self, rule: AlertRule):
        """添加预警规则"""
        self.rules.append(rule)
        logger.info(f"添加预警规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除预警规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"移除预警规则: {rule_name}")
    
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置预警回调函数"""
        self.alert_callback = callback
    
    def check_alerts(self, data: Dict[str, Any]):
        """
        检查预警
        :param data: 数据字典（可能来自价格更新或信号触发）
        """
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.check(data):
                    alert_data = {
                        'rule_name': rule.name,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'data': data
                    }
                    
                    # 记录预警历史
                    self.alert_history.append(alert_data)
                    
                    # 触发回调
                    if self.alert_callback:
                        self.alert_callback(alert_data)
                    
                    logger.warning(f"🔔 预警触发: {rule.name}")
            
            except Exception as e:
                logger.error(f"检查预警失败 {rule.name}: {e}")
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取预警历史"""
        return self.alert_history[-limit:]


class RealtimeMonitor:
    """
    实时监控主类
    整合数据源、信号监控和预警系统
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化实时监控"""
        self.config = config
        self.data_manager = DataManager(config)
        
        # 创建各个组件
        self.data_source = RealtimeDataSource(self.data_manager, interval=config.get('monitor_interval', 3))
        self.signal_monitor = SignalMonitor()
        self.alert_system = AlertSystem()
        
        # 设置回调
        self.data_source.set_callback(self._on_data_update)
        self.signal_monitor.set_callback(self._on_signal_trigger)
        
        # 外部回调
        self.data_callback = None
        self.signal_callback = None
        self.alert_callback = None
        
        logger.info("实时监控系统初始化完成")
    
    def start(self):
        """启动监控"""
        self.data_source.start()
        logger.info("实时监控已启动")
    
    def stop(self):
        """停止监控"""
        self.data_source.stop()
        logger.info("实时监控已停止")
    
    def add_stock(self, stock_code: str, strategies: List[Dict[str, Any]] = None):
        """
        添加监控股票
        :param stock_code: 股票代码
        :param strategies: 策略列表 [{'name': 'MA_CrossOver', 'params': {...}}, ...]
        """
        # 添加到数据源
        self.data_source.add_stock(stock_code)
        
        # 添加策略
        if strategies:
            for strategy_info in strategies:
                strategy_name = strategy_info['name']
                params = strategy_info.get('params', {})
                self.signal_monitor.add_strategy(stock_code, strategy_name, **params)
        
        logger.info(f"添加监控股票: {stock_code}, 策略数: {len(strategies) if strategies else 0}")
    
    def remove_stock(self, stock_code: str):
        """移除监控股票"""
        self.data_source.remove_stock(stock_code)
        
        # 移除所有相关策略
        if stock_code in self.signal_monitor.strategies:
            del self.signal_monitor.strategies[stock_code]
        
        logger.info(f"移除监控股票: {stock_code}")
    
    def add_alert_rule(self, rule: AlertRule):
        """添加预警规则"""
        self.alert_system.add_rule(rule)
        
        # 同时设置预警回调，检查信号和价格
        self.alert_system.set_callback(self._on_alert_trigger)
    
    def _on_data_update(self, stock_code: str, data: pd.DataFrame):
        """数据更新回调"""
        try:
            # 检查策略信号
            self.signal_monitor.check_signals(stock_code, data)
            
            # 检查价格预警
            if not data.empty:
                price_data = {
                    'stock_code': stock_code,
                    'price': float(data['close'].iloc[-1]),
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self.alert_system.check_alerts(price_data)
                
                # 触发外部数据回调
                if self.data_callback:
                    self.data_callback(stock_code, data)
        
        except Exception as e:
            logger.error(f"数据更新处理失败: {e}", exc_info=True)
    
    def _on_signal_trigger(self, signal_data: Dict[str, Any]):
        """信号触发回调"""
        try:
            # 检查信号预警
            self.alert_system.check_alerts(signal_data)
            
            # 触发外部信号回调
            if self.signal_callback:
                self.signal_callback(signal_data)
        
        except Exception as e:
            logger.error(f"信号触发处理失败: {e}", exc_info=True)
    
    def _on_alert_trigger(self, alert_data: Dict[str, Any]):
        """预警触发回调"""
        try:
            # 触发外部预警回调
            if self.alert_callback:
                self.alert_callback(alert_data)
        
        except Exception as e:
            logger.error(f"预警触发处理失败: {e}", exc_info=True)
    
    def set_data_callback(self, callback: Callable[[str, pd.DataFrame], None]):
        """设置数据更新回调"""
        self.data_callback = callback
    
    def set_signal_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置信号触发回调"""
        self.signal_callback = callback
    
    def set_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置预警触发回调"""
        self.alert_callback = callback
    
    def get_signal_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取信号历史"""
        return self.signal_monitor.get_signal_history(limit)
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取预警历史"""
        return self.alert_system.get_alert_history(limit)
