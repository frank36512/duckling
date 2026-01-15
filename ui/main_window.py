"""
主窗口模块 - 基于 QFluentWidgets
量化交易工具的主界面
"""

import sys
import os
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox, QLabel, QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentIcon,
                           InfoBar, InfoBarPosition, setTheme, Theme,
                           MessageBox, Dialog, Action, setThemeColor,
                           NavigationDisplayMode)
import logging
import ctypes

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.data_panel import DataPanel
from ui.strategy_panel import StrategyPanel
from ui.backtest_panel import BacktestPanel
from ui.theme_manager import ThemeManager
from utils import ConfigManager
from ui.stock_selection_panel import StockSelectionPanel
from business.data_service import get_data_service

logger = logging.getLogger(__name__)


class MainWindow(FluentWindow):
    """主窗口类 - 使用 Fluent Design"""
    
    def __init__(self, config: dict):
        """
        初始化主窗口
        :param config: 配置字典
        """
        super().__init__()
        
        self.config = config
        self.config_manager = ConfigManager()
        self.is_restarting = False  # 标志：是否正在重启
        
        # 应用视图设置
        self._apply_view_settings()
        
        # 初始化UI
        self.init_ui()
        
        # 连接QFluentWidgets的主题变化信号
        from qfluentwidgets import qconfig
        qconfig.themeChangedFinished.connect(self.on_theme_changed)
        logger.info("已连接主题变化信号")
        
        # 连接页面切换信号，当切换页面时也刷新样式
        if hasattr(self, 'stackedWidget'):
            self.stackedWidget.currentChanged.connect(self.on_page_changed)
            logger.info("已连接页面切换信号")
        
        # 设置状态栏定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 每秒更新一次
        
        # 创建选股面板实例
        self.stock_selection_panel = StockSelectionPanel()
        
        logger.info("主窗口初始化完成（Fluent Design）")
    
    def _apply_view_settings(self):
        """应用视图设置"""
        view_config = self.config.get('view', {})
        
        # 应用主题色
        theme_color = view_config.get('theme_color', '#1890ff')
        setThemeColor(theme_color)
        
        # 应用主题
        theme = view_config.get('theme', 'light')
        if theme == 'dark':
            setTheme(Theme.DARK)
        elif theme == 'auto':
            setTheme(Theme.AUTO)
        else:
            setTheme(Theme.LIGHT)
        
        # 应用字体设置
        font_size = view_config.get('font_size', 12)
        font_weight = view_config.get('font_weight', 'normal')
        
        from PyQt5.QtGui import QFont
        app_font = QFont()
        app_font.setPointSize(font_size)
        if font_weight == 'bold':
            app_font.setBold(True)
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().setFont(app_font)
        
        # 应用全局样式（确保所有控件字体大小为12）
        from ui.styles import GLOBAL_STYLE
        QApplication.instance().setStyleSheet(GLOBAL_STYLE)
        
        logger.info(f"应用视图设置: 主题={theme}, 主题色={theme_color}, 字体大小={font_size}")
    
    def init_ui(self):
        """初始化UI组件"""
        # 初始化量化选股面板实例
        self.stock_selection_panel = StockSelectionPanel()
        
        # ==================== 初始化全局数据服务 ====================
        try:
            config_dict = self.config.config if hasattr(self.config, 'config') else self.config
            data_service = get_data_service()
            data_service.initialize(config_dict)
            logger.info("✅ 全局数据服务初始化成功")
        except Exception as e:
            logger.error(f"❌ 全局数据服务初始化失败: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "初始化错误",
                f"数据服务初始化失败！\n\n{str(e)}\n\n应用可能无法正常使用数据功能。"
            )
        
        # 设置窗口图标和任务栏图标
        # 处理打包后的路径
        if getattr(sys, 'frozen', False):
            # 打包后，资源文件在 _MEIPASS 临时目录
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(__file__))
        
        # Windows任务栏需要.ico格式，窗口可以用.png
        icon_ico_path = os.path.join(base_path, 'resources', 'duck.ico')
        icon_png_path = os.path.join(base_path, 'resources', 'duck.ico')
        
        # 优先使用ico文件（用于Windows任务栏）
        icon_path = icon_ico_path if os.path.exists(icon_ico_path) else icon_png_path
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            
            # 在 Windows 上设置任务栏图标
            try:
                # 设置应用程序ID（Windows 7+必需）
                myappid = 'duckling.quant.v1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                
                # 设置 QApplication 图标（用于任务栏显示）
                QApplication.setWindowIcon(icon)
                
                logger.info(f"已设置Windows应用程序ID和任务栏图标: {icon_path}")
            except Exception as e:
                logger.warning(f"设置Windows任务栏图标失败: {e}")
            
            logger.info(f"窗口图标已设置: {icon_path}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}, ico: {icon_ico_path}, png: {icon_png_path}")
        
        # 设置窗口属性
        self.setWindowTitle("小鸭量化(Duckling) v2.0")
        
        # 应用启动窗口大小设置
        view_config = self.config.get('view', {})
        startup_size = view_config.get('startup_size', 'default')
        
        if startup_size == 'maximized':
            # 最大化窗口
            self.showMaximized()
            logger.info("窗口启动：最大化")
        elif startup_size == 'last':
            # 使用上次关闭时的大小
            window_size = self.config.get('ui', {}).get('window_size', [1366, 768])
            self.resize(window_size[0], window_size[1])
            logger.info(f"窗口启动：上次大小 {window_size[0]}x{window_size[1]}")
        else:
            # 默认大小 1366x768
            self.resize(1366, 768)
            logger.info("窗口启动：默认大小 1366x768")
        
        # 设置导航栏：固定展开，不遮挡内容
        # 方案：禁用折叠功能，始终保持展开状态
        self.navigationInterface.setExpandWidth(150)  # 设置展开宽度
        self.navigationInterface.setCollapsible(False)  # 禁用折叠（关键：这样就不会有覆盖模式）
        
        # 自定义标题栏按钮颜色（深色主题下使用柔和的白色）
        self._apply_titlebar_style()
        
        # 创建各个面板
        config_dict = self.config.config if hasattr(self.config, 'config') else self.config
        
        # 添加顶部间距（一个分隔符）
        self.navigationInterface.addSeparator(NavigationItemPosition.TOP)
        
        # 数据管理面板
        try:
            self.data_panel = DataPanel(config_dict)
            self.data_panel.setObjectName('data_panel')
            self.addSubInterface(
                self.data_panel, 
                FluentIcon.FOLDER, 
                '数据管理',
                NavigationItemPosition.TOP
            )
        except Exception as e:
            logger.error(f"创建数据面板失败: {e}", exc_info=True)
            error_widget = QLabel(f"数据面板加载失败: {e}")
            error_widget.setObjectName('data_panel_error')
            self.addSubInterface(error_widget, FluentIcon.FOLDER, '数据管理')
        
        # 策略配置面板
        try:
            self.strategy_panel = StrategyPanel(config_dict)
            self.strategy_panel.setObjectName('strategy_panel')
            self.addSubInterface(
                self.strategy_panel,
                FluentIcon.EDIT,
                '策略配置',
                NavigationItemPosition.TOP
            )
        except Exception as e:
            logger.error(f"创建策略面板失败: {e}", exc_info=True)
            error_widget = QLabel(f"策略面板加载失败: {e}")
            error_widget.setObjectName('strategy_panel_error')
            self.addSubInterface(error_widget, FluentIcon.EDIT, '策略配置')
        
        # 回测分析面板
        try:
            self.backtest_panel = BacktestPanel(config_dict)
            self.backtest_panel.setObjectName('backtest_panel')
            self.addSubInterface(
                self.backtest_panel,
                FluentIcon.HISTORY,
                '回测分析',
                NavigationItemPosition.TOP
            )
        except Exception as e:
            logger.error(f"创建回测面板失败: {e}", exc_info=True)
            error_widget = QLabel(f"回测面板加载失败: {e}")
            error_widget.setObjectName('backtest_panel_error')
            self.addSubInterface(error_widget, FluentIcon.HISTORY, '回测分析')
        
        # 策略对比面板
        try:
            from ui.comparison_panel import ComparisonPanel
            self.comparison_panel = ComparisonPanel(config_dict)
            self.comparison_panel.setObjectName('comparison_panel')
            self.addSubInterface(
                self.comparison_panel,
                FluentIcon.TILES,
                '策略对比',
                NavigationItemPosition.TOP
            )
            logger.info("策略对比面板加载成功")
        except Exception as e:
            logger.error(f"创建策略对比面板失败: {e}", exc_info=True)
        
        # 参数优化面板
        try:
            from ui.optimization_panel import OptimizationPanel
            self.optimization_panel = OptimizationPanel(config_dict)
            self.optimization_panel.setObjectName('optimization_panel')
            self.addSubInterface(
                self.optimization_panel,
                FluentIcon.COMMAND_PROMPT,
                '参数优化',
                NavigationItemPosition.TOP
            )
            logger.info("参数优化面板加载成功")
        except Exception as e:
            logger.error(f"创建参数优化面板失败: {e}", exc_info=True)
        
        # 量化选股面板（移到参数优化后面）
        try:
            self.stock_selection_panel.setObjectName('stock_selection_panel')
            self.addSubInterface(
                self.stock_selection_panel, 
                FluentIcon.FILTER, 
                "量化选股", 
                NavigationItemPosition.TOP
            )
            logger.info("量化选股面板加载成功")
        except Exception as e:
            logger.error(f"创建量化选股面板失败: {e}", exc_info=True)
        
        # 实时监控面板
        try:
            from ui.monitor_panel import MonitorPanel
            self.monitor_panel = MonitorPanel(config_dict)
            self.monitor_panel.setObjectName('monitor_panel')
            self.addSubInterface(
                self.monitor_panel,
                FluentIcon.SPEED_HIGH,
                '实时监控',
                NavigationItemPosition.TOP
            )
            logger.info("实时监控面板加载成功")
        except Exception as e:
            logger.error(f"创建实时监控面板失败: {e}", exc_info=True)
        
        # 自动交易面板
        try:
            from ui.auto_trading_panel import AutoTradingPanel
            self.auto_trading_panel = AutoTradingPanel(config_dict)
            self.auto_trading_panel.setObjectName('auto_trading_panel')
            self.addSubInterface(
                self.auto_trading_panel,
                FluentIcon.ROBOT,
                '自动交易',
                NavigationItemPosition.TOP
            )
            logger.info("自动交易面板加载成功")
        except Exception as e:
            logger.error(f"创建自动交易面板失败: {e}", exc_info=True)
        
        # 实盘交易面板
        try:
            from ui.trading_panel import TradingPanel
            self.trading_panel = TradingPanel(config_dict)
            self.trading_panel.setObjectName('trading_panel')
            self.addSubInterface(
                self.trading_panel,
                FluentIcon.SHOPPING_CART,
                '实盘交易',
                NavigationItemPosition.SCROLL
            )
            logger.info("实盘交易面板加载成功")
        except Exception as e:
            logger.error(f"创建实盘交易面板失败: {e}", exc_info=True)
        
        # 添加底部导航项
        # 设置
        self.navigationInterface.addItem(
            routeKey='settings',
            icon=FluentIcon.SETTING,
            text='设置',
            onClick=self.show_settings,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )
        
        # 帮助
        self.navigationInterface.addItem(
            routeKey='help',
            icon=FluentIcon.HELP,
            text='帮助',
            onClick=self.show_help,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )
        
        # 关于
        self.navigationInterface.addItem(
            routeKey='about',
            icon=FluentIcon.INFO,
            text='关于',
            onClick=self.show_about,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )
        
        # 居中显示
        self.center_window()
    
    def _apply_titlebar_style(self):
        """自定义标题栏样式 - 调整按钮图标颜色"""
        from qfluentwidgets import isDarkTheme
        from PyQt5.QtWidgets import QPushButton, QWidget
        from PyQt5.QtGui import QColor, QIcon
        from PyQt5.QtCore import QSize
        
        if not hasattr(self, 'titleBar'):
            logger.debug("titleBar 属性不存在")
            return
        
        is_dark = isDarkTheme()
        if not is_dark:
            return  # 只在深色主题下调整
        
        try:
            # 深色主题下，直接设置标题栏按钮的颜色属性
            # 不使用 setStyleSheet，避免覆盖图标显示
            from PyQt5.QtGui import QColor
            
            # 获取标题栏的按钮
            if hasattr(self.titleBar, 'minBtn') and hasattr(self.titleBar, 'maxBtn') and hasattr(self.titleBar, 'closeBtn'):
                # 为每个按钮设置柔和的颜色
                soft_white = QColor(255, 255, 255, 180)  # 70% 不透明度
                hover_white = QColor(255, 255, 255, 230)  # 90% 不透明度
                
                for btn in [self.titleBar.minBtn, self.titleBar.maxBtn, self.titleBar.closeBtn]:
                    # 尝试设置按钮的图标颜色（如果支持）
                    if hasattr(btn, 'setIconColor'):
                        btn.setIconColor(soft_white)
                
                logger.info("标题栏按钮颜色已调整（深色主题）")
            else:
                logger.debug("标题栏按钮属性不存在，跳过颜色调整")
            
        except Exception as e:
            logger.debug(f"调整标题栏按钮颜色失败: {e}")
    
    def center_window(self):
        """窗口居中"""
        from PyQt5.QtWidgets import QDesktopWidget
        
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def update_status(self):
        """更新状态栏 - 显示交易时间信息"""
        from datetime import datetime
        
        # 检查是否在交易时间
        now = datetime.now()
        is_trading_time = False
        if now.weekday() < 5:  # 周一到周五
            time_now = now.time()
            from datetime import time
            if (time(9, 30) <= time_now <= time(11, 30)) or (time(13, 0) <= time_now <= time(15, 0)):
                is_trading_time = True
        
        if is_trading_time:
            # 在交易时间显示提示
            pass  # FluentWindow 没有传统状态栏，可以用其他方式显示
    
    def on_theme_changed(self):
        """QFluentWidgets主题变化的回调（官方信号）"""
        try:
            logger.info("检测到主题变化，开始刷新面板样式...")
            self._apply_titlebar_style()  # 刷新标题栏样式
            self.refresh_panel_styles()
        except Exception as e:
            logger.error(f"主题变化处理失败: {e}", exc_info=True)
    
    def on_page_changed(self, index):
        """页面切换的回调 - 刷新当前页面的样式"""
        try:
            # 获取当前页面的widget
            current_widget = self.stackedWidget.widget(index)
            if current_widget:
                from ui.theme_manager import ThemeManager
                panel_style = ThemeManager.get_panel_stylesheet()
                current_widget.setStyleSheet(panel_style)
                current_widget.update()
                logger.debug(f"页面切换，刷新了 {current_widget.__class__.__name__} 的样式")
        except Exception as e:
            logger.warning(f"页面切换时刷新样式失败: {e}")
    
    def refresh_panel_styles(self):
        """刷新所有面板的样式（主题切换后调用）
        注意：QFluentWidgets控件会自动响应qconfig.themeChanged信号，
        这里只需要更新容器（面板）的样式表即可
        """
        try:
            from ui.theme_manager import ThemeManager
            from qfluentwidgets import isDarkTheme
            from PyQt5.QtWidgets import QApplication
            
            panel_style = ThemeManager.get_panel_stylesheet()
            is_dark = isDarkTheme()
            
            logger.info(f"开始刷新面板样式，当前主题: {'深色' if is_dark else '浅色'}")
            
            # 获取所有面板
            panels = [
                self.data_panel,
                self.stock_selection_panel,
                self.strategy_panel,
                self.backtest_panel,
                self.comparison_panel,
                self.optimization_panel,
                self.monitor_panel,
                self.auto_trading_panel,
                self.trading_panel
            ]
            
            # QFluentWidgets控件会自动响应qconfig.themeChanged信号
            # 这里只需要更新面板容器的样式表
            for panel in panels:
                if panel:
                    logger.info(f"刷新面板: {panel.__class__.__name__}")
                    panel.setStyleSheet(panel_style)
                    panel.update()
            
            # 处理事件队列，确保UI更新
            QApplication.processEvents()
            
            logger.info("面板样式刷新完成")
        except Exception as e:
            logger.error(f"刷新面板样式失败: {e}", exc_info=True)
    
    def show_settings(self):
        """显示设置对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QWidget, QFormLayout, QGroupBox
        from PyQt5.QtCore import Qt
        from qfluentwidgets import ComboBox, LineEdit, SpinBox, FluentWindow
        
        # 创建设置对话框 - 使用无边框QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setModal(True)
        dialog.resize(720, 620)
        # 设置无边框和半透明背景效果
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建自定义标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 0, 5, 0)
        
        title_label = QLabel("设置")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        
        # 关闭按钮
        from qfluentwidgets import TransparentToolButton, FluentIcon
        close_btn = TransparentToolButton(FluentIcon.CLOSE)
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(dialog.reject)
        title_bar_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 20)
        
        # 根据当前主题设置对话框样式
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            # 深色主题样式
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                QLabel {
                    color: #e0e0e0;
                }
            """)
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: #202020;
                    color: #d0d0d0;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
                QLabel {
                    color: #c0c0c0;
                    background-color: transparent;
                }
                QGroupBox {
                    color: #a0a0a0;
                    background-color: transparent;
                    border: 1px solid #3a3a3a;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                }
                QTabWidget::pane {
                    border: 1px solid #3a3a3a;
                    background-color: #2b2b2b;
                    border-radius: 5px;
                }
                QTabBar::tab {
                    background-color: #2b2b2b;
                    color: #909090;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border: 1px solid #3a3a3a;
                    border-bottom: none;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }
                QTabBar::tab:selected {
                    background-color: #2b2b2b;
                    color: #b0b0b0;
                    border-bottom-color: #2b2b2b;
                }
                QTabBar::tab:hover {
                    background-color: #3a3a3a;
                    color: #c0c0c0;
                }
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #4a4a4a;
                    min-height: 30px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5a5a5a;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #2a2a2a;
                    color: #d0d0d0;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 3px;
                }
                QSpinBox:hover, QDoubleSpinBox:hover {
                    border-color: #4a4a4a;
                }
                QSpinBox:focus, QDoubleSpinBox:focus {
                    border-color: #555555;
                }
            """)
        else:
            # 浅色主题样式
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                QLabel {
                    color: #262626;
                }
            """)
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: #fafafa;
                    color: #262626;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
                QLabel {
                    color: #262626;
                    background-color: transparent;
                }
                QGroupBox {
                    color: #262626;
                    background-color: transparent;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    color: #1890ff;
                }
                QTabWidget::pane {
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    background-color: #fafafa;
                    border-radius: 5px;
                }
                QTabBar::tab {
                    background-color: #f5f5f5;
                    color: #595959;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-bottom: none;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }
                QTabBar::tab:selected {
                    background-color: #fafafa;
                    color: #1890ff;
                }
                QTabBar::tab:hover {
                    background-color: #e6f7ff;
                }
                QScrollBar:vertical {
                    background-color: #fafafa;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(0, 0, 0, 0.2);
                    min-height: 30px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(0, 0, 0, 0.3);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #ffffff;
                    color: #262626;
                    border: 1px solid rgba(0, 0, 0, 0.15);
                    border-radius: 3px;
                    padding: 3px;
                }
            """)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        content_layout.addWidget(tab_widget)
        
        # === 数据源设置 ===
        from PyQt5.QtWidgets import QWidget, QFormLayout, QGroupBox
        data_tab = QWidget()
        data_tab.setStyleSheet(ThemeManager.get_panel_stylesheet())
        data_layout = QVBoxLayout(data_tab)
        
        # 数据源选择
        data_group = QGroupBox("数据源配置")
        data_form = QFormLayout()
        
        primary_combo = ComboBox()
        primary_combo.addItems(["AKShare（免费）", "Tushare Pro（需积分）"])
        current_source = self.config.get('data_source', {}).get('primary', 'akshare')
        primary_combo.setCurrentIndex(0 if current_source == 'akshare' else 1)
        data_form.addRow("主数据源：", primary_combo)
        
        # Tushare Token
        token_edit = LineEdit()
        token_edit.setText(self.config.get('data_source', {}).get('tushare', {}).get('token', ''))
        token_edit.setPlaceholderText("请输入Tushare Pro的token")
        data_form.addRow("Tushare Token：", token_edit)
        
        data_group.setLayout(data_form)
        data_layout.addWidget(data_group)
        data_layout.addStretch()
        
        # === 券商设置 ===
        broker_tab = QWidget()
        broker_tab.setStyleSheet(ThemeManager.get_panel_stylesheet())
        broker_layout = QVBoxLayout(broker_tab)
        
        # 交易模式组
        mode_group = QGroupBox("交易模式")
        mode_form = QFormLayout()
        
        mode_combo = ComboBox()
        mode_combo.addItems(["模拟交易", "实盘交易"])
        broker_mode = self.config.get('broker', {}).get('mode', 'simulated')
        mode_combo.setCurrentIndex(0 if broker_mode == 'simulated' else 1)
        mode_form.addRow("模式：", mode_combo)
        
        mode_group.setLayout(mode_form)
        broker_layout.addWidget(mode_group)
        
        # 券商配置组
        broker_group = QGroupBox("券商配置")
        broker_form = QFormLayout()
        
        broker_combo = ComboBox()
        broker_combo.addItems([
            "东方财富",
            "华泰证券",
            "中信证券", 
            "国泰君安",
            "招商证券",
            "广发证券",
            "海通证券"
        ])
        current_broker = self.config.get('broker', {}).get('type', 'eastmoney')
        broker_map = {
            'eastmoney': 0, 'huatai': 1, 'citic': 2, 
            'guotai_junan': 3, 'guangfa': 4, 'guangfa': 5, 'haitong': 6
        }
        broker_combo.setCurrentIndex(broker_map.get(current_broker, 0))
        broker_form.addRow("选择券商：", broker_combo)
        
        # 模拟资金（只在模拟模式显示）
        sim_cash_spin = SpinBox()
        sim_cash_spin.setRange(10000, 100000000)
        sim_cash_spin.setSingleStep(10000)
        sim_cash_spin.setValue(int(self.config.get('broker', {}).get('simulated_cash', 100000)))
        sim_cash_spin.setSuffix(" 元")
        broker_form.addRow("模拟资金：", sim_cash_spin)
        
        broker_group.setLayout(broker_form)
        broker_layout.addWidget(broker_group)
        
        # 实盘账号配置（只在实盘模式显示）
        real_group = QGroupBox("实盘账号配置")
        real_form = QFormLayout()
        
        account_edit = LineEdit()
        account_edit.setText(self.config.get('broker', {}).get('account_id', ''))
        account_edit.setPlaceholderText("请输入资金账号")
        real_form.addRow("资金账号：", account_edit)
        
        password_edit = LineEdit()
        password_edit.setEchoMode(LineEdit.Password)
        password_edit.setText(self.config.get('broker', {}).get('password', ''))
        password_edit.setPlaceholderText("请输入登录密码")
        real_form.addRow("登录密码：", password_edit)
        
        trade_password_edit = LineEdit()
        trade_password_edit.setEchoMode(LineEdit.Password)
        trade_password_edit.setText(self.config.get('broker', {}).get('trade_password', ''))
        trade_password_edit.setPlaceholderText("请输入交易密码（部分券商需要）")
        real_form.addRow("交易密码：", trade_password_edit)
        
        # API配置（高级选项）
        api_key_edit = LineEdit()
        api_key_edit.setText(self.config.get('broker', {}).get('api_key', ''))
        api_key_edit.setPlaceholderText("API Key（如有）")
        real_form.addRow("API Key：", api_key_edit)
        
        api_secret_edit = LineEdit()
        api_secret_edit.setEchoMode(LineEdit.Password)
        api_secret_edit.setText(self.config.get('broker', {}).get('api_secret', ''))
        api_secret_edit.setPlaceholderText("API Secret（如有）")
        real_form.addRow("API Secret：", api_secret_edit)
        
        # 服务器地址
        server_edit = LineEdit()
        server_edit.setText(self.config.get('broker', {}).get('server_url', ''))
        server_edit.setPlaceholderText("服务器地址（默认使用券商标准地址）")
        real_form.addRow("服务器：", server_edit)
        
        real_group.setLayout(real_form)
        broker_layout.addWidget(real_group)
        
        # 根据模式切换显示/隐藏实盘配置
        def on_mode_changed(index):
            real_group.setVisible(index == 1)  # 1=实盘交易
            sim_cash_spin.setEnabled(index == 0)  # 0=模拟交易
        
        mode_combo.currentIndexChanged.connect(on_mode_changed)
        on_mode_changed(mode_combo.currentIndex())
        
        # 安全密码组
        security_group = QGroupBox("安全密码")
        security_form = QFormLayout()
        
        security_pwd_edit = LineEdit()
        security_pwd_edit.setEchoMode(LineEdit.Password)
        security_pwd_edit.setPlaceholderText("输入6位数字安全密码")
        security_pwd_edit.setText(self.config.get('broker', {}).get('security_password', ''))
        security_form.addRow("安全密码：", security_pwd_edit)
        
        security_group.setLayout(security_form)
        broker_layout.addWidget(security_group)
        
        # 重要提示框
        warning_label = QLabel(
            "⚠️ 重要提示：\n"
            "• 模拟交易：使用虚拟资金测试策略，不会产生实际交易\n"
            "• 实盘交易：连接真实券商账户，会产生实际交易和费用\n"
            "• 账号密码使用加密存储，请妥善保管\n"
            "• 建议先用模拟盘测试策略后再使用实盘\n"
            "• 投资有风险，请谨慎设置参数和风控策略"
        )
        if isDarkTheme():
            warning_label.setStyleSheet(
                "color: #ffecb3; padding: 12px; background: rgba(255, 193, 7, 0.2); "
                "border: 1px solid #ffc107; border-radius: 5px; margin: 10px 0;"
            )
        else:
            warning_label.setStyleSheet(
                "color: #856404; padding: 12px; background: #fff3cd; "
                "border: 1px solid #ffc107; border-radius: 5px; margin: 10px 0;"
            )
        broker_layout.addWidget(warning_label)
        
        broker_layout.addStretch()
        
        # === 回测设置 ===
        backtest_tab = QWidget()
        backtest_tab.setStyleSheet(ThemeManager.get_panel_stylesheet())
        backtest_layout = QVBoxLayout(backtest_tab)
        
        backtest_group = QGroupBox("回测参数")
        backtest_form = QFormLayout()
        
        cash_spin = SpinBox()
        cash_spin.setRange(10000, 10000000)
        cash_spin.setSingleStep(10000)
        cash_spin.setValue(int(self.config.get('backtest', {}).get('initial_cash', 100000)))
        backtest_form.addRow("初始资金：", cash_spin)
        
        commission_spin = SpinBox()
        commission_spin.setRange(1, 100)
        commission_spin.setValue(int(self.config.get('backtest', {}).get('commission', 0.0003) * 10000))
        commission_spin.setSuffix(" (万分之)")
        backtest_form.addRow("手续费率：", commission_spin)
        
        backtest_group.setLayout(backtest_form)
        backtest_layout.addWidget(backtest_group)
        backtest_layout.addStretch()
        
        # === 安全设置 ===
        # 提前导入需要的类
        from qfluentwidgets import PushButton, PrimaryPushButton
        
        security_tab = QWidget()
        security_tab.setStyleSheet(ThemeManager.get_panel_stylesheet())
        security_layout = QVBoxLayout(security_tab)
        
        # 启动密码
        password_group = QGroupBox("启动密码")
        password_form = QFormLayout()
        
        password_status_label = QLabel()
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from utils_auth import AuthManager
        auth_manager = AuthManager()
        if auth_manager.is_password_set():
            password_status_label.setText("✅ 已设置")
            password_status_label.setStyleSheet("color: green;")
        else:
            password_status_label.setText("❌ 未设置")

            password_status_label.setStyleSheet("color: #999;")
        password_form.addRow("密码状态：", password_status_label)
        
        change_password_btn = PushButton()
        change_password_btn.setText("修改密码")
        
        def change_password():
            """修改启动密码"""
            from ui.auth_dialogs import PasswordSetDialog
            dialog = PasswordSetDialog(self)
            if dialog.exec():
                old_pwd, new_pwd, confirm_pwd = dialog.get_passwords()
                
                # 验证原密码
                if auth_manager.is_password_set():
                    if not auth_manager.verify_password(old_pwd):
                        InfoBar.error(
                            title='错误',
                            content='原密码错误',
                            orient=Qt.Horizontal,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                        return
                
                # 设置新密码
                if auth_manager.set_password(new_pwd):
                    if new_pwd:
                        password_status_label.setText("✅ 已设置")
                        password_status_label.setStyleSheet("color: green;")
                        InfoBar.success(
                            title='成功',
                            content='启动密码已更新',
                            orient=Qt.Horizontal,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                    else:
                        password_status_label.setText("❌ 未设置")
                        password_status_label.setStyleSheet("color: #999;")
                        InfoBar.success(
                            title='成功',
                            content='已取消启动密码',
                            orient=Qt.Horizontal,
                            position=InfoBarPosition.TOP,
                            duration=2000,
                            parent=self
                        )
                else:
                    InfoBar.error(
                        title='错误',
                        content='密码设置失败',
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
        
        change_password_btn.clicked.connect(change_password)
        password_form.addRow("", change_password_btn)
        
        password_group.setLayout(password_form)
        security_layout.addWidget(password_group)
        
        # 软件激活
        license_group = QGroupBox("软件激活")
        license_form = QFormLayout()
        
        # 激活状态
        license_info = auth_manager.get_license_info()
        activation_status_label = QLabel()
        if license_info.get('activated'):
            expire_date = license_info.get('expire_date', '')
            activation_status_label.setText(f"✅ 已激活（有效期至 {expire_date[:10]}）")
            activation_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            activation_status_label.setText("❌ 未激活")
            activation_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        license_form.addRow("激活状态：", activation_status_label)
        
        # 试用信息
        trial_info = auth_manager.get_trial_info()
        if trial_info.get('active'):
            trial_status_label = QLabel()
            remaining_days = trial_info.get('remaining_days', 0)
            expire_date = trial_info.get('expire_date', '')
            
            if remaining_days <= 7:
                trial_status_label.setText(f"⚠️ 试用中（剩余 {remaining_days} 天，到期日期：{expire_date}）")
                trial_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            else:
                trial_status_label.setText(f"✅ 试用中（剩余 {remaining_days} 天，到期日期：{expire_date}）")
                trial_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            license_form.addRow("试用状态：", trial_status_label)
        elif 'expire_date' in trial_info:
            # 试用已过期
            trial_status_label = QLabel()
            trial_status_label.setText(f"❌ 试用已过期（到期日期：{trial_info.get('expire_date', '')}）")
            trial_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            license_form.addRow("试用状态：", trial_status_label)
        
        # 机器码
        machine_code_edit = LineEdit()
        machine_code_edit.setText(license_info.get('machine_code', ''))
        machine_code_edit.setReadOnly(True)
        license_form.addRow("机器码：", machine_code_edit)
        
        # 激活按钮
        activate_btn_layout = QHBoxLayout()
        
        activate_btn = PrimaryPushButton()
        activate_btn.setText("激活/重新激活")
        
        def activate_software():
            """激活软件"""
            from ui.auth_dialogs import ActivationDialog
            activation_dialog = ActivationDialog(auth_manager.get_machine_code(), self)
            result = activation_dialog.exec()
            
            if result == 1:  # 激活
                activation_code = activation_dialog.get_activation_code()
                if not activation_code:
                    InfoBar.warning(
                        title='警告',
                        content='请输入注册码',
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return
                
                success, message = auth_manager.activate(activation_code)
                if success:
                    activation_status_label.setText("✅ 已激活")
                    activation_status_label.setStyleSheet("color: green;")
                    InfoBar.success(
                        title='激活成功',
                        content=message,
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                else:
                    InfoBar.error(
                        title='激活失败',
                        content=message,
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
            elif result == 2:  # 试用模式
                InfoBar.info(
                    title='试用模式',
                    content='已启动试用模式',
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        
        activate_btn.clicked.connect(activate_software)
        activate_btn_layout.addWidget(activate_btn)
        activate_btn_layout.addStretch()
        
        license_form.addRow("", activate_btn_layout)
        
        license_group.setLayout(license_form)
        security_layout.addWidget(license_group)
        
        # 说明信息
        security_info_label = QLabel(
            "📌 安全说明：\n"
            "• 启动密码：保护软件不被他人随意打开\n"
            "• 软件激活：激活后才能使用完整功能\n"
            "• 机器码：每台电脑的唯一标识，用于生成注册码\n"
            "• 注册码：与机器码绑定，仅在当前电脑有效"
        )
        if isDarkTheme():
            security_info_label.setStyleSheet(
                "color: #b3e5fc; padding: 10px; background: rgba(23, 162, 184, 0.2); "
                "border-radius: 5px; font-size: 12px;"
            )
        else:
            security_info_label.setStyleSheet(
                "color: #004085; padding: 10px; background: #d1ecf1; "
                "border-radius: 5px; font-size: 12px;"
            )
        security_layout.addWidget(security_info_label)
        
        security_layout.addStretch()
        
        # === 视图设置 ===
        view_tab = QWidget()
        view_tab.setStyleSheet(ThemeManager.get_panel_stylesheet())
        view_layout = QVBoxLayout(view_tab)
        view_layout.setSpacing(15)
        
        # 主题设置组
        theme_group = QGroupBox("主题设置")
        theme_form = QFormLayout()
        theme_form.setVerticalSpacing(12)
        theme_form.setLabelAlignment(Qt.AlignRight)
        
        # 主题选择
        theme_combo = ComboBox()
        theme_combo.addItems(["浅色主题", "深色主题", "跟随系统"])
        current_theme = self.config.get('view', {}).get('theme', 'light')
        theme_index = {'light': 0, 'dark': 1, 'auto': 2}.get(current_theme, 0)
        theme_combo.setCurrentIndex(theme_index)
        theme_form.addRow("主题：", theme_combo)
        
        # 主题色选择
        color_combo = ComboBox()
        color_combo.addItems([
            "蓝色（默认）",
            "绿色",
            "紫色",
            "橙色",
            "红色",
            "青色"
        ])
        current_color = self.config.get('view', {}).get('theme_color', '#1890ff')
        color_map = {
            '#1890ff': 0,  # 蓝色
            '#52c41a': 1,  # 绿色
            '#722ed1': 2,  # 紫色
            '#fa8c16': 3,  # 橙色
            '#f5222d': 4,  # 红色
            '#13c2c2': 5   # 青色
        }
        color_combo.setCurrentIndex(color_map.get(current_color, 0))
        theme_form.addRow("主题色：", color_combo)
        
        theme_group.setLayout(theme_form)
        view_layout.addWidget(theme_group)
        
        # 字体设置组
        font_group = QGroupBox("字体设置")
        font_form = QFormLayout()
        font_form.setVerticalSpacing(12)
        font_form.setLabelAlignment(Qt.AlignRight)
        
        # 字体大小
        font_size_spin = SpinBox()
        font_size_spin.setRange(10, 20)
        font_size_spin.setValue(self.config.get('view', {}).get('font_size', 12))
        font_size_spin.setSuffix(" px")
        font_form.addRow("字体大小：", font_size_spin)
        
        # 字体粗细
        font_weight_combo = ComboBox()
        font_weight_combo.addItems(["正常", "加粗"])
        current_weight = self.config.get('view', {}).get('font_weight', 'normal')
        font_weight_combo.setCurrentIndex(0 if current_weight == 'normal' else 1)
        font_form.addRow("字体粗细：", font_weight_combo)
        
        font_group.setLayout(font_form)
        view_layout.addWidget(font_group)
        
        # 表格设置组
        table_group = QGroupBox("表格设置")
        table_form = QFormLayout()
        table_form.setVerticalSpacing(12)
        table_form.setLabelAlignment(Qt.AlignRight)
        
        # 行高
        row_height_spin = SpinBox()
        row_height_spin.setRange(30, 60)
        row_height_spin.setValue(self.config.get('view', {}).get('row_height', 40))
        row_height_spin.setSuffix(" px")
        table_form.addRow("表格行高：", row_height_spin)
        
        # 斑马纹
        zebra_combo = ComboBox()
        zebra_combo.addItems(["显示", "隐藏"])
        zebra_enabled = self.config.get('view', {}).get('zebra_stripes', True)
        zebra_combo.setCurrentIndex(0 if zebra_enabled else 1)
        table_form.addRow("斑马纹：", zebra_combo)
        
        # 表格边框
        border_combo = ComboBox()
        border_combo.addItems(["显示", "隐藏"])
        border_enabled = self.config.get('view', {}).get('table_border', True)
        border_combo.setCurrentIndex(0 if border_enabled else 1)
        table_form.addRow("表格边框：", border_combo)
        
        table_group.setLayout(table_form)
        view_layout.addWidget(table_group)
        
        # 其他设置组
        other_group = QGroupBox("其他设置")
        other_form = QFormLayout()
        other_form.setVerticalSpacing(12)
        other_form.setLabelAlignment(Qt.AlignRight)
        
        # 动画效果
        animation_combo = ComboBox()
        animation_combo.addItems(["启用", "禁用"])
        animation_enabled = self.config.get('view', {}).get('animation', True)
        animation_combo.setCurrentIndex(0 if animation_enabled else 1)
        other_form.addRow("动画效果：", animation_combo)
        
        # 启动时窗口大小
        window_size_combo = ComboBox()
        window_size_combo.addItems(["最大化", "上次关闭时大小", "默认大小"])
        current_size = self.config.get('view', {}).get('startup_size', 'maximized')
        size_index = {'maximized': 0, 'last': 1, 'default': 2}.get(current_size, 0)
        window_size_combo.setCurrentIndex(size_index)
        other_form.addRow("启动窗口：", window_size_combo)
        
        other_group.setLayout(other_form)
        view_layout.addWidget(other_group)
        
        # 说明信息
        view_info_label = QLabel(
            "💡 提示：\n"
            "• 修改主题、主题色和字体后会立即应用，无需重启\n"
            "• 表格设置会在下次打开面板时生效\n"
            "• 动画效果可能会影响低配置电脑的性能"
        )
        if isDarkTheme():
            view_info_label.setStyleSheet(
                "color: #b3e5fc; padding: 10px; background: rgba(23, 162, 184, 0.2); "
                "border-radius: 5px; font-size: 12px;"
            )
        else:
            view_info_label.setStyleSheet(
                "color: #004085; padding: 10px; background: #d1ecf1; "
                "border-radius: 5px; font-size: 12px;"
            )
        view_layout.addWidget(view_info_label)
        
        view_layout.addStretch()
        
        # 添加选项卡
        tab_widget.addTab(data_tab, "数据源")
        tab_widget.addTab(broker_tab, "券商")
        tab_widget.addTab(backtest_tab, "回测")
        tab_widget.addTab(view_tab, "视图")
        tab_widget.addTab(security_tab, "安全")
        
        # 按钮
        btn_layout = QHBoxLayout()
        content_layout.addLayout(btn_layout)
        
        # 添加测试连接按钮
        test_btn = PushButton()
        test_btn.setText("测试连接")
        
        def test_broker_connection():
            """测试券商连接"""
            if mode_combo.currentIndex() == 0:  # 模拟交易
                InfoBar.info(
                    title='模拟交易',
                    content='当前为模拟交易模式，无需连接券商',
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:  # 实盘交易
                # 检查必填字段
                if not account_edit.text() or not password_edit.text():
                    InfoBar.warning(
                        title='警告',
                        content='请填写账号和密码',
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return
                
                # 尝试连接券商
                InfoBar.info(
                    title='连接中',
                    content='正在连接券商服务器...',
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                
                # TODO: 实际连接逻辑
                # try:
                #     from business.broker_api import BrokerType, RealBrokerConfig, EastMoneyBroker
                #     broker_types_map = {
                #         0: BrokerType.EASTMONEY,
                #         1: BrokerType.HUATAI,
                #         2: BrokerType.CITIC,
                #         # ...
                #     }
                #     config = RealBrokerConfig(
                #         broker_type=broker_types_map[broker_combo.currentIndex()],
                #         account_id=account_edit.text(),
                #         password=password_edit.text(),
                #         trade_password=trade_password_edit.text(),
                #         api_key=api_key_edit.text(),
                #         api_secret=api_secret_edit.text(),
                #         server_url=server_edit.text()
                #     )
                #     broker = EastMoneyBroker(config)
                #     if broker.connect():
                #         InfoBar.success(...)
                #     else:
                #         InfoBar.error(...)
                # except Exception as e:
                #     InfoBar.error(...)
                
                InfoBar.warning(
                    title='功能开发中',
                    content='实盘交易功能正在开发中，敬请期待',
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        
        test_btn.clicked.connect(test_broker_connection)
        btn_layout.addWidget(test_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = PushButton()
        cancel_btn.setText("取消")
        cancel_btn.clicked.connect(dialog.reject)
        
        save_btn = PrimaryPushButton()
        save_btn.setText("保存")
        
        def save_settings():
            # 禁用保存按钮，避免重复点击
            save_btn.setEnabled(False)
            
            try:
                # 获取修改前的主题和颜色
                old_theme = self.config.get('view', {}).get('theme', 'light')
                old_color = self.config.get('view', {}).get('theme_color', '#1890ff')
                old_font_size = self.config.get('view', {}).get('font_size', 12)
                old_font_weight = self.config.get('view', {}).get('font_weight', 'normal')
                
                # 获取新的主题设置
                theme_map = {0: 'light', 1: 'dark', 2: 'auto'}
                new_theme = theme_map[theme_combo.currentIndex()]
                
                color_map = {
                    0: '#1890ff',  # 蓝色
                    1: '#52c41a',  # 绿色
                    2: '#722ed1',  # 紫色
                    3: '#fa8c16',  # 橙色
                    4: '#f5222d',  # 红色
                    5: '#13c2c2'   # 青色
                }
                new_color = color_map[color_combo.currentIndex()]
                
                new_font_size = font_size_spin.value()
                new_font_weight = 'normal' if font_weight_combo.currentIndex() == 0 else 'bold'
                
                # 检查主题是否变更
                theme_changed = new_theme != old_theme
                color_changed = new_color != old_color
                font_changed = new_font_size != old_font_size or new_font_weight != old_font_weight
                
                # 如果主题变更，先弹出确认对话框
                if theme_changed:
                    msg_box = MessageBox(
                        '确认重启',
                        '主题变更后需要重启软件才能完全应用。\n\n确认保存设置并重启软件吗？',
                        dialog  # 使用dialog作为父窗口，确保显示在设置对话框前面
                    )
                    if msg_box.exec() != 1:  # 用户点击取消
                        save_btn.setEnabled(True)  # 重新启用保存按钮
                        return
            except Exception as e:
                logger.error(f"保存设置时出错: {e}")
                save_btn.setEnabled(True)  # 出错时重新启用按钮
                return
            
            # 用户确认后，开始保存配置
            # 同步 self.config 到 config_manager.config
            self.config_manager.config = self.config
            
            # 保存数据源设置
            source = 'akshare' if primary_combo.currentIndex() == 0 else 'tushare'
            self.config_manager.config['data_source']['primary'] = source
            if token_edit.text():
                self.config_manager.config['data_source']['tushare']['token'] = token_edit.text()
            
            # 保存券商设置
            if 'broker' not in self.config_manager.config:
                self.config_manager.config['broker'] = {}
            
            # 交易模式
            self.config_manager.config['broker']['mode'] = 'simulated' if mode_combo.currentIndex() == 0 else 'real'
            
            # 券商类型
            broker_types = ['eastmoney', 'huatai', 'citic', 'guotai_junan', 'zhaoshang', 'guangfa', 'haitong']
            self.config_manager.config['broker']['type'] = broker_types[broker_combo.currentIndex()]
            
            # 模拟资金
            self.config_manager.config['broker']['simulated_cash'] = sim_cash_spin.value()
            
            # 实盘账号信息（只在实盘模式保存）
            if mode_combo.currentIndex() == 1:
                self.config_manager.config['broker']['account_id'] = account_edit.text()
                self.config_manager.config['broker']['password'] = password_edit.text()  # 注意：生产环境应该加密
                self.config_manager.config['broker']['trade_password'] = trade_password_edit.text()
                self.config_manager.config['broker']['api_key'] = api_key_edit.text()
                self.config_manager.config['broker']['api_secret'] = api_secret_edit.text()
                self.config_manager.config['broker']['server_url'] = server_edit.text()
            
            # 安全密码
            if security_pwd_edit.text():
                self.config_manager.config['broker']['security_password'] = security_pwd_edit.text()
            
            # 保存回测设置
            self.config_manager.config['backtest']['initial_cash'] = cash_spin.value()
            self.config_manager.config['backtest']['commission'] = commission_spin.value() / 10000
            
            # 保存视图设置
            if 'view' not in self.config_manager.config:
                self.config_manager.config['view'] = {}
            
            # 应用新的主题设置
            self.config_manager.config['view']['theme'] = new_theme
            self.config_manager.config['view']['theme_color'] = new_color
            self.config_manager.config['view']['font_size'] = new_font_size
            self.config_manager.config['view']['font_weight'] = new_font_weight
            
            # 表格设置
            self.config_manager.config['view']['row_height'] = row_height_spin.value()
            self.config_manager.config['view']['zebra_stripes'] = zebra_combo.currentIndex() == 0
            self.config_manager.config['view']['table_border'] = border_combo.currentIndex() == 0
            
            # 其他设置
            self.config_manager.config['view']['animation'] = animation_combo.currentIndex() == 0
            startup_size_map = {0: 'maximized', 1: 'last', 2: 'default'}
            self.config_manager.config['view']['startup_size'] = startup_size_map[window_size_combo.currentIndex()]
            
            # 同步回 self.config
            self.config = self.config_manager.config
            
            # 保存配置到文件
            self.config_manager.save()
            
            # 关闭对话框
            dialog.accept()
            
            # 如果主题或主题色变更，自动重启软件以应用新设置
            if theme_changed or color_changed:
                logger.info(f"主题已变更，准备重启软件... theme_changed={theme_changed}, color_changed={color_changed}")
                logger.info(f"旧主题: {old_theme}, 新主题: {new_theme}")
                logger.info(f"旧颜色: {old_color}, 新颜色: {new_color}")
                
                # 先显示重启提示
                InfoBar.success(
                    title='设置已保存',
                    content='软件即将重启以应用新主题...',
                    orient=Qt.Horizontal,
                    isClosable=False,
                    position=InfoBarPosition.TOP,
                    duration=800,
                    parent=self
                )
                
                logger.info("InfoBar已显示，开始处理事件...")
                
                # 确保InfoBar显示后再重启
                # 使用processEvents强制处理UI事件
                QApplication.processEvents()
                
                # 延迟一点时间让用户看到提示
                import time
                time.sleep(0.5)
                
                logger.info("准备调用restart_application()...")
                # 直接调用重启函数
                self.restart_application()
                logger.info("restart_application()已调用")
            else:
                # 非主题变更，显示成功消息
                InfoBar.success(
                    title='保存成功',
                    content='设置已保存并立即应用',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        
        save_btn.clicked.connect(save_settings)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        # 将内容区域添加到主布局
        main_layout.addWidget(content_widget)
        
        # 显示对话框
        dialog.exec()
    
    def show_help(self):
        """显示帮助对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QHBoxLayout, QLabel
        from PyQt5.QtCore import Qt
        from qfluentwidgets import PrimaryPushButton, TransparentToolButton, FluentIcon
        
        # 创建无边框对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("帮助文档")
        dialog.setModal(True)
        dialog.resize(700, 600)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建自定义标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 0, 5, 0)
        
        title_label = QLabel("帮助文档")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        
        # 关闭按钮
        close_btn_title = TransparentToolButton(FluentIcon.CLOSE)
        close_btn_title.setFixedSize(40, 40)
        close_btn_title.clicked.connect(dialog.reject)
        title_bar_layout.addWidget(close_btn_title)
        
        main_layout.addWidget(title_bar)
        
        # 创建内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 20)
        
        # 根据当前主题设置对话框样式
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            # 深色主题样式
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                QLabel {
                    color: #e0e0e0;
                }
            """)
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: #202020;
                    color: #d0d0d0;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
                QTextBrowser {
                    background-color: #2a2a2a;
                    color: #d0d0d0;
                    border: 1px solid #3a3a3a;
                    border-radius: 5px;
                }
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #4a4a4a;
                    min-height: 30px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5a5a5a;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        else:
            # 浅色主题样式
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }
                QLabel {
                    color: #262626;
                }
            """)
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: #fafafa;
                    color: #262626;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
                QTextBrowser {
                    background-color: #ffffff;
                    color: #262626;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 5px;
                }
                QScrollBar:vertical {
                    background-color: #fafafa;
                    width: 12px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(0, 0, 0, 0.2);
                    min-height: 30px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(0, 0, 0, 0.3);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        
        # 使用 QTextBrowser 显示富文本帮助
        help_browser = QTextBrowser()
        content_layout.addWidget(help_browser)
        help_browser.setOpenExternalLinks(True)
        
        # 根据当前主题动态设置HTML样式
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            text_color = "#e0e0e0"
            code_bg = "rgba(45, 45, 45, 0.8)"
            code_color = "#4fc3f7"
            warning_bg = "rgba(255, 193, 7, 0.2)"
            warning_text = "#ffecb3"
            tip_bg = "rgba(23, 162, 184, 0.2)"
            tip_text = "#b3e5fc"
        else:
            text_color = "#262626"
            code_bg = "rgba(0, 0, 0, 0.06)"
            code_color = "#0078d4"
            warning_bg = "rgba(255, 193, 7, 0.15)"
            warning_text = "#856404"
            tip_bg = "rgba(23, 162, 184, 0.15)"
            tip_text = "#004085"
        
        help_browser.setHtml(f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Microsoft YaHei', Arial; 
                    line-height: 1.6; 
                    padding: 20px; 
                    background-color: transparent;
                    color: {text_color};
                }}
                h1 {{ color: #1890ff; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }}
                h2 {{ color: #1890ff; margin-top: 20px; }}
                h3 {{ color: #4fc3f7; margin-top: 15px; }}
                ul {{ margin-left: 20px; }}
                code {{ background: {code_bg}; color: {code_color}; padding: 2px 5px; border-radius: 3px; }}
                .warning {{ 
                    background: {warning_bg}; 
                    border-left: 4px solid #ffc107; 
                    padding: 10px; 
                    margin: 10px 0;
                    color: {warning_text};
                }}
                .tip {{ 
                    background: {tip_bg}; 
                    border-left: 4px solid #17a2b8; 
                    padding: 10px; 
                    margin: 10px 0;
                    color: {tip_text};
                }}
            </style>
        </head>
        <body>
            <h1>📖 股票量化交易工具 - 使用指南</h1>
            
            <h2>1. 数据管理</h2>
            <h3>📊 功能说明：</h3>
            <ul>
                <li>支持 <b>AKShare</b>（免费）和 <b>Tushare Pro</b>（需积分）数据源</li>
                <li>可下载日线、周线、月线等多周期数据</li>
                <li>支持批量下载和增量更新</li>
            </ul>
            
            <h3>🔧 使用步骤：</h3>
            <ol>
                <li>输入股票代码（如：000001 或 sh000001）</li>
                <li>选择时间范围和数据频率</li>
                <li>点击"下载数据"按钮</li>
                <li>在表格中查看下载的数据</li>
            </ol>
            
            <div class="tip">
                <b>💡 提示：</b> 首次使用建议先下载少量数据测试，确认数据源配置正确。
            </div>
            
            <h2>2. 策略配置</h2>
            <h3>📈 内置策略（19种）：</h3>
            <ul>
                <li><b>技术指标类：</b>MA、MACD、KDJ、RSI、BOLL、CCI</li>
                <li><b>形态识别类：</b>双均线、三均线、海龟交易</li>
                <li><b>机器学习类：</b>随机森林、XGBoost、LSTM、支持向量机</li>
            </ul>
            
            <h3>⚙️ 参数调整：</h3>
            <ul>
                <li>每个策略都有可调整的参数</li>
                <li>建议使用"参数优化"功能寻找最优参数</li>
                <li>保存配置后可在回测中使用</li>
            </ul>
            
            <h2>3. 回测分析</h2>
            <h3>🔄 回测流程：</h3>
            <ol>
                <li>选择要回测的策略</li>
                <li>选择股票和时间范围</li>
                <li>设置初始资金和手续费</li>
                <li>点击"开始回测"</li>
                <li>查看收益曲线、回撤、夏普比率等指标</li>
            </ol>
            
            <div class="warning">
                <b>⚠️ 注意：</b> 回测结果仅供参考，历史业绩不代表未来收益。
            </div>
            
            <h2>4. 策略对比</h2>
            <ul>
                <li>可同时对比多个策略的表现</li>
                <li>直观显示各策略的收益、风险指标</li>
                <li>帮助选择最优策略组合</li>
            </ul>
            
            <h2>5. 参数优化</h2>
            <h3>🔍 优化方法：</h3>
            <ul>
                <li><b>网格搜索：</b>遍历参数空间，找到最优组合</li>
                <li><b>遗传算法：</b>模拟生物进化，智能搜索最优参数</li>
                <li><b>贝叶斯优化：</b>高效的黑盒优化方法</li>
            </ul>
            
            <h2>6. 实时监控</h2>
            <ul>
                <li>实时获取股票行情数据</li>
                <li>监控策略信号生成</li>
                <li>设置价格预警</li>
            </ul>
            
            <h2>7. 自动交易</h2>
            <div class="warning">
                <b>⚠️ 重要：</b> 
                <ul>
                    <li>自动交易功能请谨慎使用</li>
                    <li>建议先用小资金测试</li>
                    <li>务必设置好止损止盈</li>
                    <li>当前版本为模拟交易</li>
                </ul>
            </div>
            
            <h2>8. 实盘交易</h2>
            <ul>
                <li>支持手动下单、撤单</li>
                <li>查看持仓和资金情况</li>
                <li>当前仅支持模拟盘</li>
            </ul>
            
            <h2>💡 常见问题</h2>
            <h3>Q: 数据下载失败怎么办？</h3>
            <p>A: 检查网络连接，或在设置中切换数据源。AKShare无需token，Tushare需要注册获取。</p>
            
            <h3>Q: 回测结果不理想？</h3>
            <p>A: 尝试使用参数优化功能，或在策略对比中选择其他策略。</p>
            
            <h3>Q: 如何连接真实券商？</h3>
            <p>A: 在"券商设置"中配置账号信息，当前版本仅支持模拟交易。</p>
            
            <h2>📞 技术支持</h2>
            <p>如遇到问题，请查看日志文件：<code>logs/app_YYYYMMDD.log</code></p>
            
            <div class="warning">
                <b>⚠️ 风险提示：</b><br>
                本工具仅供学习研究使用，不构成任何投资建议。<br>
                股市有风险，投资需谨慎！使用本工具进行实盘交易的风险由用户自行承担。
            </div>
        </body>
        </html>
        """)
        
        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = PrimaryPushButton()
        close_btn.setText("关闭")
        close_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(close_btn)
        content_layout.addLayout(btn_layout)
        
        # 将内容区域添加到主布局
        main_layout.addWidget(content_widget)
        
        dialog.exec()
    
    def show_about(self):
        """显示关于对话框"""
        title = '关于'
        content = """
股票量化交易工具 v2.0

功能特点：
• 多数据源支持（Tushare、AKShare）
• 19种内置策略（技术面+机器学习）
• 完整的回测引擎（基于Backtrader）
• 智能参数优化（网格搜索+遗传算法）
• 机器学习模型训练
• 实时监控与自动交易

技术栈：
Python 3.8+ | PyQt5 | QFluentWidgets | Backtrader
Pandas | NumPy | scikit-learn | XGBoost

⚠️ 风险提示：
本工具仅供学习研究使用，不构成任何投资建议。
股市有风险，投资需谨慎！
        """
        
        w = MessageBox(title, content, self)
        w.exec()
    
    def restart_application(self):
        """重启应用程序"""
        try:
            logger.info("开始重启应用程序...")
            
            # 设置重启标志，避免closeEvent弹出确认对话框
            self.is_restarting = True
            
            # 获取当前程序路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe
                current_program = sys.executable
                logger.info(f"检测到打包程序，路径: {current_program}")
                
                # 启动新进程（exe）- 使用 DETACHED_PROCESS 标志确保进程独立运行
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    [current_program],
                    creationflags=DETACHED_PROCESS,
                    close_fds=True
                )
                logger.info("已启动新的exe进程")
                
            else:
                # 如果是Python脚本
                current_program = sys.executable
                script_path = os.path.abspath(sys.argv[0])
                logger.info(f"检测到Python脚本模式，Python: {current_program}, 脚本: {script_path}")
                
                # 启动新进程（Python脚本）
                subprocess.Popen([current_program, script_path])
                logger.info("已启动新的Python进程")
            
            # 延迟一下，确保新进程启动后再关闭
            QTimer.singleShot(500, self._finish_restart)
            
        except Exception as e:
            logger.error(f"重启程序失败: {e}", exc_info=True)
            self.is_restarting = False  # 重启失败，恢复标志
            InfoBar.error(
                title='重启失败',
                content=f'无法自动重启程序，请手动重启。\n错误: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
    
    def _finish_restart(self):
        """完成重启：关闭当前程序"""
        try:
            logger.info("正在关闭当前程序...")
            logger.info("准备退出应用...")
            
            # 关闭主窗口
            self.close()
            
            # 退出Qt应用程序
            QApplication.instance().quit()
            
            # 延迟一下再强制退出，确保进程完全关闭
            import time
            time.sleep(0.1)
            
            # 强制退出进程
            logger.info("强制退出进程...")
            os._exit(0)
            
        except Exception as e:
            logger.error(f"关闭程序时出错: {e}", exc_info=True)
            # 无论如何都要退出
            os._exit(0)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果是重启，直接关闭，不弹出确认对话框，不保存窗口大小
        if self.is_restarting:
            logger.info("正在重启，直接关闭窗口（不保存窗口尺寸）")
            event.accept()
            return
        
        # 正常关闭，显示确认对话框
        title = '确认退出'
        content = "确定要退出程序吗？"
        w = MessageBox(title, content, self)
        
        if w.exec():
            logger.info("用户关闭主窗口")
            
            # 保存窗口大小（仅在正常关闭时）
            if self.config.get('view', {}).get('startup_size') == 'last':
                window_size = [self.width(), self.height()]
                if 'ui' not in self.config:
                    self.config['ui'] = {}
                self.config['ui']['window_size'] = window_size
                self.config_manager.config = self.config
                self.config_manager.save()
                logger.info(f"已保存窗口尺寸: {window_size[0]}x{window_size[1]}")
            
            event.accept()
        else:
            event.ignore()
