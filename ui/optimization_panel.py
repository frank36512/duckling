"""
参数优化面板
提供参数优化的用户界面
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidgetItem, QHeaderView,
    QGroupBox, QSpinBox, QDoubleSpinBox, QProgressBar,
    QTabWidget, QSplitter, QFormLayout, QScrollArea,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont
from qfluentwidgets import (PushButton, LineEdit, ComboBox, DateEdit,
                            PrimaryPushButton, TextEdit, TableWidget)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from ui.theme_manager import ThemeManager
import pandas as pd
from typing import Dict, Any, Optional

from business.data_manager import DataManager
from business.parameter_optimizer import GridSearch, RandomSearch, WalkForwardAnalysis
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)

# 参数中文名称映射
PARAM_DISPLAY_NAMES = {
    'short_period': '短期周期',
    'long_period': '长期周期',
    'rsi_period': 'RSI周期',
    'oversold_level': '超卖阈值',
    'overbought_level': '超买阈值',
    'fast_period': '快线周期',
    'slow_period': '慢线周期',
    'signal_period': '信号周期',
    'ma_short': '短期均线',
    'ma_mid': '中期均线',
    'ma_long': '长期均线',
    'lookback_period': '回看周期',
    'prediction_threshold': '预测阈值',
    'max_holding_period': '最大持仓期',
    'sequence_length': '序列长度',
    'confidence_threshold': '置信阈值',
    'stop_loss': '止损比例',
    'take_profit': '止盈比例',
    'n_estimators': '估计器数量',
    'max_depth': '最大深度',
    'learning_rate': '学习率',
}

# 默认策略参数配置
STRATEGY_PARAMS = {
    'MA_CrossOver': {
        'short_period': {'type': 'int', 'min': 3, 'max': 20, 'default': 5, 'step': 1},
        'long_period': {'type': 'int', 'min': 10, 'max': 60, 'default': 20, 'step': 5},
    },
    'RSI_OverboughtOversold': {
        'rsi_period': {'type': 'int', 'min': 7, 'max': 21, 'default': 14, 'step': 1},
        'oversold_level': {'type': 'int', 'min': 20, 'max': 40, 'default': 30, 'step': 5},
        'overbought_level': {'type': 'int', 'min': 60, 'max': 80, 'default': 70, 'step': 5},
    },
    'MACD': {
        'fast_period': {'type': 'int', 'min': 8, 'max': 16, 'default': 12, 'step': 2},
        'slow_period': {'type': 'int', 'min': 20, 'max': 30, 'default': 26, 'step': 2},
        'signal_period': {'type': 'int', 'min': 7, 'max': 12, 'default': 9, 'step': 1},
    },
    'BollingerBands': {
        'period': {'type': 'int', 'min': 10, 'max': 30, 'default': 20, 'step': 5},
        'devfactor': {'type': 'float', 'min': 1.5, 'max': 3.0, 'default': 2.0, 'step': 0.5},
    },
    'KDJ': {
        'period': {'type': 'int', 'min': 7, 'max': 14, 'default': 9, 'step': 1},
        'period_dfast': {'type': 'int', 'min': 2, 'max': 5, 'default': 3, 'step': 1},
        'period_dslow': {'type': 'int', 'min': 2, 'max': 5, 'default': 3, 'step': 1},
    },
    'MA_Volume': {
        'short_period': {'type': 'int', 'min': 3, 'max': 15, 'default': 5, 'step': 1},
        'long_period': {'type': 'int', 'min': 15, 'max': 60, 'default': 20, 'step': 5},
        'volume_period': {'type': 'int', 'min': 10, 'max': 30, 'default': 20, 'step': 5},
        'volume_factor': {'type': 'float', 'min': 1.2, 'max': 3.0, 'default': 1.5, 'step': 0.1},
        'stop_loss': {'type': 'float', 'min': 0.03, 'max': 0.15, 'default': 0.05, 'step': 0.01},
    },
    'ATR_Breakout': {
        'atr_period': {'type': 'int', 'min': 10, 'max': 20, 'default': 14, 'step': 1},
        'atr_multiplier': {'type': 'float', 'min': 1.5, 'max': 3.5, 'default': 2.0, 'step': 0.5},
        'stop_loss_atr': {'type': 'float', 'min': 1.0, 'max': 3.0, 'default': 1.5, 'step': 0.5},
    },
    'CCI': {
        'cci_period': {'type': 'int', 'min': 14, 'max': 28, 'default': 20, 'step': 2},
        'oversold': {'type': 'int', 'min': -150, 'max': -50, 'default': -100, 'step': 10},
        'overbought': {'type': 'int', 'min': 50, 'max': 150, 'default': 100, 'step': 10},
    },
    'TurtleTrading': {
        'entry_period': {'type': 'int', 'min': 15, 'max': 25, 'default': 20, 'step': 5},
        'exit_period': {'type': 'int', 'min': 5, 'max': 15, 'default': 10, 'step': 5},
        'atr_period': {'type': 'int', 'min': 10, 'max': 20, 'default': 14, 'step': 2},
        'risk_per_trade': {'type': 'float', 'min': 0.01, 'max': 0.03, 'default': 0.02, 'step': 0.005},
    },
    'GridTrading': {
        'grid_size': {'type': 'float', 'min': 0.01, 'max': 0.05, 'default': 0.02, 'step': 0.005},
        'num_grids': {'type': 'int', 'min': 3, 'max': 10, 'default': 5, 'step': 1},
        'base_position_pct': {'type': 'float', 'min': 0.1, 'max': 0.3, 'default': 0.2, 'step': 0.05},
    },
    'WilliamsR': {
        'period': {'type': 'int', 'min': 10, 'max': 20, 'default': 14, 'step': 2},
        'oversold': {'type': 'int', 'min': -90, 'max': -70, 'default': -80, 'step': 5},
        'overbought': {'type': 'int', 'min': -30, 'max': -10, 'default': -20, 'step': 5},
    },
    'DMI': {
        'period': {'type': 'int', 'min': 10, 'max': 20, 'default': 14, 'step': 2},
        'adx_threshold': {'type': 'int', 'min': 20, 'max': 30, 'default': 25, 'step': 5},
    },
    'VWAP': {
        'period': {'type': 'int', 'min': 10, 'max': 30, 'default': 20, 'step': 5},
        'deviation_pct': {'type': 'float', 'min': 0.01, 'max': 0.05, 'default': 0.02, 'step': 0.005},
    },
    'OBV': {
        'sma_period': {'type': 'int', 'min': 10, 'max': 30, 'default': 20, 'step': 5},
    },
    'TripleScreen': {
        'long_period': {'type': 'int', 'min': 20, 'max': 30, 'default': 26, 'step': 2},
        'mid_period': {'type': 'int', 'min': 10, 'max': 16, 'default': 13, 'step': 1},
        'rsi_period': {'type': 'int', 'min': 10, 'max': 18, 'default': 14, 'step': 2},
    },
    'MultiFactor': {
        'ma_short': {'type': 'int', 'min': 3, 'max': 10, 'default': 5, 'step': 1},
        'ma_mid': {'type': 'int', 'min': 8, 'max': 15, 'default': 10, 'step': 1},
        'ma_long': {'type': 'int', 'min': 15, 'max': 25, 'default': 20, 'step': 5},
        'rsi_period': {'type': 'int', 'min': 10, 'max': 18, 'default': 14, 'step': 2},
    },
    # 机器学习策略 - 参数优化配置
    'RandomForest': {
        'lookback_period': {'type': 'int', 'min': 10, 'max': 30, 'default': 20, 'step': 5},
        'prediction_threshold': {'type': 'float', 'min': 0.5, 'max': 0.7, 'default': 0.6, 'step': 0.05},
        'max_holding_period': {'type': 'int', 'min': 5, 'max': 15, 'default': 10, 'step': 5},
    },
    'LSTM': {
        'sequence_length': {'type': 'int', 'min': 30, 'max': 90, 'default': 60, 'step': 10},
        'confidence_threshold': {'type': 'float', 'min': 0.01, 'max': 0.05, 'default': 0.02, 'step': 0.01},
        'stop_loss': {'type': 'float', 'min': 0.02, 'max': 0.05, 'default': 0.03, 'step': 0.01},
        'take_profit': {'type': 'float', 'min': 0.03, 'max': 0.08, 'default': 0.05, 'step': 0.01},
    },
    'XGBoost': {
        'n_estimators': {'type': 'int', 'min': 50, 'max': 200, 'default': 100, 'step': 50},
        'max_depth': {'type': 'int', 'min': 3, 'max': 7, 'default': 5, 'step': 1},
        'learning_rate': {'type': 'float', 'min': 0.05, 'max': 0.2, 'default': 0.1, 'step': 0.05},
        'prediction_threshold': {'type': 'float', 'min': 0.5, 'max': 0.7, 'default': 0.6, 'step': 0.05},
    },
}


class MLTrainingThread(QThread):
    """机器学习模型训练线程"""
    
    finished = pyqtSignal(dict)  # 训练结果
    error = pyqtSignal(str)      # 错误信息
    progress = pyqtSignal(str)   # 进度更新
    
    def __init__(
        self,
        strategy_name: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        config: Dict[str, Any],
        data_manager
    ):
        super().__init__()
        self.strategy_name = strategy_name
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.config = config
        self.data_manager = data_manager
        self._is_running = True
    
    def run(self):
        """执行训练"""
        try:
            from business.ml_trainer import create_trainer
            
            # 获取训练数据
            self.progress.emit("📥 正在加载训练数据...")
            data = self.data_manager.get_stock_data(
                self.stock_code,
                self.start_date,
                self.end_date
            )
            
            if data is None or len(data) < 100:
                self.error.emit("❌ 数据不足，需要至少100个交易日数据！")
                return
            
            self.progress.emit(f"✅ 数据加载完成，共 {len(data)} 条记录")
            
            # 创建训练器
            self.progress.emit(f"🔧 初始化 {self.strategy_name} 训练器...")
            trainer = create_trainer(self.strategy_name, self.config)
            
            # 开始训练
            results = trainer.train(
                data,
                progress_callback=lambda msg: self.progress.emit(msg) if self._is_running else None
            )
            
            if not self._is_running:
                self.error.emit("⏹ 训练已停止")
                return
            
            # 保存模型
            self.progress.emit("💾 正在保存模型...")
            model_path = trainer.save_model(
                self.stock_code,
                metadata={
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'config': self.config,
                    'results': results
                }
            )
            
            results['model_path'] = model_path
            results['stock_code'] = self.stock_code
            
            self.progress.emit(f"✅ 模型已保存: {model_path}")
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            error_msg = f"训练失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.error.emit(error_msg)
    
    def stop(self):
        """停止训练"""
        self._is_running = False


class OptimizationThread(QThread):
    """后台优化线程"""
    
    finished = pyqtSignal(list)  # 优化结果
    error = pyqtSignal(str)      # 错误信息
    progress = pyqtSignal(str)   # 进度更新
    
    def __init__(
        self,
        optimizer,
        method: str,
        strategy_name: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        param_config: Dict[str, Any]
    ):
        super().__init__()
        self.optimizer = optimizer
        self.method = method
        self.strategy_name = strategy_name
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.param_config = param_config
    
    def run(self):
        """执行优化"""
        try:
            if self.method == 'grid':
                # 网格搜索
                results = self.optimizer.optimize(
                    self.strategy_name,
                    self.stock_code,
                    self.start_date,
                    self.end_date,
                    self.param_config,
                    max_workers=4,
                    progress_callback=lambda msg: self.progress.emit(msg)
                )
            else:
                # 随机搜索
                n_iter = self.param_config.get('n_iter', 100)
                param_distributions = {
                    k: (v['min'], v['max'])
                    for k, v in self.param_config.items()
                    if k != 'n_iter'
                }
                results = self.optimizer.optimize(
                    self.strategy_name,
                    self.stock_code,
                    self.start_date,
                    self.end_date,
                    param_distributions,
                    n_iter=n_iter,
                    max_workers=4,
                    progress_callback=lambda msg: self.progress.emit(msg)
                )
            
            self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"优化执行失败: {e}", exc_info=True)
            self.error.emit(str(e))


class OptimizationPanel(QWidget):
    """参数优化面板"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.data_manager = DataManager(config)
        self.optimizer = None
        self.optimization_thread = None
        self.results = []
        
        self.init_ui()
        logger.info("参数优化面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：配置区域
        left_widget = self.create_config_panel()
        left_widget.setMinimumWidth(350)  # 设置最小宽度确保日期选择器显示完整
        left_widget.setMaximumWidth(500)  # 限制最大宽度
        splitter.addWidget(left_widget)
        
        # 右侧：结果展示区域
        right_widget = self.create_results_panel()
        splitter.addWidget(right_widget)
        
        # 设置分割比例（左侧配置区稍窄，右侧结果区更宽）
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def create_config_panel(self) -> QWidget:
        """创建配置面板"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout()
        
        # 基本配置
        basic_group = QGroupBox("基本配置")
        basic_layout = QFormLayout()
        
        # 股票代码
        self.stock_code_input = LineEdit()
        self.stock_code_input.setPlaceholderText("例如: 000001")
        basic_layout.addRow("股票代码:", self.stock_code_input)
        
        # 日期范围
        self.start_date_input = DateEdit()
        self.start_date_input.setDate(QDate(2024, 1, 1))
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setMinimumWidth(160)
        self.start_date_input.setMaximumWidth(200)
        basic_layout.addRow("开始日期:", self.start_date_input)
        
        self.end_date_input = DateEdit()
        self.end_date_input.setDate(QDate(2024, 12, 31))
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setMinimumWidth(160)
        self.end_date_input.setMaximumWidth(200)
        basic_layout.addRow("结束日期:", self.end_date_input)
        
        # 策略选择
        self.strategy_combo = ComboBox()
        from ui.strategy_panel import StrategyPanel
        strategies = StrategyFactory.get_builtin_strategies()
        for strategy_name in strategies:
            if strategy_name in STRATEGY_PARAMS:
                # 显示中文名称，存储英文代码
                display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
                self.strategy_combo.addItem(display_name, strategy_name)
        # 使用currentIndexChanged信号，通过索引获取userData
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_combo_changed)
        basic_layout.addRow("选择策略:", self.strategy_combo)
        
        # 优化方法
        self.method_combo = ComboBox()
        self.method_combo.addItems(['网格搜索', '随机搜索'])
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        self.method_combo.setMinimumWidth(150)
        basic_layout.addRow("优化方法:", self.method_combo)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 参数配置（滚动区域）
        self.param_group = QGroupBox("参数配置")
        self.param_scroll = QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_widget = QWidget()
        self.param_layout = QFormLayout()
        self.param_widget.setLayout(self.param_layout)
        self.param_scroll.setWidget(self.param_widget)
        
        param_group_layout = QVBoxLayout()
        param_group_layout.addWidget(self.param_scroll)
        self.param_group.setLayout(param_group_layout)
        layout.addWidget(self.param_group)
        
        # 随机搜索特有配置
        self.random_group = QGroupBox("随机搜索配置")
        random_layout = QFormLayout()
        
        self.n_iter_spin = QSpinBox()
        self.n_iter_spin.setRange(10, 1000)
        self.n_iter_spin.setValue(100)
        self.n_iter_spin.setSingleStep(10)
        random_layout.addRow("采样次数:", self.n_iter_spin)
        
        self.random_group.setLayout(random_layout)
        self.random_group.setVisible(False)
        layout.addWidget(self.random_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = PrimaryPushButton("🚀 开始优化")
        self.start_btn.clicked.connect(self.start_optimization)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = PushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_optimization)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        # 初始化参数配置（使用currentData获取英文策略名）
        initial_strategy = self.strategy_combo.currentData()
        if initial_strategy:
            self.on_strategy_changed(initial_strategy)
        
        return widget
    
    def create_results_panel(self) -> QWidget:
        """创建结果展示面板"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout()
        
        # 创建标签页
        self.result_tabs = QTabWidget()
        self.result_tabs.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.result_tabs.setMinimumWidth(600)  # 设置最小宽度，确保标签显示完整
        
        # 结果表格
        self.result_table = TableWidget()
        self.result_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.result_table.setSelectionBehavior(TableWidget.SelectRows)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_tabs.addTab(self.result_table, "📊 结果")
        
        # 根据主题设置figure背景色
        from qfluentwidgets import isDarkTheme
        fig_color = '#2b2b2b' if isDarkTheme() else '#fafafa'
        
        # 参数热力图
        heatmap_fig = Figure(figsize=(8, 6), facecolor=fig_color)
        self.heatmap_canvas = FigureCanvas(heatmap_fig)
        self.heatmap_canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.result_tabs.addTab(self.heatmap_canvas, "🔥 热力图")
        
        # 参数敏感度分析
        sensitivity_fig = Figure(figsize=(8, 6), facecolor=fig_color)
        self.sensitivity_canvas = FigureCanvas(sensitivity_fig)
        self.sensitivity_canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.result_tabs.addTab(self.sensitivity_canvas, "📈 敏感度")
        
        # 收益分布
        distribution_fig = Figure(figsize=(8, 6), facecolor=fig_color)
        self.distribution_canvas = FigureCanvas(distribution_fig)
        self.distribution_canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.result_tabs.addTab(self.distribution_canvas, "📉 分布")
        
        # 模型训练标签页（机器学习策略专用）
        ml_training_widget = self.create_ml_training_panel()
        self.result_tabs.addTab(ml_training_widget, "🤖 训练")
        
        layout.addWidget(self.result_tabs)
        widget.setLayout(layout)
        
        return widget
    
    def create_ml_training_panel(self) -> QWidget:
        """创建机器学习模型训练面板"""
        widget = QWidget()
        widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        layout = QVBoxLayout()
        
        # 说明文字
        info_text = """
            <h3>🤖 机器学习策略模型训练</h3>
            <p><b>当前支持的ML策略：</b></p>
            <ul>
            <li>🌲 <b>RandomForest</b> - 随机森林：使用多棵决策树进行集成学习</li>
            <li>🧠 <b>LSTM</b> - 长短期记忆网络：深度学习时间序列预测（需GPU加速）</li>
            <li>⚡ <b>XGBoost</b> - 梯度提升树：高效的梯度提升算法</li>
            </ul>
            <p><b>训练步骤：</b></p>
            <ol>
            <li>在左侧选择ML策略（RandomForest/LSTM/XGBoost）</li>
            <li>配置训练参数和数据范围</li>
            <li>点击下方"开始训练模型"按钮</li>
            <li>等待训练完成，模型会自动保存</li>
            <li>训练完成后可在回测中使用该模型</li>
            </ol>
            <p><b>⚠️ 注意事项：</b></p>
            <ul>
            <li>建议使用至少<b>1000个</b>交易日数据进行训练</li>
            <li>LSTM训练时间较长，建议使用GPU</li>
            <li>模型会保存在 <code>models/</code> 目录</li>
            <li>可以在策略配置中加载预训练模型</li>
            </ul>
        """
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 训练配置
        training_group = QGroupBox("训练配置")
        training_layout = QFormLayout()
        
        # 训练集比例
        self.train_ratio_spin = QDoubleSpinBox()
        self.train_ratio_spin.setRange(0.6, 0.9)
        self.train_ratio_spin.setValue(0.8)
        self.train_ratio_spin.setSingleStep(0.05)
        self.train_ratio_spin.setMinimumWidth(150)
        train_ratio_layout = QHBoxLayout()
        train_ratio_layout.addWidget(self.train_ratio_spin)
        train_info_label = QLabel("(80%训练, 20%测试)")
        train_ratio_layout.addWidget(train_info_label)
        train_ratio_layout.addStretch()
        training_layout.addRow("训练集比例:", train_ratio_layout)
        
        # 验证集比例
        self.val_ratio_spin = QDoubleSpinBox()
        self.val_ratio_spin.setRange(0.1, 0.3)
        self.val_ratio_spin.setValue(0.2)
        self.val_ratio_spin.setSingleStep(0.05)
        training_layout.addRow("验证集比例:", self.val_ratio_spin)
        
        # 特征工程选项
        self.feature_check = QLabel("✓ 自动特征工程（SMA, RSI, MACD等）")
        training_layout.addRow("特征:", self.feature_check)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        # 训练按钮和状态
        button_layout = QHBoxLayout()
        
        self.train_button = PrimaryPushButton("🚀 开始训练模型")
        self.train_button.clicked.connect(self.start_ml_training)
        button_layout.addWidget(self.train_button)
        
        self.train_stop_button = PushButton("⏹ 停止训练")
        self.train_stop_button.setEnabled(False)
        button_layout.addWidget(self.train_stop_button)
        
        layout.addLayout(button_layout)
        
        # 训练进度
        self.train_progress = QProgressBar()
        self.train_progress.setVisible(False)
        layout.addWidget(self.train_progress)
        
        # 训练日志
        self.train_log = TextEdit()
        self.train_log.setReadOnly(True)
        self.train_log.setMaximumHeight(200)
        self.train_log.setPlaceholderText("训练日志将在此显示...")
        layout.addWidget(self.train_log)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
    
    def start_ml_training(self):
        """开始机器学习模型训练"""
        strategy_name = self.strategy_combo.currentData()
        if not strategy_name:
            strategy_name = self.strategy_combo.currentText()
        
        # 检查是否为ML策略
        ml_strategies = ['RandomForest', 'LSTM', 'XGBoost']
        if strategy_name not in ml_strategies:
            QMessageBox.warning(
                self,
                "策略类型错误",
                f"当前选择的策略 '{strategy_name}' 不是机器学习策略！\n\n"
                f"请选择以下ML策略之一：\n"
                f"• RandomForest（随机森林）\n"
                f"• LSTM（深度学习）\n"
                f"• XGBoost（梯度提升）"
            )
            return
        
        # 获取训练数据
        stock_code = self.stock_code_input.text().strip()
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")
        
        if not stock_code or not start_date or not end_date:
            QMessageBox.warning(self, "输入错误", "请填写完整的股票代码和日期范围！")
            return
        
        # 检查是否有训练线程正在运行
        if hasattr(self, 'ml_training_thread') and self.ml_training_thread and self.ml_training_thread.isRunning():
            QMessageBox.warning(self, "训练中", "已有训练任务正在运行，请等待完成或停止当前任务！")
            return
        
        # 准备训练配置
        training_config = {
            'train_ratio': self.train_ratio_spin.value(),
            'val_ratio': self.val_ratio_spin.value()
        }
        
        # 添加策略特定参数（从参数优化配置中获取）
        if strategy_name in STRATEGY_PARAMS:
            params = STRATEGY_PARAMS[strategy_name]
            for param_name, param_config in params.items():
                # 使用默认值
                training_config[param_name] = param_config['default']
        
        # 清空训练日志
        self.train_log.clear()
        self.train_log.append(f"{'='*60}")
        self.train_log.append(f"🤖 开始训练 {strategy_name} 模型")
        self.train_log.append(f"{'='*60}")
        self.train_log.append(f"📊 股票代码: {stock_code}")
        self.train_log.append(f"📅 训练期间: {start_date} ~ {end_date}")
        self.train_log.append(f"📈 训练集比例: {training_config['train_ratio']:.0%}")
        self.train_log.append(f"📉 验证集比例: {training_config['val_ratio']:.0%}")
        self.train_log.append(f"⚙️  训练参数: {training_config}")
        self.train_log.append(f"")
        
        # 显示进度条
        self.train_progress.setVisible(True)
        self.train_progress.setValue(0)
        
        # 禁用训练按钮，启用停止按钮
        self.train_button.setEnabled(False)
        self.train_stop_button.setEnabled(True)
        
        # 创建并启动训练线程
        self.ml_training_thread = MLTrainingThread(
            strategy_name=strategy_name,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            config=training_config,
            data_manager=self.data_manager
        )
        
        # 连接信号
        self.ml_training_thread.progress.connect(self.on_training_progress)
        self.ml_training_thread.finished.connect(self.on_training_finished)
        self.ml_training_thread.error.connect(self.on_training_error)
        
        # 连接停止按钮
        self.train_stop_button.clicked.connect(self.stop_ml_training)
        
        # 启动线程
        self.ml_training_thread.start()
        
        self.train_log.append("🚀 训练线程已启动...")
    
    def stop_ml_training(self):
        """停止ML训练"""
        if hasattr(self, 'ml_training_thread') and self.ml_training_thread and self.ml_training_thread.isRunning():
            self.train_log.append("\n⏹ 正在停止训练...")
            self.ml_training_thread.stop()
            self.ml_training_thread.wait(3000)  # 等待最多3秒
            self.train_log.append("✅ 训练已停止")
            
            # 恢复按钮状态
            self.train_button.setEnabled(True)
            self.train_stop_button.setEnabled(False)
            self.train_progress.setVisible(False)
    
    def on_training_progress(self, message: str):
        """训练进度更新"""
        self.train_log.append(message)
        
        # 自动滚动到底部
        scrollbar = self.train_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # 更新进度条（简单的动画效果）
        current = self.train_progress.value()
        if current < 90:
            self.train_progress.setValue(current + 5)
    
    def on_training_finished(self, results: dict):
        """训练完成"""
        self.train_progress.setValue(100)
        
        self.train_log.append(f"\n{'='*60}")
        self.train_log.append(f"🎉 训练完成！")
        self.train_log.append(f"{'='*60}")
        self.train_log.append(f"\n� 最终评估结果:")
        
        # 显示测试集性能
        if 'test_metrics' in results:
            metrics = results['test_metrics']
            self.train_log.append(f"  ✓ 准确率:  {metrics['accuracy']*100:.2f}%")
            self.train_log.append(f"  ✓ 精确率:  {metrics['precision']*100:.2f}%")
            self.train_log.append(f"  ✓ 召回率:  {metrics['recall']*100:.2f}%")
            self.train_log.append(f"  ✓ F1分数:  {metrics['f1']*100:.2f}%")
        
        self.train_log.append(f"\n💾 模型文件: {results.get('model_path', 'N/A')}")
        self.train_log.append(f"\n✅ 现在可以在回测中使用该模型了！")
        
        # 恢复按钮状态
        self.train_button.setEnabled(True)
        self.train_stop_button.setEnabled(False)
        
        # 显示成功消息
        QMessageBox.information(
            self,
            "训练完成",
            f"模型训练成功完成！\n\n"
            f"测试集准确率: {results.get('test_metrics', {}).get('accuracy', 0)*100:.2f}%\n"
            f"模型已保存到: {results.get('model_path', 'N/A')}"
        )
    
    def on_training_error(self, error_msg: str):
        """训练错误"""
        self.train_log.append(f"\n❌ 错误:")
        self.train_log.append(error_msg)
        
        # 恢复按钮状态
        self.train_button.setEnabled(True)
        self.train_stop_button.setEnabled(False)
        self.train_progress.setVisible(False)
        
        # 显示错误消息
        QMessageBox.critical(self, "训练失败", f"模型训练失败:\n{error_msg}")
    
    def on_strategy_combo_changed(self, index: int):
        """策略组合框索引改变时的处理"""
        if index >= 0:
            strategy_name = self.strategy_combo.itemData(index)
            if strategy_name:
                self.on_strategy_changed(strategy_name)
    
    def on_strategy_changed(self, strategy_name: str):
        """策略改变时更新参数配置"""
        # 清空现有配置
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if strategy_name not in STRATEGY_PARAMS:
            return
        
        # 创建参数输入控件
        self.param_inputs = {}
        params = STRATEGY_PARAMS[strategy_name]
        
        for param_name, param_config in params.items():
            # 创建垂直分组 - 使用中文显示名称
            display_name = PARAM_DISPLAY_NAMES.get(param_name, param_name)
            param_group = QGroupBox(display_name)
            param_v_layout = QVBoxLayout()
            
            # 最小值（单独一行）
            min_layout = QHBoxLayout()
            min_layout.addWidget(QLabel("最小值:"))
            if param_config['type'] == 'int':
                min_spin = QSpinBox()
                min_spin.setRange(param_config['min'], param_config['max'])
                min_spin.setValue(param_config['min'])
                min_spin.setSingleStep(param_config['step'])
                min_spin.setMinimumWidth(100)
            else:
                min_spin = QDoubleSpinBox()
                min_spin.setRange(param_config['min'], param_config['max'])
                min_spin.setValue(param_config['min'])
                min_spin.setSingleStep(param_config['step'])
                min_spin.setDecimals(2)
                min_spin.setMinimumWidth(100)
            min_layout.addWidget(min_spin)
            min_layout.addStretch()
            
            # 最大值（单独一行）
            max_layout = QHBoxLayout()
            max_layout.addWidget(QLabel("最大值:"))
            if param_config['type'] == 'int':
                max_spin = QSpinBox()
                max_spin.setRange(param_config['min'], param_config['max'])
                max_spin.setValue(param_config['max'])
                max_spin.setSingleStep(param_config['step'])
                max_spin.setMinimumWidth(100)
            else:
                max_spin = QDoubleSpinBox()
                max_spin.setRange(param_config['min'], param_config['max'])
                max_spin.setValue(param_config['max'])
                max_spin.setSingleStep(param_config['step'])
                max_spin.setDecimals(2)
                max_spin.setMinimumWidth(100)
            max_layout.addWidget(max_spin)
            max_layout.addStretch()
            
            # 步长（单独一行，仅网格搜索）
            step_layout = QHBoxLayout()
            step_label = QLabel("步长:")
            step_layout.addWidget(step_label)
            
            if param_config['type'] == 'int':
                step_spin = QSpinBox()
                step_spin.setRange(1, param_config['step'] * 5)
                step_spin.setValue(param_config['step'])
                step_spin.setMinimumWidth(100)
            else:
                step_spin = QDoubleSpinBox()
                step_spin.setRange(0.01, param_config['step'] * 5)
                step_spin.setValue(param_config['step'])
                step_spin.setSingleStep(0.01)
                step_spin.setDecimals(2)
                step_spin.setMinimumWidth(100)
            step_layout.addWidget(step_spin)
            step_layout.addStretch()
            
            # 添加到垂直布局
            param_v_layout.addLayout(min_layout)
            param_v_layout.addLayout(max_layout)
            param_v_layout.addLayout(step_layout)
            param_group.setLayout(param_v_layout)
            
            # 添加到主布局
            self.param_layout.addRow(param_group)
            
            # 保存输入控件和标签
            self.param_inputs[param_name] = {
                'min': min_spin,
                'max': max_spin,
                'step': step_spin,
                'step_label': step_label,
                'type': param_config['type']
            }
    
    def on_method_changed(self, method_name: str):
        """优化方法改变"""
        if method_name == '随机搜索':
            self.random_group.setVisible(True)
            # 隐藏步长控件和标签
            for inputs in self.param_inputs.values():
                inputs['step'].setVisible(False)
                inputs['step_label'].setVisible(False)
        else:
            self.random_group.setVisible(False)
            # 显示步长控件和标签
            for inputs in self.param_inputs.values():
                inputs['step'].setVisible(True)
                inputs['step_label'].setVisible(True)
    
    def start_optimization(self):
        """开始优化"""
        # 验证输入
        stock_code = self.stock_code_input.text().strip()
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")
        # 使用currentData获取英文策略名
        strategy_name = self.strategy_combo.currentData()
        if not strategy_name:  # 如果没有userData，fallback到text
            strategy_name = self.strategy_combo.currentText()
        method_name = self.method_combo.currentText()
        
        if not stock_code or not start_date or not end_date:
            QMessageBox.warning(self, "输入错误", "请填写完整的股票代码和日期范围！")
            return
        
        # 构建参数配置
        param_config = {}
        
        if method_name == '网格搜索':
            # 网格搜索：生成参数列表
            for param_name, inputs in self.param_inputs.items():
                min_val = inputs['min'].value()
                max_val = inputs['max'].value()
                step_val = inputs['step'].value()
                
                if inputs['type'] == 'int':
                    param_config[param_name] = list(range(int(min_val), int(max_val) + 1, int(step_val)))
                else:
                    param_config[param_name] = list(np.arange(min_val, max_val + step_val, step_val))
            
            # 创建网格搜索优化器
            self.optimizer = GridSearch(self.config, self.data_manager)
            method = 'grid'
            
        else:
            # 随机搜索：参数范围
            for param_name, inputs in self.param_inputs.items():
                param_config[param_name] = {
                    'min': inputs['min'].value(),
                    'max': inputs['max'].value()
                }
            
            # 添加迭代次数
            param_config['n_iter'] = self.n_iter_spin.value()
            
            # 创建随机搜索优化器
            self.optimizer = RandomSearch(self.config, self.data_manager)
            method = 'random'
        
        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("优化中...")
        
        # 创建并启动后台线程
        self.optimization_thread = OptimizationThread(
            self.optimizer,
            method,
            strategy_name,
            stock_code,
            start_date,
            end_date,
            param_config
        )
        
        self.optimization_thread.finished.connect(self.on_optimization_finished)
        self.optimization_thread.error.connect(self.on_optimization_error)
        self.optimization_thread.progress.connect(self.on_optimization_progress)
        
        self.optimization_thread.start()
        
        logger.info(f"开始参数优化: {strategy_name}, {method_name}")
    
    def stop_optimization(self):
        """停止优化"""
        if self.optimization_thread and self.optimization_thread.isRunning():
            self.optimization_thread.terminate()
            self.optimization_thread.wait()
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("已停止")
            
            logger.info("参数优化已停止")
    
    def on_optimization_progress(self, message: str):
        """优化进度更新"""
        self.status_label.setText(message)
        
        # 从消息中提取进度百分比
        if "(" in message and "%" in message:
            try:
                pct_str = message.split("(")[1].split("%")[0]
                pct = float(pct_str)
                self.progress_bar.setValue(int(pct))
            except:
                pass
    
    def on_optimization_finished(self, results: list):
        """优化完成"""
        self.results = results
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"优化完成！共测试 {len(results)} 个参数组合")
        
        # 显示结果
        self.display_results()
        
        logger.info(f"参数优化完成，共 {len(results)} 个结果")
    
    def on_optimization_error(self, error_msg: str):
        """优化出错"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText(f"优化失败: {error_msg}")
        
        QMessageBox.critical(self, "优化失败", f"参数优化过程中出现错误：\n{error_msg}")
        
        logger.error(f"参数优化失败: {error_msg}")
    
    def display_results(self):
        """显示优化结果"""
        if not self.results:
            return
        
        # 显示结果表格
        self.display_results_table()
        
        # 显示可视化
        self.display_heatmap()
        self.display_sensitivity_analysis()
        self.display_return_distribution()
    
    def display_results_table(self):
        """显示结果表格"""
        df = self.optimizer.get_results_dataframe()
        
        if df.empty:
            return
        
        # 设置表格
        self.result_table.setRowCount(len(df))
        self.result_table.setColumnCount(len(df.columns))
        self.result_table.setHorizontalHeaderLabels(df.columns.tolist())
        
        # 填充数据
        for i, row in df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                
                # 高亮最优结果
                if i == 0:
                    item.setBackground(Qt.yellow)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                
                self.result_table.setItem(i, j, item)
        
        logger.info("优化结果表格显示完成")
    
    def display_heatmap(self):
        """显示参数热力图"""
        if not self.results or len(self.param_inputs) < 2:
            return
        
        try:
            df = self.optimizer.get_results_dataframe()
            
            # 获取前两个参数
            param_names = list(self.param_inputs.keys())[:2]
            
            if len(param_names) < 2:
                return
            
            # 创建数据透视表
            pivot = df.pivot_table(
                values='total_return',
                index=param_names[0],
                columns=param_names[1],
                aggfunc='mean'
            )
            
            # 绘制热力图
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            
            fig = self.heatmap_canvas.figure
            
            # 根据主题设置背景色
            if is_dark:
                fig.patch.set_facecolor('#2b2b2b')
            else:
                fig.patch.set_facecolor('#fafafa')
            
            fig.clear()
            ax = fig.add_subplot(111)
            ax.set_facecolor('transparent')
            
            im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')
            
            # 设置坐标轴
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels([f"{v:.1f}" for v in pivot.columns])
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels([f"{v:.1f}" for v in pivot.index])
            
            ax.set_xlabel(param_names[1], color=text_color)
            ax.set_ylabel(param_names[0], color=text_color)
            ax.set_title(f'参数热力图 - 总收益率(%)', color=text_color)
            
            # 坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 添加颜色条
            fig.colorbar(im, ax=ax)
            
            fig.tight_layout()
            self.heatmap_canvas.draw()
            
            logger.info("参数热力图显示完成")
            
        except Exception as e:
            logger.error(f"显示热力图失败: {e}", exc_info=True)
    
    def display_sensitivity_analysis(self):
        """显示参数敏感度分析"""
        if not self.results:
            return
        
        try:
            df = self.optimizer.get_results_dataframe()
            
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            grid_color = (1, 1, 1, 0.1) if is_dark else (0, 0, 0, 0.1)
            
            fig = self.sensitivity_canvas.figure
            
            # 根据主题设置背景色
            if is_dark:
                fig.patch.set_facecolor('#2b2b2b')
            else:
                fig.patch.set_facecolor('#fafafa')
            
            fig.clear()
            ax = fig.add_subplot(111)
            ax.set_facecolor('transparent')
            
            param_names = list(self.param_inputs.keys())
            
            # 计算每个参数的敏感度（收益率标准差）
            sensitivities = []
            for param_name in param_names:
                if param_name in df.columns:
                    # 按参数值分组，计算收益率标准差
                    grouped = df.groupby(param_name)['total_return'].std()
                    avg_sensitivity = grouped.mean()
                    sensitivities.append(avg_sensitivity)
                else:
                    sensitivities.append(0)
            
            # 绘制柱状图
            ax.bar(param_names, sensitivities, color='steelblue', alpha=0.7)
            ax.set_xlabel('参数名称', color=text_color)
            ax.set_ylabel('敏感度 (收益率标准差)', color=text_color)
            ax.set_title('参数敏感度分析', color=text_color)
            ax.grid(True, alpha=0.3, color=grid_color)
            
            # 坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            fig.tight_layout()
            self.sensitivity_canvas.draw()
            
            logger.info("参数敏感度分析显示完成")
            
        except Exception as e:
            logger.error(f"显示敏感度分析失败: {e}", exc_info=True)
    
    def display_return_distribution(self):
        """显示收益分布"""
        if not self.results:
            return
        
        try:
            df = self.optimizer.get_results_dataframe()
            
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            grid_color = (1, 1, 1, 0.1) if is_dark else (0, 0, 0, 0.1)
            
            fig = self.distribution_canvas.figure
            
            # 根据主题设置背景色
            if is_dark:
                fig.patch.set_facecolor('#2b2b2b')
            else:
                fig.patch.set_facecolor('#fafafa')
            
            fig.clear()
            ax = fig.add_subplot(111)
            ax.set_facecolor('transparent')
            
            # 绘制收益率直方图
            returns = df['total_return'].values
            ax.hist(returns, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
            
            # 添加统计信息
            mean_return = returns.mean()
            median_return = np.median(returns)
            std_return = returns.std()
            
            ax.axvline(mean_return, color='red', linestyle='--', linewidth=2, label=f'均值: {mean_return:.2f}%')
            ax.axvline(median_return, color='green', linestyle='--', linewidth=2, label=f'中位数: {median_return:.2f}%')
            
            ax.set_xlabel('总收益率 (%)', color=text_color)
            ax.set_ylabel('频数', color=text_color)
            ax.set_title(f'收益率分布 (标准差: {std_return:.2f}%)', color=text_color)
            legend = ax.legend()
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            ax.grid(True, alpha=0.3, color=grid_color)
            
            # 坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            fig.tight_layout()
            self.distribution_canvas.draw()
            
            logger.info("收益分布显示完成")
            
        except Exception as e:
            logger.error(f"显示收益分布失败: {e}", exc_info=True)
