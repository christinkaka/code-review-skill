"""
Harness CLI 入口
提供 list / feedback / stats 三个命令
"""

import argparse
import sys
from pathlib import Path

from .decision_logger import DecisionLogger
from .feedback_manager import FeedbackManager
from .quality_monitor import QualityMonitor


def cmd_list(args):
    """列出待反馈的问题"""
    logger = DecisionLogger()
    fm = FeedbackManager()

    # 获取最新的扫描
    scans = logger.list_scans()
    if not scans:
        print("暂无扫描记录")
        return

    scan_id = args.scan_id or scans[0]
    data = logger.load(scan_id)
    decisions = data.get("decisions", [])
    feedbacks = fm.get_feedbacks_for_scan(scan_id)
    feedback_ids = {f["issue_id"] for f in feedbacks}

    # 过滤：只显示未反馈的，或全部
    if not args.all:
        decisions = [d for d in decisions if d["issue_id"] not in feedback_ids]

    if not decisions:
        print(f"扫描 {scan_id} 中没有待反馈的问题")
        return

    print(f"扫描: {scan_id}")
    print(f"{'ID':<40} | {'文件':<30} | {'行':<5} | {'AI判断':<8} | {'置信度':<6}")
    print("-" * 100)
    for d in decisions:
        action = "保留" if d["ai_action"] == "keep" else "过滤"
        print(f"{d['issue_id']:<40} | {d['file']:<30} | {d['line']:<5} | {action:<8} | {d['ai_confidence']:<6.2f}")

    print(f"\n共 {len(decisions)} 个问题")


def cmd_feedback(args):
    """标记用户反馈"""
    fm = FeedbackManager()
    logger = DecisionLogger()

    scan_id = args.scan_id or (logger.list_scans()[0] if logger.list_scans() else None)
    if not scan_id:
        print("暂无扫描记录")
        return

    feedback = fm.add_feedback(
        issue_id=args.issue_id,
        scan_id=scan_id,
        verdict=args.verdict,
        comment=args.comment,
    )
    print(f"已记录反馈: {args.issue_id} → {args.verdict}")


def cmd_stats(args):
    """查看质量统计"""
    logger = DecisionLogger()
    fm = FeedbackManager()
    monitor = QualityMonitor(logger, fm)

    print(monitor.generate_report())


def main():
    parser = argparse.ArgumentParser(description="Harness CLI - AI 评审质量管控")
    subparsers = parser.add_subparsers(dest="command")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出待反馈的问题")
    list_parser.add_argument("--scan-id", help="指定扫描 ID")
    list_parser.add_argument("--all", action="store_true", help="显示所有问题（包括已反馈的）")

    # feedback 命令
    fb_parser = subparsers.add_parser("feedback", help="标记用户反馈")
    fb_parser.add_argument("--issue-id", required=True, help="问题 ID")
    fb_parser.add_argument("--verdict", required=True, choices=["confirmed", "false_positive", "uncertain"], help="裁定结果")
    fb_parser.add_argument("--comment", help="用户评论")
    fb_parser.add_argument("--scan-id", help="指定扫描 ID")

    # stats 命令
    subparsers.add_parser("stats", help="查看质量统计")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "feedback":
        cmd_feedback(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
