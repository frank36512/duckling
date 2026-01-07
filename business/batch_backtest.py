"""
批量回测引擎
支持同时回测多个策略并进行对比分析
"""

import logging
from typing import List, Dict, Any
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from business.backtest_engine import BacktestEngine, BacktestResult
from business.data_manager import DataManager
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)


class BatchBacktest:
    """批量回测引擎"""
    
    def __init__(self, config: Dict[str, Any], data_manager: DataManager):
        """
        初始化批量回测引擎
        :param config: 回测配置
        :param data_manager: 数据管理器
        """
        self.config = config
        self.data_manager = data_manager
        self.results = []  # 存储所有回测结果
        
    def run_multiple_strategies(self, 
                                stock_code: str,
                                start_date: str,
                                end_date: str,
                                strategy_names: List[str],
                                strategy_params: Dict[str, Dict] = None,
                                max_workers: int = 4) -> List[Dict[str, Any]]:
        """
        并行运行多个策略的回测
        
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param strategy_names: 策略名称列表
        :param strategy_params: 每个策略的参数字典 {strategy_name: params}
        :param max_workers: 最大并行工作线程数
        :return: 回测结果列表
        """
        logger.info("="*60)
        logger.info(f"开始批量回测: {stock_code}")
        logger.info(f"日期范围: {start_date} ~ {end_date}")
        logger.info(f"策略数量: {len(strategy_names)}")
        logger.info(f"策略列表: {strategy_names}")
        logger.info("="*60)
        
        # 先获取数据（所有策略共用同一份数据）
        try:
            data = self.data_manager.get_stock_data(stock_code, start_date, end_date)
            if data is None or data.empty:
                logger.error(f"无法获取股票 {stock_code} 的数据")
                return []
            
            logger.info(f"数据获取成功，共 {len(data)} 条记录")
        except Exception as e:
            logger.error(f"获取数据失败: {e}", exc_info=True)
            return []
        
        # 准备策略参数
        if strategy_params is None:
            strategy_params = {}
        
        # 使用线程池并行执行回测
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有回测任务
            future_to_strategy = {}
            for strategy_name in strategy_names:
                params = strategy_params.get(strategy_name, {})
                future = executor.submit(
                    self._run_single_strategy,
                    stock_code,
                    data.copy(),  # 传递数据副本
                    strategy_name,
                    params
                )
                future_to_strategy[future] = strategy_name
            
            # 收集结果
            for future in as_completed(future_to_strategy):
                strategy_name = future_to_strategy[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        logger.info(f"✓ {strategy_name} 回测完成")
                except Exception as e:
                    logger.error(f"✗ {strategy_name} 回测失败: {e}", exc_info=True)
        
        self.results = results
        logger.info("="*60)
        logger.info(f"批量回测完成，成功: {len(results)}/{len(strategy_names)}")
        logger.info("="*60)
        
        return results
    
    def _run_single_strategy(self,
                            stock_code: str,
                            data: pd.DataFrame,
                            strategy_name: str,
                            params: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行单个策略的回测
        
        :param stock_code: 股票代码
        :param data: 股票数据
        :param strategy_name: 策略名称
        :param params: 策略参数
        :return: 回测结果字典
        """
        try:
            logger.info(f"开始回测策略: {strategy_name}")
            
            # 创建回测引擎
            engine = BacktestEngine(self.config)
            
            # 添加数据
            engine.add_data(data, stock_code)
            
            # 创建策略
            strategy = StrategyFactory.create_strategy(strategy_name, params)
            if strategy is None:
                logger.error(f"无法创建策略: {strategy_name}")
                return None
            
            # 添加策略
            engine.add_strategy(strategy)
            
            # 运行回测
            result_dict = engine.run()
            
            # 添加策略信息到结果中
            result_dict['strategy_name'] = strategy_name
            result_dict['strategy_params'] = params
            result_dict['stock_code'] = stock_code
            result_dict['ohlc_data'] = data
            
            # 转换为BacktestResult对象
            result = BacktestResult(result_dict)
            
            # 返回包含更多信息的字典
            return {
                'strategy_name': strategy_name,
                'strategy_params': params,
                'result': result,
                'result_dict': result_dict
            }
            
        except Exception as e:
            logger.error(f"回测策略 {strategy_name} 失败: {e}", exc_info=True)
            return None
    
    def get_comparison_metrics(self) -> pd.DataFrame:
        """
        获取对比指标表格
        
        :return: DataFrame包含所有策略的关键指标
        """
        if not self.results:
            logger.warning("没有回测结果可供对比")
            return pd.DataFrame()
        
        metrics_list = []
        
        for result_item in self.results:
            strategy_name = result_item['strategy_name']
            result = result_item['result']
            
            metrics = {
                '策略名称': strategy_name,
                '总收益率(%)': round(result.total_return, 2),
                '年化收益率(%)': round(result.annual_return, 2),
                '夏普比率': round(result.sharpe_ratio, 3),
                '最大回撤(%)': round(result.max_drawdown, 2),
                '总交易次数': result.total_trades,
                '胜率(%)': round(result.win_rate, 2),
                '盈亏比': round(result.profit_factor, 2),
                '最终资金': round(result.final_value, 2),
            }
            
            metrics_list.append(metrics)
        
        df = pd.DataFrame(metrics_list)
        
        # 按总收益率降序排序
        df = df.sort_values('总收益率(%)', ascending=False)
        df = df.reset_index(drop=True)
        
        # 添加排名列
        df.insert(0, '排名', range(1, len(df) + 1))
        
        logger.info(f"生成对比指标表格，共 {len(df)} 个策略")
        
        return df
    
    def get_radar_data(self) -> Dict[str, List[float]]:
        """
        获取雷达图数据（归一化到0-1）
        
        :return: 字典 {strategy_name: [指标1, 指标2, ...]}
        """
        if not self.results:
            return {}
        
        # 提取原始指标
        raw_metrics = {}
        for result_item in self.results:
            strategy_name = result_item['strategy_name']
            result = result_item['result']
            
            raw_metrics[strategy_name] = {
                '收益率': result.total_return,
                '夏普比率': max(result.sharpe_ratio, 0),  # 负值设为0
                '回撤(倒数)': 100 - result.max_drawdown,  # 转换为正向指标
                '胜率': result.win_rate,
                '盈亏比': result.profit_factor,
            }
        
        # 归一化到0-1
        metrics_names = ['收益率', '夏普比率', '回撤(倒数)', '胜率', '盈亏比']
        normalized_data = {}
        
        for metric_name in metrics_names:
            values = [raw_metrics[s][metric_name] for s in raw_metrics]
            min_val = min(values)
            max_val = max(values)
            
            # 避免除以0
            if max_val - min_val < 1e-6:
                normalized = {s: 0.5 for s in raw_metrics}
            else:
                normalized = {
                    s: (raw_metrics[s][metric_name] - min_val) / (max_val - min_val)
                    for s in raw_metrics
                }
            
            # 保存归一化结果
            for strategy_name in raw_metrics:
                if strategy_name not in normalized_data:
                    normalized_data[strategy_name] = []
                normalized_data[strategy_name].append(normalized[strategy_name])
        
        logger.info(f"生成雷达图数据，维度: {metrics_names}")
        
        return {
            'data': normalized_data,
            'labels': metrics_names
        }
    
    def get_equity_curves(self) -> Dict[str, pd.Series]:
        """
        获取所有策略的资金曲线
        
        :return: 字典 {strategy_name: equity_curve}
        """
        curves = {}
        
        for result_item in self.results:
            strategy_name = result_item['strategy_name']
            result = result_item['result']
            
            if result.equity_curve is not None:
                curves[strategy_name] = result.equity_curve
        
        logger.info(f"提取 {len(curves)} 个策略的资金曲线")
        
        return curves
    
    def get_best_strategy(self, metric: str = 'total_return') -> Dict[str, Any]:
        """
        获取表现最好的策略
        
        :param metric: 评价指标 ('total_return', 'sharpe_ratio', 'win_rate')
        :return: 最佳策略的结果字典
        """
        if not self.results:
            return None
        
        metric_map = {
            'total_return': lambda r: r['result'].total_return,
            'sharpe_ratio': lambda r: r['result'].sharpe_ratio,
            'win_rate': lambda r: r['result'].win_rate,
            'max_drawdown': lambda r: -r['result'].max_drawdown,  # 负值，越小越好
        }
        
        if metric not in metric_map:
            logger.warning(f"未知指标: {metric}, 使用total_return")
            metric = 'total_return'
        
        best = max(self.results, key=metric_map[metric])
        
        logger.info(f"最佳策略({metric}): {best['strategy_name']}")
        
        return best
    
    def export_results(self, filepath: str) -> bool:
        """
        导出对比结果到Excel
        
        :param filepath: 导出文件路径
        :return: 是否成功
        """
        try:
            df = self.get_comparison_metrics()
            df.to_excel(filepath, index=False, sheet_name='策略对比')
            logger.info(f"对比结果已导出到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出结果失败: {e}", exc_info=True)
            return False
