#!/usr/bin/env python3
"""
规约预编译器
将自然语言规约转换为 Semgrep 规则，带安全审核机制。

流程：
1. 读取自然语言规约（纯 Markdown）
2. AI 理解并生成 Semgrep 规则草稿
3. AI 对比解读新旧规则差异
4. 回归测试验证规则效果
5. 人工确认后生成最终规则
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger("code-review.compiler")


class RuleCompiler:
    """规约预编译器 - 将自然语言规约转换为 Semgrep 规则"""

    def __init__(self, specs_dir: str, output_dir: str = None):
        """
        Args:
            specs_dir: 自然语言规约目录
            output_dir: 编译输出目录（默认为 specs_dir/compiled）
        """
        self.specs_dir = Path(specs_dir)
        self.output_dir = Path(output_dir) if output_dir else self.specs_dir / "compiled"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 版本历史目录
        self.history_dir = self.output_dir / ".history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def compile_all(self, force: bool = False) -> Dict:
        """
        编译所有规约
        
        Args:
            force: 是否强制重新编译（忽略缓存）
            
        Returns:
            编译结果统计
        """
        results = {
            "total": 0,
            "compiled": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }
        
        # 遍历所有 Markdown 文件
        for md_file in self.specs_dir.glob("**/*.md"):
            # 跳过编译输出目录
            if "compiled" in md_file.parts:
                continue
                
            results["total"] += 1
            
            try:
                result = self.compile_rule(md_file, force=force)
                if result["status"] == "compiled":
                    results["compiled"] += 1
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                results["details"].append(result)
            except Exception as e:
                logger.error(f"编译失败 {md_file}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "file": str(md_file),
                    "status": "failed",
                    "error": str(e)
                })
        
        return results

    def compile_rule(self, md_file: Path, force: bool = False) -> Dict:
        """
        编译单个规约
        
        Args:
            md_file: Markdown 规约文件
            force: 是否强制重新编译
            
        Returns:
            编译结果
        """
        # 检查是否需要重新编译
        output_file = self.output_dir / f"{md_file.stem}.yaml"
        if not force and output_file.exists():
            # 检查源文件是否更新
            if md_file.stat().st_mtime <= output_file.stat().st_mtime:
                return {
                    "file": str(md_file),
                    "status": "skipped",
                    "reason": "no changes"
                }
        
        # 读取自然语言规约
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取规约元数据
        metadata = self._extract_metadata(content)
        
        # 提取违规场景和安全做法
        violation_scenario = self._extract_section(content, "违规场景")
        safe_approach = self._extract_section(content, "安全做法")
        
        # 提取示例代码
        bad_example = self._extract_code_block(content, "违规代码")
        good_example = self._extract_code_block(content, "安全代码")
        
        # 调用 AI 生成 Semgrep 规则
        semgrep_rule = self._generate_semgrep_rule_with_ai(
            metadata=metadata,
            violation_scenario=violation_scenario,
            safe_approach=safe_approach,
            bad_example=bad_example,
            good_example=good_example
        )
        
        # 保存编译结果
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(semgrep_rule, f, allow_unicode=True, default_flow_style=False)
        
        # 保存版本历史
        self._save_history(md_file, semgrep_rule)
        
        return {
            "file": str(md_file),
            "status": "compiled",
            "output": str(output_file),
            "metadata": metadata
        }

    def _extract_metadata(self, content: str) -> Dict:
        """提取规约元数据"""
        metadata = {}
        
        # 提取标题
        title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        
        # 提取严重等级
        severity_match = re.search(r"## 严重等级\s*\n(.+)", content)
        if severity_match:
            severity_text = severity_match.group(1).strip()
            if "ERROR" in severity_text or "CRITICAL" in severity_text:
                metadata["severity"] = "ERROR"
            elif "WARNING" in severity_text:
                metadata["severity"] = "WARNING"
            else:
                metadata["severity"] = "INFO"
        
        # 提取语言（从示例代码块推断）
        lang_match = re.search(r"```(\w+)\s*\n", content)
        if lang_match:
            lang = lang_match.group(1).lower()
            lang_map = {
                "java": "java",
                "python": "python",
                "javascript": "javascript",
                "typescript": "typescript",
                "go": "go"
            }
            metadata["languages"] = [lang_map.get(lang, "java")]
        
        return metadata

    def _extract_section(self, content: str, section_name: str) -> str:
        """提取指定章节内容"""
        pattern = rf"## {section_name}\s*\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_code_block(self, content: str, block_name: str) -> str:
        """提取指定代码块"""
        pattern = rf"### {block_name}\s*\n```[\w]*\s*\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _generate_semgrep_rule_with_ai(
        self,
        metadata: Dict,
        violation_scenario: str,
        safe_approach: str,
        bad_example: str,
        good_example: str
    ) -> Dict:
        """
        调用 AI 生成 Semgrep 规则
        
        TODO: 实际应该调用 LLM API
        这里先用占位逻辑，后续接入 AI
        """
        # 构建 AI prompt
        prompt = f"""你是一个安全专家，需要将以下自然语言安全规约转换为 Semgrep 规则。

## 规约内容

标题：{metadata.get('title', 'Unknown')}
语言：{', '.join(metadata.get('languages', ['java']))}
严重等级：{metadata.get('severity', 'WARNING')}

### 违规场景
{violation_scenario}

### 安全做法
{safe_approach}

### 违规代码示例
```
{bad_example}
```

### 安全代码示例
```
{good_example}
```

## 任务

请生成一个 Semgrep 规则，能够检测上述违规场景。规则应该：
1. 使用 Semgrep 的 pattern 语法
2. 使用元变量（$VAR）表示变量名
3. 使用 ... 表示任意代码
4. 尽可能精确，避免误报

请只输出 Semgrep 规则的 pattern 部分，不要输出其他内容。
"""
        
        # TODO: 调用 LLM API
        # response = call_llm(prompt)
        # pattern = response.strip()
        
        # 占位实现：从违规代码示例推断简单 pattern
        pattern = self._infer_pattern_from_example(bad_example, metadata.get("languages", ["java"])[0])
        
        # 生成规则 ID：从标题提取关键词，转为小写，替换空格和特殊字符为连字符
        title = metadata.get("title", "unknown")
        # 提取前几个关键词
        keywords = title.split()[:5]  # 取前5个词
        rule_id = "-".join(keywords).lower()
        # 移除非字母数字字符（保留连字符）
        rule_id = re.sub(r'[^a-z0-9-]', '', rule_id)
        # 移除多余的连字符
        rule_id = re.sub(r'-+', '-', rule_id)
        # 移除首尾连字符
        rule_id = rule_id.strip('-')
        # 限制长度
        rule_id = rule_id[:50]
        
        return {
            "rules": [
                {
                    "id": rule_id,
                    "message": metadata.get("title", "Security issue detected"),
                    "severity": metadata.get("severity", "WARNING"),
                    "languages": metadata.get("languages", ["java"]),
                    "pattern": pattern,
                    "metadata": {
                        "violation_scenario": violation_scenario,
                        "safe_approach": safe_approach,
                        "compiled_at": datetime.now().isoformat(),
                        "source_file": metadata.get("title", "unknown")
                    }
                }
            ]
        }

    def _infer_pattern_from_example(self, bad_example: str, language: str) -> str:
        """
        从违规代码示例推断 Semgrep pattern（占位实现）
        
        TODO: 实际应该用 AI 理解语义并生成
        """
        # 简单启发式：提取关键 API 调用
        lines = bad_example.strip().split("\n")
        if not lines:
            return "TODO: AI should generate this pattern"
        
        # 提取最后一行（通常是危险调用）
        last_line = lines[-1].strip()
        
        # 替换具体变量名为元变量
        pattern = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', '$VAR', last_line)
        
        return pattern

    def _save_history(self, md_file: Path, rule: Dict):
        """保存版本历史"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = self.history_dir / f"{md_file.stem}_{timestamp}.yaml"
        
        with open(history_file, "w", encoding="utf-8") as f:
            yaml.dump(rule, f, allow_unicode=True, default_flow_style=False)

    def diff_rules(self, rule_file: Path) -> Dict:
        """
        对比新旧规则差异（AI 解读）
        
        Args:
            rule_file: 编译后的规则文件
            
        Returns:
            差异报告
        """
        # 读取当前规则
        with open(rule_file, "r", encoding="utf-8") as f:
            current = yaml.safe_load(f)
        
        # 读取上一个版本
        history_files = sorted(self.history_dir.glob(f"{rule_file.stem}_*.yaml"))
        if len(history_files) < 2:
            return {
                "status": "no_previous_version",
                "message": "这是第一个版本，没有历史版本可以对比"
            }
        
        previous_file = history_files[-2]
        with open(previous_file, "r", encoding="utf-8") as f:
            previous = yaml.safe_load(f)
        
        # 调用 AI 生成语义差异报告
        diff_report = self._generate_diff_report_with_ai(previous, current)
        
        return {
            "status": "diff_generated",
            "previous_version": str(previous_file),
            "current_version": str(rule_file),
            "report": diff_report
        }

    def _generate_diff_report_with_ai(self, previous: Dict, current: Dict) -> Dict:
        """
        调用 AI 生成语义差异报告
        
        TODO: 实际应该调用 LLM API
        """
        # 构建 AI prompt
        prompt = f"""你是一个安全专家，请对比以下两个版本的 Semgrep 规则，分析差异。

## 旧版本规则
```yaml
{yaml.dump(previous, allow_unicode=True)}
```

## 新版本规则
```yaml
{yaml.dump(current, allow_unicode=True)}
```

## 任务

请分析：
1. 规则覆盖范围的变化（检测范围是扩大还是缩小）
2. 可能新增的误报或漏报
3. 建议的测试用例（验证新规则效果）

请用中文输出差异报告。
"""
        
        # TODO: 调用 LLM API
        # report = call_llm(prompt)
        
        # 占位实现：简单的结构对比
        report = {
            "summary": "规则已更新",
            "changes": [],
            "recommendations": []
        }
        
        # 对比规则数量
        prev_count = len(previous.get("rules", []))
        curr_count = len(current.get("rules", []))
        if prev_count != curr_count:
            report["changes"].append({
                "type": "rule_count",
                "description": f"规则数量从 {prev_count} 变为 {curr_count}",
                "impact": "medium"
            })
        
        # 对比 pattern
        prev_patterns = [r.get("pattern", "") for r in previous.get("rules", [])]
        curr_patterns = [r.get("pattern", "") for r in current.get("rules", [])]
        
        if prev_patterns != curr_patterns:
            report["changes"].append({
                "type": "pattern_changed",
                "description": "检测模式已更新",
                "impact": "high",
                "recommendation": "建议使用测试用例验证新规则效果"
            })
        
        report["recommendations"].append("运行回归测试验证规则效果")
        report["recommendations"].append("检查人审核差异报告后确认")
        
        return report

    def run_regression_test(self, rule_file: Path, test_cases_dir: str) -> Dict:
        """
        回归测试验证规则效果
        
        Args:
            rule_file: 编译后的规则文件
            test_cases_dir: 测试用例目录
            
        Returns:
            测试结果
        """
        test_dir = Path(test_cases_dir)
        if not test_dir.exists():
            return {
                "status": "error",
                "message": f"测试用例目录不存在: {test_cases_dir}"
            }
        
        # 读取规则
        with open(rule_file, "r", encoding="utf-8") as f:
            rule = yaml.safe_load(f)
        
        # 生成临时 Semgrep 配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
            yaml.dump(rule, tmp, allow_unicode=True)
            tmp_rule_file = tmp.name
        
        try:
            # 运行 Semgrep
            cmd = [
                "semgrep",
                "--config", tmp_rule_file,
                "--json",
                "--quiet",
                str(test_dir)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode not in [0, 1]:  # 0=无问题, 1=有问题
                return {
                    "status": "error",
                    "message": f"Semgrep 执行失败: {result.stderr}"
                }
            
            # 解析结果
            findings = json.loads(result.stdout)
            
            # TODO: 对比预期结果，计算检出率和误报率
            # 这里先返回原始结果
            
            return {
                "status": "success",
                "rule_file": str(rule_file),
                "test_cases_dir": test_cases_dir,
                "findings_count": len(findings.get("results", [])),
                "findings": findings.get("results", [])
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "Semgrep 执行超时"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"测试执行失败: {str(e)}"
            }
        finally:
            # 清理临时文件
            if os.path.exists(tmp_rule_file):
                os.unlink(tmp_rule_file)

    def approve_and_deploy(self, rule_file: Path, auto_approve: bool = False) -> Dict:
        """
        人工确认后部署规则
        
        Args:
            rule_file: 编译后的规则文件
            auto_approve: 是否跳过交互确认（仅用于测试）
            
        Returns:
            部署结果
        """
        # 检查规则文件是否存在
        if not rule_file.exists():
            return {
                "status": "error",
                "message": f"规则文件不存在: {rule_file}"
            }
        
        # 读取规则
        with open(rule_file, "r", encoding="utf-8") as f:
            rule = yaml.safe_load(f)
        
        # 生成差异报告（如果有历史版本）
        diff_report = None
        history_files = sorted(self.history_dir.glob(f"{rule_file.stem}_*.yaml"))
        if len(history_files) >= 2:
            previous_file = history_files[-2]
            with open(previous_file, "r", encoding="utf-8") as f:
                previous = yaml.safe_load(f)
            diff_report = self._generate_diff_report_with_ai(previous, rule)
        
        # 交互式确认流程
        if not auto_approve:
            print("\n" + "=" * 70)
            print("  规约预编译 · 人工确认")
            print("=" * 70)
            
            # 展示规则基本信息
            print(f"\n📋 规则文件: {rule_file}")
            print(f"📅 编译时间: {rule.get('rules', [{}])[0].get('metadata', {}).get('compiled_at', 'N/A')}")
            
            # 展示规则内容
            print(f"\n📝 规则内容:")
            print(f"   ID: {rule.get('rules', [{}])[0].get('id', 'N/A')}")
            print(f"   严重等级: {rule.get('rules', [{}])[0].get('severity', 'N/A')}")
            print(f"   语言: {', '.join(rule.get('rules', [{}])[0].get('languages', []))}")
            print(f"   检测模式: {rule.get('rules', [{}])[0].get('pattern', 'N/A')[:100]}...")
            
            # 展示差异报告
            if diff_report:
                print(f"\n🔍 差异报告:")
                print(f"   {diff_report.get('summary', 'N/A')}")
                for change in diff_report.get('changes', []):
                    print(f"   - [{change.get('impact', 'medium').upper()}] {change.get('description', 'N/A')}")
                print(f"\n💡 建议:")
                for rec in diff_report.get('recommendations', []):
                    print(f"   - {rec}")
            else:
                print(f"\n🆕 这是第一个版本，无历史对比")
            
            # 等待用户确认
            print("\n" + "-" * 70)
            print("请确认是否部署此规则？")
            print("  1. ✅ 确认部署")
            print("  2. ❌ 取消")
            print("  3. 📝 查看详情（打开规则文件）")
            
            while True:
                choice = input("\n请选择 (1/2/3): ").strip()
                if choice == "1":
                    break
                elif choice == "2":
                    return {
                        "status": "cancelled",
                        "message": "用户取消部署"
                    }
                elif choice == "3":
                    print(f"\n规则文件路径: {rule_file.absolute()}")
                    print("请使用编辑器打开查看完整内容")
                else:
                    print("无效选择，请重新输入")
        
        # 标记为已批准
        approved_file = self.output_dir / f"{rule_file.stem}.approved.yaml"
        with open(approved_file, "w", encoding="utf-8") as f:
            yaml.dump(rule, f, allow_unicode=True, default_flow_style=False)
        
        # 记录审批信息
        approval_record = {
            "rule_file": str(rule_file),
            "approved_at": datetime.now().isoformat(),
            "approved_file": str(approved_file),
            "status": "approved"
        }
        
        # 保存审批记录
        approval_log = self.output_dir / ".approval_log.json"
        approvals = []
        if approval_log.exists():
            with open(approval_log, "r", encoding="utf-8") as f:
                approvals = json.load(f)
        
        approvals.append(approval_record)
        with open(approval_log, "w", encoding="utf-8") as f:
            json.dump(approvals, f, indent=2, ensure_ascii=False)
        
        if not auto_approve:
            print(f"\n✅ 规则已部署: {approved_file}")
            print(f"📅 部署时间: {approval_record['approved_at']}")
        
        return {
            "status": "approved",
            "approved_file": str(approved_file),
            "approved_at": approval_record["approved_at"]
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="规约预编译器")
    parser.add_argument("--specs-dir", help="规约目录（编译模式必需）")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--force", action="store_true", help="强制重新编译")
    parser.add_argument("--diff", help="对比规则差异")
    parser.add_argument("--test", help="回归测试（需要指定测试用例目录）")
    parser.add_argument("--approve", help="批准并部署规则")
    parser.add_argument("--auto-approve", action="store_true", help="跳过交互确认（仅用于测试）")
    
    args = parser.parse_args()
    
    # 根据操作模式决定是否需要 specs-dir
    if args.diff:
        # diff 模式：从规则文件路径推断 output_dir
        rule_path = Path(args.diff)
        output_dir = rule_path.parent
        compiler = RuleCompiler(str(output_dir.parent), str(output_dir))
        result = compiler.diff_rules(rule_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.test:
        # test 模式：需要 --diff 参数指定规则文件
        if not args.diff:
            print("错误：--test 模式需要 --diff 参数指定规则文件")
            exit(1)
        rule_path = Path(args.diff)
        output_dir = rule_path.parent
        compiler = RuleCompiler(str(output_dir.parent), str(output_dir))
        result = compiler.run_regression_test(rule_path, args.test)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.approve:
        # approve 模式：从规则文件路径推断 output_dir
        rule_path = Path(args.approve)
        output_dir = rule_path.parent
        compiler = RuleCompiler(str(output_dir.parent), str(output_dir))
        result = compiler.approve_and_deploy(rule_path, auto_approve=args.auto_approve)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.specs_dir:
        # compile 模式
        compiler = RuleCompiler(args.specs_dir, args.output_dir)
        result = compiler.compile_all(force=args.force)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("错误：必须指定 --specs-dir（编译模式）或 --diff（对比/测试模式）或 --approve（审批模式）")
        exit(1)
