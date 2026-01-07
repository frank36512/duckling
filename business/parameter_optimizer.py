"""
参数优化模块
支持网格搜索和随机搜索两种参数优化算法
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product
import random
from datetime import datetime, timedelta

from business.backtest_engine import BacktestEngine
from business.data_manager import DataManager
from core.strategy_base import StrategyFactory

logger = logging.getLogger(__name__)


class OptimizationResult:
    """优化结果类"""
    
    def __init__(self, params: Dict[str, Any], metrics: Dict[str, float]):
        """
        初始化优化结果
        :param params: 参数字典
        :param metrics: 指标字典
        """
        self.params = params
        self.metrics = metrics
    
    def __repr__(self):
        return f"OptimizationResult(params={self.params}, return={self.metrics.get('total_return', 0):.2f}%)"


class ParameterOptimizer:
    """
    参数优化基类
    提供通用的参数优化框架
    """
    
    def __init__(self, config: Dict[str, Any], data_manager: DataManager):
        """
        初始化参数优化器
        :param config: 配置字典
        :param data_manager: 数据管理器
        """
        self.config = config
        self.data_manager = data_manager
        self.results: List[OptimizationResult] = []
        
        # 优化配置
        self.initial_capital = config.get('initial_capital', 100000)
        self.commission = config.get('commission', 0.0003)
        self.stamp_duty = config.get('stamp_duty', 0.001)
        
        logger.info("参数优化器初始化完成")
    
    def _run_backtest_with_params(
        self, 
        strategy_name: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        params: Dict[str, Any]
    ) -> OptimizationResult:
        """
        使用指定参数运行回测
        :param strategy_name: 策略名称
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param params: 策略参数
        :return: 优化结果
        """
        try:
            # 创建回测引擎
            engine = BacktestEngine(self.config)
            
            # 获取数据
            data = self.data_manager.get_stock_data(
                stock_code, 
                start_date, 
                end_date
            )
            
            if data is None or data.empty:
                logger.warning(f"参数{params}: 数据为空")
                return OptimizationResult(params, {'total_return': -100})
            
            # 添加数据
            engine.add_data(stock_code, data)
            
            # 添加策略（带参数）
            engine.add_strategy(strategy_name, **params)
            
            # 运行回测
            result = engine.run()
            
            if result is None:
                logger.warning(f"参数{params}: 回测失败")
                return OptimizationResult(params, {'total_return': -100})
            
            # 提取指标
            metrics = {
                'total_return': result.total_return,
                'annual_return': result.annual_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor,
                'final_value': result.final_value,
            }
            
            return OptimizationResult(params, metrics)
            
        except Exception as e:
            logger.error(f"参数{params}回测异常: {e}", exc_info=True)
            return OptimizationResult(params, {'total_return': -100})
    
    def get_best_params(self, metric: str = 'total_return') -> Optional[Dict[str, Any]]:
        """
        获取最优参数
        :param metric: 优化目标指标
        :return: 最优参数字典
        """
        if not self.results:
            return None
        
        # 按指标排序
        sorted_results = sorted(
            self.results,
            key=lambda x: x.metrics.get(metric, -float('inf')),
            reverse=True
        )
        
        return sorted_results[0].params if sorted_results else None
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """
        将结果转换为DataFrame
        :return: 结果DataFrame
        """
        if not self.results:
            return pd.DataFrame()
        
        data = []
        for result in self.results:
            row = {**result.params, **result.metrics}
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 按总收益率降序排序
        if 'total_return' in df.columns:
            df = df.sort_values('total_return', ascending=False)
        
        df = df.reset_index(drop=True)
        df.insert(0, '排名', range(1, len(df) + 1))
        
        return df
    
    def export_results(self, filepath: str):
        """
        导出优化结果到Excel
        :param filepath: 文件路径
        """
        df = self.get_results_dataframe()
        df.to_excel(filepath, index=False)
        logger.info(f"优化结果已导出到: {filepath}")


class GridSearch(ParameterOptimizer):
    """
    网格搜索优化器
    遍历所有参数组合
    """
    
    def optimize(
        self,
        strategy_name: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        param_grid: Dict[str, List[Any]],
        max_workers: int = 4,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[OptimizationResult]:
        """
        执行网格搜索优化
        :param strategy_name: 策略名称
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param param_grid: 参数网格 {param_name: [value1, value2, ...]}
        :param max_workers: 最大并行工作线程数
        :param progress_callback: 进度回调函数
        :return: 优化结果列表
        """
        logger.info("=" * 60)
        logger.info("开始网格搜索优化")
        logger.info(f"策略: {strategy_name}")
        logger.info(f"股票: {stock_code}")
        logger.info(f"日期: {start_date} ~ {end_date}")
        logger.info(f"参数网格: {param_grid}")
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))
        
        total_combinations = len(param_combinations)
        logger.info(f"参数组合总数: {total_combinations}")
        logger.info("=" * 60)
        
        if total_combinations > 1000:
            logger.warning(f"⚠️  参数组合过多({total_combinations})，建议使用随机搜索")
        
        # 并行执行回测
        self.results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_params = {}
            for combination in param_combinations:
                params = dict(zip(param_names, combination))
                future = executor.submit(
                    self._run_backtest_with_params,
                    strategy_name,
                    stock_code,
                    start_date,
                    end_date,
                    params
                )
                future_to_params[future] = params
            
            # 收集结果
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    completed += 1
                    progress_pct = completed / total_combinations * 100
                    
                    # 进度回调
                    if progress_callback:
                        progress_msg = f"进度: {completed}/{total_combinations} ({progress_pct:.1f}%) - 参数: {params} - 收益: {result.metrics.get('total_return', 0):.2f}%"
                        progress_callback(progress_msg)
                    
                    logger.info(f"✓ [{completed}/{total_combinations}] {params} -> 收益: {result.metrics.get('total_return', 0):.2f}%")
                    
                except Exception as e:
                    logger.error(f"参数{params}执行失败: {e}")
                    completed += 1
        
        logger.info("=" * 60)
        logger.info(f"网格搜索完成，共测试 {len(self.results)} 个参数组合")
        
        # 输出最优参数
        best_params = self.get_best_params()
        if best_params:
            best_result = next(r for r in self.results if r.params == best_params)
            logger.info(f"最优参数: {best_params}")
            logger.info(f"最优收益: {best_result.metrics.get('total_return', 0):.2f}%")
        
        logger.info("=" * 60)
        
        return self.results


class RandomSearch(ParameterOptimizer):
    """
    随机搜索优化器
    随机采样参数空间
    """
    
    def optimize(
        self,
        strategy_name: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        param_distributions: Dict[str, Tuple[Any, Any]],
        n_iter: int = 100,
        max_workers: int = 4,
        random_state: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[OptimizationResult]:
        """
        执行随机搜索优化
        :param strategy_name: 策略名称
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param param_distributions: 参数分布 {param_name: (min, max)}
        :param n_iter: 迭代次数（采样次数）
        :param max_workers: 最大并行工作线程数
        :param random_state: 随机种子
        :param progress_callback: 进度回调函数
        :return: 优化结果列表
        """
        logger.info("=" * 60)
        logger.info("开始随机搜索优化")
        logger.info(f"策略: {strategy_name}")
        logger.info(f"股票: {stock_code}")
        logger.info(f"日期: {start_date} ~ {end_date}")
        logger.info(f"参数范围: {param_distributions}")
        logger.info(f"采样次数: {n_iter}")
        logger.info("=" * 60)
        
        # 设置随机种子
        if random_state is not None:
            random.seed(random_state)
            np.random.seed(random_state)
        
        # 生成随机参数组合
        param_combinations = []
        for _ in range(n_iter):
            params = {}
            for param_name, (min_val, max_val) in param_distributions.items():
                # 判断参数类型
                if isinstance(min_val, int) and isinstance(max_val, int):
                    # 整数参数
                    params[param_name] = random.randint(min_val, max_val)
                else:
                    # 浮点参数
                    params[param_name] = random.uniform(float(min_val), float(max_val))
            
            param_combinations.append(params)
        
        logger.info(f"已生成 {len(param_combinations)} 个随机参数组合")
        
        # 并行执行回测
        self.results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_params = {}
            for params in param_combinations:
                future = executor.submit(
                    self._run_backtest_with_params,
                    strategy_name,
                    stock_code,
                    start_date,
                    end_date,
                    params
                )
                future_to_params[future] = params
            
            # 收集结果
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    completed += 1
                    progress_pct = completed / n_iter * 100
                    
                    # 进度回调
                    if progress_callback:
                        progress_msg = f"进度: {completed}/{n_iter} ({progress_pct:.1f}%) - 参数: {params} - 收益: {result.metrics.get('total_return', 0):.2f}%"
                        progress_callback(progress_msg)
                    
                    logger.info(f"✓ [{completed}/{n_iter}] {params} -> 收益: {result.metrics.get('total_return', 0):.2f}%")
                    
                except Exception as e:
                    logger.error(f"参数{params}执行失败: {e}")
                    completed += 1
        
        logger.info("=" * 60)
        logger.info(f"随机搜索完成，共测试 {len(self.results)} 个参数组合")
        
        # 输出最优参数
        best_params = self.get_best_params()
        if best_params:
            best_result = next(r for r in self.results if r.params == best_params)
            logger.info(f"最优参数: {best_params}")
            logger.info(f"最优收益: {best_result.metrics.get('total_return', 0):.2f}%")
        
        logger.info("=" * 60)
        
        return self.results


class WalkForwardAnalysis:
    """
    Walk-Forward分析
    防止参数过拟合
    """
    
    def __init__(
        self,
        optimizer: ParameterOptimizer,
        train_period_days: int = 180,
        test_period_days: int = 60
    ):
        """
        初始化Walk-Forward分析
        :param optimizer: 参数优化器
        :param train_period_days: 训练期天数
        :param test_period_days: 测试期天数
        """
        self.optimizer = optimizer
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.walk_forward_results = []
        
        logger.info(f"Walk-Forward分析初始化: 训练期={train_period_days}天, 测试期={test_period_days}天")
    
    def run_analysis(
        self,
        strategy_name: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        param_grid: Dict[str, List[Any]]
    ) -> pd.DataFrame:
        """
        执行Walk-Forward分析
        :param strategy_name: 策略名称
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param param_grid: 参数网格
        :return: Walk-Forward结果DataFrame
        """
        logger.info("=" * 60)
        logger.info("开始Walk-Forward分析")
        logger.info(f"策略: {strategy_name}")
        logger.info(f"股票: {stock_code}")
        logger.info(f"总期间: {start_date} ~ {end_date}")
        logger.info("=" * 60)
        
        # 将日期字符串转换为datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        self.walk_forward_results = []
        window_num = 0
        
        # 滚动窗口
        current_train_start = start_dt
        
        while True:
            window_num += 1
            
            # 计算训练期和测试期
            train_start = current_train_start
            train_end = train_start + timedelta(days=self.train_period_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.test_period_days)
            
            # 检查是否超出范围
            if test_end > end_dt:
                logger.info(f"窗口{window_num}: 测试期超出数据范围，停止")
                break
            
            logger.info(f"\n窗口{window_num}:")
            logger.info(f"  训练期: {train_start.strftime('%Y-%m-%d')} ~ {train_end.strftime('%Y-%m-%d')}")
            logger.info(f"  测试期: {test_start.strftime('%Y-%m-%d')} ~ {test_end.strftime('%Y-%m-%d')}")
            
            # 1. 在训练期上优化参数
            if isinstance(self.optimizer, GridSearch):
                self.optimizer.optimize(
                    strategy_name,
                    stock_code,
                    train_start.strftime('%Y-%m-%d'),
                    train_end.strftime('%Y-%m-%d'),
                    param_grid,
                    max_workers=4
                )
            
            # 获取最优参数
            best_params = self.optimizer.get_best_params()
            if best_params is None:
                logger.warning(f"窗口{window_num}: 未找到最优参数，跳过")
                current_train_start = test_start
                continue
            
            logger.info(f"  训练期最优参数: {best_params}")
            
            # 2. 在测试期上验证
            test_result = self.optimizer._run_backtest_with_params(
                strategy_name,
                stock_code,
                test_start.strftime('%Y-%m-%d'),
                test_end.strftime('%Y-%m-%d'),
                best_params
            )
            
            logger.info(f"  测试期收益: {test_result.metrics.get('total_return', 0):.2f}%")
            
            # 保存结果
            self.walk_forward_results.append({
                '窗口': window_num,
                '训练开始': train_start.strftime('%Y-%m-%d'),
                '训练结束': train_end.strftime('%Y-%m-%d'),
                '测试开始': test_start.strftime('%Y-%m-%d'),
                '测试结束': test_end.strftime('%Y-%m-%d'),
                '最优参数': str(best_params),
                '测试收益(%)': test_result.metrics.get('total_return', 0),
                '夏普比率': test_result.metrics.get('sharpe_ratio', 0),
                '最大回撤(%)': test_result.metrics.get('max_drawdown', 0),
            })
            
            # 移动到下一个窗口
            current_train_start = test_start
        
        logger.info("=" * 60)
        logger.info(f"Walk-Forward分析完成，共 {len(self.walk_forward_results)} 个窗口")
        logger.info("=" * 60)
        
        # 转换为DataFrame
        df = pd.DataFrame(self.walk_forward_results)
        
        # 计算平均指标
        if not df.empty:
            avg_return = df['测试收益(%)'].mean()
            avg_sharpe = df['夏普比率'].mean()
            avg_drawdown = df['最大回撤(%)'].mean()
            
            logger.info(f"平均测试收益: {avg_return:.2f}%")
            logger.info(f"平均夏普比率: {avg_sharpe:.3f}")
            logger.info(f"平均最大回撤: {avg_drawdown:.2f}%")
        
        return df
