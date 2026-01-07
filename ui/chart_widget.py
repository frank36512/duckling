"""
图表组件
用于显示回测结果的可视化图表
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class BacktestChartWidget(QWidget):
    """回测图表组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 收益曲线图
        self.return_canvas = self.create_canvas()
        self.tab_widget.addTab(self.return_canvas, "📈 收益曲线")
        
        # 资金曲线图
        self.equity_canvas = self.create_canvas()
        self.tab_widget.addTab(self.equity_canvas, "💰 资金曲线")
        
        # 回撤曲线图
        self.drawdown_canvas = self.create_canvas()
        self.tab_widget.addTab(self.drawdown_canvas, "📉 回撤曲线")
        
        layout.addWidget(self.tab_widget)
        
        # 设置透明背景
        self.setStyleSheet("background-color: transparent;")
        
    def create_canvas(self):
        """创建画布"""
        # 检测当前主题
        from qfluentwidgets import isDarkTheme
        from ui.theme_manager import ThemeManager
        
        canvas = FigureCanvas(Figure(tight_layout=True))
        
        # 根据主题设置背景色
        if isDarkTheme():
            canvas.figure.patch.set_facecolor('#2b2b2b')  # 深色背景
        else:
            canvas.figure.patch.set_facecolor('#fafafa')  # 浅色背景
        
        # 设置画布的尺寸约束，防止过度拉伸
        canvas.setMinimumHeight(300)
        canvas.setMaximumHeight(600)
        
        # 设置画布样式
        canvas.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        return canvas
    
    def plot_return_curve(self, result):
        """
        绘制收益曲线
        :param result: BacktestResult对象
        """
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            
            canvas = self.return_canvas
            canvas.figure.clear()
            
            # 根据主题设置背景色
            if is_dark:
                canvas.figure.patch.set_facecolor('#2b2b2b')
                text_color = '#e0e0e0'
                grid_color = (1, 1, 1, 0.1)
                bg_color = '#2b2b2b'
            else:
                canvas.figure.patch.set_facecolor('#fafafa')
                text_color = '#262626'
                grid_color = (0, 0, 0, 0.1)
                bg_color = '#fafafa'
            
            ax = canvas.figure.add_subplot(111)
            ax.set_facecolor(bg_color)
            
            # 获取数据
            if not hasattr(result, 'equity_curve') or result.equity_curve is None:
                ax.text(0.5, 0.5, '暂无数据', 
                       ha='center', va='center', fontsize=16, color=text_color)
                canvas.draw()
                return
            
            equity_curve = result.equity_curve
            
            # 计算收益率曲线
            initial_value = equity_curve.iloc[0]
            return_curve = (equity_curve / initial_value - 1) * 100
            
            # 绘制收益率曲线
            ax.plot(return_curve.index, return_curve.values, 
                   linewidth=2, color='#2196F3', label='策略收益')
            
            # 添加零线
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            
            # 填充正收益区域
            ax.fill_between(return_curve.index, 0, return_curve.values,
                           where=(return_curve.values >= 0),
                           color='#4CAF50', alpha=0.3, label='盈利区域')
            
            # 填充负收益区域
            ax.fill_between(return_curve.index, 0, return_curve.values,
                           where=(return_curve.values < 0),
                           color='#F44336', alpha=0.3, label='亏损区域')
            
            # 标注最终收益
            final_return = return_curve.iloc[-1]
            color = '#4CAF50' if final_return >= 0 else '#F44336'
            ax.text(return_curve.index[-1], final_return,
                   f' {final_return:.2f}%',
                   color=color, fontweight='bold',
                   verticalalignment='bottom')
            
            # 设置标题和标签
            ax.set_title('策略收益曲线', fontsize=14, fontweight='bold', pad=15, color=text_color)
            ax.set_xlabel('日期', fontsize=12, color=text_color)
            ax.set_ylabel('累计收益率 (%)', fontsize=12, color=text_color)
            
            # 设置坐标轴颜色
            ax.tick_params(colors=text_color)
            ax.spines['bottom'].set_color(text_color)
            ax.spines['top'].set_color(text_color)
            ax.spines['left'].set_color(text_color)
            ax.spines['right'].set_color(text_color)
            
            # 设置图例
            legend = ax.legend(loc='best', framealpha=0.9)
            legend.get_frame().set_facecolor('#2b2b2b' if is_dark else 'white')
            for text in legend.get_texts():
                text.set_color(text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            
            # 设置网格
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 格式化x轴日期
            if len(return_curve) > 30:
                ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            canvas.figure.autofmt_xdate()
            canvas.figure.tight_layout()
            canvas.draw()
            
            logger.info("收益曲线绘制完成")
            
        except Exception as e:
            logger.error(f"绘制收益曲线失败: {e}", exc_info=True)
    
    def plot_equity_curve(self, result):
        """
        绘制资金曲线
        :param result: BacktestResult对象
        """
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            
            canvas = self.equity_canvas
            canvas.figure.clear()
            
            # 根据主题设置背景色
            if is_dark:
                canvas.figure.patch.set_facecolor('#2b2b2b')
                text_color = '#e0e0e0'
                grid_color = (1, 1, 1, 0.1)
                bg_color = '#2b2b2b'
            else:
                canvas.figure.patch.set_facecolor('#fafafa')
                text_color = '#262626'
                grid_color = (0, 0, 0, 0.1)
                bg_color = '#fafafa'
            
            ax = canvas.figure.add_subplot(111)
            ax.set_facecolor(bg_color)
            
            # 获取数据
            if not hasattr(result, 'equity_curve') or result.equity_curve is None:
                ax.text(0.5, 0.5, '暂无数据', 
                       ha='center', va='center', fontsize=16, color=text_color)
                canvas.draw()
                return
            
            equity_curve = result.equity_curve
            
            # 绘制资金曲线
            ax.plot(equity_curve.index, equity_curve.values,
                   linewidth=2, color='#FF9800', label='账户总资产')
            
            # 添加初始资金线
            initial_cash = equity_curve.iloc[0]
            ax.axhline(y=initial_cash, color='gray', linestyle='--', 
                      linewidth=1, alpha=0.5, label=f'初始资金 ({initial_cash:,.0f})')
            
            # 填充盈利区域
            ax.fill_between(equity_curve.index, initial_cash, equity_curve.values,
                           where=(equity_curve.values >= initial_cash),
                           color='#4CAF50', alpha=0.2)
            
            # 填充亏损区域
            ax.fill_between(equity_curve.index, initial_cash, equity_curve.values,
                           where=(equity_curve.values < initial_cash),
                           color='#F44336', alpha=0.2)
            
            # 标注最高和最低点
            max_idx = equity_curve.idxmax()
            max_val = equity_curve.max()
            min_idx = equity_curve.idxmin()
            min_val = equity_curve.min()
            
            ax.plot(max_idx, max_val, 'g^', markersize=10, label='最高点')
            ax.text(max_idx, max_val, f' {max_val:,.0f}',
                   verticalalignment='bottom', color='green')
            
            ax.plot(min_idx, min_val, 'rv', markersize=10, label='最低点')
            ax.text(min_idx, min_val, f' {min_val:,.0f}',
                   verticalalignment='top', color='red')
            
            # 设置标题和标签
            ax.set_title('账户资金曲线', fontsize=14, fontweight='bold', pad=15, color=text_color)
            ax.set_xlabel('日期', fontsize=12, color=text_color)
            ax.set_ylabel('总资产 (元)', fontsize=12, color=text_color)
            
            # 设置图例
            legend = ax.legend(loc='best', framealpha=0.9)
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            
            # 设置网格
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 设置坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 格式化y轴为货币格式
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
            
            # 格式化x轴日期
            if len(equity_curve) > 30:
                ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            canvas.figure.autofmt_xdate()
            canvas.figure.tight_layout()
            canvas.draw()
            
            logger.info("资金曲线绘制完成")
            
        except Exception as e:
            logger.error(f"绘制资金曲线失败: {e}", exc_info=True)
    
    def plot_drawdown_curve(self, result):
        """
        绘制回撤曲线
        :param result: BacktestResult对象
        """
        try:
            from qfluentwidgets import isDarkTheme
            is_dark = isDarkTheme()
            
            canvas = self.drawdown_canvas
            canvas.figure.clear()
            
            # 根据主题设置背景色
            if is_dark:
                canvas.figure.patch.set_facecolor('#2b2b2b')
                text_color = '#e0e0e0'
                grid_color = (1, 1, 1, 0.1)
                bg_color = '#2b2b2b'
            else:
                canvas.figure.patch.set_facecolor('#fafafa')
                text_color = '#262626'
                grid_color = (0, 0, 0, 0.1)
                bg_color = '#fafafa'
            
            ax = canvas.figure.add_subplot(111)
            ax.set_facecolor(bg_color)
            
            # 获取数据
            if not hasattr(result, 'equity_curve') or result.equity_curve is None:
                ax.text(0.5, 0.5, '暂无数据', 
                       ha='center', va='center', fontsize=16, color=text_color)
                canvas.draw()
                return
            
            equity_curve = result.equity_curve
            
            # 计算回撤
            running_max = equity_curve.expanding().max()
            drawdown = (equity_curve - running_max) / running_max * 100
            
            # 绘制回撤曲线
            ax.fill_between(drawdown.index, 0, drawdown.values,
                           color='#F44336', alpha=0.5, label='回撤')
            ax.plot(drawdown.index, drawdown.values,
                   linewidth=2, color='#D32F2F')
            
            # 添加零线
            ax.axhline(y=0, color='gray', linestyle='-', linewidth=1)
            
            # 标注最大回撤
            max_dd_idx = drawdown.idxmin()
            max_dd_val = drawdown.min()
            ax.plot(max_dd_idx, max_dd_val, 'ro', markersize=10)
            ax.text(max_dd_idx, max_dd_val, f' 最大回撤: {max_dd_val:.2f}%',
                   verticalalignment='top', color='red', fontweight='bold')
            
            # 设置标题和标签
            ax.set_title('策略回撤曲线', fontsize=14, fontweight='bold', pad=15, color=text_color)
            ax.set_xlabel('日期', fontsize=12, color=text_color)
            ax.set_ylabel('回撤 (%)', fontsize=12, color=text_color)
            
            # 设置图例
            legend = ax.legend(loc='lower left', framealpha=0.9)
            plt.setp(legend.get_texts(), color=text_color)
            # 应用深色主题图例样式
            from ui.theme_manager import ThemeManager
            ThemeManager.style_matplotlib_legend(legend)
            
            # 设置网格
            ax.grid(True, alpha=0.3, linestyle='--', color=grid_color)
            
            # 设置坐标轴颜色
            ax.tick_params(colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)
                spine.set_alpha(0.3)
            
            # 格式化x轴日期
            if len(drawdown) > 30:
                ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            canvas.figure.autofmt_xdate()
            canvas.figure.tight_layout()
            canvas.draw()
            
            logger.info("回撤曲线绘制完成")
            
        except Exception as e:
            logger.error(f"绘制回撤曲线失败: {e}", exc_info=True)
    
    def plot_all(self, result):
        """
        绘制所有图表
        :param result: BacktestResult对象
        """
        errors = []
        
        try:
            logger.info("开始绘制收益曲线")
            self.plot_return_curve(result)
            logger.info("收益曲线绘制成功")
        except Exception as e:
            logger.error(f"收益曲线绘制失败: {e}", exc_info=True)
            errors.append(f"收益曲线: {str(e)}")
        
        try:
            logger.info("开始绘制资金曲线")
            self.plot_equity_curve(result)
            logger.info("资金曲线绘制成功")
        except Exception as e:
            logger.error(f"资金曲线绘制失败: {e}", exc_info=True)
            errors.append(f"资金曲线: {str(e)}")
        
        try:
            logger.info("开始绘制回撤曲线")
            self.plot_drawdown_curve(result)
            logger.info("回撤曲线绘制成功")
        except Exception as e:
            logger.error(f"回撤曲线绘制失败: {e}", exc_info=True)
            errors.append(f"回撤曲线: {str(e)}")
        
        if errors:
            logger.warning(f"部分图表绘制失败: {', '.join(errors)}")
        else:
            logger.info("所有图表绘制完成")
