"""
实时监控面板
提供实时行情监控、策略信号监控和预警的用户界面
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidgetItem, QHeaderView,
    QGroupBox, QSpinBox, QListWidgetItem,
    QTabWidget, QSplitter, QFormLayout, QMessageBox,
    QCheckBox
)
from qfluentwidgets import TableWidget, ListWidget, TextEdit, ComboBox, PushButton, PrimaryPushButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

from business.data_manager import DataManager
from business.realtime_monitor import (
    RealtimeMonitor, PriceAlertRule, SignalAlertRule
)
from core.strategy_base import StrategyFactory
from ui.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class MonitorPanel(QWidget):
    """实时监控面板"""
    
    # 自定义信号
    data_updated = pyqtSignal(str, object)  # stock_code, data
    signal_triggered = pyqtSignal(dict)     # signal_data
    alert_triggered = pyqtSignal(dict)      # alert_data
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.monitor = RealtimeMonitor(config)
        
        # 设置回调
        self.monitor.set_data_callback(self._on_data_update)
        self.monitor.set_signal_callback(self._on_signal_trigger)
        self.monitor.set_alert_callback(self._on_alert_trigger)
        
        # 连接信号到槽
        self.data_updated.connect(self.on_data_updated)
        self.signal_triggered.connect(self.on_signal_triggered)
        self.alert_triggered.connect(self.on_alert_triggered)
        
        # 监控状态
        self.is_monitoring = False
        
        self.init_ui()
        logger.info("实时监控面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 上半部分：控制面板
        top_widget = self.create_control_panel()
        splitter.addWidget(top_widget)
        
        # 下半部分：监控展示
        bottom_widget = self.create_monitor_display()
        splitter.addWidget(bottom_widget)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QHBoxLayout()
        
        # 左侧：股票添加
        left_group = QGroupBox("监控配置")
        left_layout = QFormLayout()
        
        # 股票代码输入
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("例如: 605066")
        left_layout.addRow("股票代码:", self.stock_input)
        
        # 策略选择
        self.strategy_combo = ComboBox()
        strategies = StrategyFactory.get_builtin_strategies()
        from ui.strategy_panel import StrategyPanel
        for strategy_name in strategies:
            # 显示中文名称，存储英文代码
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
            self.strategy_combo.addItem(display_name, strategy_name)
        left_layout.addRow("监控策略:", self.strategy_combo)
        
        # 添加按钮
        add_btn_layout = QHBoxLayout()
        self.add_stock_btn = PrimaryPushButton("➕ 添加监控")
        self.add_stock_btn.clicked.connect(self.add_stock)
        add_btn_layout.addWidget(self.add_stock_btn)
        
        self.remove_stock_btn = PushButton("➖ 移除监控")
        self.remove_stock_btn.clicked.connect(self.remove_stock)
        ThemeManager.apply_pushbutton_style(self.remove_stock_btn)  # 应用主题色边框
        add_btn_layout.addWidget(self.remove_stock_btn)
        
        left_layout.addRow(add_btn_layout)
        
        left_group.setLayout(left_layout)
        layout.addWidget(left_group)
        
        # 中间：预警配置
        middle_group = QGroupBox("预警配置")
        middle_layout = QFormLayout()
        
        # 价格预警
        self.price_alert_stock = QLineEdit()
        self.price_alert_stock.setPlaceholderText("股票代码")
        middle_layout.addRow("股票代码:", self.price_alert_stock)
        
        self.price_alert_value = QLineEdit()
        self.price_alert_value.setPlaceholderText("目标价格")
        middle_layout.addRow("目标价格:", self.price_alert_value)
        
        self.price_alert_condition = ComboBox()
        self.price_alert_condition.addItems(['突破', '跌破'])
        middle_layout.addRow("条件:", self.price_alert_condition)
        
        self.add_price_alert_btn = PrimaryPushButton("➕ 添加价格预警")
        self.add_price_alert_btn.clicked.connect(self.add_price_alert)
        middle_layout.addRow(self.add_price_alert_btn)
        
        # 信号预警
        self.signal_alert_stock = QLineEdit()
        self.signal_alert_stock.setPlaceholderText("股票代码")
        middle_layout.addRow("股票代码:", self.signal_alert_stock)
        
        self.signal_alert_strategy = ComboBox()
        from ui.strategy_panel import StrategyPanel
        for strategy_name in strategies:
            # 显示中文名称，存储英文代码
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
            self.signal_alert_strategy.addItem(display_name, strategy_name)
        middle_layout.addRow("策略:", self.signal_alert_strategy)
        
        self.signal_alert_type = ComboBox()
        self.signal_alert_type.addItems(['买入', '卖出'])
        middle_layout.addRow("信号类型:", self.signal_alert_type)
        
        self.add_signal_alert_btn = PrimaryPushButton("➕ 添加信号预警")
        self.add_signal_alert_btn.clicked.connect(self.add_signal_alert)
        middle_layout.addRow(self.add_signal_alert_btn)
        
        middle_group.setLayout(middle_layout)
        layout.addWidget(middle_group)
        
        # 右侧：控制按钮
        right_group = QGroupBox("监控控制")
        right_layout = QVBoxLayout()
        
        # 启动/停止按钮
        self.start_btn = PrimaryPushButton("▶️ 启动监控")
        self.start_btn.clicked.connect(self.start_monitoring)
        right_layout.addWidget(self.start_btn)
        
        self.stop_btn = PushButton("⏸️ 停止监控")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        ThemeManager.apply_pushbutton_style(self.stop_btn)  # 应用主题色边框
        right_layout.addWidget(self.stop_btn)
        
        # 状态显示
        self.status_label = QLabel("状态: 未启动")
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)
        
        # 更新间隔配置
        interval_layout = QFormLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(3)
        self.interval_spin.setSuffix(" 秒")
        interval_layout.addRow("更新间隔:", self.interval_spin)
        right_layout.addLayout(interval_layout)
        
        # 声音提醒
        self.sound_alert_check = QCheckBox("声音提醒")
        self.sound_alert_check.setChecked(True)
        right_layout.addWidget(self.sound_alert_check)
        
        right_layout.addStretch()
        right_group.setLayout(right_layout)
        layout.addWidget(right_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_monitor_display(self) -> QWidget:
        """创建监控展示区域"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 20)  # 增加底部边距
        
        # 创建标签页
        self.display_tabs = QTabWidget()
        self.display_tabs.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.display_tabs.setMinimumHeight(400)  # 设置最小高度
        
        # 监控列表
        self.stock_list = TableWidget()
        self.stock_list.setColumnCount(6)
        self.stock_list.setHorizontalHeaderLabels([
            '股票代码', '最新价', '涨跌幅(%)', '策略', '信号', '更新时间'
        ])
        self.stock_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stock_list.setEditTriggers(TableWidget.NoEditTriggers)
        self.display_tabs.addTab(self.stock_list, "📊 监控列表")
        
        # 信号日志
        self.signal_log = TextEdit()
        self.signal_log.setReadOnly(True)
        self.display_tabs.addTab(self.signal_log, "📈 信号日志")
        
        # 预警日志
        self.alert_log = TextEdit()
        self.alert_log.setReadOnly(True)
        self.display_tabs.addTab(self.alert_log, "🔔 预警日志")
        
        # 预警规则列表
        self.alert_rules_list = ListWidget()
        self.display_tabs.addTab(self.alert_rules_list, "📋 预警规则")
        
        layout.addWidget(self.display_tabs)
        widget.setLayout(layout)
        
        return widget
    
    def start_monitoring(self):
        """启动监控"""
        if self.is_monitoring:
            return
        
        # 更新监控间隔
        self.monitor.data_source.interval = self.interval_spin.value()
        
        # 启动监控
        self.monitor.start()
        self.is_monitoring = True
        
        # 更新UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态: 监控中...")
        self.status_label.setStyleSheet(ThemeManager.get_label_style(
            color=ThemeManager.get_status_color('running'), bold=True
        ))
        
        logger.info("监控已启动")
        self.append_to_log(self.alert_log, "✅ 监控已启动", "green")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            return
        
        # 停止监控
        self.monitor.stop()
        self.is_monitoring = False
        
        # 更新UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 已停止")
        self.status_label.setStyleSheet(ThemeManager.get_label_style(
            color=ThemeManager.get_status_color('stopped'), bold=True
        ))
        
        logger.info("监控已停止")
        self.append_to_log(self.alert_log, "⏸️ 监控已停止", "red")
    
    def add_stock(self):
        """添加监控股票"""
        stock_code = self.stock_input.text().strip()
        # 获取当前选中的策略代码（从UserData）
        strategy_name = self.strategy_combo.currentData()
        if strategy_name is None:
            # 兜底，如果没有设置UserData，则使用显示文本
            strategy_name = self.strategy_combo.currentText()
        
        if not stock_code:
            QMessageBox.warning(self, "输入错误", "请输入股票代码！")
            return
        
        # 添加到监控系统
        strategies = [{'name': strategy_name, 'params': {}}]
        self.monitor.add_stock(stock_code, strategies)
        
        # 添加到表格
        row_count = self.stock_list.rowCount()
        self.stock_list.insertRow(row_count)
        
        self.stock_list.setItem(row_count, 0, QTableWidgetItem(stock_code))
        self.stock_list.setItem(row_count, 1, QTableWidgetItem("--"))
        self.stock_list.setItem(row_count, 2, QTableWidgetItem("--"))
        self.stock_list.setItem(row_count, 3, QTableWidgetItem(strategy_name))
        self.stock_list.setItem(row_count, 4, QTableWidgetItem("--"))
        self.stock_list.setItem(row_count, 5, QTableWidgetItem("--"))
        
        # 清空输入
        self.stock_input.clear()
        
        logger.info(f"添加监控: {stock_code} - {strategy_name}")
        self.append_to_log(self.alert_log, f"➕ 添加监控: {stock_code} - {strategy_name}", "blue")
    
    def remove_stock(self):
        """移除监控股票"""
        current_row = self.stock_list.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(self, "选择错误", "请先选择要移除的股票！")
            return
        
        # 获取股票代码
        stock_code = self.stock_list.item(current_row, 0).text()
        
        # 从监控系统移除
        self.monitor.remove_stock(stock_code)
        
        # 从表格移除
        self.stock_list.removeRow(current_row)
        
        logger.info(f"移除监控: {stock_code}")
        self.append_to_log(self.alert_log, f"➖ 移除监控: {stock_code}", "orange")
    
    def add_price_alert(self):
        """添加价格预警"""
        stock_code = self.price_alert_stock.text().strip()
        price_str = self.price_alert_value.text().strip()
        condition = '突破' if self.price_alert_condition.currentText() == '突破' else '跌破'
        
        if not stock_code or not price_str:
            QMessageBox.warning(self, "输入错误", "请填写完整的预警信息！")
            return
        
        try:
            price = float(price_str)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "价格必须是数字！")
            return
        
        # 创建预警规则
        condition_en = 'above' if condition == '突破' else 'below'
        rule = PriceAlertRule(stock_code, price, condition_en)
        self.monitor.add_alert_rule(rule)
        
        # 添加到规则列表
        rule_text = f"价格预警: {stock_code} {condition} {price:.2f}"
        self.alert_rules_list.addItem(rule_text)
        
        # 清空输入
        self.price_alert_stock.clear()
        self.price_alert_value.clear()
        
        logger.info(f"添加价格预警: {rule_text}")
        self.append_to_log(self.alert_log, f"➕ {rule_text}", "blue")
    
    def add_signal_alert(self):
        """添加信号预警"""
        stock_code = self.signal_alert_stock.text().strip()
        # 获取策略代码（从UserData）
        strategy_name = self.signal_alert_strategy.currentData()
        if strategy_name is None:
            strategy_name = self.signal_alert_strategy.currentText()
        signal_type = 'BUY' if self.signal_alert_type.currentText() == '买入' else 'SELL'
        
        if not stock_code:
            QMessageBox.warning(self, "输入错误", "请输入股票代码！")
            return
        
        # 创建预警规则
        rule = SignalAlertRule(stock_code, strategy_name, signal_type)
        self.monitor.add_alert_rule(rule)
        
        # 添加到规则列表（显示中文）
        from ui.strategy_panel import StrategyPanel
        display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
        rule_text = f"信号预警: {stock_code} - {display_name} - {signal_type}"
        self.alert_rules_list.addItem(rule_text)
        
        # 清空输入
        self.signal_alert_stock.clear()
        
        logger.info(f"添加信号预警: {rule_text}")
        self.append_to_log(self.alert_log, f"➕ {rule_text}", "blue")
    
    def _on_data_update(self, stock_code: str, data: pd.DataFrame):
        """数据更新回调（后台线程）"""
        self.data_updated.emit(stock_code, data)
    
    def _on_signal_trigger(self, signal_data: Dict[str, Any]):
        """信号触发回调（后台线程）"""
        self.signal_triggered.emit(signal_data)
    
    def _on_alert_trigger(self, alert_data: Dict[str, Any]):
        """预警触发回调（后台线程）"""
        self.alert_triggered.emit(alert_data)
    
    def on_data_updated(self, stock_code: str, data: pd.DataFrame):
        """数据更新槽函数（UI线程）"""
        if data.empty:
            return
        
        # 更新监控列表
        for row in range(self.stock_list.rowCount()):
            if self.stock_list.item(row, 0).text() == stock_code:
                # 获取最新数据
                latest = data.iloc[-1]
                price = float(latest['close'])
                
                # 计算涨跌幅
                if len(data) >= 2:
                    prev_close = float(data.iloc[-2]['close'])
                    change_pct = (price - prev_close) / prev_close * 100
                else:
                    change_pct = 0
                
                # 更新表格
                price_item = QTableWidgetItem(f"{price:.2f}")
                change_item = QTableWidgetItem(f"{change_pct:+.2f}")
                time_item = QTableWidgetItem(datetime.now().strftime('%H:%M:%S'))
                
                # 设置涨跌颜色
                if change_pct > 0:
                    change_item.setForeground(QColor('red'))
                elif change_pct < 0:
                    change_item.setForeground(QColor('green'))
                
                self.stock_list.setItem(row, 1, price_item)
                self.stock_list.setItem(row, 2, change_item)
                self.stock_list.setItem(row, 5, time_item)
                
                break
    
    def on_signal_triggered(self, signal_data: Dict[str, Any]):
        """信号触发槽函数（UI线程）"""
        stock_code = signal_data['stock_code']
        strategy_name = signal_data['strategy_name']
        signal = signal_data['signal']
        price = signal_data['price']
        time = signal_data['time']
        
        # 更新监控列表的信号列
        for row in range(self.stock_list.rowCount()):
            if (self.stock_list.item(row, 0).text() == stock_code and
                self.stock_list.item(row, 3).text() == strategy_name):
                
                signal_item = QTableWidgetItem(signal)
                
                # 设置信号颜色
                if signal == 'BUY':
                    signal_item.setForeground(QColor('red'))
                    signal_item.setBackground(QColor(255, 200, 200))
                elif signal == 'SELL':
                    signal_item.setForeground(QColor('green'))
                    signal_item.setBackground(QColor(200, 255, 200))
                
                self.stock_list.setItem(row, 4, signal_item)
                break
        
        # 添加到信号日志
        log_text = f"[{time}] {stock_code} - {strategy_name} - {signal} @ {price:.2f}"
        color = 'red' if signal == 'BUY' else 'green'
        self.append_to_log(self.signal_log, log_text, color)
        
        logger.info(f"信号显示: {log_text}")
    
    def on_alert_triggered(self, alert_data: Dict[str, Any]):
        """预警触发槽函数（UI线程）"""
        rule_name = alert_data['rule_name']
        time = alert_data['time']
        data = alert_data['data']
        
        # 构建日志文本
        if 'price' in data:
            log_text = f"[{time}] 🔔 {rule_name} - 价格: {data['price']:.2f}"
        else:
            log_text = f"[{time}] 🔔 {rule_name} - 信号: {data.get('signal', 'N/A')}"
        
        # 添加到预警日志
        self.append_to_log(self.alert_log, log_text, 'red')
        
        # 声音提醒
        if self.sound_alert_check.isChecked():
            self.play_alert_sound()
        
        logger.warning(f"预警显示: {log_text}")
    
    def append_to_log(self, text_edit: TextEdit, message: str, color: str = 'black'):
        """添加日志"""
        text_edit.append(f'<span style="color: {color};">{message}</span>')
        
        # 滚动到底部
        text_edit.verticalScrollBar().setValue(
            text_edit.verticalScrollBar().maximum()
        )
    
    def play_alert_sound(self):
        """播放预警声音"""
        try:
            # Windows系统提示音
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)
        except:
            # 其他系统
            print('\a')  # 系统蜂鸣声
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.is_monitoring:
            self.stop_monitoring()
        event.accept()
