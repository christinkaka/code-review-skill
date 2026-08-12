# 代码评审工具 (Code Review Skill)

自动化代码评审工具，支持分支差异扫描、调用链分析、多规约（设计/实现/安全）自动评审，输出结构化问题报告与修复建议。

**核心特性**：
- **多引擎融合**：Semgrep + Tree-sitter AST + 内置正则三引擎融合扫描，去重合并结果
- **主 Agent 调度**：主 Agent 编排流程，委派子 Agent 进行代码评审
- **离线优先**：所有核心功能离线可用，无需外部 API
- **预过滤机制**：可配置预过滤规则，70-80% 的确定性问题自动判定
- **决策日志**：完整记录每次评审决策，支持反馈闭环

---

## 文档目录

### 🚀 入门

- [docs/getting-started.md](docs/getting-started.md) - 引导提示词、安装、扫描、报告、常见问题

### 🏗️ 架构与设计

- [docs/architecture.md](docs/architecture.md) - 工作流、技术栈、多引擎融合、工作空间机制、各层实现
- [docs/project-structure.md](docs/project-structure.md) - 项目目录结构与职责

### 📐 规则与检测

- [docs/rules.md](docs/rules.md) - 规约库（安全/设计/实现）、检测模式、Profile 配置

### 🤖 AI 评审

- [docs/ai-review.md](docs/ai-review.md) - Harness 系统、决策日志、反馈闭环、AI 交互字段约定
- [references/subagent-contract.md](references/subagent-contract.md) - 子 Agent 规约（职责/不能做/能做）
- [.trae/skills/code-review/SKILL.md](.trae/skills/code-review/SKILL.md) - Skill 入口（含主 Agent 调度流程、预过滤机制说明）

### 📊 验证与效果

- [docs/validation.md](docs/validation.md) - 验证效果、案例、违规/正确示例

### ⚙️ 高级用法

- [docs/advanced.md](docs/advanced.md) - 定期扫描、CI/CD 集成、评审流水线、扩展开发

### 📚 项目内已有文档

- [.trae/skills/code-review/SKILL.md](.trae/skills/code-review/SKILL.md) - Skill 入口（TRAE Agent 使用）
- [references/main-agent-contract.md](references/main-agent-contract.md) - 主 Agent 规约
- [references/subagent-contract.md](references/subagent-contract.md) - 子 Agent 规约
- [references/RULE-GENERATOR-GUIDE.md](references/RULE-GENERATOR-GUIDE.md) - 规则开发指南

### 🗄️ 历史文档（docs/）

- [docs/TECH-STACK.md](docs/TECH-STACK.md) - 技术选型详解
- [docs/SUBAGENT-REVIEW-ARCHITECTURE.md](docs/SUBAGENT-REVIEW-ARCHITECTURE.md) - Subagent 架构演进
- [docs/DIRECTORY-STRUCTURE.md](docs/DIRECTORY-STRUCTURE.md) - 目录结构设计
- [docs/VERIFICATION_MATRIX.md](docs/VERIFICATION_MATRIX.md) - 验收矩阵
- [docs/COMPLETION-REPORT.md](docs/COMPLETION-REPORT.md) - 完成报告
- [docs/IMPLEMENTATION-PLAN.md](docs/IMPLEMENTATION-PLAN.md) - 实施计划
- [docs/CLEANUP-REPORT.md](docs/CLEANUP-REPORT.md) - 清理报告
- [docs/ITERATION-REPORT.md](docs/ITERATION-REPORT.md) - 迭代报告
- [docs/SPECS-SUMMARY.md](docs/SPECS-SUMMARY.md) - 规约摘要
- [docs/WORKFLOW-UPDATE.md](docs/WORKFLOW-UPDATE.md) - 工作流更新
- [docs/guides/](docs/guides/) - 离线安装指南
- [docs/reports/](docs/reports/) - 历史报告归档

---

## 30 秒上手

```bash
# 1. 克隆并安装
git clone https://github.com/christinkaka/code-review-skill.git
cd code-review-skill
pip install -r requirements.txt
brew install semgrep  # macOS 可选

# 2. 扫描一个项目（注意：必须在 skill 仓库目录下执行）
python scripts/scan.py --repo ~/my-project --full-scan --workflow comprehensive

# 3. 查看报告（在被扫描项目的 .code-review/ 目录下）
cat ~/my-project/.code-review/workspace/<scan_id>/report/report.md
```

详细说明：[docs/getting-started.md](docs/getting-started.md)

---

## 验证效果

跨项目双盲测试（详见 [docs/validation.md](docs/validation.md)）：

| 项目 | 一致率 | 测试阶段 |
|------|--------|----------|
| Jenkins | 40% | 修复前 |
| Dubbo | 30% | 修复前 |
| Dubbo | 95% | **修复后（修复 Semgrep 脱敏）** |
| Spring Framework | 100% | **修复后** |

关键修复：
- `code_snippet='requires login'` 从 76.3% → 0%
- 预过滤：Dubbo 82.6%、Spring 71.6% 的问题被确定性过滤

---

## 目录结构（顶层）

```
code-review-skill/
├── scripts/           # 扫描引擎（Python）
├── references/        # 规约与规约 Profile
├── harness/           # Harness 系统（决策日志、反馈闭环）
├── config/            # 配置文件（harness.yaml）
├── docs/              # 项目文档
├── tests/             # 单元测试
├── test-validation/   # 集成测试用例
├── config.yaml                    # 主配置
├── requirements.txt               # Python 依赖
├── install-offline.sh             # 离线安装脚本
├── install-semgrep-offline.sh     # Semgrep 离线安装（Unix）
├── install-semgrep-offline.ps1    # Semgrep 离线安装（Windows）
├── download-offline-packages.sh   # 离线包下载脚本
├── offline-packages/              # 核心离线依赖包
├── semgrep-offline-packages/      # Semgrep 离线依赖包
└── .trae/skills/                  # TRAE Skill 入口
```

详细结构：[docs/project-structure.md](docs/project-structure.md)

---

## 许可证

MIT License
