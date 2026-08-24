#!/usr/bin/env python3
"""
最小方案：失败案例累积 + 通过率阈值测试

覆盖：
1. 失败案例累积（CEGIS 核心：反例驱动修复）
   - golden test 失败后带反馈重试（预算上限 3 轮）
   - 每轮重试看到全部历史失败记录
   - 修复成功后停止重试
2. 通过率阈值（≥90% 才允许部署）
   - validation 结果包含 pass_rate 字段
   - pass_rate < 阈值时拒绝部署
"""

import json
import textwrap
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rule_compiler import RuleCompiler


# ===================================================================
# 测试素材
# ===================================================================

SPEC_CONTENT = textwrap.dedent("""\
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


@pytest.fixture
def spec_dir(tmp_path):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "plain-hash.md").write_text(SPEC_CONTENT, encoding="utf-8")
    return specs


class SequenceLLM:
    """按调用顺序返回不同 pattern 的假 LLM（模拟失败后修复）"""

    def __init__(self, patterns):
        self.patterns = patterns
        self.call_count = 0
        self.prompts_received = []

    def is_available(self):
        return True

    def chat(self, prompt, system=None, temperature=0.0, max_tokens=1024):
        self.prompts_received.append(prompt)
        pattern = self.patterns[min(self.call_count, len(self.patterns) - 1)]
        self.call_count += 1
        return pattern


def semgrep_mock(findings_by_path):
    """构造 semgrep mock：{文件名关键词: 命中数}"""
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


class SequenceSemgrep:
    """按调用顺序返回不同 semgrep 结果的 mock"""

    def __init__(self, results_sequence):
        self.results = results_sequence
        self.call_count = 0

    def __call__(self, cmd, **kwargs):
        result = self.results[min(self.call_count, len(self.results) - 1)]
        self.call_count += 1
        return result


# ===================================================================
# 1. 失败案例累积（重试循环）
# ===================================================================

class TestRepairLoop:
    """golden test 失败后的反馈重试"""

    def _compile(self, tmp_path, spec_dir, llm_patterns, semgrep_results):
        fake = SequenceLLM(llm_patterns)
        compiler = RuleCompiler(str(spec_dir), str(tmp_path / "compiled"),
                                llm_client=fake)
        seq = SequenceSemgrep(semgrep_results)
        with patch("subprocess.run", side_effect=seq):
            result = compiler.compile_rule(spec_dir / "plain-hash.md", force=True)
        return result, fake, seq

    def test_retry_triggered_on_failure(self, tmp_path, spec_dir):
        """第 1 轮失败后自动重试，第 2 轮成功"""
        # LLM: 第 1 次返回差 pattern，第 2 次返回好 pattern
        # semgrep: 第 1 次 bad 不命中（失败），第 2 次 bad 命中（通过）
        result, fake, seq = self._compile(
            tmp_path, spec_dir,
            llm_patterns=["bad.pattern(", "$MD.digest($X.getBytes())"],
            semgrep_results=[
                semgrep_mock({"bad": 0, "good": 0}),  # 第 1 轮：漏检
                semgrep_mock({"bad": 1, "good": 0}),  # 第 2 轮：通过
            ],
        )

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        v = rule["rules"][0]["metadata"]["validation"]

        assert fake.call_count == 2, "失败后应自动重试 1 次"
        assert v["status"] == "passed", "第 2 轮应通过验证"

    def test_retry_prompt_contains_failure_feedback(self, tmp_path, spec_dir):
        """重试的 prompt 中包含失败反馈（漏检/误报原因）"""
        result, fake, seq = self._compile(
            tmp_path, spec_dir,
            llm_patterns=["bad.pattern(", "$MD.digest($X.getBytes())"],
            semgrep_results=[
                semgrep_mock({"bad": 0, "good": 0}),
                semgrep_mock({"bad": 1, "good": 0}),
            ],
        )

        # 第 2 次 LLM 调用的 prompt 应包含失败反馈
        assert len(fake.prompts_received) == 2
        retry_prompt = fake.prompts_received[1]
        assert "失败" in retry_prompt or "漏检" in retry_prompt, \
            "重试 prompt 应包含失败反馈信息"

    def test_repair_budget_exhausted(self, tmp_path, spec_dir):
        """所有轮次都失败时，最多重试 3 轮后停止（不无限循环）"""
        result, fake, seq = self._compile(
            tmp_path, spec_dir,
            llm_patterns=["always.bad.pattern("],
            semgrep_results=[semgrep_mock({"bad": 0, "good": 0})],
        )

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        v = rule["rules"][0]["metadata"]["validation"]

        # 1 次初始 + 3 次修复 = 最多 4 次 LLM 调用
        assert fake.call_count == 4, f"应最多调用 4 次（实际 {fake.call_count}）"
        assert v["status"] == "failed", "全部失败时 validation=failed"

    def test_no_retry_when_first_pass_succeeds(self, tmp_path, spec_dir):
        """第 1 轮就通过时不重试（LLM 只调用 1 次）"""
        result, fake, seq = self._compile(
            tmp_path, spec_dir,
            llm_patterns=["$MD.digest($X.getBytes())"],
            semgrep_results=[semgrep_mock({"bad": 1, "good": 0})],
        )

        assert fake.call_count == 1, "第 1 轮通过时不应重试"
        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        v = rule["rules"][0]["metadata"]["validation"]
        assert v["status"] == "passed"

    def test_failure_history_accumulates(self, tmp_path, spec_dir):
        """多轮失败时，每轮都看到全部历史失败记录（累积）"""
        # LLM 返回 3 个不同 pattern（都失败），第 4 次成功
        result, fake, seq = self._compile(
            tmp_path, spec_dir,
            llm_patterns=["p1(", "p2(", "p3(", "$MD.digest($X.getBytes())"],
            semgrep_results=[
                semgrep_mock({"bad": 0, "good": 0}),  # p1 失败
                semgrep_mock({"bad": 0, "good": 0}),  # p2 失败
                semgrep_mock({"bad": 0, "good": 0}),  # p3 失败
                semgrep_mock({"bad": 1, "good": 0}),  # 第 4 次成功
            ],
        )

        assert fake.call_count == 4
        # 第 3 次调用（第 2 轮修复）的 prompt 应包含 2 条历史失败
        prompt_3rd = fake.prompts_received[2]
        assert "第 1 轮" in prompt_3rd or "第1轮" in prompt_3rd, \
            "应包含第 1 轮失败记录"
        assert "第 2 轮" in prompt_3rd or "第2轮" in prompt_3rd, \
            "应包含第 2 轮失败记录"

    def test_validation_records_repair_rounds(self, tmp_path, spec_dir):
        """验证通过时记录修复轮次（可追溯）"""
        result, fake, seq = self._compile(
            tmp_path, spec_dir,
            llm_patterns=["bad.pattern(", "$MD.digest($X.getBytes())"],
            semgrep_results=[
                semgrep_mock({"bad": 0, "good": 0}),
                semgrep_mock({"bad": 1, "good": 0}),
            ],
        )

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        v = rule["rules"][0]["metadata"]["validation"]
        assert v.get("repair_rounds") == 1, "应记录经历 1 轮修复"


# ===================================================================
# 2. 通过率阈值
# ===================================================================

class TestPassRateThreshold:
    """通过率计算与部署阈值"""

    def test_validation_includes_pass_rate(self, tmp_path, spec_dir):
        """validation 结果包含 pass_rate 字段"""
        fake = SequenceLLM(["$MD.digest($X.getBytes())"])
        compiler = RuleCompiler(str(spec_dir), str(tmp_path / "compiled"),
                                llm_client=fake)
        with patch("subprocess.run", return_value=semgrep_mock({"bad": 1, "good": 0})):
            result = compiler.compile_rule(spec_dir / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        v = rule["rules"][0]["metadata"]["validation"]
        assert "pass_rate" in v, "validation 应包含 pass_rate 字段"
        assert v["pass_rate"] == 1.0, "全通过时 pass_rate=1.0"

    def test_pass_rate_partial_when_good_fails(self, tmp_path, spec_dir):
        """bad 命中但 good 误报时，pass_rate=0.5"""
        fake = SequenceLLM(["$MD.digest($X.getBytes())"])
        compiler = RuleCompiler(str(spec_dir), str(tmp_path / "compiled"),
                                llm_client=fake)
        with patch("subprocess.run", return_value=semgrep_mock({"bad": 1, "good": 1})):
            result = compiler.compile_rule(spec_dir / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        v = rule["rules"][0]["metadata"]["validation"]
        assert v["pass_rate"] == 0.5, "2 项测试通过 1 项，pass_rate=0.5"

    def test_deploy_refused_when_pass_rate_below_threshold(self, tmp_path):
        """pass_rate < 90% 时拒绝部署"""
        output_dir = tmp_path / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)
        rule = {
            "rules": [{
                "id": "low-pass-rate",
                "pattern": "$X",
                "languages": ["java"],
                "severity": "ERROR",
                "message": "m",
                "metadata": {
                    "compiled_at": "2026-01-01T00:00:00",
                    "generation_method": "ai",
                    "validation": {
                        "status": "failed",
                        "pass_rate": 0.5,
                    },
                },
            }]
        }
        rule_file = output_dir / "low-pass-rate.yaml"
        rule_file.write_text(yaml.dump(rule, allow_unicode=True), encoding="utf-8")

        compiler = RuleCompiler(str(tmp_path), str(output_dir))
        result = compiler.approve_and_deploy(rule_file, auto_approve=True)

        assert result["status"] == "refused"
        assert "pass_rate" in result.get("message", "") or "通过率" in result.get("message", "")

    def test_deploy_allowed_when_pass_rate_meets_threshold(self, tmp_path):
        """pass_rate >= 90% 时允许部署"""
        output_dir = tmp_path / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)
        rule = {
            "rules": [{
                "id": "high-pass-rate",
                "pattern": "$X",
                "languages": ["java"],
                "severity": "ERROR",
                "message": "m",
                "metadata": {
                    "compiled_at": "2026-01-01T00:00:00",
                    "generation_method": "ai",
                    "validation": {
                        "status": "passed",
                        "pass_rate": 1.0,
                    },
                },
            }]
        }
        rule_file = output_dir / "high-pass-rate.yaml"
        rule_file.write_text(yaml.dump(rule, allow_unicode=True), encoding="utf-8")

        compiler = RuleCompiler(str(tmp_path), str(output_dir))
        result = compiler.approve_and_deploy(rule_file, auto_approve=True)

        assert result["status"] == "approved"
