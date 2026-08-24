# 双盲测试报告：真实 GitHub Top 仓库扫描

**测试日期**: 2026-08-24（P0 降噪后）
**测试工具**: AI 代码审查工具集（三引擎融合 + 分层评审，main）
**测试目标**: 验证工具在真实大型项目中的检出能力与降噪效果
**测试流程**: 完整 SKILL 链路（RuleEngine 多引擎 -> Prefilter -> 分层 AI 复核 -> ReportGenerator）

---

## 1. 测试仓库

| 仓库 | Stars | 语言 | 扫描文件数 | 规则引擎检出 | AI 复核后 |
|------|-------|------|-----------|-------------|----------|
| [freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | 375K+ | JavaScript | 50 | 90 | 75 |
| [Django](https://github.com/django/django) | 78K+ | Python | 50 | 124 | 106 |
| [Spring Boot](https://github.com/spring-boot/spring-boot) | 78K+ | Java | 50 | 1154 | 1088 |
| **合计** | - | - | **150** | **1368** | **1269** |

**AI 复核过滤率: 7.2%**（注：双盲流程使用 mock LLM，该过滤率反映链路健康度，非真实 LLM 准确率）

---

## 2. P0 降噪效果（对比 2026-08-24 基线）

| 指标 | 降噪前 | 降噪后 | 变化 |
|------|--------|--------|------|
| Spring Boot 原始检出 | 2597 | 1154 | **-55.5%** |
| 三仓库总检出 | 2811 | 1368 | **-51.4%** |
| null-java-unwrap-boxed | 761 | 19 | **-97.5%**（仅剩真实 Map.get 拆箱） |
| crypto-hardcoded-key-java | 706 | 3 | **-99.6%**（仅剩敏感命名+长字面量） |
| AI 复核过滤率 | 19.9% | 7.2% | 输入更干净 |

降噪手段：
1. **规则收紧**：`hardcoded-key` 改为 pattern-regex（敏感变量名 + 长度>=8 + 排除 `${}` 占位符）；`unwrap-boxed` 限定 `int x = y.get(...)` 形态
2. **分层评审**：CRITICAL/HIGH/ERROR 进 LLM 精审，WARNING/INFO 统计层保留（Spring Boot: LLM 精审 345 条，统计层 809 条，LLM 负载降 70%）
3. **V1 正则引擎空格缺陷修复**：`re.escape` 转义空格导致含空格 pattern 全部静默失配

---

## 3. 问题分布（Spring Boot Top 5，降噪后）

| 规则 | 检出 |
|------|------|
| naming-java-boolean-prefix | 373 |
| null-java-method-chain | 163 |
| err-java-empty-catch | 146 |
| path-write-traversal | 88 |
| path-read-traversal | 85 |

严重级别：CRITICAL 137 / ERROR 168 / WARNING 398

---

## 4. 已知边界与待办

1. **真实 LLM 准确率未测**：双盲用 mock LLM；需接入真实 LLM + 小样本人工标注（Golden set）
2. **反馈闭环空转**：`data/feedbacks.json` 无历史反馈，任务文件中"历史准确率"显示"暂无数据"
3. **AST 规则覆盖窄**：builtin-v2 的 AST 规则仅 Java，多引擎互证暂未触发（规则 ID 命名空间不重叠）
4. **白名单缺口**：Spring Boot 使用 `src/intTest/` 命名（非 `integrationTest`），未被 17 类模式覆盖
5. **误杀监控**：AI 复核对 ERROR 级过滤 29 个（Spring Boot），需人工抽查
6. **下一个降噪候选**：`naming-java-boolean-prefix`（373）现为最大噪音源

---

## 5. 结论

全链路在三个真实 Top 仓库稳定运行。P0 降噪使检出总量减半且更精准：
两条高噪音规则合计 1467 -> 22 个检出（-98.5%），
分层评审将 LLM 精审负载降低约 70%，报告可读性显著提升。
