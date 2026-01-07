"""
数据源适配模块
支持Tushare Pro, AKShare, Baostock等多数据源
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import pandas as pd

logger = logging.getLogger(__name__)


class DataSourceBase(ABC):
    """数据源基类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.retry = config.get('retry', 3)
    
    @abstractmethod
    def get_stock_list(self, market: str = 'A') -> pd.DataFrame:
        """
        获取股票列表
        :param market: 市场类型 A/HK/US
        :return: DataFrame包含股票代码、名称等信息
        """
        pass
    
    @abstractmethod
    def get_daily_data(self, stock_code: str, start_date: str, 
                       end_date: str) -> pd.DataFrame:
        """
        获取日线数据
        :param stock_code: 股票代码
        :param start_date: 开始日期 YYYY-MM-DD
        :param end_date: 结束日期 YYYY-MM-DD
        :return: DataFrame包含日期、开盘价、最高价、最低价、收盘价、成交量等
        """
        pass
    
    @abstractmethod
    def get_realtime_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情数据
        :param stock_codes: 股票代码列表
        :return: DataFrame包含实时价格、涨跌幅等信息
        """
        pass
    
    @abstractmethod
    def get_financial_data(self, stock_code: str, start_date: str,
                          end_date: str) -> pd.DataFrame:
        """
        获取财务数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: DataFrame包含市盈率、市净率、净利润等财务指标
        """
        pass


class TushareDataSource(DataSourceBase):
    """Tushare Pro数据源"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.token = config.get('token', '')
        if not self.token:
            raise ValueError("Tushare token不能为空，请在config.yaml中配置")
        
        try:
            import tushare as ts
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            logger.info("Tushare Pro初始化成功")
        except Exception as e:
            logger.error(f"Tushare Pro初始化失败: {e}")
            raise
    
    def get_stock_list(self, market: str = 'A') -> pd.DataFrame:
        """获取股票列表"""
        try:
            # 获取A股列表
            if market == 'A':
                df = self.pro.stock_basic(
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name,area,industry,list_date'
                )
            elif market == 'HK':
                df = self.pro.hk_basic(
                    list_status='L',
                    fields='ts_code,name,fullname,enname,list_date'
                )
            else:
                raise ValueError(f"不支持的市场类型: {market}")
            
            logger.info(f"获取{market}股票列表成功，共{len(df)}只股票")
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_daily_data(self, stock_code: str, start_date: str, 
                       end_date: str) -> pd.DataFrame:
        """获取日线数据"""
        try:
            df = self.pro.daily(
                ts_code=stock_code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                fields='ts_code,trade_date,open,high,low,close,vol,amount'
            )
            
            if df.empty:
                logger.warning(f"股票{stock_code}在{start_date}至{end_date}期间无数据")
                return pd.DataFrame()
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            
            logger.info(f"获取{stock_code}日线数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            raise
    
    def get_realtime_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取实时行情数据（使用日线最新数据模拟）"""
        try:
            # Tushare实时行情需要高级权限，这里用最新日线数据模拟
            import datetime
            today = datetime.date.today().strftime('%Y%m%d')
            
            all_data = []
            for code in stock_codes:
                try:
                    df = self.pro.daily(
                        ts_code=code,
                        start_date=today,
                        end_date=today
                    )
                    if not df.empty:
                        all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}实时数据失败: {e}")
            
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                logger.info(f"获取{len(stock_codes)}只股票实时数据成功")
                return result
            else:
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            raise
    
    def get_financial_data(self, stock_code: str, start_date: str,
                          end_date: str) -> pd.DataFrame:
        """获取财务数据"""
        try:
            # 获取日常指标（市盈率、市净率等）
            df = self.pro.daily_basic(
                ts_code=stock_code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                fields='ts_code,trade_date,pe,pb,ps,total_mv,circ_mv'
            )
            
            if df.empty:
                logger.warning(f"股票{stock_code}在{start_date}至{end_date}期间无财务数据")
                return pd.DataFrame()
            
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            
            logger.info(f"获取{stock_code}财务数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取财务数据失败: {e}")
            raise


class AKShareDataSource(DataSourceBase):
    """AKShare数据源（备用）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ak = None
        # 延迟导入akshare，避免初始化时的文件访问错误
        logger.info("AKShare数据源已创建（延迟加载）")
    
    def _ensure_akshare(self):
        """确保akshare已加载"""
        if self.ak is None:
            try:
                import akshare as ak
                self.ak = ak
                logger.info("AKShare延迟加载成功")
            except Exception as e:
                logger.error(f"AKShare加载失败: {e}")
                raise
    
    def get_stock_list(self, market: str = 'A') -> pd.DataFrame:
        """获取股票列表"""
        try:
            self._ensure_akshare()
            if market == 'A':
                logger.info("正在调用AKShare获取A股列表...")
                df = self.ak.stock_info_a_code_name()
                
                if df is None:
                    logger.error("AKShare返回None")
                    return pd.DataFrame()
                
                if df.empty:
                    logger.warning("AKShare返回空DataFrame")
                    return pd.DataFrame()
                
                logger.info(f"获取A股列表成功，共{len(df)}只股票")
                return df
            else:
                raise ValueError(f"AKShare暂不支持{market}市场")
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_daily_data(self, stock_code: str, start_date: str, 
                       end_date: str) -> pd.DataFrame:
        """获取日线数据"""
        try:
            self._ensure_akshare()
            # AKShare使用不同的股票代码格式
            symbol = stock_code.split('.')[0]
            df = self.ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                logger.warning(f"股票{stock_code}无数据")
                return pd.DataFrame()
            
            # 统一列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'vol',
                '成交额': 'amount'
            })
            
            df['ts_code'] = stock_code
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            logger.info(f"获取{stock_code}日线数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            raise
    
    def get_realtime_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取实时行情数据"""
        try:
            self._ensure_akshare()
            df = self.ak.stock_zh_a_spot_em()
            # 筛选指定股票
            df = df[df['代码'].isin([c.split('.')[0] for c in stock_codes])]
            logger.info(f"获取实时数据成功")
            return df
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            raise
    
    def get_financial_data(self, stock_code: str, start_date: str,
                          end_date: str) -> pd.DataFrame:
        """获取财务数据"""
        logger.warning("AKShare财务数据接口需要进一步实现")
        return pd.DataFrame()


class DataSourceFactory:
    """数据源工厂"""
    
    @staticmethod
    def create_data_source(source_type: str, config: Dict) -> DataSourceBase:
        """
        创建数据源实例
        :param source_type: 数据源类型 tushare/akshare/baostock
        :param config: 配置参数
        :return: 数据源实例
        """
        if source_type.lower() == 'tushare':
            return TushareDataSource(config)
        elif source_type.lower() == 'akshare':
            return AKShareDataSource(config)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")
