"""
配置管理工具模块
"""

import logging
import yaml
import sys
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        :param config_path: 配置文件路径
        """
        if config_path is None:
            # 处理打包后的路径
            if getattr(sys, 'frozen', False):
                # 打包后，配置文件在exe同目录下的config文件夹
                base_path = Path(sys.executable).parent
            else:
                # 开发环境，配置文件在项目根目录
                base_path = Path(__file__).parent
            config_path = base_path / 'config' / 'config.yaml'
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        :return: 配置字典
        """
        try:
            if not self.config_path.exists():
                logger.error(f"配置文件不存在: {self.config_path}")
                # 返回默认配置
                return self._get_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                return self._get_default_config()
            
            # 自动修正数据库路径为当前运行目录下的data文件夹
            # 这样可以确保打包后的程序使用exe同目录的data文件夹
            if getattr(sys, 'frozen', False):
                base_path = Path(sys.executable).parent
                if 'database' in config:
                    config['database']['path'] = str(base_path / 'data' / 'stock_data.db')
                    config['database']['backup_path'] = str(base_path / 'data' / 'backup')
                    logger.info(f"已自动修正数据库路径为: {config['database']['path']}")
                if 'logging' in config:
                    config['logging']['path'] = str(base_path / 'logs')
                if 'strategy' in config and 'custom_path' in config['strategy']:
                    config['strategy']['custom_path'] = str(base_path / 'strategies')
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            return config
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 返回默认配置
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        :return: 默认配置字典
        """
        # 确定基础路径
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
        
        return {
            'data_source': {
                'primary': 'akshare',
                'backup': 'tushare',
                'tushare': {
                    'token': '',
                    'timeout': 30,
                    'retry': 3
                },
                'akshare': {
                    'use_proxy': False,
                    'timeout': 30
                },
                'update': {
                    'auto_update': False,
                    'update_time': '15:30',
                    'incremental': True
                }
            },
            'database': {
                'path': str(base_path / 'data' / 'stock_data.db'),
                'backup_path': str(base_path / 'data' / 'backup'),
                'backup_retention_days': 30
            },
            'backtest': {
                'initial_cash': 100000.0,
                'commission': 0.0003,
                'stamp_duty': 0.001,
                'slippage': 0.001,
                'position_limit': 0.3
            },
            'trading': {
                'allow_short': False,
                'order_type': 'limit',
                'stop_loss': 0.05,
                'take_profit': 0.15
            },
            'risk_control': {
                'max_daily_trades': 10,
                'max_loss_threshold': 0.1,
                'price_deviation_limit': 0.03
            },
            'alert': {
                'enable': True,
                'popup': True,
                'sound': True,
                'email': {'enable': False},
                'wechat': {'enable': False}
            },
            'logging': {
                'level': 'INFO',
                'path': str(base_path / 'logs'),
                'retention_days': 90,
                'max_file_size': '10MB'
            },
            'ui': {
                'theme': 'light',
                'language': 'zh_CN',
                'window_size': [1440, 810]
            },
            'view': {
                'theme': 'light',
                'theme_color': '#1890ff',
                'font_size': 12,
                'font_weight': 'normal',
                'row_height': 35,
                'zebra_stripes': True,
                'table_border': True,
                'animation': True,
                'startup_size': 'default'  # 默认固定尺寸 1366x768
            },
            'strategy': {
                'custom_path': str(base_path / 'strategies'),
                'builtin': [
                    'MA_CrossOver',
                    'MACD_Divergence',
                    'RSI_OverboughtOversold',
                    'BollingerBands_Breakout'
                ]
            },
            'security': {
                'encryption': {
                    'enabled': True,
                    'algorithm': 'AES'
                },
                'backup': {
                    'auto_backup': True,
                    'backup_frequency': 'daily'
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        :param key: 配置键（支持点号分隔的多级键，如 'data_source.primary'）
        :param default: 默认值
        :return: 配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置项
        :param key: 配置键
        :param value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self):
        """保存配置到文件"""
        try:
            # 确保配置文件目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, 
                         default_flow_style=False)
            
            logger.info("配置文件保存成功")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        :return: 配置字典
        """
        return self.config.copy()


def setup_logging(config: Dict[str, Any]):
    """
    设置日志系统
    :param config: 日志配置
    """
    import sys
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_path_str = log_config.get('path', './logs')
    
    # 处理日志路径（支持打包后的相对路径）
    if not Path(log_path_str).is_absolute():
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            base_path = Path(sys.executable).parent
        else:
            # 开发环境路径
            base_path = Path(__file__).parent
        log_path = base_path / log_path_str.lstrip('./')
    else:
        log_path = Path(log_path_str)
    
    # 确保日志目录存在
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 日志文件名（按日期）
    from datetime import datetime
    log_file = log_path / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 文件处理器
            logging.FileHandler(log_file, encoding='utf-8'),
            # 控制台处理器
            logging.StreamHandler()
        ]
    )
    
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {log_level}")
    logger.info(f"日志文件: {log_file}")
