"""
机器学习策略模块
使用机器学习算法进行股票预测和交易
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from core.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class MLStrategyBase(StrategyBase):
    """机器学习策略基类"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化ML策略
        
        :param params: 策略参数
        """
        default_params = {
            'lookback_period': 60,  # 回看周期
            'prediction_horizon': 1,  # 预测周期
            'feature_columns': ['close', 'volume', 'high', 'low'],  # 特征列
            'train_test_split': 0.8,  # 训练集比例
            'retrain_frequency': 20,  # 重新训练频率（天）
        }
        
        if params:
            default_params.update(params)
        
        # 初始化父类（传入策略名称和参数）
        super().__init__(self.__class__.__name__, default_params)
        
        self.model = None
        self.last_train_date = None
        self.feature_scaler = None
        self.label_scaler = None
        
        logger.info(f"机器学习策略初始化: {self.__class__.__name__}")
    
    def init(self):
        """
        策略初始化方法（backtrader要求）
        在回测开始前调用
        """
        logger.info(f"{self.name} 策略初始化完成")
        pass
    
    @abstractmethod
    def build_model(self):
        """构建模型（子类实现）"""
        pass
    
    @abstractmethod
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """训练模型（子类实现）"""
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测（子类实现）"""
        pass
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        准备特征
        
        :param data: 原始数据
        :return: 特征数据
        """
        features = pd.DataFrame(index=data.index)
        
        # 价格特征
        features['close'] = data['close']
        features['open'] = data['open']
        features['high'] = data['high']
        features['low'] = data['low']
        features['volume'] = data['volume']
        
        # 技术指标特征
        # 移动平均线
        for period in [5, 10, 20, 60]:
            features[f'ma_{period}'] = data['close'].rolling(window=period).mean()
        
        # 价格变化率
        for period in [1, 5, 10]:
            features[f'return_{period}'] = data['close'].pct_change(period)
        
        # 波动率
        features['volatility_10'] = data['close'].pct_change().rolling(window=10).std()
        features['volatility_20'] = data['close'].pct_change().rolling(window=20).std()
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        features['macd'] = exp1 - exp2
        features['macd_signal'] = features['macd'].ewm(span=9, adjust=False).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        
        # 布林带
        ma20 = data['close'].rolling(window=20).mean()
        std20 = data['close'].rolling(window=20).std()
        features['bb_upper'] = ma20 + 2 * std20
        features['bb_lower'] = ma20 - 2 * std20
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / ma20
        
        # 成交量特征
        features['volume_ma_5'] = data['volume'].rolling(window=5).mean()
        features['volume_ma_20'] = data['volume'].rolling(window=20).mean()
        features['volume_ratio'] = data['volume'] / features['volume_ma_20']
        
        # 删除NaN
        features = features.dropna()
        
        return features
    
    def prepare_labels(self, data: pd.DataFrame) -> pd.Series:
        """
        准备标签（未来收益率）
        
        :param data: 原始数据
        :return: 标签数据
        """
        horizon = self.params['prediction_horizon']
        labels = data['close'].pct_change(horizon).shift(-horizon)
        return labels
    
    def should_retrain(self, current_date: datetime) -> bool:
        """
        判断是否需要重新训练
        
        :param current_date: 当前日期
        :return: 是否需要重新训练
        """
        if self.last_train_date is None:
            return True
        
        days_since_train = (current_date - self.last_train_date).days
        return days_since_train >= self.params['retrain_frequency']
    
    def next(self, data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        策略逻辑（每个bar调用）
        
        :param data: 历史数据（可选，如果没有提供则使用self.data）
        :return: 信号字典
        """
        # 使用传入的数据或self.data
        historical_data = data if data is not None else self.data
        
        # 获取历史数据
        lookback = self.params['lookback_period']
        
        if len(historical_data) < lookback + 30:  # 需要足够的数据
            return {
                'signal': 'hold',
                'price': historical_data['close'].iloc[-1] if len(historical_data) > 0 else 0,
                'reason': '数据不足'
            }
        
        # 准备数据
        historical_data = historical_data.tail(lookback + 30)
        
        # 检查是否需要重新训练
        current_date = historical_data.index[-1]
        if self.should_retrain(current_date):
            logger.info(f"重新训练模型: {current_date}")
            success = self._train_on_data(historical_data)
            if success:
                self.last_train_date = current_date
        
        # 如果模型未训练，返回持有
        if self.model is None:
            return {
                'signal': 'hold',
                'price': historical_data['close'].iloc[-1],
                'reason': '模型未训练'
            }
        
        # 准备特征
        features = self.prepare_features(historical_data)
        if len(features) == 0:
            return {
                'signal': 'hold',
                'price': historical_data['close'].iloc[-1],
                'reason': '特征准备失败'
            }
        
        # 获取最新特征
        latest_features = features.iloc[-1:].values
        
        # 特征标准化
        if self.feature_scaler is not None:
            latest_features = self.feature_scaler.transform(latest_features)
        
        # 预测
        prediction = self.predict(latest_features)[0]
        
        # 当前价格
        current_price = historical_data['close'].iloc[-1]
        
        # 根据预测结果生成信号
        threshold = 0.01  # 1%的阈值
        
        if prediction > threshold:
            return {
                'signal': 'buy',
                'price': current_price,
                'reason': f'预测收益: {prediction:.4f} > {threshold}',
                'prediction': prediction
            }
        elif prediction < -threshold:
            return {
                'signal': 'sell',
                'price': current_price,
                'reason': f'预测收益: {prediction:.4f} < {-threshold}',
                'prediction': prediction
            }
        else:
            return {
                'signal': 'hold',
                'price': current_price,
                'reason': f'预测收益: {prediction:.4f} 在阈值内',
                'prediction': prediction
            }
    
    def _train_on_data(self, data: pd.DataFrame) -> bool:
        """
        在数据上训练模型
        
        :param data: 训练数据
        :return: 训练是否成功
        """
        try:
            # 准备特征和标签
            features = self.prepare_features(data)
            labels = self.prepare_labels(data)
            
            # 对齐特征和标签
            valid_indices = features.index.intersection(labels.index)
            features = features.loc[valid_indices]
            labels = labels.loc[valid_indices]
            
            # 删除NaN
            mask = ~labels.isna()
            features = features[mask]
            labels = labels[mask]
            
            if len(features) < 50:  # 至少需要50个样本
                logger.warning("训练样本不足")
                return False
            
            # 分割训练集和测试集
            split_idx = int(len(features) * self.params['train_test_split'])
            X_train = features.iloc[:split_idx].values
            y_train = labels.iloc[:split_idx].values
            X_test = features.iloc[split_idx:].values
            y_test = labels.iloc[split_idx:].values
            
            # 特征标准化
            from sklearn.preprocessing import StandardScaler
            self.feature_scaler = StandardScaler()
            X_train = self.feature_scaler.fit_transform(X_train)
            X_test = self.feature_scaler.transform(X_test)
            
            # 构建和训练模型
            if self.model is None:
                self.build_model()
            
            self.train_model(X_train, y_train)
            
            # 评估模型
            train_pred = self.predict(X_train)
            test_pred = self.predict(X_test)
            
            train_mse = np.mean((train_pred - y_train) ** 2)
            test_mse = np.mean((test_pred - y_test) ** 2)
            
            logger.info(f"模型训练完成 - 训练MSE: {train_mse:.6f}, 测试MSE: {test_mse:.6f}")
            return True
        
        except Exception as e:
            logger.error(f"模型训练失败: {e}", exc_info=True)
            return False


class RandomForestStrategy(MLStrategyBase):
    """随机森林策略"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化随机森林策略
        
        :param params: 策略参数
        """
        default_params = {
            'n_estimators': 100,  # 树的数量
            'max_depth': 10,  # 最大深度
            'min_samples_split': 5,  # 最小分裂样本数
            'random_state': 42,
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(default_params)
        
        logger.info("随机森林策略初始化完成")
    
    def build_model(self):
        """构建随机森林模型"""
        try:
            from sklearn.ensemble import RandomForestRegressor
            
            self.model = RandomForestRegressor(
                n_estimators=self.params['n_estimators'],
                max_depth=self.params['max_depth'],
                min_samples_split=self.params['min_samples_split'],
                random_state=self.params['random_state'],
                n_jobs=-1
            )
            
            logger.info("随机森林模型构建完成")
        
        except ImportError:
            logger.error("未安装 scikit-learn 库，请运行: pip install scikit-learn")
            raise
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """训练随机森林模型"""
        self.model.fit(X_train, y_train)
        logger.info("随机森林模型训练完成")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """使用随机森林进行预测"""
        return self.model.predict(X)


class LSTMStrategy(MLStrategyBase):
    """LSTM深度学习策略"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化LSTM策略
        
        :param params: 策略参数
        """
        default_params = {
            'lstm_units': 50,  # LSTM单元数
            'dropout': 0.2,  # Dropout率
            'epochs': 50,  # 训练轮数
            'batch_size': 32,  # 批次大小
            'sequence_length': 20,  # 序列长度
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(default_params)
        
        logger.info("LSTM策略初始化完成")
    
    def build_model(self):
        """构建LSTM模型"""
        try:
            from tensorflow import keras
            from tensorflow.keras import layers
            
            model = keras.Sequential([
                layers.LSTM(
                    self.params['lstm_units'],
                    return_sequences=True,
                    input_shape=(self.params['sequence_length'], self.n_features)
                ),
                layers.Dropout(self.params['dropout']),
                layers.LSTM(self.params['lstm_units']),
                layers.Dropout(self.params['dropout']),
                layers.Dense(1)
            ])
            
            model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            
            self.model = model
            logger.info("LSTM模型构建完成")
        
        except ImportError:
            logger.error("未安装 tensorflow 库，请运行: pip install tensorflow")
            raise
    
    def prepare_sequences(self, features: np.ndarray, labels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备序列数据
        
        :param features: 特征数组
        :param labels: 标签数组
        :return: (序列特征, 序列标签)
        """
        seq_length = self.params['sequence_length']
        X, y = [], []
        
        for i in range(len(features) - seq_length):
            X.append(features[i:i + seq_length])
            y.append(labels[i + seq_length])
        
        return np.array(X), np.array(y)
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """训练LSTM模型"""
        # 保存特征数量
        self.n_features = X_train.shape[1]
        
        # 如果模型未构建，先构建
        if self.model is None:
            self.build_model()
        
        # 准备序列数据
        X_seq, y_seq = self.prepare_sequences(X_train, y_train)
        
        # 训练模型
        self.model.fit(
            X_seq, y_seq,
            epochs=self.params['epochs'],
            batch_size=self.params['batch_size'],
            validation_split=0.1,
            verbose=0
        )
        
        logger.info("LSTM模型训练完成")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """使用LSTM进行预测"""
        seq_length = self.params['sequence_length']
        
        # 如果数据不足一个序列长度，返回0
        if len(X) < seq_length:
            return np.zeros(len(X))
        
        # 准备序列
        sequences = []
        for i in range(len(X) - seq_length + 1):
            sequences.append(X[i:i + seq_length])
        
        sequences = np.array(sequences)
        
        # 预测
        predictions = self.model.predict(sequences, verbose=0).flatten()
        
        # 补齐前面的0
        result = np.zeros(len(X))
        result[seq_length - 1:] = predictions
        
        return result


class XGBoostStrategy(MLStrategyBase):
    """XGBoost策略"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化XGBoost策略
        
        :param params: 策略参数
        """
        default_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': 42,
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(default_params)
        
        logger.info("XGBoost策略初始化完成")
    
    def build_model(self):
        """构建XGBoost模型"""
        try:
            import xgboost as xgb
            
            self.model = xgb.XGBRegressor(
                n_estimators=self.params['n_estimators'],
                max_depth=self.params['max_depth'],
                learning_rate=self.params['learning_rate'],
                random_state=self.params['random_state'],
                n_jobs=-1
            )
            
            logger.info("XGBoost模型构建完成")
        
        except ImportError:
            logger.error("未安装 xgboost 库，请运行: pip install xgboost")
            raise
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """训练XGBoost模型"""
        self.model.fit(X_train, y_train)
        logger.info("XGBoost模型训练完成")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """使用XGBoost进行预测"""
        return self.model.predict(X)


# 使用示例
if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建策略
    rf_strategy = RandomForestStrategy({
        'lookback_period': 60,
        'n_estimators': 100
    })
    
    print(f"随机森林策略创建成功: {rf_strategy.name}")
