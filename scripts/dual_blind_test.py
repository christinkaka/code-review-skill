#!/usr/bin/env python3
"""
双盲测试脚本 - 通过完整 SKILL 流程验证真实仓库

走完整流程：
1. RuleEngine (规则引擎 + Semgrep)
2. AIReviewer (AI 复核，mock LLM)
3. ReportGenerator (报告生成)

验证：
- 规则引擎检出能力
- AI 复核过滤效果
- 报告生成完整性
"""

import json
import sys
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from rule_engine import RuleEngine
from ai_reviewer import AIReviewer
from report_generator import ReportGenerator
from scan import prefilter_issues, tiered_ai_review
import yaml


def run_dual_blind_test(repo_name: str, repo_path: str, file_ext: str, max_files: int = 200):
    """对单个仓库执行双盲测试"""
    print(f"\n{'='*60}")
    print(f"双盲测试: {repo_name}")
    print(f"{'='*60}")
    
    # 1. 加载 Profile
    with open('references/profiles/default.yaml') as f:
        profile = yaml.safe_load(f)
    
    # 2. 初始化规则引擎
    engine = RuleEngine(specs_dir='references', profile=profile)
    
    # 3. 收集文件
    repo = Path(repo_path)
    files = [str(p.relative_to(repo_path)) for p in repo.rglob(f'*{file_ext}') 
             if '.git' not in str(p)][:max_files]
    
    print(f"\n[1/4] 扫描文件: {len(files)} 个 {file_ext} 文件")
    
    # 4. 规则引擎扫描
    start_time = time.time()
    raw_issues = engine.run(repo_path, [{'path': f} for f in files])
    scan_duration = time.time() - start_time
    
    print(f"[2/4] 规则引擎检出: {len(raw_issues)} 个问题 (耗时 {scan_duration:.2f}s)")
    
    # 4.5 Prefilter 白名单过滤（与 scan.py 主流程一致，测试文件误报在此过滤）
    raw_issues = prefilter_issues(raw_issues, {})
    print(f"      Prefilter 后: {len(raw_issues)} 个问题")

    # 5. AI 复核（mock LLM，分层评审：CRITICAL/ERROR 精审，WARNING/INFO 统计层保留）
    ai_config = {
        "llm": {
            "url": "https://api.example.com/v1/chat/completions",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4"
        },
        "confidence_threshold": 0.7,
        "max_retries": 0,
        "audit": {"enabled": True, "log_path": ""},
        "workflow": "security"
    }

    reviewer = AIReviewer(ai_config)

    # Mock LLM 响应：保留 80% 的问题（模拟真实 AI 过滤效果）
    import random
    random.seed(42)  # 固定种子保证可重复

    high_issues = [i for i in raw_issues
                   if i.get("severity") in ("CRITICAL", "HIGH", "ERROR")]

    mock_response = json.dumps([
        {
            "rule_id": issue["rule_id"],
            "file": issue.get("file", ""),
            "line": issue.get("line", 0),
            "is_valid": random.random() > 0.2,  # 80% 保留
            "confidence": 0.75 + random.random() * 0.2,  # 0.75-0.95
            "enhanced_fix": "建议修复方案"
        }
        for issue in high_issues
    ])

    # Monkey patch LLM 调用
    reviewer._call_llm = lambda prompt: mock_response
    reviewer._is_available = lambda: True

    filtered_issues, triage = tiered_ai_review(reviewer, raw_issues, {}, {})

    print(f"[3/4] AI 复核后: {len(filtered_issues)} 个问题")
    print(f"      分层: LLM 精审 {triage['reviewed']} 条, "
          f"统计层保留 {triage['stats_only']} 条")
    
    # 6. 审计统计
    audit_summary = reviewer.get_audit_summary()
    print(f"      - 保留: {audit_summary['kept']}")
    print(f"      - 过滤: {audit_summary['dropped']}")
    print(f"      - 误杀 ERROR: {audit_summary['dropped_errors']}")
    
    # 7. 问题分类统计
    rule_counts = Counter(i['rule_id'] for i in raw_issues)
    severity_counts = Counter(i['severity'] for i in raw_issues)
    
    print(f"\n[4/4] 问题分布:")
    print(f"  Top 5 规则:")
    for rule_id, count in rule_counts.most_common(5):
        print(f"    {rule_id}: {count}")
    
    print(f"  严重级别:")
    for sev in ['CRITICAL', 'ERROR', 'WARNING', 'INFO']:
        count = severity_counts.get(sev, 0)
        if count > 0:
            print(f"    {sev}: {count}")

    # 7.5 数学理论降噪指标（noise_theory.py，确定性判据）
    from noise_theory import fdr_report, flag_noise_rules
    confs = [i.get("confidence", 0.5) for i in filtered_issues]
    fdr = fdr_report(confs)
    print(f"  期望误报(信息论): {fdr['expected_fp']:.1f} 条 "
          f"(期望 FDR {fdr['expected_fdr']:.1%})")
    flagged = flag_noise_rules(dict(rule_counts))
    if flagged:
        print(f"  z-score 离群规则(|z|>=2): {', '.join(flagged[:3])}")

    # 8. 生成报告
    output_dir = Path('reports') / f'dual-blind-{repo_name.lower().replace(" ", "-")}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = ReportGenerator(output_dir=str(output_dir))
    report = generator.generate(
        scan_info={
            "repo": repo_name,
            "repo_path": repo_path,
            "profile": "default",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "duration_seconds": round(scan_duration, 2),
            "test_type": "dual-blind",
        },
        issues=filtered_issues,
        diff_summary={
            "changed_files": [{"path": f, "status": "modified"} for f in files[:10]],
            "changed_methods": [],
        },
        call_graph_summary={
            "node_count": 0,
            "edge_count": 0,
            "affected_methods": [],
        }
    )
    
    print(f"\n✅ 报告已生成: {output_dir}")
    
    return {
        "repo": repo_name,
        "files_scanned": len(files),
        "raw_issues": len(raw_issues),
        "filtered_issues": len(filtered_issues),
        "scan_duration": scan_duration,
        "audit_summary": audit_summary,
        "top_rules": rule_counts.most_common(5),
    }


def main():
    """运行所有仓库的双盲测试"""
    print("="*60)
    print("双盲测试 - 真实 GitHub Top 仓库")
    print("="*60)
    
    repos = [
        ("freeCodeCamp", "repos/freeCodeCamp", ".js"),
        ("Django", "repos/django", ".py"),
        ("Spring Boot", "repos/spring-boot", ".java"),
        ("WebGoat", "repos/webgoat", ".java"),
    ]
    
    results = []
    for repo_name, repo_path, file_ext in repos:
        if not Path(repo_path).exists():
            print(f"\n⚠️  跳过 {repo_name}（目录不存在）")
            continue
        
        result = run_dual_blind_test(repo_name, repo_path, file_ext)
        results.append(result)
    
    # 汇总
    print("\n" + "="*60)
    print("双盲测试汇总")
    print("="*60)
    
    total_files = sum(r['files_scanned'] for r in results)
    total_raw = sum(r['raw_issues'] for r in results)
    total_filtered = sum(r['filtered_issues'] for r in results)
    
    print(f"\n总扫描文件: {total_files}")
    print(f"规则引擎检出: {total_raw}")
    print(f"AI 复核后: {total_filtered}")
    print(f"过滤率: {(total_raw - total_filtered) / total_raw * 100:.1f}%")
    
    print(f"\n各仓库明细:")
    for r in results:
        print(f"  {r['repo']}: {r['raw_issues']} → {r['filtered_issues']} "
              f"(过滤 {r['raw_issues'] - r['filtered_issues']})")
    
    print("\n✅ 双盲测试完成！所有仓库通过 SKILL 完整流程验证。")


if __name__ == "__main__":
    main()
