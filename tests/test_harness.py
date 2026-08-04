#!/usr/bin/env python3
"""
Harness 模块测试
验证决策日志、反馈管理、质量统计的完整流程
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.decision_logger import DecisionLogger
from harness.feedback_manager import FeedbackManager
from harness.quality_monitor import QualityMonitor


def test_decision_logger():
    """测试决策日志"""
    print("=== 测试 DecisionLogger ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = DecisionLogger(storage_dir=tmpdir)
        
        # 开始扫描
        scan_id = logger.start_scan(repo="/test/repo", workflow="security", total_issues=3)
        print(f"✓ 开始扫描: {scan_id}")
        
        # 记录决策
        logger.log_decision(
            issue_id="issue-001",
            rule_id="sqli-java-string-concat",
            file="src/UserService.java",
            line=42,
            severity="ERROR",
            original_message="SQL 注入 - 字符串拼接构建 SQL",
            ai_action="keep",
            ai_confidence=0.85,
            ai_reasoning="该代码使用字符串拼接构建 SQL，确认为真实问题",
            ai_evidence=["第 42 行：String sql = \"SELECT * FROM users WHERE id = \" + userId;"],
        )
        
        logger.log_decision(
            issue_id="issue-002",
            rule_id="xxe-java-document-builder",
            file="src/XmlParser.java",
            line=15,
            severity="ERROR",
            original_message="XXE - DocumentBuilder 解析 XML 未禁用外部实体",
            ai_action="filter_false_positive",
            ai_confidence=0.72,
            ai_reasoning="已在第 10 行禁用外部实体",
            ai_evidence=["第 10 行：factory.setFeature(...)"],
        )
        
        logger.log_decision(
            issue_id="issue-003",
            rule_id="xss-js-innerhtml",
            file="src/app.js",
            line=88,
            severity="WARNING",
            original_message="XSS - innerHTML 直接赋值",
            ai_action="keep",
            ai_confidence=0.65,
            ai_reasoning="使用 innerHTML 赋值用户输入",
            ai_evidence=["第 88 行：element.innerHTML = userInput;"],
        )
        
        print(f"✓ 记录了 3 个决策")
        
        # 保存
        filepath = logger.save()
        print(f"✓ 保存到: {filepath}")
        
        # 加载验证
        data = logger.load(scan_id)
        assert data["total_issues"] == 3
        assert len(data["decisions"]) == 3
        print(f"✓ 加载验证通过")
        
        # 列出扫描
        scans = logger.list_scans()
        assert len(scans) == 1
        assert scans[0] == scan_id
        print(f"✓ 列出扫描: {scans}")
    
    print("✅ DecisionLogger 测试通过\n")


def test_feedback_manager():
    """测试反馈管理"""
    print("=== 测试 FeedbackManager ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_file = os.path.join(tmpdir, "feedbacks.json")
        fm = FeedbackManager(storage_file=storage_file)
        
        # 添加反馈
        f1 = fm.add_feedback("issue-001", "scan-001", "confirmed", "确认是真实问题")
        f2 = fm.add_feedback("issue-002", "scan-001", "false_positive", "AI 判断错误")
        f3 = fm.add_feedback("issue-003", "scan-001", "uncertain")
        
        print(f"✓ 添加了 3 个反馈")
        
        # 查询反馈
        all_feedbacks = fm.get_all_feedbacks()
        assert len(all_feedbacks) == 3
        print(f"✓ 查询所有反馈: {len(all_feedbacks)} 个")
        
        scan_feedbacks = fm.get_feedbacks_for_scan("scan-001")
        assert len(scan_feedbacks) == 3
        print(f"✓ 查询扫描反馈: {len(scan_feedbacks)} 个")
        
        issue_feedbacks = fm.get_feedbacks_for_issue("issue-001")
        assert len(issue_feedbacks) == 1
        assert issue_feedbacks[0]["verdict"] == "confirmed"
        print(f"✓ 查询问题反馈: {issue_feedbacks[0]['verdict']}")
        
        # 统计摘要
        summary = fm.get_feedback_summary()
        assert summary["total"] == 3
        assert summary["confirmed"] == 1
        assert summary["false_positive"] == 1
        assert summary["uncertain"] == 1
        print(f"✓ 统计摘要: {summary}")
    
    print("✅ FeedbackManager 测试通过\n")


def test_quality_monitor():
    """测试质量监控"""
    print("=== 测试 QualityMonitor ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        decisions_dir = os.path.join(tmpdir, "decisions")
        feedbacks_file = os.path.join(tmpdir, "feedbacks.json")
        cache_file = os.path.join(tmpdir, "stats_cache.json")
        
        # 创建决策日志
        logger = DecisionLogger(storage_dir=decisions_dir)
        scan_id = logger.start_scan(repo="/test/repo", workflow="security", total_issues=3)
        
        # 记录 3 个决策
        logger.log_decision(
            issue_id="issue-001", rule_id="sqli-java", file="a.java", line=1,
            severity="ERROR", original_message="SQL 注入",
            ai_action="keep", ai_confidence=0.85, ai_reasoning="真实问题",
        )
        logger.log_decision(
            issue_id="issue-002", rule_id="xxe-java", file="b.java", line=2,
            severity="ERROR", original_message="XXE",
            ai_action="filter_false_positive", ai_confidence=0.72, ai_reasoning="误报",
        )
        logger.log_decision(
            issue_id="issue-003", rule_id="xss-js", file="c.js", line=3,
            severity="WARNING", original_message="XSS",
            ai_action="keep", ai_confidence=0.65, ai_reasoning="真实问题",
        )
        logger.save()
        
        # 创建反馈
        fm = FeedbackManager(storage_file=feedbacks_file)
        fm.add_feedback("issue-001", scan_id, "confirmed")  # AI 正确
        fm.add_feedback("issue-002", scan_id, "confirmed")  # AI 错误（AI 过滤了，但用户确认）
        fm.add_feedback("issue-003", scan_id, "false_positive")  # AI 错误（AI 保留了，但用户认为是误报）
        
        # 创建质量监控
        monitor = QualityMonitor(logger, fm, cache_file=cache_file)
        
        # 计算准确率
        accuracy = monitor.calculate_accuracy()
        print(f"✓ 总体准确率: {accuracy}")
        
        # 按规则计算准确率
        by_rule = monitor.calculate_accuracy_by_rule()
        print(f"✓ 按规则准确率: {by_rule}")
        
        # 生成报告
        report = monitor.generate_report()
        print(f"✓ 生成报告:\n{report}")
        
        # 保存缓存
        monitor.save_cache()
        assert os.path.exists(cache_file)
        print(f"✓ 保存缓存: {cache_file}")
    
    print("✅ QualityMonitor 测试通过\n")


def test_end_to_end():
    """端到端测试：模拟完整的 AI 评审 + 用户反馈流程"""
    print("=== 端到端测试 ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        decisions_dir = os.path.join(tmpdir, "decisions")
        feedbacks_file = os.path.join(tmpdir, "feedbacks.json")
        cache_file = os.path.join(tmpdir, "stats_cache.json")
        
        # Step 1: AI 评审，记录决策
        print("\n[Step 1] AI 评审，记录决策")
        logger = DecisionLogger(storage_dir=decisions_dir)
        scan_id = logger.start_scan(repo="/test/repo", workflow="security", total_issues=5)
        
        for i in range(1, 6):
            logger.log_decision(
                issue_id=f"issue-{i:03d}",
                rule_id=f"rule-{i}",
                file=f"file{i}.java",
                line=i * 10,
                severity="ERROR",
                original_message=f"问题 {i}",
                ai_action="keep" if i % 2 == 1 else "filter_false_positive",
                ai_confidence=0.7 + i * 0.05,
                ai_reasoning=f"AI 分析理由 {i}",
                ai_evidence=[f"证据 {i}"],
            )
        logger.save()
        print(f"  ✓ 记录了 5 个决策")
        
        # Step 2: 用户反馈
        print("\n[Step 2] 用户反馈")
        fm = FeedbackManager(storage_file=feedbacks_file)
        
        # 用户确认 AI 的判断
        fm.add_feedback("issue-001", scan_id, "confirmed")  # AI keep → 用户确认 ✓
        fm.add_feedback("issue-002", scan_id, "false_positive")  # AI filter → 用户确认 ✓
        fm.add_feedback("issue-003", scan_id, "false_positive")  # AI keep → 用户说误报 ✗
        fm.add_feedback("issue-004", scan_id, "confirmed")  # AI filter → 用户说确认 ✗
        # issue-005 没有反馈
        
        print(f"  ✓ 添加了 4 个反馈")
        
        # Step 3: 查看质量统计
        print("\n[Step 3] 查看质量统计")
        monitor = QualityMonitor(logger, fm, cache_file=cache_file)
        
        accuracy = monitor.calculate_accuracy()
        print(f"  总决策数: {accuracy['total_decisions']}")
        print(f"  总反馈数: {accuracy['total_feedbacks']}")
        print(f"  有反馈的决策: {accuracy['total_with_feedback']}")
        print(f"  正确判断: {accuracy['correct']}")
        print(f"  错误判断: {accuracy['incorrect']}")
        print(f"  准确率: {accuracy['accuracy']:.1%}")
        
        # 验证：issue-001 (keep→confirmed=正确), issue-002 (filter→false_positive=正确)
        # issue-003 (keep→false_positive=错误), issue-004 (filter→confirmed=错误)
        assert accuracy['correct'] == 2, f"Expected 2 correct, got {accuracy['correct']}"
        assert accuracy['incorrect'] == 2, f"Expected 2 incorrect, got {accuracy['incorrect']}"
        assert accuracy['accuracy'] == 0.5, f"Expected 50% accuracy, got {accuracy['accuracy']}"
        
        print(f"  ✓ 准确率验证通过 (50%)")
        
        # Step 4: 生成报告
        print("\n[Step 4] 生成报告")
        report = monitor.generate_report()
        print(report)
    
    print("\n✅ 端到端测试通过\n")


if __name__ == "__main__":
    test_decision_logger()
    test_feedback_manager()
    test_quality_monitor()
    test_end_to_end()
    
    print("=" * 60)
    print("所有测试通过！")
    print("=" * 60)
