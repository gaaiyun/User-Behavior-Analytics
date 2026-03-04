"""
用户行为分析平台 - 主界面
整合漏斗分析、路径分析、留存分析、用户分群等功能
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os

# 导入分析模块
from funnel_analyzer import FunnelAnalyzer, create_sample_funnel_data
from path_analyzer import PathAnalyzer, create_sample_path_data
from retention_analyzer import RetentionAnalyzer, create_sample_retention_data
from segmentation_analyzer import UserSegmentation, create_sample_segmentation_data


# 页面配置
st.set_page_config(
    page_title="用户行为分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
    }
</style>
""", unsafe_allow_html=True)


def load_data(file_path: str = None) -> pd.DataFrame:
    """加载数据"""
    if file_path and os.path.exists(file_path):
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            return pd.read_excel(file_path)
    return None


def save_data(df: pd.DataFrame, file_path: str):
    """保存数据"""
    df.to_csv(file_path, index=False)


# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 数据源选择
    data_source = st.radio(
        "选择数据源",
        ["示例数据", "上传 CSV", "上传 Excel"],
        index=0
    )
    
    uploaded_file = None
    if data_source != "示例数据":
        uploaded_file = st.file_uploader(
            "上传数据文件",
            type=['csv', 'xlsx'],
            help="文件需包含 user_id, event, timestamp 列"
        )
    
    st.divider()
    
    # 分析选项
    st.header("📈 分析选项")
    show_raw_data = st.checkbox("显示原始数据", value=False)
    auto_refresh = st.checkbox("自动刷新", value=True)
    
    st.divider()
    
    # 关于
    st.markdown("""
    ### 关于
    **用户行为分析平台 v1.0**
    
    功能模块:
    - 🔍 漏斗分析
    - 🛤️ 路径分析
    - 📅 留存分析
    - 👥 用户分群
    - 📊 事件分析
    
    技术栈: Streamlit, Pandas, Plotly
    """)


# 主标题
st.markdown('<h1 class="main-header">📊 用户行为分析平台</h1>', unsafe_allow_html=True)
st.markdown("---")

# 加载数据
@st.cache_data
def get_data(source_type: str, uploaded_file=None):
    """获取数据的缓存函数"""
    if source_type == "示例数据":
        # 生成综合示例数据
        funnel_df = create_sample_funnel_data(1000)
        path_df = create_sample_path_data(500)
        retention_df = create_sample_retention_data(1000, 60)
        segment_df = create_sample_segmentation_data(500)
        
        # 合并为统一格式
        all_data = pd.concat([funnel_df, path_df, retention_df, segment_df], ignore_index=True)
        all_data = all_data.drop_duplicates()
        return all_data
    elif uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            return pd.read_excel(uploaded_file)
    return None


data = get_data(data_source, uploaded_file)

if data is None:
    st.error("❌ 无法加载数据，请检查数据源")
    st.stop()

# 显示数据概览
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("总用户数", f"{data['user_id'].nunique():,}")
with col2:
    st.metric("总事件数", f"{len(data):,}")
with col3:
    st.metric("事件类型", data['event'].nunique())
with col4:
    st.metric("时间跨度", f"{(data['timestamp'].max() - data['timestamp'].min()).days} 天")

# 选项卡
tabs = st.tabs([
    "📊 概览",
    "🔍 漏斗分析",
    "🛤️ 路径分析",
    "📅 留存分析",
    "👥 用户分群",
    "📈 事件分析",
    "📁 数据管理"
])

# 1. 概览
with tabs[0]:
    st.header("数据概览")
    
    # 时间序列
    st.subheader("事件趋势")
    data['date'] = pd.to_datetime(data['timestamp']).dt.date
    daily_events = data.groupby('date').size().reset_index(name='count')
    
    fig_trend = px.line(
        daily_events,
        x='date',
        y='count',
        title='每日事件数量趋势',
        markers=True
    )
    fig_trend.update_layout(height=400)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # 事件分布
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("事件类型分布")
        event_dist = data['event'].value_counts().reset_index()
        event_dist.columns = ['event', 'count']
        
        fig_pie = px.pie(
            event_dist,
            names='event',
            values='count',
            title='事件类型占比'
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.subheader("用户活跃度分布")
        user_activity = data.groupby('user_id').size().reset_index(name='event_count')
        
        fig_hist = px.histogram(
            user_activity,
            x='event_count',
            nbins=30,
            title='用户事件数量分布',
            labels={'event_count': '事件数量', 'count': '用户数'}
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

# 2. 漏斗分析
with tabs[1]:
    st.header("🔍 漏斗分析")
    
    # 漏斗步骤配置
    st.subheader("配置漏斗步骤")
    available_events = sorted(data['event'].unique().tolist())
    
    col1, col2 = st.columns([2, 1])
    with col1:
        funnel_steps = st.multiselect(
            "选择漏斗步骤（按顺序）",
            options=available_events,
            default=available_events[:5] if len(available_events) >= 5 else available_events,
            help="按选择顺序排列漏斗步骤"
        )
    
    with col2:
        time_window = st.slider("时间窗口（小时）", 1, 168, 24)
    
    if len(funnel_steps) >= 2:
        # 创建漏斗分析器
        analyzer = FunnelAnalyzer(data)
        analyzer.define_funnel(funnel_steps)
        conversion_df = analyzer.calculate_conversion(time_window=time_window)
        
        # 显示漏斗图
        st.subheader("转化漏斗")
        funnel_fig = analyzer.plot_funnel("用户转化漏斗")
        st.plotly_chart(funnel_fig, use_container_width=True)
        
        # 显示转化数据
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("转化数据")
            st.dataframe(conversion_df.style.format({
                'count': '{:,}',
                'conversion_rate': '{:.2f}%',
                'relative_rate': '{:.2f}%'
            }), use_container_width=True)
        
        with col2:
            st.subheader("流失分析")
            dropoff_df = analyzer.analyze_dropoff()
            st.dataframe(dropoff_df.style.format({
                'dropoff_count': '{:,}',
                'dropoff_rate': '{:.2f}%'
            }), use_container_width=True)
        
        # 关键指标
        summary = analyzer.get_funnel_summary()
        st.subheader("关键指标")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("总用户数", f"{summary['total_users']:,}")
        m2.metric("最终转化用户", f"{summary['final_users']:,}")
        m3.metric("整体转化率", f"{summary['overall_conversion_rate']:.2f}%")
        m4.metric("最大流失步骤", summary['max_dropoff_step'])
    else:
        st.warning("请至少选择 2 个漏斗步骤")

# 3. 路径分析
with tabs[2]:
    st.header("🛤️ 路径分析")
    
    # 配置
    col1, col2, col3 = st.columns(3)
    with col1:
        min_support = st.slider("最小支持度", 1, 50, 5)
    with col2:
        top_n_paths = st.slider("显示路径数", 5, 50, 10)
    with col3:
        min_path_length = st.slider("最小路径长度", 2, 10, 3)
    
    analyzer = PathAnalyzer(data)
    analyzer.build_path_graph(min_support=min_support)
    
    # 桑基图
    st.subheader("用户行为路径桑基图")
    sankey_fig = analyzer.plot_sankey(top_n=top_n_paths)
    st.plotly_chart(sankey_fig, use_container_width=True)
    
    # 常见路径
    st.subheader("常见路径")
    common_paths = analyzer.find_common_paths(top_n=top_n_paths, min_length=min_path_length)
    st.dataframe(common_paths.style.format({'percentage': '{:.2f}%'}), use_container_width=True)
    
    # 路径热力图
    st.subheader("路径热力图")
    heatmap_fig = analyzer.plot_path_heatmap(top_n=15)
    st.plotly_chart(heatmap_fig, use_container_width=True)
    
    # 路径指标
    st.subheader("路径指标")
    metrics = analyzer.calculate_path_metrics()
    m1, m2, m3 = st.columns(3)
    m1.metric("平均路径长度", f"{metrics['avg_path_length']:.2f}")
    m2.metric("唯一路径数", f"{metrics['unique_paths']:,}")
    m3.metric("图密度", f"{metrics['graph_density']:.4f}")
    
    if metrics['key_nodes']:
        st.write("**关键节点:**")
        key_nodes_df = pd.DataFrame(metrics['key_nodes'])
        st.dataframe(key_nodes_df, use_container_width=True)

# 4. 留存分析
with tabs[3]:
    st.header("📅 留存分析")
    
    # 配置
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("时间周期", ["D", "W", "M"], format_func=lambda x: {"D": "天", "W": "周", "M": "月"}[x])
    with col2:
        cohort_period = st.selectbox("队列周期", ["D", "W", "M"], format_func=lambda x: {"D": "天", "W": "周", "M": "月"}[x])
    
    analyzer = RetentionAnalyzer(data)
    retention_df = analyzer.calculate_retention(period=period)
    
    # 留存曲线
    st.subheader("留存曲线")
    retention_fig = analyzer.plot_retention_curve()
    st.plotly_chart(retention_fig, use_container_width=True)
    
    # 留存热力图
    st.subheader("留存热力图")
    heatmap_fig = analyzer.plot_heatmap()
    st.plotly_chart(heatmap_fig, use_container_width=True)
    
    # 留存摘要
    st.subheader("留存指标")
    summary = analyzer.get_retention_summary()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("次日留存", f"{summary['day_1_retention']:.1f}%" if summary['day_1_retention'] else "N/A")
    m2.metric("7 日留存", f"{summary['day_7_retention']:.1f}%" if summary['day_7_retention'] else "N/A")
    m3.metric("30 日留存", f"{summary['day_30_retention']:.1f}%" if summary['day_30_retention'] else "N/A")
    m4.metric("趋势", summary['trend'])
    
    # 流失率
    st.subheader("流失率分析")
    churn_df = analyzer.calculate_churn_rate()
    st.dataframe(churn_df.style.format({
        'avg_churn_rate': '{:.2f}%',
        'min_churn_rate': '{:.2f}%',
        'max_churn_rate': '{:.2f}%'
    }), use_container_width=True)

# 5. 用户分群
with tabs[4]:
    st.header("👥 用户分群")
    
    # 配置
    col1, col2, col3 = st.columns(3)
    with col1:
        n_clusters = st.slider("聚类数量", 2, 10, 5)
    with col2:
        cluster_method = st.selectbox("聚类方法", ["kmeans", "dbscan"])
    with col3:
        show_features = st.multiselect(
            "选择特征",
            options=['recency', 'frequency', 'monetary'],
            default=['recency', 'frequency', 'monetary']
        )
    
    analyzer = UserSegmentation(data)
    analyzer.create_rfm_features()
    clustered_df = analyzer.cluster_users(n_clusters=n_clusters, method=cluster_method)
    
    # 聚类分布
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("聚类分布")
        dist_fig = analyzer.plot_cluster_distribution()
        st.plotly_chart(dist_fig, use_container_width=True)
    
    with col2:
        st.subheader("聚类特征")
        stats_df = analyzer.analyze_clusters()
        st.dataframe(stats_df.style.format('{:.2f}'), use_container_width=True)
    
    # 雷达图
    st.subheader("聚类特征雷达图")
    radar_fig = analyzer.plot_cluster_radar(features=show_features)
    st.plotly_chart(radar_fig, use_container_width=True)
    
    # 用户标签
    st.subheader("用户标签")
    tags = analyzer.assign_user_tags()
    tags_df = pd.DataFrame([
        {'聚类': cluster_id, '标签': ', '.join(tag_list)}
        for cluster_id, tag_list in tags.items()
    ])
    st.dataframe(tags_df, use_container_width=True)

# 6. 事件分析
with tabs[5]:
    st.header("📈 事件分析")
    
    # 事件选择
    selected_events = st.multiselect(
        "选择要分析的事件",
        options=sorted(data['event'].unique()),
        default=sorted(data['event'].unique())[:5]
    )
    
    if selected_events:
        filtered_data = data[data['event'].isin(selected_events)].copy()
        
        # 事件趋势
        st.subheader("事件趋势")
        filtered_data['date'] = pd.to_datetime(filtered_data['timestamp']).dt.date
        event_trend = filtered_data.groupby(['date', 'event']).size().reset_index(name='count')
        
        fig = px.line(
            event_trend,
            x='date',
            y='count',
            color='event',
            title='各事件趋势',
            markers=True
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 事件详情
        st.subheader("事件详情")
        event_stats = filtered_data.groupby('event').agg({
            'user_id': ['count', 'nunique'],
            'timestamp': ['min', 'max']
        })
        event_stats.columns = ['总次数', '用户数', '最早发生', '最晚发生']
        event_stats = event_stats.reset_index()
        st.dataframe(event_stats, use_container_width=True)
        
        # 每小时分布
        st.subheader("每小时分布")
        filtered_data['hour'] = pd.to_datetime(filtered_data['timestamp']).dt.hour
        hour_dist = filtered_data.groupby(['hour', 'event']).size().reset_index(name='count')
        
        fig_hour = px.bar(
            hour_dist,
            x='hour',
            y='count',
            color='event',
            title='事件每小时分布',
            barmode='group'
        )
        fig_hour.update_layout(height=400)
        st.plotly_chart(fig_hour, use_container_width=True)

# 7. 数据管理
with tabs[6]:
    st.header("📁 数据管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("导出数据")
        export_format = st.selectbox("导出格式", ["CSV", "Excel"])
        
        if st.button("导出当前数据"):
            if export_format == "CSV":
                csv = data.to_csv(index=False)
                st.download_button(
                    label="下载 CSV",
                    data=csv,
                    file_name=f"user_behavior_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                # 需要 openpyxl
                try:
                    excel_buffer = pd.ExcelWriter('temp.xlsx', engine='openpyxl')
                    data.to_excel(excel_buffer, index=False)
                    excel_buffer.close()
                    
                    with open('temp.xlsx', 'rb') as f:
                        st.download_button(
                            label="下载 Excel",
                            data=f.read(),
                            file_name=f"user_behavior_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    os.remove('temp.xlsx')
                except:
                    st.warning("导出 Excel 需要安装 openpyxl: pip install openpyxl")
    
    with col2:
        st.subheader("生成分析报告")
        if st.button("生成 PDF 报告"):
            st.info("PDF 报告生成功能开发中...")
        
        if st.button("生成 HTML 报告"):
            st.info("HTML 报告生成功能开发中...")
    
    st.divider()
    
    # 显示原始数据
    if show_raw_data:
        st.subheader("原始数据预览")
        st.dataframe(data.head(100), use_container_width=True)
        
        st.subheader("数据统计")
        st.write(f"- 总记录数：{len(data):,}")
        st.write(f"- 唯一用户数：{data['user_id'].nunique():,}")
        st.write(f"- 唯一事件数：{data['event'].nunique()}")
        st.write(f"- 时间范围：{data['timestamp'].min()} 至 {data['timestamp'].max()}")

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        用户行为分析平台 v1.0 | Powered by Streamlit + Plotly
    </div>
    """,
    unsafe_allow_html=True
)
