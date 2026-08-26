# AI 审核机制详解

> [首页](../../README.md) / [文档索引](../README.md) / [核心机制](../README.md#核心机制详解) / **AI 审核**
>
> 对应实现：`scripts/ai_reviewer.py`（评审器主体）、`harness/`（反馈与质量监控）、`scan.py::tiered_ai_review`（分层编排）

---

## 1. 设计定位：LLM 是"复审法官"，不是"初审侦探"

静态引擎与 LLM 的分工是本机制最重要的架构决策：

```
错误路线：代码 ──全部丢给──> LLM ──> "我觉得这里有 8 个问题"
                            （不可复现、上下文放不下、幻觉检出、无法回归）

本项目：  代码 ──> 静态引擎（确定性检出，位置精确）──> LLM 只裁决 ──> 过滤/增强后的检出
                                （被告）              （法官）
```

这个分工的四个理由：

1. **确定性优先**：静态引擎给出精确的 (rule_id, file, line)，同一输入永远同一输出。LLM 的"感觉"不能作为检出来源，但适合做裁决。
2. **成本可控**：LLM 只处理引擎筛过的候选（且分层后只精审高严重级），token 消耗与检出量成正比，而不是与代码量成正比。
3. **职责匹配**：过滤误报需要的是"看懂这段代码的语义上下文"——恰是 LLM 的长处；全库找漏洞需要的是完备性——恰是 LLM 的短处。
4. **可审计**：检出来源可追溯到规则，LLM 的每个决策留痕（见第 6 节），出问题可以复盘。

## 2. 评审流水线

```
Prefilter + 熵门控后的候选问题
        │
        ▼
┌─ 分层评审（tiered）───────────────────────────────┐
│  CRITICAL / HIGH / ERROR ──► 送 LLM 精审          │
│  WARNING / INFO ──────────► 直接保留（统计层）      │
└────────────────────┬──────────────────────────────┘
                     ▼
        投票模式开启？（votes > 1）
         ├─ 否 ──► 单次评审路径
         └─ 是 ──► N 次独立采样 ──► 多数票裁决
                     │
                     ▼
        分批处理（每批 20 条，防 token 溢出）
                     │
                     ▼
        LLM 调用（低温采样，带重试）
                     │
                     ▼
        响应解析（两级映射：三元组精确 / 规则级回退）
                     │
                     ▼
        is_valid ∧ confidence ≥ 0.7 ──► 保留 + 增强字段
        否则 ──────────────────────► 过滤（审计留痕）
```

## 3. 分层评审（tiered review）

**策略**：只有 CRITICAL / HIGH / ERROR 级别进 LLM 精审；WARNING / INFO 只进统计层（计数、分组，不逐条消耗评审资源）。

**依据**（2026-08-24 双盲实测驱动）：WARNING+INFO 占检出近一半，逐条送 LLM 成本高且报告可读性差；而低严重级问题的"保留但不放大"处理对开发者体验无损。可用 `tiered: false` 回退全量评审。

这一层与静态层的降噪漏斗是衔接的：Prefilter（结构先验）和熵门控（信息论）先处理**可确定性判定**的噪音，LLM 只处理**需要语义理解**的疑难点——每个降噪层用最便宜的够用手段。

## 4. 投票机制（Self-Consistency）

**理论依据**：Self-Consistency（Wang et al. 2022）——对同一问题多次采样推理路径，取多数答案，能显著提升 LLM 决策的稳定性。应用于代码评审裁决：单次 LLM 判定存在采样方差（同一条问题两次评审可能一次保留一次过滤），多数票把"随机波动"滤掉，只留下"稳定判断"。

投票在**两条路径**上各自实现，同一配置项 `voting.votes` 控制：

### 4.1 API 路径（`AIReviewer._review_with_voting`）

```
votes = 3（配置项 voting.votes）
majority = votes // 2 + 1 = 2

第 1 票：deepcopy(issues) ──► 评审 ──► 保留集合 A
第 2 票：deepcopy(issues) ──► 评审 ──► 保留集合 B
第 3 票：deepcopy(issues) ──► 评审 ──► 保留集合 C

某问题出现在 ≥ 2 个保留集合 ──► 最终保留（取最后一次保留版本，含 AI 增强字段）
否则 ───────────────────────────► 过滤
```

三个工程细节：

- **深拷贝隔离**：每票独立 `deepcopy(issues)`，避免 `ai_confidence` 等字段在票间互相污染；
- **审计语义**：逐票的 kept/dropped 记录在投票结束后回滚，只写最终多数票裁决（reason 含 `majority_vote: 2/3 票（阈值 2）`）——否则 `total_input` 虚增 votes 倍；
- **偶数票陷阱**：votes=2 时 1:1 平票双方都达不到阈值、全部丢弃。**建议配置奇数票（3/5）**，文档中显式警告。

某票 LLM 失败时该票 fail-open（保留全部），不会让整个投票流程崩溃。

### 4.2 子 Agent 路径（`scan.py::_aggregate_votes`）

任务文件（`subagent-review-task.md`）在 votes > 1 时注入"投票委派要求"，主 Agent 并行委派 N 个**相互独立**的子 Agent 评审同一份任务文件，各自产出 `ai-review-result-vote{N}.json`；`_merge_subagent_review` 按键 (rule_id, file, line) 多数票聚合：

```
FP 票 ≥ majority → 滤除
TP 票 ≥ majority → 保留（字段取 TP 票中 ai_confidence 最高者）
无多数           → 保守保留，needs_review=true（转人工复核）
```

**与 API 路径平票语义的差异**：API 路径平票全丢弃；子 Agent 路径平票**保守保留**——子 Agent 路径覆盖 WARNING/INFO 低级别，且漏报 CRITICAL 的代价高于多一条待复核告警。

边界行为：评审员缺席某条问题不计数、损坏的投票文件跳过该票、全判误报时滤除仍生效。完整契约与真实验证数据（WebGoat 22 条三票一致率 90.9%）见 [SUBAGENT-REVIEW-ARCHITECTURE.md](../SUBAGENT-REVIEW-ARCHITECTURE.md#多评审员投票机制多数票聚合)。

**与双盲验证的关系**：投票机制（机器侧的多评审员）与双盲验证中的独立评审员一致性检验（人侧的多评审员）是同一思想在不同层的应用——裁决者的稳定性本身需要被度量。详见 [测试体系](testing.md)。

## 5. 工作流与提示词工程

五种工作流可切换（`--workflow` 参数 / config），各有专属提示词模板与参数：

| 工作流 | 提示词文件 | temperature | 输出增强字段 |
|--------|-----------|-------------|--------------|
| security（安全审计） | security-audit-prompt.md | **0.1** | `attack_vector`、`cvss_score` |
| quality（代码质量） | code-quality-prompt.md | 0.2 | `code_smell`、`technical_debt` |
| performance（性能） | performance-review-prompt.md | 0.1 | `performance_impact`、`expected_improvement` |
| architecture（架构） | architecture-review-prompt.md | 0.2 | `architecture_impact`、`design_violation` |
| comprehensive（综合） | ai-enhancer-prompt.md | 0.1 | — |

**低温设计的理由**：评审是裁决任务不是创作任务。temperature 0.1–0.2 把采样方差压到最低，配合投票机制实现"同一输入的稳定输出"。温度、批大小、阈值全部显式写入子 Agent 任务文件，评审过程参数透明。

**响应解析的两级映射**（修复实测缺陷）：LLM 响应常只含 rule_id 而省略 file/line，若只做三元组精确匹配则永远匹配不上。解析器先建精确映射（响应项带 file+line → 三元组），再建规则级映射（只带 rule_id），逐级回退。

## 6. 可靠性设计：fail-open 与审计轨迹

### 6.1 fail-open 原则

LLM 是**可用性弱依赖**：任何 LLM 侧故障都不能吞掉静态引擎的检出。

```
故障点                    行为
─────────────────────────────────────────────────────
LLM 调用失败（网络/超时）  重试（默认 2 次）→ 耗尽后返回原始批次
响应解析失败（非法 JSON）  重试 → 耗尽后返回原始批次
LLM 未配置/无 API Key     整个 AI 评审跳过，返回原始结果
AI 评审未启用             流水线正常走完（报告无 AI 字段）
投票中某票失败            该票 fail-open（保留全部）
```

语义：**宁可多报（噪音留给人工），不可漏报（AI 故障吞掉 CRITICAL）**。对安全工具而言，漏报的代价远高于误报。

### 6.2 审计轨迹（audit trail）

每一个被 AI 过滤掉的问题都必须留痕，可事后追溯（P0 级要求）：

```jsonl
{"timestamp": "...", "workflow": "security", "decision": "dropped",
 "rule_id": "xxe-java-document-builder", "file": "src/X.java", "line": 42,
 "severity": "ERROR", "ai_confidence": 0.4, "ai_is_valid": false,
 "match_type": "exact", "threshold": 0.7, "reason": "is_valid_false"}
{"timestamp": "...", "event": "llm_call_failed", "batch_index": 3,
 "batch_size": 20, "attempts": 3, "fail_open": true}
```

- **决策记录**：`decision=kept/dropped`，含完整上下文（rule_id/file/line/severity/置信度/匹配方式/理由）；
- **事件记录**：`llm_call_failed` / `parse_retry` / `parse_failed`，标记 fail_open；
- **落盘**：JSONL 追加写（`audit.log_path`），内存记录始终保留（enabled 只控制写文件）；
- **汇总**：`get_audit_summary()` 输出 kept/dropped 计数、**dropped_errors（被误杀的 ERROR 级问题数，人工复核优先回看）**、按规则分布的 dropped_by_rule、fail_open 次数。

审计解决的是 AI 评审的**问责问题**：当开发者质疑"为什么我的问题被过滤了"，答案必须是一条可查的记录，而不是"模型觉得"。

## 7. 子 Agent 委派架构

扫描完成后，`scan.py` 自动生成 `subagent-review-task.md` 任务文件，主 Agent 读取后通过 Task 工具**委派子 Agent** 执行 AI 评审——主 Agent 不自己评审（自己生成的候选自己裁决，会引入确认偏误）。配置 `voting.votes > 1` 时任务文件注入投票委派要求，主 Agent 并行委派 N 个独立评审员，多数票聚合（见第 4.2 节）。

任务文件是一份完整契约：

| 段落 | 内容 |
|------|------|
| 扫描概要 | repo / 分支对比 / profile / 工作流 / **温度参数** / 候选数 |
| 历史反馈统计 | 总反馈数、确认/误报/待定、**历史准确率** |
| 近期反馈示例 | 最近 10 条反馈（判定 + 备注），注入评审上下文 |
| 评审要求 | 决策必须给理由和证据；输出 JSON 字段契约（rule_id / is_false_positive / ai_confidence / analysis / enhanced_fix / evidence） |
| 投票委派要求 | votes > 1 时注入：并行委派 N 个独立评审员、各写 vote{N}.json、不得互相参考 |
| 待评审问题清单 | 每条含严重级、位置、引擎来源（多引擎互证标记） |

**反馈闭环**（harness 模块）：

```
评审输出 ──► 人工反馈（FeedbackManager：confirmed / false_positive / uncertain）
                │
                ▼
        反馈统计（历史准确率）+ 近期反馈示例
                │
                ▼
        注入下一次评审的任务文件（few-shot 校准）
                │
                ▼
        评审准确率随反馈积累上升（ empirically 更新先验）
```

这与降噪理论模块的设计一致：贝叶斯后验的引擎参数是"文档化假设，反馈数据积累后应经验更新"——反馈闭环就是那个经验更新通道。

## 8. 配置参考

```yaml
# config.yaml
ai_review:
  enabled: true
  workflow: security          # security/quality/performance/architecture/comprehensive
  tiered: true                # 分层评审（CRITICAL/HIGH/ERROR 精审）
  confidence_threshold: 0.7   # 置信度阈值，低于则过滤
  llm:
    url: https://api.example.com/v1/chat/completions
    api_key_env: OPENAI_API_KEY
    model: gpt-4
  voting:
    votes: 3                  # 建议奇数；1 = 禁用投票
  max_retries: 2              # LLM 调用/解析失败重试次数
  audit:
    enabled: true
    log_path: report/ai-audit.jsonl
```

## 9. 相关文档

| 主题 | 文档 |
|------|------|
| AI 评审的输入从哪来 | [扫描机制](scan-mechanism.md) |
| AI 评审效果的验证方法 | [测试体系](testing.md) |
| 子 Agent 委派的完整契约 | [SUBAGENT-REVIEW-ARCHITECTURE.md](../SUBAGENT-REVIEW-ARCHITECTURE.md) |
| 验证矩阵（P-01 ~ P-05） | [VERIFICATION_MATRIX.md](../VERIFICATION_MATRIX.md) |
