# 扫描机制详解

> [首页](../../README.md) / [文档索引](../README.md) / [核心机制](../README.md#核心机制详解) / **扫描机制**
>
> 对应实现：`scripts/scan.py`（流水线编排）、`scripts/diff_analyzer.py`、`scripts/call_graph.py`、`scripts/rule_engine.py`、`scripts/noise_theory.py`、`scripts/report_generator.py`

---

## 1. 设计定位：评审"变更"而非"全库"

代码评审的场景是 MR/PR：开发者关心的是**这次改动引入了什么问题**，不是全仓库的历史遗留。扫描机制的三条主线：

1. **范围收窄**——只扫变更文件，把扫描成本与变更规模成正比；
2. **多引擎融合**——AST / Semgrep / 正则三引擎按能力分级参与，离线环境不降级为零；
3. **分级降噪**——检出要经过白名单、熵门控、AI 复审三层过滤，宁可漏掉噪音也不淹没开发者。

## 2. 流水线总览

`scan.py::run_scan()` 编排五步流水线：

```
                     ┌────────────────────────────────────────────────────────┐
                     │                     扫描流水线                          │
                     └────────────────────────────────────────────────────────┘

[1/5] 差异分析          [2/5] 调用图           [3/5] 规约检查
DiffAnalyzer    →      CallGraphBuilder  →    RuleEngine.run()
git diff 双模式        Tree-sitter/正则        ┌─────────────────────────┐
变更文件/方法/行号      BFS 影响面分析          │ AST 引擎（始终执行）      │
                       depth-5 调用链          │ Semgrep（可用时并行）     │
                                              │ 正则（Semgrep 不可用回退）│
                                              └───────────┬─────────────┘
                                                          ▼
                                          多引擎合并去重 + 贝叶斯置信度
                                                          ▼
[4/5] AI 增强评审          [4.5] Prefilter 白名单 → 熵门控 → 分层评审
（详见 AI 审核文档）        20 类测试文件模式过滤    Shannon 熵判决硬编码检出
                           CRITICAL/HIGH/ERROR 精审；WARNING/INFO 统计层
                                                          ▼
[5/5] 报告生成
ReportGenerator：JSON + Markdown，调用链关联，独立工作空间
```

每步都有独立的工作空间隔离：`.code-review/{scan_id}/` 下建 `report/`、`cache/`、`decisions/`，避免污染被扫描项目和本工具项目。

## 3. 第一步：差异分析（DiffAnalyzer）

**职责**：确定扫描范围。输入 base/target 两个分支引用，输出变更文件清单、变更方法清单、diff 统计。

双模式实现：

| 模式 | 条件 | 特性 |
|------|------|------|
| GitPython | `git` 包可用 | `create_patch=True` 获取补丁文本（默认模式 diff 为空串，增删行数会**静默归零**——真实仓库实测发现的坑）；按 `+`/`-` 行首前缀统计增删行 |
| git CLI 后备 | GitPython 未安装 | `git diff --stat` + 全量 diff 文本解析 |

**变更方法提取**：解析目标分支文件内容提取方法定义（Java/Python/JS/TS 各有正则），再与 diff hunk 的变更行号求交集——只有**变更行落在方法体内**的方法才进入后续调用图分析。

```
@@ hunk header 解析变更起始行 → 变更行号集合
     ∩
文件方法定义区间 [line, end_line]
     =
changed_methods: [{file, name, line}]
```

## 4. 第二步：调用图（CallGraphBuilder）

**职责**：回答"这个变更会波及谁"。为 AI 评审提供血缘上下文，为报告提供调用链注解。

- **解析模式**：Tree-sitter 可用时用精确解析，否则正则近似（方法定义 + 方法体内调用名匹配）；
- **影响面分析**：以变更方法为起点，沿 callers 邻接表 **BFS 向上追溯**所有调用者——变更方法的 bug 会沿调用链向上放大，这是影响范围的定义；
- **调用链**：为每个变更方法向上追溯调用链（深度 5），报告中对每个检出标注 `call_chain`，帮评审者理解问题的传播路径。

调用链在盲测中的实际价值：Shiro-550 漏洞的检出说明（`@RequestMapping` 参数 → 反序列化 helper → `ObjectInputStream.readObject()`）正是靠这种血缘上下文让人工评审者快速确认真实性。

## 5. 第三步：多引擎并行检查（RuleEngine.run）

### 5.1 三引擎架构

| 引擎 | 实现 | 执行条件 | 优先级 | 灵敏度/误报假设 |
|------|------|----------|--------|-----------------|
| AST | `builtin_engine_v2.py`（Tree-sitter） | **始终执行** | 3（最高） | 0.90 / 0.05 |
| Semgrep | 外部进程 | `semgrep --version` 探测通过 | 2 | 0.80 / 0.10 |
| 正则 | `_run_with_builtin`（模式转正则） | **仅 Semgrep 不可用时** | 1（最低） | 0.60 / 0.20 |

三引擎不是冗余设计，而是**能力与可用性分层**：

- AST 引擎零外部依赖，保证内网/离线环境下工具不失效；
- Semgrep 承载 taint 数据流分析（AST/正则引擎原理上不支持数据流），是高严重级检出主力；
- 正则引擎是纯离线兜底，`$VAR → \w+`、`... → [\s\S]*?` 的模式转换覆盖 pattern 规则的近似执行。

**taint 降级透明化**：Semgrep 不可用时明确警告"N 条 taint 数据流规则本次无法执行，相关检出将缺失"，不静默吞掉能力差异——用户需要知道这次扫描的盲区在哪。

### 5.2 范围收窄与越界防护

扫描范围严格限定在 `changed_files`：

```
changed_files ──► --include <path>（逐文件传参）
                    │
                    ├─ ≤ 4000 个文件：argv 正常传递
                    │   （_INCLUDE_ARG_MAX：macOS argv ~1MB 上限保护，
                    │    按每对参数 ~120 字节保守取值）
                    │
                    └─ > 4000 个文件：不传 --include，改为
                        对结果做路径过滤兜底
                        （保证范围外文件的检出绝不泄漏进报告）
```

这是一个实测驱动的修复：此前 `target="."` 无视变更清单扫全仓库，50 文件输入时 1096/1097 条检出来自范围外文件——diff 扫描报告的全是未变更代码。

### 5.3 结果合并：优先级覆盖 + 贝叶斯置信度

合并键为 `(rule_id, file, line)` 三元组：

```
AST 检出 ─┐
          ├─► 同一 (rule_id, file, line)？
Semgrep ──┤      ├─ 是：保留最高优先级引擎内容，engines 列表记录全部
检出 ─────┘      │        confidence = 贝叶斯后验 P(TP|多引擎一致)
                 └─ 否：各自保留，confidence = 单引擎后验
```

**置信度不是拍脑袋常数，是校准概率**（`noise_theory.engine_agreement_posterior`）：

$$P(TP \mid E) = \frac{LR \cdot \pi}{LR \cdot \pi + (1 - \pi)}, \quad LR = \prod_i \frac{sensitivity_i}{false\_alarm_i}$$

- $\pi = 0.5$ 为最大熵先验（Jeffreys 选择：无反馈数据时最无偏）；
- 引擎参数（灵敏度/误报率）为文档化假设，可配置覆盖；
- 条件独立假设下双引擎一致检出的后验显著高于单引擎——多引擎互证是真实置信度的证据，不是装饰字段。

检出后追加 `(rule_id, file, line)` 去重，消除同一位置的多重报告。

## 6. 第四步：降噪漏斗

扫描的原始检出噪音很大（实测 Spring Boot 项目一次检出 359 个 path-traversal 命中，几乎全在测试文件）。降噪是**漏斗**结构，每层有明确的理论依据：

```
原始检出（三引擎合并后）
    │
    ▼ Prefilter 白名单 ──── 20 类测试文件模式（结构先验：测试代码不是生产攻击面）
    ▼ 熵门控 ───────────── Shannon 熵 + Miller-Madow 修正 + 字符集分层（信息论）
    ▼ AI 复审 ──────────── 分层评审 + 投票（见 AI 审核文档）
    │
最终报告
```

### 6.1 Prefilter 白名单（结构先验降噪）

默认 20 类 glob 模式覆盖主流测试文件约定：

| 类别 | 模式 |
|------|------|
| 测试目录 | `**/test/**`、`**/tests/**`、`**/__tests__/**`、`**/spec/**`、`**/dockerTest/**`、`**/integrationTest/**`、`**/smoke-test/**`、`**/test-support/**`、`**/testFixtures/**` |
| 测试命名 | `**/*Test.*`、`**/*Tests.*`、`**/*IT.*`、`**/*TestCase.*`、`**/*_test.*`、`**/test_*.py`、`**/*.spec.*`、`**/*.test.*`、`**/*Spec.*` |
| 加固示例 | `**/Safe.*`、`**/safe.*` |

设计逻辑：测试代码中的"漏洞"是靶场性质的教学/断言代码，不是生产攻击面——这是**结构先验**（路径即证据），命中即过滤，无需消耗 LLM 配额。白名单可经 config 扩展，也支持 `rule_id + file` 精确组合豁免。

### 6.2 熵门控（信息论降噪）

**问题**：硬编码凭证类规则（`crypto-hardcoded-key`）会把 `"username"`、`"test"` 这类低熵字面量也报出来。经验阈值（"长度 ≥ 8"）没有理论依据且不稳定。

**方案**（`noise_theory.is_high_entropy_secret`）：用信息论判据替代经验阈值，全部为**确定性纯函数**（同输入同输出）：

```
字面量判决流程（顺序短路）：

1. 模板占位符（${...} / {%...%} / <<...>>）      → 拒绝（结构判决）
2. URL（含 ://）/ URI 路径（/ 开头）/ HTTP 头名   → 拒绝（结构判据：
   （大写+连字符）/ 连字符自然词                     凭据不存在于这些语法命名空间）
3. n < 12                                        → 拒绝（统计判决：样本不足，
                                                     Miller-Madow 修正方差过大）
4. 字符集 = natural（含空白）                      → 拒绝（假设检验：非凭据字符集）
5. 凭据字符集（hex/base62/base64/alnum_sym）：
   H_MM ≥ 3.5 bits/char   （单位熵检验：接近均匀随机抽取）
   且 n · H_MM ≥ 32 bits  （总熵检验：暴力破解代价 ≥ 2^32）
                                                  → 保留（高熵凭据）
```

三个数学支柱：

1. **Shannon 熵（Shannon 1948）**：$H(s) = -\sum_i p_i \log_2 p_i$，度量每个字符平均携带的信息量。均匀随机抽取的字符串 $H \to \log_2 K$；重复模式 $H \to 0$。
2. **Miller-Madow 偏差修正（Miller 1955）**：有限样本下 plug-in 熵估计系统性低估真实熵，期望偏差约 $-(K-1)/(2n)$。修正估计量 $\hat{H}_{MM} = \hat{H} + (K-1)/(2n \ln 2)$。不修正则短字符串会被系统性低估而漏报。
3. **字符集分层检验**：绝对熵无法区分十六进制密钥（H=4.0）与英文文本（order-0 ≈ 4.1–4.5）——必须先按字符集分类（hex/base62/base64/alnum_sym/natural/placeholder），再在凭据字符集内做熵检验。

**已知局限（诚实声明）**：字符频率熵无法识别顺序结构（`"123456..."` 与随机数字同分布）——这是 Shannon 熵与 Kolmogorov 复杂度之间鸿沟的体现，detect-secrets / truffleHog 等业界工具同样存在；自然语言口令短语会被拒绝（此类值多为示例文案，报告价值低）。

**工程回退**：管理环境的 semgrep 会把匹配代码脱敏为固定文案，导致字面量提取失败。回退策略是回读源文件对应行重新提取（`entropy_snippet_source` 字段记录来源，可审计）。每条被拒绝的检出都带 `decision_trace`（拒绝理由），可事后追溯。

### 6.3 扫描级统计监控（FDR 与 Z-score）

`noise_theory.py` 还提供两个扫描级工具（供质量监控使用）：

- **期望错误发现率（BH 风格 FDR）**：N 条检出各带校准后验 $p_i$，则 $E[FP] = \sum_i (1-p_i)$。给定 FDR 预算 q，`bh_keep_count` 按后验降序保留最大前缀使 $\sum_{i \le k}(1-p_i)/k \le q$——Benjamini-Hochberg 程序在后验意义上的对应物。
- **规则维度 Z-score 离群检验**：规则检出量相对全体规则分布的标准化离群度 $z_j = (r_j - \mu_r)/\sigma_r$，$|z| \ge 2$ 判为噪音规则候选。用统计检验替代"Top N 排名"（后者随机且不稳定），这是统计过程控制（SPC）思想。

## 7. 第五步：报告生成

- **双格式输出**：`report.json`（机器可读，含全部字段）+ `report.md`（人读，按严重级分组）；
- **调用链关联**：每个检出附带 `call_chain` 字段，来源于第二步的调用图；
- **AI 增强字段透出**：`ai_confidence`、`enhanced_fix`、工作流特定字段（如 security 工作流的 `attack_vector` / `cvss_score`）；
- **摘要统计**：按 CRITICAL/HIGH/MEDIUM/LOW 分级计数，`confidence` 反映多引擎互证情况。

## 8. 理论依据汇总表

| 机制 | 理论基础 | 实现位置 |
|------|----------|----------|
| 多引擎优先级合并 | 证据分层：AST（精确语法）> Semgrep（语法+数据流）> 正则（文本近似） | `rule_engine._merge_multi_engine` |
| 多引擎置信度 | 贝叶斯后验校准（Jeffreys 先验 + 似然比乘积） | `noise_theory.engine_agreement_posterior` |
| Prefilter 白名单 | 结构先验：路径形态即噪音证据，先验 P(TP)≈0 | `scan.prefilter_issues` |
| 熵门控 | Shannon 熵 + Miller-Madow 修正 + 字符集分层假设检验 | `noise_theory.is_high_entropy_secret` |
| FDR 监控 | Benjamini-Hochberg 错误发现率控制 | `noise_theory.fdr_report` / `bh_keep_count` |
| 噪音规则监控 | Z-score 离群检验（统计过程控制） | `noise_theory.rule_z_scores` |
| 范围收窄 | 评审对象是变更而非全库；argv 边界 + 结果兜底双保险 | `rule_engine._run_with_semgrep` |

## 9. 工程边界（超时、降级与失败语义）

| 边界条件 | 行为 |
|----------|------|
| Semgrep 超时（300s） | 记录错误，返回空结果（不阻塞流水线） |
| semgrep rc=2（个别规则解析失败） | stdout 仍含其余规则的有效结果时照常解析；仅整份配置报废时记 error（区分"部分失败"与"全部失效"，此前不区分导致静默 0 检出） |
| LLM 不可用 | AI 评审整体跳过，返回原始结果（fail-open，详见 AI 审核文档） |
| Semgrep 不可用 | AST 始终执行 + 正则回退；taint 规则缺失明确告警 |
| 无代码变更 | 正常退出（退出码 0），不产生空报告 |
| 扫描异常 | Webhook 告警 + 退出码 1（调度场景可感知） |

## 10. 相关文档

| 主题 | 文档 |
|------|------|
| 规则如何编译为引擎输入 | [规则机制](rule-mechanism.md) |
| 第四步 AI 复审的完整设计 | [AI 审核](ai-review.md) |
| 降噪机制的验证数据 | [测试体系](testing.md) |
| 整体分层架构 | [architecture.md](../architecture.md) |
