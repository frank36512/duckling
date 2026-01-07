"""
策略配置面板
用于选择、配置和测试交易策略
"""

import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QSpinBox, QDoubleSpinBox, QFormLayout,
                             QMessageBox)
from PyQt5.QtCore import Qt
from qfluentwidgets import (PushButton, LineEdit, TextEdit, ComboBox,
                            PrimaryPushButton, ListWidget)
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategy_base import StrategyFactory
from ui.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class StrategyPanel(QWidget):
    """策略配置面板"""
    
    # 策略中英文名称映射（类变量，方便其他地方使用）
    STRATEGY_DISPLAY_NAMES = {
        'MA_CrossOver': '📈 均线策略（金叉死叉）',
        'RSI_OverboughtOversold': '📊 RSI策略（超买超卖）',
        'MACD': '📉 MACD策略（趋势跟踪）',
        'BollingerBands': '📊 布林带策略（均值回归）',
        'KDJ': '⚡ KDJ策略（超买超卖）',
        'MA_Volume': '📊 双均线+成交量策略',
        'ATR_Breakout': '💥 ATR突破策略',
        'CCI': '📈 CCI策略（顺势指标）',
        'TurtleTrading': '🐢 海龟交易策略',
        'GridTrading': '🔲 网格交易策略',
        'WilliamsR': '📉 威廉指标策略',
        'DMI': '📊 DMI/ADX策略（趋势强度）',
        'VWAP': '📊 VWAP策略（成交量加权）',
        'OBV': '📈 OBV策略（能量潮）',
        'TripleScreen': '🔍 三重滤网策略',
        'MultiFactor': '🎯 多因子策略',
        'MeanReversion': '🔄 均值回归策略（经典量化）',
        'MomentumBreakout': '🚀 动量突破策略（趋势跟踪）',
        'AlphaArbitrage': '💎 Alpha套利策略（市场中性）',
        'DualMAEnhanced': '📈 双均线增强策略（葛兰碧法则）',
        'TrendStrength': '💪 趋势强度策略（ADX+DMI）',
        'GapTrading': '⚡ 跳空缺口策略（缺口理论）',
        'SupportResistance': '🎯 支撑阻力突破（关键价位）',
        'RandomForest': '🌲 随机森林策略（机器学习）',
        'LSTM': '🧠 LSTM策略（深度学习）',
        'XGBoost': '⚡ XGBoost策略（梯度提升）',
    }
    
    def __init__(self, config: dict):
        """
        初始化策略配置面板
        :param config: 配置字典
        """
        super().__init__()
        
        self.config = config
        self.current_strategy = None
        self.init_ui()
        
        logger.info("策略配置面板初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        
        # 使用主题管理器的统一样式
        self.setStyleSheet(ThemeManager.get_panel_stylesheet())
        
        # 使用分割器实现左右布局
        from PyQt5.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：策略列表（更窄）
        left_panel = self.create_strategy_list_panel()
        left_panel.setMaximumWidth(350)  # 限制最大宽度
        splitter.addWidget(left_panel)
        
        # 右侧：策略配置（更宽）
        right_panel = self.create_strategy_config_panel()
        splitter.addWidget(right_panel)
        
        # 设置比例 1:3
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
    
    def create_strategy_list_panel(self):
        """创建策略列表面板"""
        group = QGroupBox("策略列表")
        layout = QVBoxLayout()
        
        # 策略分类标签
        layout.addWidget(QLabel("<b>内置策略</b>"))
        
        # 策略列表
        self.strategy_list = ListWidget()
        
        # 获取内置策略
        builtin_strategies = StrategyFactory.get_builtin_strategies()
        
        for strategy_name in builtin_strategies:
            display_name = self.STRATEGY_DISPLAY_NAMES.get(strategy_name, strategy_name)
            self.strategy_list.addItem(display_name)
        
        self.strategy_list.currentItemChanged.connect(self.on_strategy_selected)
        layout.addWidget(self.strategy_list)
        
        # 按钮组
        btn_layout = QVBoxLayout()
        
        self.load_custom_btn = PushButton("📂 导入自定义策略")
        self.load_custom_btn.clicked.connect(self.load_custom_strategy)
        btn_layout.addWidget(self.load_custom_btn)
        
        self.save_strategy_btn = PushButton("💾 保存配置")
        self.save_strategy_btn.clicked.connect(self.save_strategy_config)
        btn_layout.addWidget(self.save_strategy_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
    
    def create_strategy_config_panel(self):
        """创建策略配置面板"""
        group = QGroupBox("策略配置")
        layout = QVBoxLayout()
        
        # 策略名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("策略名称:"))
        self.strategy_name_label = QLabel("未选择")
        name_layout.addWidget(self.strategy_name_label)
        name_layout.addStretch()
        layout.addLayout(name_layout)
        
        # 策略描述
        layout.addWidget(QLabel("策略说明:"))
        self.strategy_desc = TextEdit()
        self.strategy_desc.setReadOnly(True)
        self.strategy_desc.setMinimumHeight(150)  # 增加最小高度，确保完整显示
        self.strategy_desc.setMaximumHeight(200)  # 增加最大高度
        layout.addWidget(self.strategy_desc)
        
        # 参数配置区域
        self.params_group = QGroupBox("参数配置")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        layout.addWidget(self.params_group)
        
        # 参数控件字典
        self.param_widgets = {}
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.load_config_btn = PushButton("📁 加载配置")
        self.load_config_btn.clicked.connect(self.load_strategy_config)
        btn_layout.addWidget(self.load_config_btn)
        
        btn_layout.addStretch()
        
        self.test_strategy_btn = PrimaryPushButton("🧪 快速测试策略")
        self.test_strategy_btn.clicked.connect(self.test_strategy)
        self.test_strategy_btn.setEnabled(False)
        btn_layout.addWidget(self.test_strategy_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    @classmethod
    def get_strategy_name_from_display(cls, display_name: str) -> str:
        """从显示名称获取真实策略名称"""
        for strategy_name, display in cls.STRATEGY_DISPLAY_NAMES.items():
            if display == display_name:
                return strategy_name
        return display_name
    
    def on_strategy_selected(self, current, previous):
        """策略选择事件"""
        if current is None:
            return
        
        display_name = current.text()
        strategy_name = self.get_strategy_name_from_display(display_name)
        
        # 根据策略名称加载对应的配置
        if strategy_name == 'MA_CrossOver':
            self.load_ma_strategy()
        elif strategy_name == 'RSI_OverboughtOversold':
            self.load_rsi_strategy()
        elif strategy_name == 'MACD':
            self.load_macd_strategy()
        elif strategy_name == 'BollingerBands':
            self.load_bollinger_strategy()
        elif strategy_name == 'KDJ':
            self.load_kdj_strategy()
        elif strategy_name == 'MA_Volume':
            self.load_ma_volume_strategy()
        elif strategy_name == 'ATR_Breakout':
            self.load_atr_strategy()
        elif strategy_name == 'CCI':
            self.load_cci_strategy()
        elif strategy_name == 'TurtleTrading':
            self.load_turtle_strategy()
        elif strategy_name == 'GridTrading':
            self.load_grid_strategy()
        elif strategy_name == 'WilliamsR':
            self.load_williams_r_strategy()
        elif strategy_name == 'DMI':
            self.load_dmi_strategy()
        elif strategy_name == 'VWAP':
            self.load_vwap_strategy()
        elif strategy_name == 'OBV':
            self.load_obv_strategy()
        elif strategy_name == 'TripleScreen':
            self.load_triple_screen_strategy()
        elif strategy_name == 'MultiFactor':
            self.load_multifactor_strategy()
        else:
            # 其他策略的通用加载（机器学习策略等）
            self.load_generic_strategy(strategy_name, display_name)
    
    def load_ma_strategy(self):
        """加载均线策略"""
        self.strategy_name_label.setText("均线策略（金叉死叉）")
        
        description = """
        <b>策略原理：</b><br>
        利用短期均线和长期均线的交叉来判断买卖时机。<br><br>
        
        <b>交易信号：</b><br>
        • 金叉（买入）：短期均线从下向上穿过长期均线<br>
        • 死叉（卖出）：短期均线从上向下穿过长期均线<br><br>
        
        <b>适用场景：</b><br>
        趋势明显的市场环境，不适合震荡市。
        """
        
        self.strategy_desc.setHtml(description)
        
        # 清空参数布局
        self.clear_params_layout()
        
        # 添加参数控件
        short_period = QSpinBox()
        short_period.setRange(1, 100)
        short_period.setValue(5)
        self.param_widgets['short_period'] = short_period
        self.params_layout.addRow("短期均线周期:", short_period)
        
        long_period = QSpinBox()
        long_period.setRange(1, 200)
        long_period.setValue(20)
        self.param_widgets['long_period'] = long_period
        self.params_layout.addRow("长期均线周期:", long_period)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_rsi_strategy(self):
        """加载RSI策略"""
        self.strategy_name_label.setText("RSI策略（超买超卖）")
        
        description = """
        <b>策略原理：</b><br>
        利用RSI指标判断市场超买超卖状态。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：RSI < 超卖阈值（如30），表示超卖<br>
        • 卖出：RSI > 超买阈值（如70），表示超买<br><br>
        
        <b>适用场景：</b><br>
        震荡市场，用于捕捉短期反弹或回调。
        """
        
        self.strategy_desc.setHtml(description)
        
        # 清空参数布局
        self.clear_params_layout()
        
        # 添加参数控件
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
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_macd_strategy(self):
        """加载MACD策略"""
        self.strategy_name_label.setText("MACD策略（趋势跟踪）")
        
        description = """
        <b>策略原理：</b><br>
        利用MACD线与信号线的交叉判断趋势变化。<br><br>
        
        <b>交易信号：</b><br>
        • 金叉（买入）：MACD线从下向上穿过信号线<br>
        • 死叉（卖出）：MACD线从上向下穿过信号线<br><br>
        
        <b>适用场景：</b><br>
        中长期趋势跟踪，适合趋势明确的市场。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        fast_period = QSpinBox()
        fast_period.setRange(5, 30)
        fast_period.setValue(12)
        self.param_widgets['fast_period'] = fast_period
        self.params_layout.addRow("快线周期:", fast_period)
        
        slow_period = QSpinBox()
        slow_period.setRange(15, 50)
        slow_period.setValue(26)
        self.param_widgets['slow_period'] = slow_period
        self.params_layout.addRow("慢线周期:", slow_period)
        
        signal_period = QSpinBox()
        signal_period.setRange(5, 20)
        signal_period.setValue(9)
        self.param_widgets['signal_period'] = signal_period
        self.params_layout.addRow("信号线周期:", signal_period)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_bollinger_strategy(self):
        """加载布林带策略"""
        self.strategy_name_label.setText("布林带策略（均值回归）")
        
        description = """
        <b>策略原理：</b><br>
        利用价格在布林带上下轨之间的波动进行交易。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：价格触及或跌破下轨，预期反弹<br>
        • 卖出：价格触及或突破上轨，预期回调<br><br>
        
        <b>适用场景：</b><br>
        震荡市场，适合捕捉短期波动。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        period = QSpinBox()
        period.setRange(10, 50)
        period.setValue(20)
        self.param_widgets['period'] = period
        self.params_layout.addRow("均线周期:", period)
        
        devfactor = QDoubleSpinBox()
        devfactor.setRange(1.0, 3.0)
        devfactor.setSingleStep(0.1)
        devfactor.setValue(2.0)
        self.param_widgets['devfactor'] = devfactor
        self.params_layout.addRow("标准差倍数:", devfactor)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_kdj_strategy(self):
        """加载KDJ策略"""
        self.strategy_name_label.setText("KDJ策略（超买超卖）")
        
        description = """
        <b>策略原理：</b><br>
        利用KDJ指标判断超买超卖状态。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：K值和D值都在超卖区，且K线上穿D线<br>
        • 卖出：K值和D值都在超买区，且K线下穿D线<br><br>
        
        <b>适用场景：</b><br>
        短期交易，适合震荡市场。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        period = QSpinBox()
        period.setRange(5, 20)
        period.setValue(9)
        self.param_widgets['period'] = period
        self.params_layout.addRow("KDJ周期:", period)
        
        oversold = QSpinBox()
        oversold.setRange(10, 30)
        oversold.setValue(20)
        self.param_widgets['oversold'] = oversold
        self.params_layout.addRow("超卖线:", oversold)
        
        overbought = QSpinBox()
        overbought.setRange(70, 90)
        overbought.setValue(80)
        self.param_widgets['overbought'] = overbought
        self.params_layout.addRow("超买线:", overbought)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_ma_volume_strategy(self):
        """加载双均线+成交量策略"""
        self.strategy_name_label.setText("双均线+成交量策略")
        
        description = """
        <b>策略原理：</b><br>
        结合价格均线和成交量，确保交易信号有成交量配合。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：均线金叉 + 成交量放大<br>
        • 卖出：均线死叉 或 触发止损<br><br>
        
        <b>适用场景：</b><br>
        趋势启动阶段，避免虚假突破。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        short_period = QSpinBox()
        short_period.setRange(3, 15)
        short_period.setValue(5)
        self.param_widgets['short_period'] = short_period
        self.params_layout.addRow("短期均线:", short_period)
        
        long_period = QSpinBox()
        long_period.setRange(15, 60)
        long_period.setValue(20)
        self.param_widgets['long_period'] = long_period
        self.params_layout.addRow("长期均线:", long_period)
        
        volume_factor = QDoubleSpinBox()
        volume_factor.setRange(1.2, 3.0)
        volume_factor.setSingleStep(0.1)
        volume_factor.setValue(1.5)
        self.param_widgets['volume_factor'] = volume_factor
        self.params_layout.addRow("放量倍数:", volume_factor)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_atr_strategy(self):
        """加载ATR突破策略"""
        self.strategy_name_label.setText("ATR突破策略")
        
        description = """
        <b>策略原理：</b><br>
        ATR（平均真实波幅）衡量市场波动性，当价格突破近期高点+ATR倍数时买入。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：收盘价 > N日最高价 + ATR × 突破系数<br>
        • 卖出：收盘价 < N日最低价 - ATR × 突破系数，或触发止损<br><br>
        
        <b>适用场景：</b><br>
        波动率突破系统，适合趋势行情，避免震荡市场。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        atr_period = QSpinBox()
        atr_period.setRange(5, 30)
        atr_period.setValue(14)
        self.param_widgets['atr_period'] = atr_period
        self.params_layout.addRow("ATR周期:", atr_period)
        
        lookback_period = QSpinBox()
        lookback_period.setRange(10, 60)
        lookback_period.setValue(20)
        self.param_widgets['lookback_period'] = lookback_period
        self.params_layout.addRow("回看周期:", lookback_period)
        
        breakout_multiplier = QDoubleSpinBox()
        breakout_multiplier.setRange(1.0, 5.0)
        breakout_multiplier.setSingleStep(0.5)
        breakout_multiplier.setValue(2.0)
        self.param_widgets['breakout_multiplier'] = breakout_multiplier
        self.params_layout.addRow("突破倍数:", breakout_multiplier)
        
        stop_multiplier = QDoubleSpinBox()
        stop_multiplier.setRange(1.0, 5.0)
        stop_multiplier.setSingleStep(0.5)
        stop_multiplier.setValue(3.0)
        self.param_widgets['stop_multiplier'] = stop_multiplier
        self.params_layout.addRow("止损倍数:", stop_multiplier)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_cci_strategy(self):
        """加载CCI策略"""
        self.strategy_name_label.setText("CCI策略（顺势指标）")
        
        description = """
        <b>策略原理：</b><br>
        CCI（商品通道指数）衡量价格偏离统计平均值的程度。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：CCI从下方上穿-100（超卖反弹）<br>
        • 卖出：CCI从上方下穿+100（超买回调）<br><br>
        
        <b>适用场景：</b><br>
        捕捉超买超卖反转机会，适合波动性较大的市场。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        cci_period = QSpinBox()
        cci_period.setRange(10, 50)
        cci_period.setValue(20)
        self.param_widgets['cci_period'] = cci_period
        self.params_layout.addRow("CCI周期:", cci_period)
        
        oversold_level = QSpinBox()
        oversold_level.setRange(-200, 0)
        oversold_level.setValue(-100)
        self.param_widgets['oversold_level'] = oversold_level
        self.params_layout.addRow("超卖水平:", oversold_level)
        
        overbought_level = QSpinBox()
        overbought_level.setRange(0, 200)
        overbought_level.setValue(100)
        self.param_widgets['overbought_level'] = overbought_level
        self.params_layout.addRow("超买水平:", overbought_level)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_turtle_strategy(self):
        """加载海龟交易策略"""
        self.strategy_name_label.setText("海龟交易策略")
        
        description = """
        <b>策略原理：</b><br>
        经典趋势跟踪系统，使用唐奇安通道（Donchian Channel）进行突破交易。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：价格突破N日最高价<br>
        • 卖出：价格跌破M日最低价，或触发ATR动态止损<br><br>
        
        <b>适用场景：</b><br>
        中长期趋势跟踪，适合大趋势行情。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        entry_period = QSpinBox()
        entry_period.setRange(10, 60)
        entry_period.setValue(20)
        self.param_widgets['entry_period'] = entry_period
        self.params_layout.addRow("入场周期:", entry_period)
        
        exit_period = QSpinBox()
        exit_period.setRange(5, 30)
        exit_period.setValue(10)
        self.param_widgets['exit_period'] = exit_period
        self.params_layout.addRow("出场周期:", exit_period)
        
        atr_period = QSpinBox()
        atr_period.setRange(10, 30)
        atr_period.setValue(20)
        self.param_widgets['atr_period'] = atr_period
        self.params_layout.addRow("ATR周期:", atr_period)
        
        atr_multiplier = QDoubleSpinBox()
        atr_multiplier.setRange(1.0, 5.0)
        atr_multiplier.setSingleStep(0.5)
        atr_multiplier.setValue(2.0)
        self.param_widgets['atr_multiplier'] = atr_multiplier
        self.params_layout.addRow("ATR止损倍数:", atr_multiplier)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_grid_strategy(self):
        """加载网格交易策略"""
        self.strategy_name_label.setText("网格交易策略")
        
        description = """
        <b>策略原理：</b><br>
        在价格区间内设置网格线，价格下跌到网格线买入，上涨到网格线卖出。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：价格跌破下方网格线<br>
        • 卖出：价格突破上方网格线<br><br>
        
        <b>适用场景：</b><br>
        震荡行情高抛低吸，不适合单边趋势行情。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        lookback_period = QSpinBox()
        lookback_period.setRange(30, 120)
        lookback_period.setValue(60)
        self.param_widgets['lookback_period'] = lookback_period
        self.params_layout.addRow("回看周期:", lookback_period)
        
        grid_num = QSpinBox()
        grid_num.setRange(3, 10)
        grid_num.setValue(5)
        self.param_widgets['grid_num'] = grid_num
        self.params_layout.addRow("网格数量:", grid_num)
        
        grid_spacing = QDoubleSpinBox()
        grid_spacing.setRange(0.02, 0.15)
        grid_spacing.setSingleStep(0.01)
        grid_spacing.setValue(0.05)
        self.param_widgets['grid_spacing'] = grid_spacing
        self.params_layout.addRow("网格间距(%):", grid_spacing)
        
        max_layers = QSpinBox()
        max_layers.setRange(1, 5)
        max_layers.setValue(3)
        self.param_widgets['max_layers'] = max_layers
        self.params_layout.addRow("最大持仓层数:", max_layers)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_williams_r_strategy(self):
        """加载威廉指标策略"""
        self.strategy_name_label.setText("威廉指标策略")
        
        description = """
        <b>策略原理：</b><br>
        Williams %R衡量当前收盘价在过去N日价格区间中的相对位置。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：%R从下方上穿超卖线（例如-80）<br>
        • 卖出：%R从上方下穿超买线（例如-20）<br><br>
        
        <b>适用场景：</b><br>
        短期超买超卖判断，适合波动市场。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        period = QSpinBox()
        period.setRange(5, 30)
        period.setValue(14)
        self.param_widgets['period'] = period
        self.params_layout.addRow("计算周期:", period)
        
        oversold = QSpinBox()
        oversold.setRange(-100, -50)
        oversold.setValue(-80)
        self.param_widgets['oversold'] = oversold
        self.params_layout.addRow("超卖线:", oversold)
        
        overbought = QSpinBox()
        overbought.setRange(-50, 0)
        overbought.setValue(-20)
        self.param_widgets['overbought'] = overbought
        self.params_layout.addRow("超买线:", overbought)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_dmi_strategy(self):
        """加载DMI/ADX策略"""
        self.strategy_name_label.setText("DMI/ADX策略（趋势强度）")
        
        description = """
        <b>策略原理：</b><br>
        DMI（方向运动指标）包含+DI、-DI和ADX，用于判断趋势方向和强度。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：+DI上穿-DI，且ADX > 阈值（趋势强）<br>
        • 卖出：-DI上穿+DI，或ADX下降（趋势减弱）<br><br>
        
        <b>适用场景：</b><br>
        趋势跟踪，ADX可过滤震荡行情。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        period = QSpinBox()
        period.setRange(10, 30)
        period.setValue(14)
        self.param_widgets['period'] = period
        self.params_layout.addRow("DMI周期:", period)
        
        adx_threshold = QSpinBox()
        adx_threshold.setRange(15, 35)
        adx_threshold.setValue(25)
        self.param_widgets['adx_threshold'] = adx_threshold
        self.params_layout.addRow("ADX阈值:", adx_threshold)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_vwap_strategy(self):
        """加载VWAP策略"""
        self.strategy_name_label.setText("VWAP策略（成交量加权）")
        
        description = """
        <b>策略原理：</b><br>
        VWAP（成交量加权平均价）是机构常用的基准价格。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：价格跌破VWAP一定比例（低于市场平均成本）<br>
        • 卖出：价格超过VWAP一定比例（高于市场平均成本）<br><br>
        
        <b>适用场景：</b><br>
        日内交易或短期均值回归，适合有一定流动性的股票。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        period = QSpinBox()
        period.setRange(10, 60)
        period.setValue(20)
        self.param_widgets['period'] = period
        self.params_layout.addRow("VWAP周期:", period)
        
        buy_threshold = QDoubleSpinBox()
        buy_threshold.setRange(0.01, 0.10)
        buy_threshold.setSingleStep(0.01)
        buy_threshold.setValue(0.02)
        self.param_widgets['buy_threshold'] = buy_threshold
        self.params_layout.addRow("买入偏离度(%):", buy_threshold)
        
        sell_threshold = QDoubleSpinBox()
        sell_threshold.setRange(0.01, 0.10)
        sell_threshold.setSingleStep(0.01)
        sell_threshold.setValue(0.02)
        self.param_widgets['sell_threshold'] = sell_threshold
        self.params_layout.addRow("卖出偏离度(%):", sell_threshold)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_obv_strategy(self):
        """加载OBV策略"""
        self.strategy_name_label.setText("OBV策略（能量潮）")
        
        description = """
        <b>策略原理：</b><br>
        OBV（能量潮）通过累计成交量来判断资金流向和趋势。<br><br>
        
        <b>交易信号：</b><br>
        • 买入：OBV上穿其均线（资金流入）<br>
        • 卖出：OBV下穿其均线（资金流出）<br><br>
        
        <b>适用场景：</b><br>
        验证价格趋势，防止虚假突破。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        obv_period = QSpinBox()
        obv_period.setRange(10, 50)
        obv_period.setValue(20)
        self.param_widgets['obv_period'] = obv_period
        self.params_layout.addRow("OBV均线周期:", obv_period)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_triple_screen_strategy(self):
        """加载三重滤网策略"""
        self.strategy_name_label.setText("三重滤网策略")
        
        description = """
        <b>策略原理：</b><br>
        三重滤网交易系统，使用三个不同时间框架进行多重确认。<br><br>
        
        <b>交易信号：</b><br>
        • 第一重：长期趋势（MACD判断方向）<br>
        • 第二重：中期震荡（RSI寻找反转）<br>
        • 第三重：短期入场（价格突破）<br><br>
        
        <b>适用场景：</b><br>
        多重确认降低风险，适合稳健型交易。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        long_period = QSpinBox()
        long_period.setRange(20, 60)
        long_period.setValue(26)
        self.param_widgets['long_period'] = long_period
        self.params_layout.addRow("长期MACD慢线:", long_period)
        
        rsi_period = QSpinBox()
        rsi_period.setRange(10, 30)
        rsi_period.setValue(14)
        self.param_widgets['rsi_period'] = rsi_period
        self.params_layout.addRow("中期RSI周期:", rsi_period)
        
        breakout_period = QSpinBox()
        breakout_period.setRange(5, 20)
        breakout_period.setValue(10)
        self.param_widgets['breakout_period'] = breakout_period
        self.params_layout.addRow("短期突破周期:", breakout_period)
        
        stop_loss = QDoubleSpinBox()
        stop_loss.setRange(0.03, 0.15)
        stop_loss.setSingleStep(0.01)
        stop_loss.setValue(0.05)
        self.param_widgets['stop_loss'] = stop_loss
        self.params_layout.addRow("止损比例:", stop_loss)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_multifactor_strategy(self):
        """加载多因子策略"""
        self.strategy_name_label.setText("多因子策略")
        
        description = """
        <b>策略原理：</b><br>
        综合多个技术指标进行评分，当总分达到阈值时产生交易信号。<br><br>
        
        <b>交易信号：</b><br>
        • 评分因子：趋势、动量、波动率、成交量等<br>
        • 买入：综合得分 > 买入阈值<br>
        • 卖出：综合得分 < 卖出阈值<br><br>
        
        <b>适用场景：</b><br>
        量化选股，综合多维度信息。
        """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        ma_weight = QDoubleSpinBox()
        ma_weight.setRange(0.0, 1.0)
        ma_weight.setSingleStep(0.1)
        ma_weight.setValue(0.3)
        self.param_widgets['ma_weight'] = ma_weight
        self.params_layout.addRow("均线权重:", ma_weight)
        
        rsi_weight = QDoubleSpinBox()
        rsi_weight.setRange(0.0, 1.0)
        rsi_weight.setSingleStep(0.1)
        rsi_weight.setValue(0.3)
        self.param_widgets['rsi_weight'] = rsi_weight
        self.params_layout.addRow("RSI权重:", rsi_weight)
        
        volume_weight = QDoubleSpinBox()
        volume_weight.setRange(0.0, 1.0)
        volume_weight.setSingleStep(0.1)
        volume_weight.setValue(0.4)
        self.param_widgets['volume_weight'] = volume_weight
        self.params_layout.addRow("成交量权重:", volume_weight)
        
        buy_threshold = QDoubleSpinBox()
        buy_threshold.setRange(0.5, 1.0)
        buy_threshold.setSingleStep(0.05)
        buy_threshold.setValue(0.7)
        self.param_widgets['buy_threshold'] = buy_threshold
        self.params_layout.addRow("买入阈值:", buy_threshold)
        
        sell_threshold = QDoubleSpinBox()
        sell_threshold.setRange(0.0, 0.5)
        sell_threshold.setSingleStep(0.05)
        sell_threshold.setValue(0.3)
        self.param_widgets['sell_threshold'] = sell_threshold
        self.params_layout.addRow("卖出阈值:", sell_threshold)
        
        self.test_strategy_btn.setEnabled(True)
    
    def load_generic_strategy(self, strategy_name: str, display_name: str):
        """加载通用策略（用于机器学习策略等特殊策略）"""
        self.strategy_name_label.setText(display_name)
        
        # 判断是否为机器学习策略
        if strategy_name in ['RandomForest', 'LSTM', 'XGBoost']:
            description = f"""
            <b>策略类型：</b>机器学习策略<br>
            <b>策略名称：</b>{display_name}<br><br>
            
            <b>说明：</b><br>
            机器学习策略需要先进行模型训练，然后才能用于交易。<br><br>
            
            <b>使用步骤：</b><br>
            1. 准备历史数据（至少1-2年）<br>
            2. 在"参数优化"页面训练模型<br>
            3. 模型训练完成后，在"回测分析"页面测试<br>
            4. 验证效果后可用于实盘交易<br><br>
            
            <b>⚠️ 注意：</b><br>
            • 机器学习策略对数据质量要求较高<br>
            • 需要定期重新训练模型以适应市场变化<br>
            • 建议先用传统策略熟悉系统后再使用
            """
        else:
            description = f"""
            <b>策略名称：</b>{display_name}<br>
            <b>策略代码：</b>{strategy_name}<br><br>
            
            <b>说明：</b><br>
            该策略的详细配置界面正在开发中。<br>
            您可以使用默认参数进行回测，或通过编辑配置文件来自定义参数。<br><br>
            
            <b>使用方法：</b><br>
            1. 点击"保存配置"保存当前设置<br>
            2. 在回测面板中选择该策略进行测试<br>
            3. 查看策略源代码了解详细参数<br>
            """
        
        self.strategy_desc.setHtml(description)
        self.clear_params_layout()
        
        # 添加提示标签
        if strategy_name in ['RandomForest', 'LSTM', 'XGBoost']:
            info_label = QLabel("ℹ️ 机器学习策略需要先训练模型，请前往\"参数优化\"页面")
        else:
            info_label = QLabel("⚠️ 该策略使用默认参数，详细配置功能正在开发中")
        
        info_label.setWordWrap(True)
        self.params_layout.addRow(info_label)
        
        self.test_strategy_btn.setEnabled(True)
    
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
            elif isinstance(widget, LineEdit):
                params[key] = widget.text()
        
        return params
    
    def test_strategy(self):
        """测试策略"""
        strategy_name = self.strategy_name_label.text()
        params = self.get_strategy_params()
        
        msg = f"<b>策略名称：</b>{strategy_name}<br><br>"
        msg += "<b>配置参数：</b><br>"
        for key, value in params.items():
            msg += f"• {key}: {value}<br>"
        msg += "<br><b>💡 快速测试提示：</b><br>"
        msg += "1. 切换到<b>\"回测分析\"</b>选项卡进行完整回测<br>"
        msg += "2. 选择股票代码（如：000001）<br>"
        msg += "3. 设置回测周期（建议1-2年）<br>"
        msg += "4. 点击\"开始回测\"查看结果<br><br>"
        msg += "<b>⚠️ 说明：</b><br>"
        msg += "完整的回测可以生成收益曲线、回撤曲线等可视化图表，"
        msg += "并计算夏普比率、最大回撤等关键指标。"
        
        QMessageBox.information(self, "策略配置完成", msg)
    
    def load_custom_strategy(self):
        """加载自定义策略"""
        from PyQt5.QtWidgets import QFileDialog
        
        # 显示开发指南
        guide_msg = (
            "<h3>自定义策略开发指南</h3><br>"
            "<b>📝 步骤：</b><br>"
            "1. 在 <code>strategies/</code> 目录创建新策略文件<br>"
            "2. 继承 <code>StrategyBase</code> 类<br>"
            "3. 实现必要方法（如 <code>__init__</code>, <code>next</code>）<br>"
            "4. 重启程序后即可在策略列表中使用<br><br>"
            "<b>📖 参考示例：</b><br>"
            "• ma_crossover_strategy.py（均线交叉）<br>"
            "• macd_strategy.py（MACD策略）<br>"
            "• rsi_strategy.py（RSI策略）<br><br>"
            "<b>💡 提示：</b><br>"
            "目前已提供6种内置策略，建议先使用内置策略进行测试。<br>"
            "如需自定义策略，请参考strategies目录下的示例代码。<br><br>"
            "<b>是否要打开策略目录？</b>"
        )
        
        reply = QMessageBox.question(
            self,
            "自定义策略",
            guide_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            import os
            import subprocess
            strategy_dir = Path(__file__).parent.parent / 'strategies'
            
            try:
                # 在资源管理器中打开策略目录
                if os.name == 'nt':  # Windows
                    os.startfile(str(strategy_dir))
                elif os.name == 'posix':  # Linux/Mac
                    subprocess.Popen(['xdg-open', str(strategy_dir)])
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开目录：{e}")
    
    def load_strategy_config(self):
        """加载策略配置"""
        import json
        from PyQt5.QtWidgets import QFileDialog
        
        config_dir = Path(__file__).parent.parent / 'strategies' / 'configs'
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择策略配置文件",
            str(config_dir),
            "JSON配置文件 (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            strategy_name = config_data.get('strategy_name', '')
            params = config_data.get('parameters', {})
            saved_time = config_data.get('saved_time', '未知')
            
            # 根据策略名称加载对应策略
            if "均线策略" in strategy_name:
                self.load_ma_strategy()
            elif "RSI策略" in strategy_name:
                self.load_rsi_strategy()
            else:
                QMessageBox.warning(self, "警告", f"未知的策略类型：{strategy_name}")
                return
            
            # 应用参数
            for param_name, param_value in params.items():
                if param_name in self.param_widgets:
                    widget = self.param_widgets[param_name]
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.setValue(param_value)
            
            logger.info(f"策略配置已加载: {file_path}")
            QMessageBox.information(
                self,
                "加载成功",
                f"策略配置已加载！\n\n"
                f"配置文件：{Path(file_path).name}\n"
                f"策略：{strategy_name}\n"
                f"保存时间：{saved_time}\n"
                f"参数：{params}"
            )
        except Exception as e:
            logger.error(f"加载策略配置失败: {e}")
            QMessageBox.critical(
                self,
                "加载失败",
                f"加载策略配置时出错：\n{e}"
            )
    
    def save_strategy_config(self):
        """保存策略配置"""
        import json
        from datetime import datetime
        
        strategy_name = self.strategy_name_label.text()
        
        if strategy_name == "未选择":
            QMessageBox.warning(self, "警告", "请先选择一个策略！")
            return
        
        params = self.get_strategy_params()
        
        # 创建策略配置目录
        config_dir = Path(__file__).parent.parent / 'strategies' / 'configs'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        config_data = {
            'strategy_name': strategy_name,
            'parameters': params,
            'saved_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        config_file = config_dir / f'{strategy_name}_config.json'
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"策略配置已保存: {config_file}")
            QMessageBox.information(
                self,
                "保存成功",
                f"策略配置已保存到：\n{config_file}\n\n"
                f"策略：{strategy_name}\n"
                f"参数：{params}"
            )
        except Exception as e:
            logger.error(f"保存策略配置失败: {e}")
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存策略配置时出错：\n{e}"
            )
