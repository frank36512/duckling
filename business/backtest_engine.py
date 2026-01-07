"""
回测引擎模块
基于Backtrader实现策略回测
"""

import logging
import backtrader as bt
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class BacktraderStrategy(bt.Strategy):
    """
    Backtrader策略适配器
    将自定义策略适配到Backtrader框架
    """
    
    params = (
        ('custom_strategy', None),  # 自定义策略实例
    )
    
    def __init__(self):
        """初始化策略"""
        self.custom_strategy = self.params.custom_strategy
        if self.custom_strategy:
            self.custom_strategy.init()
        
        self.order = None
        self.buy_price = None
        self.buy_commission = None
        
        # 交易记录列表（用于K线图标注）
        self.trade_records = []
        
        logger.info(f"Backtrader策略初始化: {self.custom_strategy.name if self.custom_strategy else 'None'}")
    
    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_commission = order.executed.comm
                
                # 记录买入信号
                self.trade_records.append({
                    'date': self.data.datetime.date(0),
                    'price': order.executed.price,
                    'type': 'buy',
                    'size': order.executed.size
                })
                
                logger.info(f"买入执行: 价格={order.executed.price:.2f}, "
                           f"数量={order.executed.size:.0f}, "
                           f"手续费={order.executed.comm:.2f}")
            else:
                profit = order.executed.price - self.buy_price
                
                # 记录卖出信号
                self.trade_records.append({
                    'date': self.data.datetime.date(0),
                    'price': order.executed.price,
                    'type': 'sell',
                    'size': order.executed.size,
                    'profit': profit
                })
                
                logger.info(f"卖出执行: 价格={order.executed.price:.2f}, "
                           f"数量={order.executed.size:.0f}, "
                           f"盈亏={profit:.2f}, "
                           f"手续费={order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"订单取消/拒绝: {order.status}")
        
        self.order = None
    
    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return
        
        logger.info(f"交易利润: 毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}")
    
    def next(self):
        """策略执行"""
        if not self.custom_strategy:
            return
        
        # 检查是否有未完成的订单
        if self.order:
            return
        
        # 构建当前数据DataFrame
        data_len = len(self.data)
        closes = [self.data.close[-i] for i in range(min(data_len, 100), 0, -1)]
        
        current_data = pd.DataFrame({
            'close': closes
        })
        
        # 调用自定义策略生成信号
        signal = self.custom_strategy.next(current_data)
        
        # 执行交易
        if signal['signal'] == 'buy':
            if not self.position:
                # 计算可购买数量（使用95%的可用资金）
                cash = self.broker.get_cash() * 0.95
                size = int(cash / self.data.close[0] / 100) * 100  # 按100股整数倍买入
                
                if size > 0:
                    self.order = self.buy(size=size)
                    logger.info(f"买入信号: {signal['reason']}, 数量={size}")
        
        elif signal['signal'] == 'sell':
            if self.position:
                self.order = self.sell(size=self.position.size)
                logger.info(f"卖出信号: {signal['reason']}")


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测引擎
        :param config: 回测配置
        """
        self.config = config
        
        # 回测参数
        self.initial_cash = config.get('initial_cash', 100000.0)
        self.commission = config.get('commission', 0.0003)
        self.stamp_duty = config.get('stamp_duty', 0.001)
        self.slippage = config.get('slippage', 0.001)
        
        # 创建Backtrader引擎
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(self.initial_cash)
        
        # 设置手续费（买入和卖出）
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturns')
        
        # 添加观察器
        self.cerebro.addobserver(bt.observers.Value)
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        logger.info(f"回测引擎初始化完成: 初始资金={self.initial_cash}, "
                   f"手续费={self.commission}, 印花税={self.stamp_duty}")
    
    def add_data(self, data: pd.DataFrame, name: str = 'stock'):
        """
        添加数据到回测引擎
        :param data: DataFrame包含OHLCV数据
        :param name: 数据名称
        """
        try:
            # 确保数据格式正确
            if not all(col in data.columns for col in ['open', 'high', 'low', 'close', 'vol']):
                raise ValueError("数据必须包含: open, high, low, close, vol 列")
            
            # 确保有日期索引
            if 'trade_date' in data.columns:
                data = data.set_index('trade_date')
            
            # 确保索引是datetime类型
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)
            
            # 重命名列以匹配Backtrader要求
            data = data.rename(columns={
                'vol': 'volume',
                'amount': 'openinterest'
            })
            
            # 创建Backtrader数据源
            bt_data = bt.feeds.PandasData(
                dataname=data,
                datetime=None,  # 使用索引作为日期
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1  # 不使用openinterest
            )
            
            self.cerebro.adddata(bt_data, name=name)
            logger.info(f"添加数据成功: {name}, 数据量={len(data)}")
            
        except Exception as e:
            logger.error(f"添加数据失败: {e}")
            raise
    
    def add_strategy(self, strategy):
        """
        添加策略到回测引擎
        :param strategy: 策略实例或策略类
        """
        try:
            import backtrader as bt
            
            # 判断是否为Backtrader原生策略类
            if isinstance(strategy, type) and issubclass(strategy, bt.Strategy):
                # 直接添加Backtrader策略类
                self.cerebro.addstrategy(strategy)
                logger.info(f"添加Backtrader策略成功: {strategy.__name__}")
            else:
                # 使用适配器包装自定义策略实例
                self.cerebro.addstrategy(BacktraderStrategy, custom_strategy=strategy)
                logger.info(f"添加自定义策略成功: {strategy.name}")
        except Exception as e:
            logger.error(f"添加策略失败: {e}")
            raise
    
    def run(self) -> Dict[str, Any]:
        """
        运行回测
        :return: 回测结果字典
        """
        try:
            logger.info("="*60)
            logger.info("开始回测...")
            logger.info(f"初始资金: {self.initial_cash:.2f}")
            
            # 运行回测
            results = self.cerebro.run()
            
            # 获取最终资金
            final_value = self.cerebro.broker.getvalue()
            
            logger.info(f"最终资金: {final_value:.2f}")
            logger.info("回测完成")
            logger.info("="*60)
            
            # 提取分析结果
            strategy_results = results[0]
            
            # 提取交易记录（如果策略是BacktraderStrategy）
            trade_records = []
            if hasattr(strategy_results, 'trade_records'):
                trade_records = strategy_results.trade_records
                logger.info(f"提取到 {len(trade_records)} 条交易记录")
            
            # 提取资金曲线数据
            equity_curve_data = []
            dates = []
            
            try:
                # 从TimeReturn分析器提取每日收益率
                timereturns = strategy_results.analyzers.timereturns.get_analysis()
                
                if timereturns:
                    # 按日期排序
                    sorted_dates = sorted(timereturns.keys())
                    
                    # 计算每日资金
                    current_value = self.initial_cash
                    for date in sorted_dates:
                        dates.append(date)
                        daily_return = timereturns[date]
                        current_value = current_value * (1 + daily_return)
                        equity_curve_data.append(current_value)
                    
                    logger.info(f"从TimeReturn提取到 {len(equity_curve_data)} 个资金数据点")
                else:
                    logger.warning("TimeReturn分析器返回空数据")
                
            except Exception as e:
                logger.warning(f"提取资金曲线数据失败: {e}")
            
            # 构建结果字典
            result = {
                'initial_cash': self.initial_cash,
                'final_value': final_value,
                'total_return': final_value - self.initial_cash,
                'return_rate': (final_value - self.initial_cash) / self.initial_cash,
                'equity_curve': equity_curve_data,
                'dates': dates,
                'trade_records': trade_records,  # 添加交易记录
            }
            
            # 添加分析器结果
            try:
                # 夏普比率
                sharpe = strategy_results.analyzers.sharpe.get_analysis()
                sharpe_value = sharpe.get('sharperatio', None)
                result['sharpe_ratio'] = sharpe_value if sharpe_value is not None else 0.0
                
                # 最大回撤
                drawdown = strategy_results.analyzers.drawdown.get_analysis()
                result['max_drawdown'] = drawdown.get('max', {}).get('drawdown', 0)
                result['max_drawdown_period'] = drawdown.get('max', {}).get('len', 0)
                
                # 收益率
                returns = strategy_results.analyzers.returns.get_analysis()
                result['total_return_rate'] = returns.get('rtot', 0)
                result['avg_return_rate'] = returns.get('ravg', 0)
                
                # 交易分析
                trades = strategy_results.analyzers.trades.get_analysis()
                result['total_trades'] = trades.get('total', {}).get('closed', 0)
                result['won_trades'] = trades.get('won', {}).get('total', 0)
                result['lost_trades'] = trades.get('lost', {}).get('total', 0)
                
                # 计算胜率
                if result['total_trades'] > 0:
                    result['win_rate'] = result['won_trades'] / result['total_trades']
                else:
                    result['win_rate'] = 0
                
                # 盈亏比
                if result['lost_trades'] > 0:
                    avg_win = trades.get('won', {}).get('pnl', {}).get('average', 0)
                    avg_loss = abs(trades.get('lost', {}).get('pnl', {}).get('average', 0))
                    result['profit_loss_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
                else:
                    result['profit_loss_ratio'] = 0
                
            except Exception as e:
                logger.warning(f"提取分析结果时出错: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"回测运行失败: {e}")
            raise
    
    def plot(self, save_path: str = None):
        """
        绘制回测结果图表
        :param save_path: 保存路径，如果为None则显示图表
        """
        try:
            # Backtrader内置绘图
            self.cerebro.plot(style='candlestick')
            
            if save_path:
                logger.info(f"图表已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"绘制图表失败: {e}")


class BacktestResult:
    """回测结果类"""
    
    def __init__(self, result: Dict[str, Any]):
        """
        初始化回测结果
        :param result: 回测结果字典
        """
        self.result = result
        
        # 构建资金曲线DataFrame
        self.equity_curve = None
        if 'equity_curve' in result and 'dates' in result:
            try:
                equity_data = result['equity_curve']
                dates = result['dates']
                if equity_data and dates and len(equity_data) == len(dates):
                    # 确保日期是datetime类型
                    dates_converted = pd.to_datetime(dates)
                    self.equity_curve = pd.Series(equity_data, index=dates_converted)
                    logger.info(f"资金曲线构建成功，共 {len(self.equity_curve)} 个数据点")
                else:
                    logger.warning(f"数据长度不匹配: equity={len(equity_data) if equity_data else 0}, dates={len(dates) if dates else 0}")
            except Exception as e:
                logger.error(f"构建资金曲线失败: {e}", exc_info=True)
        
        # 存储OHLC数据（用于K线图）
        self.ohlc_data = None
        if 'ohlc_data' in result:
            self.ohlc_data = result['ohlc_data']
            logger.info(f"OHLC数据已加载，共 {len(self.ohlc_data) if self.ohlc_data is not None else 0} 条记录")
        
        # 存储股票代码
        self.stock_code = result.get('stock_code', 'Unknown')
        
        # 存储交易记录（用于K线图标注）
        self.trade_records = result.get('trade_records', [])
        logger.info(f"交易记录已加载，共 {len(self.trade_records)} 条")
    
    @property
    def total_return(self) -> float:
        """总收益率"""
        return self.result.get('return_rate', 0) * 100
    
    @property
    def annual_return(self) -> float:
        """年化收益率"""
        # 简化计算，假设一年250个交易日
        if self.equity_curve is not None and len(self.equity_curve) > 0:
            days = len(self.equity_curve)
            years = days / 250
            if years > 0:
                return (pow(1 + self.result.get('return_rate', 0), 1/years) - 1) * 100
        return self.total_return
    
    @property
    def sharpe_ratio(self) -> float:
        """夏普比率"""
        return self.result.get('sharpe_ratio', 0)
    
    @property
    def max_drawdown(self) -> float:
        """最大回撤"""
        return abs(self.result.get('max_drawdown', 0))
    
    @property
    def total_trades(self) -> int:
        """总交易次数"""
        return self.result.get('total_trades', 0)
    
    @property
    def win_rate(self) -> float:
        """胜率"""
        return self.result.get('win_rate', 0) * 100
    
    @property
    def profit_factor(self) -> float:
        """盈亏比"""
        return self.result.get('profit_loss_ratio', 0)
    
    @property
    def final_value(self) -> float:
        """最终资金"""
        return self.result.get('final_value', 0)
    
    def get_summary(self) -> str:
        """获取摘要（兼容旧代码）"""
        return self.summary()
    
    def summary(self) -> str:
        """
        生成回测摘要
        :return: 摘要字符串
        """
        lines = [
            "="*60,
            "回测结果摘要",
            "="*60,
            f"初始资金: ¥{self.result['initial_cash']:,.2f}",
            f"最终资金: ¥{self.result['final_value']:,.2f}",
            f"总收益: ¥{self.result['total_return']:,.2f}",
            f"收益率: {self.result['return_rate']*100:.2f}%",
            "",
            "风险指标:",
            f"  最大回撤: {self.result.get('max_drawdown', 0):.2f}%",
            f"  夏普比率: {self.result.get('sharpe_ratio', 0):.4f}",
            "",
            "交易统计:",
            f"  总交易次数: {self.result.get('total_trades', 0)}",
            f"  盈利次数: {self.result.get('won_trades', 0)}",
            f"  亏损次数: {self.result.get('lost_trades', 0)}",
            f"  胜率: {self.result.get('win_rate', 0)*100:.2f}%",
            f"  盈亏比: {self.result.get('profit_loss_ratio', 0):.2f}",
            "="*60
        ]
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        :return: 结果字典
        """
        return self.result.copy()
    
    def save(self, filepath: str):
        """
        保存结果到文件
        :param filepath: 文件路径
        """
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"回测结果已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
