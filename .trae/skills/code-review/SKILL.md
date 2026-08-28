---
name: "code-review"
description: "自动化代码评审工具。对指定 Git 仓库执行分支差异扫描、调用链分析、多规约（设计/实现/安全）自动评审，输出结构化问题报告与修复建议。当用户需要代码扫描、代码评审、安全规约检查、分支差异分析、调用链追踪时调用。"
---

# Code Review Skill

基于分层规约库（设计/实现/安全）执行自动评审，输出结构化问题报告与修复建议。

**核心理念**：确定性锚点（Semgrep/正则）+ AI 增强 + LLM 无关 + 离线优先 + 用户确认

---

## 触发条件

- 代码评审 / 代码扫描
- 检查 release 与 master 分支差异
- 安全规约检查（越权、XXE、XSS、目录穿越等）
- 调用链分析
- 生成评审报告

---

## 工作流概览

```
Step 0: 环境准备（Python 3.8+、依赖安装、Semgrep 检测）
    ↓
Step 1: 策略识别（意图/规模/扫描策略/Profile/投票配置）
    ↓
Step 1.5: 策略确认 ← 用户确认点（含外部规则加载交互）
    ↓
Step 2: 确定性扫描（Git diff + 调用图 + 规则匹配 → report.json + .scan-meta.json）
    ↓
Step 3: AI 增强评审（主 Agent 读 .scan-meta.json → 委派子 Agent → 等待投票文件就绪）
    ↓
Step 4: 结果合并（scan.py --merge-only → 多数票聚合 → 最终报告）
```

---

## Step 0: 环境准备

```bash
# 检测 Python
python3 --version  # 需要 3.8+

# 安装依赖（优先离线）
cd <skill-root>
if [ -d "offline-packages" ] && [ "$(ls -A offline-packages)" ]; then
    pip3 install --no-index --find-links=offline-packages -r requirements.txt
else
    pip3 install -r requirements.txt --break-system-packages
fi

# 检测 Semgrep（可选增强）
command -v semgrep && echo "Semgrep: $(semgrep --version)" || echo "Semgrep 未安装，使用正则引擎"
```

---

## Step 1: 策略识别与路由

### 扫描策略

| 策略 | 确定性扫描 | AI 增强 | 适用场景 |
|------|-----------|---------|----------|
| python-only | Semgrep/正则 | 无 | 快速扫描、离线 |
| ai-enhanced | Semgrep/正则 | 增强 | 日常评审（推荐） |
| hybrid | Semgrep（必须） | 增强 | 严格审查、安全审计 |

### 策略选择逻辑

```python
def select_scan_strategy(user_intent, semgrep_available, repo_size):
    if user_intent == "快速扫描": return "python-only"
    if user_intent == "严格审查" and semgrep_available: return "hybrid"
    return "ai-enhanced"  # 默认推荐
```

### 仓库规模评估

```bash
FILE_COUNT=$(find <repo> -type f \( -name "*.java" -o -name "*.py" -o -name "*.js" -o -name "*.ts" \) | wc -l)
# < 100: small (全量) | 100-1000: medium (增量) | > 1000: large (增量+分批)
```

### 投票配置

| 配置 | 值 | 说明 |
|------|-----|------|
| `voting.votes` | 1（默认） | 禁用投票，单评审员 |
| `voting.votes` | 3（推荐） | 3 票多数票，Self-Consistency |
| `voting.votes` | 5 | 更高稳定性，成本 5 倍 |

投票配置从 `config.yaml` 的 `ai_review.voting.votes` 读取，或由用户在策略确认阶段指定。

---

## Step 1.5: 策略确认（用户确认点）

**⚠️ 执行前必须与用户确认策略。**

### 1.5.0 规则配置检测（AI 主动执行）

展示策略前，AI **必须主动执行**：

1. **检测项目语言**：扫描目标仓库主要编程语言
2. **检测已有外部规则**：检查 `references/external/` 是否已有规则
3. **匹配推荐规则库**：根据语言匹配

| 项目语言 | 推荐规则库 | 说明 |
|---|---|---|
| Java / Kotlin | android-security | OWASP MASTG 移动安全 |
| C / C++ | 0xdea-c-cpp | 内存安全、缓冲区溢出 |
| JavaScript / TypeScript | dom-xss | DOM XSS 深度检测 |
| 任意语言 | semgrep-official | OWASP Top 10 全集 |

### 1.5.1 展示策略

```
═══════════════════════════════════════════════════════════════
                    代码评审策略确认
═══════════════════════════════════════════════════════════════

## 1. 扫描策略
• 策略: ai-enhanced | Profile: default | 模式: 增量扫描

## 2. 规则配置
• 内部规则: 98 条（security 67 + design 16 + implementation 15）
• 外部规则: 0 条（尚未加载）
• 检测到项目语言: Java, Python
• 推荐: semgrep-official（15.8k stars）- OWASP Top 10 全集

## 3. AI 增强配置
• 工作流: security | 温度: 0.1 | 置信度阈值: 0.7
• 评审模式: 子 Agent 委派 | 投票: 3 票（Self-Consistency）

## 4. 预期输出
• report.json + report.md + summary.json + 投票文件 → report/ 目录

═══════════════════════════════════════════════════════════════

请确认策略：
1. ✅ 确认执行
2. 📦 加载外部规则
3. 🔧 调整策略
4. ❌ 取消执行
```

### 1.5.2 处理用户反馈

**选择 1 "确认执行"** → 继续 Step 2

**选择 2 "加载外部规则"**（关键交互）：

**第一步**：展示推荐规则库

```
推荐的外部规则库：
1. semgrep-official（15.8k stars）- OWASP Top 10 全集，20000+ 规则
2. 0xdea-c-cpp（~500 stars）- C/C++ 内存安全
3. android-security（335 stars）- Android 移动安全
4. dom-xss（~30 stars）- JavaScript DOM XSS

请选择（可多选，如 1,3）：
```

**第二步**：用户选择后执行加载

```bash
python3 scripts/rule_loader.py --from recommended --repo-key <选择的库>
```

**第三步**：展示结果

```
已加载 50 条规则，来源: 0xdea-c-cpp
规则示例：raptor-write-into-stack-buffer、raptor-double-free...

是否继续加载？1. 继续  2. 完成，返回策略确认
```

**第四步**：更新策略展示，重新确认

**选择 3 "调整策略"** → 询问调整内容（策略/Profile/AI模式/置信度/外部规则管理）→ 重新展示

**选择 4 "取消执行"** → 取消

---

## Step 2: 确定性扫描（必须执行）

**这是确定性锚点，不依赖 LLM。**

```bash
# Git 差异分析
python3 scripts/diff_analyzer.py --repo <repo> --base master --target release/1.0 --output diff_result.json

# 调用图构建
python3 scripts/call_graph.py --repo <repo> --diff-result diff_result.json --output call_graph.json

# 规则匹配（Semgrep 或正则）
python3 scripts/rule_engine.py --repo <repo> --diff-result diff_result.json --specs-dir references/ --profile default --output deterministic_issues.json
```

**输出**：确定性问题列表，confidence=1.0，可重现。

---

## Step 3: AI 增强评审（子 Agent 委派）

Step 2 完成后，scan.py 在输出目录生成两个关键文件：
- `subagent-review-task.md` — 评审任务文件（含待评审问题清单、裁决契约、投票委派说明）
- `.scan-meta.json` — 编排元数据（主 Agent 读取后执行确定性委派）

### 3.1 读取编排元数据

```bash
cat <output_dir>/.scan-meta.json
```

输出示例：
```json
{
  "output_dir": "reports/e2e-ruoyi-v4.8.1",
  "task_file": "reports/e2e-ruoyi-v4.8.1/subagent-review-task.md",
  "report_file": "reports/e2e-ruoyi-v4.8.1/report.json",
  "votes": 3,
  "issue_count": 45,
  "workflow": "security"
}
```

### 3.2 委派子 Agent（确定性协议）

根据 `votes` 字段决定委派模式：

**votes = 1（单评审员）**：
- 委派 **1 个**子 Agent（Task 工具，subagent_type: general_purpose_task）
- 子 Agent 读取 `task_file`，对全部 `issue_count` 条问题逐条裁决
- 输出写入 `<output_dir>/ai-review-result.json`

**votes > 1（多评审员投票）**：
- **并行**委派 `votes` 个**相互独立**的子 Agent（同一消息中发起多个 Task 调用）
- 每个子 Agent 读取**相同的** `task_file`，独立裁决全部 `issue_count` 条问题
- 第 N 个评审员输出写入 `<output_dir>/ai-review-result-vote{N}.json`
- 评审员之间**不得共享结论或互相参考**（Self-Consistency 的前提）

### 3.3 子 Agent 提示词模板

每个子 Agent 的 prompt 必须包含以下要素（主 Agent 按此模板构造）：

```
你是代码评审员 {N}/{votes}（共 {votes} 位相互独立的评审员之一）。

## 输入
1. 任务文件：<task_file 绝对路径>
2. 被扫描仓库：<repo 绝对路径>（已 checkout 到目标版本）

## 工作流程
1. 读任务文件的待评审问题清单（{issue_count} 条）
2. 对每条问题，用 Read 读取 file:line 处的实际源代码后再下判断
3. 按裁决标准逐条输出

## 裁决标准
- is_false_positive=true：当前上下文安全（非目标文件类型、已有加固/白名单等）
- is_false_positive=false：确需修复的真实问题
- needs_review=true：代码不可读或上下文不足，保守不裁决
- ai_confidence：0.9-1.0 明确；0.7-0.9 比较确定；0.5-0.7 需人工确认

## 输出
将全部 {issue_count} 条评审结果写入：<output_dir>/ai-review-result-vote{N}.json
（单评审员模式写入 ai-review-result.json）

## 禁止事项
- 不得修改被扫描仓库内任何文件
- 不得读取其他评审员的输出文件
- 不得声称"已读代码"但 analysis 中没有引用具体代码特征
- 必须覆盖全部 {issue_count} 条，一条不落
```

### 3.4 等待投票文件就绪

子 Agent 完成后，主 Agent 验证输出文件：

```bash
# 单评审员：检查 ai-review-result.json 存在且非空
ls -la <output_dir>/ai-review-result.json

# 投票模式：检查全部 vote 文件存在
ls -la <output_dir>/ai-review-result-vote*.json
# 期望文件数 = votes
```

如有缺失，检查子 Agent 执行日志，必要时重新委派。

---

## Step 4: 结果合并与报告生成

### 4.1 触发合并

子 Agent 评审完成后，主 Agent 执行合并命令：

```bash
python3 scripts/scan.py --merge-only --output <output_dir>
```

该命令：
1. 读取 `<output_dir>/report.json`（Step 2 生成的原始报告）
2. 读取投票文件（`ai-review-result.json` 或 `ai-review-result-vote{N}.json`）
3. 执行多数票聚合（投票模式）或直接合并（单评审员）
4. 更新 `report.json`（滤除多数票判误报的条目，合并 AI 增强字段）
5. 输出合并后的问题数

### 4.2 聚合规则（投票模式）

```
majority = votes // 2 + 1    （3 票需 ≥ 2 票）

对每条问题（键 = rule_id + file + line）：
  FP 票 ≥ majority  → 滤除（多数票认定误报）
  TP 票 ≥ majority  → 保留（取 TP 票中 ai_confidence 最高者）
  无多数            → 保守保留，needs_review=true（转人工复核）
```

### 4.3 最终报告

合并完成后，`<output_dir>/` 下包含：
- `report.json` — 最终结构化报告（已合并 AI 字段）
- `report.md` — Markdown 可读报告
- `summary.json` — 统计摘要
- `ai-review-result-vote{N}.json` — 各评审员原始裁决（留档可审计）

---

## 规约库结构

```
references/
├── design/               # 设计规约（architecture/api-design/database）
├── implementation/       # 实现规约（naming/error-handling/concurrency/null-safety）
├── security/             # 安全规约（authorization/xxe/xss/path-traversal/...）
├── external/             # 外部加载规则（从 GitHub 高分仓库）
├── rules/                # 自定义业务规则
├── profiles/             # 规约配置（default/strict/minimal）
├── prompts/              # 提示词模板
└── test-cases/           # 测试案例
```

### Markdown 规约格式

```markdown
# XXE - DocumentBuilderFactory 未禁用外部实体
> XML 解析器未禁用外部实体，攻击者可读取服务器文件。

```yaml
id: xxe-java-document-builder
languages: [java]
severity: ERROR
cwe: CWE-611
```

## 违规示例
```java
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.parse(inputStream);
```

## 检测模式
```pattern
DocumentBuilderFactory $factory = DocumentBuilderFactory.newInstance();
...
$factory.parse(...);
```
```

---

## 规约预编译（推荐）

将自然语言规约转换为 Semgrep 规则，带安全审核机制。

**流程**：人写自然语言 → AI 生成规则草稿 → 差异对比 → **人工确认** → 部署

**⚠️ AI 行为要求**：禁止自动部署，必须等待用户确认。

详见 `references/rule-compiler-guide.md`

---

## 外部规则加载（推荐）

从高分开源规约库加载经过验证的规则，无需从零编写。

**推荐规则库**：Semgrep 官方（15.8k stars）、0xdea C/C++（~500）、Android Security（335）、DOM XSS（~30）

**⚠️ AI 行为要求**：策略确认阶段主动询问用户是否需要加载外部规则。

详见 `references/external-rules-guide.md`

---

## LLM 稳定性保障

**核心**：确定性锚点 + 结构化约束 + 提示词增强

1. **确定性锚点**：Python 脚本扫描的问题必须保留，AI 不能删除
2. **结构化输出**：强制 JSON Schema
3. **规则绑定**：severity/rule_id 由规则定义，AI 不能改
4. **置信度阈值**：AI 结果需达到 0.7 才被采纳
5. **回退机制**：AI 不稳定时回退到纯 Python 结果

无论使用 GPT-4/Claude/本地模型，**确定性问题列表始终一致**。

---

## 常见问题

**Q: 不同 LLM 结果不一致？** A: 确定性锚点保证核心结果一致，AI 增强只是锦上添花。

**Q: 如何选择扫描策略？** A: 快速→python-only | 日常→ai-enhanced | 严格→hybrid

**Q: AI 增强必须启用？** A: 不是必须，离线环境自动跳过。

**Q: 如何添加自定义规则？** A: 编辑 `references/rules/custom.md`，运行 `python scripts/test_rules.py` 验证。

**Q: 外部规则和内部规则冲突？** A: 独立管理，不会冲突。相同问题会分别报告。
