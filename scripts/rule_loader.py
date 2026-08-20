#!/usr/bin/env python3
"""
外部规则加载器
从高分开源规约库加载 Semgrep 规则到本地外部规则目录。

支持的规则库：
- Semgrep 官方规则（20000+ 规则）
- 0xdea/semgrep-rules（C/C++ 内存安全）
- mindedsecurity/semgrep-rules-android-security（移动安全）
- 自定义 GitHub 仓库

使用方式：
1. 列出可用规则库：python3 scripts/rule_loader.py --list
2. 从推荐库加载：python3 scripts/rule_loader.py --from recommended
3. 从 GitHub 仓库加载：python3 scripts/rule_loader.py --from github --repo <url>
4. 查看已加载规则：python3 scripts/rule_loader.py --status
5. 移除外部规则：python3 scripts/rule_loader.py --remove <rule-id>
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


# 推荐的高分开源规约库
RECOMMENDED_REPOS = {
    "semgrep-official": {
        "url": "https://github.com/semgrep/semgrep-rules",
        "stars": "15.8k",
        "description": "Semgrep 官方规则库，覆盖 OWASP Top 10，20000+ 规则",
        "languages": ["java", "python", "javascript", "typescript", "go", "c", "cpp"],
        "categories": ["security", "best-practices", "performance"],
        "subdir": "rules"  # 规则在仓库中的子目录
    },
    "0xdea-c-cpp": {
        "url": "https://github.com/0xdea/semgrep-rules",
        "stars": "~500",
        "description": "C/C++ 内存安全规则：缓冲区溢出、use-after-free、整数溢出等",
        "languages": ["c", "cpp"],
        "categories": ["security", "memory-safety"],
        "subdir": "rules"
    },
    "android-security": {
        "url": "https://github.com/mindedsecurity/semgrep-rules-android-security",
        "stars": "335",
        "description": "Android 移动安全规则，基于 OWASP MASTG",
        "languages": ["java", "kotlin"],
        "categories": ["security", "mobile"],
        "subdir": "rules"
    },
    "dom-xss": {
        "url": "https://github.com/dipa96/semgrep-rules",
        "stars": "~30",
        "description": "JavaScript DOM XSS 深度检测规则",
        "languages": ["javascript", "typescript"],
        "categories": ["security", "xss"],
        "subdir": "rules"
    }
}


class RuleLoader:
    """外部规则加载器"""

    def __init__(self, external_rules_dir: str = None):
        """
        Args:
            external_rules_dir: 外部规则目录（默认为 references/external/）
        """
        self.base_dir = Path(__file__).parent.parent
        self.external_dir = Path(external_rules_dir) if external_rules_dir else self.base_dir / "references" / "external"
        self.external_dir.mkdir(parents=True, exist_ok=True)
        
        # 规则元数据文件
        self.metadata_file = self.external_dir / ".loaded_rules.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """加载已加载规则的元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"loaded_rules": [], "sources": {}}

    def _save_metadata(self):
        """保存规则元数据"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def list_recommended(self) -> Dict:
        """列出推荐的规则库"""
        return {
            "status": "success",
            "recommended_repos": RECOMMENDED_REPOS
        }

    def load_from_recommended(self, repo_key: str, categories: List[str] = None) -> Dict:
        """
        从推荐规则库加载
        
        Args:
            repo_key: 规则库标识（如 "semgrep-official"）
            categories: 只加载指定类别的规则
            
        Returns:
            加载结果
        """
        if repo_key not in RECOMMENDED_REPOS:
            return {
                "status": "error",
                "message": f"未知的规则库: {repo_key}。可用: {list(RECOMMENDED_REPOS.keys())}"
            }
        
        repo_info = RECOMMENDED_REPOS[repo_key]
        return self._clone_and_load(
            url=repo_info["url"],
            source_name=repo_key,
            subdir=repo_info.get("subdir"),
            categories=categories
        )

    def load_from_github(self, repo_url: str, subdir: str = None, categories: List[str] = None) -> Dict:
        """
        从自定义 GitHub 仓库加载
        
        Args:
            repo_url: GitHub 仓库 URL
            subdir: 规则在仓库中的子目录
            categories: 只加载指定类别的规则
            
        Returns:
            加载结果
        """
        # 从 URL 提取仓库名
        repo_name = repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        
        return self._clone_and_load(
            url=repo_url,
            source_name=repo_name,
            subdir=subdir,
            categories=categories
        )

    def _clone_and_load(self, url: str, source_name: str, subdir: str = None, categories: List[str] = None) -> Dict:
        """克隆仓库并加载规则"""
        # 创建临时目录
        temp_dir = self.external_dir / ".temp" / source_name
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)
        
        try:
            # 克隆仓库
            print(f"正在克隆 {url} ...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(temp_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"克隆失败: {result.stderr}"
                }
            
            # 确定规则目录
            rules_dir = temp_dir / subdir if subdir else temp_dir
            
            # 扫描并加载规则
            loaded = self._scan_and_load_rules(rules_dir, source_name, categories)
            
            # 记录元数据
            self.metadata["sources"][source_name] = {
                "url": url,
                "loaded_at": datetime.now().isoformat(),
                "rule_count": len(loaded)
            }
            self._save_metadata()
            
            return {
                "status": "success",
                "source": source_name,
                "url": url,
                "loaded_count": len(loaded),
                "loaded_rules": loaded
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "克隆超时（120秒）"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"加载失败: {str(e)}"
            }
        finally:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _scan_and_load_rules(self, rules_dir: Path, source_name: str, categories: List[str] = None) -> List[Dict]:
        """扫描目录并加载 Semgrep 规则"""
        loaded = []
        
        # 查找所有 YAML 文件
        yaml_files = list(rules_dir.rglob("*.yaml")) + list(rules_dir.rglob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                
                # 验证是否为 Semgrep 规则文件
                if not isinstance(content, dict) or "rules" not in content:
                    continue
                
                # 处理每条规则
                for rule in content.get("rules", []):
                    rule_id = rule.get("id")
                    if not rule_id:
                        continue
                    
                    # 检查是否已加载
                    if any(r["rule_id"] == rule_id for r in loaded):
                        continue
                    
                    # 检查类别过滤
                    if categories:
                        rule_category = self._infer_category(rule, yaml_file)
                        if rule_category not in categories:
                            continue
                    
                    # 生成目标文件名
                    target_file = self.external_dir / f"{source_name}_{rule_id}.yaml"
                    
                    # 写入单条规则文件
                    with open(target_file, "w", encoding="utf-8") as f:
                        yaml.dump({"rules": [rule]}, f, allow_unicode=True, default_flow_style=False)
                    
                    loaded.append({
                        "rule_id": rule_id,
                        "source": source_name,
                        "file": str(target_file),
                        "severity": rule.get("severity", "WARNING"),
                        "languages": rule.get("languages", []),
                        "message": rule.get("message", "")[:100]
                    })
                    
                    # 记录到元数据
                    self.metadata["loaded_rules"].append({
                        "rule_id": rule_id,
                        "source": source_name,
                        "loaded_at": datetime.now().isoformat(),
                        "file": str(target_file)
                    })
                
            except Exception as e:
                print(f"警告: 跳过 {yaml_file}: {e}")
                continue
        
        return loaded

    def _infer_category(self, rule: Dict, yaml_file: Path) -> str:
        """推断规则类别"""
        # 从文件路径推断
        path_str = str(yaml_file).lower()
        if "security" in path_str or "vuln" in path_str:
            return "security"
        if "performance" in path_str:
            return "performance"
        if "best-practice" in path_str or "style" in path_str:
            return "best-practices"
        
        # 从规则元数据推断
        metadata = rule.get("metadata", {})
        if "cwe" in metadata or "owasp" in metadata:
            return "security"
        
        return "security"  # 默认

    def status(self) -> Dict:
        """查看已加载规则状态"""
        return {
            "status": "success",
            "external_dir": str(self.external_dir),
            "total_loaded": len(self.metadata["loaded_rules"]),
            "sources": self.metadata["sources"],
            "rules": self.metadata["loaded_rules"]
        }

    def remove_rule(self, rule_id: str) -> Dict:
        """移除已加载的规则"""
        # 查找规则
        rule_info = None
        for rule in self.metadata["loaded_rules"]:
            if rule["rule_id"] == rule_id:
                rule_info = rule
                break
        
        if not rule_info:
            return {
                "status": "error",
                "message": f"未找到规则: {rule_id}"
            }
        
        # 删除文件
        rule_file = Path(rule_info["file"])
        if rule_file.exists():
            rule_file.unlink()
        
        # 从元数据移除
        self.metadata["loaded_rules"] = [
            r for r in self.metadata["loaded_rules"] if r["rule_id"] != rule_id
        ]
        self._save_metadata()
        
        return {
            "status": "success",
            "message": f"已移除规则: {rule_id}"
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="外部规则加载器")
    parser.add_argument("--list", action="store_true", help="列出推荐的规则库")
    parser.add_argument("--from", dest="source", help="加载来源（recommended 或 github）")
    parser.add_argument("--repo", help="GitHub 仓库 URL（--from github 时使用）")
    parser.add_argument("--repo-key", help="推荐规则库标识（--from recommended 时使用）")
    parser.add_argument("--subdir", help="规则在仓库中的子目录")
    parser.add_argument("--categories", nargs="+", help="只加载指定类别的规则")
    parser.add_argument("--status", action="store_true", help="查看已加载规则状态")
    parser.add_argument("--remove", help="移除指定规则")
    
    args = parser.parse_args()
    
    loader = RuleLoader()
    
    if args.list:
        result = loader.list_recommended()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.source == "recommended":
        if not args.repo_key:
            print("错误: --from recommended 需要指定 --repo-key")
            print(f"可用: {list(RECOMMENDED_REPOS.keys())}")
            sys.exit(1)
        result = loader.load_from_recommended(args.repo_key, args.categories)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.source == "github":
        if not args.repo:
            print("错误: --from github 需要指定 --repo")
            sys.exit(1)
        result = loader.load_from_github(args.repo, args.subdir, args.categories)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.status:
        result = loader.status()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.remove:
        result = loader.remove_rule(args.remove)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()
