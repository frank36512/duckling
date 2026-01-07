"""
数据管理面板
用于下载、查看和管理股票数据
"""

import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidgetItem, QLabel,
                             QMessageBox, QProgressBar, QGroupBox,
                             QHeaderView, QSpinBox, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from qfluentwidgets import (PushButton, LineEdit, ComboBox, DateEdit,
                            PrimaryPushButton, TransparentToolButton, TableWidget)
import logging
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logger = logging.getLogger(__name__)


class UpdateStockListThread(QThread):
    """更新股票列表的工作线程"""
    # 定义信号
    finished = pyqtSignal(object)  # 完成信号，传递结果
    error = pyqtSignal(str)  # 错误信号，传递错误信息
    progress = pyqtSignal(str)  # 进度信号，传递状态文本
    
    def __init__(self, data_service):
        super().__init__()
        self.data_service = data_service
    
    def run(self):
        """在后台线程中执行更新操作"""
        try:
            logger.info("后台线程开始更新股票列表")
            self.progress.emit("正在从数据源获取股票列表...")
            
            # 执行实际的更新操作
            stock_list = self.data_service.update_stock_list()
            
            logger.info(f"后台线程更新完成，结果: {stock_list is not None}")
            self.finished.emit(stock_list)
            
        except Exception as e:
            logger.error(f"后台线程更新失败: {e}", exc_info=True)
            self.error.emit(str(e))


class BatchDownloadThread(QThread):
    """批量下载股票数据的工作线程"""
    # 定义信号
    progress = pyqtSignal(int, int, str, bool)  # 当前进度, 总数, 股票代码, 是否成功
    finished = pyqtSignal(dict)  # 完成信号，传递统计结果
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, data_service, stock_list, start_date, end_date):
        super().__init__()
        self.data_service = data_service
        self.stock_list = stock_list
        self.start_date = start_date
        self.end_date = end_date
    
    def run(self):
        """在后台线程中执行批量下载"""
        import time
        start_time = time.time()
        
        try:
            logger.info(f"批量下载线程启动，共 {len(self.stock_list)} 只股票")
            
            success_count = 0
            failed_count = 0
            total = len(self.stock_list)
            
            for idx, row in self.stock_list.iterrows():
                stock_code = row['code']
                
                try:
                    # 下载单只股票数据
                    data = self.data_service.download_stock_data(
                        stock_code,
                        self.start_date,
                        self.end_date
                    )
                    
                    if data is not None and not data.empty:
                        success_count += 1
                        self.progress.emit(success_count + failed_count, total, stock_code, True)
                        logger.info(f"✅ 批量下载: {stock_code} 成功 ({success_count + failed_count}/{total})")
                    else:
                        failed_count += 1
                        self.progress.emit(success_count + failed_count, total, stock_code, False)
                        logger.warning(f"❌ 批量下载: {stock_code} 失败 - 返回空数据")
                    
                    # 控制下载速率，避免请求过快
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_count += 1
                    self.progress.emit(success_count + failed_count, total, stock_code, False)
                    logger.error(f"❌ 批量下载: {stock_code} 失败 - {e}")
            
            # 计算总耗时
            duration = time.time() - start_time
            
            # 发送完成信号
            results = {
                'success': success_count,
                'failed': failed_count,
                'total': total,
                'duration': duration
            }
            
            logger.info(f"批量下载完成: 成功={success_count}, 失败={failed_count}, 耗时={duration:.1f}秒")
            self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"批量下载线程异常: {e}", exc_info=True)
            self.error.emit(str(e))


class DataPanel(QWidget):
    """数据管理面板"""
    
    def __init__(self, config: dict = None):
        """
        初始化数据管理面板
        :param config: 配置字典（可选，已由全局DataService管理）
        """
        super().__init__()
        
        self.config = config
        
        # 分页相关变量
        self.current_page = 1
        self.page_size = 100  # 每页显示100条
        self.total_data = None  # 缓存所有数据
        
        # 使用全局数据服务（不再创建独立的DataManager）
        from business.data_service import get_data_service
        try:
            self.data_service = get_data_service()
            logger.info("✅ 数据面板已连接到全局数据服务")
            
            # 连接数据更新信号
            self.data_service.stock_list_updated.connect(self._on_stock_list_updated)
            self.data_service.stock_data_updated.connect(self._on_stock_data_updated)
            
        except Exception as e:
            logger.error(f"❌ 数据面板连接数据服务失败: {e}", exc_info=True)
            self.data_service = None
            QMessageBox.critical(
                self,
                "初始化错误",
                f"数据面板无法连接到数据服务！\n\n"
                f"错误原因：{str(e)}\n\n"
                f"请重启应用程序。"
            )
        
        self.init_ui()
        
        # 初始化完成后，自动显示已下载数据的股票列表
        if self.data_service is not None:
            from PyQt5.QtCore import QTimer
            # 延迟500ms加载数据，确保UI完全初始化
            QTimer.singleShot(500, self.view_downloaded_stocks_list)
        
        logger.info("数据管理面板初始化完成")
    
    def _on_stock_list_updated(self, stock_list: pd.DataFrame):
        """股票列表更新回调"""
        logger.info(f"收到股票列表更新通知，共 {len(stock_list)} 只股票")
        # 可以在这里刷新显示
    
    def _on_stock_data_updated(self, stock_code: str, data: pd.DataFrame):
        """股票数据更新回调"""
        logger.info(f"收到股票 {stock_code} 数据更新通知，共 {len(data)} 条记录")
        # 如果当前显示的是该股票，刷新显示
        if self.stock_code_input.text().strip() == stock_code[:6]:
            self.load_default_data()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 应用统一主题样式
        from ui.theme_manager import ThemeManager
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 创建控制区域
        control_group = self.create_control_group()
        layout.addWidget(control_group)
        
        # 创建数据表格
        data_group = self.create_data_table_group()
        layout.addWidget(data_group)
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def create_control_group(self):
        """创建控制区域"""
        group = QGroupBox("数据下载控制")
        layout = QVBoxLayout()
        
        # 第一行：股票代码和日期范围
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("股票代码:"))
        self.stock_code_input = LineEdit()
        self.stock_code_input.setPlaceholderText("例如: 000001.SZ")
        self.stock_code_input.setMaximumWidth(150)
        row1.addWidget(self.stock_code_input)
        
        row1.addSpacing(10)
        
        start_label = QLabel("开始日期:")
        start_label.setMinimumWidth(60)
        row1.addWidget(start_label)
        self.start_date = DateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setFixedWidth(180)  # 增加宽度显示完整日期
        row1.addWidget(self.start_date)
        
        row1.addSpacing(10)
        
        end_label = QLabel("结束日期:")
        end_label.setMinimumWidth(60)
        row1.addWidget(end_label)
        self.end_date = DateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setFixedWidth(180)  # 增加宽度显示完整日期
        row1.addWidget(self.end_date)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        # 第二行：按钮组
        row2 = QHBoxLayout()
        
        # 默认激活的按钮 - 使用主题色
        self.downloaded_list_btn = PrimaryPushButton("📊 已下载日线数据股票列表")
        self.downloaded_list_btn.clicked.connect(self.view_downloaded_stocks_list)
        self.downloaded_list_btn.setToolTip("查看已下载日线数据的股票列表")
        self.downloaded_list_btn.setMinimumWidth(200)
        row2.addWidget(self.downloaded_list_btn)
        
        # 其他按钮使用普通样式
        self.download_btn = PushButton("📥 下载该股票日线数据")
        self.download_btn.clicked.connect(self.download_data)
        self.download_btn.setMinimumWidth(160)
        row2.addWidget(self.download_btn)
        
        self.update_list_btn = PushButton("🔄 更新所有股票列表")
        self.update_list_btn.clicked.connect(self.update_stock_list)
        self.update_list_btn.setToolTip("从数据源更新所有A股股票列表")
        self.update_list_btn.setMinimumWidth(160)
        row2.addWidget(self.update_list_btn)
        
        self.view_list_btn = PushButton("📋 查看所有股票列表")
        self.view_list_btn.clicked.connect(self.view_stock_list)
        self.view_list_btn.setToolTip("查看本地已有的所有股票列表")
        self.view_list_btn.setMinimumWidth(160)
        row2.addWidget(self.view_list_btn)
        
        self.refresh_btn = PushButton("🔄 刷新已下载股票日线数据")
        self.refresh_btn.clicked.connect(self.load_default_data)
        self.refresh_btn.setToolTip("刷新所有已下载股票的日线数据")
        self.refresh_btn.setMinimumWidth(180)
        row2.addWidget(self.refresh_btn)
        
        self.batch_download_btn = PushButton("📦 更新所有股票日线数据")
        self.batch_download_btn.clicked.connect(self.batch_download_all_stocks)
        self.batch_download_btn.setToolTip("批量下载所有股票的日线数据")
        self.batch_download_btn.setMinimumWidth(180)
        row2.addWidget(self.batch_download_btn)
        
        row2.addStretch()
        layout.addLayout(row2)
        
        group.setLayout(layout)
        return group
    
    def create_data_table_group(self):
        """创建数据表格区域"""
        group = QGroupBox("数据预览")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)  # 增加顶部间距，避免标题和内容重叠
        
        # 创建一个包含表格和水印的容器
        from PyQt5.QtWidgets import QStackedWidget
        self.table_container = QStackedWidget()
        
        # 创建表格 - 使用 QFluentWidgets 的 TableWidget
        self.data_table = TableWidget()
        # 默认显示行情数据（不包含序号列，使用表格自带的行号）
        self.data_table.setColumnCount(10)
        self.data_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "所属市场", "行业", "上市日期", 
            "日期", "收盘价", "涨跌幅", "成交量", "成交额"
        ])
        
        # 设置表格属性
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # 所有列均匀分布
        # 不使用交替行颜色，让QFluentWidgets主题统一管理
        self.data_table.setAlternatingRowColors(False)
        self.data_table.setSelectionBehavior(TableWidget.SelectRows)
        self.data_table.setEditTriggers(TableWidget.NoEditTriggers)
        
        # 显示表格自带的行号（取代序号列）
        self.data_table.verticalHeader().setVisible(True)
        
        # 连接行点击事件
        self.data_table.cellClicked.connect(self.on_table_row_clicked)
        
        # 创建空状态提示页面
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        # 大图标
        icon_label = QLabel("📊")
        icon_font = QFont()
        icon_font.setPointSize(72)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_label)
        
        # 主提示文字
        title_label = QLabel("暂无数据")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)
        
        # 提示步骤
        steps_label = QLabel(
            "开始使用：\n\n"
            "1️⃣ 点击上方「🔄 更新股票列表」按钮，下载A股股票列表\n\n"
            "2️⃣ 输入股票代码（如：000001），设置日期范围，点击「📥 下载数据」获取行情数据\n\n"
            "3️⃣ 数据下载完成后，页面将自动显示行情信息\n\n"
            "💡 提示：也可以点击「🔄 刷新数据」按钮手动刷新显示"
        )
        steps_font = QFont()
        steps_font.setPointSize(11)
        steps_label.setFont(steps_font)
        steps_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(steps_label)
        
        empty_layout.addStretch()
        
        # 添加到堆叠容器
        self.table_container.addWidget(self.empty_state_widget)  # 索引0: 空状态
        self.table_container.addWidget(self.data_table)          # 索引1: 表格
        
        # 默认显示空状态
        self.table_container.setCurrentIndex(0)
        
        layout.addWidget(self.table_container)
        
        # 分页控制区域
        pagination_layout = QHBoxLayout()
        
        self.page_info_label = QLabel("第 1 页，共 0 页 (共 0 条记录)")
        pagination_layout.addWidget(self.page_info_label)
        
        pagination_layout.addStretch()
        
        self.first_page_btn = PushButton("⏮ 首页")
        self.first_page_btn.clicked.connect(self.goto_first_page)
        self.first_page_btn.setMinimumWidth(90)
        pagination_layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = PushButton("⏪ 上一页")
        self.prev_page_btn.clicked.connect(self.goto_prev_page)
        self.prev_page_btn.setMinimumWidth(110)
        pagination_layout.addWidget(self.prev_page_btn)
        
        jump_label = QLabel("跳转到")
        jump_label.setMinimumWidth(50)
        pagination_layout.addWidget(jump_label)
        self.page_input = QSpinBox()
        self.page_input.setMinimum(1)
        self.page_input.setMaximum(1)
        self.page_input.setValue(1)
        self.page_input.setFixedWidth(60)
        self.page_input.valueChanged.connect(self.goto_page)
        pagination_layout.addWidget(self.page_input)
        page_label = QLabel("页")
        page_label.setMinimumWidth(30)
        pagination_layout.addWidget(page_label)
        
        self.next_page_btn = PushButton("下一页 ⏩")
        self.next_page_btn.clicked.connect(self.goto_next_page)
        self.next_page_btn.setMinimumWidth(110)
        pagination_layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = PushButton("末页 ⏭")
        self.last_page_btn.clicked.connect(self.goto_last_page)
        self.last_page_btn.setMinimumWidth(90)
        pagination_layout.addWidget(self.last_page_btn)
        
        pagination_layout.addStretch()
        
        # 每页显示条数
        size_label = QLabel("每页显示:")
        size_label.setMinimumWidth(70)
        pagination_layout.addWidget(size_label)
        self.page_size_combo = ComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500"])
        self.page_size_combo.setCurrentText("100")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        self.page_size_combo.setFixedWidth(80)
        pagination_layout.addWidget(self.page_size_combo)
        count_label = QLabel("条")
        count_label.setMinimumWidth(30)
        pagination_layout.addWidget(count_label)
        
        layout.addLayout(pagination_layout)
        
        # 添加状态标签
        self.status_label = QLabel("正在加载数据...")
        layout.addWidget(self.status_label)
        
        group.setLayout(layout)
        return group
    
    def download_data(self):
        """下载数据"""
        if self.data_service is None:
            QMessageBox.warning(self, "警告", "数据服务未初始化！")
            return
        
        stock_code = self.stock_code_input.text().strip()
        
        if not stock_code:
            QMessageBox.warning(self, "警告", "请输入股票代码！")
            return
        
        # 验证股票代码格式（6位数字）
        if not stock_code.isdigit() or len(stock_code) != 6:
            QMessageBox.warning(self, "警告", "股票代码格式错误！\n请输入6位数字代码，如：000001")
            return
        
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            "确认下载",
            f"确定要下载股票 {stock_code} 的数据吗？\n"
            f"日期范围: {start_date} 至 {end_date}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.status_label.setText(f"正在下载 {stock_code} 的数据...")
            self.download_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            
            try:
                # 实际下载逻辑
                success = self.data_service.download_stock_data(
                    stock_code, 
                    start_date, 
                    end_date
                )
                
                if success:
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.success(
                        title="下载成功",
                        content=f"股票 {stock_code} 数据已保存到本地数据库",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    self.status_label.setText(f"下载完成: {stock_code}")
                    
                    # 自动显示该股票的日线数据
                    self._load_single_stock(stock_code, start_date, end_date)
                    
                    # 设置按钮激活状态（下载后显示日线数据，激活刷新按钮）
                    self._set_active_button('refresh')
                else:
                    QMessageBox.warning(
                        self, 
                        "失败", 
                        f"股票 {stock_code} 数据下载失败！\n\n"
                        f"可能原因：\n"
                        f"1. 股票代码不存在\n"
                        f"2. 网络连接问题\n"
                        f"3. API调用限制\n\n"
                        f"请查看日志文件了解详情。"
                    )
                    self.status_label.setText("下载失败")
                    
            except Exception as e:
                logger.error(f"下载数据时出错: {e}", exc_info=True)
                QMessageBox.critical(
                    self, 
                    "错误", 
                    f"下载数据时发生错误：\n{str(e)}\n\n请查看日志文件了解详情。"
                )
                self.status_label.setText("下载出错")
            
            finally:
                self.progress_bar.setVisible(False)
                self.download_btn.setEnabled(True)
    
    def update_stock_list(self):
        """更新股票列表"""
        logger.info("用户点击了更新股票列表按钮")
        
        if self.data_service is None:
            logger.warning("数据服务未初始化")
            QMessageBox.warning(self, "警告", "数据服务未初始化！")
            return
        
        # 添加确认对话框，避免误操作
        from qfluentwidgets import MessageBox
        logger.info("显示确认对话框")
        confirm = MessageBox(
            "确认更新",
            "即将从数据源更新A股股票列表，此操作可能需要1-2分钟时间。\n\n"
            "是否继续？",
            self
        )
        confirm.yesButton.setText("确认更新")
        confirm.cancelButton.setText("取消")
        
        # QFluentWidgets的MessageBox需要使用exec()方法，且返回值是布尔值
        # 点击Yes按钮返回True，点击Cancel返回False
        result = confirm.exec()
        logger.info(f"用户选择结果: {result}, 类型: {type(result)}")
        
        if not result:  # 如果返回False（用户点击取消）
            logger.info("用户取消了更新操作")
            return
        
        logger.info("用户确认更新，继续执行")
        
        # 显示进度提示
        logger.info("开始显示进度条和状态信息")
        self.status_label.setText("正在连接数据源，更新股票列表中...")
        self.update_list_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 设置为不确定进度模式（循环动画）
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("正在更新，请稍候...")
        logger.info(f"进度条可见性: {self.progress_bar.isVisible()}")
        
        # 创建并启动工作线程
        self.update_thread = UpdateStockListThread(self.data_service)
        self.update_thread.progress.connect(self._on_update_progress)
        self.update_thread.finished.connect(self._on_update_finished)
        self.update_thread.error.connect(self._on_update_error)
        logger.info("启动后台线程执行更新")
        self.update_thread.start()
    
    def _on_update_progress(self, message):
        """处理更新进度信号"""
        logger.info(f"更新进度: {message}")
        self.status_label.setText(message)
    
    def _on_update_finished(self, stock_list):
        """处理更新完成信号"""
        logger.info(f"更新完成，返回结果类型: {type(stock_list)}")
        
        # 恢复UI状态
        self.progress_bar.setVisible(False)
        self.update_list_btn.setEnabled(True)
        
        if stock_list is not None and not stock_list.empty:
            count = len(stock_list)
            logger.info(f"股票列表更新成功，共 {count} 只股票")
            
            # 显示股票列表到表格
            self.display_stock_list(stock_list)
            
            # 显示成功提示
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title="更新成功",
                content=f"共获取 {count} 只股票信息，数据已保存到本地数据库",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.status_label.setText(f"股票列表更新完成，共 {count} 只股票")
            
            # 更新成功后自动显示查看列表窗口
            logger.info("更新成功，自动显示股票列表窗口")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.view_stock_list)
        else:
            logger.warning("股票列表更新失败或返回为空")
            QMessageBox.warning(
                self,
                "失败",
                "股票列表更新失败！\n\n"
                "可能原因：\n"
                "1. 网络连接问题\n"
                "2. API调用限制\n"
                "3. 数据源服务异常\n\n"
                "请查看日志文件了解详情。"
            )
            self.status_label.setText("更新失败")
    
    def _on_update_error(self, error_msg):
        """处理更新错误信号"""
        logger.error(f"更新出错: {error_msg}")
        
        # 恢复UI状态
        self.progress_bar.setVisible(False)
        self.update_list_btn.setEnabled(True)
        self.status_label.setText("更新出错")
        
        QMessageBox.critical(
            self,
            "错误",
            f"更新股票列表时发生错误：\n{error_msg}\n\n请查看日志文件了解详情。"
        )
    
    def batch_download_all_stocks(self):
        """批量下载所有股票的日线数据"""
        logger.info("用户点击了批量下载所有股票数据按钮")
        
        if self.data_service is None:
            logger.warning("数据服务未初始化")
            QMessageBox.warning(self, "警告", "数据服务未初始化！")
            return
        
        # 获取股票列表
        stock_list = self.data_service.get_stock_list()
        
        if stock_list is None or stock_list.empty:
            QMessageBox.warning(
                self,
                "警告",
                "股票列表为空！\n\n请先点击【更新所有股票列表】按钮获取股票列表。"
            )
            return
        
        stock_count = len(stock_list)
        
        # 获取日期范围
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # 显示确认对话框（增强警示信息）
        from qfluentwidgets import MessageBox
        confirm = MessageBox(
            "⚠️ 批量下载确认",
            f"即将批量下载 {stock_count} 只股票的日线数据！\n\n"
            f"📅 日期范围: {start_date} 至 {end_date}\n"
            f"⏱️ 预计耗时: {stock_count * 2 // 60} 分钟以上\n\n"
            f"⚠️ 重要提示：\n"
            f"• 此操作会占用大量网络资源和时间\n"
            f"• 建议在网络稳定且非交易时段进行\n"
            f"• 下载过程中请勿关闭程序\n"
            f"• API可能有频率限制，部分股票可能下载失败\n\n"
            f"💡 推荐方式：\n"
            f"  对于少量股票，建议使用【下载该股票日线数据】\n"
            f"  按钮逐个下载，更加稳定可靠。\n\n"
            f"是否继续批量下载？",
            self
        )
        confirm.yesButton.setText("确认批量下载")
        confirm.cancelButton.setText("取消")
        
        if not confirm.exec():
            logger.info("用户取消了批量下载")
            return
        
        logger.info("用户确认批量下载，开始执行")
        
        # 创建批量下载线程
        self.batch_thread = BatchDownloadThread(
            self.data_service,
            stock_list,
            start_date,
            end_date
        )
        
        # 连接信号
        self.batch_thread.progress.connect(self._on_batch_progress)
        self.batch_thread.finished.connect(self._on_batch_finished)
        self.batch_thread.error.connect(self._on_batch_error)
        
        # 禁用按钮，显示进度
        self.batch_download_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.update_list_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, stock_count)
        self.progress_bar.setValue(0)
        self.status_label.setText("开始批量下载...")
        
        # 启动线程
        self.batch_thread.start()
        logger.info("批量下载线程已启动")
    
    def _on_batch_progress(self, current, total, stock_code, success):
        """批量下载进度回调"""
        self.progress_bar.setValue(current)
        status = "成功" if success else "失败"
        self.status_label.setText(f"批量下载进度: {current}/{total} - {stock_code} ({status})")
        logger.info(f"批量下载进度: {current}/{total} - {stock_code} - {status}")
    
    def _on_batch_finished(self, results):
        """批量下载完成回调"""
        logger.info(f"批量下载完成，结果: 成功={results['success']}, 失败={results['failed']}")
        
        # 恢复UI状态
        self.progress_bar.setVisible(False)
        self.batch_download_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.update_list_btn.setEnabled(True)
        
        # 显示结果
        from qfluentwidgets import InfoBar, InfoBarPosition
        
        if results['failed'] == 0:
            # 全部成功
            InfoBar.success(
                title="批量下载完成",
                content=f"成功下载 {results['success']} 只股票的数据",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            self.status_label.setText(f"批量下载完成: {results['success']} 成功")
        else:
            # 部分失败
            QMessageBox.information(
                self,
                "批量下载完成",
                f"批量下载完成！\n\n"
                f"✅ 成功: {results['success']} 只\n"
                f"❌ 失败: {results['failed']} 只\n"
                f"⏱️ 总耗时: {results['duration']:.1f} 秒\n\n"
                f"失败原因可能是网络问题或股票已退市，\n"
                f"请查看日志文件了解详情。"
            )
            self.status_label.setText(f"批量下载完成: {results['success']} 成功, {results['failed']} 失败")
        
        # 批量下载完成后不自动刷新，避免数据格式混淆
        # 用户可以手动输入股票代码查看日线数据，或点击查看列表按钮查看股票列表
        logger.info("批量下载完成，等待用户手动查看数据")
    
    def _on_batch_error(self, error_msg):
        """批量下载错误回调"""
        logger.error(f"批量下载出错: {error_msg}")
        
        # 恢复UI状态
        self.progress_bar.setVisible(False)
        self.batch_download_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.update_list_btn.setEnabled(True)
        self.status_label.setText("批量下载出错")
        
        QMessageBox.critical(
            self,
            "错误",
            f"批量下载时发生错误：\n{error_msg}\n\n请查看日志文件了解详情。"
        )
    
    def display_stock_list(self, stock_list):
        """显示股票列表到表格（使用股票列表格式）"""
        try:
            # 清空表格
            self.data_table.setRowCount(0)
            
            # 设置表头 - 股票列表模式（3列简化格式）
            self.data_table.setColumnCount(3)
            self.data_table.setHorizontalHeaderLabels([
                "股票代码", "股票名称", "更新时间"
            ])
            
            # 设置列宽 - 简化的3列格式
            header = self.data_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Stretch)
            
            # 填充数据
            self.data_table.setRowCount(len(stock_list))
            
            for i, (index, row) in enumerate(stock_list.iterrows()):
                # 股票代码
                code = str(row.get('code', ''))
                # 移除可能的后缀（.SH, .SZ）
                if '.' in code:
                    code = code.split('.')[0]
                code = code[:6] if len(code) >= 6 else code
                
                item = QTableWidgetItem(code)
                item.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(i, 0, item)
                
                # 股票名称
                name = str(row.get('name', ''))
                item = QTableWidgetItem(name)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.data_table.setItem(i, 1, item)
                
                # 更新时间
                update_time = row.get('update_time', '-')
                if pd.notna(update_time) and update_time != '-':
                    if isinstance(update_time, pd.Timestamp):
                        update_time = update_time.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        update_time = str(update_time)
                else:
                    update_time = '-'
                
                item = QTableWidgetItem(update_time)
                item.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(i, 2, item)
            
            logger.info(f"股票列表显示完成，共 {len(stock_list)} 只")
            
        except Exception as e:
            logger.error(f"显示股票列表失败: {e}", exc_info=True)
    
    def view_stock_list(self):
        """查看股票列表（切换到列表模式）"""
        if self.data_service is None:
            QMessageBox.warning(self, "警告", "数据服务未初始化！")
            return
        
        self.status_label.setText("正在加载股票列表...")
        
        try:
            # 从数据库获取股票列表
            stock_list = self.data_service.get_stock_list()
            
            if stock_list is None or stock_list.empty:
                QMessageBox.information(
                    self,
                    "提示",
                    "本地还没有股票列表数据！\n\n"
                    "请点击'更新股票列表'按钮下载最新的股票列表。"
                )
                self.status_label.setText("无股票列表数据")
                return
            
            # 显示股票列表
            self.display_stock_list(stock_list)
            self.status_label.setText(f"共 {len(stock_list)} 只股票")
            
            # 设置按钮激活状态
            self._set_active_button('view_list')
            
        except Exception as e:
            logger.error(f"查看股票列表失败: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "错误",
                f"查看股票列表失败：\n{str(e)}"
            )
            self.status_label.setText("加载失败")
    
    def view_downloaded_stocks_list(self):
        """查看已下载日线数据的股票列表"""
        if self.data_service is None:
            QMessageBox.warning(self, "警告", "数据服务未初始化！")
            return
        
        self.status_label.setText("正在加载已下载数据的股票列表...")
        
        try:
            # 从数据管理器获取已下载数据的股票列表
            from business.data_manager import DataManager
            data_manager = DataManager(self.config)
            
            # 查询所有以 daily_ 开头的表
            import sqlite3
            db_path = data_manager.db_path
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取所有 daily_ 开头的表名
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'daily_%'
            """)
            tables = cursor.fetchall()
            
            results = []
            for (table_name,) in tables:
                # 从表名提取股票代码 (daily_000001_SZ -> 000001.SZ)
                code_part = table_name.replace('daily_', '').replace('_', '.')
                
                # 查询该表的数据统计
                try:
                    cursor.execute(f"""
                        SELECT COUNT(*) as record_count,
                               MIN(trade_date) as earliest_date,
                               MAX(trade_date) as latest_date
                        FROM {table_name}
                    """)
                    row = cursor.fetchone()
                    if row and row[0] > 0:  # 只包含有数据的表
                        results.append((code_part, row[0], row[1], row[2]))
                except Exception as e:
                    logger.warning(f"查询表 {table_name} 失败: {e}")
                    continue
            
            conn.close()
            
            if not results:
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.warning(
                    title="暂无数据",
                    content="还没有下载任何股票的日线数据",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.status_label.setText("暂无已下载的数据")
                # 显示空状态
                self.total_data = None
                self.table_container.setCurrentIndex(0)
                return
            
            # 构建 DataFrame
            downloaded_stocks = []
            
            # 获取股票列表（用于获取股票名称）
            stock_list = self.data_service.get_stock_list()
            logger.info(f"获取股票列表用于显示名称: {len(stock_list) if stock_list is not None and not stock_list.empty else 0} 只")
            
            for ts_code, record_count, earliest_date, latest_date in results:
                # 提取6位代码
                code_6 = ts_code[:6] if len(ts_code) >= 6 else ts_code
                
                # 从股票列表获取名称
                stock_name = ""
                if stock_list is not None and not stock_list.empty:
                    # 使用更宽松的匹配逻辑
                    matching = stock_list[stock_list['code'].str.contains(code_6, na=False, regex=False)]
                    if not matching.empty:
                        stock_name = matching.iloc[0].get('name', '')
                        logger.debug(f"找到股票名称: {code_6} -> {stock_name}")
                
                downloaded_stocks.append({
                    'code': code_6,
                    'name': stock_name if stock_name else '未知',
                    'record_count': record_count,
                    'earliest_date': earliest_date,
                    'latest_date': latest_date
                })
            
            # 转换为 DataFrame
            df = pd.DataFrame(downloaded_stocks)
            
            # 显示已下载股票列表
            self.display_downloaded_stocks_list(df)
            self.status_label.setText(f"已下载 {len(df)} 只股票的日线数据")
            
            # 设置按钮激活状态
            self._set_active_button('downloaded_list')
            
            logger.info(f"显示已下载数据的股票列表，共 {len(df)} 只")
            
        except Exception as e:
            logger.error(f"查看已下载股票列表失败: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "错误",
                f"查看已下载股票列表失败：\n{str(e)}"
            )
            self.status_label.setText("加载失败")
    
    def display_downloaded_stocks_list(self, downloaded_stocks):
        """显示已下载数据的股票列表（使用特殊格式）"""
        try:
            # 清空表格
            self.data_table.setRowCount(0)
            
            # 设置表头 - 已下载股票列表模式（5列）
            self.data_table.setColumnCount(5)
            self.data_table.setHorizontalHeaderLabels([
                "股票代码", "股票名称", "数据量", "最早日期", "最新日期"
            ])
            
            # 设置列宽
            header = self.data_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Stretch)
            
            # 切换到表格视图
            self.table_container.setCurrentIndex(1)
            
            # 填充数据
            self.data_table.setRowCount(len(downloaded_stocks))
            
            for i, (index, row) in enumerate(downloaded_stocks.iterrows()):
                # 股票代码
                code = str(row.get('code', ''))
                item = QTableWidgetItem(code)
                item.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(i, 0, item)
                
                # 股票名称
                name = str(row.get('name', ''))
                item = QTableWidgetItem(name)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.data_table.setItem(i, 1, item)
                
                # 数据量
                record_count = int(row.get('record_count', 0))
                item = QTableWidgetItem(f"{record_count:,} 条")
                item.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(i, 2, item)
                
                # 最早日期
                earliest_date = str(row.get('earliest_date', '-'))
                if earliest_date and earliest_date != '-':
                    earliest_date = earliest_date[:10]
                item = QTableWidgetItem(earliest_date)
                item.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(i, 3, item)
                
                # 最新日期
                latest_date = str(row.get('latest_date', '-'))
                if latest_date and latest_date != '-':
                    latest_date = latest_date[:10]
                item = QTableWidgetItem(latest_date)
                item.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(i, 4, item)
            
            logger.info(f"已下载股票列表显示完成，共 {len(downloaded_stocks)} 只")
            
        except Exception as e:
            logger.error(f"显示已下载股票列表失败: {e}", exc_info=True)
    
    def on_table_row_clicked(self, row, column):
        """处理表格行点击事件"""
        try:
            # 检查是否在已下载股票列表视图（5列）
            if self.data_table.columnCount() == 5:
                # 获取第一列的股票代码
                code_item = self.data_table.item(row, 0)
                if code_item:
                    stock_code = code_item.text().strip()
                    logger.info(f"用户点击了已下载列表中的股票: {stock_code}")
                    
                    # 自动填充股票代码到输入框
                    self.stock_code_input.setText(stock_code)
                    
                    # 获取日期范围
                    start_date = self.start_date.date().toString("yyyy-MM-dd")
                    end_date = self.end_date.date().toString("yyyy-MM-dd")
                    
                    # 加载该股票的详细日线数据
                    self._load_single_stock(stock_code, start_date, end_date)
                    
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.success(
                        title="加载成功",
                        content=f"正在显示股票 {stock_code} 的日线数据",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
            
        except Exception as e:
            logger.error(f"处理表格行点击事件失败: {e}", exc_info=True)
    
    def _set_active_button(self, active_button_name):
        """
        设置激活状态的按钮（使用主题色），其他按钮恢复普通样式
        :param active_button_name: 激活的按钮名称
        """
        try:
            # 保存当前按钮的状态，使用样式表来改变外观而不是重新创建按钮
            # 这样可以避免布局问题
            
            buttons = {
                'downloaded_list': self.downloaded_list_btn,
                'download': self.download_btn,
                'update_list': self.update_list_btn,
                'view_list': self.view_list_btn,
                'refresh': self.refresh_btn,
                'batch_download': self.batch_download_btn
            }
            
            # 主题色按钮和普通按钮的样式
            from ui.theme_manager import ThemeManager
            theme_color = ThemeManager.get_theme_color()
            
            # 定义激活状态样式（主题色）
            active_style = f"""
                QPushButton {{
                    background-color: {theme_color};
                    border: 1px solid {theme_color};
                    border-radius: 5px;
                    padding: 5px 12px;
                    color: white;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {theme_color};
                    opacity: 0.8;
                }}
                QPushButton:pressed {{
                    background-color: {theme_color};
                    padding: 6px 11px 4px 13px;
                }}
            """
            
            # 定义普通状态样式
            normal_style = """
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                    padding: 5px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 0.1);
                    padding: 6px 11px 4px 13px;
                }
            """
            
            # 应用样式到所有按钮
            for btn_name, btn in buttons.items():
                if btn_name == active_button_name:
                    btn.setStyleSheet(active_style)
                else:
                    btn.setStyleSheet(normal_style)
            
            logger.info(f"按钮状态已更新，当前激活: {active_button_name}")
            
        except Exception as e:
            logger.error(f"设置激活按钮失败: {e}", exc_info=True)
    
    def _get_market_from_code(self, code):
        """根据股票代码判断所属市场"""
        if not code:
            return "未知"
        
        # 去除可能的后缀
        code_num = code[:6] if len(code) >= 6 else code
        
        if code_num.startswith('60') or code_num.startswith('688'):
            if code_num.startswith('688'):
                return "科创板"
            else:
                return "上海主板"
        elif code_num.startswith('00'):
            return "深圳主板"
        elif code_num.startswith('002'):
            return "中小板"
        elif code_num.startswith('300'):
            return "创业板"
        elif code_num.startswith('8') or code_num.startswith('4'):
            return "北交所"
        else:
            return "其他"
    
    def load_default_data(self):
        """加载默认数据（所有股票的最新行情）"""
        try:
            # 检查是否输入了股票代码
            stock_code = self.stock_code_input.text().strip()
            
            if stock_code:
                # 如果输入了代码，只显示该股票
                if not stock_code.isdigit() or len(stock_code) != 6:
                    QMessageBox.warning(self, "警告", "股票代码格式错误！\n请输入6位数字代码")
                    self.status_label.setText("代码格式错误")
                    return
                
                self.status_label.setText(f"正在加载股票 {stock_code} 的数据...")
                start_date = self.start_date.date().toString("yyyy-MM-dd")
                end_date = self.end_date.date().toString("yyyy-MM-dd")
                self._load_single_stock(stock_code, start_date, end_date)
            else:
                # 没有输入代码，显示所有股票
                self.status_label.setText("正在加载股票行情数据...")
                self._load_all_stocks()
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}", exc_info=True)
            self.status_label.setText("数据加载失败")
            # 加载失败时显示空状态
            self.table_container.setCurrentIndex(0)
    
    def _load_all_stocks(self):
        """加载所有股票的最新行情（每只股票取最新一条）"""
        try:
            # 获取所有股票列表
            stock_list = self.data_service.get_stock_list()
            
            if stock_list is None or stock_list.empty:
                logger.info("股票列表为空，显示空状态提示")
                self.status_label.setText("暂无股票列表 - 请先更新股票列表")
                self.total_data = None
                self.table_container.setCurrentIndex(0)  # 显示空状态
                self.update_pagination_buttons()
                return
            
            # 获取日期范围
            end_date = self.end_date.date().toString("yyyy-MM-dd")
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            
            # 获取所有股票的行情数据
            all_data = self.data_service.get_all_stocks_data(start_date, end_date)
            
            if all_data is None or all_data.empty:
                logger.info("行情数据为空，显示空状态提示")
                self.status_label.setText("暂无行情数据 - 请先下载股票数据")
                self.total_data = None
                self.table_container.setCurrentIndex(0)  # 显示空状态
                self.update_pagination_buttons()
                return
            
            logger.info(f"成功获取 {len(all_data)} 条行情数据")
            
            # 确保trade_date是datetime类型
            if 'trade_date' in all_data.columns:
                if not pd.api.types.is_datetime64_any_dtype(all_data['trade_date']):
                    all_data['trade_date'] = pd.to_datetime(all_data['trade_date'])
            
            # 为每只股票只保留最新一条数据
            # 按ts_code分组，取每组最新的记录
            if 'ts_code' in all_data.columns and 'trade_date' in all_data.columns:
                try:
                    # 先排序，再去重，保留每个股票最新的记录
                    all_data = all_data.sort_values('trade_date', ascending=False)
                    # 重置索引以避免重复索引问题
                    all_data = all_data.reset_index(drop=True)
                    latest_data = all_data.drop_duplicates(subset=['ts_code'], keep='first')
                    # 再次重置索引
                    latest_data = latest_data.reset_index(drop=True)
                except Exception as e:
                    logger.warning(f"去重失败，使用全部数据: {e}")
                    latest_data = all_data.reset_index(drop=True)
            else:
                latest_data = all_data.reset_index(drop=True)
            
            # 合并股票名称信息
            stock_name_dict = {}
            for _, row in stock_list.iterrows():
                code = str(row.get('code', ''))
                code_6 = code[:6] if len(code) >= 6 else code
                stock_name_dict[code_6] = {
                    'name': row.get('name', ''),
                    'industry': row.get('industry', '-')
                }
            
            # 添加股票名称和行业列
            names = []
            industries = []
            
            for idx, row in latest_data.iterrows():
                ts_code = str(row.get('ts_code', ''))
                code_6 = ts_code[:6] if len(ts_code) >= 6 else ts_code
                info = stock_name_dict.get(code_6, {'name': '', 'industry': '-'})
                names.append(info.get('name', ''))
                industries.append(info.get('industry', '-'))
            
            latest_data = latest_data.copy()  # 创建副本避免警告
            latest_data['stock_name'] = names
            latest_data['industry'] = industries
            
            # 按交易日期降序排序
            latest_data = latest_data.sort_values('trade_date', ascending=False)
            
            logger.info(f"处理后得到 {len(latest_data)} 只股票的最新数据")
            
            # 缓存数据
            self.total_data = latest_data
            self.current_page = 1
            
            # 切换到表格视图
            self.table_container.setCurrentIndex(1)
            logger.info("切换到表格视图")
            
            # 显示第一页
            self.display_current_page()
            
            # 设置按钮激活状态（刷新所有股票数据）
            self._set_active_button('refresh')
            
        except Exception as e:
            logger.error(f"加载所有股票数据失败: {e}", exc_info=True)
            self.status_label.setText("加载失败")
            self.total_data = None
            self.table_container.setCurrentIndex(0)  # 显示空状态
            self.update_pagination_buttons()
    
    def _load_single_stock(self, stock_code, start_date, end_date):
        """加载单个股票的数据"""
        try:
            # 从数据库加载数据
            data = self.data_service.get_stock_data(stock_code, start_date, end_date)
            
            if data is None or data.empty:
                QMessageBox.information(
                    self, 
                    "提示", 
                    f"没有找到股票 {stock_code} 的数据！\n\n请先下载该股票的数据。"
                )
                self.status_label.setText(f"无数据: {stock_code}")
                self.total_data = None
                self.table_container.setCurrentIndex(0)  # 显示空状态
                self.update_pagination_buttons()
                return
            
            # 获取股票信息
            stock_list = self.data_service.get_stock_list()
            stock_name = ""
            industry = "-"
            
            if stock_list is not None and not stock_list.empty:
                # 使用 'code' 列而不是 'symbol'
                matching_stock = stock_list[stock_list['code'].str.contains(stock_code, na=False)]
                if not matching_stock.empty:
                    stock_name = matching_stock.iloc[0].get('name', '')
                    # stock_list 中没有 industry 列，使用默认值
                    industry = "-"
            
            # 添加股票代码、名称和行业列
            data['ts_code'] = stock_code
            data['stock_name'] = stock_name
            data['industry'] = industry
            
            # 按日期降序排序
            data = data.sort_values('trade_date', ascending=False)
            
            # 缓存数据
            self.total_data = data
            self.current_page = 1
            
            # 切换到表格视图
            self.table_container.setCurrentIndex(1)
            
            # 显示第一页
            self.display_current_page()
            
            # 设置按钮激活状态（显示日线数据，激活刷新按钮）
            self._set_active_button('refresh')
            
        except Exception as e:
            logger.error(f"加载单个股票数据失败: {e}", exc_info=True)
            self.status_label.setText(f"加载失败: {stock_code}")
            self.total_data = None
            self.update_pagination_buttons()
    
    def display_current_page(self):
        """显示当前页的数据"""
        if self.total_data is None or self.total_data.empty:
            return
        
        # 计算分页
        total_records = len(self.total_data)
        total_pages = (total_records + self.page_size - 1) // self.page_size
        
        # 确保当前页在有效范围内
        if self.current_page < 1:
            self.current_page = 1
        if self.current_page > total_pages:
            self.current_page = total_pages if total_pages > 0 else 1
        
        # 计算当前页的数据范围
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_records)
        
        # 获取当前页数据
        page_data = self.total_data.iloc[start_idx:end_idx]
        
        # 显示数据
        self._fill_table_with_data(page_data, start_idx)
        
        # 更新分页信息
        self.page_info_label.setText(f"第 {self.current_page} 页，共 {total_pages} 页 (共 {total_records} 条记录)")
        self.page_input.setMaximum(total_pages if total_pages > 0 else 1)
        self.page_input.setValue(self.current_page)
        
        # 更新按钮状态
        self.update_pagination_buttons()
        
        # 更新状态
        stocks_count = self.total_data['ts_code'].nunique() if 'ts_code' in self.total_data.columns else len(self.total_data)
        self.status_label.setText(f"显示第 {start_idx+1}-{end_idx} 条，共 {stocks_count} 只股票的 {total_records} 条记录")
    
    def _fill_table_with_data(self, data, start_idx):
        """填充表格数据（日线数据格式 - 10列）"""
        # 清空表格
        self.data_table.setRowCount(0)
        
        # 设置为日线数据格式（10列）
        self.data_table.setColumnCount(10)
        self.data_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "所属市场", "行业", "上市日期", 
            "日期", "收盘价", "涨跌幅", "成交量", "成交额"
        ])
        
        # 设置列宽
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        self.data_table.setRowCount(len(data))
        
        for i, (index, row) in enumerate(data.iterrows()):
            # 获取股票代码（统一格式）
            stock_code = str(row.get('ts_code', ''))
            if '.' in stock_code:
                stock_code = stock_code.split('.')[0]  # 去除后缀
            stock_code = stock_code[:6] if len(stock_code) >= 6 else stock_code
            
            # 列0: 股票代码
            code_item = QTableWidgetItem(stock_code)
            code_item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(i, 0, code_item)
            
            # 列1: 股票名称
            stock_name = str(row.get('stock_name', '-'))
            name_item = QTableWidgetItem(stock_name)
            name_item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(i, 1, name_item)
            
            # 列2: 所属市场
            market = self._get_market_from_code(stock_code)
            market_item = QTableWidgetItem(market)
            market_item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(i, 2, market_item)
            
            # 列3: 行业
            industry = str(row.get('industry', '其他'))
            industry_item = QTableWidgetItem(industry)
            industry_item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(i, 3, industry_item)
            
            # 列4: 上市日期
            list_date = str(row.get('list_date', '-'))
            if list_date and list_date != '-' and len(list_date) == 8:
                list_date = f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:]}"
            list_date_item = QTableWidgetItem(list_date)
            list_date_item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(i, 4, list_date_item)
            
            # 列5: 交易日期
            date_val = row.get('trade_date', '')
            if pd.notna(date_val):
                if isinstance(date_val, pd.Timestamp):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)[:10]
            else:
                date_str = str(row.name)[:10] if pd.notna(row.name) else '-'
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(i, 5, date_item)
            
            # 列6: 收盘价
            close_val = row.get('close', 0)
            close_item = QTableWidgetItem(f"{float(close_val):.2f}" if pd.notna(close_val) and close_val > 0 else "-")
            close_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.data_table.setItem(i, 6, close_item)
            
            # 列7: 涨跌幅
            pct_change = row.get('pct_chg', row.get('pct_change', 0))
            if pd.notna(pct_change):
                pct_item = QTableWidgetItem(f"{float(pct_change):.2f}%")
                pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                # 根据涨跌设置颜色
                if float(pct_change) > 0:
                    pct_item.setForeground(QColor(220, 38, 38))  # 红色
                elif float(pct_change) < 0:
                    pct_item.setForeground(QColor(34, 197, 94))  # 绿色
            else:
                pct_item = QTableWidgetItem("-")
                pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.data_table.setItem(i, 7, pct_item)
            
            # 列8: 成交量
            vol = row.get('vol', row.get('volume', 0))
            if pd.notna(vol) and vol > 0:
                vol_val = int(float(vol))
                # 格式化成交量（手）
                if vol_val >= 10000:
                    vol_item = QTableWidgetItem(f"{vol_val/10000:.2f}万")
                else:
                    vol_item = QTableWidgetItem(f"{vol_val:,}")
            else:
                vol_item = QTableWidgetItem("-")
            vol_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.data_table.setItem(i, 8, vol_item)
            
            # 列9: 成交额
            amount = row.get('amount', 0)
            if pd.notna(amount) and amount > 0:
                amount_val = float(amount)
                # 格式化成交额（元）
                if amount_val >= 100000000:
                    amount_item = QTableWidgetItem(f"{amount_val/100000000:.2f}亿")
                elif amount_val >= 10000:
                    amount_item = QTableWidgetItem(f"{amount_val/10000:.2f}万")
                else:
                    amount_item = QTableWidgetItem(f"{amount_val:,.0f}")
            else:
                amount_item = QTableWidgetItem("-")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.data_table.setItem(i, 9, amount_item)
    
    def update_pagination_buttons(self):
        """更新分页按钮状态"""
        if self.total_data is None or self.total_data.empty:
            total_pages = 0
        else:
            total_records = len(self.total_data)
            total_pages = (total_records + self.page_size - 1) // self.page_size
        
        # 首页和上一页
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        
        # 下一页和末页
        self.next_page_btn.setEnabled(self.current_page < total_pages)
        self.last_page_btn.setEnabled(self.current_page < total_pages)
    
    def goto_first_page(self):
        """跳转到首页"""
        self.current_page = 1
        self.display_current_page()
    
    def goto_prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()
    
    def goto_next_page(self):
        """下一页"""
        if self.total_data is not None:
            total_pages = (len(self.total_data) + self.page_size - 1) // self.page_size
            if self.current_page < total_pages:
                self.current_page += 1
                self.display_current_page()
    
    def goto_last_page(self):
        """跳转到末页"""
        if self.total_data is not None:
            total_pages = (len(self.total_data) + self.page_size - 1) // self.page_size
            self.current_page = total_pages if total_pages > 0 else 1
            self.display_current_page()
    
    def goto_page(self, page_num):
        """跳转到指定页"""
        self.current_page = page_num
        self.display_current_page()
    
    def on_page_size_changed(self, size_text):
        """每页显示条数改变"""
        self.page_size = int(size_text)
        self.current_page = 1  # 重置到第一页
        self.display_current_page()
