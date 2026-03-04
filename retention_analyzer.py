"""
用户留存分析模块
功能：次日/7 日/30 日留存分析、留存曲线、队列分析
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class RetentionAnalyzer:
    """用户留存分析器"""
    
    def __init__(self, data: pd.DataFrame, date_col: str = 'timestamp', user_col: str = 'user_id'):
        """
        初始化留存分析器
        
        Args:
            data: 用户行为数据 DataFrame
            date_col: 日期列名
            user_col: 用户 ID 列名
        """
        self.data = data.copy()
        self.data[date_col] = pd.to_datetime(self.data[date_col])
        self.date_col = date_col
        self.user_col = user_col
        self.retention_data = None
        self.cohort_data = None
        
    def calculate_retention(self, period: str = 'D') -> pd.DataFrame:
        """
        计算留存率
        
        Args:
            period: 时间周期 ('D'=天，'W'=周，'M'=月)
            
        Returns:
            留存率 DataFrame
        """
        # 获取每个用户的首次活跃时间
        first_active = self.data.groupby(self.user_col)[self.date_col].min().reset_index()
        first_active.columns = [self.user_col, 'cohort_date']
        
        # 按周期分组
        first_active['cohort_period'] = first_active['cohort_date'].dt.to_period(period)
        
        # 合并回原始数据
        data_with_cohort = self.data.merge(first_active, on=self.user_col)
        
        # 计算每个事件距离首次活跃的时间
        data_with_cohort['period_number'] = (
            (data_with_cohort[self.date_col].dt.to_period(period) - 
             data_with_cohort['cohort_period']).apply(lambda x: x.n if hasattr(x, 'n') else 0)
        )
        
        # 计算每个队列在每个周期的用户数
        cohort_counts = data_with_cohort.groupby(['cohort_period', 'period_number'])[self.user_col].nunique().reset_index()
        cohort_counts.columns = ['cohort_period', 'period_number', 'user_count']
        
        # 获取每个队列的初始用户数
        cohort_sizes = cohort_counts[cohort_counts['period_number'] == 0][['cohort_period', 'user_count']]
        cohort_sizes.columns = ['cohort_period', 'cohort_size']
        
        # 计算留存率
        retention = cohort_counts.merge(cohort_sizes, on='cohort_period')
        retention['retention_rate'] = retention['user_count'] / retention['cohort_size'] * 100
        
        # 转换为宽格式
        retention_pivot = retention.pivot(index='cohort_period', columns='period_number', values='retention_rate')
        
        self.retention_data = retention_pivot
        return retention_pivot
    
    def calculate_cohort_retention(self, cohort_period: str = 'M') -> pd.DataFrame:
        """
        计算队列留存
        
        Args:
            cohort_period: 队列周期 ('D'=天，'W'=周，'M'=月)
            
        Returns:
            队列留存 DataFrame
        """
        # 获取每个用户的首次活跃日期
        first_active = self.data.groupby(self.user_col)[self.date_col].min().reset_index()
        first_active.columns = [self.user_col, 'first_date']
        
        # 按指定周期分组
        first_active['cohort'] = first_active['first_date'].dt.to_period(cohort_period)
        
        # 合并回原始数据
        data_merged = self.data.merge(first_active, on=self.user_col)
        
        # 计算每个事件距离首次活跃的天数
        data_merged['days_since_first'] = (
            data_merged[self.date_col].dt.date - data_merged['first_date'].dt.date
        ).apply(lambda x: x.days if hasattr(x, 'days') else 0)
        
        # 计算每个队列在每个天数的用户数
        cohort_data = data_merged.groupby(['cohort', 'days_since_first'])[self.user_col].nunique().reset_index()
        cohort_data.columns = ['cohort', 'days', 'users']
        
        # 获取队列大小
        cohort_sizes = cohort_data[cohort_data['days'] == 0][['cohort', 'users']]
        cohort_sizes.columns = ['cohort', 'cohort_size']
        
        # 计算留存率
        cohort_data = cohort_data.merge(cohort_sizes, on='cohort')
        cohort_data['retention_rate'] = cohort_data['users'] / cohort_data['cohort_size'] * 100
        
        self.cohort_data = cohort_data
        return cohort_data
    
    def plot_retention_curve(self, title: str = "用户留存曲线") -> go.Figure:
        """
        绘制留存曲线
        
        Args:
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if self.retention_data is None:
            self.calculate_retention()
        
        fig = go.Figure()
        
        # 为每个队列添加一条线
        for cohort in self.retention_data.index:
            fig.add_trace(go.Scatter(
                x=self.retention_data.columns,
                y=self.retention_data.loc[cohort],
                mode='lines+markers',
                name=str(cohort),
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="周期",
            yaxis_title="留存率 (%)",
            yaxis=dict(range=[0, 100]),
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig
    
    def plot_heatmap(self, title: str = "留存热力图") -> go.Figure:
        """
        绘制留存热力图
        
        Args:
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if self.retention_data is None:
            self.calculate_retention()
        
        fig = go.Figure(data=go.Heatmap(
            z=self.retention_data.values,
            x=self.retention_data.columns,
            y=[str(c) for c in self.retention_data.index],
            colorscale='RdYlGn',
            showscale=True,
            text=self.retention_data.values.round(1),
            texttemplate='%{text}%',
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="周期",
            yaxis_title="队列",
            height=400 + len(self.retention_data.index) * 30
        )
        
        return fig
    
    def get_retention_summary(self) -> Dict:
        """
        获取留存分析摘要
        
        Returns:
            包含关键指标的字典
        """
        if self.retention_data is None:
            self.calculate_retention()
        
        # 计算平均次日、7 日、30 日留存
        day_1_retention = self.retention_data.get(1, pd.Series()).mean() if 1 in self.retention_data.columns else None
        day_7_retention = self.retention_data.get(7, pd.Series()).mean() if 7 in self.retention_data.columns else None
        day_30_retention = self.retention_data.get(30, pd.Series()).mean() if 30 in self.retention_data.columns else None
        
        # 整体趋势
        if len(self.retention_data.columns) > 1:
            first_period_avg = self.retention_data.iloc[:, 0].mean()
            last_period_avg = self.retention_data.iloc[:, -1].mean()
            trend = "上升" if last_period_avg > first_period_avg * 0.5 else "下降"
        else:
            trend = "数据不足"
        
        return {
            'day_1_retention': day_1_retention,
            'day_7_retention': day_7_retention,
            'day_30_retention': day_30_retention,
            'n_cohorts': len(self.retention_data.index),
            'max_periods': len(self.retention_data.columns),
            'trend': trend
        }
    
    def calculate_churn_rate(self) -> pd.DataFrame:
        """
        计算流失率
        
        Returns:
            流失率 DataFrame
        """
        if self.retention_data is None:
            self.calculate_retention()
        
        churn_data = 100 - self.retention_data
        
        # 计算每个周期的流失率
        churn_summary = pd.DataFrame({
            'period': churn_data.columns,
            'avg_churn_rate': churn_data.mean().values,
            'min_churn_rate': churn_data.min().values,
            'max_churn_rate': churn_data.max().values
        })
        
        return churn_summary


def create_sample_retention_data(n_users: int = 1000, n_days: int = 60) -> pd.DataFrame:
    """
    创建示例留存数据
    
    Args:
        n_users: 用户数量
        n_days: 天数
        
    Returns:
        示例数据 DataFrame
    """
    np.random.seed(42)
    
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 为每个用户生成首次活跃日期
    user_first_dates = {
        user_id: base_date + timedelta(days=np.random.randint(0, n_days // 2))
        for user_id in range(1, n_users + 1)
    }
    
    # 为每个用户生成后续活跃记录
    for user_id, first_date in user_first_dates.items():
        # 首日活跃
        data.append({
            'user_id': user_id,
            'timestamp': first_date,
            'event': 'login'
        })
        
        # 后续活跃（留存率随时间下降）
        current_date = first_date + timedelta(days=1)
        day = 1
        
        while day < n_days:
            # 留存概率随天数下降
            retention_prob = 0.95 ** day
            
            if np.random.random() < retention_prob:
                # 用户活跃
                n_events = np.random.randint(1, 5)
                for _ in range(n_events):
                    data.append({
                        'user_id': user_id,
                        'timestamp': current_date + timedelta(hours=np.random.randint(0, 24)),
                        'event': np.random.choice(['login', 'browse', 'click', 'purchase'])
                    })
            
            current_date += timedelta(days=1)
            day += 1
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # 测试代码
    print("测试留存分析模块...")
    df = create_sample_retention_data(500, 45)
    analyzer = RetentionAnalyzer(df)
    
    print("\n留存数据:")
    retention = analyzer.calculate_retention(period='D')
    print(retention.head(10))
    
    print("\n留存摘要:")
    summary = analyzer.get_retention_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
