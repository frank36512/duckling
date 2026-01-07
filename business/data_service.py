"""
数据服务层 - 全局数据访问中心
负责统一管理数据访问、缓存、更新通知等
使用单例模式确保全局只有一个实例
"""

import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

from business.data_manager import DataManager
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class DataService(QObject):
    """
    数据服务类 - 单例模式
    提供统一的数据访问接口，管理数据缓存和更新通知
    """
    
    # 类级别的单例实例
    _instance = None
    _lock = threading.Lock()
    
    # 信号定义
    stock_list_updated = pyqtSignal(pd.DataFrame)  # 股票列表更新信号
    stock_data_updated = pyqtSignal(str, pd.DataFrame)  # 单个股票数据更新信号（股票代码，数据）
    download_progress = pyqtSignal(str, int, int)  # 下载进度信号（消息，当前，总数）
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化数据服务（仅初始化一次）"""
        if self._initialized:
            return
            
        super().__init__()
        self._initialized = True
        
        # 数据管理器
        self._data_manager: Optional[DataManager] = None
        self._config: Optional[Dict[str, Any]] = None
        
        # 缓存配置
        self._cache_enabled = True
        self._cache_expire_minutes = 30  # 缓存过期时间（分钟）
        
        # 数据缓存
        self._stock_list_cache: Optional[pd.DataFrame] = None
        self._stock_list_cache_time: Optional[datetime] = None
        
        self._stock_data_cache: Dict[str, Dict[str, Any]] = {}
        # 缓存结构: {stock_code: {'data': DataFrame, 'time': datetime, 'start': str, 'end': str}}
        
        logger.info("数据服务层初始化完成（单例模式）")
    
    @classmethod
    def get_instance(cls) -> 'DataService':
        """获取单例实例"""
        return cls()
    
    def initialize(self, config: Dict[str, Any]):
        """
        初始化数据服务（配置数据管理器）
        :param config: 配置字典
        """
        if self._data_manager is not None:
            logger.warning("数据服务已初始化，跳过重复初始化")
            return
        
        try:
            self._config = config
            self._data_manager = DataManager(config)
            
            # 从配置加载缓存设置
            cache_config = config.get('cache', {})
            self._cache_enabled = cache_config.get('enabled', True)
            self._cache_expire_minutes = cache_config.get('expire_minutes', 30)
            
            logger.info(f"数据服务初始化成功 - 缓存: {self._cache_enabled}, 过期时间: {self._cache_expire_minutes}分钟")
        except Exception as e:
            logger.error(f"数据服务初始化失败: {e}", exc_info=True)
            raise
    
    def _check_initialized(self):
        """检查是否已初始化"""
        if self._data_manager is None:
            raise RuntimeError("数据服务未初始化，请先调用initialize()方法")
    
    # ==================== 缓存管理 ====================
    
    def _is_cache_expired(self, cache_time: Optional[datetime]) -> bool:
        """检查缓存是否过期"""
        if not self._cache_enabled or cache_time is None:
            return True
        
        expire_time = timedelta(minutes=self._cache_expire_minutes)
        return datetime.now() - cache_time > expire_time
    
    def clear_cache(self, stock_code: Optional[str] = None):
        """
        清除缓存
        :param stock_code: 股票代码，为None时清除所有缓存
        """
        if stock_code is None:
            # 清除所有缓存
            self._stock_list_cache = None
            self._stock_list_cache_time = None
            self._stock_data_cache.clear()
            logger.info("已清除所有数据缓存")
        else:
            # 清除指定股票缓存
            if stock_code in self._stock_data_cache:
                del self._stock_data_cache[stock_code]
                logger.info(f"已清除股票 {stock_code} 的缓存")
    
    # ==================== 股票列表 ====================
    
    def get_stock_list(self, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        :param use_cache: 是否使用缓存
        :return: 股票列表DataFrame
        """
        self._check_initialized()
        
        # 检查缓存
        if use_cache and self._cache_enabled:
            if (self._stock_list_cache is not None and 
                not self._is_cache_expired(self._stock_list_cache_time)):
                logger.debug("使用股票列表缓存")
                return self._stock_list_cache.copy()
        
        # 从数据库获取
        try:
            stock_list = self._data_manager.get_stock_list()
            
            if stock_list is not None and not stock_list.empty:
                # 更新缓存
                self._stock_list_cache = stock_list.copy()
                self._stock_list_cache_time = datetime.now()
                logger.info(f"获取股票列表成功，共 {len(stock_list)} 只股票")
            
            return stock_list
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}", exc_info=True)
            return None
    
    def update_stock_list(self, market: str = 'A') -> Optional[pd.DataFrame]:
        """
        更新股票列表（从数据源下载）
        :param market: 市场类型
        :return: 更新后的股票列表
        """
        self._check_initialized()
        
        try:
            logger.info(f"开始更新{market}股票列表...")
            stock_list = self._data_manager.update_stock_list(market)
            
            if stock_list is not None and not stock_list.empty:
                # 更新缓存
                self._stock_list_cache = stock_list.copy()
                self._stock_list_cache_time = datetime.now()
                
                # 发送更新信号
                self.stock_list_updated.emit(stock_list)
                
                logger.info(f"股票列表更新完成，共 {len(stock_list)} 只股票")
            
            return stock_list
        except Exception as e:
            logger.error(f"更新股票列表失败: {e}", exc_info=True)
            return None
    
    def search_stock(self, keyword: str) -> Optional[pd.DataFrame]:
        """
        搜索股票（按代码或名称）
        :param keyword: 关键词
        :return: 匹配的股票列表
        """
        stock_list = self.get_stock_list()
        
        if stock_list is None or stock_list.empty:
            return None
        
        # 搜索代码或名称包含关键词的股票（兼容不同的列名）
        code_col = 'code' if 'code' in stock_list.columns else 'symbol'
        name_col = 'name' if 'name' in stock_list.columns else 'name'
        
        mask = (stock_list[code_col].astype(str).str.contains(keyword, case=False, na=False) | 
                stock_list[name_col].astype(str).str.contains(keyword, case=False, na=False))
        
        result = stock_list[mask]
        logger.info(f"搜索关键词'{keyword}'，找到 {len(result)} 只股票")
        return result
    
    # ==================== 股票行情数据 ====================
    
    def get_stock_data(self, stock_code: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        获取股票行情数据
        :param stock_code: 股票代码
        :param start_date: 开始日期 YYYY-MM-DD
        :param end_date: 结束日期 YYYY-MM-DD
        :param use_cache: 是否使用缓存
        :return: 行情数据DataFrame
        """
        self._check_initialized()
        
        # 检查缓存
        if use_cache and self._cache_enabled and stock_code in self._stock_data_cache:
            cache = self._stock_data_cache[stock_code]
            
            # 检查日期范围和过期时间
            if (not self._is_cache_expired(cache['time']) and
                (start_date is None or cache['start'] <= start_date) and
                (end_date is None or cache['end'] >= end_date)):
                
                logger.debug(f"使用股票 {stock_code} 的缓存数据")
                data = cache['data'].copy()
                
                # 筛选日期范围
                if start_date:
                    data = data[data['trade_date'] >= start_date]
                if end_date:
                    data = data[data['trade_date'] <= end_date]
                
                return data
        
        # 从数据库获取
        try:
            data = self._data_manager.get_stock_data(stock_code, start_date, end_date)
            
            if data is not None and not data.empty:
                # 更新缓存（保存完整数据范围）
                self._stock_data_cache[stock_code] = {
                    'data': data.copy(),
                    'time': datetime.now(),
                    'start': start_date or data['trade_date'].min().strftime('%Y-%m-%d'),
                    'end': end_date or data['trade_date'].max().strftime('%Y-%m-%d')
                }
                logger.info(f"获取股票 {stock_code} 数据成功，共 {len(data)} 条记录")
            
            return data
        except Exception as e:
            logger.error(f"获取股票数据失败: {e}", exc_info=True)
            return None
    
    def download_stock_data(self, stock_code: str, start_date: str, 
                           end_date: str) -> bool:
        """
        下载股票数据（从数据源）
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 是否成功
        """
        self._check_initialized()
        
        try:
            logger.info(f"开始下载股票 {stock_code} 数据...")
            success = self._data_manager.download_stock_data(stock_code, start_date, end_date)
            
            if success:
                # 清除该股票的缓存
                self.clear_cache(stock_code)
                
                # 重新获取并缓存
                data = self.get_stock_data(stock_code, start_date, end_date, use_cache=False)
                
                if data is not None:
                    # 发送更新信号
                    self.stock_data_updated.emit(stock_code, data)
                
                logger.info(f"股票 {stock_code} 数据下载完成")
            
            return success
        except Exception as e:
            logger.error(f"下载股票数据失败: {e}", exc_info=True)
            return False
    
    def get_all_stocks_data(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        获取所有股票的行情数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 所有股票数据DataFrame
        """
        self._check_initialized()
        
        try:
            data = self._data_manager.get_all_stocks_data(start_date, end_date)
            logger.info(f"获取所有股票数据，共 {len(data)} 条记录")
            return data
        except Exception as e:
            logger.error(f"获取所有股票数据失败: {e}", exc_info=True)
            return None
    
    def batch_download(self, stock_codes: List[str], start_date: str,
                      end_date: str, progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """
        批量下载股票数据
        :param stock_codes: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param progress_callback: 进度回调函数
        :return: 下载结果字典 {股票代码: 是否成功}
        """
        self._check_initialized()
        
        results = {}
        total = len(stock_codes)
        
        for i, code in enumerate(stock_codes, 1):
            logger.info(f"批量下载进度: {i}/{total} - {code}")
            
            # 发送进度信号
            self.download_progress.emit(f"正在下载 {code}", i, total)
            
            if progress_callback:
                progress_callback(code, i, total)
            
            success = self.download_stock_data(code, start_date, end_date)
            results[code] = success
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"批量下载完成，成功 {success_count}/{total}")
        
        return results
    
    # ==================== 数据检查 ====================
    
    def check_data_exists(self, stock_code: str) -> bool:
        """
        检查股票数据是否存在
        :param stock_code: 股票代码
        :return: 是否存在
        """
        self._check_initialized()
        return self._data_manager.check_data_exists(stock_code)
    
    def get_data_date_range(self, stock_code: str) -> Optional[Dict[str, str]]:
        """
        获取股票数据的日期范围
        :param stock_code: 股票代码
        :return: {'start': '开始日期', 'end': '结束日期'} 或 None
        """
        data = self.get_stock_data(stock_code)
        
        if data is None or data.empty:
            return None
        
        return {
            'start': data['trade_date'].min().strftime('%Y-%m-%d'),
            'end': data['trade_date'].max().strftime('%Y-%m-%d')
        }
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据统计信息
        :return: 统计信息字典
        """
        self._check_initialized()
        
        stock_list = self.get_stock_list()
        stock_count = len(stock_list) if stock_list is not None else 0
        
        # 统计有数据的股票数量
        # 注：这个操作可能较慢，可以考虑缓存
        
        stats = {
            'stock_count': stock_count,
            'cache_enabled': self._cache_enabled,
            'cache_expire_minutes': self._cache_expire_minutes,
            'cached_stock_data_count': len(self._stock_data_cache),
            'stock_list_cached': self._stock_list_cache is not None,
        }
        
        return stats
    
    # ==================== 配置管理 ====================
    
    def update_cache_config(self, enabled: bool, expire_minutes: int):
        """
        更新缓存配置
        :param enabled: 是否启用缓存
        :param expire_minutes: 缓存过期时间（分钟）
        """
        self._cache_enabled = enabled
        self._cache_expire_minutes = expire_minutes
        
        if not enabled:
            self.clear_cache()
        
        logger.info(f"缓存配置已更新 - 启用: {enabled}, 过期时间: {expire_minutes}分钟")
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        """获取配置"""
        return self._config
    
    # ==================== 资源清理 ====================
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理数据服务资源...")
        self.clear_cache()
        # 注意：不要重置单例实例，因为可能被重新使用
        logger.info("数据服务资源清理完成")


# 提供便捷的全局访问函数
def get_data_service() -> DataService:
    """获取数据服务单例"""
    return DataService.get_instance()
