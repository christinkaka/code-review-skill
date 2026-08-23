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
import fnmatch
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

# Harness 模块（可选依赖，V8/V9 线的 AI 质量管控：决策日志/反馈/质量监控）
# 需要把项目根目录加入 sys.path，因为 harness 包在项目根目录
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from harness.decision_logger import DecisionLogger
    from harness.feedback_manager import FeedbackManager
    from harness.quality_monitor import QualityMonitor
except ImportError:
    DecisionLogger = None
    FeedbackManager = None
    QualityMonitor = None

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
# Prefilter 白名单
# ============================================================
def prefilter_issues(issues: list, config: dict) -> list:
    """
    P0-3 修复: 基于白名单过滤已知误报
    
    Args:
        issues: 原始问题列表
        config: 配置字典（可包含 whitelist 配置）
    
    Returns:
        过滤后的问题列表
    """
    # 从配置加载白名单
    whitelist = config.get("prefilter", {}).get("whitelist", {})

    # 默认白名单规则
    # 覆盖主流测试文件约定（双盲测试 Spring Boot 实测发现 359 个 path-traversal
    # 命中几乎全在测试文件，故扩展以下模式）：
    # - 标准目录: src/test/**、src/tests/**（Maven/Gradle）
    # - 自定义 source set: dockerTest/**、integrationTest/**（Spring Boot 等）
    # - JUnit 命名: *Test.*（单数）、*Tests.*（复数）、*IT.*（Failsafe）
    # - pytest: test_*.py、*_test.py
    # - 前端: *.spec.*、*.test.*
    file_patterns = whitelist.get("file_patterns", [
        "**/test/**",
        "**/tests/**",
        "**/dockerTest/**",
        "**/integrationTest/**",
        "**/*_test.*",
        "**/*Test.*",
        "**/*Tests.*",
        "**/*IT.*",
        "**/test_*.py",
        "**/*.spec.*",
        "**/*.test.*",
        "**/Safe.*",
        "**/safe.*",
    ])
    
    rule_file_combos = whitelist.get("rule_file_combos", [])
    
    filtered = []
    dropped_count = 0
    
    for issue in issues:
        file_path = issue.get("file", "")
        rule_id = issue.get("rule_id", "")
        
        # 检查文件路径模式
        is_whitelisted = False
        for pattern in file_patterns:
            # 使用 fnmatch 进行 glob 模式匹配
            if pattern.startswith("**/"):
                # **/ 表示任意目录层级
                # 检查完整路径
                if fnmatch.fnmatch(file_path, pattern):
                    is_whitelisted = True
                    break
                # 检查文件名部分（不带路径）
                filename = os.path.basename(file_path)
                if fnmatch.fnmatch(filename, pattern[3:]):
                    is_whitelisted = True
                    break
                # 检查路径中的任何部分
                parts = file_path.split(os.sep)
                for i in range(len(parts)):
                    partial_path = os.sep.join(parts[i:])
                    if fnmatch.fnmatch(partial_path, pattern[3:]):
                        is_whitelisted = True
                        break
                if is_whitelisted:
                    break
            elif fnmatch.fnmatch(file_path, pattern):
                is_whitelisted = True
                break
        
        # 检查 rule_id + file 组合
        if not is_whitelisted:
            for combo in rule_file_combos:
                if combo.get("rule_id") == rule_id and combo.get("file") in file_path:
                    is_whitelisted = True
                    break
        
        if is_whitelisted:
            issue["is_false_positive"] = True
            issue["ai_action"] = "drop"
            issue["prefilter_reason"] = "whitelist"
            dropped_count += 1
        else:
            filtered.append(issue)
    
    if dropped_count > 0:
        logger.info(f"Prefilter: 过滤 {dropped_count} 个白名单误报，剩余 {len(filtered)} 个")
    
    return filtered


# ============================================================
# Harness 集成（V8/V9 线移植：AI 质量管控）
# ============================================================
def load_harness_config(harness_config_path: str = None) -> dict:
    """加载 Harness 配置文件

    Harness 配置控制 AI 评审的行为约束、监控和反馈机制。
    与 config.yaml（全局扫描配置）分离，专注于 AI 质量管控。
    """
    import yaml

    if harness_config_path is None:
        project_root = Path(__file__).parent.parent
        harness_config_path = project_root / "config" / "harness.yaml"

    harness_config_path = Path(harness_config_path)
    if harness_config_path.exists():
        with open(harness_config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # 配置文件不存在时返回禁用配置
    return {
        "harness": {
            "enabled": False,
            "decision_logging": {"enabled": False, "keep_recent": 10, "storage_dir": "data/decisions"},
            "feedback": {"enabled": False, "allow_batch": True, "storage_file": "data/feedbacks.json"},
            "auto_improvement": {"enabled": False},
            "quality_monitor": {"enabled": False, "cache_file": "data/stats_cache.json"},
        }
    }


def create_workspace(repo_path: str = None, base_dir: str = None) -> dict:
    """创建独立的工作空间

    每次扫描创建独立的工作空间目录，包含：
    - report/: 扫描报告
    - cache/: 规则编译缓存
    - decisions/: 决策日志

    工作空间默认创建在被扫描项目的 .code-review/workspace/ 下，
    避免污染 code-review-skill 项目本身。

    Returns:
        {
            "scan_id": str,          # 扫描ID（时间戳_随机后缀）
            "workspace_dir": Path,   # 工作空间根目录
            "report_dir": Path,      # 报告目录
            "cache_dir": Path,       # 缓存目录
            "decisions_dir": Path,   # 决策日志目录
        }
    """
    import hashlib

    if base_dir is None:
        if repo_path:
            base_dir = Path(repo_path).resolve() / ".code-review" / "workspace"
        else:
            project_root = Path(__file__).parent.parent
            base_dir = project_root / ".code-review" / "workspace"

    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    # 生成 scan_id: 时间戳_随机后缀
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
    scan_id = f"{timestamp}_{random_suffix}"

    workspace_dir = base_dir / scan_id
    report_dir = workspace_dir / "report"
    cache_dir = workspace_dir / "cache"
    decisions_dir = workspace_dir / "decisions"

    report_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    decisions_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"工作空间已创建: {workspace_dir}")

    return {
        "scan_id": scan_id,
        "workspace_dir": workspace_dir,
        "report_dir": report_dir,
        "cache_dir": cache_dir,
        "decisions_dir": decisions_dir,
    }


def init_harness_components(harness_config: dict) -> dict:
    """根据 harness 配置初始化各组件

    Returns:
        {"decision_logger": DecisionLogger|None,
         "feedback_manager": FeedbackManager|None,
         "quality_monitor": QualityMonitor|None}
    """
    result = {
        "decision_logger": None,
        "feedback_manager": None,
        "quality_monitor": None,
    }

    harness = harness_config.get("harness", {})
    if not harness.get("enabled", False):
        return result

    # 初始化决策日志
    dl_config = harness.get("decision_logging", {})
    if dl_config.get("enabled", False) and DecisionLogger is not None:
        result["decision_logger"] = DecisionLogger(
            storage_dir=dl_config.get("storage_dir", "data/decisions")
        )

    # 初始化反馈管理（全局路径 + workspace 路径）
    fb_config = harness.get("feedback", {})
    if fb_config.get("enabled", False) and FeedbackManager is not None:
        result["feedback_manager"] = FeedbackManager(
            storage_file=fb_config.get("storage_file", "data/feedbacks.json"),
            workspace_storage_file=fb_config.get("workspace_storage_file")
        )

    # 初始化质量监控（依赖前两个组件）
    qm_config = harness.get("quality_monitor", {})
    if qm_config.get("enabled", False) and QualityMonitor is not None:
        if result["decision_logger"] and result["feedback_manager"]:
            result["quality_monitor"] = QualityMonitor(
                decision_logger=result["decision_logger"],
                feedback_manager=result["feedback_manager"],
                cache_file=qm_config.get("cache_file", "data/stats_cache.json"),
            )

    return result


def build_feedback_examples(feedback_manager, max_examples: int = 10) -> list:
    """从 FeedbackManager 提取近期反馈示例

    取最近的 max_examples 条反馈，附加到 AI 评审提示词中。

    Returns:
        [{"issue_id": str, "verdict": str, "comment": str|None, "timestamp": str}]
    """
    all_feedbacks = feedback_manager.get_all_feedbacks()
    # 按时间倒序取最近的
    recent = sorted(all_feedbacks, key=lambda f: f.get("timestamp", ""), reverse=True)
    return recent[:max_examples]


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

    logger.info(f"=" * 60)
    logger.info(f"代码评审扫描启动")
    logger.info(f"  仓库: {args.repo}")
    logger.info(f"  基线分支: {args.base}")
    logger.info(f"  目标分支: {args.target}")
    logger.info(f"  规约 Profile: {args.profile}")
    logger.info(f"  输出目录: {output_dir}")
    if hasattr(args, "workflow"):
        logger.info(f"  AI 工作流: {args.workflow}")
    logger.info(f"=" * 60)

    # 2. 差异分析
    logger.info("[1/5] 执行分支差异分析...")
    diff_analyzer = DiffAnalyzer(args.repo)
    diff_result = diff_analyzer.analyze(args.base, args.target)
    logger.info(
        f"  发现 {len(diff_result['changed_files'])} 个变更文件, "
        f"{len(diff_result['changed_methods'])} 个变更方法"
    )

    if not diff_result["changed_files"]:
        logger.info("无代码变更，扫描结束。")
        return

    # 3. 调用图构建
    logger.info("[2/5] 构建调用图与血缘分析...")
    cg_builder = CallGraphBuilder(args.repo, language=args.language)
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

    # 4.5 Prefilter 白名单过滤（P0-3 修复）
    raw_issues = prefilter_issues(raw_issues, config)

    # 5. AI 增强评审（可选）
    issues = raw_issues
    if config.get("ai_review", {}).get("enabled", False):
        logger.info("[4/5] AI 增强评审...")
        ai_config = config.get("ai_review", {})
        # 从命令行参数获取工作流
        if hasattr(args, "workflow"):
            ai_config["workflow"] = args.workflow
        ai_reviewer = AIReviewer(ai_config)
        issues = ai_reviewer.review(raw_issues, diff_result, call_graph)
        logger.info(f"  工作流: {ai_reviewer.get_current_workflow()}")
        logger.info(f"  AI 过滤后剩余 {len(issues)} 个问题")
    else:
        logger.info("[4/5] AI 增强评审已跳过（未启用）")

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
    report = generator.generate(
        scan_info={
            "repo": args.repo,
            "base_branch": args.base,
            "target_branch": args.target,
            "profile": args.profile,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(time.time() - start_time, 2),
        },
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
        """,
    )

    parser.add_argument("--repo", required=True, help="Git 仓库路径")
    parser.add_argument("--base", required=True, help="基线分支（如 master）")
    parser.add_argument("--target", required=True, help="目标分支（如 release/1.0）")
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

    args = parser.parse_args()

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
