#!/usr/bin/env python3
"""
外部规则沙箱验证器 (P2)

背景：
从 GitHub 高星仓库加载的外部 Semgrep 规则质量参差（实测 0xdea/raptor
仓库存在无 pattern 字段的规则）。坏规则直接进引擎会导致：
- 引擎报错或静默失效
- 规则清单虚胖（统计失真）
- 报告分级被非标准 severity 破坏

本模块在规则进入引擎前做两道验证：
1. 结构校验（validate_structure）：最小 Semgrep 兼容集
2. 沙箱冒烟（smoke_test）：真实 semgrep 在样本语料上试跑，
   检出 pattern 语法错误与运行时异常
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger("code-review.sandbox")

# Semgrep 规则可用的检测字段
PATTERN_FIELDS = ("pattern", "patterns", "pattern-regex", "pattern-either",
                  "pattern-sources", "pattern-sinks", "pattern-propagators")

# 内部报告系统使用的严重等级
VALID_SEVERITIES = ("ERROR", "WARNING", "INFO")


class RuleSandbox:
    """外部规则沙箱验证器"""

    @staticmethod
    def validate_structure(rule: Dict) -> Tuple[bool, str]:
        """
        结构校验：一条规则可被引擎消费的最小要求。

        Returns:
            (是否有效, 无效原因)；有效时原因为空串
        """
        if not isinstance(rule, dict):
            return False, "rule 不是字典"

        # 1. 必须有 id
        rule_id = rule.get("id")
        if not rule_id or not str(rule_id).strip():
            return False, "缺少 id"

        # 2. 必须有 languages（非空列表）
        languages = rule.get("languages")
        if not languages or not isinstance(languages, list):
            return False, "缺少 languages 或格式非法（需非空列表）"

        # 3. 必须有至少一种检测字段
        has_pattern = False
        for field in PATTERN_FIELDS:
            value = rule.get(field)
            if field == "patterns" and isinstance(value, list):
                if len(value) > 0:
                    has_pattern = True
                    break
            elif value:
                has_pattern = True
                break
        if not has_pattern:
            return False, (
                f"缺少 pattern/patterns/pattern-regex/pattern-either 等检测字段"
            )

        # 4. severity 必须在标准集合内（缺省 WARNING 可接受）
        severity = rule.get("severity", "WARNING")
        if severity not in VALID_SEVERITIES:
            return False, (
                f"severity 非法: {severity}（有效值: {', '.join(VALID_SEVERITIES)}）"
            )

        return True, ""

    def smoke_test(self, rule_file: Path, corpus_dir: str,
                   timeout: int = 30) -> Dict:
        """
        沙箱冒烟：用真实 semgrep 在样本语料上试跑规则文件。

        Args:
            rule_file: 单条规则 YAML 文件（{"rules": [...]} 格式）
            corpus_dir: 样本语料目录
            timeout: semgrep 超时（秒）

        Returns:
            {"status": "ok"|"error", "findings": int, "detail": str}
            - ok: 规则语法合法且成功执行（findings 为语料命中数）
            - error: 语法错误 / semgrep 异常（detail 含原因）
        """
        try:
            cmd = [
                "semgrep",
                "--config", str(rule_file),
                "--json",
                "--quiet",
                str(corpus_dir),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )

            if result.returncode not in (0, 1):
                return {
                    "status": "error",
                    "findings": 0,
                    "detail": (result.stderr or "semgrep 执行失败").strip()[:300],
                }

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "findings": 0,
                    "detail": "semgrep 输出不是合法 JSON",
                }

            # semgrep 的 errors 字段包含非法 pattern 等信息
            errors = data.get("errors", [])
            if errors:
                err_messages = "; ".join(
                    e.get("long_msg", e.get("message", "unknown")) for e in errors
                )
                return {
                    "status": "error",
                    "findings": 0,
                    "detail": f"semgrep 规则错误: {err_messages[:300]}",
                }

            return {
                "status": "ok",
                "findings": len(data.get("results", [])),
                "detail": "",
            }

        except FileNotFoundError:
            return {"status": "error", "findings": 0,
                    "detail": "semgrep 未安装"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "findings": 0,
                    "detail": f"semgrep 超时（>{timeout}s）"}
        except Exception as e:
            return {"status": "error", "findings": 0, "detail": str(e)[:300]}

    def check(self, rule_files: List[Path], corpus_dir: str = None) -> Dict:
        """
        批量校验：结构校验全部规则，corpus_dir 提供时追加沙箱冒烟。

        Returns:
            {
              "total", "valid", "invalid", "smoke_error",
              "quarantined": [{rule_id, file, reason}],
              "results": [{rule_id, file, structure_ok, smoke, reason}]
            }
        """
        quarantined = []
        results = []
        valid_count = 0
        smoke_error_count = 0

        for rule_file in rule_files:
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    content = yaml_safe_load(f)
            except Exception as e:
                quarantined.append({
                    "rule_id": rule_file.stem,
                    "file": str(rule_file),
                    "reason": f"YAML 解析失败: {e}",
                })
                results.append({
                    "rule_id": rule_file.stem, "file": str(rule_file),
                    "structure_ok": False, "smoke": None,
                    "reason": f"YAML 解析失败",
                })
                continue

            rules = content.get("rules", []) if isinstance(content, dict) else []
            if not rules:
                quarantined.append({
                    "rule_id": rule_file.stem,
                    "file": str(rule_file),
                    "reason": "无 rules 字段或为空",
                })
                continue

            for rule in rules:
                rule_id = rule.get("id", rule_file.stem)
                ok, reason = self.validate_structure(rule)
                smoke = None

                if not ok:
                    quarantined.append({
                        "rule_id": rule_id,
                        "file": str(rule_file),
                        "reason": reason,
                    })
                    results.append({
                        "rule_id": rule_id, "file": str(rule_file),
                        "structure_ok": False, "smoke": None, "reason": reason,
                    })
                    continue

                # 结构合法，做沙箱冒烟（可选）
                if corpus_dir:
                    smoke = self.smoke_test(rule_file, corpus_dir)
                    if smoke["status"] == "error":
                        smoke_error_count += 1
                        quarantined.append({
                            "rule_id": rule_id,
                            "file": str(rule_file),
                            "reason": f"沙箱冒烟失败: {smoke['detail'][:100]}",
                        })
                        results.append({
                            "rule_id": rule_id, "file": str(rule_file),
                            "structure_ok": True, "smoke": smoke,
                            "reason": smoke["detail"][:200],
                        })
                        continue

                valid_count += 1
                results.append({
                    "rule_id": rule_id, "file": str(rule_file),
                    "structure_ok": True, "smoke": smoke,
                    "reason": "",
                })

        return {
            "total": len(rule_files),
            "valid": valid_count,
            "invalid": len(quarantined) - smoke_error_count,
            "smoke_error": smoke_error_count,
            "quarantined": quarantined,
            "results": results,
        }


def yaml_safe_load(stream):
    """延迟导入 yaml（保持模块独立可测）"""
    import yaml
    return yaml.safe_load(stream)
