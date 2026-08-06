#!/usr/bin/env python3
"""
report_generator.py 单元测试
覆盖报告生成的各种场景
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from report_generator import ReportGenerator


@pytest.fixture
def sample_scan_info():
    """标准扫描信息"""
    return {
        "repo": "/test/repo",
        "profile": "default",
        "timestamp": "2026-08-05T10:00:00",
        "duration_seconds": 5.5,
        "mode": "diff",
        "base_branch": "master",
        "target_branch": "feature",
    }


@pytest.fixture
def sample_issues():
    """标准问题列表"""
    return [
        {
            "rule_id": "sqli-java-concat",
            "category": "security",
            "severity": "ERROR",
            "file": "src/UserDAO.java",
            "line": 42,
            "message": "SQL 注入 - 字符串拼接",
            "fix": "使用 PreparedStatement",
            "call_chain": ["handleRequest", "queryUser"],
        },
        {
            "rule_id": "xss-js-innerhtml",
            "category": "security",
            "severity": "WARNING",
            "file": "web/app.js",
            "line": 88,
            "message": "XSS - innerHTML 赋值",
            "fix": "使用 textContent",
            "call_chain": [],
        },
    ]


@pytest.fixture
def sample_diff_summary():
    """标准差异摘要"""
    return {
        "changed_files": [
            {"path": "src/UserDAO.java", "status": "modified"},
            {"path": "web/app.js", "status": "modified"},
        ],
        "changed_methods": [
            {"file": "src/UserDAO.java", "name": "queryUser", "line": 40},
        ],
    }


@pytest.fixture
def sample_call_graph_summary():
    """标准调用图摘要"""
    return {
        "node_count": 15,
        "edge_count": 20,
        "affected_methods": ["handleRequest", "queryUser", "renderPage"],
    }


class TestReportGenerator:
    """测试 ReportGenerator"""

    def test_init(self):
        """ReportGenerator 初始化接受输出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            assert generator.output_dir is not None

    def test_generate_returns_report(self, sample_scan_info, sample_issues,
                                      sample_diff_summary, sample_call_graph_summary):
        """generate() 返回包含 summary 的字典"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = generator.generate(
                scan_info=sample_scan_info,
                issues=sample_issues,
                diff_summary=sample_diff_summary,
                call_graph_summary=sample_call_graph_summary,
            )

            assert isinstance(report, dict)
            assert "summary" in report

    def test_generate_summary_counts(self, sample_scan_info, sample_issues,
                                      sample_diff_summary, sample_call_graph_summary):
        """generate() 的 summary 包含正确的问题计数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = generator.generate(
                scan_info=sample_scan_info,
                issues=sample_issues,
                diff_summary=sample_diff_summary,
                call_graph_summary=sample_call_graph_summary,
            )

            summary = report["summary"]
            assert summary["total"] == 2

    def test_generate_empty_issues(self, sample_scan_info,
                                    sample_diff_summary, sample_call_graph_summary):
        """generate() 空问题列表时生成空报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = generator.generate(
                scan_info=sample_scan_info,
                issues=[],
                diff_summary=sample_diff_summary,
                call_graph_summary=sample_call_graph_summary,
            )

            assert report["summary"]["total"] == 0

    def test_generate_writes_json_file(self, sample_scan_info, sample_issues,
                                        sample_diff_summary, sample_call_graph_summary):
        """generate() 输出 JSON 报告文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            generator.generate(
                scan_info=sample_scan_info,
                issues=sample_issues,
                diff_summary=sample_diff_summary,
                call_graph_summary=sample_call_graph_summary,
            )

            json_files = list(Path(tmpdir).glob("*.json"))
            assert len(json_files) >= 1

    def test_generate_includes_scan_metadata(self, sample_scan_info, sample_issues,
                                              sample_diff_summary, sample_call_graph_summary):
        """generate() 报告包含扫描元信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = generator.generate(
                scan_info=sample_scan_info,
                issues=sample_issues,
                diff_summary=sample_diff_summary,
                call_graph_summary=sample_call_graph_summary,
            )

            # 报告应包含扫描信息（可能在顶层或嵌套）
            report_str = json.dumps(report, ensure_ascii=False)
            assert "/test/repo" in report_str or "repo" in report
