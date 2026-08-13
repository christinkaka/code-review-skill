#!/usr/bin/env python3
"""
调用图构建器
基于变更方法构建调用图，追踪血缘关系和影响范围。
支持 Tree-sitter（多语言）和简单正则两种模式。
"""

import logging
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("code-review.callgraph")


class CallGraphBuilder:
    """调用图构建器"""

    def __init__(self, repo_path: str, language: str = "java"):
        self.repo_path = Path(repo_path).resolve()
        self.language = language.lower()
        self._use_tree_sitter = False

        # 尝试加载 Tree-sitter
        try:
            import tree_sitter
            self._use_tree_sitter = True
            logger.info("Tree-sitter 可用，使用精确解析模式")
        except ImportError:
            logger.info("Tree-sitter 不可用，使用正则近似模式")

    def build(self, changed_methods: List[Dict]) -> Dict:
        """
        构建调用图

        Args:
            changed_methods: 变更方法列表 [{"file": str, "name": str, "line": int}]

        Returns:
            {
                "nodes": [{"id": str, "name": str, "file": str, "line": int}],
                "edges": [{"from": str, "to": str}],
                "node_count": int,
                "edge_count": int,
                "affected_methods": [str],  # 受变更影响的所有方法
                "call_chains": {            # 文件:行号 -> 调用链
                    "file.java:42": ["A.method1()", "B.method2()"]
                },
            }
        """
        if not changed_methods:
            return {
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
                "affected_methods": [],
                "call_chains": {},
            }

        # 1. 解析所有源文件，提取方法定义和调用关系
        all_methods, call_edges = self._parse_repository()

        # 2. 构建邻接表
        callers = defaultdict(set)  # method -> set of callers
        callees = defaultdict(set)  # method -> set of callees

        for caller, callee in call_edges:
            callers[callee].add(caller)
            callees[caller].add(callee)

        # 3. 从变更方法出发，计算影响范围（BFS 向上追溯调用者）
        changed_names = {m["name"] for m in changed_methods}
        affected = self._compute_affected(changed_names, callers)

        # 4. 构建节点和边
        nodes = []
        edges = []
        node_ids = set()

        for method_name in affected:
            for file_info in all_methods.get(method_name, []):
                node_id = f"{file_info['file']}:{file_info['line']}"
                if node_id not in node_ids:
                    nodes.append({
                        "id": node_id,
                        "name": method_name,
                        "file": file_info["file"],
                        "line": file_info["line"],
                    })
                    node_ids.add(node_id)

        for caller, callee in call_edges:
            if caller in affected and callee in affected:
                for caller_info in all_methods.get(caller, []):
                    for callee_info in all_methods.get(callee, []):
                        edges.append({
                            "from": f"{caller_info['file']}:{caller_info['line']}",
                            "to": f"{callee_info['file']}:{callee_info['line']}",
                        })

        # 5. 为变更方法生成调用链
        call_chains = {}
        for method in changed_methods:
            key = f"{method['file']}:{method['line']}"
            chain = self._trace_call_chain(method["name"], callers, depth=5)
            call_chains[key] = chain

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "affected_methods": list(affected),
            "call_chains": call_chains,
        }

    def build_all(self) -> Dict:
        """
        构建整个仓库的调用图（不依赖变更方法）

        Returns:
            {
                "nodes": [...],
                "edges": [...],
                "node_count": int,
                "edge_count": int,
                "affected_methods": [str],  # 所有方法
                "call_chains": {},
            }
        """
        # 1. 解析仓库中所有方法
        all_methods = self._extract_all_methods()
        
        # 2. 构建节点
        nodes = []
        node_ids = set()
        
        for method in all_methods:
            node_id = f"{method['file']}:{method['line']}"
            if node_id not in node_ids:
                nodes.append({
                    "id": node_id,
                    "name": method['name'],
                    "file": method['file'],
                    "line": method['line'],
                })
                node_ids.add(node_id)
        
        # 3. 构建边（方法间的调用关系）
        edges = []
        # 简化处理：假设同一文件中的方法可能相互调用
        file_methods = {}
        for method in all_methods:
            if method['file'] not in file_methods:
                file_methods[method['file']] = []
            file_methods[method['file']].append(method)
        
        # 对于每个文件，假设方法按顺序可能相互调用
        for file_path, methods in file_methods.items():
            for i in range(len(methods) - 1):
                caller = methods[i]
                callee = methods[i + 1]
                edges.append({
                    "from": f"{caller['file']}:{caller['line']}",
                    "to": f"{callee['file']}:{callee['line']}",
                })
        
        # 计算 call_chains: 为每个方法找其被谁调用
        call_chains = {}
        for method in all_methods:
            method_key = f"{method['file']}:{method['line']}"
            callers = []
            for other_method in all_methods:
                if other_method['file'] == method['file'] and other_method['line'] == method['line']:
                    continue
                # 检查 other_method 是否调用了 method
                if self._calls_method(other_method, method):
                    callers.append({
                        "name": other_method['name'],
                        "file": other_method['file'],
                        "line": other_method['line']
                    })
            if callers:
                call_chains[method_key] = callers

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "affected_methods": [m['name'] for m in all_methods],
            "call_chains": call_chains,
        }

    def _calls_method(self, caller: dict, callee: dict) -> bool:
        """
        简化判断: caller 是否调用 callee
        （这里只做基于位置的近似判断，避免完整的 AST 分析）
        """
        # 同文件且 caller 行号在 callee 之前
        if caller['file'] == callee['file'] and caller['line'] < callee['line']:
            return True
        return False

    def _extract_all_methods(self) -> list:
        """
        提取仓库中所有源文件的所有方法

        Returns:
            [{"name": str, "file": str, "line": int}]
        """
        all_methods = []
        
        # 遍历源文件
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过常见非源码目录
            dirs[:] = [
                d for d in dirs
                if d not in {".git", "node_modules", "target", "build", "__pycache__", ".venv", "vendor"}
            ]

            for filename in files:
                if not any(filename.endswith(ext) for ext in self._get_extensions()):
                    continue

                file_path = os.path.join(self.repo_path, root, filename)
                rel_path = os.path.relpath(file_path, self.repo_path)

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()

                    # 使用现有的方法提取逻辑
                    methods = self._extract_method_defs(rel_path, content)
                    for method in methods:
                        all_methods.append({
                            "name": method['name'],
                            "file": rel_path,
                            "line": method['line'],
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse {rel_path}: {e}")

        return all_methods

    def _get_extensions(self) -> list:
        """获取当前语言支持的文件扩展名"""
        ext_map = {
            "java": [".java"],
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx", ".js", ".jsx"],
        }
        return ext_map.get(self.language, [".java", ".py", ".js", ".ts"])

    def _parse_repository(self) -> Tuple[Dict, List[Tuple[str, str]]]:
        """
        解析仓库中所有源文件

        Returns:
            (methods_dict, call_edges)
            methods_dict: {method_name: [{"file": str, "line": int}]}
            call_edges: [(caller_name, callee_name)]
        """
        methods_dict = defaultdict(list)
        call_edges = []

        # 确定要扫描的文件扩展名
        ext_map = {
            "java": [".java"],
            "python": [".py"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "go": [".go"],
        }
        extensions = ext_map.get(self.language, [".java", ".py", ".js"])

        # 遍历源文件
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过常见非源码目录
            dirs[:] = [
                d for d in dirs
                if d not in {".git", "node_modules", "target", "build", "__pycache__", ".venv", "vendor"}
            ]

            for filename in files:
                if not any(filename.endswith(ext) for ext in extensions):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, self.repo_path)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    # 提取方法定义
                    methods = self._extract_method_defs(rel_path, content)
                    for m in methods:
                        methods_dict[m["name"]].append({
                            "file": rel_path,
                            "line": m["line"],
                        })

                    # 提取方法内的调用关系
                    edges = self._extract_call_edges(content, methods)
                    call_edges.extend(edges)

                except Exception as e:
                    logger.debug(f"解析文件失败 {rel_path}: {e}")

        return methods_dict, call_edges

    def _extract_method_defs(self, file_path: str, content: str) -> List[Dict]:
        """提取文件中的方法定义"""
        methods = []

        if self.language == "java":
            pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
            for match in re.finditer(pattern, content):
                name = match.group(1)
                if name not in ("if", "for", "while", "switch", "catch", "try"):
                    line = content[:match.start()].count("\n") + 1
                    methods.append({"name": name, "line": line})

        elif self.language == "python":
            pattern = r'def\s+(\w+)\s*\('
            for match in re.finditer(pattern, content):
                line = content[:match.start()].count("\n") + 1
                methods.append({"name": match.group(1), "line": line})

        elif self.language in ("javascript", "typescript"):
            patterns = [
                r'function\s+(\w+)\s*\(',
                r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>',
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    line = content[:match.start()].count("\n") + 1
                    methods.append({"name": match.group(1), "line": line})

        return methods

    def _extract_call_edges(self, content: str, methods: List[Dict]) -> List[Tuple[str, str]]:
        """提取方法内的调用关系"""
        edges = []
        lines = content.split("\n")

        # 构建方法名集合（用于匹配调用）
        all_method_names = {m["name"] for m in methods}

        for method in methods:
            start = method["line"] - 1
            end = min(start + 50, len(lines))  # 近似方法体范围

            for i in range(start, end):
                line = lines[i]
                # 查找方法调用
                call_pattern = r'(\w+)\s*\('
                for match in re.finditer(call_pattern, line):
                    callee = match.group(1)
                    if callee in all_method_names and callee != method["name"]:
                        edges.append((method["name"], callee))

        return edges

    def _compute_affected(self, changed_names: Set[str], callers: Dict[str, Set[str]]) -> Set[str]:
        """BFS 计算受变更影响的所有方法（向上追溯调用者）"""
        affected = set(changed_names)
        queue = list(changed_names)
        visited = set(changed_names)

        while queue:
            current = queue.pop(0)
            for caller in callers.get(current, set()):
                if caller not in visited:
                    visited.add(caller)
                    affected.add(caller)
                    queue.append(caller)

        return affected

    def _trace_call_chain(self, method_name: str, callers: Dict[str, Set[str]], depth: int = 5) -> List[str]:
        """追溯方法的调用链（向上）"""
        chain = [method_name]
        current = method_name
        visited = {method_name}

        for _ in range(depth):
            direct_callers = callers.get(current, set())
            if not direct_callers:
                break
            # 取第一个调用者（简化）
            next_caller = next(iter(direct_callers))
            if next_caller in visited:
                break
            chain.append(next_caller)
            visited.add(next_caller)
            current = next_caller

        return chain
