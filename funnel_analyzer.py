"""
用户漏斗分析模块
功能：转化漏斗分析、流失分析、步骤转化率计算
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Tuple
from datetime import datetime


class FunnelAnalyzer:
    """用户漏斗分析器"""
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化漏斗分析器
        
        Args:
            data: 用户行为数据 DataFrame，需包含 user_id, event, timestamp 列
        """
        self.data = data.copy()
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.funnel_steps = []
        self.conversion_data = None
        
    def define_funnel(self, steps: List[str]) -> 'FunnelAnalyzer':
        """
        定义漏斗步骤
        
        Args:
            steps: 漏斗步骤列表，按顺序排列
            
        Returns:
            self
        """
        self.funnel_steps = steps
        return self
    
    def calculate_conversion(self, time_window: int = 24) -> pd.DataFrame:
        """
        计算漏斗转化率
        
        Args:
            time_window: 时间窗口（小时），默认24小时
            
        Returns:
            包含各步骤用户数和转化率的 DataFrame
        """
        if not self.funnel_steps:
            raise ValueError("请先定义漏斗步骤")
        
        # 按用户分组，排序事件
        user_events = self.data.sort_values(['user_id', 'timestamp'])
        
        # 计算每个用户在每个步骤的到达情况
        conversion_results = []
        
        for step_idx, step in enumerate(self.funnel_steps):
            # 获取完成到当前步骤的用户
            if step_idx == 0:
                users_at_step = user_events[user_events['event'] == step]['user_id'].unique()
            else:
                # 需要按顺序完成前面所有步骤
                users_at_previous = conversion_results[-1]['users']
                
                # 筛选这些用户
                user_data = user_events[user_events['user_id'].isin(users_at_previous)]
                
                # 检查是否按顺序完成当前步骤
                users_at_step = []
                for user_id in users_at_previous:
                    user_timeline = user_data[user_data['user_id'] == user_id]
                    step_events = user_timeline[user_timeline['event'].isin(self.funnel_steps[:step_idx+1])]
                    
                    if len(step_events) >= step_idx + 1:
                        # 检查顺序
                        event_sequence = step_events['event'].tolist()
                        if event_sequence[:step_idx+1] == self.funnel_steps[:step_idx+1]:
                            users_at_step.append(user_id)
            
            users_at_step = list(set(users_at_step))
            count = len(users_at_step)
            
            # 计算转化率
            if step_idx == 0:
                conversion_rate = 100.0
                relative_rate = 100.0
            else:
                prev_count = conversion_results[-1]['count']
                conversion_rate = (count / len(conversion_results[0]['users']) * 100) if conversion_results[0]['count'] > 0 else 0
                relative_rate = (count / prev_count * 100) if prev_count > 0 else 0
            
            conversion_results.append({
                'step': step,
                'step_index': step_idx,
                'count': count,
                'users': users_at_step,
                'conversion_rate': conversion_rate,
                'relative_rate': relative_rate
            })
        
        self.conversion_data = pd.DataFrame(conversion_results)
        return self.conversion_data[['step', 'count', 'conversion_rate', 'relative_rate']]
    
    def analyze_dropoff(self) -> pd.DataFrame:
        """
        分析流失情况
        
        Returns:
            包含各步骤流失用户数和流失率的 DataFrame
        """
        if self.conversion_data is None:
            self.calculate_conversion()
        
        dropoff_data = []
        for idx, row in self.conversion_data.iterrows():
            if idx == 0:
                dropoff = 0
                dropoff_rate = 0
            else:
                prev_count = self.conversion_data.iloc[idx-1]['count']
                dropoff = prev_count - row['count']
                dropoff_rate = (dropoff / prev_count * 100) if prev_count > 0 else 0
            
            dropoff_data.append({
                'step': row['step'],
                'dropoff_count': dropoff,
                'dropoff_rate': dropoff_rate
            })
        
        return pd.DataFrame(dropoff_data)
    
    def plot_funnel(self, title: str = "用户转化漏斗") -> go.Figure:
        """
        绘制漏斗图
        
        Args:
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if self.conversion_data is None:
            self.calculate_conversion()
        
        fig = go.Figure(go.Funnel(
            y=self.conversion_data['step'].tolist(),
            x=self.conversion_data['count'].tolist(),
            textposition="inside",
            textinfo="value+percent initial",
            opacity=0.85,
            marker={
                "color": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"][:len(self.funnel_steps)],
                "line": {"width": [2, 2, 2, 2, 2, 2]}
            },
            connector={"line": {"color": "royalblue", "dash": "dot", "width": 2}}
        ))
        
        fig.update_layout(
            title=title,
            height=400 + len(self.funnel_steps) * 30,
            font=dict(size=12)
        )
        
        return fig
    
    def get_funnel_summary(self) -> Dict:
        """
        获取漏斗分析摘要
        
        Returns:
            包含关键指标的字典
        """
        if self.conversion_data is None:
            self.calculate_conversion()
        
        total_users = self.conversion_data.iloc[0]['count']
        final_users = self.conversion_data.iloc[-1]['count']
        overall_conversion = (final_users / total_users * 100) if total_users > 0 else 0
        
        # 找到最大流失步骤
        dropoff_data = self.analyze_dropoff()
        max_dropoff_idx = dropoff_data['dropoff_count'].idxmax()
        max_dropoff_step = dropoff_data.iloc[max_dropoff_idx]['step']
        
        return {
            'total_users': total_users,
            'final_users': final_users,
            'overall_conversion_rate': overall_conversion,
            'max_dropoff_step': max_dropoff_step,
            'steps_count': len(self.funnel_steps)
        }


def create_sample_funnel_data(n_users: int = 1000) -> pd.DataFrame:
    """
    创建示例漏斗数据
    
    Args:
        n_users: 用户数量
        
    Returns:
        示例数据 DataFrame
    """
    np.random.seed(42)
    
    events = ['page_view', 'sign_up', 'add_to_cart', 'checkout', 'purchase']
    data = []
    
    base_time = datetime(2024, 1, 1)
    
    for user_id in range(1, n_users + 1):
        user_time = base_time + pd.Timedelta(hours=np.random.randint(0, 720))
        
        # 页面浏览 - 所有用户
        data.append({
            'user_id': user_id,
            'event': 'page_view',
            'timestamp': user_time
        })
        
        # 注册 - 60% 用户
        if np.random.random() < 0.6:
            user_time += pd.Timedelta(minutes=np.random.randint(5, 60))
            data.append({
                'user_id': user_id,
                'event': 'sign_up',
                'timestamp': user_time
            })
            
            # 加入购物车 - 40% 注册用户
            if np.random.random() < 0.4:
                user_time += pd.Timedelta(minutes=np.random.randint(10, 120))
                data.append({
                    'user_id': user_id,
                    'event': 'add_to_cart',
                    'timestamp': user_time
                })
                
                # 结账 - 70% 加购用户
                if np.random.random() < 0.7:
                    user_time += pd.Timedelta(minutes=np.random.randint(5, 30))
                    data.append({
                        'user_id': user_id,
                        'event': 'checkout',
                        'timestamp': user_time
                    })
                    
                    # 购买 - 80% 结账用户
                    if np.random.random() < 0.8:
                        user_time += pd.Timedelta(minutes=np.random.randint(1, 15))
                        data.append({
                            'user_id': user_id,
                            'event': 'purchase',
                            'timestamp': user_time
                        })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # 测试代码
    print("测试漏斗分析模块...")
    df = create_sample_funnel_data(500)
    analyzer = FunnelAnalyzer(df)
    analyzer.define_funnel(['page_view', 'sign_up', 'add_to_cart', 'checkout', 'purchase'])
    result = analyzer.calculate_conversion()
    print(result)
    print("\n漏斗摘要:", analyzer.get_funnel_summary())
