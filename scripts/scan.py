#!/usr/bin/env python3
"""
代码评审工具 - 主扫描入口
用法: python scripts/scan.py --repo <repo-path> --base master --target release/1.0 --profile default
"""

import argparse
import json
import yaml
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

# Harness 模块（可选依赖）
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
# 配置加载
# ============================================================
def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
    
# ============================================================
# 预过滤机制（可配置，可回退）
# ============================================================
def prefilter_issues(issues, config=None):
    """预过滤：对显式误报规则用确定性引擎过滤
    
    Args:
        issues: 扫描结果列表
        config: 配置字典，包含 prefilter.enabled 和 prefilter.rules
        
    Returns:
        (already_decided, to_review): 
        - already_decided: 已预过滤的问题（is_false_positive 或 needs_review 已设置）
        - to_review: 待 AI 评审的问题
    """
    # 检查是否启用预过滤
    if config and config.get('prefilter', {}).get('enabled', False):
        prefilter_config = config.get('prefilter', {})
        rules = prefilter_config.get('rules', {})
    else:
        # 预过滤未启用，返回原始数据
        return [], issues
    
    already_decided = []
    to_review = []
    
    for issue in issues:
        rule_id = issue.get('rule_id', '')
        file = issue.get('file', '')
        code_snippet = issue.get('code_snippet', '')
        
        filtered = False
        
        # 规则 1: sqli-mybatis-dollar
        if rules.get('sqli-mybatis-dollar', {}).get('enabled', False):
            if rule_id == 'sqli-mybatis-dollar':
                if file.endswith('pom.xml') or file.endswith('.xml'):
                    if '${' in code_snippet and '}' in code_snippet:
                        issue['is_false_positive'] = True
                        issue['ai_confidence'] = 0.99
                        issue['analysis'] = 'Maven 属性占位符（如 ${project.version}），非 SQL 注入'
                        issue['prefilter_reason'] = 'sqli-mybatis-dollar in pom.xml'
                        already_decided.append(issue)
                        filtered = True
        
        # 规则 2: crypto-hardcoded-key-java
        if not filtered and rules.get('crypto-hardcoded-key-java', {}).get('enabled', False):
            if rule_id == 'crypto-hardcoded-key-java':
                if 'Constants' in file or 'constants' in file.lower():
                    issue['is_false_positive'] = True
                    issue['ai_confidence'] = 0.95
                    issue['analysis'] = '常量类中的配置项 key（如 "password" 作为配置键名），非真实密钥'
                    issue['prefilter_reason'] = 'crypto-hardcoded-key in Constants class'
                    already_decided.append(issue)
                    filtered = True
        
        # 规则 3: naming-* 规则
        if not filtered and rules.get('naming-*', {}).get('enabled', False):
            if rule_id.startswith('naming-'):
                issue['is_false_positive'] = True
                issue['ai_confidence'] = 0.90
                issue['analysis'] = '命名风格偏好，非安全/质量缺陷'
                issue['prefilter_reason'] = 'naming-* style rule'
                already_decided.append(issue)
                filtered = True
        
        # 规则 4: code_snippet 长度检查（只对需要上下文的规则生效）
        # 只对以下规则生效：null-java-*, path-traversal-*, xss-*, sqli-*
        context_aware_rules = ['null-java-', 'path-traversal-', 'xss-', 'sqli-']
        if not filtered and rules.get('short-code-snippet', {}).get('enabled', False):
            if any(rule_id.startswith(prefix) for prefix in context_aware_rules):
                if len(code_snippet.split('\n')) < 5:
                    issue['needs_review'] = True
                    issue['analysis'] = '代码片段过短（< 5 行），上下文不足，建议人工审查'
                    issue['prefilter_reason'] = 'code_snippet too short'
                    already_decided.append(issue)
                    filtered = True
        
        # 其他规则：交给 AI 评审
        if not filtered:
            to_review.append(issue)
    
    return already_decided, to_review

def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
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
    
    Args:
        repo_path: 被扫描项目的路径（用于确定工作空间位置）
        base_dir: 工作空间基础目录（如指定则覆盖 repo_path 的默认行为）
        
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
            # 默认：在被扫描项目下创建 .code-review/workspace/
            base_dir = Path(repo_path).resolve() / ".code-review" / "workspace"
        else:
            # 回退：在 code-review-skill 项目下
            project_root = Path(__file__).parent.parent
            base_dir = project_root / ".code-review" / "workspace"
    
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成 scan_id: 时间戳_随机后缀
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
    scan_id = f"{timestamp}_{random_suffix}"
    
    # 创建工作空间目录结构
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

    # 初始化反馈管理
    fb_config = harness.get("feedback", {})
    if fb_config.get("enabled", False) and FeedbackManager is not None:
        result["feedback_manager"] = FeedbackManager(
            storage_file=fb_config.get("storage_file", "data/feedbacks.json")
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
# 主扫描流程
# ============================================================
def run_scan(args):
    """执行完整扫描流程"""
    start_time = time.time()

    # 0. 创建工作空间（在被扫描项目下）
    workspace = create_workspace(repo_path=args.repo)
    scan_id = workspace["scan_id"]
    output_dir = workspace["report_dir"]  # 报告输出到工作空间
    cache_dir = workspace["cache_dir"]
    decisions_dir = workspace["decisions_dir"]

    # 1. 加载配置
    config = load_config(args.config)
    specs_dir = args.specs_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references"
    )
    profile = load_profile(args.profile, specs_dir)

    # 确定扫描模式
    is_full_scan = getattr(args, "full_scan", False)

    logger.info(f"=" * 60)
    logger.info(f"代码评审扫描启动")
    logger.info(f"  Scan ID: {scan_id}")
    logger.info(f"  仓库: {args.repo}")
    if is_full_scan:
        logger.info(f"  扫描模式: 全库静态分析")
    else:
        logger.info(f"  基线分支: {args.base}")
        logger.info(f"  目标分支: {args.target}")
    logger.info(f"  规约 Profile: {args.profile}")
    logger.info(f"  工作空间: {workspace['workspace_dir']}")
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

    # 5. 初始化 Harness 组件（使用工作空间的 decisions_dir）
    harness_config = load_harness_config()
    # 覆盖 decisions_dir 为工作空间目录
    harness_config["harness"]["decision_logging"]["storage_dir"] = str(decisions_dir)
    harness_config["harness"]["feedback"]["storage_file"] = str(workspace["workspace_dir"] / "feedbacks.json")
    harness_config["harness"]["quality_monitor"]["cache_file"] = str(workspace["workspace_dir"] / "stats_cache.json")
    harness_components = init_harness_components(harness_config)
    decision_logger = harness_components["decision_logger"]
    feedback_manager = harness_components["feedback_manager"]

    if decision_logger:
        logger.info("  Harness: 决策日志已启用")
    if feedback_manager:
        logger.info("  Harness: 反馈管理已启用")

    # 6. 生成 Subagent 评审任务
    issues = raw_issues
    logger.info("[4/5] 生成 Subagent 评审任务...")
    ai_config = {}
    # 从命令行参数获取工作流
    if hasattr(args, "workflow"):
        ai_config["workflow"] = args.workflow

    # 注入历史反馈数据到 AI 评审器
    if feedback_manager:
        ai_config["feedback_summary"] = feedback_manager.get_feedback_summary()
        ai_config["feedback_examples"] = build_feedback_examples(feedback_manager)

    ai_reviewer = AIReviewer(ai_config)

    # 预过滤：对显式误报规则用确定性引擎过滤
    already_decided, to_review = prefilter_issues(raw_issues, config)
    logger.info(f"  预过滤: {len(already_decided)} 条已决定，{len(to_review)} 条待 AI 评审")
    
    # 生成 subagent 任务描述（只包含待 AI 评审的问题）
    task = ai_reviewer.generate_subagent_task(to_review, diff_result, call_graph)

    # 保存任务到文件
    task_file = output_dir / "subagent-review-task.md"
    ai_reviewer.save_task_to_file(task, str(task_file))

    logger.info(f"  工作流: {ai_reviewer.get_current_workflow()}")
    logger.info(f"  Subagent 任务已保存到: {task_file}")
    logger.info(f"  请 TRAE Agent 委派 subagent 读取该文件并执行评审")

    # 7. 记录决策日志
    if decision_logger:
        # 使用工作空间的 scan_id
        decision_logger.start_scan(
            repo=args.repo,
            workflow=getattr(args, "workflow", "comprehensive"),
            total_issues=len(raw_issues),
        )
        for idx, issue in enumerate(raw_issues):
            decision_logger.log_decision(
                issue_id=f"{scan_id}-{idx:04d}",
                rule_id=issue.get("rule_id", "unknown"),
                file=issue.get("file", ""),
                line=issue.get("line", 0),
                severity=issue.get("severity", "UNKNOWN"),
                original_message=issue.get("message", ""),
                ai_action="keep",
                ai_confidence=issue.get("ai_confidence", 0.8),
                ai_reasoning=issue.get("analysis", "规则引擎检出，待 AI 二次评审"),
                ai_evidence=[issue.get("code_snippet", "")] if issue.get("code_snippet") else [],
            )
        decision_logger.save()
        logger.info(f"  决策日志已记录 ({len(raw_issues)} 条，scan_id={scan_id})")

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
  python scripts/scan.py --repo ./my-project --base master --target HEAD --profile strict

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
