#!/usr/bin/env python3
"""java-sec-code 方法级 ground truth 对比：taint/deep-detection 规则检出 vs vuln/sec 标注"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from rule_engine import RuleEngine
import yaml

REPO = Path(__file__).resolve().parent.parent / "repos" / "java-sec-code"
FOCUS_RULES = ("path-traversal-taint", "ssrf-taint", "xss-taint", "sqli-taint",
               "deser-taint", "ssrf-deep-detection", "xxe-deep-detection",
               "spel-taint", "qlexpress-taint", "script-engine-taint")

MAPPING_RE = re.compile(
    r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(([^)]*)\)')
METHOD_RE = re.compile(
    r'^\s+(?:public|private|protected)\s+[\w<>,\[\]\s\.\?]+?\s+(\w+)\s*\(', re.M)


def extract_methods(java_src: str):
    """返回 [(name, mapping_path, start_line, end_line)]，行号 1-based"""
    lines = java_src.split("\n")
    methods = []
    # 找每个 mapping 注解后紧跟的方法签名
    for m in MAPPING_RE.finditer(java_src):
        ann_end = java_src.index("\n", m.end()) + 1 if "\n" in java_src[m.end():] else len(java_src)
        sig = METHOD_RE.search(java_src, ann_end)
        if not sig or sig.start() > ann_end + 200:
            continue
        name_m = sig
        start_line = java_src[:name_m.start()].count("\n") + 1
        # 方法体结束：下一个 mapping 或类结束（近似：下一个方法签名）
        next_sig = METHOD_RE.search(java_src, name_m.end())
        end_line = (java_src[:next_sig.start()].count("\n") + 1
                    if next_sig else len(lines))
        # 提取路径
        path = ""
        pv = re.search(r'(?:value\s*=\s*|path\s*=\s*)?"([^"]*)"', m.group(2))
        if pv:
            path = pv.group(1)
        methods.append((name_m.group(1), path, start_line, end_line))
    return methods


def classify(path: str) -> str:
    p = path.lower()
    if "vuln" in p:
        return "vuln"
    if "sec" in p or "safe" in p or "security" in p or "check" in p:
        return "sec"
    return "other"


def main():
    with open(Path(__file__).resolve().parent.parent / "references" / "profiles" / "default.yaml") as f:
        profile = yaml.safe_load(f)
    engine = RuleEngine(specs_dir=str(
        Path(__file__).resolve().parent.parent / "references"), profile=profile)

    files = [{"path": str(p.relative_to(REPO))}
             for p in REPO.rglob("*.java") if ".git" not in str(p)]
    issues = engine.run(str(REPO), files)

    # 每个文件解析方法表
    src_cache = {}
    for f in files:
        p = REPO / f["path"]
        src_cache[f["path"]] = extract_methods(p.read_text(encoding="utf-8", errors="ignore"))

    print(f"{'规则':<28} {'文件':<22} {'行':>4}  {'方法':<24} {'路径':<32} 标注")
    print("-" * 130)
    tp = fp = other = 0
    hits = []
    for i in issues:
        rid = str(i.get("rule_id", ""))
        if not any(r in rid for r in FOCUS_RULES):
            continue
        fp_rel = str(i.get("file", ""))
        line = int(i.get("line", 0))
        # 定位所属方法
        entry = None
        for (name, path, s, e) in src_cache.get(fp_rel, []):
            if s <= line <= e:
                entry = (name, path)
                break
        if entry is None:
            # 检出点不在入口方法内（辅助方法/字段）——向上下文标注
            label = "NON-ENTRY"
            other += 1
            hits.append((rid.split("__")[0], fp_rel, line, "-", "-", label))
            continue
        name, path = entry
        label = classify(path)
        if label == "vuln":
            tp += 1
        elif label == "sec":
            fp += 1
        hits.append((rid.split("__")[0], fp_rel, line, name, path, label))

    for h in sorted(hits):
        print(f"{h[0]:<28} {h[1]:<22} {h[2]:>4}  {h[3]:<24} {h[4]:<32} {h[5]}")

    print("-" * 130)
    print(f"入口方法内检出: TP(vuln)={tp}  FP(sec)={fp}  非入口方法/other={other}")

    # 漏检统计：全部 vuln 方法中被任一 focus 规则命中的
    total_vuln = 0
    covered_vuln = set()
    for f, methods in src_cache.items():
        for (name, path, s, e) in methods:
            if classify(path) == "vuln":
                total_vuln += 1
                for h in hits:
                    if h[1] == f and h[5] in ("vuln", "NON-ENTRY") and s <= h[2] <= e:
                        covered_vuln.add((f, name, path))
    print(f"仓库 vuln 方法总数(映射路径含vuln): {total_vuln}")


if __name__ == "__main__":
    main()
