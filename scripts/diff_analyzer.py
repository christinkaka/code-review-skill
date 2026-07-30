#!/usr/bin/env python3
"""
分支差异分析器
提取两个分支之间的代码差异，包括变更文件、变更方法、变更行等。
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("code-review.diff")


class DiffAnalyzer:
    """分支差异分析器"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self._repo = None

    @property
    def repo(self):
        """延迟加载 Git 仓库"""
        if self._repo is None:
            try:
                import git
                self._repo = git.Repo(str(self.repo_path))
            except ImportError:
                logger.warning("GitPython 未安装，使用命令行 git 作为后备")
                self._repo = None
            except Exception as e:
                logger.error(f"无法打开 Git 仓库: {e}")
                raise
        return self._repo

    def analyze(self, base_branch: str, target_branch: str) -> Dict:
        """
        分析两个分支之间的差异

        Returns:
            {
                "changed_files": [{"path": str, "status": str, "additions": int, "deletions": int}],
                "changed_methods": [{"file": str, "name": str, "line": int, "end_line": int}],
                "diff_text": str,
                "stats": {"files_changed": int, "insertions": int, "deletions": int},
            }
        """
        if self.repo:
            return self._analyze_with_gitpython(base_branch, target_branch)
        else:
            return self._analyze_with_cli(base_branch, target_branch)

    def _analyze_with_gitpython(self, base_branch: str, target_branch: str) -> Dict:
        """使用 GitPython 分析差异"""
        import git

        repo = self.repo

        try:
            base_commit = repo.commit(base_branch)
            target_commit = repo.commit(target_branch)
        except git.exc.BadName as e:
            logger.error(f"分支引用无效: {e}")
            raise ValueError(f"无法解析分支引用: {e}")

        diff_index = base_commit.diff(target_commit)

        changed_files = []
        diff_text_parts = []

        for diff_item in diff_index:
            file_info = {
                "path": diff_item.b_path or diff_item.a_path,
                "status": self._diff_type(diff_item),
                "additions": 0,
                "deletions": 0,
            }

            # 统计增删行数
            try:
                raw_diff = diff_item.diff.decode("utf-8", errors="replace")
                diff_text_parts.append(raw_diff)
                file_info["additions"] = raw_diff.count("\n+") - raw_diff.count("\n+++")
                file_info["deletions"] = raw_diff.count("\n-") - raw_diff.count("\n---")
            except Exception:
                pass

            changed_files.append(file_info)

        # 提取变更方法
        changed_methods = self._extract_changed_methods(diff_index, target_commit)

        return {
            "changed_files": changed_files,
            "changed_methods": changed_methods,
            "diff_text": "\n".join(diff_text_parts),
            "stats": {
                "files_changed": len(changed_files),
                "insertions": sum(f["additions"] for f in changed_files),
                "deletions": sum(f["deletions"] for f in changed_files),
            },
        }

    def _analyze_with_cli(self, base_branch: str, target_branch: str) -> Dict:
        """使用命令行 git 分析差异（后备方案）"""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", f"{base_branch}..{target_branch}", "--stat"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 解析 --stat 输出
            changed_files = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line and not line.startswith(" "):
                    parts = line.split("|")
                    if len(parts) >= 2:
                        path = parts[0].strip()
                        changed_files.append({
                            "path": path,
                            "status": "modified",
                            "additions": 0,
                            "deletions": 0,
                        })

            # 获取完整 diff
            diff_result = subprocess.run(
                ["git", "diff", f"{base_branch}..{target_branch}"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "changed_files": changed_files,
                "changed_methods": self._extract_methods_from_diff(diff_result.stdout),
                "diff_text": diff_result.stdout,
                "stats": {
                    "files_changed": len(changed_files),
                    "insertions": 0,
                    "deletions": 0,
                },
            }
        except Exception as e:
            logger.error(f"Git CLI 分析失败: {e}")
            return {
                "changed_files": [],
                "changed_methods": [],
                "diff_text": "",
                "stats": {"files_changed": 0, "insertions": 0, "deletions": 0},
            }

    def _diff_type(self, diff_item) -> str:
        """判断 diff 类型"""
        if diff_item.new_file:
            return "added"
        elif diff_item.deleted_file:
            return "deleted"
        elif diff_item.renamed_file:
            return "renamed"
        else:
            return "modified"

    def _extract_changed_methods(self, diff_index, target_commit) -> List[Dict]:
        """从 diff 中提取变更的方法/函数"""
        changed_methods = []

        for diff_item in diff_index:
            file_path = diff_item.b_path or diff_item.a_path
            if not file_path:
                continue

            try:
                # 获取目标分支中的文件内容
                blob = target_commit.tree / file_path
                content = blob.data_stream.read().decode("utf-8", errors="replace")
            except Exception:
                continue

            # 根据文件类型提取方法
            methods = self._parse_methods(file_path, content)

            # 获取变更行号
            changed_lines = self._get_changed_lines(diff_item)

            # 过滤出变更行所在的方法
            for method in methods:
                if self._method_overlaps_lines(method, changed_lines):
                    method["file"] = file_path
                    changed_methods.append(method)

        return changed_methods

    def _parse_methods(self, file_path: str, content: str) -> List[Dict]:
        """解析文件中的方法/函数定义"""
        methods = []
        ext = Path(file_path).suffix.lower()

        if ext == ".java":
            # Java 方法匹配
            pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
            for match in re.finditer(pattern, content):
                line_no = content[:match.start()].count("\n") + 1
                methods.append({
                    "name": match.group(1),
                    "line": line_no,
                    "end_line": line_no + 20,  # 近似
                })

        elif ext == ".py":
            # Python 函数匹配
            pattern = r'(?:def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*[\w\[\],\s]+)?\s*:)'
            for match in re.finditer(pattern, content):
                line_no = content[:match.start()].count("\n") + 1
                methods.append({
                    "name": match.group(1),
                    "line": line_no,
                    "end_line": line_no + 30,
                })

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # JavaScript/TypeScript 函数匹配
            patterns = [
                r'(?:function\s+(\w+)\s*\([^)]*\)\s*\{)',
                r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>',
                r'(?:class\s+(\w+))',
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    line_no = content[:match.start()].count("\n") + 1
                    methods.append({
                        "name": match.group(1),
                        "line": line_no,
                        "end_line": line_no + 25,
                    })

        return methods

    def _get_changed_lines(self, diff_item) -> set:
        """获取 diff 中变更的行号集合"""
        changed_lines = set()
        try:
            raw_diff = diff_item.diff.decode("utf-8", errors="replace")
            current_line = 0
            for line in raw_diff.split("\n"):
                if line.startswith("@@"):
                    # 解析 hunk header: @@ -old_start,old_count +new_start,new_count @@
                    match = re.search(r'\+(\d+)', line)
                    if match:
                        current_line = int(match.group(1))
                elif line.startswith("+") and not line.startswith("+++"):
                    changed_lines.add(current_line)
                    current_line += 1
                elif line.startswith("-") and not line.startswith("---"):
                    pass  # 删除行不影响新文件的行号
                else:
                    current_line += 1
        except Exception:
            pass
        return changed_lines

    def _method_overlaps_lines(self, method: Dict, changed_lines: set) -> bool:
        """判断方法是否与变更行有交集"""
        if not changed_lines:
            return True  # 如果没有行信息，保守地认为所有方法都相关
        method_lines = set(range(method["line"], method["end_line"] + 1))
        return bool(method_lines & changed_lines)

    def _extract_methods_from_diff(self, diff_text: str) -> List[Dict]:
        """从 diff 文本中提取变更方法（CLI 后备方案）"""
        methods = []
        current_file = None

        for line in diff_text.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("@@") and current_file:
                match = re.search(r'\+(\d+)', line)
                if match:
                    line_no = int(match.group(1))
                    methods.append({
                        "file": current_file,
                        "name": f"line_{line_no}",
                        "line": line_no,
                        "end_line": line_no + 10,
                    })

        return methods

    def scan_full(self) -> Dict:
        """
        全库扫描模式：收集仓库中所有源文件和方法

        Returns:
            {
                "changed_files": [{"path": str, "status": "unchanged", "additions": 0, "deletions": 0}],
                "changed_methods": [{"file": str, "name": str, "line": int, "end_line": int}],
                "diff_text": "",
                "stats": {"files_changed": int, "insertions": 0, "deletions": 0},
                "mode": "full"
            }
        """
        all_files = []
        all_methods = []
        
        # 遍历仓库所有文件
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过非源码目录
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'target', 'build', 'dist', '.python', 'venv', '.venv', 'env', '.env', 'site-packages', '.python-version', 'vendor', 'third_party', 'third-party']]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.repo_path)
                
                # 只处理源文件
                if not self._is_source_file(file):
                    continue
                
                all_files.append({
                    "path": str(rel_path),
                    "status": "unchanged",
                    "additions": 0,
                    "deletions": 0
                })
                
                # 读取文件并提取方法
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    methods = self._parse_methods(str(rel_path), content)
                    for method in methods:
                        method['file'] = str(rel_path)
                        all_methods.append(method)
                except Exception as e:
                    logger.debug(f"Failed to parse {rel_path}: {e}")
        
        logger.info(f"Full scan: found {len(all_files)} files and {len(all_methods)} methods")
        
        return {
            "changed_files": all_files,
            "changed_methods": all_methods,
            "diff_text": "",
            "stats": {
                "files_changed": len(all_files),
                "insertions": 0,
                "deletions": 0
            },
            "mode": "full"
        }
    
    def _is_source_file(self, filename: str) -> bool:
        """判断是否为源文件"""
        source_extensions = {
            '.java', '.py', '.js', '.jsx', '.ts', '.tsx',
            '.go', '.rs', '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp',
            '.cs', '.swift', '.kt', '.scala', '.rb', '.php'
        }
        ext = Path(filename).suffix.lower()
        return ext in source_extensions
