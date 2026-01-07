"""
机器学习模型训练引擎
支持RandomForest、LSTM、XGBoost策略的模型训练
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, Callable
from datetime import datetime
import os
import pickle
import json

logger = logging.getLogger(__name__)


class MLTrainer:
    """机器学习训练器基类"""
    
    def __init__(self, strategy_name: str, config: Dict[str, Any] = None):
        """
        初始化训练器
        
        :param strategy_name: 策略名称 (RandomForest/LSTM/XGBoost)
        :param config: 配置参数
        """
        self.strategy_name = strategy_name
        self.config = config or {}
        self.model = None
        self.scaler = None
        self.feature_names = []
        
        # 创建模型保存目录
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        logger.info(f"初始化 {strategy_name} 训练器")
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        准备特征数据
        
        :param data: 原始股票数据 (包含 open, high, low, close, volume)
        :return: 特征数据框
        """
        logger.info("开始特征工程...")
        df = data.copy()
        
        # 1. 价格特征
        # 移动平均线
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_60'] = df['close'].rolling(window=60).mean()
        
        # 指数移动平均
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # 2. 动量指标
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ROC (Rate of Change)
        df['roc'] = df['close'].pct_change(periods=10) * 100
        
        # 3. 波动率指标
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # 4. 成交量指标
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # OBV (On Balance Volume)
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        
        # 5. 价格变化特征
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(periods=5)
        df['price_change_10'] = df['close'].pct_change(periods=10)
        
        # 6. 高低点特征
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        
        # 7. 趋势特征
        df['trend_5'] = (df['close'] > df['sma_5']).astype(int)
        df['trend_20'] = (df['close'] > df['sma_20']).astype(int)
        
        # 删除NaN值
        df = df.dropna()
        
        logger.info(f"特征工程完成，生成 {len(df.columns)} 个特征，{len(df)} 条样本")
        
        return df
    
    def create_labels(self, data: pd.DataFrame, horizon: int = 1, threshold: float = 0.02) -> pd.Series:
        """
        创建训练标签
        
        :param data: 特征数据
        :param horizon: 预测时间范围（天）
        :param threshold: 涨跌阈值
        :return: 标签序列 (1: 上涨, 0: 下跌)
        """
        # 计算未来收益
        future_return = data['close'].shift(-horizon) / data['close'] - 1
        
        # 创建二分类标签
        labels = (future_return > threshold).astype(int)
        
        logger.info(f"标签分布 - 上涨: {labels.sum()}, 下跌: {len(labels) - labels.sum()}")
        
        return labels
    
    def split_data(
        self, 
        features: pd.DataFrame, 
        labels: pd.Series,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        分割训练集、验证集、测试集
        
        :param features: 特征数据
        :param labels: 标签数据
        :param train_ratio: 训练集比例
        :param val_ratio: 验证集比例
        :return: (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        n = len(features)
        train_size = int(n * train_ratio)
        val_size = int(n * val_ratio)
        
        # 时间序列数据，按顺序分割
        X_train = features.iloc[:train_size]
        y_train = labels.iloc[:train_size]
        
        X_val = features.iloc[train_size:train_size + val_size]
        y_val = labels.iloc[train_size:train_size + val_size]
        
        X_test = features.iloc[train_size + val_size:]
        y_test = labels.iloc[train_size + val_size:]
        
        logger.info(f"数据分割 - 训练集: {len(X_train)}, 验证集: {len(X_val)}, 测试集: {len(X_test)}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def normalize_features(self, X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame):
        """
        特征标准化
        
        :param X_train: 训练集特征
        :param X_val: 验证集特征
        :param X_test: 测试集特征
        :return: 标准化后的数据
        """
        from sklearn.preprocessing import StandardScaler
        
        self.scaler = StandardScaler()
        
        # 只在训练集上fit
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info("特征标准化完成")
        
        return X_train_scaled, X_val_scaled, X_test_scaled
    
    def evaluate_model(self, y_true, y_pred, set_name: str = "测试集") -> Dict[str, float]:
        """
        评估模型性能
        
        :param y_true: 真实标签
        :param y_pred: 预测标签
        :param set_name: 数据集名称
        :return: 评估指标字典
        """
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
        
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0)
        }
        
        cm = confusion_matrix(y_true, y_pred)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{set_name}评估结果:")
        logger.info(f"  准确率 (Accuracy):  {metrics['accuracy']:.4f}")
        logger.info(f"  精确率 (Precision): {metrics['precision']:.4f}")
        logger.info(f"  召回率 (Recall):    {metrics['recall']:.4f}")
        logger.info(f"  F1分数 (F1-Score):  {metrics['f1']:.4f}")
        logger.info(f"\n混淆矩阵:")
        logger.info(f"  TN: {cm[0,0]:4d}  FP: {cm[0,1]:4d}")
        logger.info(f"  FN: {cm[1,0]:4d}  TP: {cm[1,1]:4d}")
        logger.info(f"{'='*60}")
        
        return metrics
    
    def save_model(self, stock_code: str, metadata: Dict[str, Any] = None):
        """
        保存模型和配置
        
        :param stock_code: 股票代码
        :param metadata: 元数据
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_name = f"{self.strategy_name}_{stock_code}_{timestamp}"
        
        # 保存模型
        model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'strategy_name': self.strategy_name,
                'stock_code': stock_code,
                'timestamp': timestamp,
                'metadata': metadata or {}
            }, f)
        
        logger.info(f"模型已保存: {model_path}")
        
        # 保存配置
        config_path = os.path.join(self.model_dir, f"{model_name}.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({
                'strategy_name': self.strategy_name,
                'stock_code': stock_code,
                'timestamp': timestamp,
                'feature_count': len(self.feature_names),
                'metadata': metadata or {}
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"配置已保存: {config_path}")
        
        return model_path
    
    def train(
        self, 
        data: pd.DataFrame,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        训练模型（子类实现）
        
        :param data: 训练数据
        :param progress_callback: 进度回调函数
        :return: 训练结果
        """
        raise NotImplementedError("子类需要实现 train 方法")


class RandomForestTrainer(MLTrainer):
    """随机森林训练器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('RandomForest', config)
    
    def train(
        self, 
        data: pd.DataFrame,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        训练随机森林模型
        """
        from sklearn.ensemble import RandomForestClassifier
        
        def log(msg):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)
        
        log("🌲 开始训练随机森林模型...")
        
        # 1. 特征工程
        log("📊 步骤 1/6: 特征工程...")
        features_df = self.prepare_features(data)
        
        # 2. 创建标签
        log("🏷️  步骤 2/6: 创建标签...")
        labels = self.create_labels(features_df, horizon=1, threshold=0.02)
        
        # 对齐特征和标签
        features_df = features_df[:-1]  # 移除最后一行（没有标签）
        labels = labels[:-1]
        
        # 选择特征列
        feature_cols = [col for col in features_df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        X = features_df[feature_cols]
        y = labels
        
        self.feature_names = feature_cols
        
        # 3. 分割数据
        log("✂️  步骤 3/6: 分割数据集...")
        train_ratio = self.config.get('train_ratio', 0.8)
        val_ratio = self.config.get('val_ratio', 0.1)
        X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y, train_ratio, val_ratio)
        
        # 4. 特征标准化
        log("🔄 步骤 4/6: 特征标准化...")
        X_train_scaled, X_val_scaled, X_test_scaled = self.normalize_features(X_train, X_val, X_test)
        
        # 5. 训练模型
        log("🚀 步骤 5/6: 训练随机森林...")
        n_estimators = self.config.get('n_estimators', 100)
        max_depth = self.config.get('max_depth', 10)
        
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
            verbose=1
        )
        
        self.model.fit(X_train_scaled, y_train)
        log(f"✅ 模型训练完成！使用 {n_estimators} 棵树，最大深度 {max_depth}")
        
        # 6. 评估模型
        log("📈 步骤 6/6: 评估模型性能...")
        
        y_train_pred = self.model.predict(X_train_scaled)
        train_metrics = self.evaluate_model(y_train, y_train_pred, "训练集")
        
        y_val_pred = self.model.predict(X_val_scaled)
        val_metrics = self.evaluate_model(y_val, y_val_pred, "验证集")
        
        y_test_pred = self.model.predict(X_test_scaled)
        test_metrics = self.evaluate_model(y_test, y_test_pred, "测试集")
        
        # 特征重要性
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        log("\n📊 Top 10 重要特征:")
        for idx, row in feature_importance.head(10).iterrows():
            log(f"  {row['feature']:20s}: {row['importance']:.4f}")
        
        results = {
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
            'test_metrics': test_metrics,
            'feature_importance': feature_importance.to_dict('records'),
            'n_samples': len(data),
            'n_features': len(self.feature_names)
        }
        
        log("\n🎉 随机森林模型训练完成！")
        
        return results


class XGBoostTrainer(MLTrainer):
    """XGBoost训练器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('XGBoost', config)
    
    def train(
        self, 
        data: pd.DataFrame,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        训练XGBoost模型
        """
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("XGBoost未安装，请运行: pip install xgboost")
            raise ImportError("需要安装 xgboost 库")
        
        def log(msg):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)
        
        log("⚡ 开始训练XGBoost模型...")
        
        # 1. 特征工程
        log("📊 步骤 1/6: 特征工程...")
        features_df = self.prepare_features(data)
        
        # 2. 创建标签
        log("🏷️  步骤 2/6: 创建标签...")
        labels = self.create_labels(features_df, horizon=1, threshold=0.02)
        
        # 对齐
        features_df = features_df[:-1]
        labels = labels[:-1]
        
        # 选择特征
        feature_cols = [col for col in features_df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        X = features_df[feature_cols]
        y = labels
        
        self.feature_names = feature_cols
        
        # 3. 分割数据
        log("✂️  步骤 3/6: 分割数据集...")
        train_ratio = self.config.get('train_ratio', 0.8)
        val_ratio = self.config.get('val_ratio', 0.1)
        X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y, train_ratio, val_ratio)
        
        # 4. 特征标准化
        log("🔄 步骤 4/6: 特征标准化...")
        X_train_scaled, X_val_scaled, X_test_scaled = self.normalize_features(X_train, X_val, X_test)
        
        # 5. 训练模型
        log("🚀 步骤 5/6: 训练XGBoost...")
        n_estimators = self.config.get('n_estimators', 100)
        max_depth = self.config.get('max_depth', 5)
        learning_rate = self.config.get('learning_rate', 0.1)
        
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss'
        )
        
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=True
        )
        log(f"✅ 模型训练完成！")
        
        # 6. 评估
        log("📈 步骤 6/6: 评估模型性能...")
        
        y_train_pred = self.model.predict(X_train_scaled)
        train_metrics = self.evaluate_model(y_train, y_train_pred, "训练集")
        
        y_val_pred = self.model.predict(X_val_scaled)
        val_metrics = self.evaluate_model(y_val, y_val_pred, "验证集")
        
        y_test_pred = self.model.predict(X_test_scaled)
        test_metrics = self.evaluate_model(y_test, y_test_pred, "测试集")
        
        # 特征重要性
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        log("\n📊 Top 10 重要特征:")
        for idx, row in feature_importance.head(10).iterrows():
            log(f"  {row['feature']:20s}: {row['importance']:.4f}")
        
        results = {
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
            'test_metrics': test_metrics,
            'feature_importance': feature_importance.to_dict('records'),
            'n_samples': len(data),
            'n_features': len(self.feature_names)
        }
        
        log("\n🎉 XGBoost模型训练完成！")
        
        return results


def create_trainer(strategy_name: str, config: Dict[str, Any] = None) -> MLTrainer:
    """
    创建训练器工厂函数
    
    :param strategy_name: 策略名称
    :param config: 配置参数
    :return: 训练器实例
    """
    if strategy_name == 'RandomForest':
        return RandomForestTrainer(config)
    elif strategy_name == 'XGBoost':
        return XGBoostTrainer(config)
    elif strategy_name == 'LSTM':
        # LSTM训练器暂未实现
        raise NotImplementedError("LSTM训练器开发中，请使用RandomForest或XGBoost")
    else:
        raise ValueError(f"不支持的策略: {strategy_name}")
