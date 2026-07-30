#!/usr/bin/env python3
"""
验证扫描效果脚本
直接扫描 test-validation 目录中的测试代码，对比已知问题清单
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from rule_engine import RuleEngine
from scan import load_profile


def scan_test_validation(specs_dir: str, test_dir: str):
    """扫描 test-validation 目录"""
    print("=" * 60)
    print("开始扫描 test-validation 目录")
    print("=" * 60)
    
    # 加载 Profile
    profile = load_profile("default", specs_dir)
    engine = RuleEngine(specs_dir=specs_dir, profile=profile)
    
    # 收集所有测试文件
    test_path = Path(test_dir)
    all_files = []
    for ext in ["*.java", "*.py", "*.ts", "*.js"]:
        all_files.extend(test_path.rglob(ext))
    
    print(f"找到 {len(all_files)} 个测试文件")
    
    # 扫描所有文件
    all_issues = []
    for file_path in all_files:
        rel_path = file_path.relative_to(test_path)
        changed_files = [{"path": str(rel_path), "status": "modified"}]
        
        issues = engine.run(str(test_path), changed_files)
        
        # 过滤出当前文件的问题
        file_issues = [
            i for i in issues
            if i["file"] == str(rel_path)
        ]
        
        if file_issues:
            print(f"\n{rel_path}: 检出 {len(file_issues)} 个问题")
            for issue in file_issues:
                print(f"  - 行 {issue['line']}: [{issue['rule_id']}] {issue['message'][:60]}...")
        
        all_issues.extend(file_issues)
    
    print(f"\n{'=' * 60}")
    print(f"扫描完成，共检出 {len(all_issues)} 个问题")
    print(f"{'=' * 60}")
    
    return all_issues


def validate_results(issues, known_issues_path: str):
    """验证扫描结果"""
    print("\n" + "=" * 60)
    print("验证扫描结果")
    print("=" * 60)
    
    # 加载已知问题
    with open(known_issues_path, "r", encoding="utf-8") as f:
        known = json.load(f)
    
    # 构建检出结果索引
    detected = set()
    for issue in issues:
        # 标准化文件路径（去除开头的 ./）
        file_path = issue["file"].lstrip("./")
        key = (file_path, issue["line"], issue["rule_id"])
        detected.add(key)
    
    # 统计
    total = 0
    found = 0
    missed = []
    
    for lang in ["java", "python", "typescript"]:
        for issue in known.get(lang, []):
            total += 1
            file_path = issue["file"].lstrip("./")
            key = (file_path, issue["line"], issue["rule_id"])
            if key in detected:
                found += 1
            else:
                missed.append(issue)
    
    # 检查安全文件误报
    safe_files = {s["file"] for s in known.get("safe_files", [])}
    false_positives = [
        issue for issue in issues
        if issue["file"].lstrip("./") in safe_files
    ]
    
    # 输出结果
    print(f"\n总已知问题数：{total}")
    print(f"已检出：{found}")
    print(f"未检出（漏报）：{total - found}")
    print(f"检出率：{found / total * 100:.1f}%")
    print(f"漏报率：{(total - found) / total * 100:.1f}%")
    print(f"安全文件误报数：{len(false_positives)}")
    
    if missed:
        print(f"\n漏报详情（{len(missed)} 个）：")
        for m in missed:
            print(f"  - {m['file']}:{m['line']} [{m['rule_id']}] {m['description'][:60]}...")
    
    if false_positives:
        print(f"\n误报详情（{len(false_positives)} 个）：")
        for fp in false_positives:
            print(f"  - {fp['file']}:{fp['line']} [{fp['rule_id']}]")
    
    # 按语言统计
    print("\n按语言统计：")
    for lang in ["java", "python", "typescript"]:
        lang_issues = known.get(lang, [])
        lang_total = len(lang_issues)
        lang_found = sum(
            1 for issue in lang_issues
            if (issue["file"].lstrip("./"), issue["line"], issue["rule_id"]) in detected
        )
        lang_rate = lang_found / lang_total * 100 if lang_total > 0 else 0
        print(f"  {lang}: {lang_found}/{lang_total} ({lang_rate:.1f}%)")
    
    # 按漏洞类型统计
    print("\n按漏洞类型统计：")
    vuln_types = {}
    for lang in ["java", "python", "typescript"]:
        for issue in known.get(lang, []):
            rule_id = issue["rule_id"]
            # 提取漏洞类型（规则 ID 的第一部分）
            vuln_type = rule_id.split("-")[0] if "-" in rule_id else rule_id
            if vuln_type not in vuln_types:
                vuln_types[vuln_type] = {"total": 0, "found": 0}
            vuln_types[vuln_type]["total"] += 1
            if (issue["file"].lstrip("./"), issue["line"], issue["rule_id"]) in detected:
                vuln_types[vuln_type]["found"] += 1
    
    for vuln_type, stats in sorted(vuln_types.items()):
        rate = stats["found"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {vuln_type}: {stats['found']}/{stats['total']} ({rate:.1f}%)")
    
    return {
        "total": total,
        "found": found,
        "missed": missed,
        "false_positives": false_positives,
        "detection_rate": found / total * 100 if total > 0 else 0,
    }


def main():
    project_root = Path(__file__).parent
    specs_dir = str(project_root / "references")
    test_dir = str(project_root / "test-validation")
    known_issues_path = str(project_root / "test-validation" / "known-issues.json")
    
    # 扫描
    issues = scan_test_validation(specs_dir, test_dir)
    
    # 验证
    result = validate_results(issues, known_issues_path)
    
    # 保存结果
    output_path = project_root / "test-validation" / "scan-results-latest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "issues": issues,
            "validation": result,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到：{output_path}")


if __name__ == "__main__":
    main()
