"""
量化选股模块
实现多因子选股、条件筛选、技术指标筛选等功能
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import tushare as ts
import akshare as ak

logger = logging.getLogger(__name__)


class StockSelector:
    """量化选股器"""
    
    def __init__(self):
        """初始化选股器"""
        self.ts_token = None
        self.stock_pool = None
        logger.info("量化选股器初始化完成")
    
    def set_tushare_token(self, token: str):
        """设置Tushare Token"""
        try:
            self.ts_token = token
            ts.set_token(token)
            logger.info("Tushare Token设置成功")
        except Exception as e:
            logger.error(f"设置Tushare Token失败: {e}")
    
    def get_stock_basic_info(self, use_cache: bool = True) -> pd.DataFrame:
        """
        获取股票基础信息
        :param use_cache: 是否使用缓存
        :return: 股票基础信息DataFrame
        """
        try:
            logger.info("开始获取股票基础信息...")
            
            # 使用akshare获取股票列表
            stock_info = ak.stock_zh_a_spot_em()
            
            # 重命名列以便统一处理
            if stock_info is not None and not stock_info.empty:
                # 提取需要的列
                df = pd.DataFrame()
                df['code'] = stock_info['代码']
                df['name'] = stock_info['名称']
                df['industry'] = stock_info.get('行业', '')
                df['market_cap'] = stock_info.get('总市值', 0) / 1e8  # 转换为亿
                df['pe'] = stock_info.get('市盈率-动态', 0)
                df['pb'] = stock_info.get('市净率', 0)
                df['price'] = stock_info.get('最新价', 0)
                df['change_pct'] = stock_info.get('涨跌幅', 0)
                df['volume'] = stock_info.get('成交量', 0)
                df['amount'] = stock_info.get('成交额', 0)
                
                # 过滤掉无效数据
                df = df[df['code'].str.match(r'^\d{6}$')]
                df = df.reset_index(drop=True)
                
                self.stock_pool = df
                logger.info(f"成功获取 {len(df)} 只股票的基础信息")
                return df
            else:
                logger.warning("未获取到股票数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取股票基础信息失败: {e}", exc_info=True)
            return pd.DataFrame()
    
    def filter_by_industry(self, df: pd.DataFrame, industry: str) -> pd.DataFrame:
        """
        按行业筛选
        :param df: 股票数据DataFrame
        :param industry: 行业名称
        :return: 筛选后的DataFrame
        """
        if industry == "全部" or not industry:
            return df
        
        try:
            filtered = df[df['industry'].str.contains(industry, na=False)]
            logger.info(f"行业筛选[{industry}]: {len(filtered)} 只股票")
            return filtered
        except Exception as e:
            logger.error(f"行业筛选失败: {e}")
            return df
    
    def filter_by_market_cap(self, df: pd.DataFrame, min_cap: float = None, 
                            max_cap: float = None) -> pd.DataFrame:
        """
        按市值区间筛选
        :param df: 股票数据DataFrame
        :param min_cap: 最小市值(亿)
        :param max_cap: 最大市值(亿)
        :return: 筛选后的DataFrame
        """
        try:
            result = df.copy()
            
            if min_cap is not None and min_cap > 0:
                result = result[result['market_cap'] >= min_cap]
            
            if max_cap is not None and max_cap > 0:
                result = result[result['market_cap'] <= max_cap]
            
            logger.info(f"市值筛选[{min_cap}-{max_cap}亿]: {len(result)} 只股票")
            return result
        except Exception as e:
            logger.error(f"市值筛选失败: {e}")
            return df
    
    def filter_by_pe(self, df: pd.DataFrame, min_pe: float = None, 
                     max_pe: float = None) -> pd.DataFrame:
        """
        按市盈率筛选
        :param df: 股票数据DataFrame
        :param min_pe: 最小PE
        :param max_pe: 最大PE
        :return: 筛选后的DataFrame
        """
        try:
            result = df.copy()
            
            # 过滤掉PE为0或负值的股票
            result = result[result['pe'] > 0]
            
            if min_pe is not None and min_pe > 0:
                result = result[result['pe'] >= min_pe]
            
            if max_pe is not None and max_pe > 0:
                result = result[result['pe'] <= max_pe]
            
            logger.info(f"PE筛选[{min_pe}-{max_pe}]: {len(result)} 只股票")
            return result
        except Exception as e:
            logger.error(f"PE筛选失败: {e}")
            return df
    
    def filter_by_pb(self, df: pd.DataFrame, min_pb: float = None, 
                     max_pb: float = None) -> pd.DataFrame:
        """
        按市净率筛选
        :param df: 股票数据DataFrame
        :param min_pb: 最小PB
        :param max_pb: 最大PB
        :return: 筛选后的DataFrame
        """
        try:
            result = df.copy()
            
            # 过滤掉PB为0或负值的股票
            result = result[result['pb'] > 0]
            
            if min_pb is not None and min_pb > 0:
                result = result[result['pb'] >= min_pb]
            
            if max_pb is not None and max_pb > 0:
                result = result[result['pb'] <= max_pb]
            
            logger.info(f"PB筛选[{min_pb}-{max_pb}]: {len(result)} 只股票")
            return result
        except Exception as e:
            logger.error(f"PB筛选失败: {e}")
            return df
    
    def calculate_technical_indicators(self, code: str, days: int = 60) -> Dict:
        """
        计算技术指标
        :param code: 股票代码
        :param days: 计算天数
        :return: 技术指标字典
        """
        try:
            # 获取历史数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+50)  # 多取一些数据用于计算
            
            # 使用akshare获取历史数据
            stock_code = code
            if code.startswith('6'):
                stock_code = f"sh{code}"
            else:
                stock_code = f"sz{code}"
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                   start_date=start_date.strftime('%Y%m%d'),
                                   end_date=end_date.strftime('%Y%m%d'))
            
            if df is None or df.empty:
                return {}
            
            # 重命名列
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 
                         'amount', 'amplitude', 'change_pct', 'change_amount', 'turnover']
            
            # 计算技术指标
            indicators = {}
            
            # MA均线
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            
            # MACD
            df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
            df['dif'] = df['ema12'] - df['ema26']
            df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
            df['macd'] = 2 * (df['dif'] - df['dea'])
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # 布林带
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            df['bb_std'] = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
            df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
            
            # 获取最新值
            latest = df.iloc[-1]
            
            indicators['ma5'] = round(latest['ma5'], 2) if not pd.isna(latest['ma5']) else 0
            indicators['ma10'] = round(latest['ma10'], 2) if not pd.isna(latest['ma10']) else 0
            indicators['ma20'] = round(latest['ma20'], 2) if not pd.isna(latest['ma20']) else 0
            indicators['ma60'] = round(latest['ma60'], 2) if not pd.isna(latest['ma60']) else 0
            indicators['macd'] = round(latest['macd'], 4) if not pd.isna(latest['macd']) else 0
            indicators['dif'] = round(latest['dif'], 4) if not pd.isna(latest['dif']) else 0
            indicators['dea'] = round(latest['dea'], 4) if not pd.isna(latest['dea']) else 0
            indicators['rsi'] = round(latest['rsi'], 2) if not pd.isna(latest['rsi']) else 0
            indicators['bb_upper'] = round(latest['bb_upper'], 2) if not pd.isna(latest['bb_upper']) else 0
            indicators['bb_lower'] = round(latest['bb_lower'], 2) if not pd.isna(latest['bb_lower']) else 0
            
            # 判断技术形态
            indicators['ma_trend'] = self._judge_ma_trend(latest)
            indicators['macd_signal'] = 'MACD金叉' if latest['macd'] > 0 and latest['dif'] > latest['dea'] else 'MACD死叉'
            
            return indicators
            
        except Exception as e:
            logger.error(f"计算技术指标失败[{code}]: {e}")
            return {}
    
    def _judge_ma_trend(self, data: pd.Series) -> str:
        """判断均线趋势"""
        try:
            ma5 = data.get('ma5', 0)
            ma10 = data.get('ma10', 0)
            ma20 = data.get('ma20', 0)
            ma60 = data.get('ma60', 0)
            
            if ma5 > ma10 > ma20 > ma60:
                return "多头排列"
            elif ma5 < ma10 < ma20 < ma60:
                return "空头排列"
            elif ma5 > ma10 > ma20:
                return "短期上涨"
            elif ma5 < ma10 < ma20:
                return "短期下跌"
            else:
                return "震荡"
        except:
            return "未知"
    
    def filter_by_technical_factor(self, df: pd.DataFrame, factor: str) -> pd.DataFrame:
        """
        按技术因子筛选
        :param df: 股票数据DataFrame
        :param factor: 技术因子名称
        :return: 筛选后的DataFrame
        """
        if factor == "全部" or not factor:
            return df
        
        try:
            result_list = []
            
            for idx, row in df.iterrows():
                code = row['code']
                indicators = self.calculate_technical_indicators(code, days=60)
                
                if not indicators:
                    continue
                
                # 根据不同因子进行筛选
                selected = False
                
                if factor == "SMA" and indicators.get('ma_trend') in ["多头排列", "短期上涨"]:
                    selected = True
                elif factor == "RSI" and 30 <= indicators.get('rsi', 0) <= 70:
                    selected = True
                elif factor == "MACD" and indicators.get('macd_signal') == 'MACD金叉':
                    selected = True
                elif factor == "动量" and indicators.get('ma5', 0) > indicators.get('ma20', 0):
                    selected = True
                
                if selected:
                    result_list.append(row)
            
            result = pd.DataFrame(result_list)
            logger.info(f"技术因子筛选[{factor}]: {len(result)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"技术因子筛选失败: {e}", exc_info=True)
            return df
    
    def evaluate_custom_condition(self, df: pd.DataFrame, condition: str) -> pd.DataFrame:
        """
        评估自定义筛选条件
        :param df: 股票数据DataFrame
        :param condition: 自定义条件表达式，如 "PE<20 and PB>1"
        :return: 筛选后的DataFrame
        """
        if not condition or condition.strip() == "":
            return df
        
        try:
            # 安全地评估表达式
            # 替换列名以便pandas query使用
            safe_condition = condition.replace('PE', 'pe').replace('PB', 'pb')
            safe_condition = safe_condition.replace('市值', 'market_cap')
            safe_condition = safe_condition.replace('涨幅', 'change_pct')
            
            result = df.query(safe_condition)
            logger.info(f"自定义条件筛选[{condition}]: {len(result)} 只股票")
            return result
        except Exception as e:
            logger.error(f"自定义条件评估失败: {e}")
            return df
    
    def multi_factor_selection(self, 
                              industry: str = "全部",
                              min_market_cap: float = None,
                              max_market_cap: float = None,
                              min_pe: float = None,
                              max_pe: float = None,
                              min_pb: float = None,
                              max_pb: float = None,
                              technical_factor: str = "全部",
                              custom_condition: str = "") -> pd.DataFrame:
        """
        多因子综合选股
        :param industry: 行业
        :param min_market_cap: 最小市值
        :param max_market_cap: 最大市值
        :param min_pe: 最小PE
        :param max_pe: 最大PE
        :param min_pb: 最小PB
        :param max_pb: 最大PB
        :param technical_factor: 技术因子
        :param custom_condition: 自定义条件
        :return: 筛选结果DataFrame
        """
        try:
            logger.info("开始多因子选股...")
            
            # 获取股票基础信息
            df = self.get_stock_basic_info()
            
            if df.empty:
                logger.warning("股票池为空，无法进行选股")
                return pd.DataFrame()
            
            # 行业筛选
            df = self.filter_by_industry(df, industry)
            
            # 市值筛选
            df = self.filter_by_market_cap(df, min_market_cap, max_market_cap)
            
            # PE筛选
            df = self.filter_by_pe(df, min_pe, max_pe)
            
            # PB筛选
            df = self.filter_by_pb(df, min_pb, max_pb)
            
            # 自定义条件筛选
            if custom_condition:
                df = self.evaluate_custom_condition(df, custom_condition)
            
            # 技术因子筛选（较耗时，限制数量）
            if technical_factor != "全部" and len(df) > 0:
                # 为了提高速度，只对前100只股票进行技术指标筛选
                df_sample = df.head(100)
                df = self.filter_by_technical_factor(df_sample, technical_factor)
            
            logger.info(f"多因子选股完成，共筛选出 {len(df)} 只股票")
            return df
            
        except Exception as e:
            logger.error(f"多因子选股失败: {e}", exc_info=True)
            return pd.DataFrame()
    
    def export_to_excel(self, df: pd.DataFrame, filepath: str) -> bool:
        """
        导出选股结果到Excel
        :param df: 选股结果DataFrame
        :param filepath: 文件路径
        :return: 是否成功
        """
        try:
            df.to_excel(filepath, index=False, engine='openpyxl')
            logger.info(f"选股结果已导出到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出Excel失败: {e}")
            return False
    
    def export_to_csv(self, df: pd.DataFrame, filepath: str) -> bool:
        """
        导出选股结果到CSV
        :param df: 选股结果DataFrame
        :param filepath: 文件路径
        :return: 是否成功
        """
        try:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"选股结果已导出到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False
