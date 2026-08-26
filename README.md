# Code Review Skill

> 基于 Semgrep + Tree-sitter + AI Agent 的自动化代码评审工具。离线可用，支持分支差异扫描、调用链分析、多规约安全评审。

[![Tests](https://img.shields.io/badge/tests-620%20passed-brightgreen)](tests/)
[![Rules](https://img.shields.io/badge/rules-155%20security%20%2B%20design%20%2B%20impl-blue)](references/)
[![Coverage](https://img.shields.io/badge/CWE%20Top%2025-12%20categories%20L3-orange)](docs/capability-map.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 核心特色

| 特色 | 说明 |
|------|------|
| **Agent 主导评审** | Agent 自身就是 LLM，直接执行评审，无需外部 API，离线可用 |
| **双引擎融合** | Semgrep 数据流分析 + Tree-sitter AST 精确语法分析，互补检出 |
| **Markdown 规约** | 人机都好的半结构化 DSL，一条规则 = 一段 Markdown，无需学 Semgrep YAML |
| **双盲验证** | 靶场泛化（WebGoat/java-sec-code）+ 4 仓库真实盲测（765 文件），精确率 57.9% |
| **一键扩展** | 说「整理 CWE-xxx 转成规则」即可按 8 步 SOP 接入新漏洞类别 |
| **离线优先** | 所有核心功能离线可用，内置 20 个依赖包（~19MB），无网络环境秒部署 |

---

## 快速上手

### 1. 安装依赖

```bash
# 离线安装（推荐，无需网络）
pip3 install --no-index --find-links=offline-packages -r requirements.txt

# 或在线安装
pip3 install -r requirements.txt --break-system-packages

# 可选：安装 Semgrep 增强引擎
brew install semgrep  # macOS
```

### 2. 执行扫描

```bash
python3 scripts/scan.py \
  --repo /path/to/your/repo \
  --base master \
  --target release/1.0 \
  --profile default \
  --output report/
```

### 3. 查看报告

报告输出到 `report/` 目录：
- `report.json` — 结构化 JSON，便于程序处理
- `report.md` — 可读的 Markdown，按文件/规则分组

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      调度层                                  │
│  Cron 定时 / 手动触发 / CI/CD Webhook                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   差异分析层                                  │
│  Git Diff → 变更文件提取 → Tree-sitter 调用图 → 血缘追踪      │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   规约引擎层                                  │
│  Markdown DSL → Semgrep YAML → 双引擎并行扫描                 │
│  (内置正则 + Semgrep) → 去重合并                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                    AI 评审层                                  │
│  上下文感知 → 误报过滤（置信度） → 修复建议生成                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                     输出层                                    │
│  JSON 报告 / Markdown 报告 / Webhook 通知                     │
└─────────────────────────────────────────────────────────────┘
```

> 详细架构设计、技术选型、实现原理见 [docs/architecture.md](docs/architecture.md)

---

## 安全能力速览

覆盖 **OWASP Top 10 (2021)** + **CWE Top 25 (2025)**，155 条规则，12 个 L3 类别。

| 漏洞类别 | CWE | 规则数 | 质量等级 | 盲测验证 |
|---------|-----|--------|---------|---------|
| SQL 注入 | CWE-89 | 3 | **L3** | java-sec-code + WebGoat |
| 路径穿越 | CWE-22 | 8 | **L3** | java-sec-code + WebGoat + freeCodeCamp |
| SSRF | CWE-918 | 6 | **L3** | java-sec-code |
| XXE | CWE-611 | 9 | **L3** | java-sec-code |
| XSS | CWE-79 | 7 | **L3** | java-sec-code + WebGoat + freeCodeCamp |
| 反序列化 | CWE-502 | 5 | **L3** | java-sec-code + WebGoat |
| 命令注入 | CWE-78 | 5 | **L3** | java-sec-code + WebGoat |
| 表达式注入 | CWE-94/95/917 | 3 | **L3** | java-sec-code |
| 日志注入 | CWE-117 | 2 | **L3** | java-sec-code + WebGoat |
| 硬编码凭证 | CWE-798 | 4 | **L3** | WebGoat + freeCodeCamp |
| 弱随机数 | CWE-330 | 1 | **L3** | WebGoat |
| 开放重定向 | CWE-601 | 1 | **L3** | java-sec-code |
| Django/Flask 安全 | CWE-79/89/1336 | 8 | **L2** | 待盲测 |

> 完整能力地图见 [docs/capability-map.md](docs/capability-map.md)（自动生成）

---

## 验证数据

### 双盲测试结果

| 靶场 | 语言 | 规则数 | 检出 | TP | FP | 精确率 |
|------|------|--------|------|----|----|--------|
| java-sec-code | Java | 155 | 134 | 134 | 0 | 100% |
| WebGoat | Java | 155 | 22 | 22 | 0 | 100% |

### 真实仓库验证（第二轮，2026-08-26）

| 仓库 | Stars | 扫描文件 | 引擎检出 | 子 Agent 复核后 | 滤除率 |
|------|-------|---------|---------|----------|--------|
| freeCodeCamp | 375K+ | 165 | 6 | 0 | 100% |
| Django | 78K+ | 200 | 0 | 0 | N/A |
| Spring Boot | 70K+ | 200 | 10 | 1 | 90% |
| WebGoat | 12K+ | 200 | 22 | 6 | 72.7% |
| **总计** | | **765** | **38** | **7** | **81.6%** |

> 第二轮改进：禁用 path-traversal-pattern 字面量规则（消除 120 条 FP）、crypto-hardcoded-key 最小长度降噪、新增 8 条 Django/Flask 规则。总 FP 从 136 降至 16（-88%）。

> 第三轮（真实智能体链路）：scan.py 任务文件 → 主 Agent 委派子 Agent（qwen-3.7-plus）逐条读源码裁决 → 自动合并过滤。38 条检出 → 7 条高价值告警，保留的 7 条均有真实风险（命令注入、任意文件删写、JWT 签名失效仍有效等）；证据抽查 6/6 属实，零 API 依赖。

> 详细盲测报告见 [docs/blind-test-java-sec-code.md](docs/blind-test-java-sec-code.md)、[docs/blind-test-webgoat.md](docs/blind-test-webgoat.md)、[reports/dual-blind-analysis.md](reports/dual-blind-analysis.md) 和 [reports/real-agent-validation-2026-08-26.md](reports/real-agent-validation-2026-08-26.md)

---

## 规约体系

### 安全规约（14 类）

| 类别 | 规则文件 | 风险等级 |
|------|---------|---------|
| 越权访问 | `security/authorization.md` | CRITICAL |
| XXE | `security/xxe.md` | HIGH |
| XSS | `security/xss.md` | HIGH |
| 目录穿越 | `security/path-traversal.md` | HIGH |
| 提权/命令注入 | `security/privilege-escalation.md` | CRITICAL |
| 签名绕过 | `security/signature-bypass.md` | CRITICAL |
| SQL 注入 | `security/sql-injection.md` | CRITICAL |
| SSRF | `security/ssrf.md` | HIGH |
| 硬编码密钥 | `security/hardcoded-secrets.md` | HIGH |
| 反序列化 | `security/deserialization.md` | CRITICAL |
| 表达式注入 | `security/expression-injection.md` | CRITICAL |
| 日志注入 | `security/log-injection.md` | MEDIUM |
| 弱随机数 | `security/weak-randomness.md` | MEDIUM |
| 开放重定向 | `security/open-redirect.md` | HIGH |
| Django/Flask 安全 | `security/django-flask-security.md` | CRITICAL |

### 设计规约（3 类）

- **架构合规** — `design/architecture.md`：分层依赖、循环引用
- **API 设计** — `design/api-design.md`：RESTful 规范、命名规范
- **数据库设计** — `design/database.md`：N+1 查询、事务管理

### 实现规约（4 类）

- **命名规范** — `implementation/naming.md`
- **异常处理** — `implementation/error-handling.md`
- **并发安全** — `implementation/concurrency.md`
- **空指针防护** — `implementation/null-safety.md`

> 每条规约都有对应的测试案例（`references/test-cases/`），确保规则正确生效

---

## 扩展规则库

### 一句话接入新漏洞

```
整理 CWE-352 漏洞案例，转换成我们的 md 规则
```

Agent 会按 [8 步 SOP](docs/rule-intake-sop.md) 自动执行：
1. 案例归集 → 2. 三元组提炼 → 3. PoC 矩阵 → 4. 规约落地 → 5. 孪生注册 → 6. e2e 固化 → 7. 靶场实测 → 8. 地图更新

### 扩展锚点

7 个扩展锚点覆盖规则全生命周期：
- **规约层** / **DSL 块** / **入口点** / **净化器** / **孪生产物** / **验证** / **质量**

> 详见 [docs/extension-points.md](docs/extension-points.md)

---

## CI/CD 集成

### GitHub Actions

```yaml
name: Code Review
on:
  push:
    branches: [release/*]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/scan.py --repo . --base master --target HEAD --output report/
      - uses: actions/upload-artifact@v4
        with:
          name: review-report
          path: report/
```

### Cron 定时扫描

```yaml
# config.yaml
schedule:
  cron: "0 2 * * *"  # 每天凌晨 2 点
  notify: true
  notify_target: "https://hooks.example.com/scan-result"
```

---

## 文档导航

### 核心设计

| 文档 | 说明 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 架构设计、技术选型、实现原理、双盲验证方法论 |
| [docs/blueprint.md](docs/blueprint.md) | 能力蓝图、三阶段推进方案、质量度量 |
| [docs/capability-map.md](docs/capability-map.md) | 能力地图（自动生成，107 规则全景） |

### 核心机制详解

四大机制的设计原理与理论依据，每份文档含实现对照与机制图：

| 文档 | 说明 |
|------|------|
| [docs/mechanisms/rule-mechanism.md](docs/mechanisms/rule-mechanism.md) | 规则机制：Markdown DSL、taint 编译管线、入口点锚定、自然语言预编译（CEGIS） |
| [docs/mechanisms/scan-mechanism.md](docs/mechanisms/scan-mechanism.md) | 扫描机制：五步流水线、三引擎融合、降噪漏斗（熵门控/贝叶斯置信度） |
| [docs/mechanisms/ai-review.md](docs/mechanisms/ai-review.md) | AI 审核：分层评审、Self-Consistency 投票（API 路径 + 子 Agent 多数票）、fail-open、审计轨迹 |
| [docs/mechanisms/testing.md](docs/mechanisms/testing.md) | 测试体系：620 测试分层、质量阶梯 L0-L3、双盲验证方法论 |

### 验证报告

| 文档 | 说明 |
|------|------|
| [docs/blind-test-java-sec-code.md](docs/blind-test-java-sec-code.md) | java-sec-code 靶场盲测报告 |
| [docs/blind-test-webgoat.md](docs/blind-test-webgoat.md) | WebGoat 靶场盲测报告 |
| [reports/dual-blind-analysis.md](reports/dual-blind-analysis.md) | 第二轮双盲测试分析报告（4 仓库 765 文件） |
| [reports/improvement-summary-2026-08-26.md](reports/improvement-summary-2026-08-26.md) | 改进总结：FP 降噪 + Django/Flask 规则扩展 |

### 扩展指南

| 文档 | 说明 |
|------|------|
| [docs/rule-intake-sop.md](docs/rule-intake-sop.md) | 规则接入 8 步 SOP（CWE/CVE → L3 规则） |
| [docs/extension-points.md](docs/extension-points.md) | 7 个扩展锚点详解 |
| [docs/guides/OFFLINE-INSTALL.md](docs/guides/OFFLINE-INSTALL.md) | 离线安装说明 |

### 使用指南

| 文档 | 说明 |
|------|------|
| [.trae/skills/code-review/SKILL.md](.trae/skills/code-review/SKILL.md) | Skill 完整工作流 |
| [docs/getting-started.md](docs/getting-started.md) | 入门指南 |
| [docs/advanced.md](docs/advanced.md) | 高级用法 |

---

## 项目结构

```
code-review-skill/
├── .trae/skills/code-review/     # Agent Skill 定义
├── docs/                         # 文档（架构/蓝图/验证/指南）
├── references/                   # 规约库（Markdown DSL）
│   ├── design/                   # 设计规约
│   ├── implementation/           # 实现规约
│   ├── security/                 # 安全规约（12 类）
│   ├── profiles/                 # Profile 配置
│   └── test-cases/               # 测试案例
├── scripts/                      # Python 工程脚本
├── tests/                        # 单元测试（620 个）
├── reports/                      # 盲测报告与改进总结
├── offline-packages/             # 离线依赖包（~19MB）
├── config.yaml                   # 全局配置
└── README.md
```

---

## 常见问题

**Q: 为什么不需要 AI API Key？**  
A: Agent 本身就是 LLM，在 AI Agent 内部执行，无需调用外部 API，离线可用。

**Q: Agent 评审和 Semgrep 评审有什么区别？**  
A: Agent 评审利用 LLM 能力理解上下文、过滤误报；Semgrep 做精准模式匹配和数据流分析。建议默认用 Agent，安装 Semgrep 后双重评审。

**Q: 如何添加自定义规则？**  
A: 编辑 `references/rules/custom.md`，按 Markdown 格式添加，运行 `python scripts/test_rules.py` 验证。

**Q: 如何优化大仓库扫描性能？**  
A: 增量扫描（只扫变更文件，提升 10x-100x）、分批处理、跳过测试文件、并行分析。

---

## 技术栈

| 技术 | 用途 | 状态 |
|------|------|------|
| **Python 3.8+** | 运行环境 | 必须 |
| **Semgrep** | 跨行模式匹配、数据流分析 | 可选增强 |
| **Tree-sitter** | AST 解析、调用图构建 | 已集成 |
| **GitPython** | Git 差异分析 | 已集成 |
| **Rich** | 终端输出美化 | 已集成 |

> 详细技术对比见 [docs/architecture.md](docs/architecture.md#技术栈)

---

## License

MIT

---

## 贡献

欢迎提交 Issue 和 Pull Request。扩展规则库请遵循 [rule-intake-sop.md](docs/rule-intake-sop.md)。
