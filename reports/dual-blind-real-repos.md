# 双盲测试报告：真实 GitHub Top 仓库扫描

**测试日期**: 2026-08-24
**测试工具**: AI 代码审查工具集（三引擎融合版，main @ 8826a5e）
**测试目标**: 验证工具在真实大型项目中的检出能力与过滤效果
**测试流程**: 完整 SKILL 链路（RuleEngine 多引擎 -> Prefilter -> AIReviewer -> ReportGenerator）

---

## 1. 测试仓库

| 仓库 | Stars | 语言 | 扫描文件数 | 规则引擎检出 | AI 复核后 |
|------|-------|------|-----------|-------------|----------|
| [freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | 375K+ | JavaScript | 50 | 90 | 72 |
| [Django](https://github.com/django/django) | 78K+ | Python | 50 | 124 | 101 |
| [Spring Boot](https://github.com/spring-boot/spring-boot) | 78K+ | Java | 50 | 2597 | 2080 |
| **合计** | - | - | **150** | **2811** | **2253** |

**AI 复核过滤率: 19.9%**（注：双盲流程使用 mock LLM，该过滤率反映链路健康度，非真实 LLM 准确率）

---

## 2. 三引擎实测贡献

| 引擎 | 检出量 | 说明 |
|------|--------|------|
| Semgrep | 2252 | 主力引擎（本机已安装，全部仓库生效） |
| Tree-sitter AST | 1 | freeCodeCamp 贡献 1 个独立检出（builtin-v2 规则集） |
| 内置正则 | 0（未启用） | Semgrep 可用时作为回退不参与 |
| 多引擎互证 | 0 | AST 规则 ID 与 Markdown 规约 ID 命名空间不重叠，同位置互证暂未触发 |

---

## 3. 问题分布（Spring Boot Top 5）

| 规则 | 检出 |
|------|------|
| null-java-unwrap-boxed | 761 |
| crypto-hardcoded-key-java | 706 |
| naming-java-boolean-prefix | 373 |
| null-java-method-chain | 163 |
| err-java-empty-catch | 146 |

严重级别：CRITICAL 137 / ERROR 168 / WARNING 1140 / INFO 411

---

## 4. 已知边界与待办

1. **真实 LLM 准确率未测**：双盲用 mock LLM；需接入真实 LLM + 小样本人工标注
2. **反馈闭环空转**：`data/feedbacks.json` 无历史反馈，任务文件中"历史准确率"显示"暂无数据"
3. **AST 规则覆盖窄**：builtin-v2 的 AST 规则仅 Java，通用正则补充规则有限
4. **白名单缺口**：Spring Boot 使用 `src/intTest/` 命名（非 `integrationTest`），未被 17 类模式覆盖
5. **误杀监控**：AI 复核对 ERROR 级过滤 37 个（Spring Boot），需人工抽查是否误杀

---

## 5. 结论

全链路（多引擎扫描 -> 白名单过滤 -> AI 复核 -> 报告生成）在三个真实 Top 仓库上稳定运行，
三引擎编排按设计策略生效（AST 始终执行 / Semgrep 并行 / 正则回退）。
