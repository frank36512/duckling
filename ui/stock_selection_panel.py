from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidgetItem, QGroupBox, QFormLayout, 
                             QLineEdit, QPushButton, QScrollArea, QProgressBar, 
                             QFileDialog, QMessageBox, QSpinBox, QCheckBox, QTabWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from qfluentwidgets import PrimaryPushButton, PushButton, InfoBar, InfoBarPosition, TableWidget, ComboBox
from ui.theme_manager import ThemeManager
from business.stock_selector import StockSelector
from business.stock_selector_enhanced import EnhancedStockSelector
from core.data_source import AKShareDataSource
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class SelectionWorker(QThread):
    """选股工作线程"""
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    
    def __init__(self, selector, enhanced_selector, params, selection_mode):
        super().__init__()
        self.selector = selector
        self.enhanced_selector = enhanced_selector
        self.params = params
        self.selection_mode = selection_mode
    
    def run(self):
        try:
            if self.selection_mode == 'basic':
                # 基础选股
                self.progress.emit(10, "正在获取股票列表...")
                result = self.selector.multi_factor_selection(**self.params)
                self.progress.emit(100, "选股完成")
                self.finished.emit(result)
            
            elif self.selection_mode == 'multifactor':
                # 多因子选股（增强版）
                self.progress.emit(10, "正在获取股票池...")
                stock_list = self._get_stock_pool()
                
                self.progress.emit(30, f"正在分析 {len(stock_list)} 只股票...")
                result = self.enhanced_selector.select_by_multifactor(
                    stock_list, 
                    top_n=self.params.get('top_n', 20)
                )
                
                self.progress.emit(100, "多因子选股完成")
                self.finished.emit(result)
            
            elif self.selection_mode == 'technical':
                # 技术信号选股
                self.progress.emit(10, "正在获取股票池...")
                stock_list = self._get_stock_pool()
                
                self.progress.emit(30, f"正在筛选技术信号...")
                result = self.enhanced_selector.select_by_technical_signals(
                    stock_list,
                    signal_type=self.params.get('signal_type', 'MACD金叉')
                )
                
                self.progress.emit(100, "技术信号选股完成")
                self.finished.emit(result)
                
        except Exception as e:
            logger.error(f"选股线程出错: {e}", exc_info=True)
            self.error.emit(str(e))
    
    def _get_stock_pool(self):
        """获取股票池"""
        try:
            import akshare as ak
            stock_info = ak.stock_zh_a_spot_em()
            # 提取股票代码
            stock_codes = stock_info['代码'].tolist()
            # 过滤：只要主板和创业板，排除ST和退市股
            filtered = [code for code in stock_codes 
                       if (code.startswith('6') or code.startswith('0') or code.startswith('3'))
                       and len(code) == 6]
            return filtered[:500]  # 限制数量避免太慢
        except Exception as e:
            logger.error(f"获取股票池失败: {e}")
            return []


class StockSelectionPanel(QWidget):
    """
    量化选股功能面板：支持多因子选股、条件筛选、结果展示
    集成增强版选股器，复用现有策略模型
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        self.selector = StockSelector()
        # 创建AKShare数据源（不需要config）
        self.enhanced_selector = EnhancedStockSelector(AKShareDataSource({}))
        self.current_result = None
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 选股模式选择（Tab标签页）
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(400)  # 设置最小高度确保内容显示完整
        
        # Tab 1: 基础条件筛选
        basic_tab = self._create_basic_tab()
        self.tab_widget.addTab(basic_tab, "📊 基础筛选")
        
        # Tab 2: 多因子选股（增强版）
        multifactor_tab = self._create_multifactor_tab()
        self.tab_widget.addTab(multifactor_tab, "🎯 多因子选股")
        
        # Tab 3: 技术信号选股
        technical_tab = self._create_technical_tab()
        self.tab_widget.addTab(technical_tab, "📈 技术信号")
        
        layout.addWidget(self.tab_widget)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮区域
        button_layout = QHBoxLayout()
        self.search_btn = PrimaryPushButton("🔍 开始选股")
        self.search_btn.clicked.connect(self.run_selection)
        self.export_excel_btn = PushButton("📊 导出Excel")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_excel_btn.setEnabled(False)
        self.export_csv_btn = PushButton("📄 导出CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_csv_btn.setEnabled(False)
        
        button_layout.addWidget(self.search_btn)
        button_layout.addWidget(self.export_excel_btn)
        button_layout.addWidget(self.export_csv_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 结果展示区域
        self.result_group = QGroupBox("选股结果")
        result_layout = QVBoxLayout()
        
        # 结果统计标签
        self.result_label = QLabel("等待选股...")
        result_layout.addWidget(self.result_label)
        
        self.result_table = TableWidget()
        self.result_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.result_table.setSelectionBehavior(TableWidget.SelectRows)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        result_layout.addWidget(self.result_table)
        self.result_group.setLayout(result_layout)
        layout.addWidget(self.result_group)

        self.setLayout(layout)
    
    def _create_basic_tab(self):
        """创建基础筛选Tab"""
        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        widget = QWidget()
        condition_layout = QFormLayout()
        condition_layout.setVerticalSpacing(15)  # 增加垂直间距

        # 行业筛选
        self.industry_combo = ComboBox()
        self.industry_combo.addItems(["全部", "银行", "证券", "保险", "软件", "通信", 
                                      "医药", "食品", "家电", "汽车", "房地产", 
                                      "煤炭", "钢铁", "化工", "电子"])
        self.industry_combo.setMinimumWidth(200)
        condition_layout.addRow("行业:", self.industry_combo)

        # 市值筛选
        self.market_cap_min = QLineEdit()
        self.market_cap_min.setPlaceholderText("最小市值(亿)")
        self.market_cap_max = QLineEdit()
        self.market_cap_max.setPlaceholderText("最大市值(亿)")
        cap_layout = QHBoxLayout()
        cap_layout.addWidget(self.market_cap_min)
        cap_layout.addWidget(QLabel("~"))
        cap_layout.addWidget(self.market_cap_max)
        condition_layout.addRow("市值区间:", cap_layout)

        # PE筛选
        self.pe_min = QLineEdit()
        self.pe_min.setPlaceholderText("最小PE")
        self.pe_max = QLineEdit()
        self.pe_max.setPlaceholderText("最大PE")
        pe_layout = QHBoxLayout()
        pe_layout.addWidget(self.pe_min)
        pe_layout.addWidget(QLabel("~"))
        pe_layout.addWidget(self.pe_max)
        condition_layout.addRow("PE区间:", pe_layout)

        # PB筛选
        self.pb_min = QLineEdit()
        self.pb_min.setPlaceholderText("最小PB")
        self.pb_max = QLineEdit()
        self.pb_max.setPlaceholderText("最大PB")
        pb_layout = QHBoxLayout()
        pb_layout.addWidget(self.pb_min)
        pb_layout.addWidget(QLabel("~"))
        pb_layout.addWidget(self.pb_max)
        condition_layout.addRow("PB区间:", pb_layout)

        # 技术因子筛选
        self.factor_combo = ComboBox()
        self.factor_combo.addItems(["全部", "SMA", "RSI", "MACD", "动量"])
        self.factor_combo.setMinimumWidth(200)
        condition_layout.addRow("技术因子:", self.factor_combo)

        # 自定义条件
        self.custom_condition = QLineEdit()
        self.custom_condition.setPlaceholderText("自定义筛选表达式，如 pe<20 and pb>1")
        condition_layout.addRow("自定义条件:", self.custom_condition)

        widget.setLayout(condition_layout)
        scroll.setWidget(widget)
        return scroll
    
    def _create_multifactor_tab(self):
        """创建多因子选股Tab"""
        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        widget = QWidget()
        layout = QFormLayout()
        layout.setVerticalSpacing(15)
        
        # 选股数量
        self.multifactor_top_n = QSpinBox()
        self.multifactor_top_n.setRange(5, 100)
        self.multifactor_top_n.setValue(20)
        self.multifactor_top_n.setSuffix(" 只")
        layout.addRow("选股数量:", self.multifactor_top_n)
        
        # 说明文字
        info_label = QLabel(
            "💡 多因子选股说明：\n"
            "• 综合6大因子：MACD、均线、RSI、ROC、布林带、成交量\n"
            "• 每个因子独立打分后加权计算综合得分\n"
            "• 自动选出综合得分最高的股票\n"
            "• 复用MultiFactorStrategy策略的因子体系"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(ThemeManager.get_info_box_style())
        layout.addRow(info_label)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        return scroll
    
    def _create_technical_tab(self):
        """创建技术信号Tab"""
        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        widget = QWidget()
        layout = QFormLayout()
        layout.setVerticalSpacing(15)
        
        # 信号类型选择
        self.technical_signal_type = ComboBox()
        self.technical_signal_type.addItems([
            "MACD金叉",
            "均线多头",
            "RSI超跌",
            "布林带突破",
            "成交量放大"
        ])
        self.technical_signal_type.setMinimumWidth(200)
        layout.addRow("技术信号:", self.technical_signal_type)
        
        # 说明文字
        info_label = QLabel(
            "💡 技术信号选股说明：\n"
            "• MACD金叉：DIF上穿DEA，趋势转强\n"
            "• 均线多头：MA5>MA10>MA20>MA60，趋势向上\n"
            "• RSI超跌：RSI从30以下回升，超跌反弹\n"
            "• 布林带突破：价格突破上轨或从下轨反弹\n"
            "• 成交量放大：成交量超过均量2倍以上"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(ThemeManager.get_info_box_style())
        layout.addRow(info_label)
        
        widget.setLayout(layout)
        scroll.setWidget(widget)
        return scroll

    def run_selection(self):
        """执行选股"""
        try:
            # 禁用按钮
            self.search_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 根据当前Tab确定选股模式
            current_tab = self.tab_widget.currentIndex()
            
            if current_tab == 0:
                # 基础筛选模式
                selection_mode = 'basic'
                params = {
                    'industry': self.industry_combo.currentText(),
                    'min_market_cap': self._get_float_value(self.market_cap_min),
                    'max_market_cap': self._get_float_value(self.market_cap_max),
                    'min_pe': self._get_float_value(self.pe_min),
                    'max_pe': self._get_float_value(self.pe_max),
                    'min_pb': self._get_float_value(self.pb_min),
                    'max_pb': self._get_float_value(self.pb_max),
                    'technical_factor': self.factor_combo.currentText(),
                    'custom_condition': self.custom_condition.text().strip()
                }
            
            elif current_tab == 1:
                # 多因子选股模式
                selection_mode = 'multifactor'
                params = {
                    'top_n': self.multifactor_top_n.value()
                }
            
            elif current_tab == 2:
                # 技术信号选股模式
                selection_mode = 'technical'
                params = {
                    'signal_type': self.technical_signal_type.currentText()
                }
            
            else:
                raise ValueError("未知的选股模式")
            
            # 创建工作线程
            self.worker = SelectionWorker(
                self.selector, 
                self.enhanced_selector, 
                params, 
                selection_mode
            )
            self.worker.finished.connect(self.on_selection_finished)
            self.worker.error.connect(self.on_selection_error)
            self.worker.progress.connect(self.on_progress_update)
            self.worker.start()
            
            logger.info(f"开始选股，模式: {selection_mode}, 参数: {params}")
            
        except Exception as e:
            logger.error(f"启动选股失败: {e}", exc_info=True)
            InfoBar.error(
                title="错误",
                content=f"启动选股失败: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
            self.search_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def _get_float_value(self, line_edit):
        """从QLineEdit获取浮点数值"""
        text = line_edit.text().strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    
    def on_progress_update(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.result_label.setText(message)
    
    def on_selection_finished(self, result_df):
        """选股完成回调"""
        try:
            self.current_result = result_df
            self.search_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            
            if result_df.empty:
                self.result_label.setText("未找到符合条件的股票")
                self.result_table.setRowCount(0)
                self.export_excel_btn.setEnabled(False)
                self.export_csv_btn.setEnabled(False)
                InfoBar.warning(
                    title="提示",
                    content="未找到符合条件的股票，请调整筛选条件",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            
            # 更新结果标签
            self.result_label.setText(f"共筛选出 {len(result_df)} 只股票")
            
            # 显示结果
            self.display_results(result_df)
            
            # 启用导出按钮
            self.export_excel_btn.setEnabled(True)
            self.export_csv_btn.setEnabled(True)
            
            InfoBar.success(
                title="成功",
                content=f"选股完成，共找到 {len(result_df)} 只股票",
                parent=self,
                position=InfoBarPosition.TOP
            )
            
        except Exception as e:
            logger.error(f"显示选股结果失败: {e}", exc_info=True)
    
    def on_selection_error(self, error_msg):
        """选股错误回调"""
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.result_label.setText("选股失败")
        
        InfoBar.error(
            title="错误",
            content=f"选股失败: {error_msg}",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def display_results(self, df):
        """显示选股结果（动态适配列）"""
        try:
            if df.empty:
                self.result_table.setRowCount(0)
                self.result_table.setColumnCount(0)
                return
            
            # 设置列
            columns = df.columns.tolist()
            self.result_table.setColumnCount(len(columns))
            self.result_table.setHorizontalHeaderLabels(columns)
            self.result_table.setRowCount(len(df))
            
            # 填充数据
            for i, (idx, row) in enumerate(df.iterrows()):
                for j, col in enumerate(columns):
                    value = row[col]
                    
                    # 格式化显示
                    if pd.isna(value):
                        text = "-"
                    elif isinstance(value, float):
                        text = f"{value:.2f}" if abs(value) < 1000 else f"{value:.0f}"
                    else:
                        text = str(value)
                    
                    item = QTableWidgetItem(text)
                    
                    # 涨跌幅列着色
                    if '涨跌幅' in col:
                        try:
                            val = float(value)
                            if val > 0:
                                item.setForeground(Qt.red)
                            elif val < 0:
                                item.setForeground(Qt.green)
                        except:
                            pass
                    
                    # 得分列着色
                    if '得分' in col:
                        try:
                            val = float(value)
                            if val > 0.5:
                                item.setForeground(Qt.red)
                            elif val < -0.3:
                                item.setForeground(Qt.green)
                        except:
                            pass
                    
                    self.result_table.setItem(i, j, item)
            
            # 调整列宽
            self.result_table.resizeColumnsToContents()
            
            logger.info(f"成功显示 {len(df)} 条选股结果")
            
        except Exception as e:
            logger.error(f"显示结果失败: {e}", exc_info=True)
    
    def export_to_excel(self):
        """导出到Excel"""
        if self.current_result is None or self.current_result.empty:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return
        
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出Excel", "", "Excel文件 (*.xlsx)"
            )
            
            if filepath:
                if self.selector.export_to_excel(self.current_result, filepath):
                    InfoBar.success(
                        title="成功",
                        content=f"已导出到: {filepath}",
                        parent=self,
                        position=InfoBarPosition.TOP
                    )
                else:
                    InfoBar.error(
                        title="错误",
                        content="导出失败",
                        parent=self,
                        position=InfoBarPosition.TOP
                    )
        except Exception as e:
            logger.error(f"导出Excel失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def export_to_csv(self):
        """导出到CSV"""
        if self.current_result is None or self.current_result.empty:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return
        
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出CSV", "", "CSV文件 (*.csv)"
            )
            
            if filepath:
                if self.selector.export_to_csv(self.current_result, filepath):
                    InfoBar.success(
                        title="成功",
                        content=f"已导出到: {filepath}",
                        parent=self,
                        position=InfoBarPosition.TOP
                    )
                else:
                    InfoBar.error(
                        title="错误",
                        content="导出失败",
                        parent=self,
                        position=InfoBarPosition.TOP
                    )
        except Exception as e:
            logger.error(f"导出CSV失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
