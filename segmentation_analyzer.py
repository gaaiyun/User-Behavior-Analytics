"""
用户分群模块
功能：基于行为的聚类分析、用户画像、标签体系
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class UserSegmentation:
    """用户分群分析器"""
    
    def __init__(self, data: pd.DataFrame, user_col: str = 'user_id'):
        """
        初始化用户分群器
        
        Args:
            data: 用户行为数据 DataFrame
            user_col: 用户 ID 列名
        """
        self.data = data.copy()
        self.user_col = user_col
        self.user_features = None
        self.cluster_labels = None
        self.scaler = StandardScaler()
        
    def create_rfm_features(self) -> pd.DataFrame:
        """
        创建 RFM 特征（Recency, Frequency, Monetary）
        
        Returns:
            包含 RFM 特征的 DataFrame
        """
        if 'timestamp' not in self.data.columns:
            raise ValueError("数据需要包含 timestamp 列")
        
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        reference_date = self.data['timestamp'].max()
        
        # Recency: 最近一次活跃距离参考日期的天数
        recency = self.data.groupby(self.user_col)['timestamp'].max().apply(
            lambda x: (reference_date - x).days
        )
        
        # Frequency: 活跃次数
        frequency = self.data.groupby(self.user_col).size()
        
        # Monetary: 如果有金额列则计算，否则用事件数代替
        if 'value' in self.data.columns:
            monetary = self.data.groupby(self.user_col)['value'].sum()
        else:
            monetary = frequency
        
        self.user_features = pd.DataFrame({
            'user_id': recency.index,
            'recency': recency.values,
            'frequency': frequency.values,
            'monetary': monetary.values
        })
        
        return self.user_features
    
    def create_behavior_features(self, event_types: List[str] = None) -> pd.DataFrame:
        """
        创建行为特征
        
        Args:
            event_types: 要统计的事件类型列表
            
        Returns:
            包含行为特征的 DataFrame
        """
        if event_types is None:
            event_types = self.data['event'].unique().tolist()
        
        # 统计每个用户每种事件的发生次数
        event_counts = self.data.groupby([self.user_col, 'event']).size().unstack(fill_value=0)
        
        # 确保所有事件类型都存在
        for event in event_types:
            if event not in event_counts.columns:
                event_counts[event] = 0
        
        # 计算其他特征
        user_stats = self.data.groupby(self.user_col).agg({
            'timestamp': ['min', 'max', 'count']
        })
        user_stats.columns = ['first_active', 'last_active', 'total_events']
        user_stats['active_days'] = (
            user_stats['last_active'] - user_stats['first_active']
        ).dt.days + 1
        
        # 合并特征
        if self.user_features is None:
            self.user_features = user_stats.reset_index()
        else:
            self.user_features = self.user_features.merge(
                user_stats.reset_index(), 
                on='user_id', 
                how='outer'
            )
        
        # 添加事件计数
        self.user_features = self.user_features.merge(
            event_counts.reset_index(), 
            on='user_id', 
            how='outer'
        )
        
        return self.user_features
    
    def cluster_users(self, n_clusters: int = 5, method: str = 'kmeans') -> pd.DataFrame:
        """
        对用户进行聚类
        
        Args:
            n_clusters: 聚类数量
            method: 聚类方法 ('kmeans' 或 'dbscan')
            
        Returns:
            包含聚类标签的 DataFrame
        """
        if self.user_features is None:
            self.create_rfm_features()
        
        # 选择数值特征
        feature_cols = self.user_features.select_dtypes(include=[np.number]).columns.tolist()
        if 'user_id' in feature_cols:
            feature_cols.remove('user_id')
        
        X = self.user_features[feature_cols].fillna(0)
        
        # 标准化
        X_scaled = self.scaler.fit_transform(X)
        
        # 聚类
        if method == 'kmeans':
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = model.fit_predict(X_scaled)
        elif method == 'dbscan':
            model = DBSCAN(eps=0.5, min_samples=5)
            labels = model.fit_predict(X_scaled)
        else:
            raise ValueError(f"不支持的聚类方法：{method}")
        
        self.user_features['cluster'] = labels
        self.cluster_labels = labels
        
        return self.user_features
    
    def analyze_clusters(self) -> pd.DataFrame:
        """
        分析聚类结果
        
        Returns:
            包含各聚类统计信息的 DataFrame
        """
        if 'cluster' not in self.user_features.columns:
            self.cluster_users()
        
        # 数值特征
        numeric_cols = self.user_features.select_dtypes(include=[np.number]).columns.tolist()
        if 'cluster' in numeric_cols:
            numeric_cols.remove('cluster')
        if 'user_id' in numeric_cols:
            numeric_cols.remove('user_id')
        
        cluster_stats = self.user_features.groupby('cluster')[numeric_cols].mean()
        cluster_stats['user_count'] = self.user_features.groupby('cluster').size()
        cluster_stats['percentage'] = (
            cluster_stats['user_count'] / len(self.user_features) * 100
        )
        
        return cluster_stats
    
    def plot_cluster_distribution(self, title: str = "用户分群分布") -> go.Figure:
        """
        绘制聚类分布图
        
        Args:
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if 'cluster' not in self.user_features.columns:
            self.cluster_users()
        
        cluster_counts = self.user_features['cluster'].value_counts().sort_index()
        
        fig = go.Figure(data=[
            go.Bar(
                x=[f"Cluster {c}" for c in cluster_counts.index],
                y=cluster_counts.values,
                marker_color=px.colors.qualitative.Set2,
                text=cluster_counts.values,
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title="聚类",
            yaxis_title="用户数",
            height=400
        )
        
        return fig
    
    def plot_cluster_radar(self, features: List[str] = None, title: str = "聚类特征雷达图") -> go.Figure:
        """
        绘制聚类特征雷达图
        
        Args:
            features: 要显示的特征列表
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if 'cluster' not in self.user_features.columns:
            self.cluster_users()
        
        if features is None:
            features = ['recency', 'frequency', 'monetary']
        
        # 获取每个聚类的特征均值
        cluster_stats = self.user_features.groupby('cluster')[features].mean()
        
        fig = go.Figure()
        
        for cluster_id in cluster_stats.index:
            values = cluster_stats.loc[cluster_id].values.tolist()
            values.append(values[0])  # 闭合雷达图
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=features + [features[0]],
                fill='toself',
                name=f'Cluster {cluster_id}'
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(self.user_features[features].max())])
            ),
            showlegend=True,
            title=title,
            height=500
        )
        
        return fig
    
    def assign_user_tags(self) -> Dict[int, List[str]]:
        """
        为用户分配标签
        
        Returns:
            聚类 ID 到标签列表的映射
        """
        if 'cluster' not in self.user_features.columns:
            self.cluster_users()
        
        cluster_stats = self.analyze_clusters()
        
        tags = {}
        for cluster_id in cluster_stats.index:
            cluster_tags = []
            
            # 基于 RFM 特征打标签
            if cluster_stats.loc[cluster_id, 'recency'] < 7:
                cluster_tags.append('活跃用户')
            elif cluster_stats.loc[cluster_id, 'recency'] > 30:
                cluster_tags.append('流失风险')
            
            if cluster_stats.loc[cluster_id, 'frequency'] > cluster_stats['frequency'].mean():
                cluster_tags.append('高频用户')
            
            if 'monetary' in cluster_stats.columns:
                if cluster_stats.loc[cluster_id, 'monetary'] > cluster_stats['monetary'].mean():
                    cluster_tags.append('高价值用户')
            
            if cluster_stats.loc[cluster_id, 'user_count'] < len(self.user_features) * 0.1:
                cluster_tags.append('小众群体')
            
            tags[cluster_id] = cluster_tags if cluster_tags else ['普通用户']
        
        return tags


def create_sample_segmentation_data(n_users: int = 500) -> pd.DataFrame:
    """
    创建示例分群数据
    
    Args:
        n_users: 用户数量
        
    Returns:
        示例数据 DataFrame
    """
    np.random.seed(42)
    
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 创建不同类型的用户
    user_types = ['high_value', 'regular', 'at_risk', 'new']
    user_type_probs = [0.2, 0.5, 0.2, 0.1]
    
    for user_id in range(1, n_users + 1):
        user_type = np.random.choice(user_types, p=user_type_probs)
        
        if user_type == 'high_value':
            # 高价值用户：频繁活跃，最近活跃
            n_events = np.random.randint(20, 50)
            days_range = 30
        elif user_type == 'regular':
            # 普通用户：中等活跃
            n_events = np.random.randint(5, 20)
            days_range = 60
        elif user_type == 'at_risk':
            # 流失风险用户：很久没活跃
            n_events = np.random.randint(1, 5)
            days_range = 90
        else:  # new
            # 新用户：最近加入，活跃次数少
            n_events = np.random.randint(1, 5)
            days_range = 7
        
        # 生成事件
        for _ in range(n_events):
            event_date = base_date + timedelta(days=np.random.randint(0, days_range))
            data.append({
                'user_id': user_id,
                'timestamp': event_date + timedelta(hours=np.random.randint(0, 24)),
                'event': np.random.choice(['login', 'browse', 'click', 'purchase', 'share']),
                'value': np.random.exponential(50) if np.random.random() < 0.3 else 0
            })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # 测试代码
    print("测试用户分群模块...")
    df = create_sample_segmentation_data(300)
    analyzer = UserSegmentation(df)
    
    print("\n创建 RFM 特征...")
    features = analyzer.create_rfm_features()
    print(features.head())
    
    print("\n聚类分析...")
    clustered = analyzer.cluster_users(n_clusters=4)
    print(clustered[['user_id', 'recency', 'frequency', 'cluster']].head(10))
    
    print("\n聚类统计...")
    stats = analyzer.analyze_clusters()
    print(stats)
