# 测试体系详解

> [首页](../../README.md) / [文档索引](../README.md) / [核心机制](../README.md#核心机制详解) / **测试体系**
>
> 对应实现：`tests/`（605 个测试）、`scripts/dual_blind_test.py`（盲测脚本）、`scripts/test_rules.py`（规则测试）、`references/test-cases/`（测试用例库）

---

## 1. 设计定位：验证"泛化能力"而非"预期行为"

安全规则工具最大的验证陷阱是**自证清白**：规则作者写测试用例，测试用例天然覆盖规则的设计意图，但不覆盖规则盲区。E2E 测试通过只证明"规则在预期场景下工作"，不证明"规则在未知场景下不误报"。

本项目的测试体系因此有两个轴：

- **纵向（常规工程轴）**：单元 → 集成 → E2E，保证功能正确、防止回归；
- **横向（实证轴）**：golden test → 靶场盲测 → 双盲验证，度量真实精确率与泛化能力。

```
                        ┌─────────────────────────────────────┐
                        │      双盲验证（泛化实证）             │  L3
                        │  规则作者未知的代码库 × 独立评审员      │
                        └───────────────▲─────────────────────┘
                        ┌───────────────┴─────────────────────┐
                        │      靶场盲测（真实精确率）           │  L3 凭证
                        │  java-sec-code / WebGoat 全量实测    │
                        └───────────────▲─────────────────────┘
                        ┌───────────────┴─────────────────────┐
                        │      E2E（真实 semgrep 行为固化）      │  L2
                        │  TP/TN 矩阵：违规样本必中、加固样本必免  │
                        └───────────────▲─────────────────────┘
                        ┌───────────────┴─────────────────────┐
                        │      Golden Test（编译产物 oracle）    │
                        │  自然语言规约的编译产物行为断言          │
                        └───────────────▲─────────────────────┘
                        ┌───────────────┴─────────────────────┐
                        │      单元 / 集成（605 个测试）         │  L1
                        │  解析、引擎、评审器、降噪理论、边界       │
                        └─────────────────────────────────────┘
```

## 2. 测试分层

全量 605 个测试（`pytest tests/`），按验证对象分层：

### 2.1 单元层（纯函数与模块行为）

| 测试文件 | 验证对象 |
|----------|----------|
| `test_markdown_parser.py` | DSL 解析：section 拆分、yaml/pattern/taint 块、语言分组、metavariable-regex 校验 |
| `test_rule_engine.py` | 规则加载、多语言拆分、taint 构建入口点展开、focus 后缀、sink 排除复合 |
| `test_ai_reviewer.py` / `test_ai_reviewer_audit.py` | 评审器：提示词构建、响应解析两级映射、置信度阈值、审计留痕 |
| `test_noise_theory.py` / `test_noise_reduction.py` | 降噪理论：熵计算正确性、Miller-Madow 修正、字符集分类、贝叶斯后验、FDR、Z-score |
| `test_prefilter.py` | 白名单 20 类模式匹配、规则+文件组合豁免 |
| `test_diff_analyzer.py` / `test_call_graph.py` | 变更文件/方法提取、BFS 影响面、调用链 |
| `test_rule_sandbox.py` | 外部规则结构校验、坏规则拦截 |
| `test_entropy_gate_fallback.py` | snippet 脱敏时的源文件回读回退 |
| `test_taint_rules.py` / `test_taint_compiler.py` | taint 规则结构、taint 编译、降级语义 |
| 其余 | 报告生成、调度、通知、harness、子 Agent 任务、一致性检查等 |

### 2.2 集成层（模块间协作）

- `test_semgrep_integration.py` / `test_semgrep_scope.py`——真实调用 semgrep 的范围控制与输出解析（check_id 前缀剥离、`__{lang}` 后缀还原、rc=2 语义区分）；
- `test_multi_engine.py`——三引擎结果合并、优先级覆盖、贝叶斯置信度；
- `test_scan.py`——流水线编排（diff → 调用图 → 规则 → prefilter → 报告）；
- `test_dual_blind.py`——完整流程（引擎 + mock LLM 评审 + 报告）的仓库级冒烟。

### 2.3 E2E 层（真实 semgrep，行为固化）

`test_taint_e2e.py`、`test_pattern_rules_e2e.py`、`test_command_injection_e2e.py`、`test_expression_injection_e2e.py`、`test_log_injection_e2e.py`、`test_ai_reviewer_e2e.py` 等。

以 `test_taint_e2e.py` 为例，一个测试类内嵌一组 Java 方法样本，构成 **TP/TN 矩阵**：

| 样本方法 | 形态 | 预期 |
|----------|------|------|
| `readUserFile` | `request.getParameter` → `Files.readAllBytes` | **命中**（TP） |
| `readConstFile` | 常量路径拼接 | **不命中**（TN：无污点源） |
| `readSanitized` | `new File(userPath).getName()` 净化后使用 | **不命中**（TN：净化器生效） |
| `upload` | `getOriginalFilename()` → 传输 | **命中**（TP：文件名污点源） |
| `normalized` | `normalize()` + 前缀校验加固 | **不命中**（TN：加固豁免） |

E2E 测试的价值：**违规形态必检出、安全形态必豁免**是规则的行为契约，固化进测试后，任何破坏该契约的规则改动（DSL 修改、编译逻辑修改、semgrep 升级）都会被立即拦截。本机无 semgrep 时自动 skip（不假绿）。

### 2.4 Golden Test（编译产物 oracle）

`test_rule_compiler_golden.py` / `test_rule_compiler_llm.py`：对自然语言规约的编译产物执行 golden 断言（违规示例命中、安全示例不命中、pass_rate 计算、CEGIS 重试轮次），是 [规则机制](rule-mechanism.md) 第 6 节预编译链路的测试侧对应物。

### 2.5 测试用例库（人读形态）

`references/test-cases/security/*.md`：每个漏洞类别一份 Markdown 测试用例（违规代码 + 预期命中规则 + 文件类型），与规约一一对应。既是人工评审的参考，也是 e2e 测试用例的来源。

## 3. 规则质量阶梯（L0–L3）

质量阶梯是横向轴的标尺——**规则数量不说明能力，等级才说明**：

```
L0 ─────────────► L1 ─────────────► L2 ─────────────► L3
未覆盖    可解析回归通过    e2e TP/TN 固化    靶场盲测零误报
(有CWE归属   (规则存在且      (真实semgrep      (规则作者未知的
 无规则)      不静默失效)      行为契约进tests)   代码库实测达标)
```

| 等级 | 定义 | 达标凭证 | 当前状态 |
|------|------|----------|----------|
| L0 | 有 CVE/CWE 归属、无规则 | — | 8 格待扩展（见能力地图） |
| L1 | 规则存在且可解析 | 全量可解析性回归通过（rc=2 防护） | 全部规则 |
| L2 | 端到端行为固化 | 真实 semgrep e2e（TP/TN 矩阵）进 tests/ | 32 条规则覆盖 |
| L3 | 靶场盲测零误报 | 靶场全量实测 TP/FP 记录进盲测报告 | 11 类（含 11 条 taint 全部） |

等级数据由 `docs/capability-map.md` 从规则库**实时推导**（脚本生成，人工只维护薄数据层的等级与靶场凭证），地图永不与规则库脱节。

## 4. 双盲验证方法论

### 4.1 为什么需要双盲

安全规则验证的三个确认偏误来源：

1. **测试用例由规则作者编写**——天然覆盖设计意图，不覆盖盲区；
2. **E2E 通过 ≠ 不误报**——预期场景工作与未知场景不误报是两个命题；
3. **单一靶场模式拟合**——靶场的漏洞模式可能恰好匹配规则 pattern，无法检验泛化。

### 4.2 框架

```
┌─────────────────────────────────────────────────────┐
│                    双盲验证框架                        │
└──────────────────┬──────────────────────────────────┘
                   │
   ┌───────────────┼───────────────┐
   ▼               ▼               ▼
第一盲：靶场泛化   第二盲：多评审员    收敛：质量判定
(Generalization)  (Consistency)    (Adjudication)
   │               │               │
规则作者未知的      独立评审员        TP/FP 判定 +
代码库零先验扫描    背靠背判定        精确率 ≥ 95%
                   计算一致性        方可晋升 L3
```

- **第一盲（靶场泛化）**：扫描规则作者从未见过的真实漏洞靶场（java-sec-code 32 类漏洞 controller、OWASP WebGoat），规则无法针对靶场"应试"；
- **第二盲（多评审员）**：检出的 TP/FP 判定由独立评审员背靠背完成，度量评审员间一致性——这一思想与 AI 评审的投票机制（[AI 审核](ai-review.md) 第 4 节）同构：裁决者自身的稳定性需要被度量；
- **收敛判定**：精确率达标才能晋升 L3，未达标的规则回炉修复后重测。

### 4.3 实测数据汇总

| 靶场 | 性质 | 检出 | TP | FP | 精确率 | 报告 |
|------|------|------|----|----|--------|------|
| java-sec-code | 真实漏洞靶场（方法级盲测） | 37 | 37 | 0 | **100%** | [blind-test-java-sec-code.md](../blind-test-java-sec-code.md) |
| OWASP WebGoat | Spring Boot 教学靶场（第二泛化验证） | 49 | 48 | 1 | **97.96%** | [blind-test-webgoat.md](../blind-test-webgoat.md) |
| freeCodeCamp / Django / Spring Boot | 真实开源仓库（3 语言全链路） | — | — | — | 噪音验证 | [validation.md](../validation.md) |

代表性检出（泛化能力的直接证据）：

- **Shiro-550 反序列化**：入口点 `HttpServletRequest` 参数锚定为污点源，经 **5 层调用链**命中 `ObjectInputStream.readObject()`——规则未针对该场景编写，纯靠数据流语义泛化命中；
- **文件上传路径穿越**：`getOriginalFilename()` 源在私有辅助方法直接生效；
- **TomcatFilterMemShell 内存马 RCE 点**（命令注入规则）；
- WebGoat 唯一 FP（`path-traversal-pattern` 对 `replace("../", "")` 过滤形态的判定分歧）反过来驱动了规则修复。

### 4.4 盲测驱动的修复闭环

盲测不只是"打分"，其产出直接进入规则修复：java-sec-code 盲测发现 5 条 taint 规则 2 处 FP 与 1 条静默失效规则，修复后从 10 TP + 2 FP 提升到 **11 TP + 0 FP**；2 条 pattern 规则从 5 TP + 5 FP 修复到 5 TP + 3 FP。三个代表性修复：

1. **sqli-taint 类型化 sink**：Semgrep 类型化元变量不做子类型匹配 → 显式枚举 PreparedStatement/Statement/CallableStatement；
2. **XXE reader 级加固豁免**：`createXMLReader()` 后 `setFeature` 的加固形态补 `pattern-not-inside`；
3. **arch 规则静默失效**：`$CLASSImpl` 含小写字母是非法元变量，自创建起从未生效 → 发现后先按禁用处理，再通过 `pattern-metavariable-regex` DSL 扩展（`$CLASS: .*Impl`）复活。

## 5. 防回归的专项设计

### 5.1 全量可解析性回归（防静默失效）

**问题**：semgrep 对个别规则解析失败会 rc=2 但继续运行其余规则；若一条规则因语法错误从未生效，没有任何报错——规则清单虚胖、检出静默缺失（`$CLASSImpl` 事件就是如此，静默失效数月才被发现）。

**对策**：回归测试对全部规则跑可解析性断言，任何规则退化为不可解析立即红灯。这是 L1 的达标凭证。

### 5.2 Profile 完备性测试（防孪生漂移）

每个结构化规约 md 必须有对应的静态孪生 yaml（`references/security/<stem>.yaml`），测试强制校验——新增规约忘记导出孪生产物会被拦截。

### 5.3 Marker 精确断言（防注释行抢先命中）

**踩坑两次的教训**：断言用的 marker 若与代码文本相同，注释行会抢先命中（测试通过但断言的是注释不是代码）。对策：marker 带前缀/后缀区分代码行与注释行，例如断言 sink 行而不是数组初始化行（semgrep 报告位置是 **sink 行**而非污点产生行）。

### 5.4 失败样本累积（CEGIS 在测试侧的对应）

规则编译的每轮 golden test 失败原因累积进测试集；盲测发现的每个 FP 也转化为新的 TN 样本进 e2e 矩阵——**缺陷即测试用例**，同一个坑不允许踩第二次。

## 6. 运行方式

```bash
# 全量回归（605 tests）
python3 -m pytest tests/ -v

# 仅真实 semgrep e2e（本机需安装 semgrep）
python3 -m pytest tests/test_taint_e2e.py tests/test_pattern_rules_e2e.py -v

# 单规则快速验证（规则测试脚本）
python3 scripts/test_rules.py --rule cmdi-taint

# 靶场盲测（完整流程：引擎 + mock LLM + 报告）
python3 scripts/dual_blind_test.py
```

无 semgrep 环境下 e2e 自动 skip（不假绿）；CI 中建议安装 semgrep 跑全量。

## 7. 相关文档

| 主题 | 文档 |
|------|------|
| 被测对象的设计 | [规则机制](rule-mechanism.md) / [扫描机制](scan-mechanism.md) / [AI 审核](ai-review.md) |
| 双盲方法论完整版 | [architecture.md](../architecture.md) |
| 质量阶梯与推进批次 | [blueprint.md](../blueprint.md) |
| 规则全景与等级 | [capability-map.md](../capability-map.md) |
| 新规则接入流程 | [rule-intake-sop.md](../rule-intake-sop.md) |
