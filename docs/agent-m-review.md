# Agent M 文档验证报告（第 1 轮）

> 验证时间：2026-08-12
> 验证范围：README.md、docs/getting-started.md、docs/architecture.md、docs/ai-review.md
> 验证方式：逐条对照文档描述与实际代码/文件结构

---

## 验证通过项

- [x] **依赖安装说明完整** -- requirements.txt 包含 pyyaml、gitpython、rich、tree-sitter、tree-sitter-java、tree-sitter-python、tree-sitter-javascript、jinja2、pandas。getting-started.md 手动安装命令列出了全部 9 个包，依赖说明表（用途描述）与实际一致。
- [x] **scan.py 全库扫描命令正确** -- `python scripts/scan.py --repo ~/my-project --full-scan --workflow comprehensive` 可在 skill 仓库目录下运行，所有 CLI 参数（`--repo`、`--full-scan`、`--workflow`）均在 scan.py argparse 中定义。
- [x] **scan.py 分支差异扫描命令正确** -- `--base master --target release/1.0 --workflow security` 参数与 scan.py 定义匹配。
- [x] **scan.py Profile 指定命令正确** -- `--profile strict` 参数有效，scan.py 中 `load_profile()` 函数正确读取 `references/profiles/strict.yaml`。
- [x] **报告目录结构描述与实际一致** -- getting-started.md 和 architecture.md 描述的工作空间结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与 `create_workspace()` 函数实际创建的目录完全一致。
- [x] **文档中引用的所有主要文件均存在** -- `.trae/skills/code-review/SKILL.md`、`references/subagent-contract.md`、`references/main-agent-contract.md`、`references/RULE-GENERATOR-GUIDE.md`、`config.yaml`、`config/harness.yaml`、`requirements.txt`、`install-offline.sh`、`download-offline-packages.sh` 均存在。
- [x] **docs/ 目录下所有文档均存在** -- README.md 引用的 14 个历史文档（TECH-STACK.md、SUBAGENT-REVIEW-ARCHITECTURE.md、DIRECTORY-STRUCTURE.md 等）全部存在。
- [x] **规约文件完整** -- references/ 下的 design/（3 组）、implementation/（4 组）、security/（12 组）、rules/（1 组）、profiles/（3 个）、prompts/（5 个提示词 + README）、test-cases/（security 7 个、design 3 个、implementation 4 个）全部存在，与文档描述一致。
- [x] **harness/ 目录文件与 ai-review.md 描述一致** -- `__init__.py`、`decision_logger.py`、`feedback_manager.py`、`quality_monitor.py`、`cli.py` 全部存在。
- [x] **scripts/harness.py 入口正确** -- 脚本正确将项目根目录加入 sys.path 后 `from harness.cli import main`。
- [x] **Harness CLI 命令与文档一致** -- ai-review.md 描述的 `list`、`feedback`、`stats` 三个命令在 `harness/cli.py` 中全部实现，参数（`--issue-id`、`--verdict`、`--comment`、`--all`）匹配。
- [x] **scan.py 读取 harness.yaml** -- `load_harness_config()` 函数存在，正确读取 `config/harness.yaml`。
- [x] **scan.py 写入决策日志** -- `run_scan()` 中初始化 DecisionLogger 并调用 `log_decision()` + `save()`，将决策写入工作空间 decisions/ 目录。
- [x] **scan.py 读取历史反馈** -- `build_feedback_examples()` 函数存在，从 FeedbackManager 提取反馈并注入 AI 评审器。
- [x] **config.yaml 温度参数配置与 architecture.md 描述一致** -- config.yaml 中 `review.subagent.temperature` 的 5 个工作流值（security: 0.1, quality: 0.2, performance: 0.1, architecture: 0.2, comprehensive: 0.1）与 architecture.md 表格完全一致。
- [x] **project-structure.md 目录结构与实际情况一致** -- 该文档列出的所有目录和文件均存在，目录职责说明表准确。
- [x] **离线安装指南文件存在** -- getting-started.md 引用的 `docs/guides/OFFLINE-INSTALL.md` 和 `docs/guides/SEMGREP-OFFLINE-INSTALL.md` 均存在。
- [x] **README.md 顶层目录结构描述准确** -- scripts/、references/、harness/、config/、docs/、tests/、test-validation/、config.yaml、requirements.txt、install-offline.sh、.trae/skills/ 均与实际一致。

---

## 发现的问题

### 问题 1: [严重度 HIGH]
- **文件**: `docs/ai-review.md` 第 396 行、`docs/architecture.md` 第 505 行、`docs/project-structure.md` 第 32 行
- **描述**: `scripts/builtin_engine_v2.py` 文件状态矛盾。ai-review.md "已完成的工作"章节明确声明"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"，但该文件实际仍然存在于 `scripts/` 目录下（约 300+ 行代码）。同时 architecture.md 和 project-structure.md 的项目结构树仍将其列为正式文件。文档声明与实际状态存在直接矛盾。
- **建议修复**: 二选一：(a) 如果确实应该删除，则执行删除并确认 architecture.md / project-structure.md 的结构树中移除该文件；(b) 如果仍需要保留，则修正 ai-review.md 中的"删除"记录，说明该文件当前状态为"实验性，未集成到主流程"。

### 问题 2: [严重度 MEDIUM]
- **文件**: `docs/ai-review.md` 第 341、392 行
- **描述**: 测试数量描述过时。ai-review.md 两处声称"195 个测试全部通过"，但实际运行 `pytest tests/ --collect-only` 收集到 **314 个测试**。差异达 119 个测试，可能是后续迭代新增了测试文件（如 test_ai_reviewer_e2e.py、test_semgrep_integration.py、test_scheduler_e2e.py 等）但未更新文档。
- **建议修复**: 将"195 个测试全部通过"更新为"314 个测试全部通过"（需先确认全部通过），或改为动态描述如"300+ 个测试"。

### 问题 3: [严重度 MEDIUM]
- **文件**: `docs/ai-review.md` 第 168 行（架构总览 Mermaid 图）
- **描述**: 架构图中引用了不存在的 `confidence_thresholds.yaml` 文件。该文件在约束层中作为独立组件展示（"置信度阈值 -- confidence_thresholds.yaml -- 按规则配置最低置信度"），但该文件实际不存在。置信度阈值配置实际内嵌在 `config/harness.yaml` 的 `auto_improvement.min_accuracy_threshold` 字段中，并非独立文件。新开发者可能会尝试查找或创建这个文件。
- **建议修复**: 将架构图中的 `confidence_thresholds.yaml` 改为 `config/harness.yaml`（或 `harness.yaml 中的 auto_improvement 配置`），以反映实际配置位置。

### 问题 4: [严重度 MEDIUM]
- **文件**: `scripts/scan.py` 第 576 行、`docs/architecture.md` 第 149 行
- **描述**: `scan.py` 的 `--output` CLI 参数被接受但被静默忽略。argparse 定义了 `--output` 参数（默认值 `"report"`），architecture.md 示例中使用 `--output report/multi-engine/`，但 `run_scan()` 函数中从未读取 `args.output`。实际输出始终写入被扫描项目下的 `.code-review/workspace/<scan_id>/report/`。用户指定 `--output` 后不会收到任何错误，但输出位置与预期不符。
- **建议修复**: 二选一：(a) 在 `run_scan()` 中使用 `args.output` 覆盖默认输出目录；(b) 如果工作空间机制已取代 `--output`，则从 argparse 中移除该参数，并在 `--help` 中说明输出位置由工作空间自动管理。

### 问题 5: [严重度 LOW]
- **文件**: `docs/ai-review.md` 第 186-195 行（架构总览 Mermaid 图）
- **描述**: `auto_improver.py` 在架构图中作为已实现组件展示（反馈层："自动改进 -- auto_improver.py -- 根据反馈调整阈值"），但该文件尚未实现。ai-review.md 第 404 行的"待完成的工作"章节正确标注了该文件为"阶段 3：自动改进（优先级：低）"，但架构图未区分"已实现"与"计划中"的组件，容易误导新开发者认为该功能已可用。
- **建议修复**: 在架构图中对未实现的组件添加视觉标记（如虚线边框或"（计划中）"后缀），或在图下方添加注释说明哪些组件尚未实现。

### 问题 6: [严重度 LOW]
- **文件**: `docs/architecture.md` 第 119-143 行 vs `README.md` 第 6 行
- **描述**: "双引擎"与"三引擎"术语存在上下文混淆。README.md 核心特性写"三引擎融合"（Semgrep + Tree-sitter AST + 内置正则），architecture.md "多引擎融合架构"章节也列出三个引擎。但 architecture.md "各层实现原理详解 > 规约引擎层"中写"双引擎并行扫描（内置正则 + Semgrep）"，并在术语说明中解释 Tree-sitter AST 属于差异分析层。虽然从架构分层角度是正确的，但"双引擎"和"三引擎"在同一文档中交替出现，缺乏统一的顶层说明，新开发者容易困惑。
- **建议修复**: 在 architecture.md "多引擎融合架构"章节开头添加一段说明："整体系统采用三引擎融合（Semgrep + AST + Regex），其中规约引擎层使用双引擎（Semgrep + Regex），AST 引擎在差异分析层提供调用图支持。"统一读者预期。

---

## 总结

- **通过项**: 19
- **问题数**: HIGH=1, MEDIUM=3, LOW=2
- **总体评价**: 文档质量较高，核心功能描述（依赖安装、扫描命令、报告结构、规约文件、Harness 系统）与实际代码高度一致。主要问题集中在：(1) 一个已声明删除但仍存在的文件造成文档间矛盾；(2) 测试数量等统计数据未及时更新；(3) 架构图展示了尚未实现或不存在的配置组件，未做视觉区分。建议优先修复 HIGH 级别的文件状态矛盾问题。
