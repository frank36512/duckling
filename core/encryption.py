"""
加密服务模块
用于敏感信息的加密存储
"""

import logging
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import os

logger = logging.getLogger(__name__)


class EncryptionService:
    """加密服务类"""
    
    def __init__(self, password: str = None):
        """
        初始化加密服务
        :param password: 加密密码，如果不提供则使用默认密码
        """
        if password is None:
            # 默认密码（生产环境应该让用户设置）
            password = "StockQuantTool@2024"
        
        self.key = self._generate_key(password)
        self.cipher = Fernet(self.key)
        logger.info("加密服务初始化成功")
    
    def _generate_key(self, password: str) -> bytes:
        """
        从密码生成加密密钥
        :param password: 密码
        :return: 加密密钥
        """
        # 使用固定的盐值（生产环境应该存储在安全位置）
        salt = b'stock_quant_tool_salt_2024'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        :param plaintext: 明文
        :return: 加密后的字符串（Base64编码）
        """
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        解密字符串
        :param encrypted_text: 加密的字符串（Base64编码）
        :return: 解密后的明文
        """
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
    
    def encrypt_dict(self, data: dict) -> dict:
        """
        加密字典中的敏感字段
        :param data: 包含敏感信息的字典
        :return: 加密后的字典
        """
        encrypted_data = data.copy()
        sensitive_keys = ['token', 'password', 'api_key', 'secret']
        
        for key in sensitive_keys:
            if key in encrypted_data and encrypted_data[key]:
                try:
                    encrypted_data[key] = self.encrypt(encrypted_data[key])
                except Exception as e:
                    logger.warning(f"加密字段 {key} 失败: {e}")
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """
        解密字典中的敏感字段
        :param data: 包含加密信息的字典
        :return: 解密后的字典
        """
        decrypted_data = data.copy()
        sensitive_keys = ['token', 'password', 'api_key', 'secret']
        
        for key in sensitive_keys:
            if key in decrypted_data and decrypted_data[key]:
                try:
                    decrypted_data[key] = self.decrypt(decrypted_data[key])
                except Exception as e:
                    logger.warning(f"解密字段 {key} 失败: {e}")
        
        return decrypted_data


# 全局加密服务实例
_encryption_service = None


def get_encryption_service(password: str = None) -> EncryptionService:
    """
    获取全局加密服务实例（单例模式）
    :param password: 加密密码
    :return: 加密服务实例
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService(password)
    return _encryption_service
