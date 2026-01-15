"""
认证管理模块
处理启动密码和注册码验证
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        """初始化认证管理器"""
        # 获取当前文件所在目录（项目根目录）
        self.base_path = Path(__file__).resolve().parent
        self.config_dir = self.base_path / 'config'
        self.auth_file = self.config_dir / 'auth.json'
        self.license_file = self.config_dir / 'license.dat'
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载认证配置
        self.auth_config = self._load_auth_config()
        
        logger.info("认证管理器初始化完成")
    
    def _load_auth_config(self) -> dict:
        """加载认证配置"""
        if self.auth_file.exists():
            try:
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载认证配置失败: {e}")
                return {}
        return {}
    
    def _save_auth_config(self):
        """保存认证配置"""
        try:
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                json.dump(self.auth_config, f, indent=2, ensure_ascii=False)
            logger.info("认证配置已保存")
        except Exception as e:
            logger.error(f"保存认证配置失败: {e}")
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def is_password_set(self) -> bool:
        """检查是否已设置启动密码"""
        return 'password_hash' in self.auth_config
    
    def set_password(self, password: str) -> bool:
        """设置启动密码"""
        try:
            if not password:
                # 清除密码
                if 'password_hash' in self.auth_config:
                    del self.auth_config['password_hash']
            else:
                # 设置密码
                self.auth_config['password_hash'] = self._hash_password(password)
            
            self._save_auth_config()
            logger.info("启动密码已更新")
            return True
        except Exception as e:
            logger.error(f"设置密码失败: {e}")
            return False
    
    def verify_password(self, password: str) -> bool:
        """验证启动密码"""
        if not self.is_password_set():
            return True  # 未设置密码，直接通过
        
        try:
            stored_hash = self.auth_config.get('password_hash', '')
            return self._hash_password(password) == stored_hash
        except Exception as e:
            logger.error(f"验证密码失败: {e}")
            return False
    
    def is_activated(self) -> bool:
        """检查软件是否已激活"""
        if not self.license_file.exists():
            return False
        
        try:
            with open(self.license_file, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
            
            # 验证注册码
            activation_code = license_data.get('activation_code', '')
            machine_code = self.get_machine_code()
            
            # 检查是否为有效的注册码
            if not self._verify_activation_code(activation_code, machine_code):
                return False
            
            # 检查过期时间
            expire_date_str = license_data.get('expire_date')
            if expire_date_str:
                expire_date = datetime.fromisoformat(expire_date_str)
                if datetime.now() > expire_date:
                    logger.warning("软件许可证已过期")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"验证激活状态失败: {e}")
            return False
    
    def get_machine_code(self) -> str:
        """获取机器码"""
        try:
            import platform
            import uuid
            
            # 获取机器特征信息
            machine_info = f"{platform.node()}-{uuid.getnode()}"
            
            # 生成机器码（取前16位）
            machine_code = hashlib.md5(machine_info.encode()).hexdigest()[:16].upper()
            return machine_code
        except Exception as e:
            logger.error(f"获取机器码失败: {e}")
            return "UNKNOWN"
    
    @staticmethod
    def generate_activation_code(machine_code: str, days: int = 365) -> str:
        """
        生成注册码（服务端使用）
        :param machine_code: 机器码
        :param days: 有效天数
        :return: 注册码
        """
        # 密钥（实际使用时应该保密）
        secret_key = "STOCK_QUANT_TOOL_2025_SECRET_KEY"
        
        # 生成注册码
        data = f"{machine_code}-{secret_key}-{days}"
        activation_code = hashlib.sha256(data.encode()).hexdigest()[:20].upper()
        
        # 格式化注册码（xxxx-xxxx-xxxx-xxxx-xxxx）
        formatted_code = '-'.join([activation_code[i:i+4] for i in range(0, 20, 4)])
        
        return formatted_code
    
    def _verify_activation_code(self, activation_code: str, machine_code: str) -> bool:
        """
        验证注册码
        :param activation_code: 注册码
        :param machine_code: 机器码
        :return: 是否有效
        """
        try:
            # 移除分隔符
            code = activation_code.replace('-', '')
            
            # 密钥
            secret_key = "STOCK_QUANT_TOOL_2025_SECRET_KEY"
            
            # 尝试不同的天数（常见的有效期）
            for days in [30, 90, 180, 365, 730, 9999]:  # 9999表示永久
                expected_code = self.generate_activation_code(machine_code, days).replace('-', '')
                if code == expected_code:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"验证注册码失败: {e}")
            return False
    
    def activate(self, activation_code: str, days: int = 365) -> tuple[bool, str]:
        """
        激活软件
        :param activation_code: 注册码
        :param days: 有效天数
        :return: (是否成功, 消息)
        """
        try:
            machine_code = self.get_machine_code()
            
            # 验证注册码
            if not self._verify_activation_code(activation_code, machine_code):
                return False, "注册码无效，请检查后重试"
            
            # 计算过期时间
            if days == 9999:
                expire_date = datetime(2099, 12, 31)  # 永久许可
            else:
                expire_date = datetime.now() + timedelta(days=days)
            
            # 保存许可证
            license_data = {
                'activation_code': activation_code,
                'machine_code': machine_code,
                'activate_date': datetime.now().isoformat(),
                'expire_date': expire_date.isoformat(),
                'version': '2.0'
            }
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(license_data, f, indent=2, ensure_ascii=False)
            
            logger.info("软件激活成功")
            return True, f"激活成功！有效期至 {expire_date.strftime('%Y-%m-%d')}"
        except Exception as e:
            logger.error(f"激活失败: {e}")
            return False, f"激活失败: {str(e)}"
    
    def start_trial(self) -> tuple[bool, str]:
        """
        启动试用模式（自动静默启动）
        :return: (是否成功, 消息)
        """
        try:
            # 检查是否已经在试用中
            if self.is_trial_active():
                trial_info = self.get_trial_info()
                remaining_days = trial_info.get('remaining_days', 0)
                return True, f"试用模式已启动，剩余 {remaining_days} 天"
            
            # 检查是否已经试用过期（防止重新试用）
            trial_data = self.auth_config.get('trial')
            if trial_data:
                # 已经有试用记录，检查是否过期
                try:
                    expire_date = datetime.fromisoformat(trial_data.get('expire_date'))
                    if datetime.now() > expire_date:
                        return False, "试用期已结束，请激活软件"
                except:
                    pass
            
            # 首次试用：记录试用开始时间和校验信息
            now = datetime.now()
            trial_data = {
                'start_date': now.isoformat(),
                'expire_date': (now + timedelta(days=180)).isoformat(),
                'trial_days': 180,
                'first_run': now.isoformat(),  # 首次运行时间（用于检测时间篡改）
                'checksum': self._generate_trial_checksum(now)  # 校验和（防篡改）
            }
            
            self.auth_config['trial'] = trial_data
            self._save_auth_config()
            
            logger.info("试用模式已启动，有效期180天")
            return True, "试用模式已启动，有效期180天"
        except Exception as e:
            logger.error(f"启动试用模式失败: {e}")
            return False, f"启动试用模式失败: {str(e)}"
    
    def _generate_trial_checksum(self, start_time: datetime) -> str:
        """生成试用数据的校验和（防篡改）"""
        secret_key = "STOCK_QUANT_TRIAL_CHECKSUM_2025"
        data = f"{start_time.isoformat()}-{self.get_machine_code()}-{secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _verify_trial_checksum(self, trial_data: dict) -> bool:
        """验证试用数据完整性"""
        try:
            stored_checksum = trial_data.get('checksum', '')
            start_date = datetime.fromisoformat(trial_data.get('first_run'))
            expected_checksum = self._generate_trial_checksum(start_date)
            return stored_checksum == expected_checksum
        except:
            return False
    
    def is_trial_active(self) -> bool:
        """检查试用是否有效（包含防篡改检测）"""
        trial_data = self.auth_config.get('trial')
        if not trial_data:
            return False
        
        try:
            # 验证数据完整性
            if not self._verify_trial_checksum(trial_data):
                logger.warning("试用数据校验失败，可能被篡改")
                return False
            
            # 检查是否修改了系统时间（时间回退检测）
            first_run = datetime.fromisoformat(trial_data.get('first_run'))
            now = datetime.now()
            
            # 如果当前时间早于首次运行时间，说明系统时间被回退
            if now < first_run:
                logger.warning("检测到系统时间被修改（时间回退）")
                return False
            
            # 检查过期时间
            expire_date = datetime.fromisoformat(trial_data.get('expire_date'))
            is_valid = now <= expire_date
            
            # 更新最后检查时间（用于检测时间跳跃）
            if 'last_check' in trial_data:
                last_check = datetime.fromisoformat(trial_data['last_check'])
                # 如果当前时间早于上次检查时间，说明时间被回退
                if now < last_check:
                    logger.warning("检测到系统时间被修改（时间回退）")
                    return False
            
            # 更新最后检查时间
            trial_data['last_check'] = now.isoformat()
            self._save_auth_config()
            
            return is_valid
        except Exception as e:
            logger.error(f"检查试用状态失败: {e}")
            return False
    
    def get_trial_info(self) -> dict:
        """获取试用信息"""
        trial_data = self.auth_config.get('trial')
        if not trial_data:
            return {
                'active': False,
                'message': '未启动试用'
            }
        
        try:
            start_date = datetime.fromisoformat(trial_data.get('start_date'))
            expire_date = datetime.fromisoformat(trial_data.get('expire_date'))
            now = datetime.now()
            
            if now > expire_date:
                return {
                    'active': False,
                    'message': '试用期已过期',
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'expire_date': expire_date.strftime('%Y-%m-%d'),
                    'remaining_days': 0
                }
            
            remaining = expire_date - now
            remaining_days = remaining.days
            
            return {
                'active': True,
                'message': f'试用中，剩余 {remaining_days} 天',
                'start_date': start_date.strftime('%Y-%m-%d'),
                'expire_date': expire_date.strftime('%Y-%m-%d'),
                'remaining_days': remaining_days
            }
        except Exception as e:
            logger.error(f"获取试用信息失败: {e}")
            return {
                'active': False,
                'message': f'获取试用信息失败: {str(e)}'
            }
    
    def get_license_info(self) -> dict:
        """获取许可证信息"""
        if not self.license_file.exists():
            return {
                'activated': False,
                'machine_code': self.get_machine_code()
            }
        
        try:
            with open(self.license_file, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
            
            license_data['activated'] = self.is_activated()
            license_data['machine_code'] = self.get_machine_code()
            
            return license_data
        except Exception as e:
            logger.error(f"读取许可证信息失败: {e}")
            return {
                'activated': False,
                'machine_code': self.get_machine_code(),
                'error': str(e)
            }
    
    def deactivate(self) -> bool:
        """注销激活"""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            logger.info("软件已注销")
            return True
        except Exception as e:
            logger.error(f"注销失败: {e}")
            return False


# 生成注册码的辅助函数（供管理员使用）
def generate_license_for_machine(machine_code: str, days: int = 365):
    """
    为指定机器生成注册码（管理员工具）
    :param machine_code: 机器码
    :param days: 有效天数
    """
    auth_manager = AuthManager()
    activation_code = auth_manager.generate_activation_code(machine_code, days)
    
    print("=" * 60)
    print("股票量化交易工具 - 注册码生成")
    print("=" * 60)
    print(f"机器码: {machine_code}")
    print(f"有效期: {days} 天")
    print(f"注册码: {activation_code}")
    print("=" * 60)
    
    return activation_code


if __name__ == '__main__':
    # 测试代码
    auth = AuthManager()
    machine_code = auth.get_machine_code()
    print(f"当前机器码: {machine_code}")
    
    # 生成测试注册码
    activation_code = generate_license_for_machine(machine_code, 365)
