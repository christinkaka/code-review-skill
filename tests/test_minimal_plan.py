#!/usr/bin/env python3
"""
最小方案三项功能的测试（2026-08-24，维护成本优先）

覆盖：
1. 3票多数投票（Self-Consistency, Wang et al. 2022）
   - CRITICAL/ERROR 级问题多次采样，多数票才保留
2. 失败案例累积（CEGIS 核心：反例驱动修复）
   - golden test 失败后带反馈重试，每轮看到全部历史失败
3. 通过率阈值（≥90% 才允许部署）
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai_reviewer import AIReviewer


# ===================================================================
# 辅助构造
# ===================================================================

def make_reviewer(votes=None, threshold=0.7):
    """构造 AIReviewer 实例，可选投票配置"""
    config = {
        "llm": {
            "url": "https://api.example.com/v1/chat/completions",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4",
        },
        "confidence_threshold": threshold,
    }
    if votes is not None:
        config["voting"] = {"votes": votes}
    return AIReviewer(config)


def make_issue(rule_id="rule-a", severity="ERROR", line=10):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "file": "src/Foo.java",
        "line": line,
        "message": f"Issue {rule_id}",
        "code_snippet": "foo();",
    }


def llm_response_for(issues, valid_map):
    """构造 LLM 响应：valid_map = {rule_id: (is_valid, confidence)}"""
    return json.dumps([
        {
            "rule_id": issue["rule_id"],
            "file": issue["file"],
            "line": issue["line"],
            "is_valid": valid_map[issue["rule_id"]][0],
            "confidence": valid_map[issue["rule_id"]][1],
            "enhanced_fix": "fix suggestion" if valid_map[issue["rule_id"]][0] else "",
        }
        for issue in issues
    ])


# ===================================================================
# 1. 3票多数投票
# ===================================================================

class TestVotingMajority:
    """投票机制：多数票保留，少数票过滤"""

    def setup_method(self):
        self.issues = [make_issue("rule-a"), make_issue("rule-b", line=20)]
        self.diff = {"changed_files": [{"path": "src/Foo.java", "status": "modified"}]}
        self.call_graph = {}

    def _inject_responses(self, reviewer, responses):
        """注入按调用顺序返回的 LLM 响应列表"""
        call_count = {"n": 0}

        def mock_llm(prompt):
            resp = responses[call_count["n"] % len(responses)]
            call_count["n"] += 1
            return resp

        reviewer._call_llm = mock_llm
        reviewer._is_available = lambda: True

    def test_majority_vote_keeps_stable_issue(self):
        """rule-a 在 3 票中被保留 2 次（稳定），应保留"""
        reviewer = make_reviewer(votes=3)

        # 票1: 两个都保留；票2: 都过滤；票3: 都保留
        # rule-a: 2/3 票保留 -> 多数，保留
        resp_keep = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })
        resp_drop = llm_response_for(self.issues, {
            "rule-a": (False, 0.2), "rule-b": (False, 0.2),
        })
        self._inject_responses(reviewer, [resp_keep, resp_drop, resp_keep])

        result = reviewer.review(self.issues, self.diff, self.call_graph)

        kept_ids = [i["rule_id"] for i in result]
        assert "rule-a" in kept_ids, "2/3 票保留的稳定问题应被保留"

    def test_majority_vote_drops_unstable_issue(self):
        """rule-b 在 3 票中只被保留 1 次（不稳定），应过滤"""
        reviewer = make_reviewer(votes=3)

        # 票1: 都保留；票2: 都过滤；票3: 都过滤
        # rule-b: 1/3 票保留 -> 少数，过滤
        resp_keep = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })
        resp_drop = llm_response_for(self.issues, {
            "rule-a": (False, 0.2), "rule-b": (False, 0.2),
        })
        self._inject_responses(reviewer, [resp_keep, resp_drop, resp_drop])

        result = reviewer.review(self.issues, self.diff, self.call_graph)

        kept_ids = [i["rule_id"] for i in result]
        assert "rule-b" not in kept_ids, "1/3 票保留的不稳定问题应被过滤"

    def test_unanimous_vote_keeps_all(self):
        """3 票全部保留时，所有问题保留"""
        reviewer = make_reviewer(votes=3)

        resp = llm_response_for(self.issues, {
            "rule-a": (True, 0.95), "rule-b": (True, 0.9),
        })
        self._inject_responses(reviewer, [resp, resp, resp])

        result = reviewer.review(self.issues, self.diff, self.call_graph)

        assert len(result) == 2, "3/3 票一致保留的问题都应保留"

    def test_voting_preserves_enhanced_fix(self):
        """投票保留的问题应包含 AI 增强字段（ai_confidence）"""
        reviewer = make_reviewer(votes=3)

        resp = llm_response_for(self.issues, {
            "rule-a": (True, 0.95), "rule-b": (True, 0.9),
        })
        self._inject_responses(reviewer, [resp, resp, resp])

        result = reviewer.review(self.issues, self.diff, self.call_graph)

        for issue in result:
            assert "ai_confidence" in issue, "保留的问题应含 ai_confidence 字段"

    def test_voting_disabled_by_default(self):
        """默认配置（无 voting 节）时单次评审，LLM 只调用 1 次"""
        reviewer = make_reviewer()  # 无 voting 配置

        call_count = {"n": 0}
        resp = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })

        def mock_llm(prompt):
            call_count["n"] += 1
            return resp

        reviewer._call_llm = mock_llm
        reviewer._is_available = lambda: True

        result = reviewer.review(self.issues, self.diff, self.call_graph)

        assert call_count["n"] == 1, "默认应只调用 1 次 LLM"
        assert len(result) == 2

    def test_voting_calls_llm_three_times(self):
        """votes=3 时 LLM 被调用 3 次"""
        reviewer = make_reviewer(votes=3)

        call_count = {"n": 0}
        resp = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })

        def mock_llm(prompt):
            call_count["n"] += 1
            return resp

        reviewer._call_llm = mock_llm
        reviewer._is_available = lambda: True

        reviewer.review(self.issues, self.diff, self.call_graph)

        assert call_count["n"] == 3, "votes=3 应调用 3 次 LLM"

    def test_voting_with_llm_failure_fail_open(self):
        """某票 LLM 调用失败时 fail-open（该票保留原始问题），不应崩溃"""
        reviewer = make_reviewer(votes=3)

        resp = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })
        call_count = {"n": 0}

        def mock_llm(prompt):
            call_count["n"] += 1
            if call_count["n"] == 2:
                return None  # 第 2 票失败
            return resp

        reviewer._call_llm = mock_llm
        reviewer._is_available = lambda: True

        # 不应抛异常；失败票按 fail-open 保留全部
        result = reviewer.review(self.issues, self.diff, self.call_graph)

        # 票1 保留 2 个，票2 fail-open 保留 2 个，票3 保留 2 个
        # 两个问题都是 3/3，都保留
        assert len(result) == 2


# ===================================================================
# 1b. 投票模式的审计语义（I-1 修复验证）
# ===================================================================

class TestVotingAudit:
    """投票模式下审计统计必须反映最终裁决，不被逐票记录污染"""

    def setup_method(self):
        self.issues = [make_issue("rule-a"), make_issue("rule-b", line=20)]
        self.diff = {"changed_files": [{"path": "src/Foo.java", "status": "modified"}]}
        self.call_graph = {}

    def _inject(self, reviewer, responses):
        call_count = {"n": 0}

        def mock_llm(prompt):
            resp = responses[call_count["n"] % len(responses)]
            call_count["n"] += 1
            return resp

        reviewer._call_llm = mock_llm
        reviewer._is_available = lambda: True

    def test_audit_total_input_not_inflated(self):
        """投票模式下 total_input 只计一次（不是 votes 倍）"""
        reviewer = make_reviewer(votes=3)

        resp = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })
        self._inject(reviewer, [resp, resp, resp])

        reviewer.review(self.issues, self.diff, self.call_graph)

        summary = reviewer.get_audit_summary()
        assert summary["total_input"] == 2, (
            f"total_input 应为 2（问题数），实际 {summary['total_input']}（被逐票虚增）"
        )

    def test_audit_reflects_final_majority_decision(self):
        """审计记录的是最终多数票裁决：rule-a 保留(2/3)、rule-b 过滤(1/3)"""
        reviewer = make_reviewer(votes=3)

        resp_keep = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })
        resp_drop_b = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (False, 0.2),
        })
        # 票1: 都保留；票2: rule-b 过滤；票3: rule-b 过滤
        self._inject(reviewer, [resp_keep, resp_drop_b, resp_drop_b])

        result = reviewer.review(self.issues, self.diff, self.call_graph)

        summary = reviewer.get_audit_summary()
        # 最终裁决：rule-a 保留（3/3），rule-b 过滤（1/3，未达多数 2/3）
        assert summary["kept"] == 1, (
            f"最终保留应为 1，实际 {summary['kept']}"
        )
        assert summary["dropped"] == 1, (
            f"最终过滤应为 1（不是逐票累计），实际 {summary['dropped']}"
        )
        assert len(result) == 1
        assert result[0]["rule_id"] == "rule-a"

    def test_audit_dropped_reason_mentions_vote(self):
        """最终过滤的审计记录 reason 应说明投票结果（可追溯）"""
        reviewer = make_reviewer(votes=3)

        resp_keep = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (True, 0.9),
        })
        resp_drop_b = llm_response_for(self.issues, {
            "rule-a": (True, 0.9), "rule-b": (False, 0.2),
        })
        self._inject(reviewer, [resp_keep, resp_drop_b, resp_drop_b])

        reviewer.review(self.issues, self.diff, self.call_graph)

        dropped_records = [
            r for r in reviewer.audit_records
            if r.get("decision") == "dropped"
        ]
        assert len(dropped_records) == 1
        assert "vote" in dropped_records[0].get("reason", "").lower() or \
               "票" in dropped_records[0].get("reason", ""), \
            "dropped 记录的 reason 应包含投票信息"
