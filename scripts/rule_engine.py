#!/usr/bin/env python3
"""
规则引擎
从 Markdown 规约文件中解析规则，调用 Semgrep 执行检查，输出结构化问题列表。

Markdown 规约格式约定：
- 每个规则以 # 标题开头
- 规则元数据写在 ```yaml 代码块中（id, languages, severity, cwe 等）
- 检测模式写在 ```pattern 代码块中
- 排除模式写在 ```pattern-not 代码块中
"""

import glob
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger("code-review.rules")


class MarkdownRuleParser:
    """从 Markdown 文件中解析规则"""

    def parse_file(self, file_path: str) -> List[Dict]:
        """
        解析一个 Markdown 文件中的所有规则

        Returns:
            [{"id": str, "languages": list, "severity": str, "message": str,
              "patterns": [{"type": "pattern"|"pattern-not", "content": str}],
              "metadata": dict, "category": str, "fix": str}]
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 按 --- 分隔符拆分规则块（每个规则是一个 section）
        # 也按 # 一级标题拆分
        sections = self._split_sections(content)
        rules = []

        for section in sections:
            rule = self._parse_section(section, file_path)
            if rule and rule.get("id"):
                rules.append(rule)

        return rules

    def _split_sections(self, content: str) -> List[str]:
        """按 --- 分隔符或 # 一级标题拆分 Markdown 内容为多个规则 section"""
        # 优先按 --- 分隔
        if "\n---\n" in content:
            return [s.strip() for s in content.split("\n---\n") if s.strip()]

        # 否则按 # 一级标题拆分
        sections = []
        current = []
        for line in content.split("\n"):
            if line.startswith("# ") and current:
                sections.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append("\n".join(current))

        return sections

    def _parse_section(self, section: str, source_file: str) -> Optional[Dict]:
        """解析单个规则 section

        支持在 ## 检测模式 下使用 ### Java / ### Python / ### Node.js 等
        子标题将 pattern 按语言分组，解析时会为每个 pattern 打上 lang 标签。
        """
        rule = {
            "_source_file": os.path.basename(source_file),
            "patterns": [],
            "metadata": {},
        }

        # 提取标题作为 message
        title_match = re.search(r"^# (.+)$", section, re.MULTILINE)
        if title_match:
            rule["title"] = title_match.group(1).strip()

        # 提取 > 引用作为描述
        desc_match = re.search(r"^> (.+)$", section, re.MULTILINE)
        if desc_match:
            rule["message"] = desc_match.group(1).strip()

        # 子标题到语言的映射
        lang_map = {
            "java": "java",
            "python": "python",
            "node.js": "javascript",
            "nodejs": "javascript",
            "javascript": "javascript",
            "js": "javascript",
            "typescript": "typescript",
            "ts": "typescript",
            "go": "go",
        }

        # 逐行解析，跟踪当前 ### 子标题对应的语言
        current_lang = None
        lines = section.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # ### 子标题：可能指示语言分组
            sub_match = re.match(r"^###\s+(.+)$", line)
            if sub_match:
                heading = sub_match.group(1).strip().lower()
                current_lang = lang_map.get(heading)
                i += 1
                continue

            # ## 标题：重置语言上下文
            if re.match(r"^##\s+", line):
                current_lang = None
                i += 1
                continue

            # 代码块开始
            code_start = re.match(r"^```(\w[\w-]*)\s*$", line)
            if code_start:
                block_type = code_start.group(1).strip().lower()
                block_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    block_lines.append(lines[i])
                    i += 1
                i += 1  # 跳过结束的 ```

                block_content = "\n".join(block_lines).strip()

                if block_type == "yaml":
                    try:
                        meta = yaml.safe_load(block_content)
                        if isinstance(meta, dict):
                            for key in ("id", "languages", "severity", "category", "cwe", "owasp", "fix", "enabled"):
                                if key in meta:
                                    rule[key] = meta[key]
                            rule["metadata"] = {
                                k: v for k, v in meta.items()
                                if k not in ("id", "languages", "severity", "category", "fix")
                            }
                    except yaml.YAMLError:
                        pass

                elif block_type in ("pattern", "pattern-not", "pattern-regex"):
                    entry = {
                        "type": block_type,
                        "content": block_content,
                    }
                    if current_lang:
                        entry["lang"] = current_lang
                    rule["patterns"].append(entry)
            else:
                i += 1

        # 用 title 补充 message（如果没有从 > 引用中获取）
        if not rule.get("message") and rule.get("title"):
            rule["message"] = rule["title"]

        return rule


class RuleEngine:
    """规则引擎 - 从 Markdown 规约加载规则并执行检查"""

    def __init__(self, specs_dir: str, profile: Dict):
        self.specs_dir = Path(specs_dir)
        self.profile = profile
        self.md_parser = MarkdownRuleParser()
        
        # 初始化预编译器
        try:
            from rule_compiler import RuleCompiler
            self.compiler = RuleCompiler(specs_dir)
            self.use_cache = True
        except ImportError:
            self.compiler = None
            self.use_cache = False
        
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:
        """加载 Profile 中启用的所有规则（优先使用预编译缓存）"""
        all_rules = []

        for spec in self.profile.get("specs", []):
            if not spec.get("enabled", True):
                continue

            spec_path = self.specs_dir / spec["path"]
            severity_override = spec.get("severity_override")

            # 支持 glob 模式
            if "*" in str(spec_path):
                matched_files = sorted(glob.glob(str(spec_path)))
            else:
                matched_files = [str(spec_path)]

            for file_path in matched_files:
                if not os.path.exists(file_path):
                    logger.warning(f"规约文件不存在: {file_path}")
                    continue

                if not file_path.endswith(".md"):
                    logger.debug(f"跳过非 Markdown 文件: {file_path}")
                    continue

                try:
                    # 尝试从缓存加载
                    if self.use_cache and self.compiler:
                        rel_path = str(Path(file_path).relative_to(self.specs_dir))
                        manifest = self.compiler.load_manifest()
                        current_hash = self.compiler.compute_file_hash(file_path)
                        
                        if self.compiler.is_cache_valid(rel_path, current_hash, manifest):
                            # 从缓存加载
                            compiled_path = self.compiler.compiled_dir / f"{rel_path}.json"
                            with open(compiled_path, "r", encoding="utf-8") as f:
                                compiled = json.load(f)
                                rules = compiled.get("rules", [])
                                logger.debug(f"从缓存加载 {rel_path} ({len(rules)} 条规则)")
                        else:
                            # 缓存无效，重新解析
                            rules = self.md_parser.parse_file(file_path)
                            logger.debug(f"缓存无效，重新解析 {os.path.basename(file_path)}")
                    else:
                        # 不使用缓存，直接解析
                        rules = self.md_parser.parse_file(file_path)
                    
                    for rule in rules:
                        # Skip disabled rules
                        if rule.get("enabled") is False:
                            logger.debug(f"跳过已禁用规则: {rule.get('id', 'unknown')}")
                            continue
                        if severity_override:
                            rule["severity"] = severity_override
                        all_rules.append(rule)
                    logger.debug(f"从 {os.path.basename(file_path)} 加载 {len(rules)} 条规则")
                except Exception as e:
                    logger.error(f"加载规约文件失败 {file_path}: {e}")

        logger.info(f"已加载 {len(all_rules)} 条规则（从 Markdown 规约）")
        return all_rules

    def run(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """
        执行规则检查

        Args:
            repo_path: 仓库路径
            changed_files: 变更文件列表

        Returns:
            问题列表
        """
        if not self.rules:
            logger.warning("无可用规则，跳过检查")
            return []

        # 尝试使用 Semgrep
        if self._semgrep_available():
            return self._run_with_semgrep(repo_path, changed_files)
        else:
            logger.info("Semgrep 不可用，使用内置模式匹配引擎")
            return self._run_with_builtin(repo_path, changed_files)

    def _semgrep_available(self) -> bool:
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

    def _build_semgrep_rule(self, rule: Dict, languages: List[str], rule_id: str = None) -> Dict:
        """将单条规则转换为 Semgrep 格式（指定语言）

        当 rule 的 patterns 带有 lang 标签时，只选取匹配目标语言的 pattern。
        没有 lang 标签的 pattern 视为通用于所有语言。
        """
        semgrep_rule = {
            "id": rule_id or rule["id"],
            "message": rule.get("message", rule.get("title", "Issue detected")),
            "severity": rule.get("severity", "WARNING"),
            "languages": languages,
        }

        # 按语言过滤 patterns
        target_lang = languages[0] if len(languages) == 1 else None
        filtered_patterns = []
        for p in rule["patterns"]:
            p_lang = p.get("lang")
            # 如果 pattern 有语言标签且与目标语言不匹配，跳过
            if target_lang and p_lang and p_lang != target_lang:
                continue
            filtered_patterns.append(p)

        # 构建 patterns
        pattern_list = []
        pattern_not_list = []
        pattern_regex = None

        for p in filtered_patterns:
            if p["type"] == "pattern":
                pattern_list.append(p["content"])
            elif p["type"] == "pattern-not":
                pattern_not_list.append(p["content"])
            elif p["type"] == "pattern-regex":
                pattern_regex = p["content"]

        # 如果有 pattern-regex，需要与 pattern-not 配合使用 patterns 数组
        if pattern_regex:
            if pattern_not_list:
                # pattern-regex 与 pattern-not 组合使用 patterns 数组
                semgrep_rule["patterns"] = [{"pattern-regex": pattern_regex}]
                for pn in pattern_not_list:
                    semgrep_rule["patterns"].append({"pattern-not": pn})
            else:
                # 单独的 pattern-regex
                semgrep_rule["pattern-regex"] = pattern_regex
        elif len(pattern_list) == 1 and not pattern_not_list:
            semgrep_rule["pattern"] = pattern_list[0]
        elif len(pattern_list) == 1 and pattern_not_list:
            semgrep_rule["patterns"] = [{"pattern": pattern_list[0]}]
            for pn in pattern_not_list:
                semgrep_rule["patterns"].append({"pattern-not": pn})
        elif len(pattern_list) > 1:
            # 多个 pattern 用 pattern-either
            semgrep_rule["patterns"] = [
                {"pattern-either": [{"pattern": p} for p in pattern_list]}
            ]
            for pn in pattern_not_list:
                semgrep_rule["patterns"].append({"pattern-not": pn})

        if "fix" in rule:
            semgrep_rule["fix"] = rule["fix"]
        if rule.get("metadata"):
            semgrep_rule["metadata"] = rule["metadata"]

        return semgrep_rule

    def _rules_to_semgrep(self) -> Dict:
        """将解析出的规则转换为 Semgrep 格式

        对于多语言规则，拆分为每语言一个 Semgrep 规则，
        避免不同语言的 pattern 在 pattern-either 中互相导致解析失败。
        """
        semgrep_rules = {"rules": []}

        for rule in self.rules:
            if not rule.get("patterns"):
                continue

            languages = rule.get("languages", ["java"])

            if len(languages) <= 1:
                # 单语言规则：直接创建
                semgrep_rule = self._build_semgrep_rule(rule, languages)
                semgrep_rules["rules"].append(semgrep_rule)
            else:
                # 多语言规则：为每个语言创建独立的 Semgrep 规则
                # 使用 __{lang} 后缀确保 ID 唯一，后续在结果处理时还原
                for lang in languages:
                    # 检查该语言是否有可用的 pattern（跳过无 pattern 的语言）
                    has_pattern = False
                    for p in rule["patterns"]:
                        p_lang = p.get("lang")
                        if not p_lang or p_lang == lang:
                            has_pattern = True
                            break
                    if not has_pattern:
                        continue

                    suffixed_id = f"{rule['id']}__{lang}"
                    semgrep_rule = self._build_semgrep_rule(rule, [lang], suffixed_id)
                    semgrep_rules["rules"].append(semgrep_rule)

        return semgrep_rules

    def _run_with_semgrep(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """使用 Semgrep 执行规则检查"""
        semgrep_rules = self._rules_to_semgrep()

        if not semgrep_rules["rules"]:
            return []

        # 写入临时规则文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(semgrep_rules, f, default_flow_style=False, allow_unicode=True)
            rules_file = f.name

        try:
            cmd = [
                "semgrep",
                "--config", rules_file,
                "--json",
                "--no-git-ignore",
                "--quiet",
                "--exclude", ".python",
                "--exclude", "venv",
                "--exclude", ".venv",
                "--exclude", "env",
                "--exclude", ".env",
                "--exclude", "site-packages",
                "--exclude", "vendor",
                "--exclude", "third_party",
                "--exclude", "third-party",
                "--exclude", "node_modules",
                "--exclude", "__pycache__",
                "--exclude", "target",
                "--exclude", "build",
                "--exclude", "dist",
                ".",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=repo_path,
            )

            issues = []
            if result.stdout:
                try:
                    semgrep_output = json.loads(result.stdout)
                    # 构建规则 ID 查找表（用于从 check_id 中提取真实 rule_id）
                    known_rule_ids = {r["id"] for r in self.rules if r.get("id")}
                    for finding in semgrep_output.get("results", []):
                        raw_check_id = finding.get("check_id", "")
                        # Semgrep 的 check_id 可能包含临时文件路径前缀，如 "var.folders.xxx.xxe-java-document-builder"
                        # 需要提取出真实的 rule_id
                        rule_id = raw_check_id
                        for known_id in known_rule_ids:
                            if raw_check_id == known_id or raw_check_id.endswith("." + known_id):
                                rule_id = known_id
                                break

                        # 处理多语言拆分后的 __{lang} 后缀
                        if rule_id == raw_check_id:
                            for known_id in known_rule_ids:
                                for lang in ["java", "python", "javascript", "typescript", "go"]:
                                    suffixed = f"{known_id}__{lang}"
                                    if raw_check_id == suffixed or raw_check_id.endswith("." + suffixed):
                                        rule_id = known_id
                                        break
                                if rule_id != raw_check_id:
                                    break

                        issue = {
                            "rule_id": rule_id,
                            "category": self._get_category(rule_id),
                            "severity": finding.get("extra", {}).get("severity", "WARNING"),
                            "file": finding.get("path", ""),
                            "line": finding.get("start", {}).get("line", 0),
                            "end_line": finding.get("end", {}).get("line", 0),
                            "message": finding.get("extra", {}).get("message", ""),
                            "code_snippet": finding.get("extra", {}).get("lines", ""),
                        }

                        # 补充原始规则中的 fix 和 metadata
                        for rule in self.rules:
                            if rule["id"] == issue["rule_id"]:
                                if "fix" in rule:
                                    issue["fix"] = rule["fix"]
                                if rule.get("metadata"):
                                    issue["metadata"] = rule["metadata"]
                                break

                        issues.append(issue)
                except json.JSONDecodeError:
                    logger.error("Semgrep 输出解析失败")

            logger.info(f"Semgrep 扫描完成，发现 {len(issues)} 个问题")
            return issues

        except subprocess.TimeoutExpired:
            logger.error("Semgrep 扫描超时")
            return []
        except Exception as e:
            logger.error(f"Semgrep 扫描失败: {e}")
            return []
        finally:
            os.unlink(rules_file)

    def _run_with_builtin(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """内置模式匹配引擎（Semgrep 不可用时的后备方案）
        
        增强版：支持多行模式匹配、pattern-regex、以及改进的正则转换。
        """
        issues = []
        repo = Path(repo_path)

        for rule in self.rules:
            patterns = rule.get("patterns", [])
            if not patterns:
                continue

            # 分离 pattern、pattern-not、pattern-regex
            pattern_contents = []
            pattern_not_contents = []
            pattern_regex = None

            for p in patterns:
                if p["type"] == "pattern":
                    pattern_contents.append(p["content"])
                elif p["type"] == "pattern-not":
                    pattern_not_contents.append(p["content"])
                elif p["type"] == "pattern-regex":
                    pattern_regex = p["content"]

            # 构建正则表达式列表
            regexes = []
            if pattern_regex:
                # pattern-regex 直接使用
                try:
                    regexes.append(re.compile(pattern_regex, re.DOTALL))
                except re.error:
                    continue
            else:
                # 将 Semgrep 模式转换为正则
                for content in pattern_contents:
                    regex = self._pattern_to_regex_v2(content)
                    if regex:
                        try:
                            regexes.append(re.compile(regex, re.DOTALL))
                        except re.error:
                            continue

            if not regexes:
                continue

            # 构建排除正则列表
            not_regexes = []
            for content in pattern_not_contents:
                not_regex = self._pattern_to_regex_v2(content)
                if not_regex:
                    try:
                        not_regexes.append(re.compile(not_regex, re.DOTALL))
                    except re.error:
                        pass

            languages = rule.get("languages", [])

            for file_info in changed_files:
                file_path = repo / file_info["path"]
                if not file_path.exists():
                    continue

                ext = file_path.suffix.lower()
                if not self._language_matches(ext, languages):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    lines = content.split("\n")

                    for regex in regexes:
                        for match in regex.finditer(content):
                            line_no = content[:match.start()].count("\n") + 1
                            matched_text = match.group(0)

                            # 检查是否被 pattern-not 排除
                            excluded = False
                            for not_regex in not_regexes:
                                if not_regex.search(matched_text):
                                    excluded = True
                                    break
                            if excluded:
                                continue

                            # 提取匹配的代码片段（最多 5 行）
                            end_line = min(line_no + 4, len(lines))
                            snippet = "\n".join(lines[line_no - 1:end_line])

                            issues.append({
                                "rule_id": rule["id"],
                                "category": rule.get("category", self._get_category(rule["id"])),
                                "severity": rule.get("severity", "WARNING"),
                                "file": file_info["path"],
                                "line": line_no,
                                "end_line": end_line,
                                "message": rule.get("message", rule.get("title", "")),
                                "code_snippet": snippet,
                                "fix": rule.get("fix", ""),
                                "metadata": rule.get("metadata", {}),
                            })
                except Exception as e:
                    logger.debug(f"文件扫描失败 {file_info['path']}: {e}")

        logger.info(f"内置引擎扫描完成，发现 {len(issues)} 个问题")
        return issues

    def _pattern_to_regex_v2(self, pattern: str) -> Optional[str]:
        """改进版：将 Semgrep 模式转换为正则表达式
        
        支持：
        - $VAR 元变量 -> \\w+
        - ... 通配符 -> [\\s\\S]*?（非贪婪跨行匹配）
        - 多行模式
        - 括号/花括号匹配
        """
        if not pattern or len(pattern) > 1000:
            return None

        # 先清理模式中的多余空白
        pattern = pattern.strip()

        # 转义正则特殊字符（但保留 $ 和 . 用于后续替换）
        regex = pattern
        # 先替换 $VAR 元变量为占位符
        regex = re.sub(r'\$(\w+)', r'__METAVAR_\1__', regex)
        # 替换 ... 为占位符
        regex = regex.replace('...', '__ELLIPSIS__')
        # 转义正则特殊字符
        regex = re.escape(regex)
        # 恢复元变量占位符为正则
        regex = re.sub(r'__METAVAR_(\w+)__', r'\\w+', regex)
        # 恢复省略号为跨行通配
        regex = regex.replace('__ELLIPSIS__', r'[\s\S]*?')
        # 将模式中的固定空白灵活化（允许不同缩进）
        regex = re.sub(r'(?<!\n) +', r'\\s+', regex)
        # 将换行灵活化
        regex = regex.replace(r'\n', r'\s*\n\s*')

        try:
            re.compile(regex)
            return regex
        except re.error:
            return None

    # 向后兼容别名
    _pattern_to_regex = _pattern_to_regex_v2

    def _get_category(self, rule_id: str) -> str:
        """从规则 ID 推断类别"""
        prefixes = {
            "xxe": "security", "xss": "security", "auth": "security",
            "path": "security", "priv": "security", "sig": "security",
            "sqli": "security", "ssrf": "security",
            "arch": "design", "api": "design", "db": "design",
            "naming": "implementation", "err": "implementation",
            "conc": "implementation", "null": "implementation",
            "custom": "custom",
        }
        for prefix, category in prefixes.items():
            if rule_id.startswith(prefix):
                return category
        return "unknown"

    def _language_matches(self, ext: str, languages: List[str]) -> bool:
        """检查文件扩展名是否匹配规则的语言列表"""
        ext_map = {
            ".java": "java", ".py": "python",
            ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".go": "go",
        }
        file_lang = ext_map.get(ext, "")
        return file_lang in languages or not languages
