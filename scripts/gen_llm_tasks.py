#!/usr/bin/env python3
"""从双盲测试存量报告生成子 Agent 评审任务文件（真实 LLM 验证用）"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_reviewer import AIReviewer

BASE = Path(__file__).parent.parent

REPOS = {
    "webgoat": "repos/webgoat",
    "freecodecamp": "repos/freeCodeCamp",
    "spring-boot": "repos/spring-boot",
}

reviewer = AIReviewer({})
for name, repo in REPOS.items():
    report_path = BASE / "reports" / f"dual-blind-{name}" / "report.json"
    import json

    with open(report_path) as f:
        report = json.load(f)
    issues = report.get("issues", [])
    if not issues:
        print(f"{name}: 0 issues, skip")
        continue
    task_path = BASE / "reports" / f"dual-blind-{name}" / "subagent-review-task.md"
    reviewer.generate_subagent_task(
        issues=issues,
        scan_info={"repo": repo, "profile": "default"},
        output_path=str(task_path),
    )
    print(f"{name}: {len(issues)} issues -> {task_path}")
