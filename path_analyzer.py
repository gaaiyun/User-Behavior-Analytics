"""
用户路径分析模块
功能：行为序列分析、关键路径识别、桑基图可视化、路径热力图
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import networkx as nx
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from datetime import datetime


class PathAnalyzer:
    """用户路径分析器"""
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化路径分析器
        
        Args:
            data: 用户行为数据 DataFrame，需包含 user_id, event, timestamp 列
        """
        self.data = data.copy()
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data = self.data.sort_values(['user_id', 'timestamp'])
        self.path_graph = None
        self.common_paths = None
        
    def extract_user_paths(self, max_steps: int = 10) -> Dict[int, List[str]]:
        """
        提取每个用户的行为路径
        
        Args:
            max_steps: 最大路径长度
            
        Returns:
            用户 ID 到事件路径的映射
        """
        user_paths = {}
        
        for user_id, group in self.data.groupby('user_id'):
            events = group['event'].tolist()[:max_steps]
            user_paths[user_id] = events
        
        return user_paths
    
    def build_path_graph(self, min_support: int = 5) -> nx.DiGraph:
        """
        构建路径图
        
        Args:
            min_support: 最小支持度（边出现的最小次数）
            
        Returns:
            NetworkX 有向图
        """
        G = nx.DiGraph()
        edge_counts = defaultdict(int)
        
        # 统计边的出现次数
        for user_id, group in self.data.groupby('user_id'):
            events = group['event'].tolist()
            for i in range(len(events) - 1):
                edge = (events[i], events[i + 1])
                edge_counts[edge] += 1
        
        # 添加节点和边
        for event in self.data['event'].unique():
            G.add_node(event)
        
        for (source, target), count in edge_counts.items():
            if count >= min_support:
                G.add_edge(source, target, weight=count, count=count)
        
        self.path_graph = G
        return G
    
    def find_common_paths(self, top_n: int = 10, min_length: int = 3) -> pd.DataFrame:
        """
        查找常见路径
        
        Args:
            top_n: 返回前 N 条路径
            min_length: 最小路径长度
            
        Returns:
            包含常见路径的 DataFrame
        """
        path_counter = Counter()
        
        # 提取所有用户的路径
        for user_id, group in self.data.groupby('user_id'):
            events = group['event'].tolist()
            
            # 提取所有可能的子路径
            for length in range(min_length, len(events) + 1):
                for i in range(len(events) - length + 1):
                    path = tuple(events[i:i + length])
                    path_counter[path] += 1
        
        # 获取最常见的路径
        common_paths = path_counter.most_common(top_n)
        
        self.common_paths = pd.DataFrame([
            {
                'path': ' → '.join(path),
                'path_list': list(path),
                'count': count,
                'percentage': count / len(self.data['user_id'].unique()) * 100
            }
            for path, count in common_paths
        ])
        
        return self.common_paths
    
    def plot_sankey(self, top_n: int = 10, title: str = "用户行为路径桑基图") -> go.Figure:
        """
        绘制桑基图
        
        Args:
            top_n: 显示前 N 条路径
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if self.path_graph is None:
            self.build_path_graph(min_support=3)
        
        # 获取边的流量
        links_source = []
        links_target = []
        links_value = []
        
        # 收集所有节点
        all_nodes = list(self.path_graph.nodes())
        node_indices = {node: idx for idx, node in enumerate(all_nodes)}
        
        for source, target, data in self.path_graph.edges(data=True):
            links_source.append(node_indices[source])
            links_target.append(node_indices[target])
            links_value.append(data.get('weight', 1))
        
        # 创建桑基图
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color="blue"
            ),
            link=dict(
                source=links_source,
                target=links_target,
                value=links_value,
                color="rgba(100, 150, 255, 0.5)"
            )
        )])
        
        fig.update_layout(
            title=title,
            font_size=12,
            height=500
        )
        
        return fig
    
    def plot_path_heatmap(self, top_n: int = 15, title: str = "用户路径热力图") -> go.Figure:
        """
        绘制路径热力图
        
        Args:
            top_n: 显示前 N 个事件
            title: 图表标题
            
        Returns:
            Plotly Figure 对象
        """
        if self.path_graph is None:
            self.build_path_graph(min_support=3)
        
        # 获取最常见的节点
        node_degrees = dict(self.path_graph.degree())
        top_nodes = sorted(node_degrees.keys(), key=lambda x: node_degrees[x], reverse=True)[:top_n]
        
        # 创建邻接矩阵
        matrix = np.zeros((len(top_nodes), len(top_nodes)))
        
        for i, source in enumerate(top_nodes):
            for j, target in enumerate(top_nodes):
                if self.path_graph.has_edge(source, target):
                    matrix[i, j] = self.path_graph[source][target].get('weight', 1)
        
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=top_nodes,
            y=top_nodes,
            colorscale='YlOrRd',
            showscale=True
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="目标事件",
            yaxis_title="源事件",
            height=600
        )
        
        return fig
    
    def calculate_path_metrics(self) -> Dict:
        """
        计算路径指标
        
        Returns:
            包含路径指标的字典
        """
        if self.path_graph is None:
            self.build_path_graph(min_support=3)
        
        user_paths = self.extract_user_paths()
        
        # 平均路径长度
        avg_path_length = np.mean([len(p) for p in user_paths.values()])
        
        # 路径多样性（唯一路径数）
        unique_paths = len(set(tuple(p) for p in user_paths.values()))
        
        # 图指标
        n_nodes = self.path_graph.number_of_nodes()
        n_edges = self.path_graph.number_of_edges()
        density = nx.density(self.path_graph)
        
        # 找到关键节点（入度和出度都高的节点）
        in_degrees = dict(self.path_graph.in_degree())
        out_degrees = dict(self.path_graph.out_degree())
        
        key_nodes = []
        for node in self.path_graph.nodes():
            if in_degrees.get(node, 0) > 0 and out_degrees.get(node, 0) > 0:
                key_nodes.append({
                    'node': node,
                    'in_degree': in_degrees.get(node, 0),
                    'out_degree': out_degrees.get(node, 0),
                    'total_degree': in_degrees.get(node, 0) + out_degrees.get(node, 0)
                })
        
        key_nodes = sorted(key_nodes, key=lambda x: x['total_degree'], reverse=True)
        
        return {
            'avg_path_length': avg_path_length,
            'unique_paths': unique_paths,
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'graph_density': density,
            'key_nodes': key_nodes[:5]
        }


def create_sample_path_data(n_users: int = 500) -> pd.DataFrame:
    """
    创建示例路径数据
    
    Args:
        n_users: 用户数量
        
    Returns:
        示例数据 DataFrame
    """
    np.random.seed(42)
    
    # 定义事件转移概率
    transitions = {
        'home': {'product_page': 0.6, 'search': 0.3, 'about': 0.1},
        'product_page': {'cart': 0.4, 'home': 0.3, 'product_page': 0.2, 'checkout': 0.1},
        'search': {'product_page': 0.7, 'home': 0.2, 'search': 0.1},
        'cart': {'checkout': 0.5, 'product_page': 0.3, 'home': 0.2},
        'checkout': {'purchase': 0.7, 'cart': 0.2, 'home': 0.1},
        'purchase': {'home': 0.5, 'product_page': 0.3, 'end': 0.2},
        'about': {'home': 0.6, 'contact': 0.3, 'about': 0.1},
        'contact': {'home': 0.8, 'end': 0.2}
    }
    
    data = []
    base_time = datetime(2024, 1, 1)
    
    for user_id in range(1, n_users + 1):
        current_event = 'home'
        user_time = base_time + pd.Timedelta(hours=np.random.randint(0, 720))
        steps = 0
        max_steps = np.random.randint(3, 15)
        
        while steps < max_steps and current_event != 'end':
            data.append({
                'user_id': user_id,
                'event': current_event,
                'timestamp': user_time
            })
            
            # 选择下一个事件
            if current_event in transitions:
                next_events = list(transitions[current_event].keys())
                probs = list(transitions[current_event].values())
                current_event = np.random.choice(next_events, p=probs)
            else:
                current_event = 'end'
            
            user_time += pd.Timedelta(minutes=np.random.randint(1, 30))
            steps += 1
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # 测试代码
    print("测试路径分析模块...")
    df = create_sample_path_data(300)
    analyzer = PathAnalyzer(df)
    
    print("\n常见路径:")
    common = analyzer.find_common_paths(top_n=5, min_length=2)
    print(common)
    
    print("\n路径指标:")
    metrics = analyzer.calculate_path_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
