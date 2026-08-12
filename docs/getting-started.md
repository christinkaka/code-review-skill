# 快速开始

## 引导提示词

以下是触发本 Skill 的典型提示词，Agent 会根据这些关键词自动激活代码评审能力：

### 基础扫描

```
帮我扫描一下 release/1.0 分支和 master 分支的代码差异，看看有没有安全问题
```

```
对当前仓库执行代码评审，使用默认规约
```

```
检查一下这个 PR 有没有安全漏洞
```

### 指定规约

```
用安全规约扫描一下这个仓库，重点关注 XXE 和 SQL 注入
```

```
使用严格模式评审代码，所有规约提升为 ERROR 级别
```

```
只检查安全相关的规约，跳过设计和命名规范
```

### 调用链分析

```
分析 release 分支的变更代码，找出所有受影响的方法和调用链
```

```
追踪这个变更的影响范围，看看哪些下游方法会受到影响
```

### 自定义规则

```
帮我添加一条自定义规则：检查日志中是否打印了密码
```

### 测试验证

```
对 test-validation 目录下的代码做一次全库扫描，验证规则效果
```

```
跑一下单元测试，看看有没有误报漏报
```

## 安装

> **重要**：下面的命令需要在 **code-review-skill 仓库目录**下执行（脚本在 `scripts/` 子目录）。

### 1. 一键安装所有依赖（推荐）

```bash
# 安装全部 Python 依赖
pip install -r requirements.txt

# 或手动安装核心依赖
pip install pyyaml tree-sitter tree-sitter-java tree-sitter-python tree-sitter-javascript gitpython rich jinja2 pandas
```

`requirements.txt` 中的依赖说明：
- `pyyaml`、`jinja2` - 配置加载与报告模板
- `gitpython` - Git 分支差异分析
- `rich` - 终端输出美化
- `tree-sitter`、`tree-sitter-java`、`tree-sitter-python`、`tree-sitter-javascript` - AST 解析（调用图）
- `pandas` - 报告数据处理

### 2. 可选依赖（推荐）

```bash
brew install semgrep  # macOS
```

### 3. 验证安装

```bash
python -c "import yaml, git, jinja2, pandas; print('all ok')"
semgrep --version
```

> 完整离线安装方案请参考 [guides/OFFLINE-INSTALL.md](guides/OFFLINE-INSTALL.md) 和 [guides/SEMGREP-OFFLINE-INSTALL.md](guides/SEMGREP-OFFLINE-INSTALL.md)

## 执行扫描

> **再次提醒**：下面的命令需要在 **code-review-skill 仓库目录**下执行（脚本在 `scripts/` 子目录）。

### 全库静态扫描

```bash
# 先 cd 到 skill 仓库根目录
cd /path/to/code-review-skill

python scripts/scan.py --repo ~/my-project --full-scan --workflow comprehensive
```

### 分支差异扫描

```bash
cd /path/to/code-review-skill

python scripts/scan.py \
  --repo ~/my-project \
  --base master \
  --target release/1.0 \
  --workflow security
```

### 指定 Profile

```bash
python scripts/scan.py --repo ~/my-project --full-scan --profile strict
```

## 查看报告

扫描完成后报告输出到被扫描项目的 `.code-review/workspace/<scan_id>/`：

```
.code-review/workspace/2026-08-12_10-19-16_c284/
├── report/
│   ├── report.json              # 完整 JSON 报告
│   ├── report.md                # Markdown 报告（推荐阅读）
│   ├── summary.json             # 摘要（问题数、按规则/严重度分布）
│   └── subagent-review-task.md  # 子 Agent 评审任务（主 Agent 读取）
├── cache/                       # 扫描缓存（下次扫描加速用）
├── decisions/                   # 决策日志（Harness 系统，按时间归档）
│   └── 2026-08-12_13-39-17.json
├── feedbacks.json               # 用户反馈记录（用户通过 harness.py feedback 添加反馈后生成）
└── stats_cache.json             # 统计缓存（执行 harness.py stats 后生成）
```

**关键文件说明**：

| 文件 | 作用 |
|------|------|
| `report.md` | 人类阅读入口——按文件/规则分组的问题清单 |
| `report.json` | 程序处理入口——所有问题详情 |
| `summary.json` | 摘要统计——用于 CI/CD 阈值检查 |
| `subagent-review-task.md` | 主 Agent 读取并委派给子 Agent 的任务定义 |
| `decisions/` | Harness 系统决策日志（推荐，看时间归档更易追踪） |
| `cache/` | 增量扫描缓存，加速下次扫描 |

## 运行测试

```bash
# 单元测试
python -m pytest tests/ -v

# 集成测试（使用 test-validation 内置仓库）
python scripts/scan.py --repo test-validation --full-scan --workflow comprehensive
```

## 常见问题

### Q1: 为什么不需要 AI API Key？

本 Skill 的核心架构是**主 Agent 调度 + 子 Agent 评审**：

- **Python 脚本**（确定性扫描）：基于 Semgrep + Tree-sitter + 内置正则，零 AI 依赖
- **子 Agent**：由 TRAE Agent 委派，使用主 Agent 的 LLM 上下文，**不需要单独的 API Key**
- **离线优先**：所有规则扫描、AI 评审决策记录都可在本地完成

### Q2: Subagent 评审和 Semgrep 评审有什么区别？

| 维度 | Semgrep 评审 | Subagent 评审 |
|------|-------------|---------------|
| 准确性 | 高（基于模式匹配） | 中高（基于 LLM 推理） |
| 上下文理解 | 低（无业务语义） | 高（理解业务逻辑） |
| 误报率 | 中（需结合上下文判断） | 低（AI 推理过滤） |
| 速度 | 快（毫秒级） | 慢（秒级） |
| 适用场景 | 已知模式的安全问题 | 复杂业务逻辑、设计缺陷 |

**推荐组合**：Semgrep 全量扫描 + Subagent 二次评审，覆盖 95%+ 的真实问题。

### Q3: 离线安装和在线安装有什么区别？

在线安装直接 `pip install` 即可。离线安装需要：

```bash
# 下载 wheel 包（在有网的机器上）
pip download pyyaml tree-sitter tree-sitter-java -d wheels/

# 在目标机器安装
pip install --no-index --find-links=wheels/ pyyaml tree-sitter tree-sitter-java
```

Semgrep 离线安装详见 [guides/SEMGREP-OFFLINE-INSTALL.md](guides/SEMGREP-OFFLINE-INSTALL.md)。

### Q4: 如何优化大仓库的扫描性能？

1. **使用 diff 扫描**：只在 PR/MR 触发，不全库扫描
2. **使用缓存**：`references/compiled/` 缓存规则编译结果
3. **并行扫描**：内置多进程 Semgrep（默认开启）
4. **只跑必要 Workflow**：`--workflow security` 比 `comprehensive` 快 3-5 倍

### Q5: 如何添加自定义规则？

详见 [rules.md → 自定义规则](rules.md#自定义规则)。

## 下一步

- 阅读 [architecture.md](architecture.md) 了解架构设计
- 阅读 [rules.md](rules.md) 了解规约库与配置
- 阅读 [ai-review.md](ai-review.md) 了解 AI 评审机制
