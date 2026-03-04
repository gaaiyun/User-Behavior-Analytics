"""
测试路径分析模块
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from path_analyzer import PathAnalyzer, create_sample_path_data


@pytest.fixture
def sample_data():
    """创建示例数据"""
    data = []
    base_time = datetime(2024, 1, 1)
    
    # 创建有规律的用户路径
    paths = [
        ['home', 'product_page', 'cart', 'checkout', 'purchase'],  # 完整路径
        ['home', 'product_page', 'cart'],  # 加购未完成
        ['home', 'search', 'product_page', 'cart', 'checkout'],  # 搜索路径
        ['home', 'about', 'contact'],  # 信息浏览
        ['home', 'product_page', 'home'],  # 跳出
    ]
    
    for user_id, path in enumerate(paths * 20, 1):  # 每个路径 20 个用户
        user_time = base_time + timedelta(hours=user_id)
        for event in path:
            data.append({
                'user_id': user_id,
                'event': event,
                'timestamp': user_time
            })
            user_time += timedelta(minutes=5)
    
    return pd.DataFrame(data)


@pytest.fixture
def path_analyzer(sample_data):
    """创建路径分析器"""
    return PathAnalyzer(sample_data)


class TestPathAnalyzer:
    """测试路径分析器"""
    
    def test_initialization(self, sample_data):
        """测试初始化"""
        analyzer = PathAnalyzer(sample_data)
        assert analyzer.data is not None
        assert len(analyzer.data) > 0
    
    def test_extract_user_paths(self, path_analyzer):
        """测试提取用户路径"""
        paths = path_analyzer.extract_user_paths()
        
        assert paths is not None
        assert len(paths) > 0
        assert isinstance(paths, dict)
        
        # 检查路径格式
        for user_id, path in paths.items():
            assert isinstance(path, list)
            assert len(path) > 0
    
    def test_extract_user_paths_max_steps(self, path_analyzer):
        """测试最大路径长度限制"""
        paths = path_analyzer.extract_user_paths(max_steps=3)
        
        for user_id, path in paths.items():
            assert len(path) <= 3
    
    def test_build_path_graph(self, path_analyzer):
        """测试构建路径图"""
        G = path_analyzer.build_path_graph(min_support=5)
        
        assert G is not None
        assert G.number_of_nodes() > 0
        assert G.number_of_edges() > 0
        
        # 检查图是否被缓存
        assert path_analyzer.path_graph is not None
    
    def test_find_common_paths(self, path_analyzer):
        """测试查找常见路径"""
        common = path_analyzer.find_common_paths(top_n=5, min_length=2)
        
        assert common is not None
        assert len(common) <= 5
        assert 'path' in common.columns
        assert 'count' in common.columns
        assert 'percentage' in common.columns
    
    def test_plot_sankey(self, path_analyzer):
        """测试桑基图生成"""
        fig = path_analyzer.plot_sankey(top_n=10)
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_plot_path_heatmap(self, path_analyzer):
        """测试热力图生成"""
        fig = path_analyzer.plot_path_heatmap(top_n=15)
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_calculate_path_metrics(self, path_analyzer):
        """测试路径指标计算"""
        metrics = path_analyzer.calculate_path_metrics()
        
        assert metrics is not None
        assert 'avg_path_length' in metrics
        assert 'unique_paths' in metrics
        assert 'n_nodes' in metrics
        assert 'n_edges' in metrics
        assert 'graph_density' in metrics
        assert 'key_nodes' in metrics
        
        assert metrics['avg_path_length'] > 0
        assert metrics['n_nodes'] > 0
        assert metrics['n_edges'] >= 0
    
    def test_empty_data(self):
        """测试空数据"""
        empty_data = pd.DataFrame(columns=['user_id', 'event', 'timestamp'])
        analyzer = PathAnalyzer(empty_data)
        
        paths = analyzer.extract_user_paths()
        assert len(paths) == 0


class TestCreateSamplePathData:
    """测试示例路径数据生成"""
    
    def test_create_sample_data(self):
        """测试创建示例数据"""
        df = create_sample_path_data(100)
        
        assert df is not None
        assert len(df) > 0
        assert 'user_id' in df.columns
        assert 'event' in df.columns
        assert 'timestamp' in df.columns
    
    def test_sample_data_events(self):
        """测试示例数据事件类型"""
        df = create_sample_path_data(100)
        
        expected_events = ['home', 'product_page', 'search', 'cart', 'checkout', 'purchase']
        assert all(event in df['event'].unique() for event in expected_events)
    
    def test_sample_data_user_count(self):
        """测试示例数据用户数"""
        df = create_sample_path_data(100)
        
        assert df['user_id'].nunique() == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
