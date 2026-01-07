"""
回测分析面板
用于执行策略回测并显示分析结果
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QSpinBox, QDoubleSpinBox, QFormLayout,
                             QMessageBox, QTableWidgetItem,
                             QProgressBar, QSplitter, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from qfluentwidgets import (PushButton, LineEdit, TextEdit, ComboBox, DateEdit,
                            PrimaryPushButton, ProgressBar as FluentProgressBar, TableWidget)
import logging
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.theme_manager import ThemeManager
from business.backtest_engine import BacktestEngine
from business.data_service import get_data_service
from core.strategy_base import StrategyFactory
from ui.chart_widget import BacktestChartWidget

logger = logging.getLogger(__name__)


class BacktestThread(QThread):
    """回测线程"""
    
    finished = pyqtSignal(object)  # 回测完成信号
    error = pyqtSignal(str)  # 错误信号
    progress = pyqtSignal(str)  # 进度信号
    
    def __init__(self, engine, data_service, stock_code, start_date, end_date, 
                 strategy_name, strategy_params):
        super().__init__()
        self.engine = engine
        self.data_service = data_service
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params
    
    def run(self):
        """执行回测"""
        try:
            self.progress.emit("正在获取数据...")
            
            # 获取数据
            data = self.data_service.get_stock_data(
                self.stock_code,
                self.start_date,
                self.end_date
            )
            
            if data is None or data.empty:
                self.error.emit(f"无法获取股票 {self.stock_code} 的数据")
                return
            
            self.progress.emit(f"获取到 {len(data)} 条数据")
            
            # 添加数据到回测引擎
            self.engine.add_data(data, self.stock_code)
            
            self.progress.emit("正在创建策略...")
            
            # 创建策略
            strategy = StrategyFactory.create_strategy(
                self.strategy_name,
                self.strategy_params
            )
            
            if strategy is None:
                self.error.emit(f"无法创建策略: {self.strategy_name}")
                return
            
            # 添加策略
            self.engine.add_strategy(strategy)
            
            self.progress.emit("正在执行回测...")
            
            # 运行回测
            result_dict = self.engine.run()
            
            # 在result_dict中添加原始数据，用于K线图绘制
            result_dict['ohlc_data'] = data
            result_dict['stock_code'] = self.stock_code
            
            # 转换为BacktestResult对象
            from business.backtest_engine import BacktestResult
            result = BacktestResult(result_dict)
            
            self.progress.emit("回测完成！")
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"回测执行失败: {str(e)}", exc_info=True)
            self.error.emit(f"回测执行失败: {str(e)}")


class BacktestPanel(QWidget):
    """回测分析面板"""
    
    def __init__(self, config: dict = None):
        """
        初始化回测分析面板
        :param config: 配置字典（可选）
        """
        super().__init__()
        
        self.config = config
        
        # 使用全局数据服务
        try:
            self.data_service = get_data_service()
            logger.info("✅ 回测面板已连接到全局数据服务")
        except Exception as e:
            logger.error(f"❌ 回测面板连接数据服务失败: {e}")
            self.data_service = None
        
        self.backtest_thread = None
        
        self.init_ui()
        
        logger.info("回测分析面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 创建水平分割器（左右布局）
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：配置区域
        config_panel = self.create_config_panel()
        splitter.addWidget(config_panel)
        
        # 右侧：结果显示区域
        result_panel = self.create_result_panel()
        splitter.addWidget(result_panel)
        
        # 设置初始大小比例 (左:右 = 1:2)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
    
    def create_config_panel(self):
        """创建配置面板"""
        group = QGroupBox("回测配置")
        layout = QVBoxLayout()
        
        # 使用FormLayout使配置更紧凑
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        # 股票代码
        self.stock_code_input = LineEdit()
        self.stock_code_input.setText("000001")
        form_layout.addRow("股票代码:", self.stock_code_input)
        
        # 开始日期
        self.start_date = DateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("开始日期:", self.start_date)
        
        # 结束日期
        self.end_date = DateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("结束日期:", self.end_date)
        
        layout.addLayout(form_layout)
        
        # 分隔线
        layout.addSpacing(10)
        
        # 策略配置
        strategy_form = QFormLayout()
        strategy_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        strategy_form.setLabelAlignment(Qt.AlignRight)
        
        self.strategy_combo = ComboBox()
        
        # 动态加载所有可用策略
        from ui.strategy_panel import StrategyPanel
        available_strategies = StrategyFactory.get_builtin_strategies()
        
        for strategy_name in available_strategies:
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
            # 添加显示名称，同时保存策略代码名作为数据
            self.strategy_combo.addItem(display_name, strategy_name)
        
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_changed)
        strategy_form.addRow("选择策略:", self.strategy_combo)
        
        layout.addLayout(strategy_form)
        
        # 策略参数
        layout.addSpacing(10)
        self.params_layout = QFormLayout()
        self.params_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.params_layout.setLabelAlignment(Qt.AlignRight)
        layout.addLayout(self.params_layout)
        
        # 初始化MA策略参数
        self.param_widgets = {}
        self.load_ma_params()
        
        # 回测参数
        layout.addSpacing(10)
        backtest_params_layout = QFormLayout()
        backtest_params_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        backtest_params_layout.setLabelAlignment(Qt.AlignRight)
        
        self.initial_cash = QDoubleSpinBox()
        self.initial_cash.setRange(1000, 10000000)
        self.initial_cash.setValue(100000)
        self.initial_cash.setDecimals(2)
        backtest_params_layout.addRow("初始资金:", self.initial_cash)
        
        self.commission = QDoubleSpinBox()
        self.commission.setRange(0, 1)
        self.commission.setValue(0.001)
        self.commission.setDecimals(4)
        self.commission.setSingleStep(0.0001)
        backtest_params_layout.addRow("手续费率:", self.commission)
        
        layout.addLayout(backtest_params_layout)
        
        # 按钮区域
        layout.addSpacing(15)
        btn_layout = QVBoxLayout()
        
        self.run_btn = PrimaryPushButton("🚀 开始回测")
        self.run_btn.clicked.connect(self.run_backtest)
        btn_layout.addWidget(self.run_btn)
        
        self.stop_btn = PushButton("⏹ 停止")
        self.stop_btn.clicked.connect(self.stop_backtest)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.export_btn = PushButton("📊 导出报告")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)
        
        layout.addLayout(btn_layout)
        
        # 进度条
        layout.addSpacing(10)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
        
        group.setLayout(layout)
        return group
    
    def create_result_panel(self):
        """创建结果显示面板"""
        group = QGroupBox("回测结果")
        layout = QVBoxLayout()
        
        # 创建选项卡
        result_tabs = QTabWidget()
        result_tabs.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 第一个选项卡：数据摘要
        summary_widget = QWidget()
        summary_widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        summary_layout = QVBoxLayout(summary_widget)
        
        # 使用表格显示关键指标，更清晰
        metrics_table = TableWidget()
        metrics_table.setRowCount(4)
        metrics_table.setColumnCount(4)
        metrics_table.setMaximumHeight(150)
        metrics_table.horizontalHeader().setVisible(False)
        metrics_table.verticalHeader().setVisible(False)
        metrics_table.setShowGrid(True)
        
        # 设置列宽 - 增加宽度以显示完整文字
        metrics_table.setColumnWidth(0, 110)  # 标签列
        metrics_table.setColumnWidth(1, 140)  # 值列
        metrics_table.setColumnWidth(2, 110)  # 标签列
        metrics_table.setColumnWidth(3, 140)  # 值列
        
        # 第一行
        metrics_table.setItem(0, 0, QTableWidgetItem("总收益率"))
        self.total_return_label = QTableWidgetItem("--")
        metrics_table.setItem(0, 1, self.total_return_label)
        metrics_table.setItem(0, 2, QTableWidgetItem("总交易次数"))
        self.total_trades_label = QTableWidgetItem("--")
        metrics_table.setItem(0, 3, self.total_trades_label)
        
        # 第二行
        metrics_table.setItem(1, 0, QTableWidgetItem("年化收益率"))
        self.annual_return_label = QTableWidgetItem("--")
        metrics_table.setItem(1, 1, self.annual_return_label)
        metrics_table.setItem(1, 2, QTableWidgetItem("胜率"))
        self.win_rate_label = QTableWidgetItem("--")
        metrics_table.setItem(1, 3, self.win_rate_label)
        
        # 第三行
        metrics_table.setItem(2, 0, QTableWidgetItem("夏普比率"))
        self.sharpe_label = QTableWidgetItem("--")
        metrics_table.setItem(2, 1, self.sharpe_label)
        metrics_table.setItem(2, 2, QTableWidgetItem("盈亏比"))
        self.profit_factor_label = QTableWidgetItem("--")
        metrics_table.setItem(2, 3, self.profit_factor_label)
        
        # 第四行
        metrics_table.setItem(3, 0, QTableWidgetItem("最大回撤"))
        self.max_drawdown_label = QTableWidgetItem("--")
        metrics_table.setItem(3, 1, self.max_drawdown_label)
        metrics_table.setItem(3, 2, QTableWidgetItem(""))
        metrics_table.setItem(3, 3, QTableWidgetItem(""))
        
        summary_layout.addWidget(metrics_table)
        
        # 详细结果
        self.result_text = TextEdit()
        self.result_text.setReadOnly(True)
        summary_layout.addWidget(self.result_text)
        
        result_tabs.addTab(summary_widget, "📊 摘要")
        
        # 第二个选项卡：图表展示
        self.chart_widget = BacktestChartWidget()
        result_tabs.addTab(self.chart_widget, "📈 图表")
        
        # 第三个选项卡：K线图（新增）
        try:
            from ui.kline_widget import EnhancedKLineWidget
            self.kline_widget = EnhancedKLineWidget()
            result_tabs.addTab(self.kline_widget, "📊 K线")
        except ImportError as e:
            logger.warning(f"K线图组件加载失败: {e}")
            self.kline_widget = None
        
        layout.addWidget(result_tabs)
        
        group.setLayout(layout)
        return group
    
    def on_strategy_changed(self, index):
        """策略切换事件"""
        if index == 0:
            self.load_ma_params()
        elif index == 1:
            self.load_rsi_params()
    
    def load_ma_params(self):
        """加载MA策略参数"""
        self.clear_params_layout()
        
        short_period = QSpinBox()
        short_period.setRange(1, 100)
        short_period.setValue(5)
        self.param_widgets['short_period'] = short_period
        self.params_layout.addRow("短期均线:", short_period)
        
        long_period = QSpinBox()
        long_period.setRange(1, 200)
        long_period.setValue(20)
        self.param_widgets['long_period'] = long_period
        self.params_layout.addRow("长期均线:", long_period)
    
    def load_rsi_params(self):
        """加载RSI策略参数"""
        self.clear_params_layout()
        
        period = QSpinBox()
        period.setRange(1, 100)
        period.setValue(14)
        self.param_widgets['period'] = period
        self.params_layout.addRow("RSI周期:", period)
        
        oversold = QSpinBox()
        oversold.setRange(1, 50)
        oversold.setValue(30)
        self.param_widgets['oversold'] = oversold
        self.params_layout.addRow("超卖阈值:", oversold)
        
        overbought = QSpinBox()
        overbought.setRange(50, 100)
        overbought.setValue(70)
        self.param_widgets['overbought'] = overbought
        self.params_layout.addRow("超买阈值:", overbought)
    
    def clear_params_layout(self):
        """清空参数布局"""
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.param_widgets.clear()
    
    def get_strategy_params(self):
        """获取策略参数"""
        params = {}
        for key, widget in self.param_widgets.items():
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                params[key] = widget.value()
        return params
    
    def run_backtest(self):
        """执行回测"""
        # 检查数据服务
        if self.data_service is None:
            QMessageBox.warning(self, "警告", "数据服务未初始化，请检查配置！")
            return
        
        # 验证输入
        stock_code = self.stock_code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码！")
            return
        
        # 获取策略名称（通过显示名称反向查找代码名）
        strategy_text = self.strategy_combo.currentText()
        
        # 通过显示名称反向查找策略代码名
        from ui.strategy_panel import StrategyPanel
        strategy_name = None
        for code_name, display_name in StrategyPanel.STRATEGY_DISPLAY_NAMES.items():
            if display_name == strategy_text:
                strategy_name = code_name
                break
        
        if not strategy_name:
            logger.error(f"无法找到策略代码名，显示名称: {strategy_text}")
            QMessageBox.warning(self, "错误", f"无法识别策略: {strategy_text}")
            return
        
        logger.info(f"选择的策略: 显示名={strategy_text}, 代码名={strategy_name}")
        
        # 获取参数
        strategy_params = self.get_strategy_params()
        
        # 创建回测配置
        backtest_config = {
            'initial_cash': self.initial_cash.value(),
            'commission': self.commission.value(),
            'stamp_duty': 0.001,
            'slippage': 0.001
        }
        
        # 创建回测引擎
        engine = BacktestEngine(backtest_config)
        
        # 获取日期
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # 创建并启动回测线程
        self.backtest_thread = BacktestThread(
            engine=engine,
            data_service=self.data_service,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            strategy_name=strategy_name,
            strategy_params=strategy_params
        )
        
        self.backtest_thread.finished.connect(self.on_backtest_finished)
        self.backtest_thread.error.connect(self.on_backtest_error)
        self.backtest_thread.progress.connect(self.on_backtest_progress)
        
        # 更新UI状态
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.status_label.setText("正在准备回测...")
        
        # 清空结果
        self.clear_results()
        
        # 启动线程
        self.backtest_thread.start()
    
    def stop_backtest(self):
        """停止回测"""
        if self.backtest_thread and self.backtest_thread.isRunning():
            self.backtest_thread.terminate()
            self.backtest_thread.wait()
            self.status_label.setText("回测已停止")
            self.reset_ui_state()
    
    def on_backtest_progress(self, message):
        """回测进度更新"""
        self.status_label.setText(message)
    
    def on_backtest_finished(self, result):
        """回测完成"""
        self.reset_ui_state()
        
        if result is None:
            QMessageBox.warning(self, "警告", "回测返回空结果")
            return
        
        # 显示结果
        self.display_results(result)
        self.export_btn.setEnabled(True)
    
    def on_backtest_error(self, error_msg):
        """回测错误"""
        self.reset_ui_state()
        QMessageBox.critical(self, "错误", f"回测失败：\n{error_msg}")
    
    def display_results(self, result):
        """显示回测结果"""
        try:
            logger.info("开始显示回测结果")
            
            # 更新关键指标
            logger.info(f"总收益率: {result.total_return}")
            self.total_return_label.setText(f"{result.total_return:.2f}%")
            
            logger.info(f"年化收益率: {result.annual_return}")
            self.annual_return_label.setText(f"{result.annual_return:.2f}%")
            
            sharpe_value = result.sharpe_ratio if result.sharpe_ratio is not None else 0.0
            logger.info(f"夏普比率: {sharpe_value}")
            self.sharpe_label.setText(f"{sharpe_value:.2f}")
            
            logger.info(f"最大回撤: {result.max_drawdown}")
            self.max_drawdown_label.setText(f"{result.max_drawdown:.2f}%")
            
            # 更新交易统计
            logger.info(f"总交易次数: {result.total_trades}")
            self.total_trades_label.setText(f"{result.total_trades}")
            
            logger.info(f"胜率: {result.win_rate}")
            self.win_rate_label.setText(f"{result.win_rate:.2f}%")
            
            logger.info(f"盈亏比: {result.profit_factor}")
            self.profit_factor_label.setText(f"{result.profit_factor:.2f}")
            
            # 显示详细信息
            logger.info("生成回测摘要")
            summary = result.get_summary()
            self.result_text.setPlainText(summary)
            
            # 绘制图表
            logger.info("准备绘制图表")
            try:
                self.chart_widget.plot_all(result)
                logger.info("回测图表绘制完成")
            except Exception as e:
                logger.error(f"绘制图表失败: {e}", exc_info=True)
                QMessageBox.warning(self, "警告", f"图表绘制失败：{str(e)}\n其他结果已正常显示")
            
            # 绘制K线图（如果可用）
            if hasattr(self, 'kline_widget') and self.kline_widget is not None:
                try:
                    logger.info("准备绘制K线图")
                    
                    # 从回测结果中获取OHLC数据
                    if hasattr(result, 'ohlc_data') and result.ohlc_data is not None:
                        ohlc_data = result.ohlc_data.copy()
                        
                        # 确保数据格式正确
                        if 'trade_date' in ohlc_data.columns:
                            ohlc_data = ohlc_data.set_index('trade_date')
                        
                        # 确保索引是datetime类型
                        if not isinstance(ohlc_data.index, pd.DatetimeIndex):
                            ohlc_data.index = pd.to_datetime(ohlc_data.index)
                        
                        # 重命名列以匹配K线图需要的格式
                        column_mapping = {
                            'vol': 'volume',
                            'amount': 'amount'
                        }
                        ohlc_data = ohlc_data.rename(columns=column_mapping)
                        
                        # 提取交易记录
                        trades = None
                        if hasattr(result, 'trade_records') and result.trade_records:
                            trades = result.trade_records
                            logger.info(f"提取到 {len(trades)} 条交易记录")
                        
                        # 设置数据到K线图
                        self.kline_widget.set_data(ohlc_data, trades)
                        logger.info(f"K线图数据设置完成，共 {len(ohlc_data)} 条记录")
                    else:
                        logger.warning("回测结果中没有OHLC数据")
                        
                except Exception as e:
                    logger.error(f"绘制K线图失败: {e}", exc_info=True)
            
            self.status_label.setText("回测完成！")
            logger.info("回测结果显示完成")
            
        except Exception as e:
            logger.error(f"显示回测结果失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"显示结果失败：{str(e)}")
    
    def clear_results(self):
        """清空结果显示"""
        self.total_return_label.setText("--")
        self.annual_return_label.setText("--")
        self.sharpe_label.setText("--")
        self.max_drawdown_label.setText("--")
        self.total_trades_label.setText("--")
        self.win_rate_label.setText("--")
        self.profit_factor_label.setText("--")
        self.result_text.clear()
    
    def reset_ui_state(self):
        """重置UI状态"""
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    def export_report(self):
        """导出报告"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存回测报告",
            f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.toPlainText())
                
                QMessageBox.information(self, "成功", f"报告已导出到：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：\n{str(e)}")
