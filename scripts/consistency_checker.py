#!/usr/bin/env python3
"""
AI 决策漂移一致性量化器 (P1-②)

背景：
AI 复核层的采样温度非零（0.1~0.2），同一输入多次评审可能产生不同结论，
被过滤/保留的问题存在翻转风险。本模块通过多次运行量化漂移：

1. 确定性基线：LLM 响应恒定时，漂移必须为 0（管线自身不引入随机性）
2. 漂移检出：模拟采样方差（注入不同响应），量化每个问题的结论稳定性
3. 可操作输出：不稳定问题定位到 rule_id/file/line，漂移率对比阈值给出结论

用法：
    # 测试环境：注入每轮的 LLM 响应
    checker = ConsistencyChecker(config)
    report = checker.measure(issues, diff, call_graph, runs=5,
                             llm_responses=[resp1, resp2, ...])

    # 真实环境：不注入响应，走配置的真实 LLM（每轮真实采样）
    report = checker.measure(issues, diff, call_graph, runs=5)
"""

import copy
import logging
from typing import Dict, List, Optional

from ai_reviewer import AIReviewer

logger = logging.getLogger("code-review.consistency")


class ConsistencyChecker:
    """AI 决策漂移量化器"""

    def __init__(self, config: Dict):
        """
        Args:
            config: AIReviewer 同款配置，额外支持:
                consistency.drift_threshold: 漂移率阈值（默认 0.1，
                    超过即 verdict=unstable）
        """
        self.config = config
        consistency_cfg = config.get("consistency", {})
        self.drift_threshold = consistency_cfg.get("drift_threshold", 0.1)

    def measure(
        self,
        issues: List[Dict],
        diff_result: Dict,
        call_graph: Dict,
        runs: int = 5,
        llm_responses: Optional[List[str]] = None,
    ) -> Dict:
        """
        多次运行评审并量化决策漂移。

        Args:
            issues: 待评审问题列表（内部深拷贝，不污染入参）
            diff_result: 差异分析结果
            call_graph: 调用图
            runs: 运行次数（>= 2 才有意义）
            llm_responses: 每轮注入的 LLM 响应（长度必须等于 runs）；
                           None 时走真实 LLM 配置

        Returns:
            漂移报告：
            {
              "runs", "total_issues", "stable_issues", "unstable_issues",
              "flip_rate", "drift_threshold", "verdict",
              "per_issue": [{rule_id, file, line, stability, decisions}]
            }
        """
        if runs < 2:
            raise ValueError(f"runs 必须 >= 2（当前 {runs}），单次运行无法度量漂移")
        if llm_responses is not None and len(llm_responses) != runs:
            raise ValueError(
                f"llm_responses 数量（{len(llm_responses)}）必须等于 runs（{runs}）"
            )

        # 以 (rule_id, file, line) 为问题身份，收集每轮的保留决策
        issue_keys = [
            (i.get("rule_id"), i.get("file"), i.get("line")) for i in issues
        ]
        decisions_by_key: Dict[tuple, List[bool]] = {
            key: [] for key in issue_keys
        }

        for run_index in range(runs):
            reviewer = AIReviewer(copy.deepcopy(self.config))

            # 注入本轮 LLM 响应（模拟该轮采样），并强制评审器视为可用
            if llm_responses is not None:
                response = llm_responses[run_index]
                reviewer._call_llm = lambda prompt, _r=response: _r
                reviewer._is_available = lambda: True

            result = reviewer.review(
                copy.deepcopy(issues), diff_result, call_graph
            )
            kept_keys = {
                (i.get("rule_id"), i.get("file"), i.get("line")) for i in result
            }

            for key in issue_keys:
                decisions_by_key[key].append(key in kept_keys)

        # 汇总每个问题的稳定性
        per_issue = []
        unstable_count = 0
        for key, decisions in decisions_by_key.items():
            stability = sum(decisions) / len(decisions)
            if 0.0 < stability < 1.0:
                unstable_count += 1
            per_issue.append({
                "rule_id": key[0],
                "file": key[1],
                "line": key[2],
                "stability": stability,
                "decisions": decisions,
            })

        total = len(issue_keys)
        flip_rate = (unstable_count / total) if total else 0.0
        verdict = "stable" if flip_rate <= self.drift_threshold else "unstable"

        report = {
            "runs": runs,
            "total_issues": total,
            "stable_issues": total - unstable_count,
            "unstable_issues": unstable_count,
            "flip_rate": flip_rate,
            "drift_threshold": self.drift_threshold,
            "verdict": verdict,
            "per_issue": per_issue,
        }

        if verdict == "unstable":
            unstable_list = [
                f"{p['rule_id']}@{p['file']}:{p['line']}(稳定性 {p['stability']:.0%})"
                for p in per_issue if 0.0 < p["stability"] < 1.0
            ]
            logger.warning(
                f"检测到决策漂移：flip_rate={flip_rate:.0%} > "
                f"阈值 {self.drift_threshold:.0%}，不稳定问题: {unstable_list}"
            )

        return report
