#!/usr/bin/env python3
"""
内置引擎 V2 - 基于 Tree-sitter AST 的安全规则扫描器

相比 V1 正则引擎的改进：
1. 基于 AST 精确匹配，不依赖正则转换
2. 支持多行模式（通过 AST 结构自然支持）
3. 支持控制流分析（if/else 分支检测）
4. 显著减少误报和漏报

用法:
    python scripts/builtin_engine_v2.py --repo /path/to/repo [--output report.json]
"""

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("code-review.builtin-v2")

# ============================================================
# Tree-sitter AST 引擎
# ============================================================

try:
    import tree_sitter
    try:
        import tree_sitter_java
        JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
    except ImportError:
        JAVA_LANGUAGE = None
    TS_AVAILABLE = True
except ImportError:
    TS_AVAILABLE = False
    JAVA_LANGUAGE = None


class ASTNode:
    """Tree-sitter 节点的简化包装"""

    def __init__(self, node, source_bytes: bytes):
        self._node = node
        self._source = source_bytes
        self.type = node.type
        self.start_point = node.start_point  # (row, col)
        self.end_point = node.end_point
        self.start_byte = node.start_byte
        self.end_byte = node.end_byte
        self.text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @property
    def line(self):
        return self.start_point[0] + 1

    @property
    def children(self):
        return [ASTNode(c, self._source) for c in self._node.children]

    def find_children_by_type(self, node_type: str) -> List["ASTNode"]:
        return [c for c in self.children if c.type == node_type]

    def find_descendants_by_type(self, node_type: str) -> List["ASTNode"]:
        result = []
        for child in self.children:
            if child.type == node_type:
                result.append(child)
            result.extend(child.find_descendants_by_type(node_type))
        return result

    def has_method_call(self, method_name: str) -> bool:
        for inv in self.find_descendants_by_type("method_invocation"):
            name_node = inv.find_children_by_type("identifier")
            if name_node and name_node[0].text == method_name:
                return True
        return False

    def get_method_name(self) -> str:
        for child in self.children:
            if child.type == "identifier":
                return child.text
        name_node = self.find_children_by_type("identifier")
        if name_node:
            return name_node[0].text
        return ""


class SecurityRule:
    """安全规则基类"""

    def __init__(self, rule_id: str, severity: str, message: str,
                 languages: List[str] = None, cwe: str = ""):
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.languages = languages if languages is not None else ["java"]
        self.cwe = cwe

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        raise NotImplementedError


# ============================================================
# 具体安全规则实现
# ============================================================

class XXEDocumentBuilderRule(SecurityRule):
    """XXE: DocumentBuilderFactory 未禁用外部实体"""

    def __init__(self):
        super().__init__(
            rule_id="xxe-java-document-builder-usage",
            severity="ERROR",
            message="[XXE] DocumentBuilderFactory 未禁用外部实体，存在 XXE 注入风险。",
            cwe="CWE-611",
        )

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        for inv in root.find_descendants_by_type("method_invocation"):
            method_name = inv.get_method_name()
            if method_name == "newInstance":
                obj = inv.find_children_by_type("identifier")
                if obj and "DocumentBuilderFactory" in obj[0].text:
                    parent_method = self._find_enclosing_method(inv)
                    if parent_method:
                        has_disallow = "disallow-doctype-decl" in parent_method.text
                        if not has_disallow:
                            issues.append(self._make_issue(inv, file_path))
            elif method_name == "newDocumentBuilder":
                parent_method = self._find_enclosing_method(inv)
                if parent_method and "disallow-doctype-decl" not in parent_method.text:
                    class_node = self._find_enclosing_class(inv)
                    if class_node and "disallow-doctype-decl" not in class_node.text:
                        issues.append(self._make_issue(inv, file_path))
        return issues

    def _find_enclosing_method(self, node: ASTNode) -> Optional[ASTNode]:
        current = node
        while current:
            if current.type in ("method_declaration", "constructor_declaration"):
                return current
            current = getattr(current, '_parent', None)
        return None

    def _find_enclosing_class(self, node: ASTNode) -> Optional[ASTNode]:
        current = node
        while current:
            if current.type in ("class_declaration",):
                return current
            current = getattr(current, '_parent', None)
        return None

    def _make_issue(self, node: ASTNode, file_path: str) -> Dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "file": file_path,
            "line": node.line,
            "end_line": node.end_point[0] + 1,
            "code_snippet": node.text[:200],
            "engine": "builtin-v2",
            "cwe": self.cwe,
        }


class SignatureBypassVersionRule(SecurityRule):
    """签名绕过: 版本检查跳过签名验证"""

    def __init__(self):
        super().__init__(
            rule_id="sig-bypass-version-skip",
            severity="CRITICAL",
            message="[签名绕过] 基于协议版本的条件分支跳过签名验证。",
            cwe="CWE-345",
        )

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        for if_stmt in root.find_descendants_by_type("if_statement"):
            condition = if_stmt.find_children_by_type("parenthesized_expression")
            if not condition:
                continue
            cond_text = condition[0].text

            version_patterns = [
                r'\w*[Vv]ersion\w*\s*[<>=!]+\s*\d+',
                r'\w*[Vv]ersion\w*\s*==\s*\d+',
                r'check[Vv]ersion\w*\s*[<>=!]+\s*\d+',
            ]

            is_version_check = False
            for pat in version_patterns:
                if re.search(pat, cond_text):
                    is_version_check = True
                    break

            if not is_version_check:
                continue

            consequence = if_stmt.find_children_by_type("block")
            if consequence:
                block_text = consequence[0].text
                has_verify = any(kw in block_text for kw in [
                    "verifySignature", "checkHeaderSign", "verify",
                    "checkSign", "validateSignature", "verifyDataStr",
                ])
                if not has_verify:
                    issues.append({
                        "rule_id": self.rule_id,
                        "severity": self.severity,
                        "message": self.message,
                        "file": file_path,
                        "line": if_stmt.line,
                        "end_line": if_stmt.end_point[0] + 1,
                        "code_snippet": if_stmt.text[:300],
                        "engine": "builtin-v2",
                        "cwe": self.cwe,
                    })

        return issues


class PathTraversalRule(SecurityRule):
    """路径穿越: 文件操作未验证路径"""

    def __init__(self):
        super().__init__(
            rule_id="path-traversal-file-ops",
            severity="ERROR",
            message="[路径穿越] 文件操作使用外部输入路径，可能存在路径穿越风险。",
            cwe="CWE-22",
        )

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        for inv in root.find_descendants_by_type("method_invocation"):
            method_name = inv.get_method_name()
            if method_name in ("read", "write", "parse", "load"):
                args = inv.find_children_by_type("argument_list")
                if args:
                    arg_text = args[0].text
                    if any(v in arg_text for v in ["request", "param", "header", "getHeader", "getParameter"]):
                        issues.append({
                            "rule_id": self.rule_id,
                            "severity": self.severity,
                            "message": self.message,
                            "file": file_path,
                            "line": inv.line,
                            "end_line": inv.end_point[0] + 1,
                            "code_snippet": inv.text[:200],
                            "engine": "builtin-v2",
                            "cwe": self.cwe,
                        })

        for obj in root.find_descendants_by_type("object_creation_expression"):
            text = obj.text
            if "new File(" in text or "new FileInputStream(" in text:
                args = obj.find_children_by_type("argument_list")
                if args:
                    arg_text = args[0].text
                    if any(v in arg_text for v in ["request", "param", "header", "getHeader", "getParameter", "path"]):
                        if ".." not in text and "normalize" not in text:
                            issues.append({
                                "rule_id": self.rule_id,
                                "severity": self.severity,
                                "message": self.message,
                                "file": file_path,
                                "line": obj.line,
                                "end_line": obj.end_point[0] + 1,
                                "code_snippet": obj.text[:200],
                                "engine": "builtin-v2",
                                "cwe": self.cwe,
                            })

        return issues


class RuntimeExecRule(SecurityRule):
    """命令注入: Runtime.exec() 使用外部输入"""

    def __init__(self):
        super().__init__(
            rule_id="priv-java-runtime-exec",
            severity="ERROR",
            message="[命令注入] Runtime.exec() 可能执行外部输入的命令。",
            cwe="CWE-78",
        )

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        for inv in root.find_descendants_by_type("method_invocation"):
            method_name = inv.get_method_name()
            if method_name == "exec":
                obj_nodes = inv.find_children_by_type("identifier")
                is_runtime = any(n.text == "Runtime" or n.text == "runtime" for n in obj_nodes)
                if is_runtime or "Runtime" in inv.text:
                    issues.append({
                        "rule_id": self.rule_id,
                        "severity": self.severity,
                        "message": self.message,
                        "file": file_path,
                        "line": inv.line,
                        "end_line": inv.end_point[0] + 1,
                        "code_snippet": inv.text[:200],
                        "engine": "builtin-v2",
                        "cwe": self.cwe,
                    })
        return issues


class HardcodedSecretRule(SecurityRule):
    """硬编码密钥: SecretKeySpec 使用字符串常量"""

    def __init__(self):
        super().__init__(
            rule_id="sig-java-hardcoded-key",
            severity="ERROR",
            message="[硬编码密钥] 签名密钥硬编码在源码中。",
            cwe="CWE-798",
        )

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        for obj in root.find_descendants_by_type("object_creation_expression"):
            if "SecretKeySpec" in obj.text:
                string_literals = obj.find_descendants_by_type("string_literal")
                if string_literals:
                    issues.append({
                        "rule_id": self.rule_id,
                        "severity": self.severity,
                        "message": self.message,
                        "file": file_path,
                        "line": obj.line,
                        "end_line": obj.end_point[0] + 1,
                        "code_snippet": obj.text[:200],
                        "engine": "builtin-v2",
                        "cwe": self.cwe,
                    })
        return issues


class WeakSignatureAlgorithmRule(SecurityRule):
    """弱签名算法: 使用 MD5withRSA"""

    def __init__(self):
        super().__init__(
            rule_id="sig-java-weak-algorithm",
            severity="ERROR",
            message="[签名绕过] 使用 MD5withRSA 签名算法，MD5 已被证明不安全。",
            cwe="CWE-328",
        )

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        for inv in root.find_descendants_by_type("method_invocation"):
            if inv.get_method_name() == "getInstance":
                args = inv.find_children_by_type("argument_list")
                if args and "MD5withRSA" in args[0].text:
                    issues.append({
                        "rule_id": self.rule_id,
                        "severity": self.severity,
                        "message": self.message,
                        "file": file_path,
                        "line": inv.line,
                        "end_line": inv.end_point[0] + 1,
                        "code_snippet": inv.text[:200],
                        "engine": "builtin-v2",
                        "cwe": self.cwe,
                    })
        return issues


# ============================================================
# 正则补充规则（用于 Tree-sitter 不易匹配的模式）
# ============================================================

class RegexSupplementRule(SecurityRule):
    """正则补充规则 - 用于 AST 不易匹配但正则高效的模式"""

    def __init__(self, rule_id: str, severity: str, message: str,
                 regex: str, cwe: str = "", languages: List[str] = None):
        super().__init__(rule_id, severity, message, languages, cwe)
        self.regex = re.compile(regex, re.DOTALL | re.MULTILINE)

    def check(self, root: ASTNode, file_path: str) -> List[Dict]:
        issues = []
        source = root._source.decode("utf-8", errors="replace")
        for match in self.regex.finditer(source):
            line_no = source[:match.start()].count("\n") + 1
            end_line = source[:match.end()].count("\n") + 1
            issues.append({
                "rule_id": self.rule_id,
                "severity": self.severity,
                "message": self.message,
                "file": file_path,
                "line": line_no,
                "end_line": end_line,
                "code_snippet": match.group(0)[:200],
                "engine": "builtin-v2",
                "cwe": self.cwe,
            })
        return issues

    def check_regex(self, content: str, file_path: str) -> List[Dict]:
        issues = []
        for match in self.regex.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            end_line = content[:match.end()].count("\n") + 1
            issues.append({
                "rule_id": self.rule_id,
                "severity": self.severity,
                "message": self.message,
                "file": file_path,
                "line": line_no,
                "end_line": end_line,
                "code_snippet": match.group(0)[:200],
                "engine": "builtin-v2",
                "cwe": self.cwe,
            })
        return issues


# ============================================================
# 主扫描引擎
# ============================================================

class BuiltinEngineV2:
    """内置引擎 V2 - 结合 AST 和正则的混合扫描器"""

    def __init__(self):
        self.use_tree_sitter = TS_AVAILABLE and JAVA_LANGUAGE is not None
        self.rules: List[SecurityRule] = []
        self._init_rules()

    def _init_rules(self):
        """初始化所有安全规则"""
        if self.use_tree_sitter:
            # AST 规则
            self.rules.append(XXEDocumentBuilderRule())
            self.rules.append(SignatureBypassVersionRule())
            self.rules.append(PathTraversalRule())
            self.rules.append(RuntimeExecRule())
            self.rules.append(HardcodedSecretRule())
            self.rules.append(WeakSignatureAlgorithmRule())

        # 正则补充规则（无论 Tree-sitter 是否可用都生效）
        self.rules.append(RegexSupplementRule(
            rule_id="sig-bypass-version-check-regex",
            severity="WARNING",
            message="[签名绕过] 版本检查条件分支可能跳过签名验证。",
            regex=r'if\s*\(\s*\w*[Vv]ersion\w*\s*[<>=!]+\s*\d+\s*\)\s*\{',
            cwe="CWE-345",
            languages=["java"],
        ))
        # path-traversal-pattern 规则已禁用（2026-08-26）
        # 原因：匹配字面量 "../" 等字符串在相对导入、path.join 等安全场景产生大量 FP
        # 替代方案：使用数据流分析规则 path-traversal-taint (Java) 或 path-python-open/path-js-readfile (Python/JS)
        # self.rules.append(RegexSupplementRule(
        #     rule_id="path-traversal-pattern",
        #     severity="WARNING",
        #     message="[路径穿越] 检测到路径穿越相关模式。",
        #     regex=r'(?:\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f)',
        #     cwe="CWE-22",
        #     languages=[],
        # ))
        self.rules.append(RegexSupplementRule(
            rule_id="sqli-mybatis-dollar",
            severity="ERROR",
            message="[SQL 注入] MyBatis 使用 ${} 直接拼接 SQL，存在注入风险。",
            regex=r'\$\{[^}]+\}',
            cwe="CWE-89",
            languages=["xml"],
        ))
        self.rules.append(RegexSupplementRule(
            rule_id="hardcoded-password",
            severity="ERROR",
            message="[硬编码密码] 代码中包含疑似硬编码的密码或密钥。",
            regex=r'(?:password|passwd|secret|api_key|apikey)\s*=\s*["\'][^"\']{4,}["\']',
            cwe="CWE-798",
            languages=[],
        ))

    def scan_file(self, file_path: str) -> List[Dict]:
        """扫描单个文件"""
        try:
            with open(file_path, "rb") as f:
                source = f.read()
        except Exception as e:
            logger.debug(f"读取文件失败 {file_path}: {e}")
            return []

        ext = Path(file_path).suffix.lower()
        issues = []

        # 确定语言
        lang_map = {".java": "java", ".py": "python", ".js": "javascript",
                    ".ts": "typescript", ".xml": "xml", ".md": "markdown"}
        file_lang = lang_map.get(ext, "")

        # AST 扫描（仅 Java）
        if self.use_tree_sitter and file_lang == "java":
            try:
                parser = tree_sitter.Parser(JAVA_LANGUAGE)
                tree = parser.parse(source)
                root = ASTNode(tree.root_node, source)
                # 设置父节点引用
                self._set_parents(tree.root_node)

                for rule in self.rules:
                    if file_lang in rule.languages or not rule.languages:
                        found = rule.check(root, file_path)
                        issues.extend(found)
            except Exception as e:
                logger.debug(f"AST 解析失败 {file_path}: {e}")

        # 正则补充扫描（所有语言）
        try:
            content = source.decode("utf-8", errors="replace")
            file_name = Path(file_path).name.lower()
            for rule in self.rules:
                if isinstance(rule, RegexSupplementRule):
                    if file_lang in rule.languages or not rule.languages:
                        # 排除 pom.xml（Maven 属性插值不是 MyBatis SQL）
                        if rule.rule_id == "sqli-mybatis-dollar" and file_name == "pom.xml":
                            continue
                        found = rule.check_regex(content, file_path)
                        issues.extend(found)
        except Exception as e:
            logger.debug(f"正则扫描失败 {file_path}: {e}")

        return issues

    def _set_parents(self, node):
        """为所有节点设置父节点引用"""
        for child in node.children:
            child._parent = node
            self._set_parents(child)

    def scan_repo(self, repo_path: str) -> Tuple[List[Dict], Dict]:
        """扫描整个仓库"""
        all_issues = []
        stats = {
            "files_scanned": 0,
            "total_time": 0,
            "rules_count": len(self.rules),
        }

        start_time = time.time()
        scan_extensions = {".java", ".py", ".js", ".ts", ".xml", ".jsx", ".tsx"}
        skip_dirs = {".git", "node_modules", "target", "build", "__pycache__",
                     ".venv", "vendor", "dist", ".idea", ".settings"}

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext not in scan_extensions:
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)
                stats["files_scanned"] += 1

                # 使用绝对路径读取文件，但在结果中记录相对路径
                file_issues = self.scan_file(file_path)
                for issue in file_issues:
                    issue["file"] = rel_path

                all_issues.extend(file_issues)

        stats["total_time"] = round(time.time() - start_time, 2)
        return all_issues, stats


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="内置引擎 V2 - AST 安全扫描器")
    parser.add_argument("--repo", required=True, help="仓库路径")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志级别")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=" * 60)
    logger.info("内置引擎 V2 - AST 安全扫描")
    logger.info(f"  仓库: {args.repo}")
    logger.info(f"  Tree-sitter: {'可用' if TS_AVAILABLE else '不可用'}")
    logger.info("=" * 60)

    engine = BuiltinEngineV2()
    issues, stats = engine.scan_repo(args.repo)

    # 统计
    by_severity = {}
    by_rule = {}
    for issue in issues:
        sev = issue.get("severity", "UNKNOWN")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        rid = issue.get("rule_id", "unknown")
        by_rule[rid] = by_rule.get(rid, 0) + 1

    result = {
        "issues": issues,
        "stats": {
            **stats,
            "total_issues": len(issues),
            "by_severity": by_severity,
            "by_rule": by_rule,
        },
    }

    # 输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"结果保存到: {args.output}")

    # 打印摘要
    print(f"\n扫描完成！耗时: {stats['total_time']}s")
    print(f"  扫描文件数: {stats['files_scanned']}")
    print(f"  规则数: {stats['rules_count']}")
    print(f"  检出问题: {len(issues)}")
    print(f"\n按严重级别:")
    for sev, count in sorted(by_severity.items()):
        print(f"  {sev}: {count}")
    print(f"\n按规则:")
    for rid, count in sorted(by_rule.items(), key=lambda x: -x[1]):
        print(f"  {rid}: {count}")


if __name__ == "__main__":
    main()
