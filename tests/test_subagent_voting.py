"""子 Agent 多评审员投票聚合测试（Self-Consistency 平移到子 Agent 路径）"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("scanmod", SKILL_ROOT / "scripts" / "scan.py")
scanmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanmod)


def _vote(rule_id, file, line, is_fp, confidence=0.9, needs_review=False):
    return {
        "rule_id": rule_id,
        "file": file,
        "line": line,
        "is_false_positive": is_fp,
        "needs_review": needs_review,
        "ai_confidence": confidence,
        "analysis": "test",
        "enhanced_fix": "fix",
    }


def _report(*issues):
    return {
        "issues": [
            {"rule_id": r, "file": f, "line": l, "severity": "ERROR"}
            for r, f, l in issues
        ],
        "summary": {},
    }


class TestAggregateVotes:
    def test_tp_majority_kept_with_highest_confidence(self):
        votes = [
            [_vote("r", "a.java", 10, False, 0.7)],
            [_vote("r", "a.java", 10, False, 0.95)],
            [_vote("r", "a.java", 10, True, 0.8)],
        ]
        results, dropped, stats = scanmod._aggregate_votes(votes, 3)
        assert len(results) == 1
        assert results[0]["ai_confidence"] == 0.95
        assert results[0]["vote"] == "TP 2/3"
        assert stats["kept_tp"] == 1

    def test_fp_majority_dropped(self):
        votes = [
            [_vote("r", "a.java", 10, True)],
            [_vote("r", "a.java", 10, True)],
            [_vote("r", "a.java", 10, False)],
        ]
        results, dropped, stats = scanmod._aggregate_votes(votes, 3)
        assert len(results) == 0
        assert stats["dropped_fp"] == 1

    def test_tie_kept_conservatively_with_needs_review(self):
        # 2 票 1:1 平票，均未达多数阈值 2 → 保守保留
        votes = [
            [_vote("r", "a.java", 10, True)],
            [_vote("r", "a.java", 10, False)],
        ]
        results, dropped, stats = scanmod._aggregate_votes(votes, 2)
        assert len(results) == 1
        assert results[0]["needs_review"] is True
        assert "NO_MAJORITY" in results[0]["vote"]
        assert stats["kept_review"] == 1

    def test_three_way_split_kept_conservatively(self):
        # TP / FP / needs_review 三向分歧
        votes = [
            [_vote("r", "a.java", 10, False)],
            [_vote("r", "a.java", 10, True)],
            [_vote("r", "a.java", 10, False, needs_review=True)],
        ]
        results, dropped, stats = scanmod._aggregate_votes(votes, 3)
        assert len(results) == 1
        assert results[0]["needs_review"] is True
        assert stats["kept_review"] == 1

    def test_absent_vote_requires_majority_of_total(self):
        # 3 票但仅 1 票覆盖该问题：1 < 2 → 保守保留
        votes = [
            [_vote("r", "a.java", 10, False)],
            [],
            [],
        ]
        results, dropped, stats = scanmod._aggregate_votes(votes, 3)
        assert len(results) == 1
        assert results[0]["needs_review"] is True

    def test_line_type_tolerance(self):
        # 一票写整数 line、一票写字符串 line，应聚合成同一问题
        votes = [
            [_vote("r", "a.java", 10, False)],
            [_vote("r", "a.java", "10", False)],
        ]
        results, dropped, stats = scanmod._aggregate_votes(votes, 2)
        assert len(results) == 1
        assert stats["kept_tp"] == 1


class TestMergeWithVotes:
    def test_vote_files_aggregated_into_report(self, tmp_path):
        (tmp_path / "ai-review-result-vote1.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, False, 0.9), _vote("r2", "b.java", 2, True)]),
            encoding="utf-8",
        )
        (tmp_path / "ai-review-result-vote2.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, False, 0.8), _vote("r2", "b.java", 2, False)]),
            encoding="utf-8",
        )
        (tmp_path / "ai-review-result-vote3.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, True), _vote("r2", "b.java", 2, True)]),
            encoding="utf-8",
        )

        report = _report(("r1", "a.java", 1), ("r2", "b.java", 2))
        merged = scanmod._merge_subagent_review(report, tmp_path)

        # r1: TP 2/3 保留；r2: FP 2/3 滤除
        assert len(merged["issues"]) == 1
        assert merged["issues"][0]["rule_id"] == "r1"
        assert merged["issues"][0]["vote"] == "TP 2/3"
        assert merged["issues"][0]["ai_confidence"] == 0.9

    def test_needs_review_item_not_filtered(self, tmp_path):
        # 平票保守保留项：needs_review=true，不滤除
        (tmp_path / "ai-review-result-vote1.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, True)]), encoding="utf-8"
        )
        (tmp_path / "ai-review-result-vote2.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, False)]), encoding="utf-8"
        )

        report = _report(("r1", "a.java", 1))
        merged = scanmod._merge_subagent_review(report, tmp_path)
        assert len(merged["issues"]) == 1
        assert merged["issues"][0]["needs_review"] is True

    def test_single_reviewer_mode_unchanged(self, tmp_path):
        # 旧路径：单 ai-review-result.json 行为不变
        (tmp_path / "ai-review-result.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, True)]), encoding="utf-8"
        )
        report = _report(("r1", "a.java", 1))
        merged = scanmod._merge_subagent_review(report, tmp_path)
        assert len(merged["issues"]) == 0

    def test_corrupt_vote_file_skipped(self, tmp_path):
        (tmp_path / "ai-review-result-vote1.json").write_text("{invalid", encoding="utf-8")
        (tmp_path / "ai-review-result-vote2.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, True)]), encoding="utf-8"
        )
        (tmp_path / "ai-review-result-vote3.json").write_text(
            json.dumps([_vote("r1", "a.java", 1, True)]), encoding="utf-8"
        )
        report = _report(("r1", "a.java", 1))
        merged = scanmod._merge_subagent_review(report, tmp_path)
        # 坏票跳过，剩 2 票 FP 一致 → 滤除
        assert len(merged["issues"]) == 0


class TestTaskFileVotingSection:
    def test_task_file_contains_voting_instructions(self, tmp_path):
        from ai_reviewer import AIReviewer

        reviewer = AIReviewer({"voting": {"votes": 3}})
        out = tmp_path / "task.md"
        reviewer.generate_subagent_task(
            issues=[{"rule_id": "r", "file": "a.java", "line": 1, "severity": "ERROR", "message": "m"}],
            scan_info={},
            output_path=str(out),
        )
        content = out.read_text(encoding="utf-8")
        assert "投票委派要求" in content
        assert "3 评审员投票模式" in content
        assert "ai-review-result-vote1.json" in content
        assert "ai-review-result-vote3.json" in content

    def test_task_file_no_voting_section_by_default(self, tmp_path):
        from ai_reviewer import AIReviewer

        reviewer = AIReviewer({})
        out = tmp_path / "task.md"
        reviewer.generate_subagent_task(
            issues=[{"rule_id": "r", "file": "a.java", "line": 1, "severity": "ERROR", "message": "m"}],
            scan_info={},
            output_path=str(out),
        )
        assert "投票委派要求" not in out.read_text(encoding="utf-8")
