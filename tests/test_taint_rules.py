"""taint 数据流规则支持测试（解析 → 构建 → 降级行为）

背景：基于 Semgrep taint mode 的规则改造（2026-08-25），
.md 规约新增 pattern-sources/pattern-sinks/pattern-sanitizers 代码块，
引擎生成 mode: taint 规则，仅 Semgrep 引擎可执行。
"""

import logging
from unittest.mock import patch

import pytest
import yaml

from rule_engine import MarkdownRuleParser, RuleEngine

_MD_TAINT_RULE = """# 目录穿越 - taint 版

> 用户可控数据流入文件路径操作。

```yaml
id: path-traversal-taint
languages: [java]
severity: CRITICAL
cwe: CWE-22
```

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
```

```pattern-sinks
new File(...)
new FileInputStream(...)
```

```pattern-sanitizers
$F.getName()
```
"""

_MD_TAINT_RULE_LANG_TAGGED = """# 目录穿越 - 多语言 taint

> 用户可控数据流入文件操作。

```yaml
id: path-io-taint
languages: [java, python]
severity: ERROR
```

## 检测模式

### Java

```pattern-sources
$REQ.getParameter(...)
```

```pattern-sinks
new File(...)
```

### Python

```pattern-sources
request.args.get(...)
```

```pattern-sinks
open(...)
```
"""


class TestTaintBlockParsing:
    def test_sources_sinks_sanitizers_parsed(self, tmp_path):
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE, encoding="utf-8")

        rules = MarkdownRuleParser().parse_file(str(md))

        assert len(rules) == 1
        taint = rules[0]["taint"]
        assert [e["content"] for e in taint["sources"]] == [
            "$REQ.getParameter(...)", "$REQ.getHeader(...)",
        ]
        assert [e["content"] for e in taint["sinks"]] == [
            "new File(...)", "new FileInputStream(...)",
        ]
        assert [e["content"] for e in taint["sanitizers"]] == ["$F.getName()"]
        # taint 块不进入普通 patterns（AST/正则引擎不消费）
        assert rules[0]["patterns"] == []

    def test_lang_tagged_taint_entries(self, tmp_path):
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE_LANG_TAGGED, encoding="utf-8")

        rules = MarkdownRuleParser().parse_file(str(md))

        taint = rules[0]["taint"]
        java_sources = [e for e in taint["sources"] if e.get("lang") == "java"]
        py_sources = [e for e in taint["sources"] if e.get("lang") == "python"]
        assert [e["content"] for e in java_sources] == ["$REQ.getParameter(...)"]
        assert [e["content"] for e in py_sources] == ["request.args.get(...)"]

    def test_blank_lines_in_taint_block_skipped(self, tmp_path):
        md = tmp_path / "rule.md"
        md.write_text(
            _MD_TAINT_RULE.replace(
                "$REQ.getParameter(...)\n",
                "$REQ.getParameter(...)\n\n   \n",
            ),
            encoding="utf-8",
        )

        rules = MarkdownRuleParser().parse_file(str(md))
        assert all(e["content"] for e in rules[0]["taint"]["sources"])


def _make_engine(rules):
    engine = RuleEngine.__new__(RuleEngine)
    engine.rules = rules
    return engine


class TestTaintRuleBuilding:
    def test_taint_rule_structure(self, tmp_path):
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE, encoding="utf-8")
        rules = MarkdownRuleParser().parse_file(str(md))

        built = _make_engine(rules)._rules_to_semgrep()

        assert len(built["rules"]) == 1
        rule = built["rules"][0]
        assert rule["id"] == "path-traversal-taint"
        assert rule["mode"] == "taint"
        assert rule["languages"] == ["java"]
        assert rule["pattern-sources"] == [
            {"pattern": "$REQ.getParameter(...)"},
            {"pattern": "$REQ.getHeader(...)"},
        ]
        assert rule["pattern-sanitizers"] == [{"pattern": "$F.getName()"}]

    def test_lang_split_taint_rule(self, tmp_path):
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE_LANG_TAGGED, encoding="utf-8")
        rules = MarkdownRuleParser().parse_file(str(md))

        built = _make_engine(rules)._rules_to_semgrep()

        ids = {r["id"] for r in built["rules"]}
        assert ids == {"path-io-taint__java", "path-io-taint__python"}
        by_id = {r["id"]: r for r in built["rules"]}
        assert by_id["path-io-taint__java"]["pattern-sources"] == [
            {"pattern": "$REQ.getParameter(...)"}
        ]
        assert by_id["path-io-taint__python"]["pattern-sinks"] == [
            {"pattern": "open(...)"}
        ]

    def test_taint_yaml_dump_roundtrip(self, tmp_path):
        """生成的结构必须可被 yaml 序列化（写入临时规则文件的路径）"""
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE, encoding="utf-8")
        rules = MarkdownRuleParser().parse_file(str(md))

        built = _make_engine(rules)._rules_to_semgrep()
        dumped = yaml.dump(built, allow_unicode=True)
        assert yaml.safe_load(dumped)["rules"][0]["mode"] == "taint"


class TestTaintDegradation:
    def test_semgrep_unavailable_logs_taint_loss(self, tmp_path, caplog):
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE, encoding="utf-8")
        rules = MarkdownRuleParser().parse_file(str(md))
        engine = _make_engine(rules)

        repo = tmp_path / "repo"
        repo.mkdir()

        with patch.object(RuleEngine, "_semgrep_available", return_value=False):
            with patch.object(
                RuleEngine, "_run_with_builtin", return_value=[]
            ) as mock_builtin:
                with patch.object(
                    RuleEngine, "_run_with_ast", return_value=[]
                ) as mock_ast:
                    with caplog.at_level(logging.WARNING):
                        engine.run(str(repo), [])

        assert any("taint" in r.message for r in caplog.records)
        mock_builtin.assert_called_once()
        mock_ast.assert_called_once()

    def test_builtin_engine_skips_taint_rules(self, tmp_path):
        """正则回退引擎不消费 taint 块，纯 taint 规则不产生正则检出"""
        md = tmp_path / "rule.md"
        md.write_text(_MD_TAINT_RULE, encoding="utf-8")
        rules = MarkdownRuleParser().parse_file(str(md))
        engine = _make_engine(rules)

        repo = tmp_path / "repo"
        repo.mkdir()
        java = repo / "A.java"
        java.write_text(
            'class A { void f(javax.servlet.http.HttpServletRequest r) '
            '{ String p = r.getParameter("x"); new java.io.File(p); } }',
            encoding="utf-8",
        )

        issues = engine._run_with_builtin(str(repo), [{"path": "A.java"}])
        assert issues == []
