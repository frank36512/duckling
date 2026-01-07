"""
主题管理器 - 简化版
直接使用 QFluentWidgets 框架的默认样式
"""

from qfluentwidgets import isDarkTheme, qconfig
import matplotlib.pyplot as plt


class ThemeManager:
    """主题管理器 - 提供辅助方法"""
    
    @staticmethod
    def get_theme_color():
        """获取当前主题色"""
        theme_color = qconfig.themeColor.value  # 获取实际的QColor对象
        return f"rgb({theme_color.red()}, {theme_color.green()}, {theme_color.blue()})"
    
    @staticmethod
    def apply_pushbutton_style(button):
        """
        为空心按钮应用主题色边框样式
        :param button: PushButton对象
        """
        theme_color = ThemeManager.get_theme_color()
        is_dark = isDarkTheme()
        
        # 空心按钮样式：边框使用主题色
        style = f"""
            PushButton {{
                border: 1px solid {theme_color};
                color: {theme_color};
                background-color: transparent;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 14px;
            }}
            PushButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.05)'};
                border: 1px solid {theme_color};
            }}
            PushButton:pressed {{
                background-color: {'rgba(255, 255, 255, 0.12)' if is_dark else 'rgba(0, 0, 0, 0.08)'};
            }}
            PushButton:disabled {{
                border: 1px solid {'rgba(255, 255, 255, 0.15)' if is_dark else 'rgba(0, 0, 0, 0.15)'};
                color: {'rgba(255, 255, 255, 0.3)' if is_dark else 'rgba(0, 0, 0, 0.3)'};
            }}
        """
        button.setStyleSheet(style)
    
    @staticmethod
    def get_panel_stylesheet():
        """
        获取面板样式表
        只为容器提供背景色，不影响 QFluentWidgets 控件
        """
        is_dark = isDarkTheme()
        theme_color = ThemeManager.get_theme_color()  # 获取当前主题色
        
        if is_dark:
            return """
                QWidget {
                    background-color: #202020;
                    color: rgba(255, 255, 255, 0.9);
                }
                /* 原生 QTabWidget 样式 */
                QTabWidget::pane {
                    background-color: #2b2b2b;
                    border: none;
                }
                QTabWidget > QWidget {
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #3a3a3a;
                    color: rgba(255, 255, 255, 0.7);
                    padding: 6px 16px;
                    margin-right: 4px;
                    border: 1px solid #4a4a4a;
                    border-bottom: none;
                    border-radius: 4px 4px 0 0;
                    min-height: 32px;
                }
                QTabBar::tab:selected {
                    background-color: #2b2b2b;
                    color: #b0b0b0;
                    border-color: #5a5a5a;
                    border-bottom: 2px solid #2b2b2b;
                    font-weight: 500;
                    margin-bottom: -1px;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #3a3a3a;
                    color: #c0c0c0;
                    border-color: #5a5a5a;
                }
                QGroupBox {
                    background-color: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 18px;
                    color: rgba(255, 255, 255, 0.9);
                    font-weight: bold;
                }
                QGroupBox::title {
                    color: #a0a0a0;
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 8px;
                    left: 10px;
                    top: 2px;
                }
                /* QFluentWidgets 控件深色主题 - 使用底层Qt类名 */
                QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {
                    background-color: #2a2a2a;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 3px;
                    color: #d0d0d0;
                }
                QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QDateTimeEdit:hover {
                    border-color: #4a4a4a;
                }
                QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus {
                    border-color: #555555;
                }
                /* ComboBox 下拉箭头 */
                QComboBox::drop-down {
                    border: none;
                    width: 32px;
                }
                QComboBox::down-arrow {
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 8px solid #aaa;
                    margin-right: 8px;
                }
                QComboBox:hover::down-arrow {
                    border-top-color: #b0b0b0;
                }
                /* ComboBox 下拉列表 */
                QComboBox QAbstractItemView {
                    background-color: #2a2a2a;
                    border: 1px solid #3a3a3a;
                    border-radius: 6px;
                    selection-background-color: #3a3a3a;
                    padding: 4px;
                }
                QComboBox QAbstractItemView::item {
                    padding: 6px 12px;
                    border-radius: 3px;
                    min-height: 28px;
                    border: none;
                    color: rgba(255, 255, 255, 0.75);
                }
                QComboBox QAbstractItemView::item:hover {
                    background-color: #3a3a3a;
                    color: #d0d0d0;
                }
                QComboBox QAbstractItemView::item:selected {
                    background-color: #4a4a4a;
                    color: #e0e0e0;
                    font-weight: 500;
                }
            """
        else:
            return """
                QWidget {{
                    background-color: #fafafa;
                    color: rgba(0, 0, 0, 0.9);
                }}
                /* 原生 QTabWidget 样式 */
                QTabWidget::pane {{
                    background-color: white;
                    border: none;
                }}
                QTabWidget > QWidget {{
                    background-color: white;
                }}
                QTabBar::tab {{
                    background-color: #f5f5f5;
                    color: #595959;
                    padding: 6px 16px;
                    margin-right: 4px;
                    border: 1px solid #d9d9d9;
                    border-bottom: none;
                    border-radius: 4px 4px 0 0;
                    min-height: 32px;
                }}
                QTabBar::tab:selected {{
                    background-color: white;
                    color: {theme_color};
                    border-color: {theme_color};
                    border-bottom: 2px solid white;
                    font-weight: 500;
                    margin-bottom: -1px;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: #e6f7ff;
                    color: {theme_color};
                    border-color: {theme_color};
                    opacity: 0.8;
                }}
                QGroupBox {{
                    background-color: transparent;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 18px;
                    color: rgba(0, 0, 0, 0.9);
                    font-weight: bold;
                }}
                QGroupBox::title {{
                    color: {theme_color};
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 8px;
                    left: 10px;
                    top: 2px;
                }}
                /* QFluentWidgets 控件浅色主题 - 使用底层Qt类名 */
                QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{
                    background-color: white;
                    color: #262626;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 13px;
                }}
                QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QDateTimeEdit:hover {{
                    border-color: #40a9ff;
                    background-color: #fafafa;
                }}
                QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
                    border-color: {theme_color};
                    border-width: 2px;
                }}
                /* ComboBox 下拉箭头 */
                QComboBox::drop-down {{
                    border: none;
                    width: 32px;
                }}
                QComboBox::down-arrow {{
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 8px solid #8c8c8c;
                    margin-right: 8px;
                }}
                QComboBox:hover::down-arrow {{
                    border-top-color: {theme_color};
                }}
                /* ComboBox 下拉列表 */
                QComboBox QAbstractItemView {{
                    background-color: white;
                    border: 1px solid #d9d9d9;
                    border-radius: 6px;
                    selection-background-color: #e6f7ff;
                    padding: 4px;
                }}
                QComboBox QAbstractItemView::item {{
                    padding: 6px 12px;
                    border-radius: 3px;
                    min-height: 28px;
                    border: none;
                }}
                QComboBox QAbstractItemView::item:hover {{
                    background-color: #f0f7ff;
                    color: {theme_color};
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background-color: #e6f7ff;
                    color: {theme_color};
                    font-weight: 500;
                }}
            """.format(theme_color=theme_color)
    
    @staticmethod
    def get_status_color(status):
        """获取状态颜色"""
        is_dark = isDarkTheme()
        colors = {
            'success': '#52C41A' if not is_dark else '#73d13d',
            'running': '#52C41A' if not is_dark else '#73d13d',
            'error': '#FF4D4F' if not is_dark else '#ff7875',
            'stopped': '#FF4D4F' if not is_dark else '#ff7875',
            'warning': '#FAAD14' if not is_dark else '#ffc53d',
            'paused': '#FAAD14' if not is_dark else '#ffc53d',
            'info': '#1890FF' if not is_dark else '#40a9ff',
        }
        return colors.get(status.lower(), '#1890FF' if not is_dark else '#40a9ff')
    
    @staticmethod
    def get_label_style(color=None, bold=False, size=13):
        """获取Label样式"""
        style = f"QLabel {{ font-size: {size}px;"
        if bold:
            style += " font-weight: bold;"
        if color:
            style += f" color: {color};"
        style += " }}"
        return style
    
    @staticmethod
    def get_badge_style(type_='info'):
        """获取徽章/标签样式"""
        is_dark = isDarkTheme()
        styles = {
            'info': {
                'bg': '#e6f7ff' if not is_dark else '#1e3a5f',
                'color': '#1890FF' if not is_dark else '#40a9ff',
                'border': '#91d5ff' if not is_dark else '#4a90e2'
            },
            'success': {
                'bg': '#f6ffed' if not is_dark else '#1e3a1e',
                'color': '#52C41A' if not is_dark else '#73d13d',
                'border': '#b7eb8f' if not is_dark else '#3a7516'
            },
            'warning': {
                'bg': '#fffbe6' if not is_dark else '#3a3020',
                'color': '#FAAD14' if not is_dark else '#ffc53d',
                'border': '#ffe58f' if not is_dark else '#856f14'
            },
            'error': {
                'bg': '#fff2f0' if not is_dark else '#3a1e1e',
                'color': '#FF4D4F' if not is_dark else '#ff7875',
                'border': '#ffccc7' if not is_dark else '#7a2e2e'
            }
        }
        s = styles.get(type_, styles['info'])
        return f"""
            QLabel {{
                background-color: {s['bg']};
                color: {s['color']};
                border: 1px solid {s['border']};
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: 500;
            }}
        """
    
    @staticmethod
    def get_info_box_style():
        """获取信息提示框样式"""
        is_dark = isDarkTheme()
        return f"""
            QLabel {{
                color: {'rgba(255, 255, 255, 0.7)' if is_dark else '#666'};
                padding: 10px;
                background: {'rgba(255, 255, 255, 0.05)' if is_dark else '#f0f0f0'};
                border-radius: 8px;
                border: 1px solid {'rgba(255, 255, 255, 0.1)' if is_dark else '#e8e8e8'};
            }}
        """
    
    @staticmethod
    def apply_matplotlib_style(fig=None, ax=None):
        """
        为matplotlib图表应用深色主题样式
        :param fig: matplotlib figure对象
        :param ax: matplotlib axes对象或axes列表
        """
        is_dark = isDarkTheme()
        
        if not is_dark:
            return  # 浅色主题使用默认样式
        
        # 深色主题配置
        bg_color = '#202020'
        text_color = '#d0d0d0'
        grid_color = '#3a3a3a'
        
        # 设置figure背景色
        if fig:
            fig.patch.set_facecolor(bg_color)
        
        # 设置axes
        axes_list = []
        if ax is not None:
            if isinstance(ax, list):
                axes_list = ax
            else:
                axes_list = [ax]
        
        for axis in axes_list:
            # 背景色
            axis.set_facecolor(bg_color)
            
            # 坐标轴颜色
            axis.tick_params(colors=text_color, which='both')
            axis.xaxis.label.set_color(text_color)
            axis.yaxis.label.set_color(text_color)
            axis.title.set_color(text_color)
            
            # 边框颜色
            for spine in axis.spines.values():
                spine.set_edgecolor(grid_color)
            
            # 网格颜色
            axis.grid(True, color=grid_color, alpha=0.3, linestyle='--')
            
            # 图例样式
            legend = axis.get_legend()
            if legend:
                frame = legend.get_frame()
                frame.set_facecolor('#2a2a2a')
                frame.set_edgecolor('#3a3a3a')
                frame.set_alpha(0.9)
                for text in legend.get_texts():
                    text.set_color(text_color)
    
    @staticmethod
    def style_matplotlib_legend(legend):
        """
        单独为matplotlib图例应用深色主题样式
        :param legend: matplotlib legend对象
        """
        is_dark = isDarkTheme()
        
        if not is_dark or not legend:
            return
        
        # 深色主题图例样式
        frame = legend.get_frame()
        frame.set_facecolor('#2a2a2a')
        frame.set_edgecolor('#3a3a3a')
        frame.set_alpha(0.9)
        
        for text in legend.get_texts():
            text.set_color('#d0d0d0')