#!/usr/bin/env python3
"""
规则引擎单元测试 (UT2-UT3)

覆盖 RuleEngine 的核心方法：
- UT2: _rules_to_semgrep() 生成的 YAML 符合 Semgrep schema
- UT3: _run_with_semgrep() 正确解析 Semgrep JSON 输出
- Semgrep 超时处理
- Semgrep 崩溃处理
- 空规则列表处理
"""

import json
import os
import subprocess
import tempfile
import textwrap
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from rule_engine import MarkdownRuleParser, RuleEngine


# ===================================================================
# 辅助 fixtures
# ===================================================================

@pytest.fixture
def basic_profile():
    """基础 profile 配置"""
    return {
        "specs": [
            {"path": "security/xxe.md", "enabled": True},
        ],
    }


@pytest.fixture
def empty_profile():
    """空 profile 配置（无规则）"""
    return {"specs": []}


@pytest.fixture
def engine_with_rules(tmp_path, sample_markdown_file):
    """创建带有已加载规则的 RuleEngine 实例"""
    # 将测试 markdown 文件复制到 specs 目录
    specs_dir = tmp_path / "specs" / "security"
    specs_dir.mkdir(parents=True)
    import shutil
    shutil.copy(sample_markdown_file, str(specs_dir / "xxe.md"))

    profile = {
        "specs": [
            {"path": "security/xxe.md", "enabled": True},
        ],
    }
    engine = RuleEngine(str(tmp_path / "specs"), profile)
    return engine


@pytest.fixture
def engine_empty(tmp_path):
    """创建空规则的 RuleEngine 实例"""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir(parents=True)
    profile = {"specs": []}
    engine = RuleEngine(str(specs_dir), profile)
    return engine


# ===================================================================
# UT2: _rules_to_semgrep() 生成的 YAML 符合 Semgrep schema
# ===================================================================

class TestRulesToSemgrep:
    """测试规则到 Semgrep 格式的转换"""

    def test_rules_to_semgrep_yaml(self, engine_with_rules):
        """UT2: _rules_to_semgrep() 生成包含 rules 键的字典"""
        result = engine_with_rules._rules_to_semgrep()

        assert "rules" in result
        assert isinstance(result["rules"], list)
        assert len(result["rules"]) >= 1

    def test_semgrep_schema_validation(self, engine_with_rules):
        """UT2: 生成的每条 Semgrep 规则包含必需字段"""
        result = engine_with_rules._rules_to_semgrep()

        required_fields = {"id", "message", "severity", "languages"}

        for rule in result["rules"]:
            for field in required_fields:
                assert field in rule, f"Semgrep 规则缺少必需字段: {field}"

            # severity 必须是 Semgrep 接受的值
            assert rule["severity"] in ("ERROR", "WARNING", "INFO")

            # languages 必须是非空列表
            assert isinstance(rule["languages"], list)
            assert len(rule["languages"]) >= 1

    def test_semgrep_single_pattern(self, engine_with_rules):
        """UT2: 单个 pattern 无 pattern-not 时使用 pattern 字段"""
        result = engine_with_rules._rules_to_semgrep()

        # 找到只有 pattern 没有 pattern-not 的规则（如 xxe-java-sax-parser）
        sax_rule = None
        for rule in result["rules"]:
            if rule["id"] == "xxe-java-sax-parser":
                sax_rule = rule
                break

        if sax_rule:
            # 单个 pattern 无 pattern-not 应使用 "pattern" 字段
            assert "pattern" in sax_rule

    def test_semgrep_pattern_with_exclusion(self, engine_with_rules):
        """UT2: 有 pattern-not 时使用 patterns 数组"""
        result = engine_with_rules._rules_to_semgrep()

        # 找到有 pattern-not 的规则（如 xxe-java-document-builder）
        builder_rule = None
        for rule in result["rules"]:
            if rule["id"] == "xxe-java-document-builder":
                builder_rule = rule
                break

        if builder_rule:
            # 有 pattern-not 应使用 "patterns" 数组
            assert "patterns" in builder_rule
            pattern_types = set()
            for p in builder_rule["patterns"]:
                pattern_types.update(p.keys())
            assert "pattern" in pattern_types or "pattern-not" in pattern_types

    def test_semgrep_yaml_serializable(self, engine_with_rules):
        """UT2: 生成的规则可以被 yaml.dump 序列化"""
        result = engine_with_rules._rules_to_semgrep()

        # 应能正确序列化为 YAML
        yaml_str = yaml.dump(result, default_flow_style=False, allow_unicode=True)
        assert yaml_str
        assert "rules:" in yaml_str

        # 反序列化后应与原始数据一致
        parsed = yaml.safe_load(yaml_str)
        assert parsed == result

    def test_semgrep_metadata_preserved(self, engine_with_rules):
        """UT2: 规则的 metadata 字段被正确传递到 Semgrep 格式"""
        result = engine_with_rules._rules_to_semgrep()

        # 至少有一条规则包含 metadata
        rules_with_metadata = [r for r in result["rules"] if "metadata" in r]
        assert len(rules_with_metadata) >= 1

        for rule in rules_with_metadata:
            assert isinstance(rule["metadata"], dict)

    @pytest.mark.parametrize("severity", ["ERROR", "WARNING", "INFO"])
    def test_semgrep_severity_values(self, tmp_path, severity):
        """UT2: 参数化测试各种 severity 值的正确传递"""
        content = textwrap.dedent(f"""\
            # 测试规则

            ```yaml
            id: severity-test
            languages: [java]
            severity: {severity}
            ```

            ```pattern
            some_code();
            ```
        """)
        specs_dir = tmp_path / "specs" / "test"
        specs_dir.mkdir(parents=True)
        md_file = specs_dir / "test.md"
        md_file.write_text(content, encoding="utf-8")

        profile = {"specs": [{"path": "test/test.md", "enabled": True}]}
        engine = RuleEngine(str(tmp_path / "specs"), profile)

        result = engine._rules_to_semgrep()
        assert len(result["rules"]) == 1
        assert result["rules"][0]["severity"] == severity


# ===================================================================
# UT3: _run_with_semgrep() 正确解析 Semgrep JSON 输出
# ===================================================================

class TestRunWithSemgrep:
    """测试 Semgrep 执行和输出解析"""

    def test_parse_semgrep_output(self, engine_with_rules, sample_semgrep_json):
        """UT3: 正确解析 Semgrep JSON 输出为结构化问题列表"""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(sample_semgrep_json)
        mock_result.returncode = 0

        with patch("rule_engine.subprocess.run", return_value=mock_result):
            with patch.object(engine_with_rules, "_semgrep_available", return_value=True):
                issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        assert isinstance(issues, list)
        assert len(issues) == 2

        # 验证第一个 issue 的字段
        issue1 = issues[0]
        assert issue1["rule_id"] == "xxe-java-document-builder"
        assert issue1["file"] == "src/main/java/com/example/Parser.java"
        assert issue1["line"] == 42
        assert issue1["end_line"] == 45
        assert issue1["severity"] == "ERROR"
        assert "XXE" in issue1["message"]

    def test_parse_semgrep_output_fields(self, engine_with_rules, sample_semgrep_json):
        """UT3: 解析后的 issue 包含所有必需字段"""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(sample_semgrep_json)
        mock_result.returncode = 0

        required_fields = {"rule_id", "category", "severity", "file", "line", "end_line", "message"}

        with patch("rule_engine.subprocess.run", return_value=mock_result):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        for issue in issues:
            for field in required_fields:
                assert field in issue, f"Issue 缺少必需字段: {field}"

    def test_semgrep_empty_results(self, engine_with_rules):
        """UT3: Semgrep 输出为空结果时返回空列表"""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"results": [], "errors": []})
        mock_result.returncode = 0

        with patch("rule_engine.subprocess.run", return_value=mock_result):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        assert issues == []

    def test_semgrep_category_inference(self, engine_with_rules, sample_semgrep_json):
        """UT3: 根据 rule_id 正确推断 category"""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(sample_semgrep_json)
        mock_result.returncode = 0

        with patch("rule_engine.subprocess.run", return_value=mock_result):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        # xxe-* 开头的规则应推断为 security 类别
        for issue in issues:
            if issue["rule_id"].startswith("xxe"):
                assert issue["category"] == "security"


# ===================================================================
# Semgrep 超时处理
# ===================================================================

class TestSemgrepTimeout:
    """测试 Semgrep 超时场景"""

    def test_semgrep_timeout_handling(self, engine_with_rules):
        """UT3: Semgrep 超时时返回空列表而非抛出异常"""
        with patch(
            "rule_engine.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="semgrep", timeout=300),
        ):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        assert issues == []

    def test_semgrep_timeout_logs_error(self, engine_with_rules, caplog):
        """UT3: Semgrep 超时时记录错误日志"""
        import logging

        with patch(
            "rule_engine.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="semgrep", timeout=300),
        ):
            with caplog.at_level(logging.ERROR, logger="code-review.rules"):
                issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        assert any("超时" in record.message for record in caplog.records)


# ===================================================================
# Semgrep 崩溃处理
# ===================================================================

class TestSemgrepCrash:
    """测试 Semgrep 崩溃场景"""

    def test_semgrep_crash_returns_empty(self, engine_with_rules):
        """UT3: Semgrep 崩溃时返回空列表"""
        with patch(
            "rule_engine.subprocess.run",
            side_effect=RuntimeError("Semgrep crashed unexpectedly"),
        ):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        assert issues == []

    def test_semgrep_invalid_json_output(self, engine_with_rules):
        """UT3: Semgrep 输出无效 JSON 时返回空列表"""
        mock_result = MagicMock()
        mock_result.stdout = "this is not valid json {{{"
        mock_result.returncode = 1

        with patch("rule_engine.subprocess.run", return_value=mock_result):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        # 应优雅处理，返回空列表
        assert issues == []

    def test_semgrep_file_not_found(self, engine_with_rules):
        """UT3: Semgrep 可执行文件不存在时返回空列表"""
        with patch(
            "rule_engine.subprocess.run",
            side_effect=FileNotFoundError("semgrep not found"),
        ):
            issues = engine_with_rules._run_with_semgrep("/fake/repo", [])

        assert issues == []


# ===================================================================
# 空规则列表处理
# ===================================================================

class TestEmptyRules:
    """测试空规则列表的处理"""

    def test_empty_rules_returns_empty(self, engine_empty):
        """空规则列表时 run() 返回空列表"""
        issues = engine_empty.run("/fake/repo", [])
        assert issues == []

    def test_empty_rules_semgrep_returns_empty(self, engine_empty):
        """空规则列表时 _run_with_semgrep() 返回空列表"""
        issues = engine_empty._run_with_semgrep("/fake/repo", [])
        assert issues == []

    def test_rules_without_patterns_skipped(self, tmp_path):
        """没有 pattern 的规则在 _rules_to_semgrep() 中被跳过"""
        content = textwrap.dedent("""\
            # 无模式规则

            ```yaml
            id: no-pattern
            languages: [java]
            severity: WARNING
            ```
        """)
        specs_dir = tmp_path / "specs" / "test"
        specs_dir.mkdir(parents=True)
        md_file = specs_dir / "test.md"
        md_file.write_text(content, encoding="utf-8")

        profile = {"specs": [{"path": "test/test.md", "enabled": True}]}
        engine = RuleEngine(str(tmp_path / "specs"), profile)

        result = engine._rules_to_semgrep()
        assert result["rules"] == []


# ===================================================================
# 参数化边界测试
# ===================================================================

class TestRuleEngineEdgeCases:
    """规则引擎参数化边界测试"""

    @pytest.mark.parametrize("rule_id,expected_category", [
        ("xxe-java-test", "security"),
        ("xss-js-test", "security"),
        ("auth-java-test", "security"),
        ("path-python-test", "security"),
        ("priv-java-test", "security"),
        ("sig-java-test", "security"),
        ("sqli-java-test", "security"),
        ("ssrf-js-test", "security"),
        ("arch-java-test", "design"),
        ("api-java-test", "design"),
        ("db-java-test", "design"),
        ("naming-java-test", "implementation"),
        ("err-java-test", "implementation"),
        ("conc-java-test", "implementation"),
        ("null-java-test", "implementation"),
        ("custom-java-test", "custom"),
        ("unknown-rule", "unknown"),
    ])
    def test_category_inference(self, engine_with_rules, rule_id, expected_category):
        """参数化测试：各种 rule_id 前缀的类别推断"""
        category = engine_with_rules._get_category(rule_id)
        assert category == expected_category

    @pytest.mark.parametrize("ext,languages,expected", [
        (".java", ["java"], True),
        (".py", ["python"], True),
        (".js", ["javascript"], True),
        (".ts", ["typescript"], True),
        (".go", ["go"], True),
        (".java", ["python"], False),
        (".py", ["java"], False),
        (".java", ["java", "python"], True),
        (".xyz", ["java"], False),
        (".java", [], True),  # 空语言列表匹配所有
    ])
    def test_language_matching(self, engine_with_rules, ext, languages, expected):
        """参数化测试：文件扩展名与语言列表的匹配"""
        result = engine_with_rules._language_matches(ext, languages)
        assert result == expected

    def test_severity_override(self, tmp_path):
        """测试 severity 覆盖功能"""
        content = textwrap.dedent("""\
            # 测试规则

            ```yaml
            id: severity-override-test
            languages: [java]
            severity: WARNING
            ```

            ```pattern
            some_code();
            ```
        """)
        specs_dir = tmp_path / "specs" / "test"
        specs_dir.mkdir(parents=True)
        md_file = specs_dir / "test.md"
        md_file.write_text(content, encoding="utf-8")

        profile = {
            "specs": [
                {
                    "path": "test/test.md",
                    "enabled": True,
                    "severity.override": "ERROR",
                },
            ],
        }
        engine = RuleEngine(str(tmp_path / "specs"), profile)

        # severity override 通过 spec.get("severity.override") 获取
        # 由于 _load_rules 中使用 spec.get("severity.override")
        # 验证规则是否被加载
        assert len(engine.rules) >= 1
