#!/usr/bin/env python3
"""
AI 评审器审计轨迹测试 (P0-①)

核心诉求：
1. 每一个被 AI 过滤掉的问题都必须留痕（rule_id/文件/行号/原因/置信度）
2. LLM 解析失败时自动重试，重试耗尽后 fail-open 并留痕
3. 审计日志落盘为 JSONL，可事后追溯
4. 提供 get_audit_summary() 统计
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from ai_reviewer import AIReviewer


# ===================================================================
# 辅助构造
# ===================================================================

def make_config(tmp_path, audit_enabled=True, retries=2, threshold=0.7):
    """构造带审计配置的 AIReviewer 配置"""
    return {
        "llm": {
            "url": "https://api.openai.com/v1/chat/completions",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4",
        },
        "confidence_threshold": threshold,
        "audit": {
            "enabled": audit_enabled,
            "log_path": str(tmp_path / "ai_decisions.jsonl"),
        },
        "max_retries": retries,
    }


def make_issues():
    return [
        {
            "rule_id": "xxe-java-document-builder",
            "category": "security",
            "severity": "ERROR",
            "file": "src/Parser.java",
            "line": 42,
            "end_line": 45,
            "message": "XXE vulnerability",
            "code_snippet": "DocumentBuilderFactory factory = ...",
        },
        {
            "rule_id": "naming-convention",
            "category": "implementation",
            "severity": "WARNING",
            "file": "src/Utils.java",
            "line": 10,
            "end_line": 10,
            "message": "Variable name convention",
            "code_snippet": "String a = \"hello\";",
        },
    ]


def make_diff():
    return {"changed_files": [{"path": "src/Parser.java", "status": "modified"}]}


def llm_response_mock(content: str):
    """构造 urlopen mock，返回指定 content"""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"choices": [{"message": {"content": content}}]}
    ).encode("utf-8")
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ===================================================================
# 审计记录：被过滤的问题必须留痕
# ===================================================================

class TestDroppedIssueAudit:
    """被 AI 过滤的问题必须有审计记录"""

    def test_dropped_by_is_valid_false_recorded(self, tmp_path):
        """is_valid=False 被过滤的问题必须出现在审计记录中，含原因"""
        reviewer = AIReviewer(make_config(tmp_path))
        issues = make_issues()
        # LLM 判定第一个问题无效（is_valid=False），但置信度很高
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": False,
             "confidence": 0.9, "enhanced_fix": ""},
            {"rule_id": "naming-convention", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        dropped = [r for r in reviewer.audit_records
                   if r.get("decision") == "dropped"]
        assert len(dropped) == 1
        assert dropped[0]["rule_id"] == "xxe-java-document-builder"
        assert dropped[0]["file"] == "src/Parser.java"
        assert dropped[0]["line"] == 42
        assert dropped[0]["reason"] == "is_valid_false"
        assert dropped[0]["ai_confidence"] == 0.9

    def test_dropped_by_low_confidence_recorded(self, tmp_path):
        """置信度低于阈值被过滤的问题必须留痕，原因=low_confidence"""
        reviewer = AIReviewer(make_config(tmp_path))
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.4, "enhanced_fix": ""},
            {"rule_id": "naming-convention", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        dropped = [r for r in reviewer.audit_records
                   if r.get("decision") == "dropped"]
        assert len(dropped) == 1
        assert dropped[0]["rule_id"] == "xxe-java-document-builder"
        assert dropped[0]["reason"] == "low_confidence"
        assert dropped[0]["threshold"] == 0.7

    def test_kept_issue_recorded(self, tmp_path):
        """保留的问题也必须留痕（decision=kept）"""
        reviewer = AIReviewer(make_config(tmp_path))
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.95, "enhanced_fix": "fix it"},
            {"rule_id": "naming-convention", "is_valid": False,
             "confidence": 0.2, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        kept = [r for r in reviewer.audit_records if r.get("decision") == "kept"]
        assert len(kept) == 1
        assert kept[0]["rule_id"] == "xxe-java-document-builder"
        assert kept[0]["ai_confidence"] == 0.95

    def test_severity_recorded_for_rollback_analysis(self, tmp_path):
        """审计记录包含 severity，便于评估'误杀高严重度问题'的风险"""
        reviewer = AIReviewer(make_config(tmp_path))
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": False,
             "confidence": 0.9, "enhanced_fix": ""},
            {"rule_id": "naming-convention", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        dropped = [r for r in reviewer.audit_records if r.get("decision") == "dropped"]
        assert dropped[0]["severity"] == "ERROR"


# ===================================================================
# 审计日志落盘
# ===================================================================

class TestAuditLogPersistence:
    """审计日志必须落盘为 JSONL"""

    def test_jsonl_file_written(self, tmp_path):
        """审计日志写入 JSONL 文件，每行一个合法 JSON"""
        config = make_config(tmp_path)
        reviewer = AIReviewer(config)
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": ""},
            {"rule_id": "naming-convention", "is_valid": False,
             "confidence": 0.2, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        log_path = tmp_path / "ai_decisions.jsonl"
        assert log_path.exists()
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 2
        for line in lines:
            record = json.loads(line)  # 每行必须是合法 JSON
            assert "timestamp" in record
            assert "workflow" in record

    def test_audit_disabled_no_file(self, tmp_path):
        """audit.enabled=False 时不写文件，但仍保留内存记录"""
        config = make_config(tmp_path, audit_enabled=False)
        reviewer = AIReviewer(config)
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": ""},
            {"rule_id": "naming-convention", "is_valid": False,
             "confidence": 0.2, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        assert not (tmp_path / "ai_decisions.jsonl").exists()
        assert len(reviewer.audit_records) >= 2


# ===================================================================
# LLM 失败事件留痕 + 重试
# ===================================================================

class TestLLMFailureAudit:
    """LLM 调用/解析失败必须留痕"""

    def test_llm_call_failure_recorded_fail_open(self, tmp_path):
        """LLM 调用失败：原样返回（fail-open），且审计记录 batch 事件"""
        reviewer = AIReviewer(make_config(tmp_path, retries=1))
        issues = make_issues()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen",
                       side_effect=ConnectionError("network down")):
                result = reviewer.review(issues, make_diff(), {})

        assert result == issues  # fail-open
        events = [r for r in reviewer.audit_records
                  if r.get("event") == "llm_call_failed"]
        assert len(events) == 1
        assert events[0]["fail_open"] is True

    def test_parse_failure_retry_then_success(self, tmp_path):
        """解析失败自动重试：第一次返回垃圾，第二次返回合法 JSON"""
        reviewer = AIReviewer(make_config(tmp_path, retries=2))
        issues = make_issues()
        good_response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": "x"},
            {"rule_id": "naming-convention", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": "x"},
        ])
        # 第一次垃圾，第二次合法
        responses = [
            llm_response_mock("garbage not json"),
            llm_response_mock(good_response),
        ]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen",
                       side_effect=responses):
                result = reviewer.review(issues, make_diff(), {})

        assert len(result) == 2  # 重试成功，全部保留
        retried = [r for r in reviewer.audit_records
                   if r.get("event") == "parse_retry"]
        assert len(retried) >= 1

    def test_retry_exhausted_fail_open_recorded(self, tmp_path):
        """重试耗尽：返回原始问题（fail-open），审计记录 fail_open"""
        reviewer = AIReviewer(make_config(tmp_path, retries=2))
        issues = make_issues()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen",
                       side_effect=ConnectionError("still down")):
                result = reviewer.review(issues, make_diff(), {})

        assert result == issues
        events = [r for r in reviewer.audit_records
                  if r.get("event") == "llm_call_failed"]
        assert len(events) == 1
        assert events[0]["attempts"] == 1 + 2  # 初次 + 2 次重试

    def test_parse_retry_exhausted_fail_open(self, tmp_path):
        """解析重试耗尽：返回原始问题并留痕"""
        reviewer = AIReviewer(make_config(tmp_path, retries=1))
        issues = make_issues()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen",
                       return_value=llm_response_mock("always garbage")):
                result = reviewer.review(issues, make_diff(), {})

        assert result == issues
        events = [r for r in reviewer.audit_records
                  if r.get("event") == "parse_failed"]
        assert len(events) == 1
        assert events[0]["fail_open"] is True


# ===================================================================
# 审计统计
# ===================================================================

class TestAuditSummary:
    """get_audit_summary() 提供统计"""

    def test_summary_counts(self, tmp_path):
        """统计 kept/dropped/fail_open 数量正确"""
        reviewer = AIReviewer(make_config(tmp_path, retries=1))
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.95, "enhanced_fix": "fix"},
            {"rule_id": "naming-convention", "is_valid": False,
             "confidence": 0.2, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        summary = reviewer.get_audit_summary()
        assert summary["total_input"] == 2
        assert summary["kept"] == 1
        assert summary["dropped"] == 1
        assert summary["dropped_by_rule"] == {"naming-convention": 1}

    def test_summary_dropped_error_severity_flagged(self, tmp_path):
        """误杀 ERROR 级问题必须在统计中高亮（dropped_errors）"""
        reviewer = AIReviewer(make_config(tmp_path, retries=1))
        issues = make_issues()
        # LLM 错误地把 ERROR 级安全问题判为无效
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": False,
             "confidence": 0.55, "enhanced_fix": ""},
            {"rule_id": "naming-convention", "is_valid": True,
             "confidence": 0.9, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                reviewer.review(issues, make_diff(), {})

        summary = reviewer.get_audit_summary()
        assert summary["dropped_errors"] == 1  # ERROR 级被误杀必须可见


# ===================================================================
# 回归保护：原有行为不变
# ===================================================================

class TestBackwardCompatibility:
    """加审计后，原有过滤行为不能变"""

    def test_filtering_behavior_unchanged(self, tmp_path):
        """审计不影响过滤结果本身"""
        reviewer = AIReviewer(make_config(tmp_path, retries=1))
        issues = make_issues()
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder", "is_valid": True,
             "confidence": 0.95, "enhanced_fix": "use setFeature"},
            {"rule_id": "naming-convention", "is_valid": False,
             "confidence": 0.3, "enhanced_fix": ""},
        ])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("urllib.request.urlopen", return_value=llm_response_mock(response)):
                result = reviewer.review(issues, make_diff(), {})

        assert len(result) == 1
        assert result[0]["rule_id"] == "xxe-java-document-builder"
        assert "setFeature" in result[0]["fix"]
