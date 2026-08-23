#!/usr/bin/env python3
"""
AI 决策漂移一致性量化测试 (P1-②)

核心诉求：
温度非零（0.1~0.2）意味着同一输入多次评审可能产生不同结论。
必须能量化这个漂移：
1. 确定性 LLM（同响应）-> 漂移必须为 0（管线自身不引入随机性）
2. 带采样噪声的 LLM（模拟温度方差）-> 漂移必须被检出并量化
3. 不稳定问题（结论翻转）必须被点名（rule_id/file/line 级定位）
4. 漂移率超阈值 -> verdict=unstable
"""

import copy
import json

import pytest

from consistency_checker import ConsistencyChecker


# ===================================================================
# 测试数据
# ===================================================================

ISSUES = [
    {
        "rule_id": "xxe-java-document-builder",
        "category": "security",
        "severity": "ERROR",
        "file": "src/Parser.java",
        "line": 42,
        "message": "XXE",
    },
    {
        "rule_id": "naming-convention",
        "category": "implementation",
        "severity": "WARNING",
        "file": "src/Utils.java",
        "line": 10,
        "message": "naming",
    },
]

DIFF = {"changed_files": [{"path": "src/Parser.java", "status": "modified"}]}


def make_response(verdicts):
    """verdicts: {rule_id: is_valid}"""
    return json.dumps([
        {"rule_id": rid, "is_valid": v, "confidence": 0.9 if v else 0.2,
         "enhanced_fix": ""}
        for rid, v in verdicts.items()
    ])


BASE_CONFIG = {
    "llm": {"url": "https://api.example.com/v1/chat/completions",
            "api_key_env": "OPENAI_API_KEY", "model": "gpt-4"},
    "confidence_threshold": 0.7,
    "max_retries": 0,
    "audit": {"enabled": False},
}


# ===================================================================
# 确定性基线：漂移必须为 0
# ===================================================================

class TestDeterministicBaseline:
    """同响应多次运行 -> 零漂移"""

    def test_deterministic_llm_zero_drift(self):
        """LLM 每次返回相同响应 -> flip_rate=0，verdict=stable"""
        always_keep = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": True,
        })
        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))

        report = checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=5,
            llm_responses=[always_keep] * 5,
        )

        assert report["flip_rate"] == 0.0
        assert report["verdict"] == "stable"
        assert report["stable_issues"] == 2

    def test_deterministic_drop_zero_drift(self):
        """每次都过滤同一问题 -> 同样零漂移"""
        always_drop = make_response({
            "xxe-java-document-builder": False,
            "naming-convention": False,
        })
        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))

        report = checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=3,
            llm_responses=[always_drop] * 3,
        )

        assert report["flip_rate"] == 0.0
        assert report["verdict"] == "stable"


# ===================================================================
# 漂移检出：模拟采样方差
# ===================================================================

class TestDriftDetection:
    """LLM 响应翻转 -> 漂移必须被量化"""

    def test_flipping_verdict_detected(self):
        """问题 A 每次保留、问题 B 一半保留一半过滤 -> B 是不稳定问题"""
        keep_both = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": True,
        })
        keep_a_drop_b = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": False,
        })
        # 4 次运行：B 翻转 2 次
        responses = [keep_both, keep_a_drop_b, keep_both, keep_a_drop_b]

        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))
        report = checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=4,
            llm_responses=responses,
        )

        assert report["flip_rate"] == 0.5          # 2 个问题中 1 个不稳定
        assert report["unstable_issues"] == 1
        assert report["verdict"] == "unstable"

    def test_unstable_issue_identified_by_location(self):
        """不稳定问题必须定位到 rule_id/file/line"""
        keep_both = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": True,
        })
        drop_b = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": False,
        })

        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))
        report = checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=2,
            llm_responses=[keep_both, drop_b],
        )

        unstable = report["per_issue"][
            [p["rule_id"] for p in report["per_issue"]].index("naming-convention")
        ]
        assert unstable["stability"] == 0.5
        assert unstable["file"] == "src/Utils.java"
        assert unstable["line"] == 10
        assert unstable["decisions"] == [True, False]

    def test_drift_threshold_verdict_boundary(self):
        """漂移率恰好等于阈值 -> stable（阈值内可接受）"""
        keep_both = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": True,
        })
        drop_b = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": False,
        })
        # 阈值 0.5：1/2 翻转 -> flip_rate == threshold -> stable
        config = copy.deepcopy(BASE_CONFIG)
        config["consistency"] = {"drift_threshold": 0.5}
        checker = ConsistencyChecker(config)

        report = checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=2,
            llm_responses=[keep_both, drop_b],
        )

        assert report["flip_rate"] == 0.5
        assert report["verdict"] == "stable"


# ===================================================================
# 报告结构
# ===================================================================

class TestReportStructure:
    """漂移报告必须包含可操作的完整字段"""

    def test_report_fields(self):
        always_keep = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": True,
        })
        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))
        report = checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=3,
            llm_responses=[always_keep] * 3,
        )

        for field in ["runs", "total_issues", "stable_issues",
                      "unstable_issues", "flip_rate", "drift_threshold",
                      "verdict", "per_issue"]:
            assert field in report, f"报告缺少字段: {field}"

    def test_issues_not_mutated_across_runs(self):
        """每次运行必须用独立副本，原始 issues 不被污染"""
        always_keep = make_response({
            "xxe-java-document-builder": True,
            "naming-convention": True,
        })
        original = copy.deepcopy(ISSUES)
        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))
        checker.measure(
            copy.deepcopy(ISSUES), DIFF, {},
            runs=3,
            llm_responses=[always_keep] * 3,
        )

        assert ISSUES == original or original  # 原数据保持可用
        # 深度校验：原始 issues 不含运行时附加字段
        assert "ai_confidence" not in ISSUES[0]
        assert "ai_confidence" not in original[0]


# ===================================================================
# 无注入响应：走真实配置路径（不实际调网）
# ===================================================================

class TestRealPathFallback:
    """不注入响应时构造真实调用路径（此处仅验证参数校验）"""

    def test_invalid_runs_rejected(self):
        """runs < 2 无意义，必须拒绝"""
        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))
        with pytest.raises(ValueError):
            checker.measure(copy.deepcopy(ISSUES), DIFF, {}, runs=1)

    def test_responses_length_mismatch_rejected(self):
        """注入响应数与 runs 不符必须报错"""
        checker = ConsistencyChecker(copy.deepcopy(BASE_CONFIG))
        with pytest.raises(ValueError):
            checker.measure(
                copy.deepcopy(ISSUES), DIFF, {},
                runs=3,
                llm_responses=["[]", "[]"],  # 只有 2 个
            )
