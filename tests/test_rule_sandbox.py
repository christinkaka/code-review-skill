#!/usr/bin/env python3
"""
外部规则沙箱验证测试 (P2)

核心诉求：
1. 结构校验：无 pattern 的规则（raptor-insecure-api-scanf__c 实例）必须在
   加载时被隔离，不能进引擎
2. 沙箱冒烟：规则用真实 semgrep 在样本语料上试跑，语法错误/异常必须检出
3. rule_loader 集成：无效规则不落盘，隔离记录可追溯
4. 引擎侧防御：即使 external/ 目录存在坏规则文件，引擎也不加载；
   空 profile 不隐式拉入外部规则
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rule_sandbox import RuleSandbox
import rule_loader


# ===================================================================
# 结构校验
# ===================================================================

class TestStructuralValidation:
    """规则结构校验（Semgrep 兼容性最小集）"""

    def test_valid_pattern_rule_passes(self):
        rule = {"id": "ok-1", "languages": ["java"], "severity": "ERROR",
                "message": "m", "pattern": "$X.toString()"}
        valid, reason = RuleSandbox.validate_structure(rule)
        assert valid is True
        assert reason == ""

    def test_valid_patterns_list_passes(self):
        rule = {"id": "ok-2", "languages": ["python"],
                "patterns": [{"pattern": "eval($X)"}]}
        valid, _ = RuleSandbox.validate_structure(rule)
        assert valid is True

    def test_valid_pattern_regex_passes(self):
        rule = {"id": "ok-3", "languages": ["js"],
                "pattern-regex": "eval\\(.*\\)"}
        valid, _ = RuleSandbox.validate_structure(rule)
        assert valid is True

    def test_missing_all_patterns_fails(self):
        """raptor 实例：有 id 有 languages 但没有任何 pattern -> 隔离"""
        rule = {"id": "raptor-insecure-api-scanf__c",
                "languages": ["c"], "severity": "ERROR",
                "message": "buffer overflow"}
        valid, reason = RuleSandbox.validate_structure(rule)
        assert valid is False
        assert "pattern" in reason

    def test_missing_id_fails(self):
        rule = {"languages": ["java"], "pattern": "$X"}
        valid, reason = RuleSandbox.validate_structure(rule)
        assert valid is False
        assert "id" in reason

    def test_missing_languages_fails(self):
        rule = {"id": "no-lang", "pattern": "$X"}
        valid, reason = RuleSandbox.validate_structure(rule)
        assert valid is False
        assert "languages" in reason

    def test_invalid_severity_flagged(self):
        """严重等级不在标准集合 -> 隔离（避免破坏报告分级）

        注：CRITICAL/HIGH 与 scan.py 分层评审口径一致，属合法值；
        非法值用 BOGUS 表示。
        """
        rule = {"id": "bad-sev", "languages": ["java"],
                "pattern": "$X", "severity": "BOGUS"}
        valid, reason = RuleSandbox.validate_structure(rule)
        assert valid is False
        assert "severity" in reason

    def test_empty_patterns_list_fails(self):
        """patterns 为空列表 -> 等同无 pattern"""
        rule = {"id": "empty-pats", "languages": ["java"], "patterns": []}
        valid, _ = RuleSandbox.validate_structure(rule)
        assert valid is False


# ===================================================================
# 沙箱冒烟测试（mock semgrep）
# ===================================================================

class TestSandboxSmoke:
    """规则在样本语料上的冒烟测试"""

    def _make_rule_file(self, tmp_path, rule):
        f = tmp_path / f"{rule['id']}.yaml"
        f.write_text(yaml.dump({"rules": [rule]}), encoding="utf-8")
        return f

    def test_valid_rule_smoke_passes(self, tmp_path):
        """规则语法正确、能执行 -> smoke=ok"""
        rule = {"id": "smoke-ok", "languages": ["java"], "pattern": "eval($X)"}
        rule_file = self._make_rule_file(tmp_path, rule)
        (tmp_path / "Sample.java").write_text("class A {}", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"results": [], "errors": []})
        mock_result.stderr = ""

        sandbox = RuleSandbox()
        with patch("subprocess.run", return_value=mock_result):
            result = sandbox.smoke_test(rule_file, str(tmp_path))

        assert result["status"] == "ok"
        assert result["findings"] == 0

    def test_semgrep_syntax_error_detected(self, tmp_path):
        """pattern 语法错误（semgrep 报错）-> status=error"""
        rule = {"id": "syntax-bad", "languages": ["java"], "pattern": "((("}
        rule_file = self._make_rule_file(tmp_path, rule)
        (tmp_path / "Sample.java").write_text("class A {}", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = "{}"
        mock_result.stderr = "Invalid pattern syntax"

        sandbox = RuleSandbox()
        with patch("subprocess.run", return_value=mock_result):
            result = sandbox.smoke_test(rule_file, str(tmp_path))

        assert result["status"] == "error"
        assert "syntax" in result["detail"].lower() or result["detail"]

    def test_findings_counted(self, tmp_path):
        """语料命中数必须上报"""
        rule = {"id": "hit-rule", "languages": ["java"], "pattern": "eval($X)"}
        rule_file = self._make_rule_file(tmp_path, rule)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"results": [
            {"check_id": "hit-rule", "path": "x.java"},
            {"check_id": "hit-rule", "path": "y.java"},
        ], "errors": []})
        mock_result.stderr = ""

        sandbox = RuleSandbox()
        with patch("subprocess.run", return_value=mock_result):
            result = sandbox.smoke_test(rule_file, str(tmp_path))

        assert result["findings"] == 2


# ===================================================================
# 真实 semgrep 沙箱冒烟
# ===================================================================

class TestRealSemgrepSandbox:
    """真实 semgrep 端到端冒烟（本机已装 semgrep）"""

    def test_real_semgrep_run_on_validation_corpus(self, tmp_path):
        """用真实 semgrep 在 test-validation 语料上跑一条已知有效规则"""
        rule = {
            "id": "sandbox-real-xxe",
            "languages": ["java"],
            "severity": "ERROR",
            "message": "XXE",
            "pattern": "DocumentBuilderFactory.newInstance()",
        }
        rule_file = tmp_path / "rule.yaml"
        rule_file.write_text(yaml.dump({"rules": [rule]}), encoding="utf-8")

        corpus = "test-validation/java/xxe"
        sandbox = RuleSandbox()
        result = sandbox.smoke_test(rule_file, corpus)

        assert result["status"] == "ok"
        assert result["findings"] >= 2  # Vulnerable.java 有 2 处 XXE

    def test_real_semgrep_detects_bad_syntax(self, tmp_path):
        """真实 semgrep 检出非法 pattern"""
        rule = {"id": "bad-syntax-real", "languages": ["java"],
                "pattern": "((("}
        rule_file = tmp_path / "bad.yaml"
        rule_file.write_text(yaml.dump({"rules": [rule]}), encoding="utf-8")

        sandbox = RuleSandbox()
        result = sandbox.smoke_test(rule_file, "test-validation/java/xxe")

        assert result["status"] == "error"


# ===================================================================
# rule_loader 集成：无效规则不落盘
# ===================================================================

class TestLoaderIntegration:
    """rule_loader 加载时必须做沙箱校验"""

    def _make_loader(self, tmp_path):
        loader = rule_loader.RuleLoader(external_rules_dir=str(tmp_path / "external"))
        return loader

    def test_invalid_rule_not_written(self, tmp_path):
        """结构无效的规则不写入 external/，进隔离名单"""
        loader = self._make_loader(tmp_path)
        rules_dir = tmp_path / "src"
        rules_dir.mkdir()
        bad_rule_file = rules_dir / "bad.yaml"
        bad_rule_file.write_text(yaml.dump({"rules": [
            {"id": "no-pattern-rule", "languages": ["c"],
             "severity": "ERROR", "message": "no pattern here"}
        ]}), encoding="utf-8")

        loaded = loader._scan_and_load_rules(rules_dir, "test-src")

        assert loaded == []
        # 隔离记录可追溯
        assert len(loader.metadata["quarantined_rules"]) == 1
        assert loader.metadata["quarantined_rules"][0]["rule_id"] == "no-pattern-rule"
        # 目录里没有落盘文件
        assert not list((tmp_path / "external").glob("*.yaml"))

    def test_valid_rule_written(self, tmp_path):
        """结构有效的规则正常落盘"""
        loader = self._make_loader(tmp_path)
        rules_dir = tmp_path / "src"
        rules_dir.mkdir()
        good_rule_file = rules_dir / "good.yaml"
        good_rule_file.write_text(yaml.dump({"rules": [
            {"id": "good-rule", "languages": ["java"], "severity": "ERROR",
             "message": "m", "pattern": "eval($X)"}
        ]}), encoding="utf-8")

        loaded = loader._scan_and_load_rules(rules_dir, "test-src")

        assert len(loaded) == 1
        assert (tmp_path / "external" / "test-src_good-rule.yaml").exists()


# ===================================================================
# 引擎侧防御（修复 3 个存量失败）
# ===================================================================

class TestEngineGuard:
    """引擎不加载无效外部规则；空 profile 不拉外部规则"""

    def test_engine_skips_invalid_external_rules(self, tmp_path):
        """external/ 里的坏规则（无 pattern）不得进入 engine.rules"""
        from rule_engine import RuleEngine

        specs = tmp_path / "specs"
        ext = specs / "external"
        ext.mkdir(parents=True)
        (ext / "bad.yaml").write_text(yaml.dump({"rules": [
            {"id": "raptor-insecure-api-scanf__c", "languages": ["c"],
             "severity": "ERROR", "message": "no pattern"}
        ]}), encoding="utf-8")
        (ext / "good.yaml").write_text(yaml.dump({"rules": [
            {"id": "good-external", "languages": ["java"], "severity": "WARNING",
             "message": "m", "pattern": "eval($X)"}
        ]}), encoding="utf-8")

        profile = {"specs": [{"path": "good.yaml"}]}
        engine = RuleEngine(specs_dir=str(specs), profile=profile)

        rule_ids = [r["id"] for r in engine.rules]
        assert "raptor-insecure-api-scanf__c" not in rule_ids
        assert "good-external" in rule_ids

    def test_empty_profile_no_external_autoload(self, tmp_path):
        """profile specs 为空 -> 不隐式加载外部规则（用户明确要空）"""
        from rule_engine import RuleEngine

        specs = tmp_path / "specs"
        ext = specs / "external"
        ext.mkdir(parents=True)
        (ext / "some.yaml").write_text(yaml.dump({"rules": [
            {"id": "some-rule", "languages": ["java"], "pattern": "eval($X)"}
        ]}), encoding="utf-8")

        engine = RuleEngine(specs_dir=str(specs), profile={"specs": []})
        assert len(engine.rules) == 0

    def test_default_profile_still_loads_external(self, tmp_path):
        """正常 profile（有 specs）仍加载有效外部规则"""
        from rule_engine import RuleEngine

        specs = tmp_path / "specs"
        ext = specs / "external"
        ext.mkdir(parents=True)
        md = specs / "rule.md"
        md.write_text(
            "# 规则\n\n```yaml\nid: md-rule\nlanguages: [java]\nseverity: WARNING\n```\n\n"
            "```pattern\nsafeCall($X);\n```\n",
            encoding="utf-8",
        )
        (ext / "ext.yaml").write_text(yaml.dump({"rules": [
            {"id": "ext-rule", "languages": ["java"], "severity": "WARNING",
             "message": "m", "pattern": "eval($X)"}
        ]}), encoding="utf-8")

        profile = {"specs": [{"path": "rule.md"}]}
        engine = RuleEngine(specs_dir=str(specs), profile=profile)

        rule_ids = [r["id"] for r in engine.rules]
        assert "ext-rule" in rule_ids
        assert "md-rule" in rule_ids
