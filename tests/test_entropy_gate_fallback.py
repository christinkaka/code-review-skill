#!/usr/bin/env python3
"""
熵门控 snippet 脱敏回退测试

背景（2026-08-24 端到端验证发现）：
TRAE 管理的 semgrep 对匹配代码内容脱敏，extra.lines 恒返回
"requires login"（检出本身正常：rule_id/file/line 准确）。
导致熵门控从 code_snippet 提取不到字符串字面量，semgrep 引擎的
硬编码检出全部跳过熵门控（门控失效）。

修复：snippet 无双引号字面量时，回读源文件对应行提取字面量。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from rule_engine import RuleEngine


@pytest.fixture
def engine():
    """最小化构造（熵门控不依赖规则加载）"""
    return RuleEngine.__new__(RuleEngine)


@pytest.fixture
def redacted_repo(tmp_path):
    """模拟 semgrep snippet 被脱敏的场景：真实文件含低熵/高熵字面量"""
    (tmp_path / "Db.java").write_text(
        'public class Db {\n'
        '    void connect() {\n'
        '        String dbPassword = "guest";\n'
        '    }\n'
        '}\n',
        encoding="utf-8",
    )
    (tmp_path / "Api.java").write_text(
        'public class Api {\n'
        '    void call() {\n'
        '        String apiKey = "sk-9f2kQz7mXv4bN8pL3wR6";\n'
        '    }\n'
    '}\n',
        encoding="utf-8",
    )
    return tmp_path


def make_issue(file, line, snippet):
    return {
        "rule_id": "crypto-hardcoded-key-java",
        "severity": "ERROR",
        "file": file,
        "line": line,
        "end_line": line,
        "message": "hardcoded",
        "code_snippet": snippet,
    }


class TestRedactedSnippetFallback:
    """snippet 被脱敏（"requires login"）时回读源文件行"""

    def test_redacted_snippet_reads_source_file(self, engine, redacted_repo):
        """snippet=requires login 时回读源文件：低熵 'guest' 应被拒绝"""
        issue = make_issue("Db.java", 3, "requires login")
        result = engine._apply_entropy_gate([issue], str(redacted_repo))

        assert len(result) == 0, "低熵字面量 guest 应被熵门控拒绝"
        assert "entropy_gate_rejected" in issue, "拒绝原因应写入 issue"

    def test_redacted_snippet_high_entropy_kept(self, engine, redacted_repo):
        """snippet 脱敏但源文件含高熵凭据：应保留并附熵详情"""
        issue = make_issue("Api.java", 3, "requires login")
        result = engine._apply_entropy_gate([issue], str(redacted_repo))

        assert len(result) == 1, "高熵凭据应保留"
        assert "entropy" in issue, "熵详情应写入 issue"
        assert issue["entropy"]["total_bits"] > 32

    def test_normal_snippet_still_works(self, engine, redacted_repo):
        """snippet 正常（含字面量）时不读文件，行为不变"""
        issue = make_issue("Db.java", 99, 'String x = "guest";')
        result = engine._apply_entropy_gate([issue], str(redacted_repo))

        # snippet 自身的 'guest'（低熵）被拒，且未因 line=99 越界崩溃
        assert len(result) == 0

    def test_no_repo_path_no_crash(self, engine, redacted_repo):
        """不传 repo_path（旧调用方式）时保持旧行为：保守保留"""
        issue = make_issue("Db.java", 3, "requires login")
        result = engine._apply_entropy_gate([issue])

        assert len(result) == 1, "无 repo_path 时保守保留（向后兼容）"

    def test_file_missing_no_crash(self, engine, tmp_path):
        """源文件不存在时不崩溃，保守保留"""
        issue = make_issue("NonExist.java", 3, "requires login")
        result = engine._apply_entropy_gate([issue], str(tmp_path))

        assert len(result) == 1, "文件缺失时保守保留"

    def test_redacted_multi_literal_uses_best(self, engine, redacted_repo):
        """源文件行含多个字面量时取最后一个（赋值右侧）"""
        # 构造一行双字面量
        (redacted_repo / "Two.java").write_text(
            'String prefix = "user-"; String pw = "short";\n',
            encoding="utf-8",
        )
        issue = make_issue("Two.java", 1, "requires login")
        result = engine._apply_entropy_gate([issue], str(redacted_repo))

        # "short" 低熵 -> 拒绝（证明取到了赋值右侧字面量而非 prefix）
        assert len(result) == 0
