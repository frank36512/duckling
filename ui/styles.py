"""
UI样式定义模块
仅保留必要的自定义样式配置
QFluentWidgets 框架已提供完整的控件样式，无需覆盖
"""

# 主题色彩 - 参考Ant Design配色系统
COLORS = {
    # 主色调 - 专业金融蓝
    'primary': '#1677ff',
    'primary_light': '#4096ff',
    'primary_lighter': '#69b1ff',
    'primary_dark': '#0958d9',
    
    # 功能色
    'success': '#52c41a',
    'warning': '#faad14',
    'danger': '#ff4d4f',
    'info': '#1677ff',
    
    # 图表色 - 金融配色
    'chart_up': '#ec5b56',
    'chart_down': '#47b262',
    'chart_ma5': '#6395f9',
    'chart_ma10': '#62daab',
    'chart_ma20': '#657798',
    'chart_ma60': '#f6c344',
    'chart_volume': '#4096ff',
}

# 全局样式 - 设置字体大小为12
GLOBAL_STYLE = """
* {
    font-size: 12px;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
}

QMainWindow {
    background-color: #f5f5f5;
}

/* 确保 QFluentWidgets 控件也使用12号字体 */
PushButton, PrimaryPushButton, ToolButton, TransparentToolButton {
    font-size: 12px;
}

ComboBox, LineEdit, TextEdit, PlainTextEdit, SpinBox, DoubleSpinBox, DateEdit {
    font-size: 12px;
}

TabBar, NavigationBar, TreeWidget, ListWidget, TableWidget {
    font-size: 12px;
}
"""

# 主窗口样式（仅背景色）
MAIN_WINDOW_STYLE = f"""
QMainWindow {{
    background-color: #f5f5f5;
}}
"""