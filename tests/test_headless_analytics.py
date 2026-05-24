"""headless_analytics.py 测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from headless_analytics import (
    FunnelReport, FunnelStep, PathReport, RetentionReport, SegmentReport,
    compute_funnel, compute_retention, compute_segments, compute_top_paths,
)


@pytest.fixture
def behavior_df() -> pd.DataFrame:
    """5 个用户，多事件、跨多天的行为数据。"""
    rows = [
        # user 1：完整漏斗 + day 1/7 留存
        (1, "page_view", "2024-01-01 08:00:00"),
        (1, "sign_up", "2024-01-01 08:10:00"),
        (1, "add_to_cart", "2024-01-01 08:30:00"),
        (1, "purchase", "2024-01-01 09:00:00"),
        (1, "page_view", "2024-01-02 10:00:00"),    # day 1
        (1, "page_view", "2024-01-08 10:00:00"),    # day 7
        # user 2：漏斗到 cart 流失
        (2, "page_view", "2024-01-01 09:00:00"),
        (2, "sign_up", "2024-01-01 09:05:00"),
        (2, "add_to_cart", "2024-01-01 09:30:00"),
        # user 3：只浏览不注册
        (3, "page_view", "2024-01-02 10:00:00"),
        (3, "page_view", "2024-01-02 11:00:00"),
        # user 4：注册后没下文
        (4, "page_view", "2024-01-03 10:00:00"),
        (4, "sign_up", "2024-01-03 10:05:00"),
        # user 5：heavy 用户
        (5, "page_view", "2024-01-04 10:00:00"),
        (5, "sign_up", "2024-01-04 10:05:00"),
        (5, "add_to_cart", "2024-01-04 11:00:00"),
        (5, "purchase", "2024-01-04 12:00:00"),
        (5, "page_view", "2024-01-04 13:00:00"),
        (5, "page_view", "2024-01-04 14:00:00"),
        (5, "page_view", "2024-01-04 15:00:00"),
    ]
    return pd.DataFrame(rows, columns=["user_id", "event", "timestamp"])


# --- Funnel ----------------------------------------------------------------

def test_funnel_basic_conversion(behavior_df):
    report = compute_funnel(behavior_df,
                             steps=["page_view", "sign_up", "purchase"])
    assert isinstance(report, FunnelReport)
    assert len(report.steps) == 3
    # 5 个用户都做过 page_view
    assert report.steps[0].n_users == 5
    # 4 个注册（1, 2, 4, 5）
    assert report.steps[1].n_users == 4
    # 2 个购买（1, 5）
    assert report.steps[2].n_users == 2


def test_funnel_overall_conversion_pct(behavior_df):
    report = compute_funnel(behavior_df,
                             steps=["page_view", "sign_up", "purchase"])
    # 2/5 = 40%
    assert report.overall_conversion_pct == 40.0


def test_funnel_weakest_step_identified(behavior_df):
    report = compute_funnel(behavior_df,
                             steps=["page_view", "sign_up", "purchase"])
    # 从 sign_up (4) → purchase (2) 流失 50%；从 page_view (5) → sign_up (4) 流失 20%
    # 最弱应该是 purchase 这步
    assert report.weakest_step == "purchase"
    assert report.weakest_drop_pct == 50.0


def test_funnel_time_window_enforces_24h(behavior_df):
    """添加一个超过 24h 才购买的用户 → 不算入。"""
    extra = pd.DataFrame([
        (6, "page_view", "2024-01-01 08:00:00"),
        (6, "purchase", "2024-01-03 08:00:00"),  # 48h 后
    ], columns=["user_id", "event", "timestamp"])
    df = pd.concat([behavior_df, extra])
    report = compute_funnel(df, steps=["page_view", "purchase"],
                             time_window_hours=24)
    # 在 24h 内 purchase 的：user 1, 5（不算 user 6）
    assert report.steps[1].n_users == 2


def test_funnel_empty_steps_raises(behavior_df):
    with pytest.raises(ValueError, match="steps"):
        compute_funnel(behavior_df, steps=[])


def test_funnel_no_starting_users(behavior_df):
    """起点事件没人触发 → 全 0。"""
    report = compute_funnel(behavior_df,
                             steps=["nonexistent_event", "page_view"])
    assert report.steps[0].n_users == 0
    assert report.steps[1].n_users == 0


def test_funnel_to_dict_serializable(behavior_df):
    import json
    report = compute_funnel(behavior_df, steps=["page_view", "sign_up"])
    json.dumps(report.to_dict(), ensure_ascii=False)


# --- Retention -------------------------------------------------------------

def test_retention_basic(behavior_df):
    report = compute_retention(behavior_df)
    assert isinstance(report, RetentionReport)
    assert report.cohort_size == 5


def test_retention_day_1_some_users(behavior_df):
    report = compute_retention(behavior_df)
    # user 1 在 day 1 来了 → 1/5 = 20%
    assert report.day_1_retention == 20.0


def test_retention_day_7_user1_returns(behavior_df):
    report = compute_retention(behavior_df)
    # user 1 day 7 也来了
    assert report.day_7_retention == 20.0


def test_retention_with_first_event_filter(behavior_df):
    """只把 sign_up 作为 cohort 起点。"""
    report = compute_retention(behavior_df, first_event_filter="sign_up")
    # 4 个用户注册了（1, 2, 4, 5）
    assert report.cohort_size == 4


def test_retention_empty_df_raises():
    with pytest.raises(ValueError):
        compute_retention(pd.DataFrame())


def test_retention_no_first_event_match(behavior_df):
    report = compute_retention(behavior_df, first_event_filter="nonexistent")
    assert report.cohort_size == 0
    assert report.day_1_retention == 0


def test_retention_to_dict_serializable(behavior_df):
    import json
    report = compute_retention(behavior_df)
    json.dumps(report.to_dict(), ensure_ascii=False)


# --- Path Analysis ---------------------------------------------------------

def test_paths_returns_top_sequences(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3, top_k=5)
    assert isinstance(report, PathReport)
    assert len(report.top_sequences) <= 5
    assert all(isinstance(seq, str) for seq, _ in report.top_sequences)


def test_paths_n_unique_paths(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3)
    # 5 个用户路径不一定都不同（user 3 / 4 可能撞）
    assert 1 <= report.n_unique_paths <= 5


def test_paths_avg_length(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3)
    # 每个用户最多取 3 步
    assert report.avg_path_length <= 3.0


def test_paths_to_dict_serializable(behavior_df):
    import json
    report = compute_top_paths(behavior_df)
    json.dumps(report.to_dict(), ensure_ascii=False)


# --- Segmentation ----------------------------------------------------------

def test_segments_classifies_correctly(behavior_df):
    report = compute_segments(behavior_df,
                               high_threshold=5, medium_threshold=2)
    assert isinstance(report, SegmentReport)
    # user 1: 6 事件 → heavy; user 5: 7 事件 → heavy
    # user 2: 3 事件 → regular; user 3: 2 事件 → regular
    # user 4: 2 事件 → regular
    assert report.segments["heavy"] == 2
    assert report.segments["regular"] == 3
    assert report.segments["light"] == 0


def test_segments_n_users_matches(behavior_df):
    report = compute_segments(behavior_df)
    assert report.n_users == 5


def test_segments_avg_events_computed(behavior_df):
    report = compute_segments(behavior_df)
    # 总事件 = 20，5 用户 → 平均 4
    assert report.avg_events_per_user == 4.0


def test_segments_empty_df_raises():
    with pytest.raises(ValueError):
        compute_segments(pd.DataFrame())


def test_segments_to_dict_serializable(behavior_df):
    import json
    report = compute_segments(behavior_df)
    json.dumps(report.to_dict(), ensure_ascii=False)
