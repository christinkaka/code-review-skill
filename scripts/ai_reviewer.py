#!/usr/bin/env python3
"""
AI 增强评审器
对规则引擎的检查结果进行二次评审，过滤误报、补充上下文、生成修复建议。
支持多工作流提示词切换。
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("code-review.ai")


class AIReviewer:
    """AI 增强评审器"""

    # 工作流配置
    WORKFLOW_CONFIG = {
        "security": {
            "prompt_file": "security-audit-prompt.md",
            "temperature": 0.1,
            "max_tokens": 2048,
            "description": "安全审计工作流",
        },
        "quality": {
            "prompt_file": "code-quality-prompt.md",
            "temperature": 0.2,
            "max_tokens": 1536,
            "description": "代码质量工作流",
        },
        "performance": {
            "prompt_file": "performance-review-prompt.md",
            "temperature": 0.1,
            "max_tokens": 2048,
            "description": "性能优化工作流",
        },
        "architecture": {
            "prompt_file": "architecture-review-prompt.md",
            "temperature": 0.2,
            "max_tokens": 2048,
            "description": "架构审查工作流",
        },
        "comprehensive": {
            "prompt_file": "ai-enhancer-prompt.md",
            "temperature": 0.1,
            "max_tokens": 1024,
            "description": "综合评审工作流",
        },
    }

    def __init__(self, config: Dict):
        self.config = config
        self.llm_config = config.get("llm", {})
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.workflow = config.get("workflow", "comprehensive")
        self._client = None
        
        # 加载工作流提示词
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"AI 评审器初始化，工作流: {self.workflow}")

    def _load_prompt_template(self) -> str:
        """加载工作流对应的提示词模板"""
        workflow_config = self.WORKFLOW_CONFIG.get(self.workflow, self.WORKFLOW_CONFIG["comprehensive"])
        prompt_file = workflow_config["prompt_file"]
        
        # 查找提示词文件
        prompts_dir = Path(__file__).parent.parent / "references" / "prompts"
        prompt_path = prompts_dir / prompt_file
        
        if not prompt_path.exists():
            logger.warning(f"提示词文件不存在: {prompt_path}，使用默认提示词")
            return self._get_default_prompt()
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 提取 Python 代码块中的提示词
            import re
            match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            
            return content
        except Exception as e:
            logger.error(f"加载提示词失败: {e}")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """获取默认提示词"""
        return """你是一个专业的代码评审专家。请对以下代码扫描结果进行二次评审。

## 任务
1. 判断每个问题是否为真正的代码问题（排除误报）
2. 评估问题的严重程度（0-1 之间的置信度分数）
3. 如果问题确实存在，提供更具体的修复建议

## 输出格式
请以 JSON 数组格式返回，每个元素包含：
- "rule_id": 规则 ID
- "is_valid": true/false（是否为真正的问题）
- "confidence": 0.0-1.0（置信度）
- "enhanced_fix": 增强的修复建议（字符串）

只返回 JSON 数组，不要其他内容。
"""

    def review(
        self,
        issues: List[Dict],
        diff_result: Dict,
        call_graph: Dict,
    ) -> List[Dict]:
        """
        对规则引擎的结果进行 AI 二次评审

        Args:
            issues: 规则引擎输出的问题列表
            diff_result: 差异分析结果
            call_graph: 调用图数据

        Returns:
            过滤和增强后的问题列表
        """
        if not issues:
            return issues

        if not self._is_available():
            logger.warning("AI 评审不可用（LLM 未配置），返回原始结果")
            return issues

        logger.info(f"AI 评审开始，工作流: {self.workflow}，输入 {len(issues)} 个问题")

        # 分批处理（避免超出 token 限制）
        batch_size = 20
        filtered_issues = []

        for i in range(0, len(issues), batch_size):
            batch = issues[i:i + batch_size]
            result = self._review_batch(batch, diff_result, call_graph)
            filtered_issues.extend(result)

        logger.info(f"AI 评审完成，输出 {len(filtered_issues)} 个问题")
        return filtered_issues

    def _is_available(self) -> bool:
        """检查 AI 评审是否可用"""
        if not self.llm_config.get("url"):
            return False

        api_key_env = self.llm_config.get("api_key_env", "")
        if api_key_env and not os.environ.get(api_key_env):
            return False

        return True

    def _review_batch(
        self,
        batch: List[Dict],
        diff_result: Dict,
        call_graph: Dict,
    ) -> List[Dict]:
        """评审一批问题"""
        # 构建 prompt
        prompt = self._build_prompt(batch, diff_result, call_graph)

        # 调用 LLM
        response = self._call_llm(prompt)
        if not response:
            return batch  # LLM 调用失败，返回原始结果

        # 解析 LLM 响应
        return self._parse_response(batch, response)

    def _build_prompt(self, issues: List[Dict], diff_result: Dict, call_graph: Dict) -> str:
        """构建评审 prompt"""
        issues_text = json.dumps(issues, ensure_ascii=False, indent=2)
        changed_files = [f["path"] for f in diff_result.get("changed_files", [])[:10]]
        
        # 使用工作流提示词模板
        prompt = self.prompt_template.replace("{actual_input}", issues_text)
        
        # 如果不是默认提示词，添加变更文件上下文
        if "{actual_input}" not in self.prompt_template:
            context = f"\n\n## 变更文件\n{json.dumps(changed_files, ensure_ascii=False)}\n\n## 扫描结果\n{issues_text}"
            prompt += context

        return prompt

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM API"""
        try:
            import urllib.request

            api_key_env = self.llm_config.get("api_key_env", "")
            api_key = os.environ.get(api_key_env, "")

            url = self.llm_config.get("url", "")
            model = self.llm_config.get("model", "gpt-4")

            # 获取工作流配置
            workflow_config = self.WORKFLOW_CONFIG.get(self.workflow, self.WORKFLOW_CONFIG["comprehensive"])

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"你是一个专业的代码评审助手，当前使用{workflow_config['description']}。请严格按照要求的 JSON 格式输出。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": workflow_config["temperature"],
                "max_tokens": workflow_config["max_tokens"],
            }

            headers = {
                "Content-Type": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None

    def _parse_response(self, original_issues: List[Dict], response: str) -> List[Dict]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            response = response.strip()
            if response.startswith("```"):
                # 去除 markdown 代码块
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            ai_results = json.loads(response)

            # 构建映射
            ai_map = {}
            for item in ai_results:
                if isinstance(item, dict) and "rule_id" in item:
                    ai_map[item["rule_id"]] = item

            # 过滤和增强
            filtered = []
            for issue in original_issues:
                rule_id = issue.get("rule_id", "")
                ai_result = ai_map.get(rule_id, {})

                # 检查是否为有效问题
                is_valid = ai_result.get("is_valid", True)
                confidence = ai_result.get("confidence", 0.8)

                if is_valid and confidence >= self.confidence_threshold:
                    # 增强修复建议
                    enhanced_fix = ai_result.get("enhanced_fix", "")
                    if enhanced_fix:
                        issue["fix"] = enhanced_fix
                    issue["ai_confidence"] = confidence
                    
                    # 添加工作流特定字段
                    if self.workflow == "security":
                        issue["attack_vector"] = ai_result.get("attack_vector", "")
                        issue["cvss_score"] = ai_result.get("cvss_score", 0.0)
                    elif self.workflow == "quality":
                        issue["code_smell"] = ai_result.get("code_smell", "")
                        issue["technical_debt"] = ai_result.get("technical_debt", "")
                    elif self.workflow == "performance":
                        issue["performance_impact"] = ai_result.get("performance_impact", "")
                        issue["expected_improvement"] = ai_result.get("expected_improvement", "")
                    elif self.workflow == "architecture":
                        issue["architecture_impact"] = ai_result.get("architecture_impact", "")
                        issue["design_violation"] = ai_result.get("design_violation", "")
                    
                    filtered.append(issue)

            return filtered

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"AI 响应解析失败: {e}，返回原始结果")
            return original_issues

    def get_available_workflows(self) -> List[str]:
        """获取可用的工作流列表"""
        return list(self.WORKFLOW_CONFIG.keys())

    def get_current_workflow(self) -> str:
        """获取当前工作流"""
        return self.workflow

    def set_workflow(self, workflow: str) -> bool:
        """切换工作流"""
        if workflow not in self.WORKFLOW_CONFIG:
            logger.error(f"不支持的工作流: {workflow}")
            return False
        
        self.workflow = workflow
        self.prompt_template = self._load_prompt_template()
        logger.info(f"已切换工作流: {workflow}")
        return True
