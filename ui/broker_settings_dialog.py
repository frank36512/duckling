"""
券商设置对话框
用于配置券商账户信息和交易模式
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QComboBox, QPushButton, QCheckBox,
                            QGroupBox, QFormLayout, QMessageBox, QSpinBox,
                            QDoubleSpinBox, QTabWidget, QWidget, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BrokerSettingsDialog(QDialog):
    """券商设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = Path("config/broker_config.yaml")
        self.config = self.load_config()
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("券商设置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # 应用深色主题样式
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            self.setStyleSheet("""
                QDialog {
                    background-color: #202020;
                }
                QWidget {
                    background-color: #202020;
                    color: #d0d0d0;
                }
                QTabWidget::pane {
                    background-color: #2b2b2b;
                    border: 1px solid #3a3a3a;
                }
                QTabBar::tab {
                    background-color: #2b2b2b;
                    color: #909090;
                    padding: 8px 20px;
                    border: 1px solid #3a3a3a;
                }
                QTabBar::tab:selected {
                    background-color: #2b2b2b;
                    color: #b0b0b0;
                    border-bottom-color: #2b2b2b;
                }
                QGroupBox {
                    color: #a0a0a0;
                    border: 1px solid #3a3a3a;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                    background-color: #2a2a2a;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 3px;
                    color: #d0d0d0;
                }
                QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                    border-color: #4a4a4a;
                }
                QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                    border-color: #555555;
                }
                QPushButton {
                    background-color: #3a3a3a;
                    border: 1px solid #4a4a4a;
                    border-radius: 3px;
                    padding: 5px 15px;
                    color: #d0d0d0;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
                QPushButton:pressed {
                    background-color: #2a2a2a;
                }
                QCheckBox {
                    color: #d0d0d0;
                }
                QLabel {
                    color: #c0c0c0;
                    background-color: transparent;
                }
            """)
        
        layout = QVBoxLayout()
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 基本设置标签页
        self.tabs.addTab(self.create_basic_tab(), "基本设置")
        
        # 券商配置标签页
        self.tabs.addTab(self.create_broker_tab(), "券商配置")
        
        # 交易限制标签页
        self.tabs.addTab(self.create_limits_tab(), "交易限制")
        
        # 风控设置标签页
        self.tabs.addTab(self.create_risk_tab(), "风控设置")
        
        # 通知设置标签页
        self.tabs.addTab(self.create_notification_tab(), "通知设置")
        
        # 帮助标签页
        self.tabs.addTab(self.create_help_tab(), "使用说明")
        
        layout.addWidget(self.tabs)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_basic_tab(self):
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 交易模式组
        mode_group = QGroupBox("交易模式")
        mode_layout = QFormLayout()
        
        # 模式选择
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["模拟交易", "实盘交易"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addRow("模式:", self.mode_combo)
        
        # 模拟资金
        self.simulation_capital = QDoubleSpinBox()
        self.simulation_capital.setRange(10000, 10000000)
        self.simulation_capital.setValue(100000)
        self.simulation_capital.setSuffix(" 元")
        mode_layout.addRow("模拟资金:", self.simulation_capital)
        
        # 实盘确认
        self.real_confirmed = QCheckBox("我已知晓实盘交易风险")
        self.real_confirmed.setEnabled(False)
        mode_layout.addRow("实盘确认:", self.real_confirmed)
        
        # 安全密码
        self.safety_password = QLineEdit()
        self.safety_password.setEchoMode(QLineEdit.Password)
        self.safety_password.setEnabled(False)
        self.safety_password.setPlaceholderText("输入6位数字密码")
        mode_layout.addRow("安全密码:", self.safety_password)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 警告信息
        warning_label = QLabel(
            "⚠️ 重要提示:\n"
            "• 模拟交易：使用虚拟资金，不会产生真实交易\n"
            "• 实盘交易：连接真实券商账户，会产生实际交易\n"
            "• 启用实盘前请务必充分测试策略\n"
            "• 设置合理的交易限制和风控参数"
        )
        warning_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 5px;
                padding: 10px;
                color: #856404;
            }
        """)
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_broker_tab(self):
        """创建券商配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        broker_group = QGroupBox("券商账户信息")
        broker_layout = QFormLayout()
        
        # 券商类型
        self.broker_type = QComboBox()
        self.broker_type.addItems([
            "模拟券商",
            "东方财富",
            "华泰证券", 
            "中信证券",
            "国泰君安",
            "广发证券",
            "海通证券",
            "其他券商"
        ])
        broker_layout.addRow("券商:", self.broker_type)
        
        # 账户信息
        self.account_id = QLineEdit()
        self.account_id.setPlaceholderText("资金账号/客户号")
        broker_layout.addRow("账户ID:", self.account_id)
        
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("登录密码")
        broker_layout.addRow("登录密码:", self.password)
        
        self.trade_password = QLineEdit()
        self.trade_password.setEchoMode(QLineEdit.Password)
        self.trade_password.setPlaceholderText("交易密码（如需要）")
        broker_layout.addRow("交易密码:", self.trade_password)
        
        self.communication_password = QLineEdit()
        self.communication_password.setEchoMode(QLineEdit.Password)
        self.communication_password.setPlaceholderText("通讯密码（如需要）")
        broker_layout.addRow("通讯密码:", self.communication_password)
        
        # API信息
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("API Key（如需要）")
        broker_layout.addRow("API Key:", self.api_key)
        
        self.api_secret = QLineEdit()
        self.api_secret.setEchoMode(QLineEdit.Password)
        self.api_secret.setPlaceholderText("API Secret（如需要）")
        broker_layout.addRow("API Secret:", self.api_secret)
        
        # 服务器信息
        self.server_url = QLineEdit()
        self.server_url.setPlaceholderText("https://api.broker.com")
        broker_layout.addRow("服务器地址:", self.server_url)
        
        self.server_port = QLineEdit()
        self.server_port.setPlaceholderText("443")
        broker_layout.addRow("端口:", self.server_port)
        
        # 其他信息
        self.branch_code = QLineEdit()
        self.branch_code.setPlaceholderText("营业部代码（如需要）")
        broker_layout.addRow("营业部:", self.branch_code)
        
        # 自动登录
        self.auto_login = QCheckBox("启用自动登录")
        broker_layout.addRow("", self.auto_login)
        
        broker_group.setLayout(broker_layout)
        layout.addWidget(broker_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_limits_tab(self):
        """创建交易限制标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        limits_group = QGroupBox("交易限制")
        limits_layout = QFormLayout()
        
        # 金额限制
        self.max_order_amount = QDoubleSpinBox()
        self.max_order_amount.setRange(1000, 10000000)
        self.max_order_amount.setValue(50000)
        self.max_order_amount.setSuffix(" 元")
        limits_layout.addRow("单笔最大金额:", self.max_order_amount)
        
        self.min_order_amount = QDoubleSpinBox()
        self.min_order_amount.setRange(100, 100000)
        self.min_order_amount.setValue(1000)
        self.min_order_amount.setSuffix(" 元")
        limits_layout.addRow("单笔最小金额:", self.min_order_amount)
        
        self.max_daily_amount = QDoubleSpinBox()
        self.max_daily_amount.setRange(10000, 100000000)
        self.max_daily_amount.setValue(200000)
        self.max_daily_amount.setSuffix(" 元")
        limits_layout.addRow("单日最大金额:", self.max_daily_amount)
        
        # 次数限制
        self.max_daily_orders = QSpinBox()
        self.max_daily_orders.setRange(1, 1000)
        self.max_daily_orders.setValue(20)
        self.max_daily_orders.setSuffix(" 次")
        limits_layout.addRow("单日最大次数:", self.max_daily_orders)
        
        # 持仓限制
        self.max_positions = QSpinBox()
        self.max_positions.setRange(1, 100)
        self.max_positions.setValue(10)
        self.max_positions.setSuffix(" 只")
        limits_layout.addRow("最大持仓数:", self.max_positions)
        
        self.max_position_amount = QDoubleSpinBox()
        self.max_position_amount.setRange(10000, 10000000)
        self.max_position_amount.setValue(100000)
        self.max_position_amount.setSuffix(" 元")
        limits_layout.addRow("单股最大金额:", self.max_position_amount)
        
        # 其他选项
        self.allow_t0 = QCheckBox("允许T+0交易")
        limits_layout.addRow("", self.allow_t0)
        
        self.allow_margin = QCheckBox("允许融资融券")
        limits_layout.addRow("", self.allow_margin)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_risk_tab(self):
        """创建风控设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        risk_group = QGroupBox("风险控制")
        risk_layout = QFormLayout()
        
        # 仓位控制
        self.max_position_ratio = QDoubleSpinBox()
        self.max_position_ratio.setRange(0.01, 1.0)
        self.max_position_ratio.setSingleStep(0.05)
        self.max_position_ratio.setValue(0.3)
        self.max_position_ratio.setDecimals(2)
        risk_layout.addRow("单股最大仓位:", self.max_position_ratio)
        
        # 回撤控制
        self.max_drawdown = QDoubleSpinBox()
        self.max_drawdown.setRange(0.01, 0.5)
        self.max_drawdown.setSingleStep(0.01)
        self.max_drawdown.setValue(0.15)
        self.max_drawdown.setDecimals(2)
        risk_layout.addRow("最大回撤限制:", self.max_drawdown)
        
        # 亏损控制
        self.max_daily_loss = QDoubleSpinBox()
        self.max_daily_loss.setRange(0.01, 0.5)
        self.max_daily_loss.setSingleStep(0.01)
        self.max_daily_loss.setValue(0.05)
        self.max_daily_loss.setDecimals(2)
        risk_layout.addRow("单日亏损限制:", self.max_daily_loss)
        
        # 止损止盈
        self.stop_loss_ratio = QDoubleSpinBox()
        self.stop_loss_ratio.setRange(0.01, 0.5)
        self.stop_loss_ratio.setSingleStep(0.01)
        self.stop_loss_ratio.setValue(0.08)
        self.stop_loss_ratio.setDecimals(2)
        risk_layout.addRow("止损比例:", self.stop_loss_ratio)
        
        self.take_profit_ratio = QDoubleSpinBox()
        self.take_profit_ratio.setRange(0.01, 1.0)
        self.take_profit_ratio.setSingleStep(0.01)
        self.take_profit_ratio.setValue(0.15)
        self.take_profit_ratio.setDecimals(2)
        risk_layout.addRow("止盈比例:", self.take_profit_ratio)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        # 说明
        info_label = QLabel(
            "风控说明:\n"
            "• 单股最大仓位：单只股票占总资金的最大比例\n"
            "• 最大回撤限制：超过此值将强制平仓\n"
            "• 单日亏损限制：超过此值将停止当日交易\n"
            "• 止损/止盈比例：自动触发平仓的盈亏比例"
        )
        info_label.setStyleSheet("color: #666; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_notification_tab(self):
        """创建通知设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 邮件通知
        email_group = QGroupBox("邮件通知")
        email_layout = QFormLayout()
        
        self.email_enabled = QCheckBox("启用邮件通知")
        email_layout.addRow("", self.email_enabled)
        
        self.email_address = QLineEdit()
        self.email_address.setPlaceholderText("your@email.com")
        email_layout.addRow("邮箱地址:", self.email_address)
        
        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("smtp.gmail.com")
        email_layout.addRow("SMTP服务器:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(465)
        email_layout.addRow("SMTP端口:", self.smtp_port)
        
        self.smtp_user = QLineEdit()
        self.smtp_user.setPlaceholderText("SMTP用户名")
        email_layout.addRow("SMTP用户:", self.smtp_user)
        
        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        self.smtp_password.setPlaceholderText("SMTP密码")
        email_layout.addRow("SMTP密码:", self.smtp_password)
        
        email_group.setLayout(email_layout)
        layout.addWidget(email_group)
        
        # 微信通知
        wechat_group = QGroupBox("微信通知")
        wechat_layout = QFormLayout()
        
        self.wechat_enabled = QCheckBox("启用微信通知")
        wechat_layout.addRow("", self.wechat_enabled)
        
        self.wechat_webhook = QLineEdit()
        self.wechat_webhook.setPlaceholderText("企业微信Webhook URL")
        wechat_layout.addRow("Webhook:", self.wechat_webhook)
        
        wechat_group.setLayout(wechat_layout)
        layout.addWidget(wechat_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_help_tab(self):
        """创建帮助标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>券商设置使用说明</h2>
        
        <h3>一、模拟交易 vs 实盘交易</h3>
        <ul>
            <li><b>模拟交易</b>: 使用虚拟资金进行交易，不会产生实际交易。适合策略测试和学习。</li>
            <li><b>实盘交易</b>: 连接真实券商账户，产生实际交易。需要谨慎配置。</li>
        </ul>
        
        <h3>二、启用实盘交易步骤</h3>
        <ol>
            <li>在"基本设置"中选择"实盘交易"模式</li>
            <li>勾选"我已知晓实盘交易风险"确认框</li>
            <li>设置6位数字安全密码</li>
            <li>在"券商配置"中填写真实券商账户信息</li>
            <li>在"交易限制"中设置合理的限制</li>
            <li>在"风控设置"中配置风险控制参数</li>
            <li>点击"测试连接"确保连接正常</li>
            <li>保存设置</li>
        </ol>
        
        <h3>三、支持的券商</h3>
        <ul>
            <li><b>东方财富</b>: 需要资金账号和登录密码</li>
            <li><b>华泰证券</b>: 需要客户号、密码、API Key和Secret</li>
            <li><b>中信证券</b>: 需要资金账号、密码和通讯密码</li>
            <li><b>国泰君安</b>: 需要资金账号和密码</li>
            <li><b>广发证券</b>: 需要资金账号、密码和营业部代码</li>
            <li><b>海通证券</b>: 需要资金账号和密码</li>
        </ul>
        
        <h3>四、安全建议</h3>
        <ul>
            <li>✅ 首次使用务必选择模拟交易模式</li>
            <li>✅ 充分测试策略后再切换到实盘</li>
            <li>✅ 设置合理的单笔和单日交易限制</li>
            <li>✅ 启用止损止盈保护</li>
            <li>✅ 定期检查交易记录和持仓</li>
            <li>✅ 不要将密码告诉他人</li>
            <li>⚠️ 实盘交易有风险，投资需谨慎</li>
        </ul>
        
        <h3>五、常见问题</h3>
        <p><b>Q: 如何切换交易模式？</b></p>
        <p>A: 在"基本设置"标签页修改"模式"选项，保存后重启程序生效。</p>
        
        <p><b>Q: 忘记安全密码怎么办？</b></p>
        <p>A: 手动编辑 config/broker_config.yaml 文件，删除 real_trading_password 字段。</p>
        
        <p><b>Q: 测试连接失败？</b></p>
        <p>A: 检查账户信息是否正确，网络是否正常，券商服务是否可用。</p>
        
        <p><b>Q: 如何查看交易日志？</b></p>
        <p>A: 在 logs/broker 目录下可以找到详细的交易日志。</p>
        """)
        layout.addWidget(help_text)
        
        widget.setLayout(layout)
        return widget
        
    def on_mode_changed(self, index):
        """交易模式改变"""
        is_real = (index == 1)  # 1 = 实盘交易
        
        # 启用/禁用实盘相关控件
        self.real_confirmed.setEnabled(is_real)
        self.safety_password.setEnabled(is_real)
        self.simulation_capital.setEnabled(not is_real)
        
        if is_real:
            # 显示警告
            QMessageBox.warning(
                self,
                "风险提示",
                "⚠️ 您即将启用实盘交易模式！\n\n"
                "实盘交易将连接真实券商账户，产生实际交易和资金变动。\n"
                "请务必:\n"
                "1. 确认已充分测试策略\n"
                "2. 设置合理的交易限制\n"
                "3. 配置风险控制参数\n"
                "4. 定期监控交易状况\n\n"
                "股市有风险，投资需谨慎！"
            )
        
    def load_config(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                return self.get_default_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return self.get_default_config()
            
    def get_default_config(self):
        """获取默认配置"""
        return {
            'trading_mode': {
                'mode': 'simulation',
                'simulation_capital': 100000,
                'real_trading_confirmed': False,
                'real_trading_password': ''
            },
            'broker': {
                'type': 'simulation',
                'account_id': '',
                'password': '',
                'trade_password': '',
                'communication_password': '',
                'api_key': '',
                'api_secret': '',
                'server_url': '',
                'server_port': '',
                'branch_code': '',
                'auto_login': False
            },
            'trading_limits': {
                'max_order_amount': 50000,
                'min_order_amount': 1000,
                'max_daily_amount': 200000,
                'max_daily_orders': 20,
                'max_positions': 10,
                'max_position_amount': 100000,
                'allow_t0': False,
                'allow_margin': False
            },
            'risk_control': {
                'max_position_ratio': 0.3,
                'max_drawdown': 0.15,
                'max_daily_loss': 0.05,
                'stop_loss_ratio': 0.08,
                'take_profit_ratio': 0.15
            },
            'notification': {
                'email_enabled': False,
                'email_address': '',
                'smtp_server': '',
                'smtp_port': 465,
                'smtp_user': '',
                'smtp_password': '',
                'wechat_enabled': False,
                'wechat_webhook': ''
            }
        }
        
    def load_settings(self):
        """加载设置到UI"""
        try:
            # 基本设置
            mode = self.config.get('trading_mode', {})
            self.mode_combo.setCurrentIndex(0 if mode.get('mode') == 'simulation' else 1)
            self.simulation_capital.setValue(mode.get('simulation_capital', 100000))
            self.real_confirmed.setChecked(mode.get('real_trading_confirmed', False))
            self.safety_password.setText(mode.get('real_trading_password', ''))
            
            # 券商配置
            broker = self.config.get('broker', {})
            broker_types = {
                'simulation': 0, 'eastmoney': 1, 'huatai': 2, 
                'citic': 3, 'guotai_junan': 4, 'guangfa': 5, 'haitong': 6
            }
            self.broker_type.setCurrentIndex(broker_types.get(broker.get('type', 'simulation'), 0))
            self.account_id.setText(broker.get('account_id', ''))
            self.password.setText(broker.get('password', ''))
            self.trade_password.setText(broker.get('trade_password', ''))
            self.communication_password.setText(broker.get('communication_password', ''))
            self.api_key.setText(broker.get('api_key', ''))
            self.api_secret.setText(broker.get('api_secret', ''))
            self.server_url.setText(broker.get('server_url', ''))
            self.server_port.setText(broker.get('server_port', ''))
            self.branch_code.setText(broker.get('branch_code', ''))
            self.auto_login.setChecked(broker.get('auto_login', False))
            
            # 交易限制
            limits = self.config.get('trading_limits', {})
            self.max_order_amount.setValue(limits.get('max_order_amount', 50000))
            self.min_order_amount.setValue(limits.get('min_order_amount', 1000))
            self.max_daily_amount.setValue(limits.get('max_daily_amount', 200000))
            self.max_daily_orders.setValue(limits.get('max_daily_orders', 20))
            self.max_positions.setValue(limits.get('max_positions', 10))
            self.max_position_amount.setValue(limits.get('max_position_amount', 100000))
            self.allow_t0.setChecked(limits.get('allow_t0', False))
            self.allow_margin.setChecked(limits.get('allow_margin', False))
            
            # 风控设置
            risk = self.config.get('risk_control', {})
            self.max_position_ratio.setValue(risk.get('max_position_ratio', 0.3))
            self.max_drawdown.setValue(risk.get('max_drawdown', 0.15))
            self.max_daily_loss.setValue(risk.get('max_daily_loss', 0.05))
            self.stop_loss_ratio.setValue(risk.get('stop_loss_ratio', 0.08))
            self.take_profit_ratio.setValue(risk.get('take_profit_ratio', 0.15))
            
            # 通知设置
            notif = self.config.get('notification', {})
            self.email_enabled.setChecked(notif.get('email_enabled', False))
            self.email_address.setText(notif.get('email_address', ''))
            self.smtp_server.setText(notif.get('smtp_server', ''))
            self.smtp_port.setValue(notif.get('smtp_port', 465))
            self.smtp_user.setText(notif.get('smtp_user', ''))
            self.smtp_password.setText(notif.get('smtp_password', ''))
            self.wechat_enabled.setChecked(notif.get('wechat_enabled', False))
            self.wechat_webhook.setText(notif.get('wechat_webhook', ''))
            
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
            QMessageBox.warning(self, "错误", f"加载设置失败: {e}")
            
    def save_settings(self):
        """保存设置"""
        try:
            # 验证实盘交易设置
            if self.mode_combo.currentIndex() == 1:  # 实盘交易
                if not self.real_confirmed.isChecked():
                    QMessageBox.warning(self, "警告", "请勾选风险确认选项！")
                    return
                    
                password = self.safety_password.text()
                if not password or len(password) != 6 or not password.isdigit():
                    QMessageBox.warning(self, "警告", "请设置6位数字安全密码！")
                    return
                    
                if not self.account_id.text():
                    QMessageBox.warning(self, "警告", "请填写券商账户ID！")
                    return
                    
                if not self.password.text():
                    QMessageBox.warning(self, "警告", "请填写登录密码！")
                    return
            
            # 构建配置
            broker_types = [
                'simulation', 'eastmoney', 'huatai', 'citic', 
                'guotai_junan', 'guangfa', 'haitong', 'other'
            ]
            
            config = {
                'trading_mode': {
                    'mode': 'simulation' if self.mode_combo.currentIndex() == 0 else 'real',
                    'simulation_capital': self.simulation_capital.value(),
                    'real_trading_confirmed': self.real_confirmed.isChecked(),
                    'real_trading_password': self.safety_password.text()
                },
                'broker': {
                    'type': broker_types[self.broker_type.currentIndex()],
                    'account_id': self.account_id.text(),
                    'password': self.password.text(),
                    'trade_password': self.trade_password.text(),
                    'communication_password': self.communication_password.text(),
                    'api_key': self.api_key.text(),
                    'api_secret': self.api_secret.text(),
                    'server_url': self.server_url.text(),
                    'server_port': self.server_port.text(),
                    'branch_code': self.branch_code.text(),
                    'auto_login': self.auto_login.isChecked()
                },
                'trading_limits': {
                    'max_order_amount': self.max_order_amount.value(),
                    'min_order_amount': self.min_order_amount.value(),
                    'max_daily_amount': self.max_daily_amount.value(),
                    'max_daily_orders': self.max_daily_orders.value(),
                    'max_positions': self.max_positions.value(),
                    'max_position_amount': self.max_position_amount.value(),
                    'allow_t0': self.allow_t0.isChecked(),
                    'allow_margin': self.allow_margin.isChecked()
                },
                'risk_control': {
                    'max_position_ratio': self.max_position_ratio.value(),
                    'max_drawdown': self.max_drawdown.value(),
                    'max_daily_loss': self.max_daily_loss.value(),
                    'stop_loss_ratio': self.stop_loss_ratio.value(),
                    'take_profit_ratio': self.take_profit_ratio.value()
                },
                'notification': {
                    'email_enabled': self.email_enabled.isChecked(),
                    'email_address': self.email_address.text(),
                    'smtp_server': self.smtp_server.text(),
                    'smtp_port': self.smtp_port.value(),
                    'smtp_user': self.smtp_user.text(),
                    'smtp_password': self.smtp_password.text(),
                    'wechat_enabled': self.wechat_enabled.isChecked(),
                    'wechat_webhook': self.wechat_webhook.text()
                }
            }
            
            # 保存到文件
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            QMessageBox.information(self, "成功", "设置已保存！\n请重启程序使设置生效。")
            self.accept()
            
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
            
    def test_connection(self):
        """测试连接"""
        try:
            mode = self.mode_combo.currentIndex()
            
            if mode == 0:  # 模拟交易
                QMessageBox.information(
                    self, 
                    "测试成功", 
                    "✅ 模拟交易模式\n无需连接券商服务器"
                )
            else:  # 实盘交易
                # 这里应该调用实际的券商API测试连接
                # 目前只做基本验证
                if not self.account_id.text() or not self.password.text():
                    QMessageBox.warning(self, "错误", "请先填写账户信息！")
                    return
                
                # 模拟测试
                QMessageBox.information(
                    self,
                    "提示",
                    "⚠️ 实盘连接测试功能正在开发中\n\n"
                    "请确保:\n"
                    "• 账户信息正确\n"
                    "• 网络连接正常\n"
                    "• 券商服务可用"
                )
                
        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            QMessageBox.critical(self, "错误", f"测试连接失败: {e}")
