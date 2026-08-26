# Agent K 文档验证报告

> 验证时间：2026-08-12
> 验证身份：第一次接触 code-review-skill 项目的新开发者
> 验证方法：严格按照 README.md 和 docs/getting-started.md 的指引，逐步操作并对照验证

---

## 验证通过项

- [x] `requirements.txt` 文件存在，包含所有核心 Python 依赖（pyyaml, gitpython, rich, tree-sitter, tree-sitter-java, tree-sitter-python, tree-sitter-javascript, jinja2, pandas）
- [x] `pip install -r requirements.txt` 命令可正常执行
- [x] `python scripts/scan.py --help` 可正常运行，帮助信息完整
- [x] `python scripts/scan.py --repo test-validation --full-scan --workflow comprehensive` 可在 skill 仓库目录下成功运行，输出 70 个问题
- [x] 报告输出路径 `<被扫描项目>/.code-review/workspace/<scan_id>/report/` 与文档描述一致
- [x] 报告文件 `report.json`、`report.md`、`summary.json`、`subagent-review-task.md` 均已生成
- [x] 决策日志目录 `decisions/` 已生成，包含 JSON 文件
- [x] 安全规约 12 个文件全部存在于 `references/security/` 目录（authorization, xxe, xss, path-traversal, privilege-escalation, signature-bypass, sql-injection, ssrf, hardcoded-secrets, deserialization, log-injection, weak-randomness）
- [x] 设计规约 3 个文件全部存在于 `references/design/` 目录（architecture, api-design, database）
- [x] 实现规约 4 个文件全部存在于 `references/implementation/` 目录（naming, error-handling, concurrency, null-safety）
- [x] 测试案例目录 `references/test-cases/` 结构完整（security/design/implementation 子目录均有测试文件）
- [x] `references/profiles/` 包含 default.yaml、strict.yaml、minimal.yaml 三个 Profile
- [x] `references/prompts/` 包含 5 个工作流提示词文件
- [x] `config/harness.yaml` 存在且配置完整
- [x] `harness/` 目录包含 `__init__.py`、`decision_logger.py`、`feedback_manager.py`、`quality_monitor.py`、`cli.py`，与 ai-review.md 描述一致
- [x] `scripts/harness.py` CLI 命令可运行（list/feedback/stats 子命令均可用）
- [x] `scripts/rule_compiler.py --status` 可正常运行，显示 22 个规则文件编译状态
- [x] `.trae/skills/code-review/SKILL.md` 存在
- [x] `references/RULE-GENERATOR-GUIDE.md` 存在
- [x] `references/main-agent-contract.md` 和 `references/subagent-contract.md` 存在
- [x] `config.yaml` 存在且包含完整配置（review、semgrep、call_graph、schedule、prefilter 等）
- [x] `docs/` 目录下的文档文件齐全（getting-started.md, architecture.md, rules.md, ai-review.md, validation.md, advanced.md, project-structure.md 等）

---

## 发现的问题

### 问题 1: [MEDIUM] getting-started.md 手动安装命令遗漏 tree-sitter-python 和 tree-sitter-javascript

- **文件**: `docs/getting-started.md` 第 72 行
- **描述**: 手动安装命令 `pip install pyyaml tree-sitter tree-sitter-java gitpython rich jinja2 pandas` 遗漏了 `tree-sitter-python` 和 `tree-sitter-javascript`。而 `requirements.txt` 中包含了这两个依赖。新开发者如果按照手动安装指引操作，将缺少这两个包。
- **建议修复**: 将手动安装命令更新为：
  ```bash
  pip install pyyaml tree-sitter tree-sitter-java tree-sitter-python tree-sitter-javascript gitpython rich jinja2 pandas
  ```

### 问题 2: [MEDIUM] getting-started.md 验证安装命令不完整

- **文件**: `docs/getting-started.md` 第 91 行
- **描述**: 验证命令 `python -c "import yaml, git, jinja2, pandas; print('all ok')"` 没有验证 `tree_sitter` 和 `rich` 是否安装成功。新开发者执行此命令后，可能仍然缺少 tree-sitter 相关包。
- **建议修复**: 更新验证命令为：
  ```bash
  python -c "import yaml, git, jinja2, pandas, tree_sitter, rich; print('all ok')"
  ```

### 问题 3: [MEDIUM] getting-started.md 报告目录结构描述与实际输出不一致

- **文件**: `docs/getting-started.md` 第 132-144 行
- **描述**: 文档描述的工作空间结构包含多个在实际扫描输出中不存在的文件和目录。实际运行 `python scripts/scan.py --repo test-validation --full-scan --workflow comprehensive` 后，工作空间结构如下：

  **文档描述的结构**：
  ```
  .code-review/workspace/<scan_id>/
  ├── report/
  │   ├── report.json
  │   ├── report.md
  │   ├── summary.json
  │   └── subagent-review-task.md
  ├── cache/                       # 实际不存在
  ├── decisions/
  │   └── <scan_id>.json
  ├── decision-log.jsonl           # 实际不存在
  └── scan-config.yaml             # 实际不存在
  ```

  **实际输出的结构**：
  ```
  .code-review/workspace/<scan_id>/
  ├── decisions/
  │   └── 2026-08-12_13-52-04.json
  └── report/
      ├── report.json
      ├── report.md
      ├── subagent-review-task.md
      └── summary.json
  ```

  缺失项：`cache/` 目录、`decision-log.jsonl` 文件、`scan-config.yaml` 文件。
- **建议修复**: 更新文档中的目录结构描述，移除不存在的文件和目录，或标注为"计划中/可选"。

### 问题 4: [HIGH] architecture.md scripts/ 文件列表遗漏主入口 scan.py

- **文件**: `docs/architecture.md` 第 497-509 行
- **描述**: architecture.md 中"项目结构"章节列出了 scripts/ 目录下的文件，但遗漏了最重要的 `scan.py`（主扫描入口）。这是整个工具的核心入口文件，新开发者阅读架构文档时如果看不到这个文件，会对项目结构产生严重误解。
- **实际 scripts/ 目录文件列表**：
  - `ai_reviewer.py` - 文档已列
  - `builtin_engine_v2.py` - 文档已列
  - `call_graph.py` - 文档已列
  - `diff_analyzer.py` - 文档已列
  - `harness.py` - 文档已列
  - `notifier.py` - 文档已列
  - `report_generator.py` - 文档已列
  - `rule_compiler.py` - 文档已列
  - `rule_engine.py` - 文档已列
  - **`scan.py` - 文档未列（主入口！）**
  - `scheduler.py` - 文档已列
  - `test_rules.py` - 文档已列
- **建议修复**: 在 scripts/ 文件列表的最前面添加：
  ```
  ├── scan.py               # 主扫描入口
  ```

### 问题 5: [MEDIUM] architecture.md 工作空间目录结构描述与实际输出不一致

- **文件**: `docs/architecture.md` 第 199-215 行
- **描述**: 与问题 3 类似，architecture.md 中"目录关系"章节描述的工作空间结构也包含了实际不存在的 `cache/compiled/`、`feedbacks.json`、`stats_cache.json`。实际扫描只生成 `report/` 和 `decisions/` 两个子目录。
- **建议修复**: 更新目录结构描述，使其与实际输出一致。

### 问题 6: [MEDIUM] ai-review.md 目录结构描述中 `data/` 目录实际不存在

- **文件**: `docs/ai-review.md` 第 306-325 行
- **描述**: ai-review.md 描述了一个位于项目根目录的 `data/` 目录，包含 `decisions/`、`feedbacks.json`、`adjustments.json`、`stats_cache.json`。但经验证：
  - 项目根目录下 **不存在** `data/` 目录
  - 决策日志实际存储在被扫描项目的 `.code-review/workspace/<scan_id>/decisions/` 中
  - `harness.py list` 命令输出"暂无扫描记录"，尽管已有成功扫描的决策日志（说明 CLI 查找路径与实际存储路径不一致）
  - 虽然 `.gitignore` 中有 `data/` 条目，但该目录从未被创建
  - `config/harness.yaml` 中配置的路径（如 `data/decisions`、`data/feedbacks.json`）与实际行为不符
- **建议修复**: 更新 ai-review.md 的目录结构描述，明确说明决策日志存储在工作空间目录中而非 `data/` 目录。同时更新 `config/harness.yaml` 中的默认路径配置。

### 问题 7: [MEDIUM] ai-review.md 声称 builtin_engine_v2.py 已删除但文件仍存在

- **文件**: `docs/ai-review.md` 第 395 行
- **描述**: ai-review.md "代码清理"章节明确写道"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但该文件实际仍然存在于 `scripts/builtin_engine_v2.py`。这与文档描述矛盾，也与 `docs/architecture.md` 第 503 行和 `docs/project-structure.md` 第 32 行将其列为正式组件矛盾。
- **建议修复**: 二选一：
  1. 如果该文件确实应该删除，则执行删除操作
  2. 如果该文件仍有用途，则修正 ai-review.md 中的描述

### 问题 8: [MEDIUM] architecture.md Mermaid 图引用不存在的 `confidence_thresholds.yaml` 文件

- **文件**: `docs/architecture.md` 第 167-169 行
- **描述**: 架构图中"监控层"部分引用了 `confidence_thresholds.yaml` 作为"置信度阈值"的配置文件。但在整个项目中不存在此文件。置信度相关配置实际在 `config/harness.yaml` 中（`auto_improvement.min_accuracy_threshold` 和 `max_adjustment_delta`）。新开发者按照架构图去寻找这个文件会找不到。
- **建议修复**: 将架构图中的 `confidence_thresholds.yaml` 改为 `config/harness.yaml`，或在 `config/` 目录下创建独立的 `confidence_thresholds.yaml` 文件。

### 问题 9: [LOW] README.md 顶层目录结构描述不完整

- **文件**: `README.md` 第 106-117 行
- **描述**: README.md 的"目录结构（顶层）"章节遗漏了多个实际存在的顶层目录和文件：
  - 缺少 `config/` 目录（存放 harness.yaml）
  - 缺少 `harness/` 目录（Harness 系统模块）
  - 缺少 `requirements.txt` 文件
  - 缺少 `install-offline.sh` 等安装脚本
  - 缺少 `test-validation/` 目录
- **建议修复**: 补充缺失的目录和文件：
  ```
  code-review-skill/
  ├── scripts/           # 扫描引擎（Python）
  ├── references/        # 规约与规约 Profile
  ├── harness/           # Harness 系统（决策日志、反馈闭环）
  ├── config/            # 配置文件（harness.yaml）
  ├── docs/              # 项目文档
  ├── tests/             # 单元测试
  ├── test-validation/   # 集成测试用例
  ├── config.yaml        # 主配置
  ├── requirements.txt   # Python 依赖
  ├── install-offline.sh # 离线安装脚本
  └── .trae/skills/      # TRAE Skill 入口
  ```

### 问题 10: [LOW] architecture.md 工作空间使用说明中的示例输出与实际不符

- **文件**: `docs/architecture.md` 第 239-243 行
- **描述**: 文档示例中 `ls` 命令输出显示工作空间包含 `report/ cache/ decisions/ feedbacks.json stats_cache.json`，但实际扫描后只生成 `report/` 和 `decisions/`。新开发者按照文档操作后看到的输出与预期不符，可能产生困惑。
- **建议修复**: 更新示例输出为实际的结构：`report/ decisions/`

---

## 补充说明

### 关于 harness.py CLI 与数据存储路径的一致性问题

`scripts/harness.py list` 输出"暂无扫描记录"，但实际已有成功扫描并生成了决策日志文件（位于 `test-validation/.code-review/workspace/<scan_id>/decisions/`）。这说明 Harness CLI 的数据查找路径与扫描时的决策日志写入路径不一致。这可能是 `config/harness.yaml` 中配置的 `data/decisions` 路径仍在使用，而 scan.py 实际将数据写入了工作空间目录。建议统一数据存取路径。

### 关于 architecture.md 中"已删除"与"仍存在"的矛盾

ai-review.md 声称删除了 `builtin_engine_v2.py` 和 `dual_engine.py`，但 `builtin_engine_v2.py` 实际存在，`dual_engine.py` 确实已删除。architecture.md 和 project-structure.md 都将 `builtin_engine_v2.py` 列为正式组件。这说明 ai-review.md 的清理记录有误，或删除操作未执行。

---

## 总结

- **通过项**: 23
- **问题数**: HIGH=1, MEDIUM=7, LOW=2
- **总计**: 10 个问题

### 按严重度分布

| 严重度 | 数量 | 说明 |
|--------|------|------|
| HIGH | 1 | architecture.md 遗漏 scan.py 主入口 |
| MEDIUM | 7 | 目录结构描述不一致、依赖列表不完整、文件引用错误 |
| LOW | 2 | README 目录结构不完整、示例输出过时 |

### 核心问题归纳

1. **文档与实际输出不一致**（问题 3、5、10）：getting-started.md 和 architecture.md 描述的工作空间目录结构包含多个实际不存在的文件和目录，新开发者按照文档操作会产生困惑。
2. **依赖说明不完整**（问题 1、2）：手动安装和验证命令遗漏了 tree-sitter-python 和 tree-sitter-javascript。
3. **文件引用错误**（问题 4、8）：architecture.md 遗漏 scan.py 主入口，引用不存在的 confidence_thresholds.yaml。
4. **描述与实际矛盾**（问题 7）：ai-review.md 声称已删除的文件实际仍存在。
5. **Harness 数据路径不一致**（问题 6 + 补充说明）：harness.yaml 配置路径、CLI 查找路径、scan.py 写入路径三者不一致。
