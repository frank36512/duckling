"""
增强版量化选股模块
复用现有策略的多因子模型和机器学习模型
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_source import AKShareDataSource

logger = logging.getLogger(__name__)


class EnhancedStockSelector:
    """增强版量化选股器 - 复用现有策略模型"""
    
    def __init__(self, data_source=None):
        """初始化选股器"""
        self.data_source = data_source or AKShareDataSource({})
        logger.info("增强版量化选股器初始化完成")
    
    def calculate_multifactor_score(self, data: pd.DataFrame) -> Tuple[float, Dict]:
        """
        计算多因子得分（复用MultiFactorStrategy的逻辑）
        
        返回: (综合得分, 各因子详情)
        """
        if data is None or len(data) < 60:
            return None, None
        
        try:
            # 计算技术指标
            close = data['close'].values
            volume = data['volume'].values
            
            # 1. MACD因子（趋势）
            macd_line, signal_line, _ = self._calculate_macd(close)
            if macd_line is None:
                return None, None
                
            macd_diff = macd_line[-1] - signal_line[-1]
            macd_score = np.clip(macd_diff / abs(signal_line[-1]) * 2, -1, 1) if signal_line[-1] != 0 else 0
            
            # 2. 均线因子（趋势）
            ma_20 = np.mean(close[-20:])
            ma_score = np.clip((close[-1] - ma_20) / ma_20 * 10, -1, 1)
            
            # 3. RSI因子（动量）
            rsi = self._calculate_rsi(close, period=14)
            if rsi[-1] < 30:
                rsi_score = 1.0  # 超卖
            elif rsi[-1] > 70:
                rsi_score = -1.0  # 超买
            else:
                rsi_score = (50 - rsi[-1]) / 20
            
            # 4. ROC因子（动量）
            roc = ((close[-1] - close[-10]) / close[-10]) * 100 if len(close) >= 10 else 0
            roc_score = np.clip(roc / 10, -1, 1)
            
            # 5. 布林带因子（波动）
            bb_upper, bb_mid, bb_lower = self._calculate_bollinger_bands(close, period=20)
            bb_range = bb_upper[-1] - bb_lower[-1]
            bb_position = (close[-1] - bb_lower[-1]) / bb_range if bb_range > 0 else 0.5
            bb_score = 1.0 - 2 * bb_position  # 下轨附近为正，上轨附近为负
            
            # 6. 成交量因子
            volume_ma = np.mean(volume[-20:])
            volume_ratio = volume[-1] / volume_ma if volume_ma > 0 else 1
            volume_score = 0.5 * (1 if macd_score > 0 else -1) if volume_ratio > 1.5 else 0
            
            # 因子权重
            factors = [
                ('MACD', macd_score, 1.0),
                ('MA', ma_score, 0.8),
                ('RSI', rsi_score, 0.9),
                ('ROC', roc_score, 0.7),
                ('BB', bb_score, 0.6),
                ('Volume', volume_score, 0.5),
            ]
            
            # 计算加权得分
            total_weight = sum(w for _, _, w in factors)
            weighted_score = sum(s * w for _, s, w in factors) / total_weight
            
            # 返回详细信息
            factor_details = {
                'MACD得分': round(macd_score, 3),
                'MA得分': round(ma_score, 3),
                'RSI得分': round(rsi_score, 3),
                'ROC得分': round(roc_score, 3),
                'BB得分': round(bb_score, 3),
                '成交量得分': round(volume_score, 3),
                'RSI值': round(rsi[-1], 2),
                'MACD': round(macd_diff, 4),
            }
            
            return weighted_score, factor_details
            
        except Exception as e:
            logger.error(f"计算多因子得分失败: {e}")
            return None, None
    
    def calculate_ml_features(self, data: pd.DataFrame) -> Dict:
        """
        计算机器学习特征（复用XGBoost/RandomForest策略的特征工程）
        
        返回10维特征向量
        """
        try:
            close = data['close'].values
            volume = data['volume'].values
            
            # 价格特征
            sma_5 = np.mean(close[-5:])
            sma_10 = np.mean(close[-10:])
            sma_20 = np.mean(close[-20:])
            
            # 动量特征
            rsi = self._calculate_rsi(close, period=14)[-1]
            macd_line, signal_line, _ = self._calculate_macd(close)
            macd_value = macd_line[-1] if macd_line is not None else 0
            macd_signal = signal_line[-1] if signal_line is not None else 0
            roc = ((close[-1] - close[-10]) / close[-10]) * 100 if len(close) >= 10 else 0
            
            # 波动率特征
            returns = np.diff(close) / close[:-1]
            atr = np.mean(np.abs(returns[-14:])) * close[-1] if len(returns) >= 14 else 0
            bb_upper, bb_mid, bb_lower = self._calculate_bollinger_bands(close)
            bb_width = (bb_upper[-1] - bb_lower[-1]) / close[-1] if close[-1] > 0 else 0
            
            # 成交量特征
            volume_ma = np.mean(volume[-20:])
            volume_ratio = volume[-1] / volume_ma if volume_ma > 0 else 1
            
            features = {
                'sma5_ratio': sma_5 / close[-1] if close[-1] > 0 else 1,
                'sma10_ratio': sma_10 / close[-1] if close[-1] > 0 else 1,
                'sma20_ratio': sma_20 / close[-1] if close[-1] > 0 else 1,
                'rsi_normalized': rsi / 100,
                'macd': macd_value,
                'macd_signal': macd_signal,
                'roc_normalized': roc / 100,
                'atr_ratio': atr / close[-1] if close[-1] > 0 else 0,
                'bb_width': bb_width,
                'volume_ratio': volume_ratio,
            }
            
            return features
            
        except Exception as e:
            logger.error(f"计算ML特征失败: {e}")
            return None
    
    def select_by_multifactor(self, stock_codes: List[str], top_n: int = 20) -> pd.DataFrame:
        """
        多因子选股（使用复用的因子体系）
        
        :param stock_codes: 股票代码列表
        :param top_n: 选出前N只
        :return: 选股结果DataFrame
        """
        logger.info(f"开始多因子选股，候选股票数: {len(stock_codes)}")
        results = []
        
        for i, code in enumerate(stock_codes):
            if (i + 1) % 50 == 0:
                logger.info(f"处理进度: {i+1}/{len(stock_codes)}")
            
            try:
                # 获取历史数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                
                data = self.data_source.get_stock_data(code, start_date, end_date)
                
                if data is None or len(data) < 60:
                    continue
                
                # 计算多因子得分
                score, factor_details = self.calculate_multifactor_score(data)
                
                if score is None:
                    continue
                
                # 组装结果
                result = {
                    '股票代码': code,
                    '最新价': round(data['close'].iloc[-1], 2),
                    '涨跌幅%': round((data['close'].iloc[-1] / data['close'].iloc[-2] - 1) * 100, 2),
                    '综合得分': round(score, 3),
                }
                
                # 添加因子详情
                if factor_details:
                    result.update(factor_details)
                
                results.append(result)
                
            except Exception as e:
                logger.debug(f"处理股票 {code} 失败: {e}")
                continue
        
        # 转换为DataFrame并排序
        if not results:
            logger.warning("没有找到符合条件的股票")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df = df.sort_values('综合得分', ascending=False).head(top_n)
        df = df.reset_index(drop=True)
        df.index = df.index + 1
        
        logger.info(f"选股完成，共选出 {len(df)} 只股票")
        return df
    
    def select_by_technical_signals(self, stock_codes: List[str], 
                                    signal_type: str = "金叉") -> pd.DataFrame:
        """
        技术信号选股（复用各个策略的信号逻辑）
        
        :param stock_codes: 股票代码列表
        :param signal_type: 信号类型（金叉、突破、超跌反弹等）
        :return: 选股结果DataFrame
        """
        logger.info(f"开始技术信号选股，信号类型: {signal_type}")
        results = []
        
        for code in stock_codes:
            try:
                # 获取历史数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
                
                data = self.data_source.get_stock_data(code, start_date, end_date)
                
                if data is None or len(data) < 60:
                    continue
                
                # 根据信号类型判断
                signal_found = False
                signal_desc = ""
                
                if signal_type == "MACD金叉":
                    signal_found, signal_desc = self._check_macd_cross(data)
                elif signal_type == "均线多头":
                    signal_found, signal_desc = self._check_ma_bullish(data)
                elif signal_type == "RSI超跌":
                    signal_found, signal_desc = self._check_rsi_oversold(data)
                elif signal_type == "布林带突破":
                    signal_found, signal_desc = self._check_bb_breakout(data)
                elif signal_type == "成交量放大":
                    signal_found, signal_desc = self._check_volume_surge(data)
                
                if signal_found:
                    results.append({
                        '股票代码': code,
                        '最新价': round(data['close'].iloc[-1], 2),
                        '涨跌幅%': round((data['close'].iloc[-1] / data['close'].iloc[-2] - 1) * 100, 2),
                        '信号描述': signal_desc,
                    })
                
            except Exception as e:
                logger.debug(f"处理股票 {code} 失败: {e}")
                continue
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.reset_index(drop=True)
            df.index = df.index + 1
        
        logger.info(f"技术信号选股完成，找到 {len(df)} 只股票")
        return df
    
    # ==================== 辅助方法 ====================
    
    def _calculate_macd(self, close: np.ndarray, fast=12, slow=26, signal=9):
        """计算MACD"""
        try:
            if len(close) < slow:
                return None, None, None
            
            ema_fast = self._ema(close, fast)
            ema_slow = self._ema(close, slow)
            macd_line = ema_fast - ema_slow
            signal_line = self._ema(macd_line, signal)
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
        except:
            return None, None, None
    
    def _calculate_rsi(self, close: np.ndarray, period=14):
        """计算RSI"""
        try:
            if len(close) < period + 1:
                return np.array([50] * len(close))
            
            deltas = np.diff(close)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
            avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
            
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            # 补齐长度
            rsi = np.concatenate([np.array([50] * period), rsi])
            
            return rsi
        except:
            return np.array([50] * len(close))
    
    def _calculate_bollinger_bands(self, close: np.ndarray, period=20, std_dev=2):
        """计算布林带"""
        try:
            if len(close) < period:
                return close, close, close
            
            sma = np.convolve(close, np.ones(period)/period, mode='valid')
            sma = np.concatenate([close[:period-1], sma])
            
            std = np.array([np.std(close[max(0, i-period+1):i+1]) for i in range(len(close))])
            
            upper = sma + std_dev * std
            lower = sma - std_dev * std
            
            return upper, sma, lower
        except:
            return close, close, close
    
    def _ema(self, data: np.ndarray, period: int):
        """计算EMA"""
        try:
            alpha = 2 / (period + 1)
            ema = np.zeros_like(data)
            ema[0] = data[0]
            
            for i in range(1, len(data)):
                ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
            
            return ema
        except:
            return data
    
    def _check_macd_cross(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """检查MACD金叉"""
        close = data['close'].values
        macd_line, signal_line, _ = self._calculate_macd(close)
        
        if macd_line is None:
            return False, ""
        
        # 最近5天内金叉
        for i in range(max(0, len(macd_line)-5), len(macd_line)-1):
            if macd_line[i] < signal_line[i] and macd_line[i+1] > signal_line[i+1]:
                return True, f"MACD金叉({len(macd_line)-i-1}天前)"
        
        return False, ""
    
    def _check_ma_bullish(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """检查均线多头排列"""
        close = data['close'].values
        
        if len(close) < 60:
            return False, ""
        
        ma5 = np.mean(close[-5:])
        ma10 = np.mean(close[-10:])
        ma20 = np.mean(close[-20:])
        ma60 = np.mean(close[-60:])
        
        if ma5 > ma10 > ma20 > ma60:
            return True, f"均线多头排列(MA5>{ma10:.2f}>MA20>{ma60:.2f})"
        
        return False, ""
    
    def _check_rsi_oversold(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """检查RSI超跌反弹"""
        close = data['close'].values
        rsi = self._calculate_rsi(close, period=14)
        
        # RSI从30以下回升到30-50区间
        if len(rsi) >= 5:
            if rsi[-5] < 30 and 30 < rsi[-1] < 50:
                return True, f"RSI超跌反弹(从{rsi[-5]:.1f}回升至{rsi[-1]:.1f})"
        
        return False, ""
    
    def _check_bb_breakout(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """检查布林带突破"""
        close = data['close'].values
        bb_upper, bb_mid, bb_lower = self._calculate_bollinger_bands(close)
        
        # 价格突破上轨
        if close[-1] > bb_upper[-1]:
            return True, f"突破布林带上轨({close[-1]:.2f}>{bb_upper[-1]:.2f})"
        
        # 价格从下轨反弹
        if len(close) >= 3:
            if close[-3] < bb_lower[-3] and close[-1] > bb_mid[-1]:
                return True, "从下轨反弹至中轨上方"
        
        return False, ""
    
    def _check_volume_surge(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """检查成交量放大"""
        volume = data['volume'].values
        
        if len(volume) < 20:
            return False, ""
        
        volume_ma = np.mean(volume[-20:-1])  # 排除今天
        volume_ratio = volume[-1] / volume_ma if volume_ma > 0 else 1
        
        if volume_ratio > 2.0:
            return True, f"成交量放大{volume_ratio:.1f}倍"
        
        return False, ""
