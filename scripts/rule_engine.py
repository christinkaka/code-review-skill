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

from rule_sandbox import RuleSandbox

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
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:
        """加载 Profile 中启用的所有规则（从 Markdown 文件解析 + 外部 YAML 规则）"""
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

                # 处理 Markdown 规约文件
                if file_path.endswith(".md"):
                    try:
                        rules = self.md_parser.parse_file(file_path)
                        for rule in rules:
                            # Skip disabled rules
                            if rule.get("enabled") is False:
                                logger.debug(f"跳过已禁用规则: {rule.get('id', 'unknown')}")
                                continue
                            if severity_override:
                                rule["severity"] = severity_override
                            all_rules.append(rule)
                        logger.debug(f"从 {os.path.basename(file_path)} 解析出 {len(rules)} 条规则")
                    except Exception as e:
                        logger.error(f"解析规约文件失败 {file_path}: {e}")

                # 处理外部 YAML 规则文件（从 rule_loader.py 加载）
                elif file_path.endswith((".yaml", ".yml")):
                    try:
                        rules = self._load_yaml_rules(file_path)
                        for rule in rules:
                            if severity_override:
                                rule["severity"] = severity_override
                            all_rules.append(rule)
                        logger.debug(f"从 {os.path.basename(file_path)} 加载 {len(rules)} 条外部规则")
                    except Exception as e:
                        logger.error(f"加载外部规则失败 {file_path}: {e}")

        # 自动扫描 external/ 目录下的所有 YAML 规则
        # （仅当 profile 实际启用规则时：空 specs 是用户的明确意愿，不隐式拉入外部规则）
        profile_specs = (self.profile or {}).get("specs", [])
        external_dir = self.specs_dir / "external"
        if external_dir.exists() and external_dir.is_dir() and profile_specs:
            external_rules = self._load_external_rules(external_dir)
            all_rules.extend(external_rules)
            logger.info(f"从 external/ 目录自动加载 {len(external_rules)} 条外部规则")

        logger.info(f"已加载 {len(all_rules)} 条规则（Markdown + 外部 YAML）")
        return all_rules

    def _load_yaml_rules(self, yaml_file: str) -> List[Dict]:
        """加载单个 YAML 规则文件（Semgrep 格式，含结构校验）"""
        with open(yaml_file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if not isinstance(content, dict) or "rules" not in content:
            return []

        rules = []
        for rule in content.get("rules", []):
            rule_id = rule.get("id")
            if not rule_id:
                continue

            # 结构校验（P2 引擎侧防御）：无效规则不进引擎
            valid, reason = RuleSandbox.validate_structure(rule)
            if not valid:
                logger.warning(f"跳过无效外部规则 {rule_id}: {reason}")
                continue

            # 转换为内部规则格式
            internal_rule = {
                "id": rule_id,
                "message": rule.get("message", f"External rule: {rule_id}"),
                "severity": rule.get("severity", "WARNING"),
                "languages": rule.get("languages", []),
                "patterns": [],
                "metadata": rule.get("metadata", {}),
                "_source_file": os.path.basename(yaml_file),
                "_external": True,  # 标记为外部规则
                "_raw_yaml": rule,  # 保留原始 YAML 供 Semgrep 直接使用
            }

            # 提取 pattern/patterns
            if "pattern" in rule:
                internal_rule["patterns"].append({
                    "type": "pattern",
                    "content": rule["pattern"]
                })
            elif "patterns" in rule:
                for p in rule["patterns"]:
                    if isinstance(p, dict):
                        if "pattern" in p:
                            internal_rule["patterns"].append({
                                "type": "pattern",
                                "content": p["pattern"]
                            })
                        elif "pattern-not" in p:
                            internal_rule["patterns"].append({
                                "type": "pattern-not",
                                "content": p["pattern-not"]
                            })

            rules.append(internal_rule)

        return rules

    def _load_external_rules(self, external_dir: Path) -> List[Dict]:
        """自动加载 external/ 目录下的所有 YAML 规则"""
        all_rules = []
        yaml_files = list(external_dir.glob("*.yaml")) + list(external_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                rules = self._load_yaml_rules(str(yaml_file))
                all_rules.extend(rules)
            except Exception as e:
                logger.warning(f"跳过外部规则文件 {yaml_file}: {e}")

        return all_rules

    # 引擎优先级：AST(3) > Semgrep(2) > Regex(1)
    ENGINE_PRIORITY = {"ast": 3, "semgrep": 2, "regex": 1}

    def run(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """
        执行规则检查（多引擎并行 + 优先级合并）

        引擎策略（对齐 docs/architecture.md 多引擎融合架构）：
        1. Tree-sitter AST 引擎（builtin_engine_v2）：始终执行，最精确，优先级最高
        2. Semgrep 引擎：可用时执行
        3. 内置正则引擎：Semgrep 不可用时执行（离线回退方案）

        合并去重：同一 (rule_id, file, line) 保留最高优先级引擎的检出内容，
        多引擎同时检出时 confidence = 1.0。

        Args:
            repo_path: 仓库路径
            changed_files: 变更文件列表

        Returns:
            问题列表
        """
        if not self.rules:
            logger.warning("无可用规则，跳过检查")
            return []

        engine_results: List[Tuple[str, List[Dict]]] = []

        # [引擎 1/3] Tree-sitter AST（始终执行）
        ast_issues = self._run_with_ast(repo_path, changed_files)
        engine_results.append(("ast", ast_issues))

        # [引擎 2/3] Semgrep（可用时） / [引擎 3/3] 内置正则（回退）
        if self._semgrep_available():
            semgrep_issues = self._run_with_semgrep(repo_path, changed_files)
            engine_results.append(("semgrep", semgrep_issues))
        else:
            logger.info("Semgrep 不可用，启用内置正则引擎（回退方案）")
            regex_issues = self._run_with_builtin(repo_path, changed_files)
            engine_results.append(("regex", regex_issues))

        merged = self._merge_multi_engine(engine_results)
        merged = self._apply_entropy_gate(merged)

        for engine_name, engine_issues in engine_results:
            logger.info(f"{engine_name} 引擎检出 {len(engine_issues)} 个问题")
        multi = sum(1 for i in merged if len(i.get("engines", [])) > 1)
        logger.info(
            f"多引擎合并去重: {sum(len(x[1]) for x in engine_results)} -> {len(merged)} "
            f"(多引擎同时检出 {multi} 个)"
        )
        return merged

    _ENTROPY_GATE_RULE_KEYWORD = "hardcoded"

    def _apply_entropy_gate(self, issues: List[Dict]) -> List[Dict]:
        """对硬编码类规则应用信息论熵门控（数学理论降噪，见 noise_theory.py）

        判决依据：Shannon 熵 + Miller-Madow 修正 + 字符集分层检验，
        全部为确定性函数（同输入同输出），替代经验长度阈值。
        每条被拒绝的检出记录拒绝理由（decision_trace），可审计。
        """
        try:
            from noise_theory import is_high_entropy_secret
        except ImportError:
            return issues

        kept: List[Dict] = []
        gate_stats = {"evaluated": 0, "rejected": 0}
        for issue in issues:
            if self._ENTROPY_GATE_RULE_KEYWORD not in issue.get("rule_id", ""):
                kept.append(issue)
                continue

            snippet = issue.get("code_snippet", "") or ""
            # 提取被赋值的字符串字面量
            literal_match = re.search(r'"([^"]*)"', snippet)
            if not literal_match:
                # 无可评估字面量：保守保留（门控只对可提取字面量的检出生效）
                kept.append(issue)
                continue

            verdict, detail = is_high_entropy_secret(literal_match.group(1))
            gate_stats["evaluated"] += 1
            if verdict:
                issue["entropy"] = detail
                kept.append(issue)
            else:
                gate_stats["rejected"] += 1
                issue["entropy_gate_rejected"] = detail
                logger.debug(
                    f"熵门控拒绝 {issue.get('rule_id')}@{issue.get('file')}:"
                    f"{issue.get('line')} - {detail.get('reason')}"
                )

        if gate_stats["evaluated"]:
            logger.info(
                f"熵门控: 评估 {gate_stats['evaluated']} 条硬编码检出, "
                f"拒绝 {gate_stats['rejected']} 条低熵/占位符"
            )
        return kept

    def _run_with_ast(self, repo_path: str, changed_files: List[Dict]) -> List[Dict]:
        """Tree-sitter AST 引擎（builtin_engine_v2，精确语法分析，优先级最高）"""
        try:
            from builtin_engine_v2 import BuiltinEngineV2
        except ImportError:
            logger.debug("builtin_engine_v2 不可用，跳过 AST 引擎")
            return []

        if not hasattr(self, "_ast_engine"):
            self._ast_engine = BuiltinEngineV2()

        repo = Path(repo_path)
        issues: List[Dict] = []
        for file_info in changed_files:
            file_path = repo / file_info["path"]
            if not file_path.exists():
                continue
            try:
                found = self._ast_engine.scan_file(str(file_path))
            except Exception as e:
                logger.debug(f"AST 扫描失败 {file_info['path']}: {e}")
                continue
            for it in found:
                # 统一为相对路径，与其他引擎对齐
                it["file"] = file_info["path"]
            issues.extend(found)
        return issues

    @classmethod
    def _merge_multi_engine(cls, engine_results: List[Tuple[str, List[Dict]]]) -> List[Dict]:
        """多引擎结果合并去重（优先级 AST > Semgrep > Regex）

        同一 (rule_id, file, line) 被多个引擎检出时：
        - 保留最高优先级引擎的检出内容（覆盖 message/severity 等）
        - engines 列表记录所有检出该位置的引擎
        - confidence = 贝叶斯后验 P(TP|引擎一致检出)（校准概率，
          见 noise_theory.engine_agreement_posterior，替代任意常数）
        """
        try:
            from noise_theory import engine_agreement_posterior
        except ImportError:
            engine_agreement_posterior = None

        ordered = sorted(
            engine_results, key=lambda kv: cls.ENGINE_PRIORITY.get(kv[0], 0)
        )
        merged: Dict[str, Dict] = {}
        for engine_name, engine_issues in ordered:
            for issue in engine_issues:
                key = f"{issue.get('rule_id', '')}:{issue.get('file', '')}:{issue.get('line', 0)}"
                issue["engine"] = engine_name
                if key in merged:
                    existing = merged[key]
                    engines = existing.setdefault("engines", [])
                    if engine_name not in engines:
                        engines.append(engine_name)
                    # 高优先级引擎（后处理）的检出内容覆盖低优先级
                    existing.update({k: v for k, v in issue.items() if k != "engines"})
                    existing["engines"] = engines
                    if engine_agreement_posterior is not None:
                        existing["confidence"] = engine_agreement_posterior(engines)
                else:
                    issue["engines"] = [engine_name]
                    if engine_agreement_posterior is not None:
                        issue["confidence"] = engine_agreement_posterior([engine_name])
                    merged[key] = issue
        return list(merged.values())

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

        # 如果有 pattern-regex，直接使用
        if pattern_regex:
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

            has_positive_pattern = any(
                p.get("type") in ("pattern", "pattern-regex")
                for p in rule["patterns"]
            )
            if not has_positive_pattern:
                logger.debug(
                    f"跳过无正向 pattern 的规则 {rule.get('id')}（仅有 pattern-not）"
                )
                continue

            languages = rule.get("languages", ["java"])

            if len(languages) <= 1:
                semgrep_rule = self._build_semgrep_rule(rule, languages)
                semgrep_rules["rules"].append(semgrep_rule)
            else:
                for lang in languages:
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

            # P0-2 修复: 基于 (rule_id, file, line) 去重
            seen = set()
            deduped = []
            for issue in issues:
                key = (issue["rule_id"], issue["file"], issue["line"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(issue)
            
            if len(deduped) < len(issues):
                logger.info(f"去重: {len(issues)} -> {len(deduped)} (移除 {len(issues) - len(deduped)} 个重复)")
            
            logger.info(f"Semgrep 扫描完成，发现 {len(deduped)} 个问题")
            return deduped

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
        # 将模式中的固定空白灵活化（允许不同缩进）
        # 注意：re.escape 会把空格转义为 "\ "（反斜杠+空格），
        # 必须匹配转义后的空格序列，否则会产生 "\\s" 双反斜杠导致永远无法匹配
        # （2026-08-24 P0 修复：此前 V1 正则引擎对含空格 pattern 全部静默失配）
        regex = re.sub(r'(?<!\n)(?:\\ )+', r'\\s+', regex)
        # 将换行灵活化（re.escape 把 "\n" 转为 反斜杠+真实换行，统一替换为 \s+）
        regex = re.sub(r'\\\n', r'\\s+', regex)
        # 兼容字面量 \n 写法
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
