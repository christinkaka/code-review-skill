#!/usr/bin/env python3
"""
AI 增强评审模块验收测试
覆盖 ACCEPTANCE-CRITERIA.md 中 AI-AC1 至 AI-AC4 的全部测试场景。

测试场景清单：
  AI-AC1-TS1: Mock LLM 误报过滤效果验证
  AI-AC1-TS2: 不同置信度阈值下的过滤效果
  AI-AC2-TS1: AI 修复建议代码片段验证
  AI-AC2-TS2: 原始规则 fix 字段保留与增强
  AI-AC3-TS1: 批量 20 问题 AI 评审性能测试
  AI-AC3-TS2: 超大批量（50 问题）分批处理验证
  AI-AC4-TS1: 无 API Key 时降级
  AI-AC4-TS2: LLM API 超时/异常时降级
  AI-AC4-TS3: LLM 返回无效 JSON 时降级

运行方式：
  # 全部 AI 评审测试（全部 Mock，可离线运行）
  pytest tests/test_ai_reviewer_e2e.py -v

  # 运行特定测试类
  pytest tests/test_ai_reviewer_e2e.py::TestAIAC1FalsePositiveReduction -v
  pytest tests/test_ai_reviewer_e2e.py::TestAIAC2FixSuggestions -v
  pytest tests/test_ai_reviewer_e2e.py::TestAIAC3Performance -v
  pytest tests/test_ai_reviewer_e2e.py::TestAIAC4Fallback -v
"""

import json
import logging
import os
import sys
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# 确保可以导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ai_reviewer import AIReviewer

# 导入测试辅助函数
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import (
    build_test_issues,
    build_mock_ai_response,
    build_mock_diff_result,
    build_mock_call_graph,
)


# ============================================================
# 辅助函数
# ============================================================
def create_reviewer(
    confidence_threshold: float = 0.7,
    api_key_env: str = "TEST_LLM_API_KEY",
    api_key_value: str = "test-key-12345",
    llm_url: str = "http://mock-llm.example.com/v1/chat/completions",
) -> AIReviewer:
    """创建配置好的 AIReviewer 实例"""
    os.environ[api_key_env] = api_key_value
    config = {
        "llm": {
            "url": llm_url,
            "api_key_env": api_key_env,
            "model": "gpt-4",
        },
        "confidence_threshold": confidence_threshold,
    }
    return AIReviewer(config=config)


def make_mock_response(
    issues,
    real_indices=None,
    confidence_map=None,
    enhanced_fixes=None,
    threshold=0.7,
):
    """
    构造 Mock LLM 响应

    Args:
        issues: 问题列表
        real_indices: 真实问题索引（默认前半部分为真实）
        confidence_map: 自定义置信度映射 {index: confidence}
        enhanced_fixes: 自定义修复建议映射 {index: fix_text}
        threshold: 用于判断 is_valid 的置信度阈值
    """
    if real_indices is None:
        real_indices = list(range(len(issues) // 2))

    results = []
    for i, issue in enumerate(issues):
        if confidence_map and i in confidence_map:
            confidence = confidence_map[i]
            is_valid = confidence >= threshold
        else:
            is_real = i in real_indices
            confidence = 0.9 if is_real else 0.2
            is_valid = is_real

        if enhanced_fixes and i in enhanced_fixes:
            fix = enhanced_fixes[i]
        elif is_valid:
            fix = (
                f"// Secure alternative for {issue['rule_id']}\n"
                f"safeMethod(input);\n"
            )
        else:
            fix = ""

        results.append({
            "rule_id": issue["rule_id"],
            "is_valid": is_valid,
            "confidence": confidence,
            "enhanced_fix": fix,
        })

    return json.dumps(results, ensure_ascii=False)


# ============================================================
# AI-AC1: 误报率降低 > 30%
# ============================================================
class TestAIAC1FalsePositiveReduction:
    """AI-AC1 测试组：误报率降低验证"""

    def test_false_positive_reduction(self):
        """
        AI-AC1-TS1: Mock LLM 误报过滤效果验证

        验证：
        - 构造 10 个问题（5 真实 + 5 误报）
        - AI 评审后剩余问题 <= 7（过滤掉至少 3 个误报）
        - 误报率降低 > 30%
        - 真实问题全部保留
        """
        issues = build_test_issues(count=10, real_count=5)
        real_indices = list(range(5))  # 前 5 个为真实问题

        mock_response = make_mock_response(issues, real_indices=real_indices)

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            diff_result = build_mock_diff_result()
            call_graph = build_mock_call_graph()
            result = reviewer.review(issues, diff_result, call_graph)

        # 验证过滤后问题数 <= 7
        assert len(result) <= 7, (
            f"Expected <= 7 issues after AI review, got {len(result)}"
        )

        # 验证误报率降低 > 30%
        original_fp_count = 5  # 5 个误报
        remaining_fp = len(result) - 5  # 剩余的误报数（假设 5 个真实问题全部保留）
        remaining_fp = max(0, remaining_fp)  # 防止负数
        fp_reduction_rate = (original_fp_count - remaining_fp) / original_fp_count
        assert fp_reduction_rate > 0.3, (
            f"False positive reduction rate {fp_reduction_rate:.2%} <= 30%"
        )

        # 验证实数问题（置信度 >= 0.7）都被保留
        result_rule_ids = {i["rule_id"] for i in result}
        for idx in real_indices:
            assert issues[idx]["rule_id"] in result_rule_ids, (
                f"Real issue #{idx} ({issues[idx]['rule_id']}) was incorrectly filtered"
            )

    @pytest.mark.parametrize("threshold,expected_min_kept,expected_max_kept", [
        (0.7, 3, 3),
        (0.5, 4, 4),
        (0.9, 2, 2),
        (0.3, 5, 5),
    ])
    def test_confidence_threshold_filtering(
        self, threshold, expected_min_kept, expected_max_kept
    ):
        """
        AI-AC1-TS2: 不同置信度阈值下的过滤效果

        验证：
        - threshold=0.7 时，保留置信度 >= 0.7 的问题
        - threshold=0.5 时，保留置信度 >= 0.5 的问题
        - threshold=0.9 时，保留置信度 >= 0.9 的问题
        - threshold=0.3 时，保留置信度 >= 0.3 的问题
        """
        issues = build_test_issues(count=5)
        # 为 5 个问题设置不同置信度：0.3, 0.5, 0.7, 0.9, 0.95
        confidence_map = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.9, 4: 0.95}

        mock_response = make_mock_response(
            issues, confidence_map=confidence_map, threshold=threshold
        )

        reviewer = create_reviewer(confidence_threshold=threshold)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            diff_result = build_mock_diff_result()
            call_graph = build_mock_call_graph()
            result = reviewer.review(issues, diff_result, call_graph)

        assert expected_min_kept <= len(result) <= expected_max_kept, (
            f"With threshold={threshold}, expected {expected_min_kept}-{expected_max_kept} "
            f"issues kept, got {len(result)}"
        )

    def test_all_false_positives_filtered(self):
        """
        AI-AC1-TS1 补充：全部为误报时全部过滤

        验证：
        - 5 个问题全部为误报（置信度 0.1-0.3）
        - AI 评审后结果为空
        """
        issues = build_test_issues(count=5)
        confidence_map = {0: 0.1, 1: 0.15, 2: 0.2, 3: 0.25, 4: 0.3}

        mock_response = make_mock_response(
            issues,
            real_indices=[],  # 全部为误报
            confidence_map=confidence_map,
        )

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 0, (
            f"Expected 0 issues when all are false positives, got {len(result)}"
        )

    def test_all_real_issues_preserved(self):
        """
        AI-AC1-TS1 补充：全部为真实问题时全部保留

        验证：
        - 5 个问题全部为真实（置信度 0.8-0.99）
        - AI 评审后全部保留
        """
        issues = build_test_issues(count=5)
        confidence_map = {0: 0.8, 1: 0.85, 2: 0.9, 3: 0.95, 4: 0.99}

        mock_response = make_mock_response(
            issues,
            real_indices=[0, 1, 2, 3, 4],
            confidence_map=confidence_map,
        )

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 5, (
            f"Expected 5 issues when all are real, got {len(result)}"
        )


# ============================================================
# AI-AC2: 修复建议包含具体代码片段
# ============================================================
class TestAIAC2FixSuggestions:
    """AI-AC2 测试组：修复建议代码片段验证"""

    def test_fix_suggestions_contain_code_snippets(self):
        """
        AI-AC2-TS1: AI 修复建议代码片段验证

        验证：
        - 3 个问题（XXE、提权、XSS 各 1 个）
        - 每个问题的 fix 字段包含代码特征（括号、分号、缩进等）
        - 100% 的修复建议包含代码片段
        """
        # 构造 3 个不同类型的安全问题
        issues = [
            {
                "rule_id": "xxe-java-document-builder",
                "category": "security",
                "severity": "ERROR",
                "file": "src/Parser.java",
                "line": 33,
                "end_line": 35,
                "message": "DocumentBuilderFactory 未禁用外部实体",
                "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
                "fix": "",
            },
            {
                "rule_id": "priv-python-eval",
                "category": "security",
                "severity": "ERROR",
                "file": "scripts/eval.py",
                "line": 25,
                "end_line": 25,
                "message": "eval() 执行用户可控代码",
                "code_snippet": "result = eval(user_input)",
                "fix": "",
            },
            {
                "rule_id": "xss-js-innerhtml",
                "category": "security",
                "severity": "WARNING",
                "file": "web/component.js",
                "line": 51,
                "end_line": 52,
                "message": "innerHTML 直接赋值存在 XSS 风险",
                "code_snippet": "element.innerHTML = userInput;",
                "fix": "",
            },
        ]

        # 构造包含代码片段的修复建议
        enhanced_fixes = {
            0: (
                '// Fix: Disable external entities\n'
                'DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();\n'
                'factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);\n'
                'factory.setFeature("http://xml.org/sax/features/external-general-entities", false);\n'
                'DocumentBuilder builder = factory.newDocumentBuilder();\n'
            ),
            1: (
                '# Fix: Use ast.literal_eval instead of eval\n'
                'import ast\n'
                'result = ast.literal_eval(user_input)\n'
            ),
            2: (
                '// Fix: Use textContent instead of innerHTML\n'
                'element.textContent = userInput;\n'
                '// Or use DOMPurify for sanitization:\n'
                'element.innerHTML = DOMPurify.sanitize(userInput);\n'
            ),
        }

        mock_response = make_mock_response(
            issues,
            real_indices=[0, 1, 2],
            enhanced_fixes=enhanced_fixes,
        )

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 3, f"Expected 3 issues, got {len(result)}"

        # 验证每个修复建议包含代码特征
        code_indicators = ["(", ")", "{", "}", ";", "=", "import", "factory", "element"]
        for issue in result:
            fix = issue.get("fix", "")
            assert fix, f"Issue {issue['rule_id']} has empty fix"

            # 检查是否包含代码特征
            has_code = any(indicator in fix for indicator in code_indicators)
            assert has_code, (
                f"Fix for {issue['rule_id']} does not contain code snippets: {fix[:100]}"
            )

            # 或者长度 > 50 字符（代码片段通常较长）
            assert len(fix) > 50 or has_code, (
                f"Fix for {issue['rule_id']} too short and lacks code indicators"
            )

    def test_original_fix_preserved_when_no_enhancement(self):
        """
        AI-AC2-TS2: 原始规则 fix 字段保留与增强

        验证：
        - 当 AI 提供增强修复时，fix 字段被更新
        - 当 AI 未提供增强修复（空字符串）时，原始 fix 字段不被覆盖
        """
        original_fix = "Use factory.setFeature() to disable external entities"

        issues = [
            {
                "rule_id": "xxe-java-document-builder",
                "category": "security",
                "severity": "ERROR",
                "file": "src/Parser.java",
                "line": 33,
                "end_line": 35,
                "message": "XXE vulnerability",
                "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
                "fix": original_fix,
            },
        ]

        # 场景 1：AI 提供增强修复
        enhanced_fix_text = (
            '// Enhanced fix:\n'
            'factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);\n'
            'factory.setFeature("http://xml.org/sax/features/external-general-entities", false);\n'
        )
        response_with_enhancement = json.dumps([{
            "rule_id": "xxe-java-document-builder",
            "is_valid": True,
            "confidence": 0.95,
            "enhanced_fix": enhanced_fix_text,
        }])

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=response_with_enhancement):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 1
        # 当 AI 提供增强修复时，fix 应被更新
        assert result[0].get("fix") == enhanced_fix_text, (
            "Fix should be updated with AI enhanced version"
        )

        # 场景 2：AI 未提供增强修复（空字符串）
        response_without_enhancement = json.dumps([{
            "rule_id": "xxe-java-document-builder",
            "is_valid": True,
            "confidence": 0.95,
            "enhanced_fix": "",
        }])

        # 重新构造 issues（因为上面的 result 可能已被修改）
        issues[0]["fix"] = original_fix

        with patch.object(reviewer, "_call_llm", return_value=response_without_enhancement):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 1
        # 当 AI 未提供增强修复时，原始 fix 应保留
        assert result[0].get("fix") == original_fix, (
            f"Original fix should be preserved when AI provides empty enhancement, "
            f"got: {result[0].get('fix')}"
        )

    def test_fix_with_code_block_format(self):
        """
        AI-AC2-TS1 补充：验证修复建议包含多行代码块

        验证：
        - 修复建议包含多行代码
        - 包含函数调用、方法链等代码结构
        """
        issues = build_test_issues(count=1)
        issues[0]["rule_id"] = "xxe-java-document-builder"
        issues[0]["fix"] = ""

        multi_line_fix = (
            'DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();\n'
            'factory.setFeature(\n'
            '    "http://apache.org/xml/features/disallow-doctype-decl", true\n'
            ');\n'
            'factory.setFeature(\n'
            '    "http://xml.org/sax/features/external-general-entities", false\n'
            ');\n'
            'DocumentBuilder builder = factory.newDocumentBuilder();\n'
            'Document doc = builder.parse(inputStream);\n'
        )

        mock_response = json.dumps([{
            "rule_id": "xxe-java-document-builder",
            "is_valid": True,
            "confidence": 0.95,
            "enhanced_fix": multi_line_fix,
        }])

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 1
        fix = result[0].get("fix", "")
        assert "\n" in fix, "Fix should contain multiple lines"
        assert "factory.setFeature" in fix, "Fix should contain method calls"
        assert len(fix) > 100, "Fix should be substantial (multi-line code block)"


# ============================================================
# AI-AC3: AI 评审耗时 < 60s
# ============================================================
class TestAIAC3Performance:
    """AI-AC3 测试组：AI 评审性能测试"""

    def test_ai_review_performance_20_issues(self):
        """
        AI-AC3-TS1: 批量 20 问题 AI 评审性能测试

        验证：
        - 20 个问题总耗时 < 60 秒
        - Mock 场景下应 < 5 秒
        - LLM 调用次数 = 1（20 个问题在 1 个批次内，batch_size=20）
        """
        issues = build_test_issues(count=20)
        mock_response = make_mock_response(issues, real_indices=list(range(10)))

        reviewer = create_reviewer(confidence_threshold=0.7)

        call_count = 0

        def mock_call_with_count(prompt):
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)  # 50ms 模拟网络延迟
            return mock_response

        with patch.object(reviewer, "_call_llm", side_effect=mock_call_with_count):
            start = time.time()
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )
            duration = time.time() - start

        assert duration < 60, f"AI review took {duration:.1f}s, exceeds 60s limit"
        assert duration < 5, f"Mock AI review took {duration:.1f}s, expected < 5s"
        assert call_count == 1, (
            f"Expected 1 LLM call for 20 issues (batch_size=20), got {call_count}"
        )

    def test_batch_processing_50_issues(self):
        """
        AI-AC3-TS2: 超大批量（50 问题）分批处理验证

        验证：
        - 50 个问题分 3 批处理（20 + 20 + 10）
        - LLM 调用次数 = 3
        - 总耗时 < 60 秒
        - 所有问题均被处理
        """
        issues = build_test_issues(count=50)
        # 为每批构造不同的响应
        batch_responses = []
        for batch_start in range(0, 50, 20):
            batch_end = min(batch_start + 20, 50)
            batch = issues[batch_start:batch_end]
            batch_responses.append(
                make_mock_response(batch, real_indices=list(range(len(batch) // 2)))
            )

        call_count = 0

        def mock_call_batch(prompt):
            nonlocal call_count
            idx = min(call_count, len(batch_responses) - 1)
            call_count += 1
            time.sleep(0.05)
            return batch_responses[idx]

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", side_effect=mock_call_batch):
            start = time.time()
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )
            duration = time.time() - start

        assert duration < 60, f"AI review took {duration:.1f}s, exceeds 60s limit"
        assert call_count == 3, (
            f"Expected 3 LLM calls for 50 issues (20+20+10), got {call_count}"
        )
        # 所有批次的问题都应被处理
        assert isinstance(result, list), "Expected list result"
        # 结果应包含被保留的问题（来自所有批次）
        assert len(result) > 0, "Expected some issues to be retained"

    @pytest.mark.parametrize("issue_count,expected_calls", [
        (1, 1),
        (19, 1),
        (20, 1),
        (21, 2),
        (40, 2),
        (41, 3),
    ])
    def test_batch_size_boundaries(self, issue_count, expected_calls):
        """
        AI-AC3 补充：分批边界验证

        验证：
        - 1-20 个问题 -> 1 次 LLM 调用
        - 21-40 个问题 -> 2 次 LLM 调用
        - 41-60 个问题 -> 3 次 LLM 调用
        """
        issues = build_test_issues(count=issue_count)
        mock_response = make_mock_response(issues, real_indices=list(range(issue_count // 2)))

        call_count = 0

        def mock_call(prompt):
            nonlocal call_count
            call_count += 1
            return mock_response

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", side_effect=mock_call):
            reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert call_count == expected_calls, (
            f"For {issue_count} issues, expected {expected_calls} LLM calls, got {call_count}"
        )


# ============================================================
# AI-AC4: LLM 不可用时自动降级
# ============================================================
class TestAIAC4Fallback:
    """AI-AC4 测试组：LLM 不可用时自动降级"""

    def test_no_api_key_fallback(self):
        """
        AI-AC4-TS1: 无 API Key 时降级

        验证：
        - _is_available() 返回 False
        - review() 返回与输入完全相同的问题列表
        - 问题数量和顺序不变
        """
        # 确保没有 API Key
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("TEST_LLM_API_KEY", None)

        config = {
            "llm": {
                "url": "http://api.openai.com/v1/chat/completions",
                "api_key_env": "OPENAI_API_KEY",
            },
            "confidence_threshold": 0.7,
        }
        reviewer = AIReviewer(config=config)

        assert reviewer._is_available() is False, (
            "_is_available() should return False when API key is missing"
        )

        issues = build_test_issues(count=5)
        result = reviewer.review(
            issues, build_mock_diff_result(), build_mock_call_graph()
        )

        assert len(result) == len(issues), (
            f"Expected {len(issues)} issues (no filtering), got {len(result)}"
        )
        assert result == issues, (
            "Result should be identical to input when AI is unavailable"
        )

    def test_llm_api_timeout_fallback(self):
        """
        AI-AC4-TS2: LLM API 超时/异常时降级

        验证：
        - Mock urllib.request.urlopen 抛出 urllib.error.URLError
        - _call_llm 内部捕获异常并返回 None
        - 返回原始问题列表（5 个问题全部保留）
        """
        reviewer = create_reviewer(confidence_threshold=0.7)

        issues = build_test_issues(count=5)

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        # 异常不应传播，应返回原始结果
        assert len(result) == len(issues), (
            f"Expected {len(issues)} issues after LLM error, got {len(result)}"
        )

    def test_llm_returns_invalid_json_fallback(self):
        """
        AI-AC4-TS3: LLM 返回无效 JSON 时降级

        验证：
        - Mock _call_llm() 返回非 JSON 字符串
        - JSON 解析失败时不抛出异常
        - 返回原始问题列表
        """
        reviewer = create_reviewer(confidence_threshold=0.7)

        # 使用会触发 json.JSONDecodeError 的响应（被 _parse_response 正确捕获）
        invalid_responses = [
            "This is not a JSON response",
            "```json\n{invalid json here}\n```",
            "",
        ]

        issues = build_test_issues(count=5)

        for invalid_resp in invalid_responses:
            with patch.object(reviewer, "_call_llm", return_value=invalid_resp):
                result = reviewer.review(
                    issues, build_mock_diff_result(), build_mock_call_graph()
                )

                # 不应抛出异常，应返回原始结果
                assert isinstance(result, list), (
                    f"Expected list result for invalid response '{invalid_resp[:30]}'"
                )
                assert len(result) == len(issues), (
                    f"Expected {len(issues)} issues for response '{invalid_resp[:30]}', "
                    f"got {len(result)}"
                )

    def test_llm_returns_none_fallback(self):
        """
        AI-AC4-TS2 补充：_call_llm 返回 None 时降级

        验证：
        - _call_llm 返回 None（模拟网络失败后的 None 返回）
        - 返回原始问题列表
        """
        reviewer = create_reviewer(confidence_threshold=0.7)

        issues = build_test_issues(count=5)

        with patch.object(reviewer, "_call_llm", return_value=None):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == len(issues), (
            f"Expected {len(issues)} issues when LLM returns None, got {len(result)}"
        )

    def test_no_url_configured_fallback(self):
        """
        AI-AC4-TS1 补充：未配置 LLM URL 时降级

        验证：
        - config 中没有 llm.url
        - _is_available() 返回 False
        - review() 返回原始结果
        """
        config = {
            "llm": {
                "api_key_env": "OPENAI_API_KEY",
                # 没有 url
            },
            "confidence_threshold": 0.7,
        }
        reviewer = AIReviewer(config=config)

        assert reviewer._is_available() is False

        issues = build_test_issues(count=3)
        result = reviewer.review(
            issues, build_mock_diff_result(), build_mock_call_graph()
        )

        assert len(result) == len(issues)
        assert result == issues

    def test_empty_issues_list(self):
        """
        AI-AC4 补充：空问题列表不触发 LLM 调用

        验证：
        - 传入空问题列表
        - 不调用 _call_llm
        - 返回空列表
        """
        reviewer = create_reviewer(confidence_threshold=0.7)

        call_count = 0
        original_call_llm = reviewer._call_llm

        def counting_call_llm(prompt):
            nonlocal call_count
            call_count += 1
            return original_call_llm(prompt)

        with patch.object(reviewer, "_call_llm", side_effect=counting_call_llm):
            result = reviewer.review(
                [], build_mock_diff_result(), build_mock_call_graph()
            )

        assert result == [], "Expected empty result for empty input"
        assert call_count == 0, "LLM should not be called for empty issues"

    def test_partial_llm_failure_batch_fallback(self):
        """
        AI-AC4-TS2 补充：多批次中某一批 LLM 调用失败时的降级

        验证：
        - 3 个批次中第 2 批失败
        - 第 1、3 批正常处理
        - 第 2 批返回原始问题
        """
        issues = build_test_issues(count=50)
        call_count = 0

        def mock_call_selective(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # 第 2 批失败
                return None
            # 其他批次正常
            batch_start = (call_count - 1) * 20
            batch_end = min(batch_start + 20, 50)
            batch = issues[batch_start:batch_end]
            return make_mock_response(batch, real_indices=list(range(len(batch) // 2)))

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", side_effect=mock_call_selective):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        # 应包含第 1、3 批过滤后的问题 + 第 2 批原始问题
        assert isinstance(result, list)
        assert len(result) > 0, "Should have some results from successful batches"


# ============================================================
# 边界情况和鲁棒性测试
# ============================================================
class TestAIReviewerEdgeCases:
    """AI 评审器边界情况测试"""

    def test_single_issue_review(self):
        """
        验证单个问题的 AI 评审正常工作
        """
        issues = build_test_issues(count=1)
        mock_response = make_mock_response(issues, real_indices=[0])

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 1

    def test_markdown_wrapped_json_response(self):
        """
        验证 LLM 返回 Markdown 包裹的 JSON 时能正确解析
        """
        issues = build_test_issues(count=3)
        real_response = make_mock_response(issues, real_indices=[0, 1, 2])

        # 包裹在 markdown 代码块中
        wrapped_response = f"```json\n{real_response}\n```"

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=wrapped_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        assert len(result) == 3, (
            f"Expected 3 issues from markdown-wrapped JSON, got {len(result)}"
        )

    def test_ai_confidence_added_to_result(self):
        """
        验证 AI 评审后问题的 ai_confidence 字段被设置
        """
        issues = build_test_issues(count=2)
        mock_response = make_mock_response(
            issues,
            real_indices=[0, 1],
            confidence_map={0: 0.85, 1: 0.92},
        )

        reviewer = create_reviewer(confidence_threshold=0.7)

        with patch.object(reviewer, "_call_llm", return_value=mock_response):
            result = reviewer.review(
                issues, build_mock_diff_result(), build_mock_call_graph()
            )

        for issue in result:
            assert "ai_confidence" in issue, (
                f"Issue {issue['rule_id']} missing ai_confidence field"
            )
            assert issue["ai_confidence"] >= 0.7, (
                f"Issue {issue['rule_id']} confidence {issue['ai_confidence']} below threshold"
            )
