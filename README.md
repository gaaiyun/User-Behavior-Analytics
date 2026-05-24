# User-Behavior-Analytics

用户行为分析平台：Streamlit 仪表板（v1）+ headless CLI（v2）。

v1 提供 4 个核心 analyzer（漏斗 / 留存 / 路径 / 分群）+ Streamlit 仪表板 + 52 个
单元测试，覆盖丰富。v2 在不动 v1 代码的前提下加：

- **Headless 分析层** — 纯 pandas / numpy，不依赖 plotly / Streamlit，可在脚本 /
  cron / CI 跑
- **统一 CLI** — 一个 `python __main__.py` 入口覆盖 5 个子命令

为什么需要 v2：v1 的 4 个 analyzer 都返回 plotly figure + 强耦合 Streamlit 渲染，
数据团队想"每天定时生成漏斗转化报告 → 推钉钉"做不到。v2 把指标和图表彻底拆开。

## v2 新增

| 文件 | 干什么 |
|---|---|
| `headless_analytics.py` | `compute_funnel` / `compute_retention` / `compute_top_paths` / `compute_segments` 纯 pandas 实现 |
| `__main__.py` | CLI 5 子命令：funnel / retention / paths / segments / overview |
| `tests/test_headless_analytics.py` | 23 测试：漏斗时间窗口 / 留存 Day-N / 路径序列 / 分群阈值 |

总测试 75 个（52 v1 + 23 v2），5 秒跑完。

## v1 仍保留

| 模块 | 干什么 |
|---|---|
| `dashboard.py` | Streamlit 交互式主界面 |
| `funnel_analyzer.py` | 漏斗 + plotly Sankey/桑基图 |
| `retention_analyzer.py` | 留存矩阵 + cohort 热力图 |
| `path_analyzer.py` | 用户路径桑基图 |
| `segmentation_analyzer.py` | RFM-like 多维分群 |
| `data/sample_data.csv` | 示例事件数据 |

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### v2 headless CLI

```bash
# 1. 漏斗分析：定义事件序列 + 时间窗口
python __main__.py funnel data/sample_data.csv \
    --steps "page_view,sign_up,add_to_cart,purchase" --window 24

# 2. 留存（Day-1 / 7 / 30）
python __main__.py retention data/sample_data.csv

# 只把某个事件作为 cohort 起点
python __main__.py retention data/sample_data.csv --first-event sign_up

# 3. 用户路径（最常见的前 N 步序列）
python __main__.py paths data/sample_data.csv --max-steps 5 --top-k 10

# 4. 分群（heavy / regular / light）
python __main__.py segments data/sample_data.csv --high 10 --medium 3

# 5. 一次性导全部指标
python __main__.py overview data/sample_data.csv \
    --funnel-steps "page_view,sign_up,purchase" -o report.json
```

### v1 Streamlit 仪表板

```bash
streamlit run dashboard.py
```

### 库调用

```python
import pandas as pd
from headless_analytics import (
    compute_funnel, compute_retention,
    compute_top_paths, compute_segments,
)

df = pd.read_csv("events.csv")

# 漏斗：必须 24h 内完成下一步
funnel = compute_funnel(df,
    steps=["page_view", "sign_up", "purchase"],
    time_window_hours=24,
)
print(funnel.overall_conversion_pct, funnel.weakest_step)
# 35.0 'purchase'

# 留存
retention = compute_retention(df, first_event_filter="sign_up")
print(retention.day_1_retention, retention.day_7_retention)

# 路径
paths = compute_top_paths(df, max_steps=5, top_k=10)
for seq, count in paths.top_sequences:
    print(f"{count:>4}  {seq}")

# 分群
segments = compute_segments(df, high_threshold=10, medium_threshold=3)
print(segments.segments)   # {'heavy': N, 'regular': N, 'light': N}
```

## 一个真实输出

```
$ python __main__.py funnel data/sample_data.csv \
    --steps "page_view,sign_up,add_to_cart,purchase"

{
  "steps": [
    {"name": "page_view",    "n_users": 20, "conversion_pct": 100.0, "step_conversion_pct": 100.0, "drop_off": 0},
    {"name": "sign_up",      "n_users": 16, "conversion_pct": 80.0,  "step_conversion_pct": 80.0,  "drop_off": 4},
    {"name": "add_to_cart",  "n_users": 11, "conversion_pct": 55.0,  "step_conversion_pct": 68.8,  "drop_off": 5},
    {"name": "purchase",     "n_users": 7,  "conversion_pct": 35.0,  "step_conversion_pct": 63.6,  "drop_off": 4}
  ],
  "overall_conversion_pct": 35.0,
  "weakest_step": "add_to_cart",
  "weakest_drop_pct": 31.25
}
```

`weakest_step` 自动指出转化损失最大的环节 — 这次是从 sign_up 到 add_to_cart 流失
31%（5 个用户），比 page_view→sign_up 损失 20%、add_to_cart→purchase 损失 36%
都重要（按 step_conversion_pct 比较）。

## 数据 schema

事件 CSV 必须包含三列：

| 列 | 类型 | 说明 |
|---|---|---|
| user_id | int / str | 用户唯一 ID |
| event | str | 事件名（page_view / sign_up / purchase 等） |
| timestamp | datetime-parseable | 事件时间 |

可选列：`value` 等，目前 v2 不用，但 v1 仪表板会读。

## 设计取舍

- **漏斗时间窗口默认 24h**：每一步必须在前一步发生后 24h 内完成才算转化。
  跨多日的"长漏斗"（注册 → 30 天后首次购买）需要传 `--window 720`。
- **留存只算 Day-1 / 7 / 30**：v1 的留存矩阵更细，v2 简化为 3 个关键节点。要画
  完整矩阵还是去 v1。
- **路径分析取前 max_steps 步**：避免长尾路径污染统计。`max_steps=5` 是经验值，
  电商场景通常注册后 5 步内能看出意图。
- **分群只看活跃度**：v2 用单维度（事件数）做 heavy / regular / light 分群。多
  维 RFM 走 v1 `segmentation_analyzer`。

## 项目结构

```
User-Behavior-Analytics/
├── __main__.py                  # v2 CLI
├── headless_analytics.py        # v2 纯 pandas 分析
├── dashboard.py                 # v1 Streamlit
├── funnel_analyzer.py           # v1 漏斗 + plotly
├── retention_analyzer.py        # v1 留存
├── path_analyzer.py             # v1 路径
├── segmentation_analyzer.py     # v1 分群
├── tests/                       # 75 测试
│   ├── test_funnel.py
│   ├── test_path.py
│   ├── test_retention.py
│   ├── test_segmentation.py
│   └── test_headless_analytics.py   # v2 新增
├── data/sample_data.csv
├── pytest.ini
└── requirements.txt
```

## 测试

```bash
pytest tests/ --no-cov
```

75 个测试，5 秒跑完。

## 已知限制

- `compute_funnel` 的时间窗口是固定值（小时），不支持每步不同窗口。复杂场景需要
  自己改源码。
- `compute_retention` 没区分平台 / 渠道，cohort 是按"首次出现日"切，跨渠道的用户
  会算成一个 cohort。
- `compute_top_paths` 只看事件序列，不考虑事件属性（页面 URL / 按钮 id）。

## 许可

MIT
