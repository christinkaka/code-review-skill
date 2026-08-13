#!/usr/bin/env python3
"""
二审结果合并器
读取 subagent 评审结果，校验、合并到主报告中
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("code-review.review-merger")


class ReviewMerger:
    """二审结果合并器"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        # 兼容两种目录结构：
        # 1. output_dir/report/report.json (scan.py 实际生成的位置)
        # 2. output_dir/report.json (扁平结构)
        if (self.output_dir / "report" / "report.json").exists():
            self.report_json = self.output_dir / "report" / "report.json"
        else:
            self.report_json = self.output_dir / "report.json"

    def read_review_results(self) -> List[Dict]:
        """
        读取 subagent 评审结果

        Returns:
            二审结果列表
        """
        review_file = self.output_dir / "review-results.json"
        if not review_file.exists():
            logger.warning(f"二审结果文件不存在: {review_file}")
            return []

        try:
            with open(review_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return data.get("results", [])
        except json.JSONDecodeError as e:
            logger.error(f"二审结果 JSON 解析失败: {e}")
            return []

    def validate_review_result(self, result: Dict) -> bool:
        """
        校验二审结果格式

        Returns:
            True 如果格式正确
        """
        required_fields = ["issue_id"]
        for field in required_fields:
            if field not in result:
                logger.warning(f"二审结果缺少必填字段: {field}")
                return False

        # ai_confidence 范围校验
        conf = result.get("ai_confidence")
        if conf is not None:
            try:
                conf = float(conf)
                if not (0.0 <= conf <= 1.0):
                    logger.warning(f"ai_confidence 超出范围 [0, 1]: {conf}")
                    return False
            except (TypeError, ValueError):
                logger.warning(f"ai_confidence 类型错误: {conf}")
                return False

        return True

    def merge_into_report(self) -> Tuple[int, int, int]:
        """
        将二审结果合并到主报告

        Returns:
            (已合并数, 验证失败数, 报告不存在)
        """
        if not self.report_json.exists():
            return (0, 0, 1)

        # 读取主报告
        with open(self.report_json, "r", encoding="utf-8") as f:
            report = json.load(f)

        issues = report.get("issues", [])
        if not issues:
            logger.warning("主报告无 issues 字段")
            return (0, 0, 0)

        # 读取二审结果
        review_results = self.read_review_results()
        if not review_results:
            logger.info("无二审结果，跳过合并")
            return (0, 0, 0)

        # 建立 issue_id -> review 映射
        review_map = {}
        valid_count = 0
        invalid_count = 0
        for result in review_results:
            if not self.validate_review_result(result):
                invalid_count += 1
                continue
            issue_id = result["issue_id"]
            review_map[issue_id] = result
            valid_count += 1

        # 合并到 issues
        # 如果 issue 没有 issue_id 字段，使用 file:line:rule_id 作为唯一标识
        merged_count = 0
        for issue in issues:
            issue_id = issue.get("issue_id")
            if not issue_id:
                # 使用 file:line:rule_id 作为 fallback
                issue_id = f"{issue.get('file', '')}:{issue.get('line', 0)}:{issue.get('rule_id', '')}"
                issue["issue_id"] = issue_id
            review = review_map.get(issue_id)
            if not review:
                continue

            # 合并字段
            issue["is_false_positive"] = review.get("is_false_positive", False)
            issue["ai_confidence"] = review.get("ai_confidence")
            issue["analysis"] = review.get("analysis", issue.get("analysis", ""))
            issue["enhanced_fix"] = review.get("enhanced_fix", "")
            issue["references"] = review.get("references", [])
            issue["needs_review"] = review.get("needs_review", False)
            issue["ai_reviewed"] = True
            issue["ai_reviewed_at"] = review.get("reviewed_at", "")

            # 根据 is_false_positive 决定 ai_action
            if issue["is_false_positive"]:
                issue["ai_action"] = "drop"
            elif issue["needs_review"]:
                issue["ai_action"] = "needs_review"
            else:
                issue["ai_action"] = "keep"

            merged_count += 1

        # 写回主报告
        report["issues"] = issues
        report["merge_info"] = {
            "total_review_results": len(review_results),
            "valid_review_results": valid_count,
            "invalid_review_results": invalid_count,
            "merged_count": merged_count,
        }

        with open(self.report_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"二审合并完成: 合并 {merged_count}, 验证失败 {invalid_count}")
        return (merged_count, invalid_count, 0)


def merge_review_results(output_dir: str) -> Tuple[int, int, int]:
    """
    便捷函数：合并二审结果到主报告

    Returns:
        (merged_count, invalid_count, no_report)
    """
    merger = ReviewMerger(output_dir)
    return merger.merge_into_report()
