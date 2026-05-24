"""无 Streamlit / plotly 依赖的用户行为分析函数集合。

v1 的 4 个 analyzer（funnel / path / retention / segmentation）业务逻辑
基本独立，但都返回 plotly figure，没法在脚本 / cron 跑。这一层提供同样的
**指标 + 数据结构**（dataclass / dict），不画图。

覆盖：
- 漏斗转化：定义事件序列 → 各步骤转化率 + 流失点
- 留存：Day-N 留存率矩阵 + cohort 分析
- 路径分析：用户最常见的 N 步事件序列
- 用户分群：基于活跃度 / 频次 / 多样性的简单分群
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


REQUIRED_COLS = ["user_id", "event", "timestamp"]


def _check_cols(df: pd.DataFrame) -> None:
    if df is None or len(df) == 0:
        raise ValueError("DataFrame 为空")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"缺必要列：{missing}")


# --- Funnel -----------------------------------------------------------------

@dataclass
class FunnelStep:
    name: str
    n_users: int
    conversion_pct: float        # 相对漏斗起点
    step_conversion_pct: float   # 相对上一步
    drop_off: int                # 相对上一步流失数

    def to_dict(self) -> dict:
        return {k: (float(v) if isinstance(v, (np.integer, np.floating))
                    else v) for k, v in self.__dict__.items()}


@dataclass
class FunnelReport:
    steps: List[FunnelStep] = field(default_factory=list)
    overall_conversion_pct: float = 0.0
    weakest_step: Optional[str] = None
    weakest_drop_pct: float = 0.0

    def to_dict(self) -> dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "overall_conversion_pct": float(self.overall_conversion_pct),
            "weakest_step": self.weakest_step,
            "weakest_drop_pct": float(self.weakest_drop_pct),
        }


def compute_funnel(df: pd.DataFrame, steps: List[str],
                   time_window_hours: int = 24) -> FunnelReport:
    """漏斗分析：从 steps[0] 起，每个用户必须在 time_window_hours 内
    完成下一步才算转化。
    """
    _check_cols(df)
    if not steps:
        raise ValueError("steps 不能为空")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["user_id", "timestamp"])

    # 第一步：所有做过 steps[0] 的用户
    start_events = df[df["event"] == steps[0]].groupby("user_id")["timestamp"].min()
    if len(start_events) == 0:
        # 没人触发起点
        return FunnelReport(
            steps=[FunnelStep(name=s, n_users=0, conversion_pct=0.0,
                              step_conversion_pct=0.0, drop_off=0)
                   for s in steps],
        )

    funnel_users = set(start_events.index)
    n_start = len(funnel_users)
    prev_n = n_start
    step_list = []

    # 起点
    step_list.append(FunnelStep(
        name=steps[0], n_users=n_start, conversion_pct=100.0,
        step_conversion_pct=100.0, drop_off=0,
    ))

    user_step_time = {u: start_events[u] for u in funnel_users}

    # 后续步骤
    for step in steps[1:]:
        next_users = set()
        new_step_times = {}
        for u in funnel_users:
            prev_time = user_step_time[u]
            cutoff = prev_time + pd.Timedelta(hours=time_window_hours)
            user_step_events = df[(df["user_id"] == u) & (df["event"] == step)
                                  & (df["timestamp"] > prev_time)
                                  & (df["timestamp"] <= cutoff)]
            if len(user_step_events) > 0:
                next_users.add(u)
                new_step_times[u] = user_step_events["timestamp"].iloc[0]
        n_now = len(next_users)
        step_conv = (n_now / prev_n * 100) if prev_n else 0.0
        overall_conv = (n_now / n_start * 100) if n_start else 0.0
        drop = prev_n - n_now
        step_list.append(FunnelStep(
            name=step, n_users=n_now,
            conversion_pct=overall_conv, step_conversion_pct=step_conv,
            drop_off=drop,
        ))
        funnel_users = next_users
        user_step_time = new_step_times
        prev_n = n_now

    # 找最弱环节（step_conversion 最低，除起点）
    weakest = None
    weakest_pct = 0.0
    for s in step_list[1:]:
        drop_pct = 100 - s.step_conversion_pct
        if drop_pct > weakest_pct:
            weakest_pct = drop_pct
            weakest = s.name

    overall = step_list[-1].conversion_pct if len(step_list) > 1 else 100.0
    return FunnelReport(steps=step_list, overall_conversion_pct=overall,
                        weakest_step=weakest, weakest_drop_pct=weakest_pct)


# --- Retention --------------------------------------------------------------

@dataclass
class RetentionReport:
    cohort_size: int
    day_0_users: int
    day_1_retention: float    # %
    day_7_retention: float
    day_30_retention: float
    cohort_dates: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: (v if not isinstance(v, (np.integer, np.floating))
                    else float(v)) for k, v in self.__dict__.items()}


def compute_retention(df: pd.DataFrame,
                      first_event_filter: Optional[str] = None
                      ) -> RetentionReport:
    """Day-N 留存率。用户第一次出现的日期定义为 cohort，N 天后是否还有事件。"""
    _check_cols(df)
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if first_event_filter:
        df_first = df[df["event"] == first_event_filter]
    else:
        df_first = df
    if len(df_first) == 0:
        return RetentionReport(cohort_size=0, day_0_users=0,
                               day_1_retention=0, day_7_retention=0,
                               day_30_retention=0)

    first_day = df_first.groupby("user_id")["timestamp"].min().dt.normalize()
    cohort_dates = sorted(first_day.unique())
    cohort_size = int(len(first_day))

    # 每个用户后续每天是否出现
    df["day"] = df["timestamp"].dt.normalize()
    user_day_set = df.groupby("user_id")["day"].apply(set)

    def retention_at(day_n: int) -> float:
        kept = 0
        for u, first_d in first_day.items():
            target = first_d + pd.Timedelta(days=day_n)
            days = user_day_set.get(u, set())
            if target in days:
                kept += 1
        return float(kept / cohort_size * 100) if cohort_size else 0.0

    return RetentionReport(
        cohort_size=cohort_size, day_0_users=cohort_size,
        day_1_retention=retention_at(1),
        day_7_retention=retention_at(7),
        day_30_retention=retention_at(30),
        cohort_dates=[str(d.date()) for d in cohort_dates[:20]],   # 最多 20 个
    )


# --- Path Analysis ----------------------------------------------------------

@dataclass
class PathReport:
    top_sequences: List[Tuple[str, int]]    # [("page_view -> sign_up -> ...", count), ...]
    avg_path_length: float
    n_unique_paths: int

    def to_dict(self) -> dict:
        return {
            "top_sequences": [{"sequence": s, "count": int(c)}
                              for s, c in self.top_sequences],
            "avg_path_length": float(self.avg_path_length),
            "n_unique_paths": int(self.n_unique_paths),
        }


def compute_top_paths(df: pd.DataFrame, max_steps: int = 5,
                     top_k: int = 10) -> PathReport:
    """每个用户取前 max_steps 个事件，统计最常见的路径模式。"""
    _check_cols(df)
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["user_id", "timestamp"])

    user_paths = df.groupby("user_id")["event"].apply(
        lambda x: " -> ".join(x.iloc[:max_steps].tolist())
    )

    counter = Counter(user_paths)
    top = counter.most_common(top_k)

    path_lengths = user_paths.apply(lambda p: len(p.split(" -> "))).tolist()
    avg_len = float(np.mean(path_lengths)) if path_lengths else 0.0

    return PathReport(
        top_sequences=top,
        avg_path_length=avg_len,
        n_unique_paths=len(counter),
    )


# --- Segmentation -----------------------------------------------------------

@dataclass
class SegmentReport:
    n_users: int
    segments: Dict[str, int]       # segment 名 → 用户数
    avg_events_per_user: float
    avg_unique_events_per_user: float

    def to_dict(self) -> dict:
        return {k: (v if not isinstance(v, (np.integer, np.floating))
                    else float(v)) for k, v in self.__dict__.items()}


def compute_segments(df: pd.DataFrame,
                     high_threshold: int = 10,
                     medium_threshold: int = 3) -> SegmentReport:
    """按用户事件数把用户分群：

    - heavy（n_events ≥ high_threshold）
    - regular（medium_threshold ≤ n_events < high_threshold）
    - light（< medium_threshold）
    """
    _check_cols(df)
    user_events = df.groupby("user_id")["event"].agg(["count", "nunique"])
    user_events.columns = ["n_events", "n_unique"]

    segments = {"heavy": 0, "regular": 0, "light": 0}
    for u, row in user_events.iterrows():
        n = int(row["n_events"])
        if n >= high_threshold:
            segments["heavy"] += 1
        elif n >= medium_threshold:
            segments["regular"] += 1
        else:
            segments["light"] += 1

    n_users = int(len(user_events))
    avg = float(user_events["n_events"].mean()) if n_users else 0.0
    avg_unique = float(user_events["n_unique"].mean()) if n_users else 0.0

    return SegmentReport(
        n_users=n_users, segments=segments,
        avg_events_per_user=avg, avg_unique_events_per_user=avg_unique,
    )
