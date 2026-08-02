#!/usr/bin/env python3
"""
代码评审工具 - 主扫描入口
用法: python scripts/scan.py --repo <repo-path> --base master --target release/1.0 --profile default --output report/
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 将 scripts 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diff_analyzer import DiffAnalyzer
from call_graph import CallGraphBuilder
from rule_engine import RuleEngine
from ai_reviewer import AIReviewer
from report_generator import ReportGenerator

# 调度与通知模块（可选依赖，不影响基础扫描功能）
try:
    from scheduler import Scheduler
    from notifier import Notifier
except ImportError:
    Scheduler = None
    Notifier = None

# ============================================================
# 日志配置
# ============================================================
def setup_logging(level: str = "INFO", log_file: str = None):
    """配置日志"""
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )

logger = logging.getLogger("code-review")


# ============================================================
# 配置加载
# ============================================================
def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
    import yaml

    if config_path is None:
        # 默认查找项目根目录的 config.yaml
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"

    config_path = Path(config_path)
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def load_profile(profile_name: str, specs_dir: str) -> dict:
    """加载规约 Profile"""
    import yaml

    profile_path = Path(specs_dir) / "profiles" / f"{profile_name}.yaml"
    if not profile_path.exists():
        logger.warning(f"Profile '{profile_name}' 不存在，使用 default")
        profile_path = Path(specs_dir) / "profiles" / "default.yaml"

    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# 主扫描流程
# ============================================================
def run_scan(args):
    """执行完整扫描流程"""
    start_time = time.time()

    # 1. 加载配置
    config = load_config(args.config)
    specs_dir = args.specs_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references"
    )
    profile = load_profile(args.profile, specs_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 确定扫描模式
    is_full_scan = getattr(args, "full_scan", False)

    logger.info(f"=" * 60)
    logger.info(f"代码评审扫描启动")
    logger.info(f"  仓库: {args.repo}")
    if is_full_scan:
        logger.info(f"  扫描模式: 全库静态分析")
    else:
        logger.info(f"  基线分支: {args.base}")
        logger.info(f"  目标分支: {args.target}")
    logger.info(f"  规约 Profile: {args.profile}")
    logger.info(f"  输出目录: {output_dir}")
    if hasattr(args, "workflow"):
        logger.info(f"  AI 工作流: {args.workflow}")
    logger.info(f"=" * 60)

    # 2. 差异分析或全库扫描
    diff_analyzer = DiffAnalyzer(args.repo)
    
    if is_full_scan:
        logger.info("[1/5] 执行全库静态分析...")
        diff_result = diff_analyzer.scan_full()
        logger.info(
            f"  扫描范围: 仓库中所有源文件"
        )
    else:
        logger.info("[1/5] 执行分支差异分析...")
        diff_result = diff_analyzer.analyze(args.base, args.target)
    
    logger.info(
        f"  发现 {len(diff_result['changed_files'])} 个文件, "
        f"{len(diff_result['changed_methods'])} 个方法"
    )

    if not diff_result["changed_files"]:
        if is_full_scan:
            logger.info("仓库中未发现源文件，扫描结束。")
        else:
            logger.info("无代码变更，扫描结束。")
        return

    # 3. 调用图构建
    logger.info("[2/5] 构建调用图与血缘分析...")
    cg_builder = CallGraphBuilder(args.repo, language=args.language)
    
    if is_full_scan:
        call_graph = cg_builder.build_all()
    else:
        call_graph = cg_builder.build(diff_result["changed_methods"])
    
    logger.info(
        f"  调用图节点: {call_graph['node_count']}, "
        f"边: {call_graph['edge_count']}, "
        f"影响范围: {len(call_graph['affected_methods'])} 个方法"
    )

    # 4. 规约检查
    logger.info("[3/5] 执行规约检查...")
    engine = RuleEngine(specs_dir=specs_dir, profile=profile)
    raw_issues = engine.run(
        repo_path=args.repo,
        changed_files=diff_result["changed_files"],
    )
    logger.info(f"  发现 {len(raw_issues)} 个原始问题")

    # 5. 生成 Subagent 评审任务
    issues = raw_issues
    logger.info("[4/5] 生成 Subagent 评审任务...")
    ai_config = {}
    # 从命令行参数获取工作流
    if hasattr(args, "workflow"):
        ai_config["workflow"] = args.workflow
    ai_reviewer = AIReviewer(ai_config)
    
    # 生成 subagent 任务描述
    task = ai_reviewer.generate_subagent_task(raw_issues, diff_result, call_graph)
    
    # 保存任务到文件
    task_file = output_dir / "subagent-review-task.md"
    ai_reviewer.save_task_to_file(task, str(task_file))
    
    logger.info(f"  工作流: {ai_reviewer.get_current_workflow()}")
    logger.info(f"  Subagent 任务已保存到: {task_file}")
    logger.info(f"  请 TRAE Agent 委派 subagent 读取该文件并执行评审")

    # 6. 关联调用链
    for issue in issues:
        file_path = issue.get("file", "")
        line = issue.get("line", 0)
        issue["call_chain"] = call_graph.get("call_chains", {}).get(
            f"{file_path}:{line}", []
        )

    # 7. 生成报告
    logger.info("[5/5] 生成评审报告...")
    generator = ReportGenerator(output_dir=str(output_dir))
    
    # 构建扫描信息
    scan_info = {
        "repo": args.repo,
        "profile": args.profile,
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": round(time.time() - start_time, 2),
    }
    
    if is_full_scan:
        scan_info["mode"] = "full-scan"
    else:
        scan_info["base_branch"] = args.base
        scan_info["target_branch"] = args.target
        scan_info["mode"] = "diff"
    
    report = generator.generate(
        scan_info=scan_info,
        issues=issues,
        diff_summary=diff_result,
        call_graph_summary={
            "node_count": call_graph["node_count"],
            "edge_count": call_graph["edge_count"],
            "affected_methods": call_graph["affected_methods"],
        },
    )

    # 8. 输出摘要
    summary = report.get("summary", {})
    logger.info(f"=" * 60)
    logger.info(f"扫描完成！耗时: {round(time.time() - start_time, 2)}s")
    logger.info(f"  总计问题: {summary.get('total', 0)}")
    logger.info(f"  CRITICAL: {summary.get('critical', 0)}")
    logger.info(f"  HIGH:     {summary.get('high', 0)}")
    logger.info(f"  MEDIUM:   {summary.get('medium', 0)}")
    logger.info(f"  LOW:      {summary.get('low', 0)}")
    logger.info(f"  报告输出: {output_dir}")
    logger.info(f"=" * 60)

    return report


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="代码评审工具 - 自动化代码扫描与评审",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本扫描
  python scripts/scan.py --repo ./my-project --base master --target release/1.0

  # 指定 Profile 和输出目录
  python scripts/scan.py --repo ./my-project --base master --target HEAD --profile strict --output report/

  # 使用配置文件
  python scripts/scan.py --repo ./my-project --base master --target HEAD --config config.yaml

  # 全库静态分析（全量扫描，无需 --base 和 --target）
  python scripts/scan.py --repo ./my-project --full-scan
        """,
    )

    parser.add_argument("--repo", required=True, help="Git 仓库路径")
    parser.add_argument("--base", required=False, default=None, help="基线分支（如 master）")
    parser.add_argument("--target", required=False, default=None, help="目标分支（如 release/1.0）")
    parser.add_argument("--profile", default="default", help="规约 Profile（default/strict/minimal）")
    parser.add_argument("--output", default="report", help="报告输出目录")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--specs-dir", default=None, help="规约库目录路径")
    parser.add_argument("--language", default="java", help="主要语言（java/python/javascript/go）")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--log-file", default=None, help="日志文件路径")
    parser.add_argument(
        "--workflow", default="comprehensive",
        choices=["security", "quality", "performance", "architecture", "comprehensive"],
        help="AI 评审工作流（security/quality/performance/architecture/comprehensive）",
    )
    parser.add_argument(
        "--trigger", action="store_true", default=False,
        help="手动触发扫描（立即执行，不等待定时调度）",
    )
    parser.add_argument(
        "--full-scan", action="store_true", default=False,
        help="全库静态分析模式（扫描仓库中所有源文件，无需指定 --base 和 --target）",
    )

    args = parser.parse_args()

    # 验证参数
    if not args.full_scan and (not args.base or not args.target):
        parser.error("--base 和 --target 是必需的，除非使用 --full-scan 模式")

    setup_logging(args.log_level, args.log_file)

    # 加载配置（用于通知/调度集成）
    config = load_config(args.config)

    if getattr(args, "trigger", False):
        logger.info("手动触发扫描 (--trigger)")

    # 构建 Notifier（如果配置了通知）
    notifier = None
    schedule_config = config.get("schedule", {})
    if schedule_config.get("notify", False) and Notifier is not None:
        notifier = Notifier(config={
            "notify_method": schedule_config.get("notify_method", "webhook"),
            "notify_target": schedule_config.get("notify_target", ""),
        })

    try:
        report = run_scan(args)
        # 扫描成功，发送 Webhook 通知
        if notifier and report:
            success = notifier.send_webhook(report)
            if success:
                logger.info("扫描结果已通过 Webhook 通知")
            else:
                logger.warning("Webhook 通知发送失败")
        if report:
            sys.exit(0)
        else:
            sys.exit(0)  # 无变更也是正常退出
    except Exception as e:
        logger.error(f"扫描失败: {e}", exc_info=True)
        # 扫描失败，发送告警
        if notifier:
            from datetime import datetime as _dt
            alert_data = {
                "event": "scan.failure",
                "timestamp": _dt.now().isoformat(),
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "data": {
                    "repo": getattr(args, "repo", "unknown"),
                },
            }
            alert_ok = notifier.send_alert(alert_data)
            if alert_ok:
                logger.info("扫描失败告警已通过 Webhook 发送")
            else:
                logger.warning("扫描失败告警发送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
