# 代码评审 Skill

## 何时使用

当用户请求对代码进行评审、扫描、检查（如"扫描一下这个项目"、"评审 Jenkins 代码"等）时使用本 Skill。

## 核心职责

本 Skill 指导主 Agent 完成代码评审：

1. 调用 Python 脚本执行确定性扫描
2. **委派子 Agent**对扫描结果进行 AI 评审
3. 汇总评审结果，输出报告

## 执行流程

### Step 1: 解析用户意图

确定 4 个关键参数：
- `--repo`：被扫描仓库路径
- `--workflow`：security / quality / performance / architecture / comprehensive
- `--profile`：default / strict / minimal
- 扫描模式：`--full-scan`（全库）或 `--base <branch> --target <branch>`（diff）

### Step 2: 执行扫描

调用 `scan.py`，工作空间会自动创建在 `<被扫描项目>/.code-review/workspace/{scan_id}/`：

```bash
# 全库扫描
python scripts/scan.py --repo <path> --full-scan --workflow <wf> --profile <p>

# diff 扫描
python scripts/scan.py --repo <path> --base <base> --target <target> --workflow <wf>
```

扫描完成后，主 Agent **必须**读取 `<workspace>/report/subagent-review-task.md`，这是子 Agent 评审任务的完整定义。

### Step 3: 委派子 Agent

读取任务文件后，**调用 Task 工具**委派一个子 Agent 执行 AI 评审。

**关键约束**：
- 子 Agent 的提示词已由 `scan.py` 生成（基于 `references/prompts/`），**不要修改字段名或输出格式**
- 温度参数已在任务文件中指定（0.1-0.2），子 Agent 使用对应工作流的温度
- 单次委派即可，无需多 Agent 投票（prompt 已统一字段定义）

子 Agent 评审完成后，结果会写入 `<workspace>/report/agent-review.json`。

### Step 4: 汇总报告

主 Agent 接收子 Agent 结果后：
1. 解析 JSON 结果（字段：`is_false_positive`、`ai_confidence`、`analysis`、`enhanced_fix`）
2. 区分"原始扫描结果"（确定性）和"AI 评审结论"（概率性）
3. 输出最终报告给用户

## 注意事项

- **不要**自行修改 prompt 字段——所有 AI 评审字段定义唯一来源是 `references/prompts/ai-enhancer-prompt.md`
- **不要**直接调用 Semgrep/AST——这些都由 `scan.py` 内部处理
- **不要**让子 Agent 修改 `code-review-skill` 项目文件——所有输出在被扫描项目的 `.code-review/` 目录下
- 如果扫描失败或字段不一致，检查 `config.yaml` 和 `references/prompts/` 配置

## 详细文档

- 架构与设计：[README.md](../../../README.md)
- 规则开发指南：[references/RULE-GENERATOR-GUIDE.md](../../../references/RULE-GENERATOR-GUIDE.md)
