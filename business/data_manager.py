"""
数据管理模块
负责数据的下载、存储、更新和查询
"""

import logging
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_source import DataSourceFactory, DataSourceBase

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据管理器
        :param config: 配置信息
        """
        try:
            self.config = config
            
            # 处理数据库路径（支持打包后的相对路径）
            db_path = config.get('database', {}).get('path', './data/stock_data.db')
            if not os.path.isabs(db_path):
                # 如果是相对路径，相对于可执行文件目录
                if getattr(sys, 'frozen', False):
                    # 打包后的路径
                    base_path = Path(sys.executable).parent
                else:
                    # 开发环境路径
                    base_path = Path(__file__).parent.parent
                self.db_path = str(base_path / db_path.lstrip('./'))
            else:
                self.db_path = db_path
            
            logger.info(f"数据库路径: {self.db_path}")
            
            # 确保数据库目录存在
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 初始化数据源
            data_source_config = config.get('data_source', {})
            primary_source = data_source_config.get('primary', 'akshare')
            logger.info(f"数据源: {primary_source}")
            
            self.data_source = DataSourceFactory.create_data_source(
                primary_source,
                data_source_config.get(primary_source, {})
            )
            
            # 初始化数据库
            self._init_database()
            
            logger.info("数据管理器初始化完成")
            
        except Exception as e:
            logger.error(f"数据管理器初始化失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 股票列表表（简化版本，只存储核心信息）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_list (
                code TEXT PRIMARY KEY,
                name TEXT,
                update_time TEXT
            )
        """)
        
        # 日线数据表（按股票代码分表，这里创建通用模板）
        # 实际使用时会为每只股票创建独立表
        
        # 数据更新记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT,
                data_type TEXT,
                start_date TEXT,
                end_date TEXT,
                record_count INTEGER,
                update_time TEXT,
                status TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("数据库初始化完成")
    
    def _create_stock_table(self, stock_code: str):
        """
        为指定股票创建数据表
        :param stock_code: 股票代码
        """
        table_name = f"daily_{stock_code.replace('.', '_')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                trade_date TEXT PRIMARY KEY,
                ts_code TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                vol REAL,
                amount REAL
            )
        """)
        
        # 创建日期索引
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_date 
            ON {table_name}(trade_date)
        """)
        
        conn.commit()
        conn.close()
    
    def update_stock_list(self, market: str = 'A') -> Optional[pd.DataFrame]:
        """
        更新股票列表
        :param market: 市场类型
        :return: 股票列表DataFrame，失败返回None
        """
        try:
            logger.info(f"开始更新{market}股票列表...")
            
            # 从数据源获取股票列表
            df = self.data_source.get_stock_list(market)
            
            if df is None or df.empty:
                logger.warning("获取到的股票列表为空")
                return None
            
            # 添加更新时间
            update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存到数据库（确保使用正确的列名）
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 清空旧数据
            cursor.execute("DELETE FROM stock_list")
            
            # 插入新数据 - 使用简化的表结构 (code, name, update_time)
            insert_count = 0
            for _, row in df.iterrows():
                code = None
                name = None
                
                # akshare返回的列名是'code'和'name' (英文小写)
                if 'code' in df.columns and 'name' in df.columns:
                    code = row['code']
                    name = row['name']
                # 有些数据源可能返回中文列名'代码'和'名称'
                elif '代码' in df.columns and '名称' in df.columns:
                    code = row['代码']
                    name = row['名称']
                # tushare返回的列名是'symbol'和'name'
                elif 'symbol' in df.columns and 'name' in df.columns:
                    code = row['symbol']
                    name = row['name']
                
                # 如果找到了code和name，插入数据库
                if code is not None and name is not None:
                    cursor.execute("""
                        INSERT OR REPLACE INTO stock_list (code, name, update_time)
                        VALUES (?, ?, ?)
                    """, (code, name, update_time))
                    insert_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"股票列表更新完成，共{len(df)}只股票，实际插入{insert_count}条记录")
            
            if insert_count == 0:
                logger.warning(f"警告：没有插入任何记录！DataFrame列名: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"更新股票列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def download_stock_data(self, stock_code: str, start_date: str, 
                           end_date: str) -> bool:
        """
        下载股票历史数据
        :param stock_code: 股票代码
        :param start_date: 开始日期 YYYY-MM-DD
        :param end_date: 结束日期 YYYY-MM-DD
        :return: 是否成功
        """
        try:
            logger.info(f"开始下载 {stock_code} 从 {start_date} 到 {end_date} 的数据...")
            
            # 从数据源获取数据
            df = self.data_source.get_daily_data(stock_code, start_date, end_date)
            
            if df.empty:
                logger.warning(f"{stock_code} 无数据")
                return False
            
            # 确保表存在
            self._create_stock_table(stock_code)
            
            # 保存到数据库
            table_name = f"daily_{stock_code.replace('.', '_')}"
            conn = sqlite3.connect(self.db_path)
            
            # 转换日期格式为字符串
            df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')
            
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # 获取股票名称
            stock_name = '未命名'
            try:
                # 尝试从数据源获取股票列表信息
                stock_list_df = self.data_source.get_stock_list('A')
                if not stock_list_df.empty:
                    # akshare返回的列名可能是'代码'和'名称'
                    if '代码' in stock_list_df.columns and '名称' in stock_list_df.columns:
                        matching = stock_list_df[stock_list_df['代码'] == stock_code[:6]]
                        if not matching.empty:
                            stock_name = matching.iloc[0]['名称']
                    # tushare返回的列名是'symbol'和'name'
                    elif 'symbol' in stock_list_df.columns and 'name' in stock_list_df.columns:
                        matching = stock_list_df[stock_list_df['symbol'] == stock_code[:6]]
                        if not matching.empty:
                            stock_name = matching.iloc[0]['name']
            except Exception as e:
                logger.warning(f"获取股票{stock_code}名称失败: {e}")
            
            # 添加到股票列表（如果不存在）
            cursor = conn.cursor()
            # 使用实际的表结构：code, name, update_time
            cursor.execute("""
                INSERT OR IGNORE INTO stock_list (code, name, update_time)
                VALUES (?, ?, ?)
            """, (stock_code[:6], stock_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            # 记录更新日志
            self._log_update(stock_code, 'daily', start_date, end_date, 
                           len(df), 'success')
            
            conn.close()
            
            logger.info(f"{stock_code} 数据下载完成，共{len(df)}条记录")
            return True
            
        except Exception as e:
            logger.error(f"下载股票数据失败: {e}")
            self._log_update(stock_code, 'daily', start_date, end_date, 
                           0, 'failed')
            return False
    
    def get_stock_data(self, stock_code: str, start_date: str = None, 
                      end_date: str = None) -> pd.DataFrame:
        """
        查询股票数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: DataFrame
        """
        try:
            table_name = f"daily_{stock_code.replace('.', '_')}"
            conn = sqlite3.connect(self.db_path)
            
            # 构建查询SQL
            sql = f"SELECT * FROM {table_name}"
            conditions = []
            
            if start_date:
                conditions.append(f"trade_date >= '{start_date}'")
            if end_date:
                conditions.append(f"trade_date <= '{end_date}'")
            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY trade_date"
            
            df = pd.read_sql_query(sql, conn)
            conn.close()
            
            if not df.empty:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            logger.info(f"查询 {stock_code} 数据，共{len(df)}条记录")
            return df
            
        except Exception as e:
            logger.error(f"查询股票数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表
        :return: DataFrame
        """
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM stock_list", conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def _log_update(self, stock_code: str, data_type: str, 
                   start_date: str, end_date: str, 
                   record_count: int, status: str):
        """
        记录数据更新日志
        :param stock_code: 股票代码
        :param data_type: 数据类型
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param record_count: 记录数
        :param status: 状态
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO update_log 
                (stock_code, data_type, start_date, end_date, 
                 record_count, update_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (stock_code, data_type, start_date, end_date, 
                  record_count, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  status))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录更新日志失败: {e}")
    
    def batch_download(self, stock_codes: List[str], start_date: str, 
                      end_date: str) -> Dict[str, bool]:
        """
        批量下载股票数据
        :param stock_codes: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 下载结果字典 {股票代码: 是否成功}
        """
        results = {}
        
        for i, code in enumerate(stock_codes, 1):
            logger.info(f"批量下载进度: {i}/{len(stock_codes)}")
            results[code] = self.download_stock_data(code, start_date, end_date)
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"批量下载完成，成功{success_count}个，失败{len(stock_codes)-success_count}个")
        
        return results
    
    def check_data_exists(self, stock_code: str) -> bool:
        """
        检查股票数据是否存在
        :param stock_code: 股票代码
        :return: 是否存在
        """
        try:
            table_name = f"daily_{stock_code.replace('.', '_')}"
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table_name}'
            """)
            
            exists = cursor.fetchone() is not None
            conn.close()
            
            return exists
        except Exception as e:
            logger.error(f"检查数据失败: {e}")
            return False
    
    def get_all_stocks_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取所有股票的行情数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 包含所有股票数据的DataFrame
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有日线数据表
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'daily_%'
            """)
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("没有找到任何股票数据表")
                conn.close()
                return pd.DataFrame()
            
            all_data_frames = []
            
            # 遍历所有表并合并数据
            for (table_name,) in tables:
                try:
                    # 从表名提取股票代码
                    # daily_000001_SZ -> 000001.SZ
                    # stock_code = table_name.replace('daily_', '').replace('_', '.')
                    
                    # 构建查询SQL（数据库中已有ts_code列，无需重复添加）
                    sql = f"SELECT * FROM {table_name}"
                    conditions = []
                    
                    if start_date:
                        conditions.append(f"trade_date >= '{start_date}'")
                    if end_date:
                        conditions.append(f"trade_date <= '{end_date}'")
                    
                    if conditions:
                        sql += " WHERE " + " AND ".join(conditions)
                    
                    sql += " ORDER BY trade_date DESC LIMIT 100"  # 每只股票最多取100条，避免数据量过大
                    
                    df = pd.read_sql_query(sql, conn)
                    if not df.empty:
                        all_data_frames.append(df)
                        
                except Exception as e:
                    logger.warning(f"读取表 {table_name} 失败: {e}")
                    continue
            
            conn.close()
            
            if not all_data_frames:
                logger.warning("没有读取到任何数据")
                return pd.DataFrame()
            
            # 合并所有数据
            result = pd.concat(all_data_frames, ignore_index=True)
            
            # 转换日期格式
            if 'trade_date' in result.columns:
                result['trade_date'] = pd.to_datetime(result['trade_date'])
            
            # 按日期降序排序
            result = result.sort_values('trade_date', ascending=False)
            
            logger.info(f"获取所有股票数据，共 {len(result)} 条记录，涉及 {len(all_data_frames)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"获取所有股票数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
