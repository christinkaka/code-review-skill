#!/usr/bin/env python3
"""能力地图生成器：从规则库实时推导，输出 docs/capability-map.md。

设计原则（维护成本优先）：
- 规则明细全部自动推导（规约 md 元数据 + tests/ 引用扫描 + 孪生 yaml
  存在性），不手工维护规则表格，杜绝 docs/rules.md 式过时
- 人工只维护 docs/capability-map-data.yaml 薄数据层：类别质量等级（L0-L3）
  与靶场验证凭证——这两项无法从代码推导
- 输出按 L 等级分组 + CWE 对齐 + 待扩展格，与 blueprint.md 质量阶梯一致

用法：python3 scripts/gen_capability_map.py
"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from rule_engine import MarkdownRuleParser

ROOT = Path(__file__).parent.parent
SPECS_ROOT = ROOT / "references"
DATA_FILE = ROOT / "docs" / "capability-map-data.yaml"
OUT_FILE = ROOT / "docs" / "capability-map.md"

SPEC_DIRS = ["security", "design", "implementation"]


def collect_rules():
    parser = MarkdownRuleParser()
    rules = []
    for d in SPEC_DIRS:
        for md in sorted((SPECS_ROOT / d).glob("*.md")):
            for r in parser.parse_file(str(md)):
                if r.get("id"):
                    r["_dir"] = d
                    r["_taint"] = bool(r.get("taint", {}).get("sources"))
                    rules.append(r)
    return rules


def collect_test_coverage(rules):
    tests_blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (ROOT / "tests").glob("*.py")
    )
    return {
        r["id"]: f'"{r["id"]}"' in tests_blob or f"'{r['id']}'" in tests_blob
        for r in rules
    }


def _cwe_parts(cwe_str) -> list:
    """'CWE-94/95/917' → ['CWE-94', 'CWE-95', 'CWE-917']（补全缺前缀的段）"""
    parts = []
    for p in str(cwe_str or "").split("/"):
        p = p.strip()
        if not p:
            continue
        if not p.upper().startswith("CWE-"):
            p = "CWE-" + p
        parts.append(p)
    return parts


def main():
    data = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))
    categories = data["categories"]
    planned = data.get("planned", [])

    rules = collect_rules()
    test_cov = collect_test_coverage(rules)

    # cwe 归组（规约元数据 cwe 首字段为主键，如 "CWE-94/95" 取全部）
    by_cwe = {}
    for r in rules:
        cwe = str(r.get("cwe") or "").strip()
        if not cwe:
            continue
        for part in _cwe_parts(cwe):
            by_cwe.setdefault(part, []).append(r)

    cat_by_cwe = {}
    for c in categories:
        for part in _cwe_parts(c["cwe"]):
            cat_by_cwe[part] = c

    taint_count = sum(1 for r in rules if r["_taint"])
    e2e_count = sum(1 for v in test_cov.values() if v)
    l3 = sum(1 for c in categories if c["quality_level"] == "L3")
    twin_missing = [
        r for r in rules
        if r["_dir"] == "security"
        and not (SPECS_ROOT / "security" / (r["_source_file"].rsplit(".", 1)[0] + ".yaml")).exists()
    ]

    lines = []
    lines.append("# 能力地图（自动生成，勿手改）")
    lines.append("")
    lines.append("> 由 `scripts/gen_capability_map.py` 从规则库实时推导生成。")
    lines.append("> 人工只维护 `docs/capability-map-data.yaml`（质量等级与靶场凭证），")
    lines.append("> 修改后重跑 `python3 scripts/gen_capability_map.py`。")
    lines.append("> 质量阶梯判定标准与推进批次见 `docs/blueprint.md`；")
    lines.append("> 新增规则的标准流程见 `docs/rule-intake-sop.md`。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 规则总数：**{len(rules)}**（taint 数据流 {taint_count} / pattern {len(rules) - taint_count}）")
    lines.append(f"- e2e 测试覆盖规则：**{e2e_count}**")
    lines.append(f"- L3 类别（靶场盲测零误报）：**{l3}** / L2 {sum(1 for c in categories if c['quality_level'] == 'L2')}")
    lines.append(f"- 待扩展格（L0）：**{len(planned)}**")
    if twin_missing:
        names = sorted({r["_source_file"] for r in twin_missing})
        lines.append(f"- ⚠ 孪生 yaml 缺失：{', '.join(names)}（补齐见 SOP 第 5 步）")
    lines.append("")

    lines.append("## 覆盖矩阵（按质量等级）")
    lines.append("")
    lines.append("| 等级 | CWE | 类别 | OWASP | 规则 | taint | e2e | 靶场凭证 |")
    lines.append("|------|-----|------|-------|------|-------|-----|----------|")
    for level in ("L3", "L2", "L1"):
        for c in categories:
            if c["quality_level"] != level:
                continue
            cwes = _cwe_parts(c["cwe"])
            grouped = []
            seen = set()
            for p in cwes:
                for r in by_cwe.get(p, []):
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        grouped.append(r)
            rule_names = "、".join(
                f'`{r["id"]}`' + ("⚠" if not test_cov.get(r["id"]) else "")
                for r in grouped
            ) or "—"
            taint_flag = "✓" if any(r["_taint"] for r in grouped) else "—"
            e2e_flag = "✓" if grouped and all(test_cov.get(r["id"]) for r in grouped) else ("部分" if any(test_cov.get(r["id"]) for r in grouped) else "—")
            bt = c.get("blind_test")
            bt_text = f'{bt["target"]}: {bt["result"]}' if bt else "—"
            lines.append(
                f'| {level} | {c["cwe"]} | {c["name"]} | {c["owasp"]} '
                f'| {rule_names} | {taint_flag} | {e2e_flag} | {bt_text} |'
            )
    lines.append("")
    lines.append("> 规则名后 ⚠ 表示无 e2e 测试引用；e2e 列以规则 id 在 tests/ 中出现为准。")
    lines.append("")

    lines.append("## 待扩展格（L0，有 CVE/CWE 归属无规则）")
    lines.append("")
    lines.append("| CWE | 类别 | OWASP | 推进批次 |")
    lines.append("|-----|------|-------|----------|")
    for p in planned:
        lines.append(f'| {p["cwe"]} | {p["name"]} | {p["owasp"]} | {p["batch"]} |')
    lines.append("")

    lines.append("## 规则明细（全量自动推导）")
    lines.append("")
    lines.append("| 规则 id | 类别 | 等级 | 语言 | 形态 | e2e |")
    lines.append("|---------|------|------|------|------|-----|")
    cat_level = {}
    for c in categories:
        for part in _cwe_parts(c["cwe"]):
            cat_level[part] = c["quality_level"]
    for r in sorted(rules, key=lambda x: (x["_dir"], x["id"])):
        cwe = (_cwe_parts(r.get("cwe")) or ["—"])[0]
        level = cat_level.get(cwe, "—")
        lines.append(
            f'| `{r["id"]}` | {cwe or "—"} | {level} '
            f'| {"/".join(r.get("languages", []))} '
            f'| {"taint" if r["_taint"] else "pattern"} '
            f'| {"✓" if test_cov.get(r["id"]) else "—"} |'
        )
    lines.append("")

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"生成 {OUT_FILE.relative_to(ROOT)}：{len(rules)} 规则，L3 类别 {l3}，待扩展 {len(planned)}")
    if twin_missing:
        print(f"⚠ 孪生 yaml 缺失：{sorted({r['_source_file'] for r in twin_missing})}")


if __name__ == "__main__":
    main()
