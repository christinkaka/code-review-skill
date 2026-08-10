# 代码评审 Skill

## 概述

本 Skill 指导主 Agent 执行代码评审任务。主 Agent 负责：
1. 识别用户意图，选择合适的工作流
2. 调用 Python 脚本进行确定性扫描（多引擎融合）
3. **委派子 Agent 进行代码评审**（使用温度参数确保严谨性）
4. 汇总评定决策，输出最终报告

## 核心架构

### 多引擎融合

扫描引擎采用三引擎融合架构：

| 引擎 | 分析层次 | 精准度 | 状态 |
|------|---------|--------|------|
| **Semgrep** | Pattern 匹配（基于 AST） | ⭐⭐⭐⭐⭐ | ✅ 主力引擎 |
| **Tree-sitter AST** | 语法树分析 | ⭐⭐⭐⭐⭐ | ✅ 补充引擎 |
| **内置正则** | 文本匹配 | ⭐⭐⭐ | ✅ 回退引擎 |

融合策略：
- 去重规则：同一文件/行/规则 ID 视为重复
- 保留优先级：AST > Semgrep > Regex

### 工作空间机制

每次扫描创建独立工作空间，避免并行冲突：

```
workspace/
├── {scan_id}/                    # 扫描ID: 时间戳_随机后缀
│   ├── report/                   # 扫描报告
│   ├── cache/                    # 规则编译缓存
│   └── decisions/                # 决策日志
```

## 工作流程

### Step 1: 识别用户意图

当用户触发代码评审时，主 Agent 需要：

1. **解析用户提示词**，确定：
   - 工作流类型：security / quality / performance / architecture / comprehensive
   - 扫描模式：diff 模式（需要 --base 和 --target）/ full-scan 模式
   - Profile：default / strict / minimal

2. **提取参数**：
   - 仓库路径（--repo）
   - 基线分支（--base）
   - 目标分支（--target）
   - 工作流（--workflow）

### Step 2: 执行确定性扫描

主 Agent 调用 scan.py 执行确定性扫描：

```bash
# 差异扫描模式
python scripts/scan.py \
  --repo <仓库路径> \
  --base <基线分支> \
  --target <目标分支> \
  --profile <profile> \
  --workflow <工作流>

# 全库扫描模式
python scripts/scan.py \
  --repo <仓库路径> \
  --full-scan \
  --profile <profile> \
  --workflow <工作流>
```

**scan.py 的职责**：
- Git diff 分析
- 调用图构建（Tree-sitter AST）
- 多引擎融合扫描（Semgrep + AST + Regex）
- 生成工作空间和报告文件
- 记录决策日志（Harness 系统）

**scan.py 不负责**：
- AI 评审
- 误报过滤
- 修复建议生成

### Step 3: 委派子 Agent 进行代码评审

**这是关键步骤**：主 Agent 需要委派一个子 Agent 来执行代码评审。

#### 3.1 确定温度参数

根据工作流类型，从 `config.yaml` 中读取对应的温度参数：

| 工作流 | 温度 | 说明 |
|--------|------|------|
| security | 0.1 | 安全审计需要最高严谨性 |
| quality | 0.2 | 代码质量评审需要较高一致性 |
| performance | 0.1 | 性能分析需要严谨性 |
| architecture | 0.2 | 架构评审需要一致性 |
| comprehensive | 0.1 | 综合评审需要严谨性 |

#### 3.2 委派子 Agent

主 Agent 读取 scan.py 生成的 `workspace/{scan_id}/report/subagent-review-task.md` 文件，委派子 Agent 执行评审。

**子 Agent 的职责**：
- 读取扫描结果文件
- 分析代码上下文
- 过滤误报（使用指定的温度参数）
- 生成修复建议
- 返回结构化评审结果（包含 evidence 字段）

### Step 4: 汇总评定决策

主 Agent 接收子 Agent 的评审结果后：

1. **解析评审结果**
2. **记录决策日志**（通过 Harness 系统）
3. **生成最终报告**：
   - 统计问题分布（按严重程度、类别）
   - 汇总修复建议
   - 生成可读的 Markdown 报告
4. **输出给用户**

## Harness 系统

Harness 系统提供 AI 评审的质量管控：

| 组件 | 功能 |
|------|------|
| **DecisionLogger** | 记录每个问题的 AI 决策、理由、证据 |
| **FeedbackManager** | 管理用户反馈，支持批量反馈 |
| **QualityMonitor** | 计算质量指标，监控评审准确率 |

### 反馈闭环

用户可以通过 CLI 提交反馈：

```bash
# 列出待反馈的问题
python harness/cli.py list

# 提交反馈
python harness/cli.py feedback <issue_id> confirmed "确认是真实问题"
python harness/cli.py feedback <issue_id> false_positive "这是误报"

# 查看统计
python harness/cli.py stats
```

反馈会在下次扫描时自动注入 AI 提示词，帮助 AI 学习用户的评审标准。

## 示例

### 示例 1: 安全审计

用户输入：
```
帮我扫描一下 release/1.0 分支和 master 分支的代码差异，看看有没有安全问题
```

主 Agent 执行：
1. 识别意图：工作流 = security，模式 = diff
2. 调用 scan.py：
   ```bash
   python scripts/scan.py --repo . --base master --target release/1.0 --workflow security
   ```
3. 读取工作空间中的 subagent-review-task.md
4. 委派子 Agent（温度 0.1）
5. 汇总评定决策，输出最终报告

### 示例 2: 全库扫描

用户输入：
```
对当前仓库执行代码评审，使用严格模式
```

主 Agent 执行：
1. 识别意图：工作流 = comprehensive，模式 = full-scan，profile = strict
2. 调用 scan.py：
   ```bash
   python scripts/scan.py --repo . --full-scan --profile strict --workflow comprehensive
   ```
3. 委派子 Agent（温度 0.1）
4. 汇总评定决策，输出最终报告

## 注意事项

1. **主 Agent 负责调度**：子 Agent 的委派由主 Agent 负责，不是 Python 脚本
2. **温度参数很重要**：必须使用低温度参数（0.1-0.2）确保评审的严谨性和一致性
3. **职责分离**：
   - Python 脚本：确定性扫描
   - 主 Agent：流程编排和结果汇总
   - 子 Agent：代码评审
4. **预编译机制**：修改规则文件后，必须运行预编译器更新缓存
5. **工作空间隔离**：每次扫描自动创建独立工作空间，支持并行扫描

## 规则管理

如果需要添加新规则，主 Agent 应该：

1. 读取 `references/RULE-GENERATOR-GUIDE.md` 了解规则格式和生成流程
2. 根据用户需求生成 Semgrep pattern
3. 将规则保存到对应的 Markdown 文件（如 `references/security/` 或 `references/implementation/`）
4. 运行预编译器：`python scripts/rule_compiler.py --compile`
5. 测试新规则是否正确检出
6. 继续 code-review 流程

**规则生成指南**：详见 [references/RULE-GENERATOR-GUIDE.md](../../../references/RULE-GENERATOR-GUIDE.md)
