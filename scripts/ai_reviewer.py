import os
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
        self.feedback_summary = config.get("feedback_summary")
        self.feedback_examples = config.get("feedback_examples", [])
        
        # 加载工作流提示词
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"AI 评审任务生成器初始化，工作流: {self.workflow}")
        if self.feedback_summary:
            logger.info(f"  历史反馈: {self.feedback_summary}")

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
        """获取默认提示词（与 references/prompts/ai-enhancer-prompt.md 保持一致）"""
        return """你是一个专业的代码评审助手，专门负责增强代码扫描结果。

## 你的职责

✅ 你可以做：
- 标记误报（is_false_positive = true）
- 补充分析说明（analysis）
- 生成修复建议（enhanced_fix）
- 评估风险等级（risk_level）
- 分析影响范围（impact_scope）

❌ 你不能做：
- 删除确定性问题（rule_id 必须保留）
- 改变问题的 severity（severity 由规则定义）
- 改变问题的 rule_id（rule_id 由规则定义）

## 示例 1：真实问题

### 输入
{
  "rule_id": "xxe-java-document-builder",
  "severity": "ERROR",
  "file": "Parser.java",
  "line": 42,
  "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
  "message": "DocumentBuilderFactory 未禁用外部实体"
}

### 期望输出
{
  "rule_id": "xxe-java-document-builder",
  "severity": "ERROR",
  "file": "Parser.java",
  "line": 42,
  "code_snippet": "DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();",
  "message": "DocumentBuilderFactory 未禁用外部实体",
  "is_false_positive": false,
  "ai_confidence": 0.92,
  "analysis": "该代码处理外部 XML 输入，未禁用外部实体，攻击者可构造恶意 XML 读取服务器文件。建议立即修复。",
  "risk_level": "CRITICAL",
  "impact_scope": "影响所有调用 parseXml() 方法的地方",
  "enhanced_fix": "factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);\nfactory.setFeature(\"http://xml.org/sax/features/external-general-entities\", false);",
  "references": ["https://owasp.org/Top10/A05_2021-Security-Misconfiguration/"]
}

## 示例 2：误报场景

### 输入
{
  "rule_id": "xss-java-servlet-output",
  "severity": "WARNING",
  "file": "TestController.java",
  "line": 15,
  "code_snippet": "response.getWriter().write(testData);",
  "message": "Servlet 响应直接写入用户输入"
}

### 期望输出
{
  "rule_id": "xss-java-servlet-output",
  "severity": "WARNING",
  "file": "TestController.java",
  "line": 15,
  "code_snippet": "response.getWriter().write(testData);",
  "message": "Servlet 响应直接写入用户输入",
  "is_false_positive": true,
  "ai_confidence": 0.85,
  "analysis": "这是测试代码，testData 是硬编码的测试数据，不是用户输入，不存在 XSS 风险。",
  "risk_level": "LOW",
  "impact_scope": "无",
  "enhanced_fix": "无需修复",
  "references": []
}

## 输出格式要求

你必须输出以下 JSON 格式，不要添加其他内容：
{
  "rule_id": "string (必须与输入一致)",
  "severity": "string (必须与输入一致)",
  "file": "string (必须与输入一致)",
  "line": "number (必须与输入一致)",
  "code_snippet": "string (必须与输入一致)",
  "message": "string (必须与输入一致)",
  "is_false_positive": "boolean",
  "ai_confidence": "float (0-1)",
  "analysis": "string (50-200 字)",
  "risk_level": "string (CRITICAL/HIGH/MEDIUM/LOW)",
  "impact_scope": "string (20-100 字)",
  "enhanced_fix": "string (包含具体代码)",
  "references": "array (0-3 个链接)"
}

## 字段约束

- is_false_positive: 如果代码在特定上下文中是安全的（如测试代码、硬编码数据、Maven 属性占位符等非真实安全问题），标记为 true
- ai_confidence: 0.9-1.0 非常确定；0.7-0.9 比较确定；0.5-0.7 需要人工确认；<0.5 建议跳过
- enhanced_fix: 必须包含具体的代码修改，不能只是文字描述

请以 JSON 数组格式返回评审结果，每个问题一条记录。只返回 JSON 数组，不要其他内容。
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
        
        # 构建历史反馈部分
        feedback_section = ""
        if self.feedback_summary and self.feedback_summary.get("total", 0) > 0:
            summary = self.feedback_summary
            accuracy = summary['confirmed'] / summary['total'] if summary['total'] > 0 else 0
            feedback_section = f"""
## 历史反馈统计
基于过去的评审数据：
- 总反馈数: {summary['total']}
- 确认（真实问题）: {summary['confirmed']}
- 误报: {summary['false_positive']}
- 不确定: {summary['uncertain']}
- 历史准确率: {accuracy:.1%}

请参考历史反馈模式，提高评审准确性。
"""
            if self.feedback_examples:
                feedback_section += "\n### 近期反馈示例\n"
                for example in self.feedback_examples[:5]:
                    verdict_text = {
                        "confirmed": "用户确认（真实问题）",
                        "false_positive": "用户标记为误报",
                        "uncertain": "用户不确定",
                    }.get(example.get("verdict", ""), example.get("verdict", ""))
                    feedback_section += f"- 规则 `{example.get('rule_id', 'unknown')}`: {verdict_text}"
                    if example.get("comment"):
                        feedback_section += f"（{example['comment']}）"
                    feedback_section += "\n"

        # 构建任务描述（直接使用 prompt_template，确保字段定义一致）
        task = f"""{self.prompt_template}

## 评审数据

### 扫描结果（共 {len(issues)} 条）
{json.dumps(issues, ensure_ascii=False, indent=2)}

### 变更文件
{json.dumps([f['path'] for f in diff_result.get('changed_files', [])[:10]], ensure_ascii=False)}
{feedback_section}
请严格按照上述输出格式要求返回 JSON 数组。
"""
        
        return task

    def save_task_to_file(
        self,
        task: str,
        output_path: str,
    ) -> None:
        """保存任务描述到文件"""
        # 创建父目录（如果不存在）
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
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
