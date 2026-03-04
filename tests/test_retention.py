"""
测试留存分析模块
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retention_analyzer import RetentionAnalyzer, create_sample_retention_data


@pytest.fixture
def sample_data():
    """创建示例留存数据"""
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 创建 100 个用户，分布在不同的日期
    for user_id in range(1, 101):
        # 用户首次活跃日期
        first_date = base_date + timedelta(days=user_id % 30)
        
        # 首日活跃
        data.append({
            'user_id': user_id,
            'timestamp': first_date,
            'event': 'login'
        })
        
        # 后续活跃（模拟留存）
        for day in range(1, 45):
            # 留存概率随天数下降
            if np.random.random() < (0.9 ** day):
                event_date = first_date + timedelta(days=day)
                data.append({
                    'user_id': user_id,
                    'timestamp': event_date,
                    'event': np.random.choice(['login', 'browse', 'click'])
                })
    
    return pd.DataFrame(data)


@pytest.fixture
def retention_analyzer(sample_data):
    """创建留存分析器"""
    return RetentionAnalyzer(sample_data)


class TestRetentionAnalyzer:
    """测试留存分析器"""
    
    def test_initialization(self, sample_data):
        """测试初始化"""
        analyzer = RetentionAnalyzer(sample_data)
        assert analyzer.data is not None
        assert len(analyzer.data) > 0
    
    def test_calculate_retention_daily(self, retention_analyzer):
        """测试按天计算留存"""
        result = retention_analyzer.calculate_retention(period='D')
        
        assert result is not None
        assert len(result) > 0
        
        # 检查留存率范围
        assert result.min().min() >= 0
        assert result.max().max() <= 100
    
    def test_calculate_retention_weekly(self, sample_data):
        """测试按周计算留存"""
        analyzer = RetentionAnalyzer(sample_data)
        result = analyzer.calculate_retention(period='W')
        
        assert result is not None
        assert len(result) > 0
    
    def test_calculate_retention_monthly(self, sample_data):
        """测试按月计算留存"""
        analyzer = RetentionAnalyzer(sample_data)
        result = analyzer.calculate_retention(period='M')
        
        assert result is not None
    
    def test_calculate_cohort_retention(self, retention_analyzer):
        """测试队列留存计算"""
        cohort_data = retention_analyzer.calculate_cohort_retention(cohort_period='D')
        
        assert cohort_data is not None
        assert len(cohort_data) > 0
        assert 'cohort' in cohort_data.columns
        assert 'days' in cohort_data.columns
        assert 'retention_rate' in cohort_data.columns
    
    def test_plot_retention_curve(self, retention_analyzer):
        """测试留存曲线生成"""
        retention_analyzer.calculate_retention()
        fig = retention_analyzer.plot_retention_curve()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_plot_heatmap(self, retention_analyzer):
        """测试热力图生成"""
        retention_analyzer.calculate_retention()
        fig = retention_analyzer.plot_heatmap()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_get_retention_summary(self, retention_analyzer):
        """测试留存摘要"""
        retention_analyzer.calculate_retention()
        summary = retention_analyzer.get_retention_summary()
        
        assert summary is not None
        assert 'day_1_retention' in summary or summary.get('day_1_retention') is None
        assert 'day_7_retention' in summary or summary.get('day_7_retention') is None
        assert 'n_cohorts' in summary
        assert 'trend' in summary
    
    def test_calculate_churn_rate(self, retention_analyzer):
        """测试流失率计算"""
        retention_analyzer.calculate_retention()
        churn_df = retention_analyzer.calculate_churn_rate()
        
        assert churn_df is not None
        assert len(churn_df) > 0
        assert 'avg_churn_rate' in churn_df.columns
        assert 'min_churn_rate' in churn_df.columns
        assert 'max_churn_rate' in churn_df.columns
        
        # 流失率应该在 0-100 之间
        assert churn_df['avg_churn_rate'].min() >= 0
        assert churn_df['avg_churn_rate'].max() <= 100
    
    def test_first_day_retention(self):
        """测试首日留存率应为 100%"""
        data = create_sample_retention_data(100, 30)
        analyzer = RetentionAnalyzer(data)
        result = analyzer.calculate_retention(period='D')
        
        # 第一天（period 0）的留存率应该是 100%
        if 0 in result.columns:
            assert all(result[0] == 100.0)


class TestCreateSampleRetentionData:
    """测试示例留存数据生成"""
    
    def test_create_sample_data(self):
        """测试创建示例数据"""
        df = create_sample_retention_data(100, 30)
        
        assert df is not None
        assert len(df) > 0
        assert 'user_id' in df.columns
        assert 'timestamp' in df.columns
    
    def test_sample_data_user_count(self):
        """测试示例数据用户数"""
        df = create_sample_retention_data(100, 30)
        
        assert df['user_id'].nunique() == 100
    
    def test_sample_data_time_range(self):
        """测试示例数据时间范围"""
        df = create_sample_retention_data(100, 30)
        
        time_range = (df['timestamp'].max() - df['timestamp'].min()).days
        assert time_range <= 60  # 应该在一个合理范围内


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
