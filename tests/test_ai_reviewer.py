#!/usr/bin/env python3
"""
AI 评审器单元测试 (UT1-UT3)

覆盖 AIReviewer 的核心方法：
- UT1: _build_prompt() 生成符合 OpenAI API 格式的 prompt
- UT2: _parse_response() 正确解析 JSON 响应 / 处理无效 JSON
- UT3: _is_available() 在有/无 API Key 时的行为
- API 超时处理
"""

import json
import os
import textwrap
import urllib.request
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from ai_reviewer import AIReviewer


# ===================================================================
# 辅助 fixtures
# ===================================================================

@pytest.fixture
def reviewer_with_config():
    """创建带有完整配置的 AIReviewer 实例"""
    config = {
        "llm": {
            "url": "https://api.openai.com/v1/chat/completions",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4",
        },
        "confidence_threshold": 0.7,
    }
    return AIReviewer(config)


@pytest.fixture
def reviewer_without_config():
    """创建无 LLM 配置的 AIReviewer 实例"""
    config = {}
    return AIReviewer(config)


@pytest.fixture
def reviewer_no_api_key():
    """创建有 URL 但无 API Key 环境变量的 AIReviewer 实例"""
    config = {
        "llm": {
            "url": "https://api.openai.com/v1/chat/completions",
            "api_key_env": "NONEXISTENT_API_KEY_12345",
            "model": "gpt-4",
        },
        "confidence_threshold": 0.7,
    }
    return AIReviewer(config)


@pytest.fixture
def two_issues():
    """创建两个用于 AI 评审测试的问题（包含一个真实问题和一个疑似误报）"""
    return [
        {
            "rule_id": "xxe-java-document-builder",
            "category": "security",
            "severity": "ERROR",
            "file": "src/main/java/com/example/Parser.java",
            "line": 42,
            "end_line": 45,
            "message": "XXE vulnerability: DocumentBuilderFactory not secured",
            "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
        },
        {
            "rule_id": "naming-convention",
            "category": "implementation",
            "severity": "WARNING",
            "file": "src/main/java/com/example/Utils.java",
            "line": 10,
            "end_line": 10,
            "message": "Variable name does not follow convention",
            "code_snippet": "String a = \"hello\";",
        },
    ]


@pytest.fixture
def two_issue_diff():
    """创建与 two_issues 配套的 diff 结果"""
    return {
        "changed_files": [
            {"path": "src/main/java/com/example/Parser.java", "status": "modified"},
            {"path": "src/main/java/com/example/Utils.java", "status": "added"},
        ],
        "summary": {"total_files": 2, "total_lines": 50},
    }


@pytest.fixture
def two_issue_ai_response():
    """创建与 two_issues 配套的 AI 响应"""
    return json.dumps([
        {
            "rule_id": "xxe-java-document-builder",
            "is_valid": True,
            "confidence": 0.95,
            "enhanced_fix": "在创建 DocumentBuilder 前调用 factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true) 禁用 DTD",
        },
        {
            "rule_id": "naming-convention",
            "is_valid": False,
            "confidence": 0.3,
            "enhanced_fix": "",
        },
    ], ensure_ascii=False)


# ===================================================================
# UT1: _build_prompt() 生成符合 OpenAI API 格式的 prompt
# ===================================================================

class TestBuildPrompt:
    """测试 prompt 构建"""

    def test_build_prompt_format(self, reviewer_with_config, two_issues, two_issue_diff, sample_call_graph):
        """UT1: _build_prompt() 返回非空字符串且包含关键信息"""
        prompt = reviewer_with_config._build_prompt(
            two_issues, two_issue_diff, sample_call_graph
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_build_prompt_contains_issues(self, reviewer_with_config, two_issues, two_issue_diff, sample_call_graph):
        """UT1: prompt 中包含扫描结果的问题信息"""
        prompt = reviewer_with_config._build_prompt(
            two_issues, two_issue_diff, sample_call_graph
        )

        # prompt 应包含规则 ID
        assert "xxe-java-document-builder" in prompt
        assert "naming-convention" in prompt

    def test_build_prompt_contains_changed_files(self, reviewer_with_config, two_issues, two_issue_diff, sample_call_graph):
        """UT1: prompt 中包含变更文件列表"""
        prompt = reviewer_with_config._build_prompt(
            two_issues, two_issue_diff, sample_call_graph
        )

        assert "Parser.java" in prompt
        assert "Utils.java" in prompt

    def test_build_prompt_contains_output_format(self, reviewer_with_config, sample_issues, sample_diff_result, sample_call_graph):
        """UT1: prompt 中包含期望的输出格式说明"""
        prompt = reviewer_with_config._build_prompt(
            sample_issues, sample_diff_result, sample_call_graph
        )

        # 应包含 JSON 输出格式的指示
        assert "JSON" in prompt
        assert "rule_id" in prompt
        # 新提示词使用 is_false_positive 或 is_valid
        assert "is_false_positive" in prompt or "is_valid" in prompt
        assert "confidence" in prompt or "ai_confidence" in prompt

    def test_build_prompt_contains_task_description(self, reviewer_with_config, sample_issues, sample_diff_result, sample_call_graph):
        """UT1: prompt 中包含任务描述"""
        prompt = reviewer_with_config._build_prompt(
            sample_issues, sample_diff_result, sample_call_graph
        )

        # 应包含任务指示
        assert "评审" in prompt or "review" in prompt.lower()

    def test_build_prompt_is_chinese(self, reviewer_with_config, sample_issues, sample_diff_result, sample_call_graph):
        """UT1: prompt 使用中文编写"""
        prompt = reviewer_with_config._build_prompt(
            sample_issues, sample_diff_result, sample_call_graph
        )

        # prompt 应包含中文内容
        assert "代码" in prompt or "评审" in prompt


# ===================================================================
# UT2: _parse_response() 正确解析 JSON 响应
# ===================================================================

class TestParseResponse:
    """测试 AI 响应解析"""

    def test_parse_response_json(
        self, reviewer_with_config, two_issues, two_issue_ai_response
    ):
        """UT2: 正确解析有效 JSON 响应并过滤低置信度结果"""
        result = reviewer_with_config._parse_response(
            two_issues, two_issue_ai_response
        )

        # xxe-java-document-builder 的 confidence=0.95 >= 0.7，应保留
        assert len(result) >= 1
        valid_ids = [r["rule_id"] for r in result]
        assert "xxe-java-document-builder" in valid_ids

    def test_parse_response_filters_low_confidence(
        self, reviewer_with_config, two_issues, two_issue_ai_response
    ):
        """UT2: 过滤掉置信度低于阈值的结果"""
        result = reviewer_with_config._parse_response(
            two_issues, two_issue_ai_response
        )

        # naming-convention 的 confidence=0.3 < 0.7，应被过滤
        valid_ids = [r["rule_id"] for r in result]
        assert "naming-convention" not in valid_ids

    def test_parse_response_filters_invalid(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 过滤掉 is_valid=False 的结果"""
        response = json.dumps([
            {
                "rule_id": "xxe-java-document-builder",
                "is_valid": False,
                "confidence": 0.95,
                "enhanced_fix": "",
            },
        ])

        result = reviewer_with_config._parse_response(two_issues, response)

        valid_ids = [r["rule_id"] for r in result]
        assert "xxe-java-document-builder" not in valid_ids

    def test_parse_response_filters_formal_false_positive_fields(
        self, reviewer_with_config, two_issues
    ):
        """正式 prompt 契约的 is_false_positive=true 必须被过滤"""
        response = json.dumps([
            {
                "rule_id": "xxe-java-document-builder",
                "file": "src/main/java/com/example/Parser.java",
                "line": 42,
                "is_false_positive": True,
                "ai_confidence": 0.99,
                "analysis": "已有安全配置，属于误报",
                "enhanced_fix": "",
            },
        ])

        result = reviewer_with_config._parse_response(two_issues, response)

        valid_ids = [r["rule_id"] for r in result]
        assert "xxe-java-document-builder" not in valid_ids

    def test_parse_response_uses_formal_confidence_and_analysis(
        self, reviewer_with_config, two_issues
    ):
        """正式 ai_confidence 与 analysis 应合并到保留的问题"""
        response = json.dumps([
            {
                "rule_id": "xxe-java-document-builder",
                "file": "src/main/java/com/example/Parser.java",
                "line": 42,
                "is_false_positive": False,
                "ai_confidence": 0.96,
                "analysis": "外部实体未禁用",
                "enhanced_fix": "factory.setFeature(...)",
            },
        ])

        result = reviewer_with_config._parse_response(two_issues, response)
        issue = next(i for i in result if i["rule_id"] == "xxe-java-document-builder")

        assert issue["ai_confidence"] == 0.96
        assert issue["analysis"] == "外部实体未禁用"
        assert issue["is_false_positive"] is False
        assert issue["needs_review"] is False

    def test_formal_fields_take_precedence_over_legacy_fields(
        self, reviewer_with_config, two_issues
    ):
        """新旧字段同时存在时，以正式 prompt 契约为准"""
        response = json.dumps([
            {
                "rule_id": "xxe-java-document-builder",
                "is_false_positive": True,
                "ai_confidence": 0.95,
                "is_valid": True,
                "confidence": 0.95,
            },
        ])

        result = reviewer_with_config._parse_response(two_issues, response)

        assert "xxe-java-document-builder" not in [r["rule_id"] for r in result]

    def test_parse_response_enhances_fix(
        self, reviewer_with_config, two_issues, two_issue_ai_response
    ):
        """UT2: 增强修复建议被写入 issue"""
        result = reviewer_with_config._parse_response(
            two_issues, two_issue_ai_response
        )

        xxe_issue = next(
            (r for r in result if r["rule_id"] == "xxe-java-document-builder"),
            None,
        )
        assert xxe_issue is not None
        assert "fix" in xxe_issue
        assert "setFeature" in xxe_issue["fix"]

    def test_parse_response_adds_confidence(
        self, reviewer_with_config, two_issues, two_issue_ai_response
    ):
        """UT2: 解析后 issue 包含 ai_confidence 字段"""
        result = reviewer_with_config._parse_response(
            two_issues, two_issue_ai_response
        )

        for issue in result:
            assert "ai_confidence" in issue

    def test_parse_response_with_markdown_code_block(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 处理包含 markdown 代码块包裹的 JSON 响应"""
        response = "```json\n" + json.dumps([
            {
                "rule_id": "xxe-java-document-builder",
                "is_valid": True,
                "confidence": 0.9,
                "enhanced_fix": "修复建议",
            },
        ]) + "\n```"

        result = reviewer_with_config._parse_response(two_issues, response)

        assert len(result) >= 1
        assert result[0]["rule_id"] == "xxe-java-document-builder"


# ===================================================================
# UT2: _parse_response() 处理无效 JSON
# ===================================================================

class TestParseResponseInvalidJson:
    """测试无效 JSON 响应的处理"""

    def test_parse_response_invalid_json(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 无效 JSON 响应返回原始问题列表"""
        result = reviewer_with_config._parse_response(
            two_issues, "this is not valid json"
        )

        # 应返回原始结果
        assert result == two_issues

    def test_parse_response_empty_string(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 空字符串响应返回原始问题列表"""
        result = reviewer_with_config._parse_response(two_issues, "")

        assert result == two_issues

    def test_parse_response_empty_json_array(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 空 JSON 数组时 fail-open，全部保留并转人工复核"""
        result = reviewer_with_config._parse_response(two_issues, "[]")

        assert len(result) == len(two_issues)
        assert all(issue["needs_review"] is True for issue in result)
        assert all("ai_confidence" not in issue for issue in result)

    def test_parse_response_partial_json(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 部分有效的 JSON（缺少字段）保留并转人工复核"""
        response = json.dumps([
            {"rule_id": "xxe-java-document-builder"},
            # 缺少 is_valid, confidence, enhanced_fix
        ])

        result = reviewer_with_config._parse_response(two_issues, response)

        assert len(result) == len(two_issues)
        assert all(issue["needs_review"] is True for issue in result)

    @pytest.mark.parametrize(
        "response_item",
        [
            {"rule_id": "xxe-java-document-builder", "ai_confidence": 0.9},
            {"rule_id": "xxe-java-document-builder", "is_false_positive": False},
            {
                "rule_id": "xxe-java-document-builder",
                "is_false_positive": False,
                "ai_confidence": "invalid",
            },
        ],
    )
    def test_missing_or_invalid_formal_fields_need_review(
        self, reviewer_with_config, two_issues, response_item
    ):
        """缺少必需字段或置信度非法时不能静默删除或伪造置信度"""
        result = reviewer_with_config._parse_response(
            two_issues, json.dumps([response_item])
        )
        issue = next(i for i in result if i["rule_id"] == "xxe-java-document-builder")

        assert issue["needs_review"] is True
        assert issue["is_false_positive"] is False

    def test_parse_response_non_list_json(
        self, reviewer_with_config, two_issues
    ):
        """UT2: 非数组 JSON 返回原始问题列表"""
        response = json.dumps({"key": "value"})

        result = reviewer_with_config._parse_response(two_issues, response)

        # 应优雅处理，返回原始结果
        assert result == two_issues


# ===================================================================
# UT3: _is_available() 在有/无 API Key 时的行为
# ===================================================================

class TestIsAvailable:
    """测试 AI 评审可用性检查"""

    def test_is_available_with_api_key(self, reviewer_with_config):
        """UT3: 有 URL 和有效 API Key 时返回 True"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            assert reviewer_with_config._is_available() is True

    def test_is_available_without_api_key(self, reviewer_no_api_key):
        """UT3: 有 URL 但无 API Key 环境变量时返回 False"""
        # 确保环境变量不存在
        env_key = reviewer_no_api_key.llm_config["api_key_env"]
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(env_key, None)
            assert reviewer_no_api_key._is_available() is False

    def test_is_available_without_url(self, reviewer_without_config):
        """UT3: 无 URL 配置时返回 False"""
        assert reviewer_without_config._is_available() is False

    def test_is_available_empty_url(self):
        """UT3: URL 为空字符串时返回 False"""
        config = {"llm": {"url": "", "api_key_env": "OPENAI_API_KEY"}}
        reviewer = AIReviewer(config)
        assert reviewer._is_available() is False

    def test_is_available_no_api_key_required(self):
        """UT3: 配置中未指定 api_key_env 时，只要有 URL 就可用"""
        config = {"llm": {"url": "https://api.example.com/v1"}}
        reviewer = AIReviewer(config)
        assert reviewer._is_available() is True

    def test_is_available_empty_api_key_env(self):
        """UT3: api_key_env 为空字符串时，不检查环境变量"""
        config = {"llm": {"url": "https://api.example.com/v1", "api_key_env": ""}}
        reviewer = AIReviewer(config)
        assert reviewer._is_available() is True


# ===================================================================
# API 超时处理
# ===================================================================

class TestAPITimeout:
    """测试 API 超时场景"""

    def test_api_timeout_returns_original(
        self, reviewer_with_config, two_issues, two_issue_diff, sample_call_graph
    ):
        """API 超时时返回原始问题列表"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = TimeoutError("Connection timed out")

                result = reviewer_with_config.review(
                    two_issues, two_issue_diff, sample_call_graph
                )

        # 超时时应返回原始结果
        assert result == two_issues

    def test_api_network_error_returns_original(
        self, reviewer_with_config, two_issues, two_issue_diff, sample_call_graph
    ):
        """网络错误时返回原始问题列表"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = ConnectionError("Network unreachable")

                result = reviewer_with_config.review(
                    two_issues, two_issue_diff, sample_call_graph
                )

        assert result == two_issues

    def test_api_returns_invalid_response(
        self, reviewer_with_config, two_issues, two_issue_diff, sample_call_graph
    ):
        """API 返回无效响应时返回原始问题列表"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("urllib.request.urlopen", return_value=mock_response):
                result = reviewer_with_config.review(
                    two_issues, two_issue_diff, sample_call_graph
                )

        # 无效响应应返回原始结果
        assert result == two_issues


# ===================================================================
# 集成场景测试
# ===================================================================

class TestReviewIntegration:
    """AI 评审集成场景测试"""

    def test_review_empty_issues(self, reviewer_with_config):
        """空问题列表时直接返回空列表"""
        result = reviewer_with_config.review([], {}, {})
        assert result == []

    def test_review_unavailable_returns_original(
        self, reviewer_without_config, sample_issues, sample_diff_result, sample_call_graph
    ):
        """AI 不可用时返回原始问题列表"""
        result = reviewer_without_config.review(
            sample_issues, sample_diff_result, sample_call_graph
        )
        assert result == sample_issues

    def test_review_batches_large_input(self, reviewer_with_config, sample_diff_result, sample_call_graph):
        """大量问题时分批处理"""
        # 创建超过 batch_size(20) 的问题列表
        large_issues = [
            {"rule_id": f"rule-{i}", "message": f"Issue {i}"}
            for i in range(25)
        ]

        # 模拟 LLM 调用返回有效响应
        mock_response_data = json.dumps([
            {"rule_id": f"rule-{i}", "is_valid": True, "confidence": 0.9, "enhanced_fix": ""}
            for i in range(25)
        ])

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": mock_response_data}}]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with patch("urllib.request.urlopen", return_value=mock_response):
                result = reviewer_with_config.review(
                    large_issues, sample_diff_result, sample_call_graph
                )

        # 所有问题应被保留（confidence=0.9 >= 0.7）
        assert len(result) == 25
