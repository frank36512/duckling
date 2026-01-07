"""
策略对比面板
支持多策略批量回测和对比分析
"""

import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QSpinBox,
                             QMessageBox, QTableWidgetItem,
                             QProgressBar, QSplitter, QTabWidget,
                             QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont
from qfluentwidgets import (PushButton, LineEdit, DateEdit, PrimaryPushButton, 
                            ListWidget, TableWidget)
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from ui.theme_manager import ThemeManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from business.batch_backtest import BatchBacktest
from business.data_manager import DataManager
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ComparisonThread(QThread):
    """批量回测线程"""
    
    finished = pyqtSignal(list)  # 回测完成信号
    error = pyqtSignal(str)  # 错误信号
    progress = pyqtSignal(str)  # 进度信号
    
    def __init__(self, batch_engine, stock_code, start_date, end_date, strategy_names):
        super().__init__()
        self.batch_engine = batch_engine
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_names = strategy_names
    
    def run(self):
        """执行批量回测"""
        try:
            self.progress.emit(f"正在回测 {len(self.strategy_names)} 个策略...")
            
            results = self.batch_engine.run_multiple_strategies(
                self.stock_code,
                self.start_date,
                self.end_date,
                self.strategy_names,
                max_workers=4
            )
            
            if not results:
                self.error.emit("所有策略回测均失败")
                return
            
            self.progress.emit(f"回测完成！成功: {len(results)}/{len(self.strategy_names)}")
            self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"批量回测执行失败: {str(e)}", exc_info=True)
            self.error.emit(f"批量回测执行失败: {str(e)}")


class ComparisonPanel(QWidget):
    """策略对比面板"""
    
    def __init__(self, config: dict):
        """
        初始化策略对比面板
        :param config: 配置字典
        """
        super().__init__()
        
        self.config = config
        
        # 初始化数据管理器
        try:
            self.data_manager = DataManager(config)
        except Exception as e:
            logger.error(f"初始化数据管理器失败: {e}")
            self.data_manager = None
        
        # 初始化批量回测引擎
        backtest_config = {
            'initial_cash': 100000,
            'commission': 0.0003,
            'stamp_duty': 0.001,
            'slippage': 0.001
        }
        self.batch_engine = BatchBacktest(backtest_config, self.data_manager)
        
        self.comparison_thread = None
        self.results = []
        
        self.init_ui()
        
        logger.info("策略对比面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：配置区域
        left_widget = QWidget()
        left_widget.setStyleSheet(ThemeManager.get_panel_stylesheet())
        left_layout = QVBoxLayout(left_widget)
        
        # 股票代码和日期
        config_group = QGroupBox("回测配置")
        config_layout = QVBoxLayout()
        
        # 股票代码
        stock_layout = QHBoxLayout()
        stock_layout.addWidget(QLabel("股票代码:"))
        self.stock_code_input = LineEdit()
        self.stock_code_input.setPlaceholderText("如: 600000")
        stock_layout.addWidget(self.stock_code_input)
        config_layout.addLayout(stock_layout)
        
        # 日期范围 - 分两行显示
        # 开始日期
        start_date_layout = QHBoxLayout()
        start_label = QLabel("开始日期:")
        start_label.setMinimumWidth(70)
        start_date_layout.addWidget(start_label)
        self.start_date = DateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setMinimumWidth(150)
        start_date_layout.addWidget(self.start_date)
        start_date_layout.addStretch()
        config_layout.addLayout(start_date_layout)
        
        # 结束日期
        end_date_layout = QHBoxLayout()
        end_label = QLabel("结束日期:")
        end_label.setMinimumWidth(70)
        end_date_layout.addWidget(end_label)
        self.end_date = DateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setMinimumWidth(150)
        end_date_layout.addWidget(self.end_date)
        end_date_layout.addStretch()
        config_layout.addLayout(end_date_layout)
        
        config_group.setLayout(config_layout)
        left_layout.addWidget(config_group)
        
        # 策略选择
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QVBoxLayout()
        
        # 全选/全不选按钮
        btn_layout = QHBoxLayout()
        select_all_btn = PushButton("全选")
        select_all_btn.setMaximumWidth(80)
        select_all_btn.clicked.connect(self.select_all_strategies)
        btn_layout.addWidget(select_all_btn)
        
        deselect_all_btn = PushButton("全不选")
        deselect_all_btn.setMaximumWidth(80)
        deselect_all_btn.clicked.connect(self.deselect_all_strategies)
        btn_layout.addWidget(deselect_all_btn)
        
        btn_layout.addStretch()
        strategy_layout.addLayout(btn_layout)
        
        # 策略列表
        self.strategy_list = ListWidget()
        self.strategy_list.setSelectionMode(QAbstractItemView.MultiSelection)
        
        # 策略中英文名称映射
        from ui.strategy_panel import StrategyPanel
        
        # 添加所有可用策略（显示中文名称）
        available_strategies = StrategyFactory.get_builtin_strategies()
        for strategy_name in available_strategies:
            display_name = StrategyPanel.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
            self.strategy_list.addItem(display_name)
        
        strategy_layout.addWidget(self.strategy_list)
        strategy_group.setLayout(strategy_layout)
        left_layout.addWidget(strategy_group)
        
        # 开始对比按钮
        self.compare_btn = PrimaryPushButton("🚀 开始对比")
        self.compare_btn.clicked.connect(self.start_comparison)
        left_layout.addWidget(self.compare_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        left_layout.addWidget(self.status_label)
        
        # 限制左侧面板最大宽度
        left_widget.setMaximumWidth(450)
        splitter.addWidget(left_widget)
        
        # 右侧：结果展示区域
        right_widget = QTabWidget()
        right_widget.setMinimumWidth(650)  # 设置最小宽度确保标签显示完整
        
        # Tab1: 对比表格
        table_container = QWidget()
        table_container.setStyleSheet(ThemeManager.get_panel_stylesheet())
        table_layout = QVBoxLayout(table_container)
        
        # 添加空状态提示
        self.table_empty_label = QLabel()
        self.table_empty_label.setAlignment(Qt.AlignCenter)
        empty_text = """
        <div style='text-align: center;'>
            <p style='font-size: 48px; margin: 20px;'>📊</p>
            <p style='font-size: 16px; font-weight: bold;'>策略对比表格</p>
            <p style='font-size: 12px; margin-top: 20px;'>
                请按照以下步骤进行策略对比：
            </p>
            <p style='font-size: 12px; text-align: left; max-width: 400px; margin: 20px auto;'>
                1. 在左侧输入股票代码（如：600000）<br>
                2. 选择回测日期范围<br>
                3. 选择至少 <b>2个策略</b> 进行对比<br>
                4. 点击"开始对比"按钮<br><br>
                💡 <i>系统将自动生成对比表格、雷达图和收益曲线</i>
            </p>
        </div>
        """
        self.table_empty_label.setText(empty_text)
        table_layout.addWidget(self.table_empty_label)
        
        self.result_table = TableWidget()
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setSortingEnabled(True)
        self.result_table.setVisible(False)  # 初始隐藏
        table_layout.addWidget(self.result_table)
        
        right_widget.addTab(table_container, "📊 表格")
        
        # Tab2: 雷达图
        radar_container = QWidget()
        radar_container.setStyleSheet(ThemeManager.get_panel_stylesheet())
        radar_layout = QVBoxLayout(radar_container)
        
        self.radar_empty_label = QLabel()
        self.radar_empty_label.setAlignment(Qt.AlignCenter)
        radar_text = """
        <div style='text-align: center;'>
            <p style='font-size: 48px; margin: 20px;'>🎯</p>
            <p style='font-size: 16px; font-weight: bold;'>策略雷达图</p>
            <p style='font-size: 12px; margin-top: 20px;'>
                雷达图将从多个维度展示策略性能：
            </p>
            <p style='font-size: 12px; text-align: left; max-width: 400px; margin: 20px auto;'>
                • 总收益率<br>
                • 夏普比率<br>
                • 胜率<br>
                • 最大回撤<br>
                • 盈亏比<br><br>
                💡 <i>完成对比后将在此显示雷达图</i>
            </p>
        </div>
        """
        self.radar_empty_label.setText(radar_text)
        radar_layout.addWidget(self.radar_empty_label)
        
        from qfluentwidgets import isDarkTheme
        fig_color = '#2b2b2b' if isDarkTheme() else '#fafafa'
        
        self.radar_figure = Figure(facecolor=fig_color, tight_layout=True)
        self.radar_canvas = FigureCanvas(self.radar_figure)
        self.radar_canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.radar_canvas.setMinimumHeight(300)
        self.radar_canvas.setMaximumHeight(600)
        self.radar_canvas.setVisible(False)  # 初始隐藏
        radar_layout.addWidget(self.radar_canvas)
        
        right_widget.addTab(radar_container, "🎯 雷达")
        
        # Tab3: 收益曲线
        equity_container = QWidget()
        equity_container.setStyleSheet(ThemeManager.get_panel_stylesheet())
        equity_layout = QVBoxLayout(equity_container)
        
        self.equity_empty_label = QLabel()
        self.equity_empty_label.setAlignment(Qt.AlignCenter)
        equity_text = """
        <div style='text-align: center;'>
            <p style='font-size: 48px; margin: 20px;'>📈</p>
            <p style='font-size: 16px; font-weight: bold;'>收益曲线对比</p>
            <p style='font-size: 12px; margin-top: 20px;'>
                收益曲线展示各策略的资金变化趋势
            </p>
            <p style='font-size: 12px; text-align: left; max-width: 400px; margin: 20px auto;'>
                • 直观对比各策略表现<br>
                • 识别稳定性差异<br>
                • 发现潜在风险点<br><br>
                💡 <i>完成对比后将在此显示收益曲线图</i>
            </p>
        </div>
        """
        self.equity_empty_label.setText(equity_text)
        equity_layout.addWidget(self.equity_empty_label)
        
        self.equity_figure = Figure(facecolor=fig_color, tight_layout=True)
        self.equity_canvas = FigureCanvas(self.equity_figure)
        self.equity_canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.equity_canvas.setMinimumHeight(300)
        self.equity_canvas.setMaximumHeight(600)
        self.equity_canvas.setVisible(False)  # 初始隐藏
        equity_layout.addWidget(self.equity_canvas)
        
        right_widget.addTab(equity_container, "📈 曲线")
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例和初始尺寸
        splitter.setSizes([400, 900])  # 左侧400px，右侧900px
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)  # 右侧拉伸因子更大
        
        layout.addWidget(splitter)
    
    def select_all_strategies(self):
        """全选策略"""
        for i in range(self.strategy_list.count()):
            self.strategy_list.item(i).setSelected(True)
    
    def deselect_all_strategies(self):
        """全不选策略"""
        self.strategy_list.clearSelection()
    
    def start_comparison(self):
        """开始策略对比"""
        # 验证输入
        stock_code = self.stock_code_input.text().strip()
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码！")
            return
        
        # 获取选中的策略
        selected_items = self.strategy_list.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(self, "警告", "请至少选择2个策略进行对比！")
            return
        
        # 将中文名称转换回英文策略名
        from ui.strategy_panel import StrategyPanel
        strategy_names = []
        for item in selected_items:
            display_name = item.text()
            # 查找对应的英文策略名
            for eng_name, cn_name in StrategyPanel.STRATEGY_DISPLAY_NAMES.items():
                if cn_name == display_name:
                    strategy_names.append(eng_name)
                    break
        
        if not strategy_names:
            QMessageBox.warning(self, "警告", "无法识别选中的策略！")
            return
        
        # 获取日期
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # 创建并启动回测线程
        self.comparison_thread = ComparisonThread(
            self.batch_engine,
            stock_code,
            start_date,
            end_date,
            strategy_names
        )
        
        self.comparison_thread.finished.connect(self.on_comparison_finished)
        self.comparison_thread.error.connect(self.on_comparison_error)
        self.comparison_thread.progress.connect(self.on_comparison_progress)
        
        # 更新UI状态
        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.status_label.setText("正在进行批量回测...")
        
        # 启动线程
        self.comparison_thread.start()
    
    def on_comparison_progress(self, message):
        """回测进度更新"""
        self.status_label.setText(message)
    
    def on_comparison_finished(self, results):
        """回测完成"""
        self.reset_ui_state()
        
        if not results:
            QMessageBox.warning(self, "警告", "回测返回空结果")
            return
        
        self.results = results
        
        # 显示结果
        self.display_comparison_table()
        self.display_radar_chart()
        self.display_equity_curves()
        
        self.status_label.setText(f"对比完成！共 {len(results)} 个策略")
        
        QMessageBox.information(self, "成功", f"策略对比完成！\n共对比了 {len(results)} 个策略")
    
    def on_comparison_error(self, error_msg):
        """回测错误"""
        self.reset_ui_state()
        QMessageBox.critical(self, "错误", f"批量回测失败：\n{error_msg}")
    
    def reset_ui_state(self):
        """重置UI状态"""
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def display_comparison_table(self):
        """显示对比表格"""
        try:
            df = self.batch_engine.get_comparison_metrics()
            
            if df.empty:
                logger.warning("对比指标为空")
                return
            
            # 隐藏空状态，显示表格
            self.table_empty_label.setVisible(False)
            self.result_table.setVisible(True)
            
            # 设置表格
            self.result_table.setRowCount(len(df))
            self.result_table.setColumnCount(len(df.columns))
            self.result_table.setHorizontalHeaderLabels(df.columns.tolist())
            
            # 填充数据
            for i, row in df.iterrows():
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # 排名第一高亮显示
                    if j == 0 and value == 1:
                        item.setBackground(Qt.yellow)
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    
                    self.result_table.setItem(i, j, item)
            
            # 调整列宽
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            
            logger.info("对比表格显示完成")
            
        except Exception as e:
            logger.error(f"显示对比表格失败: {e}", exc_info=True)
    
    def display_radar_chart(self):
        """显示雷达图"""
        try:
            radar_data = self.batch_engine.get_radar_data()
            
            if not radar_data or 'data' not in radar_data:
                logger.warning("雷达图数据为空")
                return
            
            # 隐藏空状态，显示图表
            self.radar_empty_label.setVisible(False)
            self.radar_canvas.setVisible(True)
            
            data = radar_data['data']
            labels = radar_data['labels']
            
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            
            # 根据主题设置背景色
            if is_dark:
                self.radar_figure.patch.set_facecolor('#2b2b2b')
                bg_color = '#2b2b2b'
            else:
                self.radar_figure.patch.set_facecolor('#fafafa')
                bg_color = '#fafafa'
            
            self.radar_figure.clear()
            ax = self.radar_figure.add_subplot(111, projection='polar')
            ax.set_facecolor(bg_color)
            
            # 计算角度
            angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
            angles += angles[:1]  # 闭合
            
            # 绘制每个策略
            colors = plt.cm.tab10(np.linspace(0, 1, len(data)))
            
            for (strategy_name, values), color in zip(data.items(), colors):
                values += values[:1]  # 闭合
                ax.plot(angles, values, 'o-', linewidth=2, label=strategy_name, color=color)
                ax.fill(angles, values, alpha=0.15, color=color)
            
            # 设置标签
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, fontsize=10, color=text_color)
            
            # 设置网格
            ax.set_ylim(0, 1)
            ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
            ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8, color=text_color)
            ax.grid(True, linestyle='--', alpha=0.5)
            
            # 坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 图例
            legend = ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            
            # 标题
            ax.set_title('策略多维度对比雷达图', fontsize=14, fontweight='bold', pad=20, color=text_color)
            
            self.radar_figure.tight_layout()
            self.radar_canvas.draw()
            
            logger.info("雷达图显示完成")
            
        except Exception as e:
            logger.error(f"显示雷达图失败: {e}", exc_info=True)
    
    def display_equity_curves(self):
        """显示收益曲线对比"""
        try:
            curves = self.batch_engine.get_equity_curves()
            
            if not curves:
                logger.warning("没有资金曲线数据")
                return
            
            # 隐藏空状态，显示图表
            self.equity_empty_label.setVisible(False)
            self.equity_canvas.setVisible(True)
            
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            grid_color = (1, 1, 1, 0.1) if is_dark else (0, 0, 0, 0.1)
            
            # 根据主题设置背景色
            if is_dark:
                self.equity_figure.patch.set_facecolor('#2b2b2b')
                bg_color = '#2b2b2b'
            else:
                self.equity_figure.patch.set_facecolor('#fafafa')
                bg_color = '#fafafa'
            
            self.equity_figure.clear()
            ax = self.equity_figure.add_subplot(111)
            ax.set_facecolor(bg_color)
            
            # 绘制每条曲线
            for strategy_name, curve in curves.items():
                # 计算收益率（相对初始资金）
                initial_value = curve.iloc[0]
                returns = (curve / initial_value - 1) * 100
                ax.plot(curve.index, returns, label=strategy_name, linewidth=2)
            
            ax.set_xlabel('日期', fontsize=11, color=text_color)
            ax.set_ylabel('累计收益率 (%)', fontsize=11, color=text_color)
            ax.set_title('策略收益曲线对比', fontsize=14, fontweight='bold', color=text_color)
            legend = ax.legend(loc='best', fontsize=9)
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 旋转x轴标签
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            self.equity_figure.tight_layout()
            self.equity_canvas.draw()
            
            logger.info("收益曲线对比显示完成")
            
        except Exception as e:
            logger.error(f"显示收益曲线失败: {e}", exc_info=True)
