#!/usr/bin/env python3
"""
P0 规则降噪测试

背景（2026-08-24 双盲实测，Spring Boot 50 文件）：
- crypto-hardcoded-key-java 误报 706 次（占检出 27%）
  原因：pattern `String $VAR = "...";` 匹配一切字符串赋值，
  metavariable-regex 变量名过滤只写在散文里未生效
- null-java-unwrap-boxed 误报 761 次（占检出 29%）
  原因：pattern `int $X = $INTEGER_OBJ;` 匹配一切 int 赋值

收紧后必须：真阳性仍然命中，明显误报不再命中。
"""

import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from rule_engine import RuleEngine


@pytest.fixture(scope="module")
def engine():
    """加载真实规约库（default profile）"""
    with open(PROJECT_ROOT / "references" / "profiles" / "default.yaml") as f:
        profile = yaml.safe_load(f)
    return RuleEngine(specs_dir=str(PROJECT_ROOT / "references"), profile=profile)


def run_builtin(engine, tmp_path, filename, code):
    """用内置引擎扫描临时 Java 文件（含熵门控，对齐 run() 完整管线），返回命中 rule_id 列表"""
    src = tmp_path / filename
    src.write_text(code, encoding="utf-8")
    issues = engine._run_with_builtin(str(tmp_path), [{"path": filename}])
    issues = engine._apply_entropy_gate(issues)
    return [i["rule_id"] for i in issues if i.get("file") == filename]


# ===================================================================
# crypto-hardcoded-key-java 收紧
# ===================================================================

class TestHardcodedKeyPrecision:
    def test_real_password_assignment_detected(self, engine, tmp_path):
        """真阳性：敏感变量名 + 长字面量 -> 必须命中"""
        rules = run_builtin(engine, tmp_path, "Db.java", """
public class Db {
    void connect() {
        String dbPassword = "hunter2_secret_value";
    }
}
""")
        assert "crypto-hardcoded-key-java" in rules

    def test_api_key_detected(self, engine, tmp_path):
        """真阳性：apiKey 命名变体"""
        rules = run_builtin(engine, tmp_path, "Api.java", """
public class Api {
    void call() {
        String apiKey = "sk-1234567890abcdef";
    }
}
""")
        assert "crypto-hardcoded-key-java" in rules

    def test_normal_string_not_detected(self, engine, tmp_path):
        """误报消除：普通字符串赋值（变量名不含敏感词）"""
        rules = run_builtin(engine, tmp_path, "Label.java", """
public class Label {
    void render() {
        String displayLabel = "some very long label text";
    }
}
""")
        assert "crypto-hardcoded-key-java" not in rules

    def test_placeholder_not_detected(self, engine, tmp_path):
        """误报消除：${...} 模板占位符（配置注入，非硬编码）"""
        rules = run_builtin(engine, tmp_path, "Conf.java", """
public class Conf {
    void load() {
        String password = "${DB_PASSWORD}";
    }
}
""")
        assert "crypto-hardcoded-key-java" not in rules

    def test_short_value_not_detected(self, engine, tmp_path):
        """误报消除：短占位值（< 8 字符）"""
        rules = run_builtin(engine, tmp_path, "Tok.java", """
public class Tok {
    void check() {
        String apiToken = "abc";
    }
}
""")
        assert "crypto-hardcoded-key-java" not in rules


# ===================================================================
# null-java-unwrap-boxed 收紧
# ===================================================================

class TestUnwrapBoxedPrecision:
    def test_map_get_unboxing_detected(self, engine, tmp_path):
        """真阳性：Map.get 返回 Integer 直接拆箱 -> 经典 NPE 源"""
        rules = run_builtin(engine, tmp_path, "Cache.java", """
public class Cache {
    void load(java.util.Map<String, Integer> cache) {
        int count = cache.get("hits");
    }
}
""")
        assert "null-java-unwrap-boxed" in rules

    def test_literal_assignment_not_detected(self, engine, tmp_path):
        """误报消除：int 字面量赋值（无数百万种安全场景）"""
        rules = run_builtin(engine, tmp_path, "Port.java", """
public class Port {
    void start() {
        int port = 8080;
        int retries = 3;
    }
}
""")
        assert "null-java-unwrap-boxed" not in rules

    def test_int_returning_method_not_detected(self, engine, tmp_path):
        """误报消除：返回基本类型 int 的方法调用（无拆箱）"""
        rules = run_builtin(engine, tmp_path, "Svc.java", """
public class Svc {
    void run() {
        int count = getCount();
    }
    int getCount() { return 0; }
}
""")
        assert "null-java-unwrap-boxed" not in rules

    def test_plain_variable_read_not_detected(self, engine, tmp_path):
        """误报消除：基本类型变量间赋值"""
        rules = run_builtin(engine, tmp_path, "Calc.java", """
public class Calc {
    void sum(int a, int b) {
        int total = a + b;
    }
}
""")
        assert "null-java-unwrap-boxed" not in rules


# ===================================================================
# 分层评审（P0-b）
# ===================================================================

class TestTieredReview:
    def _make_issues(self):
        return [
            {"rule_id": "r1", "severity": "CRITICAL", "file": "a.java", "line": 1},
            {"rule_id": "r2", "severity": "HIGH", "file": "a.java", "line": 2},
            {"rule_id": "r3", "severity": "ERROR", "file": "a.java", "line": 3},
            {"rule_id": "r4", "severity": "WARNING", "file": "a.java", "line": 4},
            {"rule_id": "r5", "severity": "INFO", "file": "a.java", "line": 5},
        ]

    def test_high_severity_goes_to_llm(self):
        from scan import tiered_ai_review

        class FakeReviewer:
            def __init__(self):
                self.received = None

            def review(self, issues, diff, cg):
                self.received = issues
                return issues

        reviewer = FakeReviewer()
        issues, triage = tiered_ai_review(
            reviewer, self._make_issues(), {}, {}, tiered=True
        )
        # CRITICAL/HIGH/ERROR 送 LLM
        assert [i["rule_id"] for i in reviewer.received] == ["r1", "r2", "r3"]
        assert triage == {"reviewed": 3, "stats_only": 2}
        # WARNING/INFO 原样保留，总数不变
        assert {i["rule_id"] for i in issues} == {"r1", "r2", "r3", "r4", "r5"}

    def test_tiered_false_reviews_everything(self):
        from scan import tiered_ai_review

        class FakeReviewer:
            def review(self, issues, diff, cg):
                return issues

        raw = self._make_issues()
        issues, triage = tiered_ai_review(
            FakeReviewer(), raw, {}, {}, tiered=False
        )
        assert triage["reviewed"] == 5
        assert triage["stats_only"] == 0

    def test_empty_high_tier(self):
        from scan import tiered_ai_review

        class FakeReviewer:
            def review(self, issues, diff, cg):
                assert issues == []
                return []

        raw = [{"rule_id": "r", "severity": "WARNING", "file": "a", "line": 1}]
        issues, triage = tiered_ai_review(FakeReviewer(), raw, {}, {})
        assert issues == raw
        assert triage == {"reviewed": 0, "stats_only": 1}
