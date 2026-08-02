#!/usr/bin/env python3
"""
规则预编译器
将 Markdown 规则文件编译为 Semgrep 可执行的格式，并通过 hash 检查避免重复编译。

工作流程：
1. 计算 Markdown 文件的 hash
2. 检查缓存（references/compiled/）是否有效
3. 如果 hash 变化，调用 AI 生成 pattern
4. 保存编译后的规则到缓存
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger("code-review.compiler")


class RuleCompiler:
    """规则预编译器"""

    def __init__(self, specs_dir: str):
        self.specs_dir = Path(specs_dir)
        self.compiled_dir = self.specs_dir / "compiled"
        self.manifest_path = self.compiled_dir / "manifest.json"
        
        # 确保编译目录存在
        self.compiled_dir.mkdir(parents=True, exist_ok=True)

    def compute_file_hash(self, file_path: str) -> str:
        """计算文件的 SHA256 hash"""
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def load_manifest(self) -> Dict:
        """加载 manifest 文件"""
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_manifest(self, manifest: Dict):
        """保存 manifest 文件"""
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def is_cache_valid(self, rel_path: str, current_hash: str, manifest: Dict) -> bool:
        """检查缓存是否有效"""
        if rel_path not in manifest:
            return False
        
        cached = manifest[rel_path]
        return cached.get("hash") == current_hash

    def compile_file(self, md_path: str, force: bool = False) -> Dict:
        """
        编译单个 Markdown 文件
        
        Args:
            md_path: Markdown 文件路径
            force: 是否强制重新编译
            
        Returns:
            编译后的规则字典
        """
        md_path = Path(md_path)
        rel_path = str(md_path.relative_to(self.specs_dir))
        
        # 计算当前 hash
        current_hash = self.compute_file_hash(str(md_path))
        
        # 加载 manifest
        manifest = self.load_manifest()
        
        # 检查缓存
        if not force and self.is_cache_valid(rel_path, current_hash, manifest):
            logger.debug(f"缓存有效，跳过编译: {rel_path}")
            compiled_path = self.compiled_dir / f"{rel_path}.json"
            with open(compiled_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 需要重新编译
        logger.info(f"编译规则文件: {rel_path}")
        
        # 解析 Markdown 文件
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from rule_engine import MarkdownRuleParser
        parser = MarkdownRuleParser()
        rules = parser.parse_file(str(md_path))
        
        # 检查是否需要 AI 生成 pattern
        for rule in rules:
            if not rule.get("patterns"):
                logger.warning(f"规则 {rule['id']} 没有 pattern，需要 AI 生成")
                # TODO: 调用 AI 生成 pattern
                # 暂时跳过
                continue
        
        # 构建编译结果
        compiled = {
            "source": rel_path,
            "hash": current_hash,
            "compiled_at": datetime.now().isoformat(),
            "rules_count": len(rules),
            "rules": rules
        }
        
        # 保存编译结果
        compiled_path = self.compiled_dir / f"{rel_path}.json"
        compiled_path.parent.mkdir(parents=True, exist_ok=True)
        with open(compiled_path, "w", encoding="utf-8") as f:
            json.dump(compiled, f, indent=2, ensure_ascii=False)
        
        # 更新 manifest
        manifest[rel_path] = {
            "hash": current_hash,
            "compiled_at": compiled["compiled_at"],
            "rules_count": len(rules)
        }
        self.save_manifest(manifest)
        
        logger.info(f"编译完成: {rel_path} ({len(rules)} 条规则)")
        return compiled

    def compile_all(self, force: bool = False) -> List[Dict]:
        """
        编译所有 Markdown 规则文件
        
        Args:
            force: 是否强制重新编译所有文件
            
        Returns:
            编译后的规则列表
        """
        compiled_rules = []
        
        # 遍历所有 Markdown 文件
        for md_file in self.specs_dir.rglob("*.md"):
            # 跳过 compiled 目录、test-cases 目录、prompts 目录和指南文件
            if ("compiled" in str(md_file) or 
                "test-cases" in str(md_file) or 
                "prompts" in str(md_file) or
                md_file.name == "RULE-GENERATOR-GUIDE.md"):
                continue
            
            try:
                compiled = self.compile_file(str(md_file), force=force)
                compiled_rules.extend(compiled.get("rules", []))
            except Exception as e:
                logger.error(f"编译失败 {md_file}: {e}")
        
        logger.info(f"编译完成，共 {len(compiled_rules)} 条规则")
        return compiled_rules

    def check_status(self) -> Dict:
        """
        检查编译状态
        
        Returns:
            状态信息字典
        """
        manifest = self.load_manifest()
        
        status = {
            "total_files": 0,
            "cached_files": 0,
            "outdated_files": 0,
            "details": []
        }
        
        for md_file in self.specs_dir.rglob("*.md"):
            # 跳过 compiled 目录、test-cases 目录、prompts 目录和指南文件
            if ("compiled" in str(md_file) or 
                "test-cases" in str(md_file) or 
                "prompts" in str(md_file) or
                md_file.name == "RULE-GENERATOR-GUIDE.md"):
                continue
            
            status["total_files"] += 1
            rel_path = str(md_file.relative_to(self.specs_dir))
            current_hash = self.compute_file_hash(str(md_file))
            
            if rel_path in manifest:
                cached_hash = manifest[rel_path]["hash"]
                if cached_hash == current_hash:
                    status["cached_files"] += 1
                    status["details"].append({
                        "file": rel_path,
                        "status": "cached",
                        "hash": current_hash[:8]
                    })
                else:
                    status["outdated_files"] += 1
                    status["details"].append({
                        "file": rel_path,
                        "status": "outdated",
                        "hash": current_hash[:8],
                        "cached_hash": cached_hash[:8]
                    })
            else:
                status["outdated_files"] += 1
                status["details"].append({
                    "file": rel_path,
                    "status": "not_compiled",
                    "hash": current_hash[:8]
                })
        
        return status


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="规则预编译器")
    parser.add_argument("--specs-dir", default="references", help="规约目录")
    parser.add_argument("--force", action="store_true", help="强制重新编译所有文件")
    parser.add_argument("--status", action="store_true", help="显示编译状态")
    parser.add_argument("--compile", action="store_true", help="编译所有文件")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    compiler = RuleCompiler(args.specs_dir)
    
    if args.status:
        status = compiler.check_status()
        print(f"\n编译状态:")
        print(f"  总文件数: {status['total_files']}")
        print(f"  已缓存: {status['cached_files']}")
        print(f"  需要更新: {status['outdated_files']}")
        print(f"\n详情:")
        for detail in status["details"]:
            status_icon = "✓" if detail["status"] == "cached" else "✗"
            print(f"  {status_icon} {detail['file']} ({detail['hash']})")
    
    elif args.compile:
        compiler.compile_all(force=args.force)
        print("\n编译完成")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
