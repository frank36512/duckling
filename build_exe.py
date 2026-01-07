"""
PyInstaller打包脚本
将程序打包成Windows可执行文件
"""

import PyInstaller.__main__
import os
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent

# PyInstaller参数
pyinstaller_args = [
    str(project_root / 'main.py'),  # 主程序入口
    '--name=小鸭量化_v2.1',  # 程序名称（包含版本号）
    '--windowed',  # 无控制台窗口
    '--onefile',  # 打包成单个exe文件
    f'--icon={project_root / "resources" / "duck.ico"}',  # 图标（使用.ico格式）
    
    # 添加数据文件和资源
    f'--add-data={project_root / "resources"};resources',
    f'--add-data={project_root / "config"};config',
    
    # 添加akshare数据文件
    '--add-data=venv/Lib/site-packages/akshare/file_fold;akshare/file_fold',
    
    # 隐藏导入 - 核心依赖
    '--hidden-import=PyQt5',
    '--hidden-import=PyQt5.QtCore',
    '--hidden-import=PyQt5.QtGui',
    '--hidden-import=PyQt5.QtWidgets',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=akshare',
    '--hidden-import=tushare',
    '--hidden-import=baostock',
    '--hidden-import=backtrader',
    '--hidden-import=matplotlib',
    '--hidden-import=matplotlib.backends.backend_qt5agg',
    '--hidden-import=cryptography',
    '--hidden-import=yaml',
    '--hidden-import=sqlite3',
    
    # QFluentWidgets 依赖
    '--hidden-import=qfluentwidgets',
    '--hidden-import=qfluentwidgets.components',
    '--hidden-import=qfluentwidgets.common',
    '--hidden-import=qfluentwidgets.window',
    
    # v2.1 新增依赖 - 机器学习
    '--hidden-import=sklearn',
    '--hidden-import=sklearn.ensemble',
    '--hidden-import=sklearn.preprocessing',
    '--hidden-import=xgboost',
    '--hidden-import=joblib',
    '--hidden-import=scipy',
    
    # 策略模块
    '--hidden-import=strategies',
    '--hidden-import=strategies.ml_strategies',
    '--hidden-import=strategies.macd_strategy',
    '--hidden-import=strategies.bollinger_strategy',
    '--hidden-import=strategies.kdj_strategy',
    '--hidden-import=strategies.dmi_strategy',
    '--hidden-import=strategies.cci_strategy',
    '--hidden-import=strategies.atr_breakout_strategy',
    '--hidden-import=strategies.random_forest_strategy',
    '--hidden-import=strategies.xgboost_strategy',
    '--hidden-import=strategies.lstm_strategy',
    
    # 业务模块
    '--hidden-import=business',
    '--hidden-import=business.data_service',
    '--hidden-import=business.data_manager',
    '--hidden-import=business.broker_api',
    '--hidden-import=business.trading_engine',
    '--hidden-import=business.backtest_engine',
    '--hidden-import=business.realtime_monitor',
    '--hidden-import=business.auto_trading',
    
    # 核心模块
    '--hidden-import=core',
    '--hidden-import=core.data_source',
    '--hidden-import=core.strategy_base',
    '--hidden-import=core.risk_control',
    '--hidden-import=core.encryption',
    
    # UI模块
    '--hidden-import=ui',
    '--hidden-import=ui.data_panel',
    '--hidden-import=ui.theme_manager',
    '--hidden-import=ui.main_window',
    
    # 排除不需要的包（减小体积）
    '--exclude-module=pytest',
    '--exclude-module=IPython',
    '--exclude-module=jupyter',
    '--exclude-module=notebook',
    '--exclude-module=sphinx',
    '--exclude-module=tk',
    '--exclude-module=tkinter',
    
    # 输出目录
    f'--distpath={project_root / "dist"}',
    f'--workpath={project_root / "build"}',
    f'--specpath={project_root}',
    
    # 清理临时文件
    '--clean',
    
    # 不显示UPX压缩警告
    '--noupx',
]

# 移除空参数
pyinstaller_args = [arg for arg in pyinstaller_args if arg]

print("=" * 60)
print("开始打包程序...")
print("=" * 60)
print("\n参数列表：")
for arg in pyinstaller_args:
    print(f"  {arg}")

print("\n" + "=" * 60)
print("注意：打包过程可能需要5-10分钟，请耐心等待...")
print("=" * 60 + "\n")

# 执行打包
try:
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\n" + "=" * 60)
    print("✅ 打包完成！")
    print("=" * 60)
    print(f"\n可执行文件位置：")
    print(f"  {project_root / 'dist' / '股票量化交易工具_v2.1.exe'}")
    print(f"\n文件大小：")
    exe_path = project_root / 'dist' / '股票量化交易工具_v2.1.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  {size_mb:.2f} MB")
    print("\n使用说明：")
    print("  1. 将 'dist/股票量化交易工具_v2.1.exe' 复制到任意位置")
    print("  2. 双击运行即可")
    print("  3. 程序会自动创建 config、data、logs 等目录")
    print("\nv2.1 新功能：")
    print("  ✨ 3种机器学习策略（RandomForest、XGBoost、LSTM）")
    print("  ✨ 券商API接口框架")
    print("  ✨ 应用程序图标")
    print("\n" + "=" * 60)
    
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ 打包失败！")
    print("=" * 60)
    print(f"\n错误信息：{e}")
    print("\n可能的解决方案：")
    print("  1. 确保已安装 pyinstaller: pip install pyinstaller")
    print("  2. 检查所有依赖是否正确安装")
    print("  3. 尝试以管理员权限运行")
