#!/usr/bin/env python3
"""
规则编译器 LLM 接入测试 (P0-②)

核心诉求：
1. LLM 可用时：规约编译走真实 AI 生成（pattern 来自 LLM），并标记 generation_method="ai"
2. LLM 不可用/失败时：降级启发式，标记 generation_method="heuristic_fallback"，绝不伪装成 AI 产物
3. LLM 返回的 pattern 需要清洗（去除代码围栏/前后缀文本）
4. 差异报告接入 LLM 解读
5. 共享 LLMClient：OpenAI 兼容协议、可注入、可用性检查
"""

import json
import os
import textwrap
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rule_compiler import RuleCompiler
from llm_client import LLMClient


# ===================================================================
# 测试用 Fake LLM（可注入）
# ===================================================================

class FakeLLMClient:
    """可控的假 LLM 客户端"""

    def __init__(self, responses=None, available=True, error=None):
        self.responses = list(responses or [])
        self.available = available
        self.error = error
        self.calls = []  # 记录 (prompt, kwargs)

    def is_available(self):
        return self.available

    def chat(self, prompt, system=None, temperature=0.0, max_tokens=1024):
        self.calls.append({"prompt": prompt, "system": system,
                           "temperature": temperature})
        if self.error:
            raise self.error
        if self.responses:
            return self.responses.pop(0)
        return None


# ===================================================================
# 自然语言规约样例（Format B：无 pattern 块）
# ===================================================================

@pytest.fixture
def natural_language_spec(tmp_path):
    """创建一个自然语言规约（无现成 pattern，需要 AI 编译）"""
    content = textwrap.dedent("""\
        # 禁止使用 MessageDigest 直接对密码做无盐哈希

        ## 严重等级

        ERROR

        ## 违规场景

        使用 MessageDigest 对密码直接做 MD5/SHA 哈希，没有加盐，
        彩虹表可以直接反查出原始密码。

        ### 违规代码

        ```java
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] digest = md.digest(password.getBytes());
        ```

        ## 安全做法

        使用带盐的 PBKDF2/bcrypt 等慢哈希。

        ### 安全代码

        ```java
        byte[] salt = generateSalt();
        PBEKeySpec spec = new PBEKeySpec(password, salt, 10000);
        ```
    """)
    spec = tmp_path / "specs" / "plain-hash.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(content, encoding="utf-8")
    return tmp_path / "specs"


# ===================================================================
# LLMClient 本身
# ===================================================================

class TestLLMClient:
    """共享 LLM 客户端"""

    def _mock_urlopen(self, content):
        resp = MagicMock()
        resp.read.return_value = json.dumps(
            {"choices": [{"message": {"content": content}}]}
        ).encode("utf-8")
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_chat_returns_content(self):
        client = LLMClient(url="https://api.example.com/v1/chat/completions",
                           api_key="sk-test", model="gpt-4")
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen("hello")):
            assert client.chat("ping") == "hello"

    def test_chat_sends_temperature_zero(self):
        client = LLMClient(url="https://api.example.com/v1/chat/completions",
                           api_key="sk-test", model="gpt-4")
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen("x")) as m:
            client.chat("ping", temperature=0.0)
            payload = json.loads(m.call_args[0][0].data)
            assert payload["temperature"] == 0.0

    def test_unavailable_without_url(self):
        client = LLMClient(url="", api_key="", model="")
        assert client.is_available() is False

    def test_chat_failure_returns_none(self):
        client = LLMClient(url="https://api.example.com/v1/chat/completions",
                           api_key="sk-test", model="gpt-4")
        with patch("urllib.request.urlopen", side_effect=ConnectionError("down")):
            assert client.chat("ping") is None

    def test_available_with_url_no_key_required(self):
        client = LLMClient(url="https://local-llm:8080/v1/chat/completions",
                           api_key="", model="local-model")
        assert client.is_available() is True


# ===================================================================
# AI 生成：LLM 可用时 pattern 来自 LLM
# ===================================================================

class TestAIGeneration:
    """LLM 可用时，规则由 AI 生成并明确标记"""

    def test_pattern_comes_from_llm(self, natural_language_spec, tmp_path):
        """pattern 必须来自 LLM 响应，而不是占位推断"""
        fake = FakeLLMClient(responses=["$MD.digest($PASSWORD.getBytes())"])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["pattern"] == "$MD.digest($PASSWORD.getBytes())"

    def test_generation_method_marked_ai(self, natural_language_spec, tmp_path):
        """元数据必须标记 generation_method=ai，可追溯生成方式"""
        fake = FakeLLMClient(responses=["$MD.digest($X.getBytes())"])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["metadata"]["generation_method"] == "ai"

    def test_llm_prompt_contains_rule_context(self, natural_language_spec, tmp_path):
        """发给 LLM 的 prompt 必须包含违规场景和两个示例"""
        fake = FakeLLMClient(responses=["$X"])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        assert len(fake.calls) >= 1
        prompt = fake.calls[0]["prompt"]
        assert "MessageDigest" in prompt          # 违规示例
        assert "PBEKeySpec" in prompt             # 安全示例
        assert "无盐" in prompt                    # 违规场景描述

    def test_llm_called_with_temperature_zero(self, natural_language_spec, tmp_path):
        """规则编译必须用 temperature=0（确定性优先）"""
        fake = FakeLLMClient(responses=["$X"])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        assert fake.calls[0]["temperature"] == 0.0

    def test_pattern_code_fence_stripped(self, natural_language_spec, tmp_path):
        """LLM 返回带 ``` 围栏的 pattern 必须被清洗"""
        fake = FakeLLMClient(responses=["```\n$MD.digest($X.getBytes())\n```"])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["pattern"] == "$MD.digest($X.getBytes())"

    def test_generated_rule_structure_valid(self, natural_language_spec, tmp_path):
        """生成的规则结构完整：id/languages/severity/pattern"""
        fake = FakeLLMClient(responses=["$MD.digest($X.getBytes())"])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        r = rule["rules"][0]
        assert r["id"]                       # 非空 id
        assert r["languages"] == ["java"]
        assert r["severity"] == "ERROR"
        assert r["pattern"]
        assert r["message"]


# ===================================================================
# 降级：LLM 不可用/失败时绝不伪装成 AI 产物
# ===================================================================

class TestFallbackGeneration:
    """LLM 不可用时降级启发式，且必须显式标记"""

    def test_fallback_marked_when_llm_unavailable(self, natural_language_spec, tmp_path):
        """无 LLM：启发式降级，generation_method=heuristic_fallback"""
        fake = FakeLLMClient(available=False)
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["metadata"]["generation_method"] == "heuristic_fallback"

    def test_fallback_when_llm_raises(self, natural_language_spec, tmp_path):
        """LLM 抛异常：降级启发式且不崩溃"""
        fake = FakeLLMClient(error=RuntimeError("api exploded"))
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["metadata"]["generation_method"] == "heuristic_fallback"

    def test_fallback_when_llm_returns_empty(self, natural_language_spec, tmp_path):
        """LLM 返回空串：降级启发式"""
        fake = FakeLLMClient(responses=[""])
        compiler = RuleCompiler(str(natural_language_spec),
                                str(tmp_path / "compiled"), llm_client=fake)
        result = compiler.compile_rule(natural_language_spec / "plain-hash.md", force=True)

        rule = yaml.safe_load(open(result["output"], encoding="utf-8"))
        assert rule["rules"][0]["metadata"]["generation_method"] == "heuristic_fallback"


# ===================================================================
# 差异报告接入 LLM
# ===================================================================

class TestDiffReportWithAI:
    """差异报告由 LLM 解读（可用时）"""

    def _two_versions(self, tmp_path):
        """构造新旧两个版本的规则文件和历史"""
        output_dir = tmp_path / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)
        history_dir = output_dir / ".history"
        history_dir.mkdir(parents=True, exist_ok=True)

        old_rule = {"rules": [{"id": "r1", "pattern": "old($X);",
                               "languages": ["java"], "severity": "WARNING",
                               "message": "m"}]}
        new_rule = {"rules": [{"id": "r1", "pattern": "new($X, $Y);",
                               "languages": ["java"], "severity": "ERROR",
                               "message": "m"}]}
        (history_dir / "r1_20250101_000000.yaml").write_text(
            yaml.dump(old_rule, allow_unicode=True), encoding="utf-8")
        (history_dir / "r1_20250102_000000.yaml").write_text(
            yaml.dump(new_rule, allow_unicode=True), encoding="utf-8")
        current_file = output_dir / "r1.yaml"
        current_file.write_text(yaml.dump(new_rule, allow_unicode=True), encoding="utf-8")
        return current_file

    def test_diff_report_uses_llm_analysis(self, tmp_path):
        """LLM 可用时，差异报告包含 AI 解读文本"""
        fake = FakeLLMClient(responses=["检测范围从单参数扩大到双参数调用，需回归验证。"])
        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"), llm_client=fake)
        current_file = self._two_versions(tmp_path)

        report = compiler.diff_rules(current_file)

        assert report["status"] == "diff_generated"
        assert "检测范围" in report["report"]["ai_analysis"]

    def test_diff_report_structural_changes_kept(self, tmp_path):
        """结构化差异（pattern 变化）仍然保留，AI 只是补充解读"""
        fake = FakeLLMClient(responses=["AI 解读文本"])
        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"), llm_client=fake)
        current_file = self._two_versions(tmp_path)

        report = compiler.diff_rules(current_file)

        changes = report["report"]["changes"]
        assert any(c["type"] == "pattern_changed" for c in changes)

    def test_diff_report_fallback_without_llm(self, tmp_path):
        """无 LLM：结构化差异照常输出，ai_analysis 标记不可用"""
        fake = FakeLLMClient(available=False)
        compiler = RuleCompiler(str(tmp_path), str(tmp_path / "compiled"), llm_client=fake)
        current_file = self._two_versions(tmp_path)

        report = compiler.diff_rules(current_file)

        assert report["report"]["ai_analysis"] == ""
        assert len(report["report"]["changes"]) > 0
