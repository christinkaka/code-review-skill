## 项目目录结构

code-review-skill 项目本身的目录结构：

```
code-review-skill/                    # 工具项目（不存放扫描输出）
├── .trae/                            # Trae Skill 配置
│   └── skills/
│       └── code-review/
│           └── SKILL.md              # Skill 定义文件
├── .gitignore                        # Git 忽略规则
├── README.md                         # 项目说明文档
├── requirements.txt                  # Python 依赖声明
├── config.yaml                       # 主配置文件
├── config/
│   └── harness.yaml                  # Harness 系统配置
├── docs/                             # 详细文档
│   ├── TECH-STACK.md                 # 技术栈说明
│   ├── DIRECTORY-STRUCTURE.md        # 目录结构
│   └── ...
├── harness/                          # Harness 系统模块
│   ├── __init__.py
│   ├── decision_logger.py            # 决策日志记录器
│   ├── feedback_manager.py           # 反馈管理器
│   ├── quality_monitor.py            # 质量监控器
│   └── cli.py                        # Harness CLI 工具
├── scripts/                          # 扫描脚本
│   ├── scan.py                       # 主扫描入口
│   ├── diff_analyzer.py              # Git diff 分析
│   ├── call_graph.py                 # 调用图构建
│   ├── rule_engine.py                # 规则引擎（Semgrep）
│   ├── builtin_engine_v2.py          # 内置规则引擎（AST + 正则）
│   ├── rule_compiler.py              # 规则预编译器
│   ├── ai_reviewer.py                # AI 评审任务生成
│   ├── report_generator.py           # 报告生成器
│   ├── scheduler.py                  # 定时调度器
│   ├── notifier.py                   # 通知器
│   ├── harness.py                    # Harness 脚本
│   └── test_rules.py                 # 规则测试
├── references/                       # 规则和提示词
│   ├── RULE-GENERATOR-GUIDE.md       # 规则生成指南
│   ├── compiled/                     # 预编译规则（自动生成）
│   ├── profiles/                     # 扫描配置 Profile
│   │   ├── default.yaml              # 默认配置
│   │   ├── strict.yaml               # 严格配置
│   │   └── minimal.yaml              # 最小配置
│   ├── prompts/                      # AI 评审提示词
│   │   ├── security-audit-prompt.md
│   │   ├── code-quality-prompt.md
│   │   └── ...
│   ├── security/                     # 安全规则
│   │   ├── authorization.yaml
│   │   └── ...
│   ├── implementation/               # 实现规则
│   │   ├── null-safety.yaml
│   │   └── ...
│   ├── design/                       # 设计规则
│   │   ├── api-design.yaml
│   │   └── ...
│   └── rules/                        # 自定义规则
│       └── custom.yaml
├── offline-packages/                 # Python 离线安装包
│   └── *.whl                         # 多平台 wheel 文件
├── semgrep-offline-packages/         # Semgrep 离线安装包
├── tests/                            # 单元测试
│   ├── test_scan.py                  # 扫描测试
│   ├── test_rule_engine.py           # 规则引擎测试
│   ├── test_harness.py               # Harness 测试
│   └── ...
├── test-validation/                  # 测试验证项目（用于演示）
├── install-offline.sh                # 离线依赖安装脚本
├── install-semgrep-offline.sh        # Semgrep 离线安装（Unix）
├── install-semgrep-offline.ps1       # Semgrep 离线安装（Windows）
└── download-offline-packages.sh      # 离线包下载脚本
```

### 目录职责说明

| 目录 | 职责 | 是否会被扫描污染 |
|------|------|------------------|
| `.trae/` | Trae Skill 定义 | ❌ 不会 |
| `config/` | 配置文件 | ❌ 不会 |
| `docs/` | 项目文档 | ❌ 不会 |
| `harness/` | Harness 系统代码 | ❌ 不会 |
| `scripts/` | 扫描脚本代码 | ❌ 不会 |
| `references/` | 规则和提示词 | ❌ 不会 |
| `tests/` | 单元测试 | ❌ 不会 |
| `offline-packages/` | Python 离线包 | ❌ 不会 |
| `semgrep-offline-packages/` | Semgrep 离线包 | ❌ 不会 |
| `<被扫描项目>/.code-review/` | **扫描输出** | ✅ 这是输出位置 |

详细技术分析请参考 [TECH-STACK.md](TECH-STACK.md)。

---

