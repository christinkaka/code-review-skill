#!/usr/bin/env python3
"""
双引擎并行扫描器
同时使用内置正则引擎和 Semgrep，合并结果，提高检出率
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("code-review.dual-engine")


class DualEngineScanner:
    """双引擎并行扫描器"""
    
    def __init__(self, specs_dir: str, profile: str = "default"):
        self.specs_dir = Path(specs_dir)
        self.profile = profile
        self.builtin_available = True
        self.semgrep_available = self._check_semgrep()
        
    def _check_semgrep(self) -> bool:
        """检查 Semgrep 是否可用"""
        try:
            result = subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def scan_with_builtin(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """使用内置正则引擎扫描"""
        from rule_engine import RuleEngine
        
        # 加载 Profile
        import yaml
        profile_path = self.specs_dir / "profiles" / f"{self.profile}.yaml"
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        
        engine = RuleEngine(specs_dir=str(self.specs_dir), profile=profile)
        return engine.run(repo_path, changed_files)
    
    def scan_with_semgrep(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """使用 Semgrep 扫描"""
        if not self.semgrep_available:
            logger.warning("Semgrep 不可用，跳过 Semgrep 扫描")
            return []
        
        # 加载规则
        import yaml
        profile_path = self.specs_dir / "profiles" / f"{self.profile}.yaml"
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        
        from rule_engine import RuleEngine
        engine = RuleEngine(specs_dir=str(self.specs_dir), profile=profile)
        
        # 转换为 Semgrep 格式
        semgrep_rules = engine._rules_to_semgrep()
        
        if not semgrep_rules["rules"]:
            return []
        
        # 写入临时规则文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(semgrep_rules, f, default_flow_style=False, allow_unicode=True)
            rules_file = f.name
        
        try:
            # 执行 Semgrep
            cmd = [
                "semgrep",
                "--config", rules_file,
                "--json",
                "--no-git-ignore",
                "--quiet",
                ".",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=repo_path,
                env={**os.environ, "SEMGREP_HOME": "/tmp/semgrep"},
            )
            
            issues = []
            if result.stdout:
                try:
                    semgrep_output = json.loads(result.stdout)
                    # 构建规则 ID 查找表（用于从 check_id 中提取真实 rule_id）
                    known_rule_ids = {r["id"] for r in engine.rules if r.get("id")}
                    for finding in semgrep_output.get("results", []):
                        raw_check_id = finding.get("check_id", "")
                        # 提取真实 rule_id（去除临时文件路径前缀）
                        rule_id = raw_check_id
                        for known_id in known_rule_ids:
                            if raw_check_id == known_id or raw_check_id.endswith("." + known_id):
                                rule_id = known_id
                                break

                        issue = {
                            "rule_id": rule_id,
                            "category": engine._get_category(rule_id),
                            "severity": finding.get("extra", {}).get("severity", "WARNING"),
                            "file": finding.get("path", ""),
                            "line": finding.get("start", {}).get("line", 0),
                            "end_line": finding.get("end", {}).get("line", 0),
                            "message": finding.get("extra", {}).get("message", ""),
                            "code_snippet": finding.get("extra", {}).get("lines", ""),
                            "engine": "semgrep",
                        }
                        issues.append(issue)
                except json.JSONDecodeError:
                    logger.error("Semgrep 输出解析失败")
            
            return issues
            
        except subprocess.TimeoutExpired:
            logger.error("Semgrep 扫描超时")
            return []
        except Exception as e:
            logger.error(f"Semgrep 扫描失败: {e}")
            return []
        finally:
            os.unlink(rules_file)
    
    def merge_results(self, builtin_issues: List[Dict], semgrep_issues: List[Dict]) -> List[Dict]:
        """合并两个引擎的结果"""
        merged = {}
        
        # 添加内置引擎结果
        for issue in builtin_issues:
            key = f"{issue['file']}:{issue['line']}:{issue.get('rule_id', '')}"
            issue["engine"] = "builtin"
            issue["engines"] = ["builtin"]
            merged[key] = issue
        
        # 合并 Semgrep 结果
        for issue in semgrep_issues:
            key = f"{issue['file']}:{issue['line']}:{issue.get('rule_id', '')}"
            if key in merged:
                # 同一个问题被两个引擎检出，标记为高置信度
                merged[key]["engines"].append("semgrep")
                merged[key]["confidence"] = 1.0  # 两个引擎都检出，置信度最高
            else:
                # Semgrep 独有的检出
                issue["engines"] = ["semgrep"]
                merged[key] = issue
        
        return list(merged.values())
    
    def scan(self, repo_path: str, changed_files: List[Dict]) -> Dict:
        """执行双引擎扫描"""
        logger.info("开始双引擎并行扫描...")
        
        # 内置引擎扫描
        logger.info("[1/2] 内置正则引擎扫描...")
        builtin_issues = self.scan_with_builtin(repo_path, changed_files)
        logger.info(f"  内置引擎检出 {len(builtin_issues)} 个问题")
        
        # Semgrep 扫描
        logger.info("[2/2] Semgrep 引擎扫描...")
        semgrep_issues = self.scan_with_semgrep(repo_path, changed_files)
        logger.info(f"  Semgrep 检出 {len(semgrep_issues)} 个问题")
        
        # 合并结果
        logger.info("合并扫描结果...")
        merged_issues = self.merge_results(builtin_issues, semgrep_issues)
        logger.info(f"  合并后共 {len(merged_issues)} 个问题")
        
        # 统计
        both_engines = sum(1 for i in merged_issues if len(i.get("engines", [])) == 2)
        builtin_only = sum(1 for i in merged_issues if i.get("engines") == ["builtin"])
        semgrep_only = sum(1 for i in merged_issues if i.get("engines") == ["semgrep"])
        
        return {
            "issues": merged_issues,
            "stats": {
                "total": len(merged_issues),
                "builtin": len(builtin_issues),
                "semgrep": len(semgrep_issues),
                "both_engines": both_engines,
                "builtin_only": builtin_only,
                "semgrep_only": semgrep_only,
            }
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="双引擎并行扫描器")
    parser.add_argument("--repo", required=True, help="仓库路径")
    parser.add_argument("--specs-dir", required=True, help="规约库目录")
    parser.add_argument("--profile", default="default", help="规约 Profile")
    parser.add_argument("--output", required=True, help="输出文件")
    
    args = parser.parse_args()
    
    # 执行扫描
    scanner = DualEngineScanner(specs_dir=args.specs_dir, profile=args.profile)
    
    # 加载变更文件（这里简化为全量扫描）
    changed_files = []
    for root, dirs, files in os.walk(args.repo):
        for file in files:
            if file.endswith((".java", ".py", ".js", ".ts")):
                changed_files.append({
                    "path": os.path.relpath(os.path.join(root, file), args.repo),
                    "status": "modified",
                })
    
    result = scanner.scan(args.repo, changed_files)
    
    # 输出结果
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"扫描完成，结果保存到: {args.output}")
    print(f"总计: {result['stats']['total']} 个问题")
    print(f"  内置引擎: {result['stats']['builtin']}")
    print(f"  Semgrep: {result['stats']['semgrep']}")
    print(f"  两个引擎都检出: {result['stats']['both_engines']}")
    print(f"  仅内置引擎: {result['stats']['builtin_only']}")
    print(f"  仅 Semgrep: {result['stats']['semgrep_only']}")


if __name__ == "__main__":
    main()
