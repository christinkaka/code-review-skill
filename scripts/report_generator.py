#!/usr/bin/env python3
"""
报告生成器
生成 JSON 和 Markdown 格式的评审报告。
"""

import json
import logging
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("code-review.report")


class ReportGenerator:
    """评审报告生成器"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        scan_info: Dict,
        issues: List[Dict],
        diff_summary: Dict,
        call_graph_summary: Dict,
    ) -> Dict:
        """
        生成完整评审报告

        Returns:
            完整的报告字典
        """
        # 计算统计摘要
        summary = self._compute_summary(issues)

        # 构建完整报告
        report = {
            "scan_info": scan_info,
            "summary": summary,
            "diff_summary": {
                "files_changed": diff_summary.get("stats", {}).get("files_changed", 0),
                "insertions": diff_summary.get("stats", {}).get("insertions", 0),
                "deletions": diff_summary.get("stats", {}).get("deletions", 0),
            },
            "call_graph_summary": call_graph_summary,
            "issues": issues,
        }

        # 输出 JSON 报告
        json_path = self.output_dir / "report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 报告已生成: {json_path}")

        # 输出摘要 JSON
        summary_path = self.output_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"摘要报告已生成: {summary_path}")

        # 输出 Markdown 报告
        md_path = self.output_dir / "report.md"
        md_content = self._generate_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"Markdown 报告已生成: {md_path}")

        return report

    def _compute_summary(self, issues: List[Dict]) -> Dict:
        """计算统计摘要"""
        severity_map = {"ERROR": "critical", "WARNING": "medium", "INFO": "low"}

        summary = {
            "total": len(issues),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "by_category": {},
            "by_file": {},
            "by_rule": {},
        }

        category_counter = Counter()
        file_counter = Counter()
        rule_counter = Counter()

        for issue in issues:
            severity = issue.get("severity", "WARNING").upper()
            mapped = severity_map.get(severity, "medium")

            # 安全类问题提升一级
            if issue.get("category") == "security" and mapped == "medium":
                mapped = "high"

            summary[mapped] = summary.get(mapped, 0) + 1
            category_counter[issue.get("category", "unknown")] += 1
            file_counter[issue.get("file", "unknown")] += 1
            rule_counter[issue.get("rule_id", "unknown")] += 1

        summary["by_category"] = dict(category_counter.most_common())
        summary["by_file"] = dict(file_counter.most_common(20))
        summary["by_rule"] = dict(rule_counter.most_common(20))

        return summary

    def _generate_markdown(self, report: Dict) -> str:
        """生成 Markdown 格式报告"""
        lines = []
        scan = report["scan_info"]
        summary = report["summary"]
        issues = report["issues"]

        # 标题
        lines.append("# 代码评审报告")
        lines.append("")
        lines.append(f"**生成时间**: {scan.get('timestamp', 'N/A')}")
        lines.append(f"**扫描耗时**: {scan.get('duration_seconds', 'N/A')}s")
        lines.append("")

        # 扫描信息
        lines.append("## 扫描信息")
        lines.append("")
        lines.append(f"| 项目 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 仓库 | `{scan.get('repo', 'N/A')}` |")
        lines.append(f"| 基线分支 | `{scan.get('base_branch', 'N/A')}` |")
        lines.append(f"| 目标分支 | `{scan.get('target_branch', 'N/A')}` |")
        lines.append(f"| 规约 Profile | `{scan.get('profile', 'N/A')}` |")
        lines.append("")

        # 差异统计
        diff = report.get("diff_summary", {})
        lines.append("## 变更统计")
        lines.append("")
        lines.append(f"- 变更文件数: **{diff.get('files_changed', 0)}**")
        lines.append(f"- 新增行数: **{diff.get('insertions', 0)}**")
        lines.append(f"- 删除行数: **{diff.get('deletions', 0)}**")
        lines.append("")

        # 调用图
        cg = report.get("call_graph_summary", {})
        if cg.get("node_count", 0) > 0:
            lines.append("## 调用图分析")
            lines.append("")
            lines.append(f"- 调用图节点: **{cg.get('node_count', 0)}**")
            lines.append(f"- 调用边: **{cg.get('edge_count', 0)}**")
            lines.append(f"- 受影响方法: **{len(cg.get('affected_methods', []))}**")
            lines.append("")

        # 问题摘要
        lines.append("## 问题摘要")
        lines.append("")
        lines.append(f"| 严重等级 | 数量 |")
        lines.append(f"|----------|------|")
        lines.append(f"| CRITICAL | {summary.get('critical', 0)} |")
        lines.append(f"| HIGH | {summary.get('high', 0)} |")
        lines.append(f"| MEDIUM | {summary.get('medium', 0)} |")
        lines.append(f"| LOW | {summary.get('low', 0)} |")
        lines.append(f"| **总计** | **{summary.get('total', 0)}** |")
        lines.append("")

        # 按类别分布
        if summary.get("by_category"):
            lines.append("### 按类别分布")
            lines.append("")
            lines.append("| 类别 | 数量 |")
            lines.append("|------|------|")
            for cat, count in summary["by_category"].items():
                lines.append(f"| {cat} | {count} |")
            lines.append("")

        # 详细问题列表
        lines.append("## 详细问题列表")
        lines.append("")

        # 按严重等级排序
        severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        sorted_issues = sorted(
            issues,
            key=lambda x: (severity_order.get(x.get("severity", "WARNING"), 1), x.get("file", "")),
        )

        for i, issue in enumerate(sorted_issues, 1):
            severity_icon = {
                "ERROR": "🔴",
                "WARNING": "🟡",
                "INFO": "🔵",
            }.get(issue.get("severity", "WARNING"), "⚪")

            lines.append(f"### {i}. {severity_icon} [{issue.get('rule_id', 'N/A')}]")
            lines.append("")
            lines.append(f"- **文件**: `{issue.get('file', 'N/A')}`")
            lines.append(f"- **行号**: {issue.get('line', 'N/A')}")
            lines.append(f"- **严重等级**: {issue.get('severity', 'N/A')}")
            lines.append(f"- **类别**: {issue.get('category', 'N/A')}")
            lines.append(f"- **描述**: {issue.get('message', 'N/A')}")

            if issue.get("code_snippet"):
                lines.append(f"- **代码片段**:")
                lines.append(f"  ```")
                lines.append(f"  {issue['code_snippet'].strip()}")
                lines.append(f"  ```")

            if issue.get("fix"):
                lines.append(f"- **修复建议**: {issue['fix']}")

            if issue.get("call_chain"):
                chain_str = " → ".join(issue["call_chain"])
                lines.append(f"- **调用链**: {chain_str}")

            metadata = issue.get("metadata", {})
            if metadata:
                cwe = metadata.get("cwe", "")
                owasp = metadata.get("owasp", "")
                if cwe or owasp:
                    lines.append(f"- **安全标准**: {cwe} {owasp}".strip())

            lines.append("")

        # 页脚
        lines.append("---")
        lines.append(f"*报告由代码评审工具自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)
