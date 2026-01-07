"""
实盘交易面板
提供账户管理、持仓查询、下单交易的用户界面
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidgetItem, QHeaderView,
    QGroupBox, QSpinBox, QDoubleSpinBox, QTabWidget,
    QSplitter, QFormLayout, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from qfluentwidgets import TableWidget, ComboBox, PushButton, PrimaryPushButton
from typing import Dict, Any
from datetime import datetime

from business.data_service import get_data_service
from business.trading_engine import TradingEngine, OrderType, OrderSide
from ui.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class TradingPanel(QWidget):
    """实盘交易面板"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config
        self.data_service = get_data_service()
        
        # 创建交易引擎（默认使用模拟交易）
        self.trading_engine = TradingEngine(config)
        
        # 定时器（用于刷新持仓市值）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_positions)
        
        self.init_ui()
        
        # 初始加载
        self.refresh_account()
        self.refresh_positions()
        self.refresh_orders()
        
        logger.info("实盘交易面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 警告标签
        warning_label = QLabel("⚠️ 当前为模拟交易模式 - 不会产生真实交易")
        warning_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning_label)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 上半部分：账户和下单
        top_widget = self.create_top_panel()
        splitter.addWidget(top_widget)
        
        # 下半部分：持仓和订单
        bottom_widget = self.create_bottom_panel()
        splitter.addWidget(bottom_widget)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def create_top_panel(self) -> QWidget:
        """创建上半部分（账户+下单）"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QHBoxLayout()
        
        # 左侧：账户信息
        account_group = QGroupBox("账户信息")
        account_layout = QFormLayout()
        
        # 交易模式显示
        self.trading_mode_label = QLabel()
        self.update_trading_mode_display()
        account_layout.addRow("交易模式:", self.trading_mode_label)
        
        account_layout.addRow(QLabel(""))  # 空行分隔
        
        self.cash_label = QLabel("--")
        account_layout.addRow("可用资金:", self.cash_label)
        
        self.market_value_label = QLabel("--")
        account_layout.addRow("持仓市值:", self.market_value_label)
        
        self.total_assets_label = QLabel("--")
        account_layout.addRow("总资产:", self.total_assets_label)
        
        self.profit_label = QLabel("--")
        account_layout.addRow("总盈亏:", self.profit_label)
        
        self.profit_ratio_label = QLabel("--")
        account_layout.addRow("收益率:", self.profit_ratio_label)
        
        refresh_btn = PrimaryPushButton("🔄 刷新账户")
        refresh_btn.clicked.connect(self.refresh_account)
        account_layout.addRow(refresh_btn)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        # 右侧：快速下单
        order_group = QGroupBox("快速下单")
        order_layout = QFormLayout()
        
        # 股票代码
        self.order_stock_code = QLineEdit()
        self.order_stock_code.setPlaceholderText("例如: 605066")
        order_layout.addRow("股票代码:", self.order_stock_code)
        
        # 当前价格（用于参考）
        self.order_current_price = QLineEdit()
        self.order_current_price.setPlaceholderText("当前价格")
        self.order_current_price.setReadOnly(True)
        
        get_price_btn = PushButton("获取价格")
        get_price_btn.clicked.connect(self.get_current_price)
        ThemeManager.apply_pushbutton_style(get_price_btn)  # 应用主题色边框
        
        price_layout = QHBoxLayout()
        price_layout.addWidget(self.order_current_price)
        price_layout.addWidget(get_price_btn)
        order_layout.addRow("当前价:", price_layout)
        
        # 交易数量
        self.order_quantity = QSpinBox()
        self.order_quantity.setRange(100, 1000000)
        self.order_quantity.setValue(100)
        self.order_quantity.setSingleStep(100)
        order_layout.addRow("数量:", self.order_quantity)
        
        # 订单类型
        self.order_type = ComboBox()
        self.order_type.addItems(['市价单', '限价单'])
        order_layout.addRow("订单类型:", self.order_type)
        
        # 限价
        self.order_price = QDoubleSpinBox()
        self.order_price.setRange(0.01, 10000)
        self.order_price.setValue(10.0)
        self.order_price.setSingleStep(0.01)
        self.order_price.setDecimals(2)
        order_layout.addRow("限价:", self.order_price)
        
        # 预估金额
        self.order_estimate = QLabel("--")
        order_layout.addRow("预估金额:", self.order_estimate)
        
        # 买入/卖出按钮
        button_layout = QHBoxLayout()
        
        self.buy_btn = PrimaryPushButton("💰 买入")
        self.buy_btn.clicked.connect(self.place_buy_order)
        button_layout.addWidget(self.buy_btn)
        
        self.sell_btn = PushButton("💸 卖出")
        self.sell_btn.clicked.connect(self.place_sell_order)
        ThemeManager.apply_pushbutton_style(self.sell_btn)  # 应用主题色边框
        button_layout.addWidget(self.sell_btn)
        
        order_layout.addRow(button_layout)
        
        # 连接信号（实时计算预估金额）
        self.order_quantity.valueChanged.connect(self.update_estimate)
        self.order_price.valueChanged.connect(self.update_estimate)
        self.order_current_price.textChanged.connect(self.update_estimate)
        
        order_group.setLayout(order_layout)
        layout.addWidget(order_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_bottom_panel(self) -> QWidget:
        """创建下半部分（持仓+订单）"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 20)  # 增加底部边距
        
        # 创建标签页
        self.display_tabs = QTabWidget()
        self.display_tabs.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.display_tabs.setMinimumHeight(400)  # 设置最小高度
        
        # 持仓列表
        self.position_table = TableWidget()
        self.position_table.setColumnCount(7)
        self.position_table.setHorizontalHeaderLabels([
            '股票代码', '持仓数量', '可用数量', '成本价', '现价', '盈亏', '盈亏比(%)'
        ])
        self.position_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.position_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.display_tabs.addTab(self.position_table, "� 持仓列表")
        
        # 订单列表
        self.order_table = TableWidget()
        self.order_table.setColumnCount(9)
        self.order_table.setHorizontalHeaderLabels([
            '订单ID', '股票代码', '方向', '类型', '数量', '价格', '成交数量', '状态', '时间'
        ])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.display_tabs.addTab(self.order_table, "📝 订单列表")
        
        # 成交记录
        self.trade_table = TableWidget()
        self.trade_table.setColumnCount(8)
        self.trade_table.setHorizontalHeaderLabels([
            '订单ID', '股票代码', '方向', '数量', '价格', '金额', '手续费', '时间'
        ])
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trade_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.display_tabs.addTab(self.trade_table, "💼 成交记录")
        
        # 交易日志
        self.trade_log = QTextEdit()
        self.trade_log.setReadOnly(True)
        self.display_tabs.addTab(self.trade_log, "📋 交易日志")
        
        layout.addWidget(self.display_tabs)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        refresh_positions_btn = PrimaryPushButton("🔄 刷新持仓")
        refresh_positions_btn.clicked.connect(self.refresh_positions)
        button_layout.addWidget(refresh_positions_btn)
        
        refresh_orders_btn = PrimaryPushButton("🔄 刷新订单")
        refresh_orders_btn.clicked.connect(self.refresh_orders)
        button_layout.addWidget(refresh_orders_btn)
        
        auto_refresh_btn = PushButton("⏰ 自动刷新")
        auto_refresh_btn.setCheckable(True)
        auto_refresh_btn.toggled.connect(self.toggle_auto_refresh)
        ThemeManager.apply_pushbutton_style(auto_refresh_btn)  # 应用主题色边框
        button_layout.addWidget(auto_refresh_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
    def update_trading_mode_display(self):
        """更新交易模式显示"""
        try:
            import yaml
            from pathlib import Path
            
            config_file = Path("config/broker_config.yaml")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    broker_config = yaml.safe_load(f)
                    mode = broker_config.get('trading_mode', {}).get('mode', 'simulation')
                    
                    if mode == 'simulation':
                        self.trading_mode_label.setText("🎮 模拟交易")
                        self.trading_mode_label.setStyleSheet(ThemeManager.get_badge_style('info'))
                    else:
                        self.trading_mode_label.setText("💰 实盘交易")
                        self.trading_mode_label.setStyleSheet(ThemeManager.get_badge_style('warning'))
            else:
                self.trading_mode_label.setText("🎮 模拟交易")
                self.trading_mode_label.setStyleSheet(ThemeManager.get_badge_style('info'))
        except Exception as e:
            logger.error(f"更新交易模式显示失败: {e}")
            self.trading_mode_label.setText("❓ 未知模式")
    
    def refresh_account(self):
        """刷新账户信息"""
        try:
            # 更新交易模式显示
            self.update_trading_mode_display()
            
            account_info = self.trading_engine.get_account_info()
            
            self.cash_label.setText(f"{account_info['cash']:.2f}")
            self.market_value_label.setText(f"{account_info['market_value']:.2f}")
            self.total_assets_label.setText(f"{account_info['total_assets']:.2f}")
            
            profit = account_info['total_profit']
            profit_ratio = account_info['total_profit_ratio']
            
            profit_text = f"{profit:+.2f}"
            profit_ratio_text = f"{profit_ratio:+.2f}%"
            
            # 设置颜色
            color = ThemeManager.get_status_color('success' if profit >= 0 else 'error')
            self.profit_label.setText(profit_text)
            self.profit_label.setStyleSheet(ThemeManager.get_label_style(color=color, bold=True))
            self.profit_ratio_label.setText(profit_ratio_text)
            self.profit_ratio_label.setStyleSheet(ThemeManager.get_label_style(color=color, bold=True))
            
            logger.info("账户信息已刷新")
        
        except Exception as e:
            logger.error(f"刷新账户信息失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"刷新账户信息失败：\n{e}")
    
    def refresh_positions(self):
        """刷新持仓列表"""
        try:
            positions = self.trading_engine.get_positions()
            
            # 获取最新价格
            prices = {}
            for position in positions:
                try:
                    data = self.data_service.get_stock_data(
                        position.stock_code,
                        datetime.now().strftime('%Y-%m-%d'),
                        datetime.now().strftime('%Y-%m-%d')
                    )
                    if data is not None and not data.empty:
                        prices[position.stock_code] = float(data['close'].iloc[-1])
                except:
                    pass
            
            # 更新市值
            self.trading_engine.update_positions_market_value(prices)
            
            # 刷新表格
            self.position_table.setRowCount(len(positions))
            
            for i, position in enumerate(positions):
                current_price = prices.get(position.stock_code, 0)
                
                self.position_table.setItem(i, 0, QTableWidgetItem(position.stock_code))
                self.position_table.setItem(i, 1, QTableWidgetItem(str(position.quantity)))
                self.position_table.setItem(i, 2, QTableWidgetItem(str(position.available_quantity)))
                self.position_table.setItem(i, 3, QTableWidgetItem(f"{position.average_cost:.2f}"))
                self.position_table.setItem(i, 4, QTableWidgetItem(f"{current_price:.2f}"))
                
                profit_item = QTableWidgetItem(f"{position.profit_loss:+.2f}")
                profit_ratio_item = QTableWidgetItem(f"{position.profit_loss_ratio:+.2f}")
                
                # 设置颜色
                color = QColor('red') if position.profit_loss >= 0 else QColor('green')
                profit_item.setForeground(color)
                profit_ratio_item.setForeground(color)
                
                self.position_table.setItem(i, 5, profit_item)
                self.position_table.setItem(i, 6, profit_ratio_item)
            
            # 同时刷新账户信息
            self.refresh_account()
            
            logger.info(f"持仓列表已刷新，共 {len(positions)} 个持仓")
        
        except Exception as e:
            logger.error(f"刷新持仓列表失败: {e}", exc_info=True)
    
    def refresh_orders(self):
        """刷新订单列表"""
        try:
            orders = self.trading_engine.get_orders()
            
            # 刷新订单表格
            self.order_table.setRowCount(len(orders))
            
            for i, order in enumerate(orders):
                order_dict = order.to_dict()
                
                self.order_table.setItem(i, 0, QTableWidgetItem(order_dict['order_id']))
                self.order_table.setItem(i, 1, QTableWidgetItem(order_dict['stock_code']))
                self.order_table.setItem(i, 2, QTableWidgetItem(order_dict['side']))
                self.order_table.setItem(i, 3, QTableWidgetItem(order_dict['order_type']))
                self.order_table.setItem(i, 4, QTableWidgetItem(str(order_dict['quantity'])))
                self.order_table.setItem(i, 5, QTableWidgetItem(f"{order_dict['price']:.2f}" if order_dict['price'] else "--"))
                self.order_table.setItem(i, 6, QTableWidgetItem(str(order_dict['filled_quantity'])))
                self.order_table.setItem(i, 7, QTableWidgetItem(order_dict['status']))
                self.order_table.setItem(i, 8, QTableWidgetItem(order_dict['create_time']))
            
            # 刷新成交记录
            trades = self.trading_engine.get_trades()
            self.trade_table.setRowCount(len(trades))
            
            for i, trade in enumerate(trades):
                self.trade_table.setItem(i, 0, QTableWidgetItem(trade['order_id']))
                self.trade_table.setItem(i, 1, QTableWidgetItem(trade['stock_code']))
                self.trade_table.setItem(i, 2, QTableWidgetItem(trade['side']))
                self.trade_table.setItem(i, 3, QTableWidgetItem(str(trade['quantity'])))
                self.trade_table.setItem(i, 4, QTableWidgetItem(f"{trade['price']:.2f}"))
                self.trade_table.setItem(i, 5, QTableWidgetItem(f"{trade['amount']:.2f}"))
                self.trade_table.setItem(i, 6, QTableWidgetItem(f"{trade['commission'] + trade['stamp_duty']:.2f}"))
                self.trade_table.setItem(i, 7, QTableWidgetItem(trade['time']))
            
            logger.info(f"订单列表已刷新，共 {len(orders)} 个订单，{len(trades)} 笔成交")
        
        except Exception as e:
            logger.error(f"刷新订单列表失败: {e}", exc_info=True)
    
    def get_current_price(self):
        """获取当前价格"""
        stock_code = self.order_stock_code.text().strip()
        
        if not stock_code:
            QMessageBox.warning(self, "输入错误", "请输入股票代码！")
            return
        
        try:
            # 获取最新数据
            data = self.data_service.get_stock_data(
                stock_code,
                datetime.now().strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )
            
            if data is None or data.empty:
                QMessageBox.warning(self, "数据错误", "无法获取股票数据！")
                return
            
            price = float(data['close'].iloc[-1])
            self.order_current_price.setText(f"{price:.2f}")
            self.order_price.setValue(price)
            
            self.append_log(f"获取价格成功: {stock_code} = {price:.2f}", "blue")
        
        except Exception as e:
            logger.error(f"获取价格失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"获取价格失败：\n{e}")
    
    def update_estimate(self):
        """更新预估金额"""
        try:
            quantity = self.order_quantity.value()
            
            if self.order_type.currentText() == '市价单':
                price_text = self.order_current_price.text()
                if price_text and price_text != '--':
                    price = float(price_text)
                else:
                    self.order_estimate.setText("--")
                    return
            else:
                price = self.order_price.value()
            
            amount = quantity * price
            fee = amount * 0.0013  # 约0.13%的费用
            total = amount + fee
            
            self.order_estimate.setText(f"{total:.2f}")
        
        except:
            self.order_estimate.setText("--")
    
    def place_buy_order(self):
        """下买单"""
        self.place_order(OrderSide.BUY)
    
    def place_sell_order(self):
        """下卖单"""
        self.place_order(OrderSide.SELL)
    
    def place_order(self, side: OrderSide):
        """下单"""
        stock_code = self.order_stock_code.text().strip()
        quantity = self.order_quantity.value()
        order_type_text = self.order_type.currentText()
        
        if not stock_code:
            QMessageBox.warning(self, "输入错误", "请输入股票代码！")
            return
        
        # 确认对话框
        side_text = "买入" if side == OrderSide.BUY else "卖出"
        confirm_msg = f"确认{side_text}？\n\n股票代码: {stock_code}\n数量: {quantity}\n订单类型: {order_type_text}"
        
        reply = QMessageBox.question(
            self,
            "确认下单",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 获取价格
            if order_type_text == '市价单':
                price_text = self.order_current_price.text()
                if not price_text or price_text == '--':
                    QMessageBox.warning(self, "错误", "请先获取当前价格！")
                    return
                price = float(price_text)
                order_type = OrderType.MARKET
            else:
                price = self.order_price.value()
                order_type = OrderType.LIMIT
            
            # 下单
            if side == OrderSide.BUY:
                success, message, order = self.trading_engine.buy(stock_code, quantity, price, order_type)
            else:
                success, message, order = self.trading_engine.sell(stock_code, quantity, price, order_type)
            
            if success:
                QMessageBox.information(self, "成功", f"{side_text}成功！\n{message}")
                self.append_log(f"✅ {side_text}成功: {stock_code} x {quantity} @ {price:.2f}", "green")
                
                # 刷新显示
                self.refresh_account()
                self.refresh_positions()
                self.refresh_orders()
            else:
                QMessageBox.warning(self, "失败", f"{side_text}失败！\n{message}")
                self.append_log(f"❌ {side_text}失败: {message}", "red")
        
        except Exception as e:
            logger.error(f"下单异常: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"下单异常：\n{e}")
            self.append_log(f"❌ 下单异常: {e}", "red")
    
    def toggle_auto_refresh(self, checked: bool):
        """切换自动刷新"""
        if checked:
            self.refresh_timer.start(5000)  # 5秒刷新一次
            self.append_log("⏰ 自动刷新已启动（5秒间隔）", "blue")
        else:
            self.refresh_timer.stop()
            self.append_log("⏸️ 自动刷新已停止", "blue")
    
    def append_log(self, message: str, color: str = 'black'):
        """添加日志"""
        time_str = datetime.now().strftime('%H:%M:%S')
        self.trade_log.append(f'<span style="color: {color};">[{time_str}] {message}</span>')
        
        # 滚动到底部
        self.trade_log.verticalScrollBar().setValue(
            self.trade_log.verticalScrollBar().maximum()
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        self.refresh_timer.stop()
        event.accept()
