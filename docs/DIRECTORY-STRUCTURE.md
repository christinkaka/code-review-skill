# 代码评审工程 - 目录结构说明

## 重要：目录关系

工具项目（code-review-skill）**不会**存放扫描输出。所有扫描结果都存储在**被扫描项目**下，避免污染工具项目本身。

### 输出位置关系

```
code-review-skill/                          # 工具项目（只读，不存放扫描输出）
├── scripts/scan.py                         # 主扫描入口
└── ...

<被扫描项目>/                               # 用户的目标项目
└── .code-review/                            # code-review 工具的输出目录（自动创建）
    └── workspace/
        └── {scan_id}/                       # 每次扫描的独立工作空间
            ├── report/                      # 扫描报告
            ├── cache/                       # 规则编译缓存
            ├── decisions/                   # 决策日志
            ├── feedbacks.json               # Harness 反馈数据
            └── stats_cache.json             # 质量监控缓存
```

---

## 目录结构


```
code-review-skill/
├── .trae/                          # TRAE 配置
│   └── skills/
│       └── code-review/
│           └── SKILL.md            # Agent Skill 定义
│
├── docs/                           # 文档目录
│   ├── guides/                     # 使用指南
│   │   ├── OFFLINE-INSTALL.md      # 离线安装指南
│   │   └── SEMGREP-OFFLINE-INSTALL.md  # Semgrep 离线安装指南
│   ├── reports/                    # 报告目录
│   │   ├── security-fixes/         # 安全规则修复报告
│   │   │   ├── metavar-fix-report.md
│   │   │   ├── rule-fix-report.md
│   │   │   ├── rule-fix-report-v2.md ~ v6.md
│   │   │   ├── rule-sync-report.md
│   │   │   ├── safety-guard-fix-report.md
│   │   │   └── security-enhancement-report.md
│   │   ├── validation/             # 验证报告
│   │   │   ├── validation-report.md
│   │   │   ├── validation-report-round9.md ~ round17.md
│   │   │   └── scan-report.md
│   │   └── scan_report_opencode.md # 扫描报告
│   ├── COMPLETION-REPORT.md        # 完成报告
│   ├── IMPLEMENTATION-PLAN.md      # 实施计划
│   ├── ITERATION-REPORT.md         # 迭代改进报告
│   ├── SPECS-SUMMARY.md            # 规约库总结
│   ├── TECH-STACK.md               # 技术栈说明
│   └── WORKFLOW-UPDATE.md          # 工作流更新说明
│
├── references/                     # 规约库
│   ├── design/                     # 设计规约
│   │   ├── api-design.md           # API 设计规范
│   │   ├── architecture.md         # 架构合规规范
│   │   └── database.md             # 数据库设计规范
│   ├── implementation/             # 实现规约
│   │   ├── concurrency.md          # 并发安全
│   │   ├── error-handling.md       # 异常处理
│   │   ├── naming.md               # 命名规范
│   │   └── null-safety.md          # 空指针防护
│   ├── profiles/                   # 规约配置
│   │   ├── default.yaml            # 默认配置
│   │   ├── minimal.yaml            # 最小配置
│   │   └── strict.yaml             # 严格配置
│   ├── prompts/                    # 提示词模板
│   │   └── ai-enhancer-prompt.md   # AI 增强评审提示词
│   ├── rules/                      # 自定义规则
│   │   └── custom.md               # 自定义规则模板
│   ├── security/                   # 安全规约
│   │   ├── authorization.md        # 越权访问
│   │   ├── deserialization.md      # 反序列化漏洞
│   │   ├── hardcoded-secrets.md    # 硬编码密钥
│   │   ├── log-injection.md        # 日志注入
│   │   ├── path-traversal.md       # 目录穿越
│   │   ├── privilege-escalation.md # 提权漏洞
│   │   ├── signature-bypass.md     # 签名绕过
│   │   ├── sql-injection.md        # SQL 注入
│   │   ├── ssrf.md                 # SSRF
│   │   ├── weak-randomness.md      # 弱随机数
│   │   ├── xss.md                  # XSS 漏洞
│   │   └── xxe.md                  # XXE 漏洞
│   └── test-cases/                 # 测试案例
│       ├── design/                 # 设计规约测试
│       ├── implementation/         # 实现规约测试
│       ├── security/               # 安全规约测试
│       └── README.md               # 测试案例说明
│
├── harness/                        # Harness 系统
│   ├── __init__.py
│   ├── decision_logger.py          # 决策日志记录器
│   ├── feedback_manager.py         # 反馈管理器
│   ├── quality_monitor.py          # 质量监控器
│   └── cli.py                      # Harness CLI 工具
│
├── config/                         # 配置目录
│   └── harness.yaml                # Harness 系统配置
│
├── scripts/                        # Python 脚本
│   ├── ai_reviewer.py              # AI 增强评审
│   ├── builtin_engine_v2.py        # 内置规则引擎 v2
│   ├── call_graph.py               # 调用图构建
│   ├── diff_analyzer.py            # 差异分析
│   ├── dual_engine.py              # 双引擎并行扫描
│   ├── harness.py                  # Harness 脚本
│   ├── notifier.py                 # 通知器
│   ├── report_generator.py         # 报告生成器
│   ├── rule_compiler.py            # 规则预编译器
│   ├── rule_engine.py              # 规则引擎
│   ├── scan.py                     # 主扫描入口
│   ├── scheduler.py                # 调度器
│   └── test_rules.py               # 规则测试
│
├── test-validation/                # 测试验证数据
│   ├── java/                       # Java 测试代码
│   │   ├── path-traversal/
│   │   ├── sqli/
│   │   ├── xss/
│   │   └── xxe/
│   ├── python/                     # Python 测试代码
│   │   ├── command-injection/
│   │   ├── path-traversal/
│   │   └── xxe/
│   ├── typescript/                 # TypeScript 测试代码
│   │   ├── ssrf/
│   │   └── xss/
│   ├── known-issues.json           # 已知问题清单
│   ├── README.md                   # 测试验证说明
│   └── scan-results-*.json         # 扫描结果
│
├── tests/                          # 单元测试
│   ├── conftest.py                 # pytest 配置
│   ├── test_ai_reviewer.py         # AI 评审测试
│   ├── test_markdown_parser.py     # Markdown 解析测试
│   ├── test_notifier.py            # 通知器测试
│   ├── test_rule_engine.py         # 规则引擎测试
│   ├── test_scheduler.py           # 调度器测试
│   └── test_semgrep_integration.py # Semgrep 集成测试
│
├── offline-packages/               # 离线依赖包（核心依赖）
├── semgrep-offline-packages/       # Semgrep 离线依赖包
├── config.yaml                     # 全局配置
├── requirements.txt                # Python 依赖
├── install-semgrep-offline.sh      # Semgrep 离线安装脚本
└── README.md                       # 项目说明
```

## 目录说明

### docs/ - 文档目录
存放所有项目文档，包括：
- **guides/**: 使用指南和安装说明
- **reports/**: 各类报告（修复报告、验证报告、扫描报告）
- 项目级文档（完成报告、实施计划、迭代报告等）

### references/ - 规约库
存放所有代码评审规约，按类别组织：
- **design/**: 设计规约（架构、API、数据库）
- **implementation/**: 实现规约（命名、异常、并发、空指针）
- **security/**: 安全规约（12 个安全场景）
- **profiles/**: 规约配置（default/strict/minimal）
- **prompts/**: AI 提示词模板
- **rules/**: 自定义规则模板
- **test-cases/**: 测试案例

### harness/ - Harness 系统
AI 评审质量管控系统：
- **decision_logger.py**: 记录每个问题的 AI 决策、理由、证据
- **feedback_manager.py**: 管理用户反馈，支持批量反馈
- **quality_monitor.py**: 计算质量指标，监控评审准确率
- **cli.py**: Harness 命令行工具

### config/ - 配置目录
- **harness.yaml**: Harness 系统的配置文件

### scripts/ - Python 脚本
存放所有 Python 脚本：
- **scan.py**: 主扫描入口
- **rule_engine.py**: 规则引擎（Semgrep）
- **builtin_engine_v2.py**: 内置规则引擎（AST + 正则）
- **rule_compiler.py**: 规则预编译器
- **diff_analyzer.py**: 差异分析
- **call_graph.py**: 调用图构建
- **dual_engine.py**: 双引擎并行扫描
- **ai_reviewer.py**: AI 评审任务生成
- **report_generator.py**: 报告生成器
- **scheduler.py**: 定时调度器
- **notifier.py**: 通知器
- 其他辅助脚本

### test-validation/ - 测试验证数据
存放测试代码和验证数据：
- **java/**, **python/**, **typescript/**: 各语言的测试代码
- **known-issues.json**: 已知问题清单
- **scan-results-*.json**: 扫描结果数据

### tests/ - 单元测试
存放 pytest 单元测试：
- 各模块的测试文件
- **conftest.py**: pytest 配置和 fixtures

### offline-packages/ - 离线依赖包
存放核心依赖的离线包：
- pyyaml, gitpython, tree-sitter, pandas 等
- 用于无网络环境的安装

### semgrep-offline-packages/ - Semgrep 离线依赖包
存放 Semgrep 及其依赖的离线包：
- semgrep 及其 60+ 个依赖包
- 用于无网络环境的 Semgrep 安装

## 文档引用规范

在文档中引用其他文档时，使用相对路径：

```markdown
# 正确示例
详细安装说明请参考 [OFFLINE-INSTALL.md](docs/guides/OFFLINE-INSTALL.md)。

# 错误示例
详细安装说明请参考 [OFFLINE-INSTALL.md](OFFLINE-INSTALL.md)。
```

## 维护说明

1. **新增规约**：在 `references/` 对应目录下添加 Markdown 文件
2. **新增脚本**：在 `scripts/` 目录下添加 Python 文件
3. **新增测试**：在 `tests/` 目录下添加测试文件
4. **新增文档**：在 `docs/` 对应目录下添加文档
5. **更新引用**：移动文件后，更新所有文档中的引用路径

---

**最后更新**: 2026-07-29  
**维护者**: Code Review Skill Team
