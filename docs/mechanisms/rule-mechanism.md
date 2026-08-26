# 规则机制详解

> [首页](../../README.md) / [文档索引](../README.md) / [核心机制](../README.md#核心机制详解) / **规则机制**
>
> 对应实现：`scripts/rule_engine.py`（DSL 解析与编译）、`scripts/rule_compiler.py`（自然语言预编译）、`scripts/rule_sandbox.py`（外部规则沙箱）

---

## 1. 设计定位：规则是"人写的规约，机器执行的代码"

规则机制要解决的根本矛盾是：**安全知识以自然语言存在于人的头脑和文档中，而执行引擎需要精确的形式化规则**。

两条常见的失败路线：

| 路线 | 问题 |
|------|------|
| 直接让所有人写 Semgrep YAML | 对人员技术要求过高，pattern 语法、元变量、taint 结构都是专业门槛 |
| 完全交给 LLM 临时判断 | 不可复现、不可审计、每次结果漂移，无法作为工程基线 |

本项目的选择是**中间态**：

```
人 ──写──> Markdown 规约（DSL / 自然语言） ──预编译──> Semgrep 规则 ──执行──> 确定性检出
                ↑                                    ↑
          可读、可评审、可版本化            机器执行、可回归测试
```

规则一经编译即**确定性执行**：同一份规则库 + 同一份代码，检出结果永远一致。这是后续所有验证方法（golden test、靶场盲测）成立的前提。

## 2. 规则的三种形态与加载决策

`RuleEngine._load_rules()` 按 Profile 加载规约，三种形态统一汇入内部规则树：

```
references/ 规约库
│
├─ security/*.md ──────── 结构化 DSL 规约（含 ```yaml / ```pattern 块）
│                          │ 解析出规则 → 直接编译执行
│                          │
│                          └─ 解析不出任何规则（纯自然语言）？
│                               └─ 回退加载 compiled/<stem>.approved.yaml
│                                  （LLM 预编译 + 人工审批的产物）
│
├─ security/*.yaml ────── 静态孪生产物（供外部直接 semgrep -f 使用）
│
└─ external/*.yaml ────── 外部规则（GitHub 高星仓库导入）
                           └─ 必须先过沙箱校验（结构 + 冒烟）
```

关键设计：

- **自然语言规约不会静默失效**——解析不出 DSL 规则时自动回退到已批准的编译产物，打通"自然语言 → LLM 预编译 → 人工审批 → 引擎消费"的完整链路。
- **外部规则必须过沙箱**（`rule_sandbox.py`）：结构校验（必须有 id / languages / 检测字段，severity 必须在标准集合内）+ 真实 semgrep 冒烟试跑。坏规则进引擎会导致整份配置 rc=2、检出静默清零。
- **空 Profile 是用户的明确意愿**：specs 为空时不隐式拉入 external/ 规则。

## 3. Markdown DSL 详解

每个规则是 Markdown 中的一个 section（以 `#` 标题或 `---` 分隔），由元数据块 + 检测块组成。

### 3.1 元数据块

```yaml
id: cmdi-taint          # 规则唯一标识（前缀决定类别：sqli/xxe/cmdi → security）
languages: [java]       # 多语言规则会按语言拆分编译
severity: CRITICAL      # CRITICAL/HIGH/ERROR/WARNING/INFO
cwe: CWE-78             # CWE 归属（能力地图的主键）
owasp: A03:2021         # OWASP Top 10 映射
```

### 3.2 pattern 块家族（语法层检测）

| DSL 块 | 编译为 | 语义 |
|--------|--------|------|
| ```` ```pattern ```` | `pattern` / `pattern-either` | 必须命中的 AST 模式 |
| ```` ```pattern-not ```` | `pattern-not` | 同范围否定（豁免） |
| ```` ```pattern-not-inside ```` | `pattern-not-inside` | 命中点位于排除块内则豁免 |
| ```` ```pattern-regex ```` | `pattern-regex` | 正则模式（最后手段） |
| ```` ```pattern-metavariable-regex ```` | `metavariable-regex` | 元变量词法约束（每行 `$VAR: regex`） |

元变量（`$VAR`）匹配任意标识符，`...` 匹配任意代码（含跨行）。多语言规则可用 `### Java` / `### Python` 子标题给 pattern 打语言标签，编译时只选取目标语言的条目。

### 3.3 taint 块家族（数据流检测）

| DSL 块 | 编译为 | 语义 |
|--------|--------|------|
| ```` ```pattern-sources ```` | `pattern-sources` | 污点源（用户可控输入），每行一个 |
| ```` ```pattern-sinks ```` | `pattern-sinks` | 污点汇（危险操作），每行一个 |
| ```` ```pattern-sanitizers ```` | `pattern-sanitizers` | 净化器（脱污点），每行一个 |
| ```` ```pattern-sinks-not ```` | 复合进每个 sink 的 `pattern-not` | sink 同范围否定 |
| ```` ```pattern-sinks-not-inside ```` | 复合进每个 sink 的 `pattern-not-inside` | sink 位于排除块内则豁免 |

### 3.4 完整示例：命令注入规则（cmdi-taint）

````markdown
# 命令注入（用户可控数据流入命令执行 API）

> 用户可控数据未经净化直接拼入命令执行，导致任意命令执行

```yaml
id: cmdi-taint
languages: [java]
severity: CRITICAL
cwe: CWE-78
owasp: A03:2021
```

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
spring-entrypoint-param
```

```pattern-sinks
(Runtime $R).exec(...)
Runtime.getRuntime().exec(...)
new ProcessBuilder(...)
```

```pattern-sanitizers
$X.cmdFilter(...)
```
````

三个值得注意的语义点：

1. **`spring-entrypoint-param` 是入口点锚定标记**（见 4.2）——不是字面 pattern，编译时展开为复合 source。
2. **sink 的三种形态缺一不可**：`(Runtime $R).exec(...)` 覆盖类型化声明，`Runtime.getRuntime().exec(...)` 覆盖链式调用，`new ProcessBuilder(...)` 覆盖构造器形态。类型化元变量不做子类型匹配，`PreparedStatement` 不会命中 `Statement` 类型的 sink，必须显式枚举。
3. **sanitizer 必须带 receiver 元变量** `$X.cmdFilter(...)`——无 receiver 的写法匹配不到静态工具类调用 `SecurityUtil.cmdFilter(...)`。

## 4. 编译管线：Markdown → Semgrep

### 4.1 流程总览

```
Markdown 规约 (.md)
        │ MarkdownRuleParser（section 拆分 → yaml/pattern/taint 块解析）
        ▼
内部规则树 [{id, patterns[], taint{sources,sinks,sanitizers}, metadata}]
        │ _rules_to_semgrep()
        │   ├─ 无正向 pattern 的规则跳过（仅有 pattern-not 不构成检测）
        │   ├─ 单语言 → 直接编译
        │   └─ 多语言 → 拆分为 id__{lang} 多条规则
        ▼
Semgrep 规则集 {rules: [...]}
        │ pattern 规则 → _build_semgrep_rule（pattern/patterns/pattern-either 组装）
        │ taint 规则   → _build_taint_rule（mode: taint + 三元组组装）
        ▼
临时规则文件 → semgrep --config 执行 → 检出结果
```

多语言拆分的原因：不同语言的 pattern 混在同一规则的 `pattern-either` 中会互相导致解析失败。拆分后以 `{id}__{lang}` 命名，检出时引擎再还原回原始 rule_id，对报告层透明。

### 4.2 入口点锚定（entry-point anchoring）

`spring-entrypoint-param` 标记展开为六种 Spring 方法级 mapping 注解（`@GetMapping` / `@PostMapping` / `@RequestMapping` / `@PutMapping` / `@DeleteMapping` / `@PatchMapping`）之一的复合 source：

```yaml
patterns:
  - pattern-inside: |
      @GetMapping(...)
      $RET $METHOD(..., $TYPE $PARAM, ...) {
        ...
      }
  - focus-metavariable: $PARAM
```

理论依据：Spring 入口点方法的全部参数经隐式参数绑定语义成为用户可控（无论是否显式标注 `@RequestParam`）。

为什么用**方法级**注解锚定而不是参数级 `@RequestParam`：

- 参数级注解在 Semgrep Java 签名匹配中过滤不可靠（实测 `@Transactional` 方法参数同样命中）；
- 业界同构方案实证：不锚定入口点直接把所有方法参数视为污点源，在 24 个 Java OSS 仓库上产生 98.7% 的 critical 误报；
- 本项目自身也证伪过"所有方法参数追加为污点源"的激进方案——java-sec-code 实测找回 2 个委托 sink，但安全控件（SSRFChecker）误报复活，静态调用图无法区分 vuln/sec 共享 helper。

### 4.3 sink 聚焦（focus 后缀）

sink 条目可加 `focus: $X` 后缀，编译为 `pattern + focus-metavariable` 复合条目：

````markdown
```pattern-sinks
$RESP.getWriter().write($DATA) focus: $DATA
```
````

必要性（PoC 9/9 矩阵实证）：focus-metavariable 参数源的污点按"起点包含"语义命中 sink——即使污点值已流经净化器（如 `htmlEscape` 转义后 `write(escape(name))` 仍报）。sink 侧聚焦数据参数后恢复值级污点判定，净化器重新生效。

### 4.4 加固场景豁免（sink 排除块）

安全代码与漏洞代码常常命中**同一个 sink**，差异只在 sink 周边的加固形态。taint DSL 用排除块表达：

| 排除块 | 典型场景 |
|--------|----------|
| `pattern-sinks-not` | SpEL 用 `SimpleEvaluationContext`（安全上下文）时排除该 sink 的特定参数形态 |
| `pattern-sinks-not-inside` | QLExpress 先设置全局安全策略语句再 execute，整个 execute 豁免；XXE 的 `createXMLReader()` 后跟 `setFeature` 加固块豁免；SnakeYAML 的 `new Yaml(new SafeConstructor())` 豁免 |

实现上，排除模式被**复合进每个 sink 条目**（`_apply_sink_exclusions`），语义与 pattern 规则的同名块完全一致。

### 4.5 静态孪生产物

每个结构化规约 md 导出一份语义等价的 YAML（`references/security/<stem>.yaml`），由引擎的 `_rules_to_semgrep()` 同一代码路径导出，保证孪生一致。作用：

- 外部用户可以脱离本项目直接 `semgrep -f <twin>.yaml` 使用规则；
- `test_profile_completeness.py` 强制每个 md 规约有对应孪生 yaml，防止两者漂移。

## 5. 理论基础：双模检测的能力光谱

规则库同时维护 pattern（96 条）与 taint（11 条）两种形态，这不是历史包袱，而是检测能力的**光谱覆盖**：

```
表达能力:  弱 ◄──────────────────────────────────────► 强
           正则          AST 模式匹配           过程内数据流分析
           ───────────►  ────────────────────►  ─────────────────────►
           regex 引擎     pattern 规则            taint 规则(Semgrep)
           (离线回退)      (三引擎均可执行)         (仅 Semgrep 可执行)

检出语义:  文本形态       语法结构                污点传播路径
                          "存在这样的代码形态"      "用户输入流到了危险操作"
```

两类规则的本质差异：

| 维度 | pattern 规则 | taint 规则 |
|------|-------------|-----------|
| 判定问题 | 代码里**存在**某形态吗？ | 污点**从 source 流到** sink 了吗？ |
| 加固豁免 | pattern-not / pattern-not-inside | sanitizers + sink 排除块 |
| 误报来源 | 形态相似但语义无关的代码 | source/sink 语义建模错误 |
| 引擎依赖 | AST / Semgrep / 正则均可 | 仅 Semgrep（数据流分析） |
| 适用场景 | API 误用、缺失防护、硬编码 | 注入类漏洞（输入→危险汇） |

**实证数据**（盲测驱动，详见 [测试体系](testing.md)）：

- 纯静态模式匹配的高严重级精确率仅 2.4%–3.2%（形态匹配无数据流语义）；
- 11 条 taint 规则在 java-sec-code 方法级盲测中达到 **11 TP + 0 FP**，在 WebGoat 达到 **97.96%** 精确率；
- 典型检出：Shiro-550 反序列化漏洞——入口点 `HttpServletRequest` 参数锚定为污点源，经 **5 层调用链**命中 `ObjectInputStream.readObject()` sink。这是 pattern 规则原理上无法表达的。

**已知边界**（诚实声明，登记于架构文档）：Semgrep OSS 是严格过程内分析（同文件同类不跨方法）。污点源在被调方法、汇在被调方法、字段间接传播三类场景会漏报；跨方法分析需 Semgrep Pro。工程上的补偿策略是入口点对象（`HttpServletRequest` 参数）作为源经不透明调用保守传播，覆盖"传 request 给 helper 取返回值"形态；其余由 AI 复审层补位。

### 5.1 Semgrep 语义陷阱清单（踩坑沉淀）

这些是规则编写中最容易静默失效的点，已全部在测试中固化：

| 陷阱 | 现象 | 正确写法 |
|------|------|----------|
| 元变量含小写字母（`$CLASSImpl`） | 非法元变量，rc=2 静默失效 | `$CLASS` + `pattern-metavariable-regex: $CLASS: .*Impl` |
| metavariable-regex 写 `Impl$` | anchored 全匹配语义下永不命中 | 写 `.*Impl`（全匹配，非搜索） |
| 隐式导入类型用全限定名 | `(java.lang.Runtime $R)` 零命中 | 简单名 `(Runtime $R)`；需显式 import 的类型（`java.sql.Statement`）则全限定名有效 |
| 类型化元变量不匹配子类型 | `PreparedStatement` 声明不命中 `Statement` sink | 显式枚举全部接口类型 |
| sanitizer 无 receiver 元变量 | `$X.cmdFilter` 匹配，`cmdFilter(...)` 写法漏匹配静态工具类调用 | sanitizer pattern 必须含 receiver 元变量 |
| metadata 含浮点值 | semgrep YAML 解析器拒收，整份规则文件 rc=2 | 编译时递归转字符串（`_sanitize_semgrep_metadata`） |
| 参数级注解过滤 | `@RequestParam` 锚定不可靠，`@Transactional` 参数误命中 | 方法级 mapping 注解锚定 |

## 6. 自然语言规约预编译链路

纯自然语言规约（无 DSL 块）走 `RuleCompiler` 预编译，这是"一句话接入新漏洞"能力的基础：

```
自然语言规约 (.md)
   │ 提取：元数据 / 违规场景 / 安全做法 / 违规代码示例 / 安全代码示例
   │       （"检测方式: 数据流" 声明 → taint 编译，否则 search 编译）
   ▼
LLM 生成规则草稿（temperature=0，确定性采样；metadata.generation_method="ai"）
   │ LLM 不可用 → search 类型降级启发式推断（确定性，标记 heuristic_fallback）
   │             taint 类型不降级 → rules=[] → validation=failed（数据流语义无法机械推断，
   │             宁可不部署也不伪装成可用规则）
   ▼
Golden Test 验证 ──────── 违规示例必须命中（漏检=失败）
   │                      安全示例必须不命中（误报=失败）
   │                      计算 pass_rate
   │
   ├─ 通过 → 人工审批 → compiled/<stem>.approved.yaml → 引擎消费
   │
   └─ 失败 → 失败反馈累积进 failure_history ──┐
                                              │（反例驱动）
              带全部历史失败重新生成 ◄─────────┘
              （MAX_REPAIR_ROUNDS=3 轮预算；LLM 不可用时首轮失败即短路，
                确定性生成重试只是空转）
```

四个理论支点：

1. **Golden Test 作为 oracle**：规则作者提供违规/安全代码对，编译产物必须区分两者。这把"规则对不对"从主观判断变成可执行断言。
2. **CEGIS（反例驱动合成）**：每轮 golden test 失败的原因（漏检/误报）作为反例注入下一轮生成 prompt，LLM 看到全部历史失败避免重复犯错。这是程序合成领域 CounterExample-Guided Inductive Synthesis 思想在规则生成上的应用。
3. **人工审批闸门**：编译产物必须人工确认才生成 `.approved.yaml`，AI 不得自动覆盖线上规则——LLM 生成的规则天然存在幻觉风险，审批是最后防线。
4. **部署阈值**：`pass_rate ≥ 90%` 才可部署，低于阈值拒绝。taint 类型 LLM 不可用时直接失败进闸门，保证"可部署"的语义含金量。

配套的版本治理：`.history/` 保存每轮编译产物，`.approval_log.json` 记录审批记录，`manifest.json` 按文件 SHA256 缓存避免重复编译。

## 7. 规则质量治理

- **沙箱验证**（外部规则）：结构校验拦截无 pattern / 非法 severity 的坏规则；冒烟测试在样本语料上真跑 semgrep 拦截运行时异常。
- **质量阶梯**：L0（未覆盖）→ L1（可解析）→ L2（e2e 测试）→ L3（靶场盲测零误报），等级由能力地图实时推导，详见 [测试体系](testing.md)。
- **规则接入 SOP**：CVE/CWE 到 L3 规则的八步流水线，见 [rule-intake-sop.md](../rule-intake-sop.md)。
- **扩展锚点**：规约层 / DSL 块 / 入口点 / 净化器 / 孪生产物 / 验证 / 质量七个扩展面，见 [extension-points.md](../extension-points.md)。

## 8. 相关文档

| 主题 | 文档 |
|------|------|
| 规则编写实操 | [rules.md](../rules.md) |
| 扫描时规则如何被执行 | [扫描机制](scan-mechanism.md) |
| 编译产物如何被验证 | [测试体系](testing.md) |
| 规则全景与质量等级 | [capability-map.md](../capability-map.md) |
