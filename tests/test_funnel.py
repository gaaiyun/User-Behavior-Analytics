"""
测试漏斗分析模块
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from funnel_analyzer import FunnelAnalyzer, create_sample_funnel_data


@pytest.fixture
def sample_data():
    """创建示例数据"""
    data = []
    base_time = datetime(2024, 1, 1)
    
    # 创建 100 个用户的行为数据
    for user_id in range(1, 101):
        user_time = base_time + timedelta(hours=user_id)
        
        # 所有用户都有 page_view
        data.append({'user_id': user_id, 'event': 'page_view', 'timestamp': user_time})
        
        # 80% 用户 sign_up
        if user_id <= 80:
            user_time += timedelta(minutes=10)
            data.append({'user_id': user_id, 'event': 'sign_up', 'timestamp': user_time})
            
            # 60% 用户 add_to_cart
            if user_id <= 60:
                user_time += timedelta(minutes=20)
                data.append({'user_id': user_id, 'event': 'add_to_cart', 'timestamp': user_time})
                
                # 40% 用户 checkout
                if user_id <= 40:
                    user_time += timedelta(minutes=10)
                    data.append({'user_id': user_id, 'event': 'checkout', 'timestamp': user_time})
                    
                    # 30% 用户 purchase
                    if user_id <= 30:
                        user_time += timedelta(minutes=5)
                        data.append({'user_id': user_id, 'event': 'purchase', 'timestamp': user_time})
    
    return pd.DataFrame(data)


@pytest.fixture
def funnel_analyzer(sample_data):
    """创建漏斗分析器"""
    analyzer = FunnelAnalyzer(sample_data)
    analyzer.define_funnel(['page_view', 'sign_up', 'add_to_cart', 'checkout', 'purchase'])
    return analyzer


class TestFunnelAnalyzer:
    """测试漏斗分析器"""
    
    def test_initialization(self, sample_data):
        """测试初始化"""
        analyzer = FunnelAnalyzer(sample_data)
        assert analyzer.data is not None
        assert len(analyzer.data) > 0
    
    def test_define_funnel(self, sample_data):
        """测试定义漏斗步骤"""
        analyzer = FunnelAnalyzer(sample_data)
        steps = ['page_view', 'sign_up', 'purchase']
        analyzer.define_funnel(steps)
        assert analyzer.funnel_steps == steps
    
    def test_calculate_conversion(self, funnel_analyzer):
        """测试转化率计算"""
        result = funnel_analyzer.calculate_conversion()
        
        assert result is not None
        assert len(result) == 5  # 5 个步骤
        assert 'step' in result.columns
        assert 'count' in result.columns
        assert 'conversion_rate' in result.columns
        
        # 第一步应该是 100%
        assert result.iloc[0]['conversion_rate'] == 100.0
        
        # 第一步用户数应该是 100
        assert result.iloc[0]['count'] == 100
        
        # 最后一步用户数应该是 30
        assert result.iloc[-1]['count'] == 30
    
    def test_analyze_dropoff(self, funnel_analyzer):
        """测试流失分析"""
        funnel_analyzer.calculate_conversion()
        dropoff = funnel_analyzer.analyze_dropoff()
        
        assert dropoff is not None
        assert len(dropoff) == 5
        assert 'dropoff_count' in dropoff.columns
        assert 'dropoff_rate' in dropoff.columns
        
        # 第一步流失应该是 0
        assert dropoff.iloc[0]['dropoff_count'] == 0
    
    def test_get_funnel_summary(self, funnel_analyzer):
        """测试漏斗摘要"""
        summary = funnel_analyzer.get_funnel_summary()
        
        assert summary is not None
        assert 'total_users' in summary
        assert 'final_users' in summary
        assert 'overall_conversion_rate' in summary
        assert 'max_dropoff_step' in summary
        
        assert summary['total_users'] == 100
        assert summary['final_users'] == 30
        assert summary['overall_conversion_rate'] == 30.0
    
    def test_plot_funnel(self, funnel_analyzer):
        """测试漏斗图生成"""
        fig = funnel_analyzer.plot_funnel()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_empty_funnel(self, sample_data):
        """测试空漏斗"""
        analyzer = FunnelAnalyzer(sample_data)
        
        with pytest.raises(ValueError):
            analyzer.calculate_conversion()
    
    def test_single_step_funnel(self, sample_data):
        """测试单步骤漏斗"""
        analyzer = FunnelAnalyzer(sample_data)
        analyzer.define_funnel(['page_view'])
        result = analyzer.calculate_conversion()
        
        assert len(result) == 1
        assert result.iloc[0]['count'] == 100
        assert result.iloc[0]['conversion_rate'] == 100.0


class TestCreateSampleFunnelData:
    """测试示例数据生成"""
    
    def test_create_sample_data(self):
        """测试创建示例数据"""
        df = create_sample_funnel_data(100)
        
        assert df is not None
        assert len(df) > 0
        assert 'user_id' in df.columns
        assert 'event' in df.columns
        assert 'timestamp' in df.columns
    
    def test_sample_data_events(self):
        """测试示例数据事件类型"""
        df = create_sample_funnel_data(100)
        
        expected_events = ['page_view', 'sign_up', 'add_to_cart', 'checkout', 'purchase']
        assert all(event in df['event'].unique() for event in expected_events)
    
    def test_sample_data_user_count(self):
        """测试示例数据用户数"""
        df = create_sample_funnel_data(100)
        
        assert df['user_id'].nunique() == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
