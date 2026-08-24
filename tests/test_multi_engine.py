#!/usr/bin/env python3
"""
多引擎融合测试（三引擎并行 + 优先级合并）

验证 docs/architecture.md 声明的引擎策略：
- AST 引擎始终执行
- Semgrep 可用时执行；不可用时回退内置正则
- 合并去重优先级：AST > Semgrep > Regex
- 同一 (rule_id, file, line) 多引擎检出时 confidence = 1.0
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from rule_engine import RuleEngine


def make_engine():
    """跳过 __init__（避免加载规约），只测引擎编排与合并逻辑"""
    return RuleEngine.__new__(RuleEngine)


def issue(rule_id, file, line, message, engine_hint):
    return {
        "rule_id": rule_id,
        "file": file,
        "line": line,
        "severity": "ERROR",
        "message": message,
        "engine": engine_hint,
    }


class TestMergePriority:
    """优先级合并：AST > Semgrep > Regex"""

    def test_ast_overrides_semgrep_same_location(self):
        """同一位置被 AST 与 Semgrep 检出：AST 内容胜出，双引擎互证"""
        eng = make_engine()
        semgrep_i = issue("xxe-doc", "a.java", 10, "semgrep 消息", "semgrep")
        ast_i = issue("xxe-doc", "a.java", 10, "ast 消息", "builtin-v2")
        merged = eng._merge_multi_engine(
            [("semgrep", [semgrep_i]), ("ast", [ast_i])]
        )
        assert len(merged) == 1
        assert merged[0]["engine"] == "ast"
        assert merged[0]["message"] == "ast 消息"
        assert set(merged[0]["engines"]) == {"ast", "semgrep"}
        # 贝叶斯后验: LR = 18*8 = 144, P = 144/145 ≈ 0.9931
        assert merged[0]["confidence"] == pytest.approx(144 / 145, abs=1e-6)

    def test_semgrep_overrides_regex_same_location(self):
        """同一位置被 Semgrep 与正则检出：Semgrep 内容胜出"""
        eng = make_engine()
        regex_i = issue("sqli", "b.py", 3, "正则消息", "builtin")
        semgrep_i = issue("sqli", "b.py", 3, "semgrep 消息", "semgrep")
        merged = eng._merge_multi_engine(
            [("semgrep", [semgrep_i]), ("regex", [regex_i])]
        )
        assert len(merged) == 1
        assert merged[0]["engine"] == "semgrep"
        assert merged[0]["message"] == "semgrep 消息"
        # LR = 8*3 = 24, P = 24/25 = 0.96
        assert merged[0]["confidence"] == pytest.approx(24 / 25, abs=1e-6)

    def test_three_engines_same_location(self):
        """三引擎同位置：AST 胜出，engines 记录全部三个"""
        eng = make_engine()
        merged = eng._merge_multi_engine(
            [
                ("regex", [issue("r", "c.js", 1, "正则", "builtin")]),
                ("semgrep", [issue("r", "c.js", 1, "semgrep", "semgrep")]),
                ("ast", [issue("r", "c.js", 1, "ast", "builtin-v2")]),
            ]
        )
        assert len(merged) == 1
        assert merged[0]["engine"] == "ast"
        assert set(merged[0]["engines"]) == {"ast", "semgrep", "regex"}
        # LR = 18*8*3 = 432, P = 432/433
        assert merged[0]["confidence"] == pytest.approx(432 / 433, abs=1e-6)

    def test_different_rule_ids_not_deduped(self):
        """同文件同行但规则 ID 不同：不合并"""
        eng = make_engine()
        merged = eng._merge_multi_engine(
            [
                ("semgrep", [issue("xss", "d.java", 7, "xss", "semgrep")]),
                ("ast", [issue("xxe", "d.java", 7, "xxe", "builtin-v2")]),
            ]
        )
        assert len(merged) == 2

    def test_single_engine_calibrated_confidence(self):
        """单引擎独有检出：校准后验而非常数（semgrep 单独 = 8/9）"""
        eng = make_engine()
        merged = eng._merge_multi_engine(
            [("semgrep", [issue("ssrf", "e.py", 2, "ssrf", "semgrep")])]
        )
        assert len(merged) == 1
        assert merged[0]["confidence"] == pytest.approx(8 / 9, abs=1e-6)
        assert merged[0]["confidence"] < 1.0


class TestRunEngineOrchestration:
    """run() 引擎编排策略"""

    def _patched_engine(self, monkeypatch, *, semgrep_available, results):
        eng = make_engine()
        eng.rules = [{"id": "demo-rule", "patterns": [], "languages": []}]
        monkeypatch.setattr(eng, "_semgrep_available", lambda: semgrep_available)
        monkeypatch.setattr(eng, "_run_with_ast", lambda rp, cf: results["ast"])
        monkeypatch.setattr(
            eng, "_run_with_semgrep", lambda rp, cf: results["semgrep"]
        )
        monkeypatch.setattr(eng, "_run_with_builtin", lambda rp, cf: results["regex"])
        return eng

    def test_ast_always_runs_with_semgrep(self, monkeypatch):
        """Semgrep 可用：AST + Semgrep 并行，正则不执行"""
        eng = self._patched_engine(
            monkeypatch,
            semgrep_available=True,
            results={
                "ast": [issue("r", "a.java", 1, "ast", "builtin-v2")],
                "semgrep": [issue("r", "a.java", 1, "semgrep", "semgrep")],
                "regex": [issue("r", "a.java", 1, "regex-不应出现", "builtin")],
            },
        )
        merged = eng.run("/tmp/repo", [{"path": "a.java"}])
        assert len(merged) == 1
        assert merged[0]["engine"] == "ast"
        # 正则引擎未参与，engines 只含 ast/semgrep
        assert set(merged[0]["engines"]) == {"ast", "semgrep"}

    def test_ast_runs_with_regex_fallback(self, monkeypatch):
        """Semgrep 不可用：AST + 内置正则回退"""
        eng = self._patched_engine(
            monkeypatch,
            semgrep_available=False,
            results={
                "ast": [],
                "semgrep": [],
                "regex": [issue("r", "b.py", 5, "正则检出", "builtin")],
            },
        )
        merged = eng.run("/tmp/repo", [{"path": "b.py"}])
        assert len(merged) == 1
        assert merged[0]["engine"] == "regex"
        assert merged[0]["engines"] == ["regex"]

    def test_no_rules_returns_empty(self, monkeypatch):
        eng = make_engine()
        eng.rules = []
        assert eng.run("/tmp/repo", []) == []


class TestASTEngineIntegration:
    """AST 引擎真实集成（builtin_engine_v2 可导入）"""

    def test_run_with_ast_normalizes_relative_path(self, tmp_path):
        eng = make_engine()
        java_file = tmp_path / "Demo.java"
        java_file.write_text(
            "public class Demo { void f() { int x = 1; } }", encoding="utf-8"
        )
        issues = eng._run_with_ast(str(tmp_path), [{"path": "Demo.java"}])
        # 无论是否检出问题，文件路径必须是相对路径（与其他引擎对齐）
        for it in issues:
            assert it["file"] == "Demo.java"

    def test_run_with_ast_missing_file_skipped(self, tmp_path):
        eng = make_engine()
        issues = eng._run_with_ast(str(tmp_path), [{"path": "NotExists.java"}])
        assert issues == []
