#!/usr/bin/env python3
"""
编译后 Golden Test 强制验证测试 (P1-①)

核心诉求：
1. AI 生成的 pattern 必须通过 golden test 才算有效：
   - 必须命中违规示例（检出能力）
   - 不得命中安全示例（不误报）
2. 验证结果写入规则元数据（validation 字段），可追溯
3. 部署闸门：validation=failed 的规则拒绝部署
4. semgrep 不可用时 validation=skipped，不阻塞但明确留痕
"""

import json
import subprocess
import textwrap
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rule_compiler import RuleCompiler


# ===================================================================
# 共享测试素材
# ===================================================================

JAVA_BAD = "MessageDigest md = MessageDigest.getInstance(\"MD5\");\nbyte[] digest = md.digest(password.getBytes());\n"
JAVA_GOOD = "byte[] salt = generateSalt();\nPBEKeySpec spec = new PBEKeySpec(password, salt, 10000);\n"


@pytest.fixture
def spec_dir(tmp_path):
    """自然语言规约目录（含一个可编译规约）"""
    content = textwrap.dedent("""\
        # 禁止无盐哈希

        ## 严重等级

        ERROR

        ## 违规场景

        MessageDigest 直接对密码做无盐哈希。

        ### 违规代码

        ```java
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] digest = md.digest(password.getBytes());
        ```

        ## 安全做法

        使用带盐慢哈希。

        ### 安全代码

        ```java
        PBEKeySpec spec = new PBEKeySpec(password, salt, 10000);
        ```
    """)
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "plain-hash.md").write_text(content, encoding="utf-8")
    return specs


class FakeLLM:
    """返回指定 pattern 的假 LLM"""

    def __init__(self, pattern):
        self.pattern = pattern

    def is_available(self):
        return True

    def chat(self, prompt, system=None, temperature=0.0, max_tokens=1024):
        return self.pattern


def semgrep_mock(findings_by_path):
    """
    构造 semgrep mock。

    Args:
        findings_by_path: {文件名关键词: 命中数}，如 {"bad": 1, "good": 0}
    """
    results = []
    for key, count in findings_by_path.items():
        for _ in range(count):
            results.append({
                "check_id": "test-rule",
                "path": f"/tmp/golden/{key}.java",
                "start": {"line": 1},
                "end": {"line": 1},
                "extra": {"message": "hit", "severity": "ERROR"},
            })

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"results": results, "errors": []})
    mock_result.stderr = ""
    return mock_result


# ===================================================================
# Golden Test 验证逻辑
# ===================================================================

class TestGoldenTestLogic:
    """golden test 判定逻辑"""

    def _compile(self, tmp_path, spec_dir, pattern, semgrep_result):
        fake = FakeLLM(pattern)
        compiler = RuleCompiler(str(spec_dir), str(tmp_path / "compiled"),
                                llm_client=fake)
        with patch("subprocess.run", return_value=semgrep_result):
            return compiler.compile_rule(spec_dir / "plain-hash.md", force=True)

    def _load_rule(self, result):
        return yaml.safe_load(open(result["output"], encoding="utf-8"))

    def test_pattern_hits_bad_only_passes(self, tmp_path, spec_dir):
        """pattern 命中违规示例且不命中安全示例 -> validation=passed"""
        result = self._compile(tmp_path, spec_dir, "$MD.digest($X.getBytes())",
                               semgrep_mock({"bad": 1, "good": 0}))
        rule = self._load_rule(result)
        assert rule["rules"][0]["metadata"]["validation"]["status"] == "passed"

    def test_pattern_missing_bad_fails(self, tmp_path, spec_dir):
        """pattern 不命中违规示例（漏检）-> validation=failed"""
        result = self._compile(tmp_path, spec_dir, "completely.unrelated.call($X)",
                               semgrep_mock({"bad": 0, "good": 0}))
        rule = self._load_rule(result)
        assert rule["rules"][0]["metadata"]["validation"]["status"] == "failed"
        assert rule["rules"][0]["metadata"]["validation"]["bad_matched"] is False

    def test_pattern_hits_good_fails(self, tmp_path, spec_dir):
        """pattern 命中安全示例（误报）-> validation=failed"""
        result = self._compile(tmp_path, spec_dir, "too.broad.pattern",
                               semgrep_mock({"bad": 1, "good": 1}))
        rule = self._load_rule(result)
        assert rule["rules"][0]["metadata"]["validation"]["status"] == "failed"
        assert rule["rules"][0]["metadata"]["validation"]["good_matched"] is True

    def test_validation_records_semgrep_findings_detail(self, tmp_path, spec_dir):
        """验证结果记录命中细节（bad/good 命中数）"""
        result = self._compile(tmp_path, spec_dir, "$MD.digest($X)",
                               semgrep_mock({"bad": 2, "good": 0}))
        rule = self._load_rule(result)
        v = rule["rules"][0]["metadata"]["validation"]
        assert v["bad_findings"] == 2
        assert v["good_findings"] == 0

    def test_semgrep_error_marks_skipped(self, tmp_path, spec_dir):
        """semgrep 执行报错 -> validation=skipped（不阻塞编译，但明确留痕）"""
        mock_result = MagicMock()
        mock_result.returncode = 2  # 非正常退出
        mock_result.stdout = "{}"
        mock_result.stderr = "semgrep not found"

        result = self._compile(tmp_path, spec_dir, "$MD.digest($X)", mock_result)
        rule = self._load_rule(result)
        assert rule["rules"][0]["metadata"]["validation"]["status"] == "skipped"

    def test_no_examples_marks_skipped(self, tmp_path):
        """规约没有违规/安全示例 -> validation=skipped"""
        specs = tmp_path / "specs2"
        specs.mkdir()
        (specs / "no-examples.md").write_text(
            "# 某规约\n\n## 严重等级\n\nWARNING\n\n## 违规场景\n\n描述而已。\n",
            encoding="utf-8")

        compiler = RuleCompiler(str(specs), str(tmp_path / "compiled2"),
                                llm_client=FakeLLM("$X"))
        result = compiler.compile_rule(specs / "no-examples.md", force=True)
        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["metadata"]["validation"]["status"] == "skipped"


# ===================================================================
# 真实 semgrep 冒烟测试（本机已装 semgrep 时执行）
# ===================================================================

class TestGoldenTestRealSemgrep:
    """用真实 semgrep 验证 golden test 管线（非 mock）"""

    def test_real_semgrep_validates_pattern(self, tmp_path, spec_dir):
        """端到端：AI pattern -> 真实 semgrep 校验 -> passed"""
        # 一个能精确命中 bad 不命中 good 的 pattern
        fake = FakeLLM("MessageDigest.getInstance(\"MD5\")")
        compiler = RuleCompiler(str(spec_dir), str(tmp_path / "compiled"),
                                llm_client=fake)
        result = compiler.compile_rule(spec_dir / "plain-hash.md", force=True)
        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))

        v = rule["rules"][0]["metadata"]["validation"]
        # 真实 semgrep 下该 pattern 应命中 bad
        assert v["status"] == "passed"
        assert v["bad_matched"] is True
        assert v["good_matched"] is False


# ===================================================================
# 部署闸门：validation=failed 拒绝部署
# ===================================================================

class TestDeployGate:
    """approve_and_deploy 必须拦截未通过验证的规则"""

    def _make_rule_file(self, tmp_path, validation_status):
        output_dir = tmp_path / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)
        rule = {
            "rules": [{
                "id": "gate-test",
                "pattern": "$X",
                "languages": ["java"],
                "severity": "ERROR",
                "message": "m",
                "metadata": {
                    "compiled_at": "2025-01-01T00:00:00",
                    "generation_method": "ai",
                    "validation": {"status": validation_status},
                },
            }]
        }
        rule_file = output_dir / "gate-test.yaml"
        rule_file.write_text(yaml.dump(rule, allow_unicode=True), encoding="utf-8")
        return rule_file

    def test_deploy_refused_when_validation_failed(self, tmp_path):
        """validation=failed -> 拒绝部署"""
        rule_file = self._make_rule_file(tmp_path, "failed")
        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"))
        result = compiler.approve_and_deploy(rule_file, auto_approve=True)

        assert result["status"] == "refused"
        assert "validation" in result["message"].lower() or "验证" in result["message"]

    def test_deploy_allowed_when_validation_passed(self, tmp_path):
        """validation=passed -> 允许部署"""
        rule_file = self._make_rule_file(tmp_path, "passed")
        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"))
        result = compiler.approve_and_deploy(rule_file, auto_approve=True)

        assert result["status"] == "approved"

    def test_deploy_warns_but_allows_when_skipped(self, tmp_path):
        """validation=skipped（semgrep 不可用）-> 允许部署但结果中带警告"""
        rule_file = self._make_rule_file(tmp_path, "skipped")
        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"))
        result = compiler.approve_and_deploy(rule_file, auto_approve=True)

        assert result["status"] == "approved"
        assert result.get("warnings")

    def test_deploy_allows_legacy_rule_without_validation(self, tmp_path):
        """旧规则（无 validation 字段）-> 不阻塞（向后兼容）"""
        output_dir = tmp_path / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)
        rule = {"rules": [{"id": "legacy", "pattern": "$X", "languages": ["java"],
                           "severity": "WARNING", "message": "m"}]}
        rule_file = output_dir / "legacy.yaml"
        rule_file.write_text(yaml.dump(rule), encoding="utf-8")

        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"))
        result = compiler.approve_and_deploy(rule_file, auto_approve=True)

        assert result["status"] == "approved"
