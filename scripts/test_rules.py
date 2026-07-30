#!/usr/bin/env python3
"""
规则测试脚本
从 test-cases/ 目录加载测试案例，验证规则是否正确生效。
"""

import argparse
import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine import RuleEngine

logger = logging.getLogger("code-review.test")


class TestCaseParser:
    """从测试案例 Markdown 中解析测试用例"""

    def parse_file(self, file_path: str) -> List[Dict]:
        """
        解析测试案例文件

        Returns:
            [{"code": str, "language": str, "expected_rules": [str], "is_valid": bool}]
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        test_cases = []

        # 按 --- 分隔符拆分
        sections = content.split("\n---\n")

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # 提取标题
            title_match = re.search(r"^## (.+)$", section, re.MULTILINE)
            title = title_match.group(1) if title_match else ""
            # 检查整个 section 内容（"违规代码"可能在 ### 子标题中）
            is_valid = "违规代码" in section or "违规" in title or "violation" in section.lower()

            # 提取代码块
            code_blocks = re.findall(
                r"```(\w+)\n(.*?)```",
                section,
                re.DOTALL,
            )

            if not code_blocks:
                continue

            # 取第一个代码块作为测试代码
            lang, code = code_blocks[0]
            code = code.strip()

            # 提取预期命中规则
            expected_match = re.search(
                r"\*\*预期命中\*\*:\s*(.+)",
                section,
            )
            expected_rules = []
            if expected_match:
                expected_text = expected_match.group(1).strip()
                if expected_text != "无":
                    # 解析 rule IDs（可能是逗号分隔的多个）
                    rule_ids = re.findall(r"`([^`]+)`", expected_text)
                    expected_rules = rule_ids

            test_cases.append({
                "title": title,
                "code": code,
                "language": lang,
                "expected_rules": expected_rules,
                "is_valid": is_valid,
                "source_file": os.path.basename(file_path),
            })

        return test_cases


class RuleTester:
    """规则测试器"""

    def __init__(self, specs_dir: str):
        self.specs_dir = specs_dir
        self.test_parser = TestCaseParser()

    def run_tests(self, test_dir: str) -> Dict:
        """
        运行所有测试案例

        Returns:
            {"total": int, "passed": int, "failed": int, "results": [...]}
        """
        test_dir = Path(test_dir)
        all_results = []

        # 加载默认 profile 的规则引擎
        from scan import load_profile
        profile = load_profile("default", self.specs_dir)
        engine = RuleEngine(specs_dir=self.specs_dir, profile=profile)

        # 遍历测试案例文件
        for md_file in sorted(test_dir.rglob("*.md")):
            if md_file.name == "README.md":
                continue

            test_cases = self.test_parser.parse_file(str(md_file))

            for tc in test_cases:
                result = self._run_single_test(engine, tc)
                all_results.append(result)

        # 统计
        passed = sum(1 for r in all_results if r["passed"])
        failed = sum(1 for r in all_results if not r["passed"])

        return {
            "total": len(all_results),
            "passed": passed,
            "failed": failed,
            "results": all_results,
        }

    def _run_single_test(self, engine: RuleEngine, test_case: Dict) -> Dict:
        """运行单个测试案例"""
        # 将测试代码写入临时文件
        ext_map = {
            "java": ".java",
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "jsx": ".jsx",
            "tsx": ".tsx",
        }
        ext = ext_map.get(test_case["language"], ".java")

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=ext,
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(test_case["code"])
            temp_file = f.name

        try:
            # 运行规则引擎（自动选择 Semgrep 或内置引擎）
            changed_files = [{"path": os.path.basename(temp_file), "status": "modified"}]
            issues = engine.run(
                os.path.dirname(temp_file),
                changed_files,
            )

            # 过滤出匹配当前文件的 issues
            file_issues = [
                i for i in issues
                if i["file"] == os.path.basename(temp_file)
            ]

            actual_rules = list(set(i["rule_id"] for i in file_issues))
            expected_rules = test_case["expected_rules"]

            # 判断是否通过
            if test_case["is_valid"]:
                # 违规代码：应该命中预期规则
                passed = all(r in actual_rules for r in expected_rules)
            else:
                # 正确代码：不应该命中任何规则
                passed = len(actual_rules) == 0

            return {
                "title": test_case["title"],
                "source_file": test_case["source_file"],
                "language": test_case["language"],
                "is_valid": test_case["is_valid"],
                "expected_rules": expected_rules,
                "actual_rules": actual_rules,
                "passed": passed,
                "details": file_issues if not passed else [],
            }

        finally:
            os.unlink(temp_file)


def main():
    parser = argparse.ArgumentParser(description="规则测试脚本")
    parser.add_argument(
        "--test-dir",
        default=None,
        help="测试案例目录（默认: references/test-cases/）",
    )
    parser.add_argument(
        "--specs-dir",
        default=None,
        help="规约库目录（默认: references/）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出 JSON 报告路径",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 确定目录
    project_root = Path(__file__).parent.parent
    specs_dir = args.specs_dir or str(project_root / "references")
    test_dir = args.test_dir or str(project_root / "references" / "test-cases")

    if not os.path.exists(test_dir):
        logger.error(f"测试目录不存在: {test_dir}")
        sys.exit(1)

    # 运行测试
    logger.info(f"测试目录: {test_dir}")
    logger.info(f"规约目录: {specs_dir}")
    logger.info("=" * 60)

    tester = RuleTester(specs_dir=specs_dir)
    report = tester.run_tests(test_dir)

    # 输出结果
    logger.info("=" * 60)
    logger.info(f"测试完成: 总计 {report['total']} | 通过 {report['passed']} | 失败 {report['failed']}")
    logger.info("=" * 60)

    if report["failed"] > 0:
        logger.info("\n失败的测试:")
        for r in report["results"]:
            if not r["passed"]:
                logger.info(f"  ✗ [{r['source_file']}] {r['title']}")
                logger.info(f"    预期: {r['expected_rules']}")
                logger.info(f"    实际: {r['actual_rules']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"\n报告已保存到: {args.output}")

    sys.exit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
