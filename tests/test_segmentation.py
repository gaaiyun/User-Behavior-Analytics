"""
测试用户分群模块
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from segmentation_analyzer import UserSegmentation, create_sample_segmentation_data


@pytest.fixture
def sample_data():
    """创建示例分群数据"""
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 创建不同类型的用户
    for user_id in range(1, 101):
        if user_id <= 20:
            # 高价值用户：频繁活跃
            n_events = np.random.randint(20, 40)
            days_range = 30
        elif user_id <= 60:
            # 普通用户
            n_events = np.random.randint(5, 15)
            days_range = 60
        else:
            # 流失风险用户
            n_events = np.random.randint(1, 5)
            days_range = 90
        
        for _ in range(n_events):
            event_date = base_date + timedelta(days=np.random.randint(0, days_range))
            data.append({
                'user_id': user_id,
                'timestamp': event_date,
                'event': np.random.choice(['login', 'browse', 'purchase']),
                'value': np.random.exponential(50) if np.random.random() < 0.3 else 0
            })
    
    return pd.DataFrame(data)


@pytest.fixture
def segmentation_analyzer(sample_data):
    """创建分群分析器"""
    return UserSegmentation(sample_data)


class TestUserSegmentation:
    """测试用户分群器"""
    
    def test_initialization(self, sample_data):
        """测试初始化"""
        analyzer = UserSegmentation(sample_data)
        assert analyzer.data is not None
        assert len(analyzer.data) > 0
    
    def test_create_rfm_features(self, segmentation_analyzer):
        """测试创建 RFM 特征"""
        features = segmentation_analyzer.create_rfm_features()
        
        assert features is not None
        assert len(features) > 0
        assert 'user_id' in features.columns
        assert 'recency' in features.columns
        assert 'frequency' in features.columns
        assert 'monetary' in features.columns
    
    def test_create_behavior_features(self, segmentation_analyzer):
        """测试创建行为特征"""
        features = segmentation_analyzer.create_behavior_features()
        
        assert features is not None
        assert len(features) > 0
    
    def test_cluster_users_kmeans(self, segmentation_analyzer):
        """测试 K-Means 聚类"""
        segmentation_analyzer.create_rfm_features()
        clustered = segmentation_analyzer.cluster_users(n_clusters=5, method='kmeans')
        
        assert 'cluster' in clustered.columns
        assert clustered['cluster'].nunique() <= 5
        assert clustered['cluster'].min() >= 0
    
    def test_cluster_users_dbscan(self, segmentation_analyzer):
        """测试 DBSCAN 聚类"""
        segmentation_analyzer.create_rfm_features()
        clustered = segmentation_analyzer.cluster_users(method='dbscan')
        
        assert 'cluster' in clustered.columns
    
    def test_invalid_cluster_method(self, segmentation_analyzer):
        """测试无效的聚类方法"""
        segmentation_analyzer.create_rfm_features()
        
        with pytest.raises(ValueError):
            segmentation_analyzer.cluster_users(method='invalid')
    
    def test_analyze_clusters(self, segmentation_analyzer):
        """测试聚类分析"""
        segmentation_analyzer.cluster_users(n_clusters=4)
        stats = segmentation_analyzer.analyze_clusters()
        
        assert stats is not None
        assert len(stats) > 0
        assert 'user_count' in stats.columns
        assert 'percentage' in stats.columns
        
        # 百分比总和应该接近 100
        assert abs(stats['percentage'].sum() - 100) < 1
    
    def test_plot_cluster_distribution(self, segmentation_analyzer):
        """测试聚类分布图"""
        segmentation_analyzer.cluster_users(n_clusters=4)
        fig = segmentation_analyzer.plot_cluster_distribution()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_plot_cluster_radar(self, segmentation_analyzer):
        """测试聚类雷达图"""
        segmentation_analyzer.cluster_users(n_clusters=4)
        fig = segmentation_analyzer.plot_cluster_radar(features=['recency', 'frequency', 'monetary'])
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_assign_user_tags(self, segmentation_analyzer):
        """测试用户标签分配"""
        segmentation_analyzer.cluster_users(n_clusters=4)
        tags = segmentation_analyzer.assign_user_tags()
        
        assert tags is not None
        assert isinstance(tags, dict)
        
        # 每个聚类都应该有标签
        for cluster_id in range(segmentation_analyzer.user_features['cluster'].nunique()):
            assert cluster_id in tags
            assert len(tags[cluster_id]) > 0
    
    def test_rfm_feature_values(self, segmentation_analyzer):
        """测试 RFM 特征值合理性"""
        features = segmentation_analyzer.create_rfm_features()
        
        # Recency 应该是非负数
        assert (features['recency'] >= 0).all()
        
        # Frequency 应该是正数
        assert (features['frequency'] > 0).all()
        
        # Monetary 应该是非负数
        assert (features['monetary'] >= 0).all()


class TestCreateSampleSegmentationData:
    """测试示例分群数据生成"""
    
    def test_create_sample_data(self):
        """测试创建示例数据"""
        df = create_sample_segmentation_data(100)
        
        assert df is not None
        assert len(df) > 0
        assert 'user_id' in df.columns
        assert 'timestamp' in df.columns
        assert 'event' in df.columns
    
    def test_sample_data_user_count(self):
        """测试示例数据用户数"""
        df = create_sample_segmentation_data(100)
        
        assert df['user_id'].nunique() == 100
    
    def test_sample_data_has_value(self):
        """测试示例数据包含价值字段"""
        df = create_sample_segmentation_data(100)
        
        assert 'value' in df.columns


class TestEdgeCases:
    """测试边界情况"""
    
    def test_single_user(self):
        """测试单个用户"""
        data = pd.DataFrame({
            'user_id': [1],
            'timestamp': [datetime(2024, 1, 1)],
            'event': ['login'],
            'value': [0]
        })
        
        analyzer = UserSegmentation(data)
        features = analyzer.create_rfm_features()
        
        assert len(features) == 1
    
    def test_single_cluster(self):
        """测试单聚类情况"""
        data = pd.DataFrame({
            'user_id': list(range(1, 11)),
            'timestamp': [datetime(2024, 1, 1)] * 10,
            'event': ['login'] * 10,
            'value': [0] * 10
        })
        
        analyzer = UserSegmentation(data)
        clustered = analyzer.cluster_users(n_clusters=1)
        
        assert clustered['cluster'].nunique() == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
