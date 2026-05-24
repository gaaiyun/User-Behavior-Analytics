"""User-Behavior-Analytics CLI（v2）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from headless_analytics import (
    compute_funnel, compute_retention, compute_segments, compute_top_paths,
)


def _load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def cmd_funnel(args) -> int:
    df = _load_csv(args.csv)
    steps = args.steps.split(",")
    report = compute_funnel(df, steps=steps, time_window_hours=args.window)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 0


def cmd_retention(args) -> int:
    df = _load_csv(args.csv)
    report = compute_retention(df, first_event_filter=args.first_event)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 0


def cmd_paths(args) -> int:
    df = _load_csv(args.csv)
    report = compute_top_paths(df, max_steps=args.max_steps, top_k=args.top_k)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 0


def cmd_segments(args) -> int:
    df = _load_csv(args.csv)
    report = compute_segments(df, high_threshold=args.high, medium_threshold=args.medium)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 0


def cmd_overview(args) -> int:
    """一次性 dump 全部指标。"""
    df = _load_csv(args.csv)
    payload = {}

    if args.funnel_steps:
        steps = args.funnel_steps.split(",")
        try:
            payload["funnel"] = compute_funnel(df, steps=steps).to_dict()
        except Exception as e:
            payload["funnel"] = {"error": str(e)}

    try:
        payload["retention"] = compute_retention(df).to_dict()
    except Exception as e:
        payload["retention"] = {"error": str(e)}

    try:
        payload["paths"] = compute_top_paths(df).to_dict()
    except Exception as e:
        payload["paths"] = {"error": str(e)}

    try:
        payload["segments"] = compute_segments(df).to_dict()
    except Exception as e:
        payload["segments"] = {"error": str(e)}

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="uba", description="用户行为分析 headless CLI"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("funnel", help="漏斗转化分析")
    sp.add_argument("csv")
    sp.add_argument("--steps", required=True,
                    help="逗号分隔事件，如 page_view,sign_up,purchase")
    sp.add_argument("--window", type=int, default=24, help="时间窗口（小时）")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_funnel)

    sp = sub.add_parser("retention", help="Day-1/7/30 留存")
    sp.add_argument("csv")
    sp.add_argument("--first-event", help="只用某个事件作为 cohort 起点")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_retention)

    sp = sub.add_parser("paths", help="最常见用户路径")
    sp.add_argument("csv")
    sp.add_argument("--max-steps", type=int, default=5)
    sp.add_argument("--top-k", type=int, default=10)
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_paths)

    sp = sub.add_parser("segments", help="按活跃度分群（heavy/regular/light）")
    sp.add_argument("csv")
    sp.add_argument("--high", type=int, default=10, help="heavy 阈值")
    sp.add_argument("--medium", type=int, default=3, help="regular 阈值")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_segments)

    sp = sub.add_parser("overview", help="一次出全部指标")
    sp.add_argument("csv")
    sp.add_argument("--funnel-steps",
                    help="可选漏斗步骤；不传则跳过漏斗部分")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_overview)

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
