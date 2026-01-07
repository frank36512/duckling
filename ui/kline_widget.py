"""
K线图组件 - 增强版
支持蜡烛图、技术指标叠加、买卖点标记、交互式操作
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QCheckBox, QGroupBox, QScrollArea)
from PyQt5.QtCore import Qt
from qfluentwidgets import ComboBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from datetime import datetime
from ui.theme_manager import ThemeManager

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class EnhancedKLineWidget(QWidget):
    """增强的K线图组件"""
    
    def __init__(self):
        super().__init__()
        self.data = None  # 当前显示数据
        self.original_data = None  # 原始数据副本（用于周期切换）
        self.trades = None  # 交易记录
        self.current_indicators = []  # 当前显示的指标
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        layout.setSpacing(3)  # 减小间距
        
        # 第一行：图表控制工具栏
        top_toolbar = QHBoxLayout()
        top_toolbar.setSpacing(8)  # 紧凑间距
        
        # 左侧：自定义工具栏
        toolbar_layout = self.create_toolbar()
        top_toolbar.addLayout(toolbar_layout)
        
        top_toolbar.addStretch()
        
        layout.addLayout(top_toolbar)
        
        # 第二行：信息显示栏
        info_layout = QHBoxLayout()
        info_layout.setSpacing(5)
        self.info_label = QLabel("无数据")
        self.info_label.setStyleSheet("color: #999; font-size: 11px; padding: 2px 5px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 图表区域 - 根据主题设置背景色
        from qfluentwidgets import isDarkTheme
        from PyQt5.QtWidgets import QSizePolicy
        fig_color = '#2b2b2b' if isDarkTheme() else '#fafafa'
        self.figure = Figure(facecolor=fig_color, tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 设置画布的尺寸策略为自适应
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(1)
        size_policy.setVerticalStretch(1)
        self.canvas.setSizePolicy(size_policy)
        
        # 设置最小尺寸，防止过小
        self.canvas.setMinimumSize(600, 400)
        
        # matplotlib导航工具栏 - 精简版
        self.nav_toolbar = NavigationToolbar(self.canvas, self)
        self.nav_toolbar.setMaximumHeight(28)  # 限制高度
        
        # 隐藏不常用的按钮，只保留核心功能
        # 获取工具栏的所有 action
        actions = self.nav_toolbar.actions()
        if len(actions) > 0:
            # 通常顺序：Home, Back, Forward, Pan, Zoom, Configure, Save
            # 只保留：Home(0), Pan(3), Zoom(4), Save(6)
            keep_indices = [0, 3, 4, 6]
            for i, action in enumerate(actions):
                if i not in keep_indices and action.isSeparator() == False:
                    action.setVisible(False)
        
        # 设置工具栏样式，使其更紧凑
        self.nav_toolbar.setStyleSheet("""
            QToolBar { 
                border: none; 
                spacing: 2px; 
                padding: 2px;
                background: transparent;
            }
            QToolButton {
                padding: 2px;
                margin: 1px;
            }
        """)
        
        # 创建一个容器来放置导航工具栏和画布
        chart_container = QVBoxLayout()
        chart_container.setContentsMargins(0, 0, 0, 0)
        chart_container.setSpacing(2)
        chart_container.addWidget(self.nav_toolbar)
        chart_container.addWidget(self.canvas, stretch=1)
        
        layout.addLayout(chart_container, stretch=1)
    
    def resizeEvent(self, event):
        """响应窗口大小变化，动态调整figure尺寸"""
        super().resizeEvent(event)
        if hasattr(self, 'canvas') and self.canvas:
            # 获取画布的实际尺寸（像素）
            canvas_width = self.canvas.width()
            canvas_height = self.canvas.height()
            
            # 转换为英寸（matplotlib使用英寸作为单位）
            dpi = self.figure.dpi
            fig_width = canvas_width / dpi
            fig_height = canvas_height / dpi
            
            # 只有当尺寸有效时才调整
            if fig_width > 0 and fig_height > 0:
                self.figure.set_size_inches(fig_width, fig_height, forward=False)
                self.canvas.draw_idle()  # 使用 draw_idle 避免频繁重绘
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)  # 紧凑间距
        
        # 时间周期选择
        period_label = QLabel("周期:")
        period_label.setStyleSheet("font-size: 12px;")
        toolbar.addWidget(period_label)
        self.period_combo = ComboBox()
        self.period_combo.setMaximumWidth(80)
        self.period_combo.addItems(["日线", "周线", "月线"])
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        toolbar.addWidget(self.period_combo)
        
        toolbar.addSpacing(10)
        
        # 图表类型选择
        type_label = QLabel("类型:")
        type_label.setStyleSheet("font-size: 12px;")
        toolbar.addWidget(type_label)
        self.chart_type_combo = ComboBox()
        self.chart_type_combo.setMaximumWidth(80)
        self.chart_type_combo.addItems(["蜡烛图", "美国线", "折线图"])
        self.chart_type_combo.currentIndexChanged.connect(self.refresh_chart)
        toolbar.addWidget(self.chart_type_combo)
        
        toolbar.addSpacing(10)
        
        # 技术指标选择 - 使用更紧凑的复选框
        self.ma_check = QCheckBox("MA")
        self.ma_check.setStyleSheet("font-size: 11px;")
        self.ma_check.stateChanged.connect(self.on_indicator_changed)
        toolbar.addWidget(self.ma_check)
        
        self.volume_check = QCheckBox("成交量")
        self.volume_check.setStyleSheet("font-size: 11px;")
        self.volume_check.setChecked(True)
        self.volume_check.stateChanged.connect(self.on_indicator_changed)
        toolbar.addWidget(self.volume_check)
        
        self.macd_check = QCheckBox("MACD")
        self.macd_check.setStyleSheet("font-size: 11px;")
        self.macd_check.stateChanged.connect(self.on_indicator_changed)
        toolbar.addWidget(self.macd_check)
        
        self.bollinger_check = QCheckBox("布林带")
        self.bollinger_check.setStyleSheet("font-size: 11px;")
        self.bollinger_check.stateChanged.connect(self.on_indicator_changed)
        toolbar.addWidget(self.bollinger_check)
        
        toolbar.addSpacing(10)
        
        # 显示交易信号
        self.signals_check = QCheckBox("买卖点")
        self.signals_check.setStyleSheet("font-size: 11px;")
        self.signals_check.setChecked(True)
        self.signals_check.stateChanged.connect(self.refresh_chart)
        toolbar.addWidget(self.signals_check)
        
        return toolbar
    
    def set_data(self, data, trades=None):
        """
        设置数据
        :param data: DataFrame with columns: date, open, high, low, close, volume
        :param trades: 交易记录列表
        """
        self.data = data.copy()
        self.trades = trades
        
        # 确保有date列
        if 'date' not in self.data.columns:
            # 如果索引是日期，则重置索引
            if isinstance(self.data.index, pd.DatetimeIndex):
                self.data = self.data.reset_index()
                if 'index' in self.data.columns:
                    self.data.rename(columns={'index': 'date'}, inplace=True)
                elif self.data.index.name:
                    self.data.rename(columns={self.data.index.name: 'date'}, inplace=True)
                else:
                    # 如果第一列看起来像日期，使用它
                    first_col = self.data.columns[0]
                    if 'date' in first_col.lower() or 'time' in first_col.lower():
                        self.data.rename(columns={first_col: 'date'}, inplace=True)
        
        # 确保日期列为datetime类型
        if 'date' in self.data.columns:
            self.data['date'] = pd.to_datetime(self.data['date'])
            logger.info(f"数据加载成功，共 {len(self.data)} 条记录，列: {list(self.data.columns)}")
        else:
            logger.error(f"无法找到日期列！当前列: {list(self.data.columns)}")
            logger.error(f"索引类型: {type(self.data.index)}, 索引名: {self.data.index.name}")
            return
        
        # 保存原始数据副本（用于多周期切换）
        self.original_data = self.data.copy()
        
        # 重置周期选择为日线
        self.period_combo.setCurrentIndex(0)
        
        # 更新信息标签
        self.update_info_label()
        
        self.refresh_chart()
    
    def on_period_changed(self, index):
        """周期改变事件"""
        if self.data is None or self.original_data is None:
            return
        
        period = self.period_combo.currentText()
        
        # 重采样数据
        if period == '日线':
            self.data = self.original_data.copy()
        else:
            self.resample_data(period)
        
        self.refresh_chart()
    
    def resample_data(self, period):
        """重采样数据到不同周期"""
        try:
            # 确保有原始数据
            if self.original_data is None:
                logger.warning("没有原始数据可供重采样")
                return
            
            # pandas重采样规则
            rule_map = {'日线': 'D', '周线': 'W-MON', '月线': 'MS'}
            rule = rule_map.get(period, 'D')
            
            logger.info(f"开始重采样数据到 {period}, 规则: {rule}")
            
            # 设置日期为索引
            data_to_resample = self.original_data.copy()
            if 'date' in data_to_resample.columns:
                data_to_resample = data_to_resample.set_index('date')
            
            # 重采样OHLCV数据
            resampled = data_to_resample.resample(rule).agg({
                'open': 'first',   # 开盘价取第一个
                'high': 'max',     # 最高价取最大值
                'low': 'min',      # 最低价取最小值
                'close': 'last',   # 收盘价取最后一个
                'volume': 'sum'    # 成交量求和
            })
            
            # 删除空行
            resampled = resampled.dropna()
            
            # 重置索引
            resampled = resampled.reset_index()
            
            self.data = resampled
            logger.info(f"重采样完成，数据点: {len(self.original_data)} -> {len(resampled)}")
            
            # 更新信息标签
            self.update_info_label()
            
        except Exception as e:
            logger.error(f"数据重采样失败: {e}", exc_info=True)
            # 失败时恢复原始数据
            self.data = self.original_data.copy()
            self.update_info_label()
    
    def on_indicator_changed(self):
        """指标改变事件"""
        self.current_indicators = []
        
        if self.ma_check.isChecked():
            self.current_indicators.append('ma')
        if self.macd_check.isChecked():
            self.current_indicators.append('macd')
        if self.bollinger_check.isChecked():
            self.current_indicators.append('bollinger')
        
        self.refresh_chart()
    
    def update_info_label(self):
        """更新数据信息标签"""
        if self.data is None or len(self.data) == 0:
            self.info_label.setText("无数据")
            return
        
        try:
            period = self.period_combo.currentText()
            data_count = len(self.data)
            
            # 计算日期范围
            start_date = self.data['date'].min().strftime('%Y-%m-%d')
            end_date = self.data['date'].max().strftime('%Y-%m-%d')
            
            # 计算价格范围
            price_min = self.data['low'].min()
            price_max = self.data['high'].max()
            
            # 交易信号数量
            trade_info = ""
            if self.trades:
                buy_count = sum(1 for t in self.trades if t.get('type') == 'buy')
                sell_count = sum(1 for t in self.trades if t.get('type') == 'sell')
                trade_info = f" | 买入{buy_count}次 卖出{sell_count}次"
            
            info_text = f"{period} | {data_count}根K线 | {start_date}~{end_date} | 价格区间: {price_min:.2f}~{price_max:.2f}{trade_info}"
            self.info_label.setText(info_text)
            
        except Exception as e:
            logger.error(f"更新信息标签失败: {e}", exc_info=True)
            self.info_label.setText("数据信息获取失败")
    
    def refresh_chart(self):
        """刷新图表"""
        if self.data is None or self.data.empty:
            return
        
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            
            # 根据主题设置背景色
            if is_dark:
                self.figure.patch.set_facecolor('#2b2b2b')
            else:
                self.figure.patch.set_facecolor('#fafafa')
            
            self.figure.clear()
            
            # 计算需要的子图数量
            n_subplots = 1  # K线图
            if self.volume_check.isChecked():
                n_subplots += 1
            if 'macd' in self.current_indicators:
                n_subplots += 1
            
            # 创建子图（使用gridspec控制高度比例）
            from matplotlib.gridspec import GridSpec
            gs = GridSpec(n_subplots, 1, height_ratios=[3] + [1] * (n_subplots - 1), 
                         hspace=0.05)
            
            current_subplot = 0
            
            # 绘制K线图
            ax_main = self.figure.add_subplot(gs[current_subplot])
            self.plot_candlestick(ax_main)
            current_subplot += 1
            
            # 绘制成交量
            if self.volume_check.isChecked():
                ax_volume = self.figure.add_subplot(gs[current_subplot], sharex=ax_main)
                self.plot_volume(ax_volume)
                current_subplot += 1
            
            # 绘制MACD
            if 'macd' in self.current_indicators:
                ax_macd = self.figure.add_subplot(gs[current_subplot], sharex=ax_main)
                self.plot_macd(ax_macd)
                current_subplot += 1
            
            # 隐藏除最后一个子图外的x轴标签
            for ax in self.figure.get_axes()[:-1]:
                ax.set_xticklabels([])
            
            # 使用 tight_layout
            self.figure.tight_layout(pad=1.0)
            self.canvas.draw()
            
            logger.info("K线图刷新完成")
            
        except Exception as e:
            logger.error(f"刷新K线图失败: {e}", exc_info=True)
    
    def plot_candlestick(self, ax):
        """绘制K线图"""
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            grid_color = (1, 1, 1, 0.1) if is_dark else (0, 0, 0, 0.1)
            bg_color = '#2b2b2b' if is_dark else '#fafafa'
            
            ax.set_facecolor(bg_color)
            
            # 准备数据
            data_plot = self.data[['date', 'open', 'high', 'low', 'close']].copy()
            
            # 转换日期为数字（matplotlib需要）
            data_plot['date_num'] = mdates.date2num(data_plot['date'])
            
            # 选择图表类型
            chart_type = self.chart_type_combo.currentText()
            
            if chart_type == "蜡烛图":
                self.plot_candlestick_chart(ax, data_plot)
            elif chart_type == "美国线":
                self.plot_ohlc_chart(ax, data_plot)
            else:  # 折线图
                self.plot_line_chart(ax, data_plot)
            
            # 绘制技术指标
            if 'ma' in self.current_indicators:
                self.plot_ma_lines(ax)
            
            if 'bollinger' in self.current_indicators:
                self.plot_bollinger_bands(ax)
            
            # 绘制买卖点
            if self.signals_check.isChecked() and self.trades:
                self.plot_trade_signals(ax)
            
            # 设置标题和标签
            ax.set_title('K线图', fontsize=14, fontweight='bold', pad=10, color=text_color)
            ax.set_ylabel('价格 (元)', fontsize=11, color=text_color)
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 设置坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 格式化x轴
            ax.xaxis_date()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            # 设置图例
            if ax.get_legend_handles_labels()[0]:
                legend = ax.legend(loc='upper left', framealpha=0.9, fontsize=9)
                plt.setp(legend.get_texts(), color=text_color)
                # 应用深色主题图例样式
                from ui.theme_manager import ThemeManager
                ThemeManager.style_matplotlib_legend(legend)
            
        except Exception as e:
            logger.error(f"绘制K线图失败: {e}", exc_info=True)
    
    def plot_candlestick_chart(self, ax, data_plot):
        """绘制蜡烛图（手工实现）"""
        from matplotlib.patches import Rectangle
        from matplotlib.lines import Line2D
        
        width = 0.6
        width2 = 0.05
        
        for idx, row in data_plot.iterrows():
            date_num = row['date_num']
            open_price = row['open']
            high = row['high']
            low = row['low']
            close = row['close']
            
            # 确定颜色（涨红跌绿）
            if close >= open_price:
                color = '#FF4444'  # 红色（涨）
                body_color = color
                body_height = close - open_price
                body_bottom = open_price
            else:
                color = '#00C853'  # 绿色（跌）
                body_color = color
                body_height = open_price - close
                body_bottom = close
            
            # 绘制上下影线
            ax.plot([date_num, date_num], [low, high], 
                   color=color, linewidth=1, solid_capstyle='round')
            
            # 绘制实体（矩形）
            if body_height > 0:
                rect = Rectangle((date_num - width/2, body_bottom), 
                               width, body_height,
                               facecolor=body_color, edgecolor=color, 
                               alpha=0.8, linewidth=0.5)
                ax.add_patch(rect)
            else:
                # 十字线（开盘价等于收盘价）
                ax.plot([date_num - width/2, date_num + width/2], 
                       [close, close], color=color, linewidth=1.5)
    
    def plot_ohlc_chart(self, ax, data_plot):
        """绘制美国线（OHLC）"""
        from matplotlib.lines import Line2D
        
        for idx, row in data_plot.iterrows():
            date_num = row['date_num']
            open_price = row['open']
            high = row['high']
            low = row['low']
            close = row['close']
            
            color = '#FF4444' if close >= open_price else '#00C853'
            
            # 绘制高低线
            ax.plot([date_num, date_num], [low, high], color=color, linewidth=1)
            
            # 绘制开盘线（左侧）
            ax.plot([date_num - 0.2, date_num], [open_price, open_price], 
                   color=color, linewidth=1)
            
            # 绘制收盘线（右侧）
            ax.plot([date_num, date_num + 0.2], [close, close], 
                   color=color, linewidth=1)
    
    def plot_line_chart(self, ax, data_plot):
        """绘制折线图"""
        ax.plot(data_plot['date'], data_plot['close'], 
               linewidth=2, color='#2196F3', label='收盘价')
    
    def plot_ma_lines(self, ax):
        """绘制均线"""
        periods = [5, 10, 20, 60]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        
        for period, color in zip(periods, colors):
            if len(self.data) >= period:
                ma = self.data['close'].rolling(window=period).mean()
                ax.plot(self.data['date'], ma, 
                       label=f'MA{period}', color=color, linewidth=1.5, alpha=0.8)
    
    def plot_bollinger_bands(self, ax):
        """绘制布林带"""
        period = 20
        if len(self.data) >= period:
            ma = self.data['close'].rolling(window=period).mean()
            std = self.data['close'].rolling(window=period).std()
            upper = ma + 2 * std
            lower = ma - 2 * std
            
            ax.plot(self.data['date'], upper, 
                   label='布林上轨', color='#FF9800', linewidth=1, linestyle='--', alpha=0.7)
            ax.plot(self.data['date'], ma, 
                   label='布林中轨', color='#9C27B0', linewidth=1, alpha=0.7)
            ax.plot(self.data['date'], lower, 
                   label='布林下轨', color='#FF9800', linewidth=1, linestyle='--', alpha=0.7)
            
            # 填充布林带区域
            ax.fill_between(self.data['date'], upper, lower, 
                           alpha=0.1, color='#9C27B0')
    
    def plot_trade_signals(self, ax):
        """绘制买卖点标记"""
        if not self.trades:
            return
        
        buy_dates = []
        buy_prices = []
        sell_dates = []
        sell_prices = []
        
        for trade in self.trades:
            trade_date = trade.get('date')
            # 转换日期格式（兼容datetime.date和pd.Timestamp）
            if trade_date is not None:
                if not isinstance(trade_date, pd.Timestamp):
                    trade_date = pd.to_datetime(trade_date)
                
                if trade.get('type') == 'buy':
                    buy_dates.append(trade_date)
                    buy_prices.append(trade.get('price'))
                elif trade.get('type') == 'sell':
                    sell_dates.append(trade_date)
                    sell_prices.append(trade.get('price'))
        
        # 绘制买点
        if buy_dates:
            ax.scatter(buy_dates, buy_prices, 
                      marker='^', color='red', s=150, 
                      label='买入', zorder=5, edgecolors='darkred', linewidths=2)
        
        # 绘制卖点
        if sell_dates:
            ax.scatter(sell_dates, sell_prices, 
                      marker='v', color='green', s=150, 
                      label='卖出', zorder=5, edgecolors='darkgreen', linewidths=2)
    
    def plot_volume(self, ax):
        """绘制成交量"""
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            grid_color = (1, 1, 1, 0.1) if is_dark else (0, 0, 0, 0.1)
            bg_color = '#2b2b2b' if is_dark else '#fafafa'
            
            ax.set_facecolor(bg_color)
            
            # 确定颜色（涨红跌绿）
            colors = []
            for idx, row in self.data.iterrows():
                if idx == 0:
                    colors.append('#FF4444')
                else:
                    prev_close = self.data.iloc[idx-1]['close']
                    curr_close = row['close']
                    colors.append('#FF4444' if curr_close >= prev_close else '#00C853')
            
            # 绘制成交量柱状图
            ax.bar(self.data['date'], self.data['volume'], 
                  color=colors, alpha=0.6, width=0.8)
            
            # 绘制成交量均线
            if len(self.data) >= 5:
                vol_ma5 = self.data['volume'].rolling(window=5).mean()
                ax.plot(self.data['date'], vol_ma5, 
                       label='VOL-MA5', color='yellow', linewidth=1.5)
            
            ax.set_ylabel('成交量', fontsize=10, color=text_color)
            legend = ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 设置坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 格式化y轴（使用科学计数法或简化显示）
            ax.yaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, p: f'{x/10000:.0f}万' if x >= 10000 else f'{x:.0f}'
            ))
            
        except Exception as e:
            logger.error(f"绘制成交量失败: {e}", exc_info=True)
    
    def plot_macd(self, ax):
        """绘制MACD指标"""
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            text_color = '#e0e0e0' if is_dark else '#262626'
            grid_color = (1, 1, 1, 0.1) if is_dark else (0, 0, 0, 0.1)
            bg_color = '#2b2b2b' if is_dark else '#fafafa'
            
            ax.set_facecolor(bg_color)
            
            # 计算MACD
            exp1 = self.data['close'].ewm(span=12, adjust=False).mean()
            exp2 = self.data['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            
            # 绘制MACD柱状图
            colors = ['#FF4444' if h > 0 else '#00C853' for h in histogram]
            ax.bar(self.data['date'], histogram, color=colors, alpha=0.6, width=0.8)
            
            # 绘制MACD线和信号线
            ax.plot(self.data['date'], macd, label='MACD', color='#2196F3', linewidth=1.5)
            ax.plot(self.data['date'], signal, label='Signal', color='#FF9800', linewidth=1.5)
            
            # 零线
            ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
            
            ax.set_ylabel('MACD', fontsize=10, color=text_color)
            legend = ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 设置坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
        except Exception as e:
            logger.error(f"绘制MACD失败: {e}", exc_info=True)
