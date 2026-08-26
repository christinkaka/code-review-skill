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

    # 默认白名单规则（17 类）
    # 覆盖主流测试文件约定（双盲测试 Spring Boot 实测发现 359 个 path-traversal
    # 命中几乎全在测试文件，故扩展以下模式）：
    # - 标准目录: test/**、tests/**、__tests__/**（Maven/Gradle/JS）、spec/**（rspec）
    # - 自定义 source set: dockerTest/**、integrationTest/**（Spring Boot 等）
    # - JUnit 命名: *Test.*（单数）、*Tests.*（复数）、*IT.*（Failsafe）、*TestCase.*
    # - pytest: test_*.py、*_test.py
    # - 前端/Ruby: *.spec.*、*.test.*、*Spec.*
    # - 2026-08-25 盲评补充: smoke-test/**、test-support/**、testFixtures/**
    #   （spring-boot 实测：冒烟/测试支撑源集目录，非生产代码）
    file_patterns = whitelist.get("file_patterns", [
        "**/test/**",
        "**/tests/**",
        "**/dockerTest/**",
        "**/integrationTest/**",
        "**/smoke-test/**",
        "**/test-support/**",
        "**/testFixtures/**",
        "**/*_test.*",
        "**/*Test.*",
        "**/*Tests.*",
        "**/*IT.*",
        "**/*TestCase.*",
        "**/test_*.py",
        "**/*.spec.*",
        "**/*.test.*",
        "**/*Spec.*",
        "**/__tests__/**",
        "**/spec/**",
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


def tiered_ai_review(ai_reviewer, raw_issues, diff_result, call_graph, tiered=True):
    """分层评审：CRITICAL/HIGH/ERROR 进 LLM 精审，WARNING/INFO 直接保留（统计层）

    P0 降噪策略（2026-08-24 双盲实测驱动：WARNING+INFO 占检出近半，
    逐条送 LLM 成本高且报告可读性差）。

    Args:
        ai_reviewer: AIReviewer 实例
        raw_issues: Prefilter 后的候选问题列表
        diff_result: DiffAnalyzer 结果
        call_graph: CallGraphBuilder 结果
        tiered: False 则全量送 LLM（旧行为）

    Returns:
        (issues, triage): 合并后的问题列表 + 分层统计
    """
    # 需 LLM 精审的严重级别（实际枚举: CRITICAL/HIGH/ERROR/WARNING/INFO）
    review_tier = ("CRITICAL", "HIGH", "ERROR")
    triage = {"reviewed": len(raw_issues), "stats_only": 0}
    if not tiered:
        return ai_reviewer.review(raw_issues, diff_result, call_graph), triage

    high = [i for i in raw_issues if i.get("severity") in review_tier]
    low = [i for i in raw_issues if i.get("severity") not in review_tier]
    triage = {"reviewed": len(high), "stats_only": len(low)}

    reviewed = ai_reviewer.review(high, diff_result, call_graph) if high else []
    if not isinstance(reviewed, list):
        reviewed = list(reviewed or [])
    return reviewed + low, triage


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
# 子 Agent 评审结果合并（单评审员 + 多评审员投票）
# ============================================================
def _issue_key(rule_id: str, file: str, line) -> tuple:
    """问题的唯一标识（line 容错 str/int）"""
    try:
        line = int(line)
    except (TypeError, ValueError):
        pass
    return (rule_id, str(file), line)


def _aggregate_votes(vote_lists: list, votes: int) -> tuple:
    """
    聚合 N 份子 Agent 评审结果（多数票投票，Self-Consistency）。

    语义（对齐 API 路径 AIReviewer._review_with_voting）：
    - majority = votes // 2 + 1（3 票需 >= 2 票）
    - FP 票 >= majority      → 判误报（键进 dropped_keys，由合并层滤除）
    - TP 票 >= majority      → 保留，字段取 TP 票中 ai_confidence 最高者
    - 无多数（平票/三向分歧/评审员覆盖不一致）→ 保守保留，needs_review=true
      （与 API 路径"平票全丢弃"不同：子 Agent 路径覆盖 WARNING/INFO 低级别，
      且漏报 CRITICAL 的代价高于多一条待人工复核的告警）

    某评审员缺席某条问题（未覆盖）视为该票缺席，不参与计数；
    缺席导致达不到多数时同样保守保留。

    Returns:
        (ai_results, dropped_keys, stats):
        聚合后的保留裁决列表（含 needs_review 项）、多数票判误报的键集合、统计
    """
    majority = votes // 2 + 1
    by_key = {}
    for vote_index, vote_list in enumerate(vote_lists):
        for ai in vote_list:
            key = _issue_key(ai.get("rule_id", ""), ai.get("file", ""), ai.get("line", 0))
            by_key.setdefault(key, []).append((vote_index, ai))

    results = []
    dropped_keys = set()
    stats = {"votes": votes, "majority": majority, "kept_tp": 0, "dropped_fp": 0, "kept_review": 0}

    for key, vote_items in by_key.items():
        tp_votes = [ai for _, ai in vote_items if not ai.get("is_false_positive", False) and not ai.get("needs_review", False)]
        fp_votes = [ai for _, ai in vote_items if ai.get("is_false_positive", False)]

        if len(fp_votes) >= majority:
            dropped_keys.add(key)
            stats["dropped_fp"] += 1
            continue
        if len(tp_votes) >= majority:
            best = max(tp_votes, key=lambda a: a.get("ai_confidence", 0))
            merged = dict(best)
            merged["vote"] = f"TP {len(tp_votes)}/{votes}"
            results.append(merged)
            stats["kept_tp"] += 1
            continue
        # 无多数：保守保留
        merged = dict(vote_items[0][1])
        merged["needs_review"] = True
        merged["vote"] = f"NO_MAJORITY (TP {len(tp_votes)}/FP {len(fp_votes)}/{votes})"
        results.append(merged)
        stats["kept_review"] += 1

    return results, dropped_keys, stats


def _merge_subagent_review(report: dict, output_dir: Path) -> dict:
    """
    合并子 Agent 评审结果到报告。

    支持两种模式：
    1. 单评审员：output_dir 下存在 ai-review-result.json（子 Agent 评审后产出）
    2. 多评审员投票：output_dir 下存在 ai-review-result-vote{N}.json（N >= 2，
       主 Agent 并行委派 N 个子 Agent 各产出一份），按多数票聚合

    两种模式均将 AI 字段（ai_confidence / analysis / enhanced_fix /
    is_false_positive / needs_review）合并到 report.issues 中对应条目，
    并过滤掉多数票认定误报的条目。

    匹配键：(rule_id, file, line) 精确匹配；若失败则回退到 (file, line)。

    Returns:
        合并后的报告字典（若无评审结果文件则原样返回）
    """
    # 收集投票文件（按编号排序）
    vote_files = sorted(
        output_dir.glob("ai-review-result-vote*.json"),
        key=lambda p: p.name,
    )

    vote_lists = []
    for vf in vote_files:
        try:
            with open(vf, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                vote_lists.append(data)
        except (json.JSONDecodeError, IOError) as err:
            logger.warning(f"投票文件读取失败（跳过该票）: {vf.name}: {err}")

    if vote_lists:
        ai_results, dropped_keys, stats = _aggregate_votes(vote_lists, len(vote_lists))
        logger.info(
            f"  子 Agent 投票聚合: {stats['votes']} 票, 多数阈值 {stats['majority']}, "
            f"TP 保留 {stats['kept_tp']}, FP 滤除 {stats['dropped_fp']}, "
            f"无多数保守保留 {stats['kept_review']}"
        )
    else:
        dropped_keys = set()
        # 单评审员模式（旧路径）
        ai_result_path = output_dir / "ai-review-result.json"
        if not ai_result_path.exists():
            return report

        try:
            with open(ai_result_path, "r", encoding="utf-8") as f:
                ai_results = json.load(f)
        except (json.JSONDecodeError, IOError) as err:
            logger.warning(f"AI 评审结果文件读取失败: {err}")
            return report

        if not isinstance(ai_results, list) or not ai_results:
            logger.debug("AI 评审结果为空，跳过合并")
            return report

    # 注意：投票模式下 ai_results 可能为空（全部判误报），dropped_keys 仍需生效，
    # 故该守卫只在单评审员分支内
    if not vote_lists and not ai_results:
        return report

    # 构建精确匹配索引：(rule_id, file, line) → ai_result
    ai_exact = {}
    ai_by_location = {}
    for ai in ai_results:
        rule_id = ai.get("rule_id", "")
        file = ai.get("file", "")
        line = ai.get("line", 0)
        if rule_id and file and line:
            try:
                line_no = int(line)
            except (TypeError, ValueError):
                line_no = line
            ai_exact[(rule_id, str(file), line_no)] = ai
            ai_by_location[(str(file), line_no)] = ai

    # 合并到 issues
    merged_issues = []
    merged_count = 0
    filtered_count = 0
    for issue in report.get("issues", []):
        rule_id = issue.get("rule_id", "")
        file = issue.get("file", "")
        line = issue.get("line", 0)

        try:
            line_no = int(line)
        except (TypeError, ValueError):
            line_no = line

        key = (rule_id, str(file), line_no)

        # 投票模式：多数票判误报 → 滤除（未进入 ai_results，需单独判定）
        if key in dropped_keys:
            filtered_count += 1
            logger.debug(f"  投票滤除误报: {rule_id} @ {file}:{line}")
            continue

        # 精确匹配优先，回退到位置匹配
        ai = ai_exact.get(key) or ai_by_location.get((str(file), line_no))

        if ai:
            # 过滤误报（needs_review=true 的保守保留项不滤除）
            if ai.get("is_false_positive", False) and not ai.get("needs_review", False):
                filtered_count += 1
                logger.debug(f"  过滤误报: {rule_id} @ {file}:{line}")
                continue

            # 合并 AI 字段
            for field in ("ai_confidence", "analysis", "enhanced_fix", "is_false_positive", "needs_review", "vote", "evidence"):
                if field in ai:
                    issue[field] = ai[field]
            merged_count += 1

        merged_issues.append(issue)

    if merged_count or filtered_count:
        logger.info(f"  子 Agent 评审合并: {merged_count} 条增强, {filtered_count} 条误报过滤")
        report["issues"] = merged_issues
        # 重新计算摘要
        report["summary"] = ReportGenerator(str(output_dir))._compute_summary(merged_issues)
        # 重新写 report.json
        json_path = output_dir / "report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"  报告已更新: {json_path}")

    return report


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

    # 4.6 生成子 Agent 评审任务文件（主 Agent 委派契约，见 main-agent-contract.md）
    try:
        task_config = dict(config.get("ai_review", {}))
        if hasattr(args, "workflow") and getattr(args, "workflow", None):
            task_config["workflow"] = args.workflow
        task_reviewer = AIReviewer(task_config)

        feedback_summary: dict = {}
        feedback_examples: list = []
        if FeedbackManager is not None:
            try:
                fm = FeedbackManager()
                feedback_summary = fm.get_feedback_summary()
                feedback_examples = build_feedback_examples(fm, max_examples=10)
            except Exception as fm_err:
                logger.debug(f"历史反馈数据加载失败（任务文件将显示暂无数据）: {fm_err}")

        task_path = output_dir / "subagent-review-task.md"
        task_reviewer.generate_subagent_task(
            issues=raw_issues,
            scan_info={
                "repo": args.repo,
                "base": args.base,
                "target": args.target,
                "profile": args.profile,
                "scan_time": datetime.now().isoformat(),
            },
            feedback_summary=feedback_summary,
            feedback_examples=feedback_examples,
            output_path=str(task_path),
        )
        logger.info(f"  子 Agent 评审任务文件: {task_path}")
    except Exception as task_err:
        logger.warning(f"子 Agent 任务文件生成失败（不影响主流程）: {task_err}")

    # 5. AI 增强评审（分层：CRITICAL/ERROR 精审，WARNING/INFO 统计层保留）
    issues = raw_issues
    if config.get("ai_review", {}).get("enabled", False):
        logger.info("[4/5] AI 增强评审（分层）...")
        ai_config = config.get("ai_review", {})
        # 从命令行参数获取工作流
        if hasattr(args, "workflow"):
            ai_config["workflow"] = args.workflow
        ai_reviewer = AIReviewer(ai_config)
        tiered = ai_config.get("tiered", True)
        issues, triage = tiered_ai_review(
            ai_reviewer, raw_issues, diff_result, call_graph, tiered=tiered
        )
        logger.info(f"  工作流: {ai_reviewer.get_current_workflow()}")
        logger.info(
            f"  分层: LLM 精审 {triage['reviewed']} 条, "
            f"统计层保留 {triage['stats_only']} 条"
        )
        logger.info(f"  AI 评审后 {len(issues)} 个问题")
        
        # Token 消耗统计
        token_stats = ai_reviewer.get_token_stats()
        if token_stats["call_count"] > 0:
            logger.info(
                f"  Token 消耗: {token_stats['total_tokens']:,} tokens "
                f"(prompt: {token_stats['prompt_tokens']:,}, "
                f"completion: {token_stats['completion_tokens']:,}, "
                f"calls: {token_stats['call_count']}, "
                f"model: {token_stats['model']})"
            )
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
    
    # 写入 token 统计到报告（如果有 AI 评审）
    if config.get("ai_review", {}).get("enabled", False) and 'ai_reviewer' in locals():
        report["token_stats"] = ai_reviewer.get_token_stats()
        # 重新写 report.json
        json_path = output_dir / "report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    # 8. 合并子 Agent 评审结果（如果存在）
    report = _merge_subagent_review(report, output_dir)

    # 9. 输出摘要
    summary = report.get("summary", {})
    logger.info(f"=" * 60)
    logger.info(f"扫描完成！耗时: {round(time.time() - start_time, 2)}s")
    logger.info(f"  总计问题: {summary.get('total', 0)}")
    logger.info(f"  CRITICAL: {summary.get('critical', 0)}")
    logger.info(f"  HIGH:     {summary.get('high', 0)}")
    logger.info(f"  MEDIUM:   {summary.get('medium', 0)}")
    logger.info(f"  LOW:      {summary.get('low', 0)}")
    ai_count = sum(1 for i in report.get("issues", []) if "ai_confidence" in i)
    if ai_count:
        logger.info(f"  AI 增强: {ai_count} 条检出已合并子 Agent 评审结果")
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
