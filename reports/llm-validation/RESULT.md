# 真实 LLM 评审验证报告（双盲精确率实测）

- 日期：2026-08-25
- 方法：spring-boot 全库扫描 → CRITICAL/HIGH/ERROR 层（587 条）→ 确定性分层抽样 42 条（18 条规则，MD5 哈希排序可复现）→ 3 个独立子 agent 盲评（每个 14 条，只看代码上下文，不知规则实现）→ 汇总 TP/FP
- 判定文件：task-1/2/3.md，verdicts-1/2/3.json

> **复测补充（同日，P0 修复后）**：见文末"复测结果"一节。
> 首轮抽样的 9 条"测试目录 FP"中多数在生产链路会被 prefilter 滤除
> （首轮抽样未经 prefilter，低估了生产精确率）；但规则 pattern 缺陷部分
> （SSRF 构造误判、size()==1 误判、Maven ${} 误判）位于 src/main 生产代码，
> 与 prefilter 无关，依然真实。

## 结论

| 指标 | 数值 |
|---|---|
| 样本 | 42 条（覆盖 18 条高严重级规则） |
| TP（真阳性） | 1 |
| FP（误报） | 41 |
| **精确率** | **2.4%** |
| 三批一致性 | 批1: 0/14，批2: 0/14，批3: 1/14 |

唯一 TP：`err-java-throw-in-finally`——finally 的 catch 中 `throw ex.getCause()`，双失败时原始异常被静默替换且无 addSuppressed。

## 误报分类（41 条 FP）

| 类别 | 约计 | 典型案例 |
|---|---|---|
| 测试目录白名单缺口 | 9 | `src/intTest`、`src/dockerTest`、`src/testFixtures`、test-support、smoke-test 不在 17 类白名单模式内 |
| URL/URI 构造误判 SSRF | 8 | `new URL(...)` 仅构造对象注册 Tomcat 资源、`URI.create()` 纯解析，均不发请求 |
| `size()==1` 误判签名绕过 | 6 | bean 条件评估、唯一 executor 选取被当成"版本判断跳过验签" |
| Maven `${...}` 误判 MyBatis 注入 | 4 | `@Parameter(defaultValue = "${project.build.finalName}")` 构建属性插值，非 SQL |
| XXE 工厂创建 + 下游加固 | 2 | `newInstance()` 后 1-3 行内设 `disallow-doctype-decl`/`FEATURE_SECURE_PROCESSING`（javadoc 引用 OWASP） |
| 常量拼接误判路径穿越/SQL | 5 | DERBY 验活 SQL 字面量、硬编码测试 jar 路径 |
| vendored 第三方库 | 2 | jQuery 1.7.2 内部 DOM 克隆 shim 命中 XSS 规则 |
| 其他语义错配 | 5 | JSON 字符串构造器命中路径穿越（方法名 `open`）、classpath 资源读取、受信运维配置等 |

## 引擎层发现（验证过程中的副产物）

1. **semgrep 无视 changed_files**：`_run_with_semgrep` 以 `cwd=repo, target=.` 扫全仓库。实测 50 文件输入时 1096/1097 条来自范围外。diff 扫描场景会把未变更文件的问题写进报告。
2. **AST 引擎规模失效**：仅 10 条手写规则（6 AST + 4 正则补充），149 条规约中 94% 的检出实际由 semgrep 单引擎执行；全库 AST 检出仅 83 条。
3. **多引擎互证为 0**：AST 与 semgrep 在 1212 条检出上零重合，贝叶斯互证（confidence=1.0）机制在真实数据上从未触发。
4. 熵门控正常：47 条硬编码检出评估，45 条被拒（其中 35 条经源文件回读提取字面量）。
5. z-score 离群监控正常：标记 null-java-method-chain、err-java-empty-catch。

## 修复优先级建议

- P0-1 prefilter 白名单补测试目录模式（intTest/dockerTest/testFixtures/e2eSupport）
- P0-2 `sqli-java-mybatis-dollar` 限定 XML mapper 文件 / `@Select` 上下文
- P0-3 SSRF 规则要求 `openConnection`/`connect` 等真实请求调用，排除纯 URL 构造
- P0-4 `sig-bypass-version-skip` pattern 修正（当前命中 `size()==1` 类比较属灾难性错配）
- P1-1 XXE 规则加 `pattern-not`（下游 disallow-doctype-decl/secure-processing）
- P1-2 semgrep 引擎按 changed_files 收窄扫描范围（生产正确性）
- P2 AST 引擎规则扩充（当前 10 条 → 覆盖高频 FP 规则，恢复互证机制）

---

# 复测结果（P0 修复后，同日）

## 修复内容（全部完成）

| 项 | 修复 | 验证 |
|---|---|---|
| P0-1 白名单 | 17→20 类模式（smoke-test/test-support/testFixtures） | 3 个新单测通过 |
| P0-2 MyBatis | 停用裸 `\$\{...\}`；新增注解版 + XML mapper 版（SQL 关键词上下文） | 4 个 Maven FP 全排除，真阳性正则验证命中 |
| P0-3 SSRF | `new URL($X)`→要求 openConnection；`URI.create`→要求序列至 send | spring-boot 归零（原 2+2 全 FP） |
| P0-4 签名绕过 | `if ($VAR==1)` → 版本语义变量+分支内 return 双证据正则 | size()==1 类 6 个 FP 全排除，漏洞模式保留 |
| P1-1 XXE | pattern-not 豁免 disallow-doctype-decl/secure-processing 加固 | 归零（原 2 全 FP） |
| P1-2 semgrep 范围 | --include 注入（≤4000 文件）+ 超限结果路径过滤兜底 | 50 文件输入范围外泄漏 0；3 个回归单测 |

全量测试：539 passed / 6 skipped。全库扫描 1129 → 1002，prefilter 后 589；
高严重级 587 → 190（-67.6%）；首轮唯一 TP（err-java-throw-in-finally）完整保留。

## 复测盲评（31 条分层样本，生产链路含 prefilter）

- 批次 v2-1：0 TP / 16 FP；批次 v2-2：1 TP / 14 FP
- **合计：1 TP / 30 FP，精确率 3.2%**（首轮 2.4%，绝对量 41 FP→30 FP）
- 修复的 6 条规则全部归零且无漏报 ✓

## 剩余 FP 的根因（模式匹配的天花板）

| 类别 | 条数 | 根因 |
|---|---|---|
| path-traversal 家族 | 20 | `new File($BASE, $SEG)` 无法区分 $SEG 是常量还是外部输入——需要污点分析 |
| 反序列化 | 3 | 数据源是 classpath 资源/鉴权后请求，非任意用户输入 |
| sig-java-verify-skip | 2 | verify() 返回值实际被 return 消费，跨方法数据流 |
| SSRF url-connection | 2 | URL 来自运维配置/war: 协议本地寻址 |
| 其他 | 3 | 常量 SQL、单线程 HashMap、日志常量路径 |

**结论**：剩余 30 条 FP 中约 27 条（90%）源于同一根本缺陷——**正则/AST
模式匹配没有数据流语义**，无法回答"$SEGMENT 从哪来"。模式层修复已到顶
（本轮 6 条规则修复全部有效且无漏报），下一阶段的正确路径是引入
**semgrep taint mode**（pattern-sources / pattern-sinks），让
path-traversal/ssrf/deser 家族只在"外部输入真实流到危险 sink"时报。
这需要扩展 md 规约格式与转换器，属中型改造。
