"""
股票量化交易工具 - 主程序入口
"""

import sys
import logging
from pathlib import Path
import io

# 修复PyInstaller打包后stdout/stderr为None的问题
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils import ConfigManager, setup_logging

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    try:
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.get_all()
        
        # 初始化日志系统
        setup_logging(config)
        
        logger.info("=" * 60)
        logger.info("小鸭量化(Duckling)启动")
        logger.info("=" * 60)
        
        # 检查并创建必要的目录
        import os
        from pathlib import Path
        if getattr(sys, 'frozen', False):
            # 打包后，确保data目录存在
            base_path = Path(sys.executable).parent
            data_dir = base_path / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"数据目录已创建/确认: {data_dir}")
        
        # 检查PyQt5是否已安装
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            from PyQt5.QtCore import Qt
            import os
        except ImportError:
            print("错误: 未安装PyQt5，请先运行以下命令安装依赖:")
            print("pip install -r requirements.txt")
            return
        
        # 禁用DPI缩放（必须在创建QApplication之前设置）
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCALE_FACTOR"] = "1"
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)
        
        # 创建应用程序
        app = QApplication(sys.argv)
        app.setApplicationName("小鸭量化(Duckling)")
        
        # 设置应用程序图标（用于任务栏）
        from PyQt5.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'duck.ico')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"应用程序图标已设置: {icon_path}")
            
            # Windows专用：设置任务栏图标
            try:
                import ctypes
                myappid = 'quanttool.stocktrading.v2.1'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                logger.info("Windows任务栏图标已设置")
            except Exception as e:
                logger.warning(f"设置Windows任务栏图标失败: {e}")
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
        
        # ========== 启动密码验证 ==========
        from utils_auth import AuthManager
        from ui.auth_dialogs import PasswordDialog
        
        auth_manager = AuthManager()
        
        # 如果设置了启动密码，需要验证
        if auth_manager.is_password_set():
            logger.info("检测到已设置启动密码，请求用户输入")
            password_dialog = PasswordDialog()
            if password_dialog.exec_() != QMessageBox.Accepted:
                logger.info("用户取消密码验证，退出程序")
                return 0
            
            password = password_dialog.get_password()
            if not auth_manager.verify_password(password):
                QMessageBox.critical(None, "验证失败", "密码错误，程序将退出")
                logger.warning("启动密码验证失败")
                return 1
            
            logger.info("启动密码验证成功")
        
        # ========== 软件激活验证 ==========
        # 新逻辑：优先检查是否已激活，未激活则自动进入试用模式，试用期结束后才要求激活
        if not auth_manager.is_activated():
            # 检查试用状态
            if auth_manager.is_trial_active():
                # 试用期内，静默运行，在主窗口显示试用信息
                trial_info = auth_manager.get_trial_info()
                logger.info(f"试用模式运行中，剩余 {trial_info['remaining_days']} 天")
            else:
                # 检查是否首次运行（从未试用过）
                trial_data = auth_manager.auth_config.get('trial')
                if not trial_data:
                    # 首次运行，自动启动试用模式
                    success, message = auth_manager.start_trial()
                    if success:
                        trial_info = auth_manager.get_trial_info()
                        logger.info(f"首次运行，自动启动试用模式，有效期180天")
                        # 静默启动，在主窗口的状态栏显示试用信息
                    else:
                        QMessageBox.critical(None, "启动失败", f"无法启动试用模式: {message}")
                        logger.error(f"启动试用模式失败: {message}")
                        return 1
                else:
                    # 试用期已结束，要求激活
                    trial_info = auth_manager.get_trial_info()
                    logger.warning("试用期已结束，要求用户激活")
                    
                    from ui.auth_dialogs import ActivationDialog
                    activation_dialog = ActivationDialog(auth_manager.get_machine_code())
                    
                    # 显示试用期已结束的提示
                    QMessageBox.warning(
                        None,
                        "试用期已结束",
                        f"您的180天试用期已于 {trial_info.get('expire_date', '未知')} 结束\n\n"
                        "请输入注册码以继续使用软件\n"
                        "如需购买，请联系供应商"
                    )
                    
                    result = activation_dialog.exec_()
                    
                    if result == 1:  # 激活
                        activation_code = activation_dialog.get_activation_code()
                        if not activation_code:
                            QMessageBox.warning(None, "警告", "未输入注册码，程序将退出")
                            logger.warning("用户未输入注册码")
                            return 0
                        
                        success, message = auth_manager.activate(activation_code)
                        if not success:
                            QMessageBox.critical(None, "激活失败", message)
                            logger.error(f"软件激活失败: {message}")
                            return 1
                        
                        QMessageBox.information(None, "激活成功", message)
                        logger.info("软件激活成功")
                    else:
                        # 用户取消激活或选择试用（但试用已结束）
                        logger.info("用户取消激活，程序退出")
                        return 0
        else:
            logger.info("软件已激活")
        
        # 创建并显示主窗口
        from ui.main_window import MainWindow
        main_window = MainWindow(config)
        main_window.show()
        
        logger.info("主窗口已显示")
        
        # 启动事件循环
        exit_code = app.exec_()
        
        logger.info("应用程序正常退出")
        return exit_code
        
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
