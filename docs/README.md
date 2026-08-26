# 文档索引

> Code Review Skill 项目文档导航

---

## 核心设计文档

| 文档 | 说明 | 适合谁 |
|------|------|--------|
| [architecture.md](architecture.md) | 架构设计、技术选型、实现原理、双盲验证方法论 | 想深入了解系统设计的开发者 |
| [blueprint.md](blueprint.md) | 能力蓝图、三阶段推进方案、质量度量 | 项目维护者、贡献者 |
| [capability-map.md](capability-map.md) | 能力地图（自动生成，107 规则全景） | 想了解规则覆盖范围的用户 |

---

## 核心机制详解

四大机制的设计原理与理论逻辑基础（`mechanisms/` 目录），每份文档对照实际实现，含机制图：

| 文档 | 主题 | 理论基础 |
|------|------|----------|
| [mechanisms/rule-mechanism.md](mechanisms/rule-mechanism.md) | 规则机制：Markdown DSL、双模检测（pattern/taint）、入口点锚定、自然语言预编译 | 模式匹配 vs 数据流分析、CEGIS 反例驱动合成 |
| [mechanisms/scan-mechanism.md](mechanisms/scan-mechanism.md) | 扫描机制：五步流水线、三引擎融合、降噪漏斗 | 贝叶斯后验校准、Shannon 熵 + Miller-Madow、BH-FDR |
| [mechanisms/ai-review.md](mechanisms/ai-review.md) | AI 审核：分层评审、投票、fail-open、审计轨迹、子 Agent 委派 | Self-Consistency（Wang et al. 2022）、低温采样 |
| [mechanisms/testing.md](mechanisms/testing.md) | 测试体系：605 测试分层、质量阶梯 L0-L3、双盲验证 | 质量阶梯、双盲实验设计、golden test oracle |

---

## 验证报告

### 靶场盲测

| 文档 | 靶场 | 结果 |
|------|------|------|
| [blind-test-java-sec-code.md](blind-test-java-sec-code.md) | java-sec-code | 37 检出，100% 精确率 |
| [blind-test-webgoat.md](blind-test-webgoat.md) | OWASP WebGoat | 49 检出，97.96% 精确率 |

### 真实仓库验证

| 文档 | 仓库 | 说明 |
|------|------|------|
| [validation.md](validation.md) | freeCodeCamp / Django / Spring Boot | 3 语言 Top 仓库全链路验证 |

### 验证场景设计

| 文档 | 场景 | 说明 |
|------|------|------|
| [mechanisms/e2e-validation-scenario.md](mechanisms/e2e-validation-scenario.md) | E2E-001 端到端代码评审验证 | 五阶段验证流程（环境准备 → 扫描 → AI 评审 → 报告 → 成本度量），覆盖子智能体触发、精确率、JSON schema 合规 |
| [mechanisms/rule-intake-validation-scenario.md](mechanisms/rule-intake-validation-scenario.md) | E2E-002 规则新增验证 | 八步 SOP 全链路验证（案例归集 → PoC 矩阵 → 规约落地 → 靶场实测 → 能力地图），以 CWE-601 开放重定向为具体案例 |

---

## 扩展指南

| 文档 | 说明 |
|------|------|
| [rule-intake-sop.md](rule-intake-sop.md) | 规则接入 8 步 SOP（CWE/CVE → L3 规则） |
| [extension-points.md](extension-points.md) | 7 个扩展锚点详解 |
| [capability-map-data.yaml](capability-map-data.yaml) | 能力地图薄数据层（人工维护） |

---

## 使用指南

| 文档 | 说明 |
|------|------|
| [getting-started.md](getting-started.md) | 入门指南 |
| [advanced.md](advanced.md) | 高级用法 |
| [guides/OFFLINE-INSTALL.md](guides/OFFLINE-INSTALL.md) | 离线安装说明 |
| [guides/SEMGREP-OFFLINE-INSTALL.md](guides/SEMGREP-OFFLINE-INSTALL.md) | Semgrep 离线安装 |

---

## 技术参考

| 文档 | 说明 |
|------|------|
| [TECH-STACK.md](TECH-STACK.md) | 技术栈详细分析 |
| [DIRECTORY-STRUCTURE.md](DIRECTORY-STRUCTURE.md) | 目录结构说明 |
| [RULE_COMPILER_GUIDE.md](RULE_COMPILER_GUIDE.md) | 规约预编译指南 |
| [rules.md](rules.md) | 规则编写指南 |

---

## 项目报告

### 迭代报告

| 文档 | 说明 |
|------|------|
| [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) | 实施规划 |
| [COMPLETION-REPORT.md](COMPLETION-REPORT.md) | 完成报告 |
| [ITERATION-REPORT.md](ITERATION-REPORT.md) | 迭代改进报告 |
| [CLEANUP-REPORT.md](CLEANUP-REPORT.md) | 清理报告 |

### 验证矩阵

| 文档 | 说明 |
|------|------|
| [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) | 验证矩阵 |
| [SUBAGENT-REVIEW-ARCHITECTURE.md](SUBAGENT-REVIEW-ARCHITECTURE.md) | 子 Agent 评审架构（含多评审员投票机制） |

---

## 历史归档

以下目录包含历史过程文件，仅供内部参考：

- `reports/` — 扫描报告、验证报告、安全修复报告
- `agent-*-review.md` — 历史 Agent 评审记录
- `stirling-pdf-*.md` — Stirling PDF 项目盲测系列
- `sample-blind-test-*.md` — 样本盲测系列

---

## 文档维护说明

### 更新频率

| 文档类型 | 更新时机 | 维护者 |
|---------|---------|--------|
| README.md | 重大功能变更 | 项目维护者 |
| architecture.md | 架构调整 | 架构师 |
| blueprint.md | 阶段完成 | 项目维护者 |
| capability-map.md | 自动生成 | 脚本（`scripts/gen_capability_map.py`） |
| blind-test-*.md | 新靶场测试 | 测试负责人 |

### 文档层级

```
README.md (门面)
    ↓
docs/README.md (文档索引)
    ↓
docs/architecture.md (深度设计) ── docs/blueprint.md (推进方案)
    ↓                                   ↓
docs/mechanisms/ (核心机制详解: 规则/扫描/AI审核/测试)
    ↓
docs/capability-map.md (能力全景)
    ↓
docs/reports/ (过程记录)
```

### 自动生成的文档

- `capability-map.md` — 运行 `python3 scripts/gen_capability_map.py` 生成
- 数据来源：`capability-map-data.yaml` + 规则库

---

## 贡献文档

欢迎改进文档！提交 PR 时请遵循：

1. **README.md** — 保持简洁，突出特色，控制在 350 行内
2. **architecture.md** — 深度技术参考，可详细展开
3. **新增指南** — 放在 `docs/guides/` 目录
4. **验证报告** — 放在 `docs/` 根目录，命名 `blind-test-{target}.md`
5. **过程记录** — 放在 `docs/reports/` 目录
