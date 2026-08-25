"""semgrep 扫描范围收窄测试（2026-08-25 修复回归防护）

修复背景：_run_with_semgrep 此前无视 changed_files 以 target="." 扫全仓库，
实测 50 文件输入时 1096/1097 条检出来自范围外文件（diff 场景误报未变更代码）。
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from rule_engine import RuleEngine

_NONEMPTY_RULES = {"rules": [{"id": "r", "languages": ["generic"], "pattern-regex": "x"}]}


def _make_engine():
    return RuleEngine.__new__(RuleEngine)


class TestSemgrepScopeNarrowing:
    def test_include_args_injected_for_small_fileset(self, tmp_path):
        """changed_files 数量在阈值内：每个文件注入 --include 对"""
        engine = _make_engine()
        engine.rules = []
        repo = tmp_path / "repo"
        repo.mkdir()

        with patch.object(RuleEngine, "_rules_to_semgrep", return_value=_NONEMPTY_RULES):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='{"results": []}', stderr="")
                engine._run_with_semgrep(str(repo), [
                    {"path": "a/Foo.java"}, {"path": "b/Bar.java"},
                ])

        cmd = mock_run.call_args[0][0]
        includes = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--include"]
        assert sorted(includes) == ["a/Foo.java", "b/Bar.java"]
        assert cmd[0] == "semgrep"

    def test_no_include_for_empty_fileset(self, tmp_path):
        """changed_files 为空：保持全库扫描（不注入 include）"""
        engine = _make_engine()
        engine.rules = []
        repo = tmp_path / "repo"
        repo.mkdir()

        with patch.object(RuleEngine, "_rules_to_semgrep", return_value=_NONEMPTY_RULES):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='{"results": []}', stderr="")
                engine._run_with_semgrep(str(repo), [])

        cmd = mock_run.call_args[0][0]
        assert "--include" not in cmd

    def test_overflow_falls_back_to_result_filter(self, tmp_path):
        """changed_files 超阈值：不传 --include，结果按路径过滤"""
        engine = _make_engine()
        engine.rules = []
        repo = tmp_path / "repo"
        repo.mkdir()
        scope = {f"src/main/F{i}.java" for i in range(RuleEngine._INCLUDE_ARG_MAX + 1)}
        changed = [{"path": p} for p in scope]
        out_of_scope = "other/Out.java"

        stdout = '{"results": [%s]}' % ",".join(
            '{"check_id": "r", "path": "%s", "start": {"line": 1}, "extra": {"severity": "ERROR"}}' % p
            for p in list(scope)[:3] + [out_of_scope]
        )
        with patch.object(RuleEngine, "_rules_to_semgrep", return_value=_NONEMPTY_RULES):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
                engine.rules = [{"id": "r"}]
                issues = engine._run_with_semgrep(str(repo), changed)

        cmd = mock_run.call_args[0][0]
        assert "--include" not in cmd, "超阈值不应传 --include"
        assert all(i["file"] in scope for i in issues), "范围外文件检出必须被过滤"
        assert len(issues) == 3
