"""
认证对话框模块
包括启动密码输入和注册码激活对话框
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QFormLayout, QWidget)
from PyQt5.QtCore import Qt, QPoint
from qfluentwidgets import (LineEdit, PrimaryPushButton, PushButton, 
                           InfoBar, InfoBarPosition, MessageBox)
import logging

logger = logging.getLogger(__name__)


class PasswordDialog(QDialog):
    """启动密码输入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("启动验证")
        self.setModal(True)
        self.setFixedSize(400, 240)  # 增加高度以容纳自定义标题栏
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        self.init_ui()
        self._apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 自定义标题栏
        self._create_title_bar_password(layout)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("请输入启动密码")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        content_layout.addWidget(title_label)
        
        # 密码输入组
        password_group = QGroupBox("密码验证")
        password_layout = QFormLayout()
        
        self.password_edit = LineEdit()
        self.password_edit.setEchoMode(LineEdit.Password)
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.returnPressed.connect(self.accept)
        password_layout.addRow("密码：", self.password_edit)
        
        password_group.setLayout(password_layout)
        content_layout.addWidget(password_group)
        
        # 提示信息
        self.hint_label = QLabel("💡 提示：首次使用或未设置密码，请直接点击确定")
        self.hint_label.setStyleSheet("font-size: 12px;")
        content_layout.addWidget(self.hint_label)
        
        content_layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = PushButton()
        self.cancel_btn.setText("退出")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = PrimaryPushButton()
        self.ok_btn.setText("确定")
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        content_layout.addLayout(btn_layout)
        
        # 添加内容区域到主布局
        layout.addWidget(content_widget)
        
        # 焦点设置到密码输入框
        self.password_edit.setFocus()
    
    def _create_title_bar_password(self, layout):
        """创建自定义标题栏"""
        from qfluentwidgets import TransparentToolButton, FluentIcon, isDarkTheme
        
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 5, 0)
        
        # 标题文本
        self.title_label = QLabel("启动验证")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = TransparentToolButton(FluentIcon.CLOSE)
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        
        # 应用标题栏样式
        is_dark = isDarkTheme()
        if is_dark:
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b;
                    border-bottom: 1px solid #3a3a3a;
                }
            """)
            self.title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: rgba(255, 255, 255, 0.9);")
        else:
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #f5f5f5;
                    border-bottom: 1px solid #e0e0e0;
                }
            """)
            self.title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: rgba(0, 0, 0, 0.9);")
        
        layout.addWidget(title_bar)
        
        # 保存标题栏用于拖动
        self._title_bar = title_bar
        self._is_dragging = False
        self._drag_position = QPoint()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            if hasattr(self, '_title_bar') and event.pos().y() <= self._title_bar.height():
                self._is_dragging = True
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton and self._is_dragging:
            self.move(event.globalPos() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._is_dragging = False
    
    def _apply_theme(self):
        """应用主题样式"""
        from qfluentwidgets import isDarkTheme
        
        is_dark = isDarkTheme()
        
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #202020;
                }
                QGroupBox {
                    color: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                }
                QLabel {
                    color: rgba(255, 255, 255, 0.9);
                }
            """)
            self.hint_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                }
                QGroupBox {
                    color: rgba(0, 0, 0, 0.9);
                    border: 1px solid rgba(0, 0, 0, 0.15);
                }
                QLabel {
                    color: rgba(0, 0, 0, 0.9);
                }
            """)
            self.hint_label.setStyleSheet("color: #666; font-size: 12px;")
    
    def get_password(self) -> str:
        """获取输入的密码"""
        return self.password_edit.text()


class ActivationDialog(QDialog):
    """注册码激活对话框"""
    
    def __init__(self, machine_code: str, parent=None):
        super().__init__(parent)
        self.machine_code = machine_code
        self.setWindowTitle("软件激活")
        self.setModal(True)
        self.setFixedSize(500, 400)  # 增加高度以容纳自定义标题栏
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        self.init_ui()
        self._apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 自定义标题栏
        self._create_title_bar(layout)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("软件未激活，请输入注册码")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1890ff;")
        content_layout.addWidget(title_label)
        
        # 机器码显示
        machine_group = QGroupBox("机器码")
        machine_layout = QVBoxLayout()
        
        self.machine_code_edit = LineEdit()
        self.machine_code_edit.setText(self.machine_code)
        self.machine_code_edit.setReadOnly(True)
        machine_layout.addWidget(self.machine_code_edit)
        
        self.copy_hint = QLabel("💡 请将此机器码发送给供应商以获取注册码")
        self.copy_hint.setStyleSheet("font-size: 12px;")
        machine_layout.addWidget(self.copy_hint)
        
        machine_group.setLayout(machine_layout)
        content_layout.addWidget(machine_group)
        
        # 注册码输入
        activation_group = QGroupBox("注册码")
        activation_layout = QFormLayout()
        
        self.activation_edit = LineEdit()
        self.activation_edit.setPlaceholderText("请输入注册码，格式：xxxx-xxxx-xxxx-xxxx-xxxx")
        self.activation_edit.returnPressed.connect(self.accept)
        activation_layout.addRow("注册码：", self.activation_edit)
        
        activation_group.setLayout(activation_layout)
        content_layout.addWidget(activation_group)
        
        # 说明信息
        self.info_label = QLabel(
            "📌 说明：\n"
            "• 每台电脑的机器码是唯一的\n"
            "• 注册码与机器码绑定，仅在本机有效\n"
            "• 如需在其他电脑使用，请联系供应商获取新的注册码"
        )
        self.info_label.setStyleSheet(
            "padding: 10px; border-radius: 5px; font-size: 12px;"
        )
        content_layout.addWidget(self.info_label)
        
        content_layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.trial_btn = PushButton()
        self.trial_btn.setText("试用模式")
        self.trial_btn.clicked.connect(self.start_trial)
        
        self.cancel_btn = PushButton()
        self.cancel_btn.setText("退出")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = PrimaryPushButton()
        self.ok_btn.setText("激活")
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.trial_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        content_layout.addLayout(btn_layout)
        
        # 添加内容区域到主布局
        layout.addWidget(content_widget)
        
        # 焦点设置到注册码输入框
        self.activation_edit.setFocus()
    
    def get_activation_code(self) -> str:
        """获取输入的注册码"""
        return self.activation_edit.text().strip()
    
    def _create_title_bar(self, layout):
        """创建自定义标题栏"""
        from qfluentwidgets import TransparentToolButton, FluentIcon, isDarkTheme
        
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 5, 0)
        
        # 标题文本
        self.title_label = QLabel("软件激活")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # 关闭按钮（使用TransparentToolButton）
        close_btn = TransparentToolButton(FluentIcon.CLOSE)
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        
        # 应用标题栏样式
        is_dark = isDarkTheme()
        if is_dark:
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b;
                    border-bottom: 1px solid #3a3a3a;
                }
            """)
            self.title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: rgba(255, 255, 255, 0.9);")
        else:
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #f5f5f5;
                    border-bottom: 1px solid #e0e0e0;
                }
            """)
            self.title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: rgba(0, 0, 0, 0.9);")
        
        layout.addWidget(title_bar)
        
        # 保存标题栏用于拖动
        self._title_bar = title_bar
        self._is_dragging = False
        self._drag_position = QPoint()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在标题栏区域
            if hasattr(self, '_title_bar') and event.pos().y() <= self._title_bar.height():
                self._is_dragging = True
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton and self._is_dragging:
            self.move(event.globalPos() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._is_dragging = False
    
    def _apply_theme(self):
        """应用主题样式"""
        from qfluentwidgets import isDarkTheme
        from ui.theme_manager import ThemeManager
        
        is_dark = isDarkTheme()
        
        # 设置对话框背景
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #202020;
                }
                QGroupBox {
                    color: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                }
                QLabel {
                    color: rgba(255, 255, 255, 0.9);
                }
            """)
            # 提示信息样式
            self.copy_hint.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
            self.info_label.setStyleSheet(
                "color: rgba(255, 255, 255, 0.7); padding: 10px; "
                "background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); "
                "border-radius: 5px; font-size: 12px;"
            )
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                }
                QGroupBox {
                    color: rgba(0, 0, 0, 0.9);
                    border: 1px solid rgba(0, 0, 0, 0.15);
                }
                QLabel {
                    color: rgba(0, 0, 0, 0.9);
                }
            """)
            # 提示信息样式
            self.copy_hint.setStyleSheet("color: #666; font-size: 12px;")
            self.info_label.setStyleSheet(
                "color: #666; padding: 10px; background: #f5f5f5; "
                "border: 1px solid #e0e0e0; border-radius: 5px; font-size: 12px;"
            )
    
    def start_trial(self):
        """启动试用模式"""
        # 试用模式可以让用户体验部分功能
        title = '试用模式'
        content = '试用模式下，部分功能将受到限制。\n是否继续？'
        w = MessageBox(title, content, self)
        
        if w.exec():
            self.done(2)  # 返回特殊代码表示试用模式


class PasswordSetDialog(QDialog):
    """设置启动密码对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置启动密码")
        self.setModal(True)
        self.setFixedSize(400, 280)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("设置启动密码")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 密码输入组
        password_group = QGroupBox("密码设置")
        password_layout = QFormLayout()
        
        self.old_password_edit = LineEdit()
        self.old_password_edit.setEchoMode(LineEdit.Password)
        self.old_password_edit.setPlaceholderText("留空表示未设置密码")
        password_layout.addRow("原密码：", self.old_password_edit)
        
        self.new_password_edit = LineEdit()
        self.new_password_edit.setEchoMode(LineEdit.Password)
        self.new_password_edit.setPlaceholderText("留空表示不使用启动密码")
        password_layout.addRow("新密码：", self.new_password_edit)
        
        self.confirm_password_edit = LineEdit()
        self.confirm_password_edit.setEchoMode(LineEdit.Password)
        self.confirm_password_edit.setPlaceholderText("再次输入新密码")
        password_layout.addRow("确认密码：", self.confirm_password_edit)
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # 提示信息
        hint_label = QLabel(
            "💡 提示：\n"
            "• 密码长度建议6位以上\n"
            "• 如不需要启动密码，请将新密码留空\n"
            "• 请妥善保管密码，遗忘后需联系技术支持"
        )
        # 移除硬编码背景色，让它跟随主题
        hint_label.setStyleSheet("font-size: 12px; padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 5px;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = PushButton()
        self.cancel_btn.setText("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = PrimaryPushButton()
        self.ok_btn.setText("确定")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def validate_and_accept(self):
        """验证并接受"""
        new_pwd = self.new_password_edit.text()
        confirm_pwd = self.confirm_password_edit.text()
        
        # 如果设置了新密码，必须确认
        if new_pwd or confirm_pwd:
            if new_pwd != confirm_pwd:
                InfoBar.warning(
                    title='警告',
                    content='两次输入的新密码不一致',
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            if len(new_pwd) < 6:
                InfoBar.warning(
                    title='警告',
                    content='密码长度至少6位',
                    orient=Qt.Horizontal,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
        
        self.accept()
    
    def get_passwords(self) -> tuple:
        """获取密码"""
        return (
            self.old_password_edit.text(),
            self.new_password_edit.text(),
            self.confirm_password_edit.text()
        )
