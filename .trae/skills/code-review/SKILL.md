# 代码评审 Skill

## 何时使用

当用户请求对代码进行评审、扫描、检查（如"扫描一下这个项目"、"评审 Jenkins 代码"等）时使用本 Skill。

## 核心职责

本 Skill 指导主 Agent 完成代码评审：

1. 调用 Python 脚本执行确定性扫描
2. **预过滤**：对显式误报规则用确定性引擎过滤（可配置）
3. **委派子 Agent**对过滤后的结果进行 AI 评审
4. 汇总评审结果，输出报告

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

扫描完成后，`scan.py` 会：
1. **预过滤**：对显式误报规则（如 `sqli-mybatis-dollar`、`crypto-hardcoded-key-java`、`naming-*`）用确定性引擎过滤
2. **生成子 Agent 任务**：只包含待 AI 评审的问题（已过滤的不会出现在任务中）

主 Agent **必须**读取 `<workspace>/report/subagent-review-task.md`，这是子 Agent 评审任务的完整定义。

### Step 3: 委派子 Agent

读取任务文件后，**调用 Task 工具**委派一个子 Agent 执行 AI 评审。

**关键约束**：
- 子 Agent 的提示词已由 `scan.py` 生成（基于 `references/prompts/` 和 `references/subagent-contract.md`）
- **不要修改字段名或输出格式**
- 温度参数已在任务文件中指定（0.1-0.2）
- 单次委派即可，无需多 Agent 投票（prompt 已统一字段定义）

子 Agent 评审完成后，结果会写入 `<workspace>/report/agent-review.json`。

### Step 4: 汇总报告

主 Agent 接收子 Agent 结果后：
1. 解析 JSON 结果（字段：`is_false_positive`、`ai_confidence`、`analysis`、`enhanced_fix`）
2. 区分"原始扫描结果"（确定性）、"预过滤结果"（确定性）和"AI 评审结论"（概率性）
3. 输出最终报告给用户

## 规约机制

### 主 Agent 规约
- 位置：`references/main-agent-contract.md`
- 职责：调度扫描、委派子 Agent、汇总报告
- 约束：不能直接评审代码、不能修改 prompt 字段、不能跳过预过滤

### 子 Agent 规约
- 位置：`references/subagent-contract.md`
- 职责：对扫描结果进行二次评审
- 约束：不能修改项目文件、不能修改字段定义、不能对显式误报规则做 AI 判断（这些已由预过滤处理）
- 强制要求：先读代码再判断

### 预过滤机制
- 位置：`config.yaml` 中的 `prefilter` 配置
- 开关：`prefilter.enabled: true/false`（可回退）
- 规则：
  - `sqli-mybatis-dollar`：在 pom.xml 或 .xml 文件中，且包含 `${...}` 模式 → 误报
  - `crypto-hardcoded-key-java`：在 Constants 类或 constants 目录中 → 误报
  - `naming-*` 规则：直接标记为误报
  - `short-code-snippet`：code_snippet 长度 < 5 行 → 标记为 needs_review

## 规则与缓存管理

### 规则预编译机制

`scan.py` 通过 `RuleEngine` 加载 `references/*.md` 规则文件。`RuleEngine` 内部会自动初始化 `RuleCompiler`，**优先从预编译缓存加载**：

- 缓存目录：`references/compiled/`（含 `manifest.json`）
- 工作原理：缓存记录每个 `.md` 文件的 hash，若 hash 与当前一致则直接加载 JSON，跳过 Markdown 解析

### 何时需要重新编译缓存

修改 `references/security/*.md`、`references/implementation/*.md`、`references/design/*.md` 等规则文件后：

```bash
# 强制重新编译所有规则
python scripts/rule_compiler.py --compile --force

# 检查编译状态
python scripts/rule_compiler.py --status
```

**注意**：缓存 hash 不匹配时 `rule_engine.py` 会自动回退到直接解析 Markdown（`从缓存加载` → `缓存无效，重新解析`）。但主动编译可确保一致性。

### 调试规则加载

如需确认规则是否从缓存加载，启动 `scan.py` 时加 `--log-level DEBUG`：

```bash
python scripts/scan.py --repo <path> --full-scan --log-level DEBUG
```

日志中可见 "从缓存加载 X.md" 或 "缓存无效，重新解析"。

## 注意事项

- **不要**自行修改 prompt 字段——所有 AI 评审字段定义唯一来源是 `references/prompts/ai-enhancer-prompt.md`
- **不要**直接调用 Semgrep/AST——这些都由 `scan.py` 内部处理
- **不要**让子 Agent 修改 `code-review-skill` 项目文件——所有输出在被扫描项目的 `.code-review/` 目录下
- 修改规则后**必须**运行 `rule_compiler.py --compile`，否则缓存可能过期
- 如果扫描失败或字段不一致，检查 `config.yaml` 和 `references/prompts/` 配置

## 详细文档

- 架构与设计：[README.md](../../../README.md)
- 规则开发指南：[references/RULE-GENERATOR-GUIDE.md](../../../references/RULE-GENERATOR-GUIDE.md)
