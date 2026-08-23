#!/usr/bin/env python3
"""
子 Agent 评审任务文件生成测试

验证 generate_subagent_task() 的内容契约，对齐
docs/VERIFICATION_MATRIX.md P-01 ~ P-05 验证要求：
- P-01: 包含历史反馈统计（总反馈数/确认/误报）
- P-02: 包含历史准确率
- P-03: 包含近期反馈示例
- P-04: 输出字段要求 evidence
- P-05: 要求提供决策理由
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai_reviewer import AIReviewer


def make_reviewer(workflow="security"):
    return AIReviewer({"workflow": workflow})


def sample_issues():
    return [
        {
            "rule_id": "xss-reflected",
            "file": "src/main/java/org/app/Render.java",
            "line": 42,
            "severity": "HIGH",
            "message": "反射型 XSS 风险",
            "engine": "ast",
            "engines": ["ast", "semgrep"],
        },
        {
            "rule_id": "path-write-traversal",
            "file": "src/main/java/org/app/Store.java",
            "line": 100,
            "severity": "CRITICAL",
            "message": "路径穿越写入",
            "engine": "semgrep",
            "engines": ["semgrep"],
        },
    ]


def sample_feedback_summary():
    return {"total": 4, "confirmed": 2, "false_positive": 2, "uncertain": 0}


def sample_feedback_examples():
    return [
        {
            "issue_id": "scan-1-0001",
            "verdict": "confirmed",
            "comment": "确实是注入点",
            "timestamp": "2026-08-20T10:00:00",
        },
        {
            "issue_id": "scan-1-0002",
            "verdict": "false_positive",
            "comment": None,
            "timestamp": "2026-08-21T11:00:00",
        },
    ]


class TestSubagentTaskContent:
    """内容契约（P-01 ~ P-05）"""

    def test_generates_task_file_on_disk(self, tmp_path):
        reviewer = make_reviewer()
        out = tmp_path / "report" / "subagent-review-task.md"
        reviewer.generate_subagent_task(
            issues=sample_issues(),
            scan_info={"repo": "demo-repo", "base": "master",
                       "target": "release/1.0", "profile": "default"},
            feedback_summary=sample_feedback_summary(),
            feedback_examples=sample_feedback_examples(),
            output_path=str(out),
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "子 Agent 评审任务" in content

    def test_p01_feedback_stats(self):
        """P-01: 历史反馈统计"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(
            issues=[],
            feedback_summary=sample_feedback_summary(),
        )
        assert "历史反馈统计" in content
        assert "总反馈数: 4" in content
        assert "确认: 2" in content
        assert "误报: 2" in content

    def test_p02_accuracy(self):
        """P-02: 历史准确率 = confirmed / (confirmed + false_positive)"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(
            issues=[],
            feedback_summary=sample_feedback_summary(),
        )
        assert "历史准确率: 50.0%" in content

    def test_p02_accuracy_no_data(self):
        """无已判定反馈时显示暂无数据，不能除零"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(
            issues=[],
            feedback_summary={"total": 0, "confirmed": 0,
                              "false_positive": 0, "uncertain": 0},
        )
        assert "历史准确率: 暂无数据" in content

    def test_p03_feedback_examples(self):
        """P-03: 近期反馈示例"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(
            issues=[],
            feedback_summary=sample_feedback_summary(),
            feedback_examples=sample_feedback_examples(),
        )
        assert "近期反馈示例" in content
        assert "scan-1-0001" in content
        assert "confirmed" in content
        assert "无备注" in content  # comment 为 None 的兜底

    def test_p04_evidence_field(self):
        """P-04: 字段契约包含 evidence"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(issues=[])
        assert '"evidence"' in content
        assert "证据列表（引用具体代码行或上下文）" in content

    def test_p05_decision_reasoning(self):
        """P-05: 要求决策理由"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(issues=[])
        assert "决策理由" in content

    def test_field_contract_complete(self):
        """字段契约完整：is_false_positive / ai_confidence / analysis / enhanced_fix"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(issues=[])
        for field in ("is_false_positive", "ai_confidence",
                      "analysis", "enhanced_fix"):
            assert field in content, f"缺少字段契约: {field}"

    def test_temperature_included(self):
        """任务文件必须写明温度参数（security 工作流 = 0.1）"""
        reviewer = make_reviewer("security")
        content = reviewer.generate_subagent_task(issues=[])
        assert "温度参数" in content
        assert "0.1" in content

    def test_issue_list_rendered(self):
        """候选问题清单完整渲染，含引擎与多引擎互证标记"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(
            issues=sample_issues(),
            feedback_summary={"total": 0, "confirmed": 0,
                              "false_positive": 0, "uncertain": 0},
        )
        assert "xss-reflected" in content
        assert "Render.java:42" in content
        assert "多引擎互证" in content
        assert "待评审问题清单" in content

    def test_empty_issues_note(self):
        """无候选问题时给出明确提示"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(issues=[])
        assert "无候选问题" in content

    def test_delegation_contract_statement(self):
        """写明主 Agent 必须委派、不能自己评审"""
        reviewer = make_reviewer()
        content = reviewer.generate_subagent_task(issues=[])
        assert "Task 工具" in content
        assert "不能自己直接评审" in content
