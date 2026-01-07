"""
自动交易面板
配置和监控自动交易系统
"""

import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QTableWidgetItem,
                             QSpinBox, QDoubleSpinBox, QMessageBox,
                             QHeaderView, QAbstractItemView, QFormLayout,
                             QLineEdit, QSplitter, QTabWidget,
                             QCheckBox)
from qfluentwidgets import TableWidget, TextEdit, ComboBox, PushButton, PrimaryPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from business.auto_trading import AutoTradingEngine, AutoTradingThread, AutoTradingStatus
from ui.theme_manager import ThemeManager
from business.trading_engine import TradingEngine
from business.data_manager import DataManager
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)


class AutoTradingPanel(QWidget):
    """自动交易面板"""
    
    def __init__(self, config: dict):
        """
        初始化自动交易面板
        
        :param config: 配置字典
        """
        super().__init__()
        
        self.config = config
        
        # 初始化数据管理器
        self.data_manager = DataManager(config)
        
        # 初始化交易引擎
        self.trading_engine = TradingEngine(config)
        
        # 初始化自动交易引擎
        self.auto_engine = AutoTradingEngine(
            self.trading_engine,
            self.data_manager,
            config
        )
        
        # 初始化自动交易线程
        self.auto_thread = None
        
        # UI状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 每秒更新一次
        
        self.init_ui()
        
        logger.info("自动交易面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 顶部：状态和控制按钮（一行显示）
        top_widget = self.create_top_control()
        layout.addWidget(top_widget)
        
        # 中间：使用Tab组织内容
        tab_widget = QTabWidget()
        
        # Tab1: 策略监控
        strategy_tab = self.create_strategy_tab()
        tab_widget.addTab(strategy_tab, "📊 策略监控")
        
        # Tab2: 风险控制
        risk_tab = self.create_risk_tab()
        tab_widget.addTab(risk_tab, "🛡️ 风险控制")
        
        # Tab3: 实时监控
        monitor_tab = self.create_realtime_monitor_tab()
        tab_widget.addTab(monitor_tab, "📈 实时监控")
        
        # Tab4: 运行日志
        log_tab = self.create_log_tab()
        tab_widget.addTab(log_tab, "📝 运行日志")
        
        layout.addWidget(tab_widget)
    
    def create_top_control(self) -> QWidget:
        """创建顶部控制区域"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # 左侧：状态信息
        status_group = QGroupBox("运行状态")
        status_layout = QHBoxLayout(status_group)
        
        self.status_label = QLabel("⏸️ 已停止")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.run_time_label = QLabel("运行时间: --")
        status_layout.addWidget(self.run_time_label)
        
        layout.addWidget(status_group, 2)
        
        # 中间：账户信息
        account_group = QGroupBox("账户概览")
        account_layout = QHBoxLayout(account_group)
        
        self.cash_label = QLabel("可用资金: ¥600,000")
        account_layout.addWidget(self.cash_label)
        
        self.profit_label = QLabel("今日盈亏: ¥0")
        account_layout.addWidget(self.profit_label)
        
        layout.addWidget(account_group, 2)
        
        layout.addStretch(1)
        
        # 右侧：控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = PrimaryPushButton("🚀 启动")
        self.start_btn.setFixedSize(100, 35)
        self.start_btn.clicked.connect(self.start_auto_trading)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = PushButton("⏸️ 暂停")
        self.pause_btn.setFixedSize(100, 35)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_auto_trading)
        ThemeManager.apply_pushbutton_style(self.pause_btn)  # 应用主题色边框
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = PushButton("⏹️ 停止")
        self.stop_btn.setFixedSize(100, 35)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_auto_trading)
        ThemeManager.apply_pushbutton_style(self.stop_btn)  # 应用主题色边框
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_strategy_tab(self) -> QWidget:
        """创建策略监控Tab"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 添加策略区域
        add_group = QGroupBox("添加监控策略")
        add_layout = QHBoxLayout(add_group)
        
        # 股票代码
        add_layout.addWidget(QLabel("股票代码:"))
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("如: 600000")
        self.stock_input.setFixedWidth(150)
        add_layout.addWidget(self.stock_input)
        
        # 策略选择
        add_layout.addWidget(QLabel("策略:"))
        self.strategy_combo = ComboBox()
        self.strategy_combo.setFixedWidth(200)
        strategies = StrategyFactory.get_builtin_strategies()
        from ui.strategy_panel import StrategyPanel
        for strategy in strategies:
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy, strategy)
            self.strategy_combo.addItem(display_name, strategy)
        add_layout.addWidget(self.strategy_combo)
        
        add_layout.addStretch()
        
        # 添加按钮
        add_btn = PrimaryPushButton("➕ 添加")
        add_btn.setFixedWidth(100)
        add_btn.clicked.connect(self.add_strategy_monitor)
        add_layout.addWidget(add_btn)
        
        layout.addWidget(add_group)
        
        # 策略列表
        list_group = QGroupBox("监控策略列表")
        list_layout = QVBoxLayout(list_group)
        
        self.strategy_table = TableWidget()
        self.strategy_table.setColumnCount(4)
        self.strategy_table.setHorizontalHeaderLabels(['股票代码', '策略名称', '状态', '操作'])
        self.strategy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.strategy_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.strategy_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        list_layout.addWidget(self.strategy_table)
        
        layout.addWidget(list_group)
        
        return widget
    
    def create_risk_tab(self) -> QWidget:
        """创建风险控制Tab"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 风险控制设置
        risk_group = QGroupBox("风险控制参数")
        risk_layout = QFormLayout(risk_group)
        risk_layout.setSpacing(15)
        risk_layout.setLabelAlignment(Qt.AlignRight)
        
        # 单股最大仓位
        self.max_position_spin = QDoubleSpinBox()
        self.max_position_spin.setRange(0.01, 1.0)
        self.max_position_spin.setSingleStep(0.05)
        self.max_position_spin.setValue(0.2)
        self.max_position_spin.setSuffix(" (20%)")
        risk_layout.addRow("单股最大仓位:", self.max_position_spin)
        
        # 单日亏损限制
        self.daily_loss_spin = QDoubleSpinBox()
        self.daily_loss_spin.setRange(0.01, 0.5)
        self.daily_loss_spin.setSingleStep(0.01)
        self.daily_loss_spin.setValue(0.05)
        self.daily_loss_spin.setSuffix(" (5%)")
        risk_layout.addRow("单日止损比例:", self.daily_loss_spin)
        
        # 最大订单数
        self.max_orders_spin = QSpinBox()
        self.max_orders_spin.setRange(1, 100)
        self.max_orders_spin.setValue(20)
        risk_layout.addRow("单日最大订单数:", self.max_orders_spin)
        
        layout.addWidget(risk_group)
        
        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_risk_btn = PrimaryPushButton("💾 保存设置")
        save_risk_btn.setFixedWidth(150)
        save_risk_btn.clicked.connect(self.save_risk_settings)
        btn_layout.addWidget(save_risk_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        return widget
    
    def create_realtime_monitor_tab(self) -> QWidget:
        """创建实时监控Tab"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 统计信息
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        
        # 创建4个统计卡片
        self.total_signals_label = self._create_stat_card("总信号数", "0", stats_layout)
        self.buy_signals_label = self._create_stat_card("买入信号", "0", stats_layout)
        self.sell_signals_label = self._create_stat_card("卖出信号", "0", stats_layout)
        self.orders_today_label = self._create_stat_card("今日订单", "0", stats_layout)
        
        layout.addWidget(stats_widget)
        
        # 信号历史表格
        signal_group = QGroupBox("信号历史")
        signal_layout = QVBoxLayout(signal_group)
        
        self.signal_table = TableWidget()
        self.signal_table.setColumnCount(6)
        self.signal_table.setHorizontalHeaderLabels([
            '时间', '股票代码', '策略', '信号', '价格', '数量'
        ])
        self.signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.signal_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        signal_layout.addWidget(self.signal_table)
        
        layout.addWidget(signal_group)
        
        return widget
    
    def _create_stat_card(self, title: str, value: str, parent_layout: QHBoxLayout) -> QLabel:
        """创建统计卡片"""
        card = QGroupBox(title)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 15, 10, 15)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)
        
        parent_layout.addWidget(card)
        return value_label
    
    def create_log_tab(self) -> QWidget:
        """创建日志Tab"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout(widget)
        
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        clear_log_btn = PushButton("🗑️ 清空日志")
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        ThemeManager.apply_pushbutton_style(clear_log_btn)  # 应用主题色边框
        btn_layout.addWidget(clear_log_btn)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_strategy_config(self) -> QWidget:
        """创建策略配置区域"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout(widget)
        
        # 添加策略
        add_group = QGroupBox("添加策略监控")
        add_layout = QFormLayout()
        
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("如: 600000")
        add_layout.addRow("股票代码:", self.stock_input)
        
        self.strategy_combo = ComboBox()
        strategies = StrategyFactory.get_builtin_strategies()
        from ui.strategy_panel import StrategyPanel
        for strategy in strategies:
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy, strategy)
            self.strategy_combo.addItem(display_name, strategy)
        add_layout.addRow("选择策略:", self.strategy_combo)
        
        add_btn = PrimaryPushButton("➕ 添加到监控列表")
        add_btn.clicked.connect(self.add_strategy_monitor)
        add_layout.addRow("", add_btn)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # 策略列表
        list_group = QGroupBox("监控策略列表")
        list_layout = QVBoxLayout()
        
        self.strategy_table = TableWidget()
        self.strategy_table.setColumnCount(4)
        self.strategy_table.setHorizontalHeaderLabels(['股票代码', '策略名称', '状态', '操作'])
        self.strategy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.strategy_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.strategy_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        list_layout.addWidget(self.strategy_table)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # 风险设置
        risk_group = QGroupBox("风险控制设置")
        risk_layout = QFormLayout()
        
        self.max_position_spin = QDoubleSpinBox()
        self.max_position_spin.setRange(0.1, 1.0)
        self.max_position_spin.setSingleStep(0.1)
        self.max_position_spin.setValue(0.2)
        self.max_position_spin.setSuffix(" (20%)")
        risk_layout.addRow("单股最大仓位:", self.max_position_spin)
        
        self.daily_loss_spin = QDoubleSpinBox()
        self.daily_loss_spin.setRange(0.01, 0.2)
        self.daily_loss_spin.setSingleStep(0.01)
        self.daily_loss_spin.setValue(0.05)
        self.daily_loss_spin.setSuffix(" (5%)")
        risk_layout.addRow("单日亏损限制:", self.daily_loss_spin)
        
        self.max_orders_spin = QSpinBox()
        self.max_orders_spin.setRange(1, 100)
        self.max_orders_spin.setValue(20)
        risk_layout.addRow("单日最大订单数:", self.max_orders_spin)
        
        save_risk_btn = PrimaryPushButton("💾 保存设置")
        save_risk_btn.clicked.connect(self.save_risk_settings)
        risk_layout.addRow("", save_risk_btn)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        layout.addStretch()
        
        return widget
    
    def add_strategy_monitor(self):
        """添加策略监控"""
        stock_code = self.stock_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码！")
            return
        
        strategy_name = self.strategy_combo.currentData()
        
        # 添加到自动交易引擎
        success = self.auto_engine.add_strategy(strategy_name, stock_code)
        
        if success:
            # 更新表格
            self.refresh_strategy_table()
            self.stock_input.clear()
            self.log(f"✅ 添加策略监控: {strategy_name} - {stock_code}")
        else:
            QMessageBox.warning(self, "错误", "添加策略监控失败！")
    
    def remove_strategy_monitor(self, strategy_name: str, stock_code: str):
        """移除策略监控"""
        success = self.auto_engine.remove_strategy(strategy_name, stock_code)
        if success:
            self.refresh_strategy_table()
            self.log(f"🗑 移除策略监控: {strategy_name} - {stock_code}")
    
    def refresh_strategy_table(self):
        """刷新策略表格"""
        self.strategy_table.setRowCount(0)
        
        for key, monitor in self.auto_engine.strategy_monitors.items():
            row = self.strategy_table.rowCount()
            self.strategy_table.insertRow(row)
            
            from ui.strategy_panel import StrategyPanel
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(
                monitor.strategy_name,
                monitor.strategy_name
            )
            
            self.strategy_table.setItem(row, 0, QTableWidgetItem(monitor.stock_code))
            self.strategy_table.setItem(row, 1, QTableWidgetItem(display_name))
            
            status_item = QTableWidgetItem("激活" if monitor.is_active else "停用")
            status_item.setForeground(QColor('green') if monitor.is_active else QColor('gray'))
            self.strategy_table.setItem(row, 2, status_item)
            
            # 操作按钮
            remove_btn = PushButton("删除")
            remove_btn.clicked.connect(
                lambda checked, s=monitor.strategy_name, c=monitor.stock_code:
                self.remove_strategy_monitor(s, c)
            )
            ThemeManager.apply_pushbutton_style(remove_btn)  # 应用主题色边框
            self.strategy_table.setCellWidget(row, 3, remove_btn)
    
    def save_risk_settings(self):
        """保存风险设置"""
        self.auto_engine.max_position_per_stock = self.max_position_spin.value()
        self.auto_engine.daily_loss_limit = self.daily_loss_spin.value()
        self.auto_engine.max_orders_per_day = self.max_orders_spin.value()
        
        QMessageBox.information(self, "成功", "风险控制设置已保存！")
        self.log("💾 风险控制设置已更新")
    
    def start_auto_trading(self):
        """启动自动交易"""
        if not self.auto_engine.strategy_monitors:
            QMessageBox.warning(
                self,
                "警告",
                "请先添加至少一个策略监控！"
            )
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认启动",
            "⚠️ 确定要启动自动交易吗？\n\n"
            "请确保：\n"
            "1. 已充分测试所选策略\n"
            "2. 风险控制参数设置合理\n"
            "3. 准备好随时监控和干预\n\n"
            "建议先在模拟账户中运行！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.auto_engine.start()
            
            if success:
                # 启动监控线程
                if self.auto_thread is None:
                    self.auto_thread = AutoTradingThread(self.auto_engine)
                    self.auto_thread.status_updated.connect(self.on_status_update)
                    self.auto_thread.error_occurred.connect(self.on_error)
                
                self.auto_thread.start()
                
                # 更新UI状态
                self.start_btn.setEnabled(False)
                self.pause_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                
                self.log("🚀 自动交易已启动")
                QMessageBox.information(self, "成功", "自动交易已启动！")
            else:
                QMessageBox.critical(self, "错误", "启动自动交易失败！")
    
    def pause_auto_trading(self):
        """暂停自动交易"""
        if self.auto_engine.status == AutoTradingStatus.RUNNING:
            self.auto_engine.pause()
            self.pause_btn.setText("▶ 继续")
            self.log("⏸ 自动交易已暂停")
        else:
            self.auto_engine.resume()
            self.pause_btn.setText("⏸ 暂停")
            self.log("▶ 自动交易已继续")
    
    def stop_auto_trading(self):
        """停止自动交易"""
        reply = QMessageBox.question(
            self,
            "确认停止",
            "确定要停止自动交易吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.auto_engine.stop()
            
            if self.auto_thread:
                self.auto_thread.stop()
                self.auto_thread.wait()
            
            # 更新UI状态
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸ 暂停")
            self.stop_btn.setEnabled(False)
            
            self.log("⏹ 自动交易已停止")
            QMessageBox.information(self, "已停止", "自动交易已停止")
    
    def update_status(self):
        """更新状态显示"""
        status = self.auto_engine.status
        
        # 更新状态标签
        status_text = f"状态: {status.value}"
        
        if status == AutoTradingStatus.RUNNING:
            self.status_label.setStyleSheet(ThemeManager.get_badge_style('success'))
        elif status == AutoTradingStatus.PAUSED:
            self.status_label.setStyleSheet(ThemeManager.get_badge_style('warning'))
        else:
            self.status_label.setStyleSheet(ThemeManager.get_badge_style('info'))
        
        self.status_label.setText(status_text)
        
        # 更新统计信息
        stats = self.auto_engine.get_statistics()
        self.total_signals_label.setText(str(stats['total_signals']))
        self.buy_signals_label.setText(str(stats['buy_signals']))
        self.sell_signals_label.setText(str(stats['sell_signals']))
        self.orders_today_label.setText(str(stats['order_count_today']))
    
    def on_status_update(self, status_dict):
        """处理状态更新"""
        # 可以在这里添加更多的状态处理逻辑
        pass
    
    def on_error(self, error_msg):
        """处理错误"""
        self.log(f"❌ 错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"自动交易发生错误:\n{error_msg}")
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        logger.info(message)
