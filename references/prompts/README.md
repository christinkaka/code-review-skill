# 多工作流提示词系统

## 概述

本目录包含针对不同代码评审工作流的 AI 提示词模板。每个工作流都有专门的提示词，针对特定场景进行了优化。

## 可用工作流

### 1. 安全审计 (security-audit-prompt.md)

**适用场景**：安全漏洞扫描、渗透测试结果分析、合规性检查

**特点**：
- 深度攻击向量分析
- CVSS 评分参考
- 攻击复杂度评估
- 安全防护措施检查
- P0-P4 优先级分类

**输出字段**：
- `attack_vector`: 攻击路径描述
- `exploitability`: 可利用程度 (HIGH/MEDIUM/LOW/NONE)
- `impact`: 影响范围
- `existing_controls`: 已有防护措施
- `cwe`: CWE 编号
- `cvss_score`: CVSS 评分 (0-10)

---

### 2. 代码质量 (code-quality-prompt.md)

**适用场景**：代码审查、技术债务评估、最佳实践检查

**特点**：
- 代码复杂度分析
- 可维护性评估
- 最佳实践违规检查
- 技术债务评估
- 代码异味识别

**输出字段**：
- `quality_impact`: 质量影响程度
- `complexity_score`: 复杂度评分
- `maintainability`: 可维护性评估
- `best_practice_violation`: 违反的最佳实践
- `code_smell`: 代码异味类型
- `technical_debt`: 技术债务评估

---

### 3. 性能优化 (performance-review-prompt.md)

**适用场景**：性能瓶颈分析、优化建议、资源使用评估

**特点**：
- 时间/空间复杂度分析
- 性能影响量化
- 优化策略建议
- 预期收益评估
- 根因分析

**输出字段**：
- `performance_impact`: 性能影响 (CRITICAL/HIGH/MEDIUM/LOW/NONE)
- `root_cause`: 根本原因
- `optimization_strategy`: 优化策略
- `expected_improvement`: 预期提升
- `complexity_before`: 优化前复杂度
- `complexity_after`: 优化后复杂度

---

### 4. 架构审查 (architecture-review-prompt.md)

**适用场景**：架构评审、设计模式检查、分层架构验证

**特点**：
- 分层架构检查
- 设计模式分析
- 耦合度评估
- 可扩展性分析
- 技术债务评估

**输出字段**：
- `architecture_impact`: 架构影响
- `design_violation`: 设计原则违反
- `coupling_issue`: 耦合问题
- `scalability_concern`: 可扩展性问题
- `architecture_pattern`: 相关架构模式
- `technical_debt`: 技术债务

---

### 5. 综合评审 (ai-enhancer-prompt.md)

**适用场景**：通用代码评审、综合质量检查

**特点**：
- 通用性强
- 覆盖多种问题类型
- 平衡的分析深度

---

## 使用方法

### 1. 在代码中加载提示词

```python
from pathlib import Path

def load_prompt(workflow: str) -> str:
    """加载指定工作流的提示词"""
    prompts_dir = Path(__file__).parent / "references" / "prompts"
    
    prompt_files = {
        "security": "security-audit-prompt.md",
        "quality": "code-quality-prompt.md",
        "performance": "performance-review-prompt.md",
        "architecture": "architecture-review-prompt.md",
        "comprehensive": "ai-enhancer-prompt.md",
    }
    
    prompt_file = prompts_dir.get(workflow, "ai-enhancer-prompt.md")
    with open(prompts_dir / prompt_file, "r", encoding="utf-8") as f:
        return f.read()
```

### 2. 在 scan.py 中指定工作流

```python
# 使用安全审计工作流
python scripts/scan.py --repo ./my-project --base master --target HEAD --workflow security

# 使用性能优化工作流
python scripts/scan.py --repo ./my-project --base master --target HEAD --workflow performance
```

### 3. 在配置文件中指定

```yaml
# config.yaml
review:
  workflow: security  # security/quality/performance/architecture/comprehensive
  llm:
    url: https://api.example.com/v1/chat
    api_key_env: LLM_API_KEY
    model: gpt-4
```

---

> **LLM 参数以 `scripts/ai_reviewer.py::WORKFLOW_CONFIG` 为单一事实来源**，CLI 参数和 YAML 配置文件可覆盖默认值。

## 优先级定义

所有工作流统一使用以下优先级：

- **P0**: 立即修复（阻塞性问题，严重影响系统）
- **P1**: 本周修复（高优先级，可能影响功能或安全）
- **P2**: 本月修复（中优先级，需要改进但不紧急）
- **P3**: 下版本修复（低优先级，可延后处理）
- **P4**: 无需修复（误报、已有防护或影响可忽略）

---

## 扩展新工作流

如需添加新的工作流提示词，请遵循以下结构：

1. **角色定义**：明确 AI 的角色和职责
2. **评估维度**：定义评估的关键维度
3. **示例**：提供 2-3 个输入输出示例（包含真实问题和误报）
4. **输出格式**：定义 JSON 输出 schema
5. **字段说明**：详细说明每个字段的含义和取值范围
6. **API 参数**：定义合适的 temperature、max_tokens 等参数

---

## 最佳实践

1. **选择合适的温度**：安全/性能类使用 0.1，质量/架构类使用 0.2
2. **提供充足上下文**：在 `{actual_input}` 中包含完整的代码片段和上下文
3. **验证输出**：检查 AI 输出是否符合 JSON schema
4. **迭代优化**：根据实际效果调整提示词和示例
