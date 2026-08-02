#!/usr/bin/env python3
"""
AI 评审任务生成器
生成 subagent 评审任务描述，供 TRAE Agent 委派 subagent 执行代码评审。
支持多工作流提示词切换，配置低温度参数确保严谨性和一致性。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("code-review.ai")


class AIReviewer:
    """AI 评审任务生成器"""

    # 工作流配置（低温度参数确保严谨性和一致性）
    WORKFLOW_CONFIG = {
        "security": {
            "prompt_file": "security-audit-prompt.md",
            "temperature": 0.1,  # 安全审计需要最高严谨性
            "description": "安全审计工作流",
        },
        "quality": {
            "prompt_file": "code-quality-prompt.md",
            "temperature": 0.2,  # 代码质量评审需要较高一致性
            "description": "代码质量工作流",
        },
        "performance": {
            "prompt_file": "performance-review-prompt.md",
            "temperature": 0.1,  # 性能分析需要严谨性
            "description": "性能优化工作流",
        },
        "architecture": {
            "prompt_file": "architecture-review-prompt.md",
            "temperature": 0.2,  # 架构评审需要一致性
            "description": "架构审查工作流",
        },
        "comprehensive": {
            "prompt_file": "ai-enhancer-prompt.md",
            "temperature": 0.1,  # 综合评审需要严谨性
            "description": "综合评审工作流",
        },
    }

    def __init__(self, config: Dict):
        self.config = config
        self.workflow = config.get("workflow", "comprehensive")
        
        # 加载工作流提示词
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"AI 评审任务生成器初始化，工作流: {self.workflow}")

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

    def generate_subagent_task(
        self,
        issues: List[Dict],
        diff_result: Dict,
        call_graph: Dict,
    ) -> str:
        """
        生成 subagent 评审任务描述

        Args:
            issues: 规则引擎输出的问题列表
            diff_result: 差异分析结果
            call_graph: 调用图数据

        Returns:
            subagent 任务描述字符串
        """
        if not issues:
            return ""

        workflow_config = self.WORKFLOW_CONFIG.get(self.workflow, self.WORKFLOW_CONFIG["comprehensive"])
        temperature = workflow_config['temperature']
        
        # 构建任务描述
        task = f"""请对以下代码扫描结果进行评审：

## 工作流
{workflow_config['description']}

## 温度参数
temperature: {temperature}

## 扫描结果
{json.dumps(issues, ensure_ascii=False, indent=2)}

## 变更文件
{json.dumps([f['path'] for f in diff_result.get('changed_files', [])[:10]], ensure_ascii=False)}

## 评审要求
1. 分析每个问题的真实性（排除误报）
2. 评估问题的严重程度（0-1 之间的置信度）
3. 为真实问题生成具体的修复建议
4. 使用严谨的评审标准（温度 {temperature}）

## 输出格式
请以 JSON 数组格式返回评审结果，每个元素包含：
- "rule_id": 规则 ID（必须与输入一致）
- "is_valid": true/false（是否为真实问题）
- "confidence": 0.0-1.0（置信度）
- "enhanced_fix": 修复建议（包含具体代码）
- "analysis": 分析说明

只返回 JSON 数组，不要其他内容。
"""
        
        return task

    def save_task_to_file(
        self,
        task: str,
        output_path: str,
    ) -> None:
        """保存任务描述到文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(task)
        logger.info(f"Subagent 任务已保存到: {output_path}")

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
