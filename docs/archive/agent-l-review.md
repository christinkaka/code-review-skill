# Agent L 文档验证报告

> 验证时间: 2026-08-12
> 验证人: Agent L (首次接触项目的新开发者视角)
> 验证范围: README.md, docs/getting-started.md, docs/architecture.md, docs/rules.md, docs/ai-review.md

---

## 验证通过项

- [x] **README.md "30 秒上手" 命令可正常执行** -- `git clone` / `pip install -r requirements.txt` / `python scripts/scan.py --repo ~/my-project --full-scan --workflow comprehensive` 均可正常运行
- [x] **requirements.txt 依赖完整** -- 包含 pyyaml, gitpython, rich, tree-sitter, tree-sitter-java, tree-sitter-python, tree-sitter-javascript, jinja2, pandas，覆盖所有代码 import 需求
- [x] **scan.py 在 skill 仓库目录下可正常运行** -- 使用 `python scripts/scan.py --repo test-validation --full-scan --workflow comprehensive` 验证，成功完成扫描，发现 70 个问题，耗时 2.46s
- [x] **报告目录结构基本正确** -- 实际输出 `report/report.json`, `report/report.md`, `report/summary.json`, `report/subagent-review-task.md`, `decisions/`, `cache/` 均存在
- [x] **architecture.md scripts/ 文件列表与实际一致** -- 文档列出 12 个脚本文件（scan.py, diff_analyzer.py, call_graph.py, rule_engine.py, rule_compiler.py, builtin_engine_v2.py, ai_reviewer.py, report_generator.py, harness.py, scheduler.py, notifier.py, test_rules.py），实际 scripts/ 目录完全匹配
- [x] **安全规约文件全部存在（12 类）** -- authorization.md, xxe.md, xss.md, path-traversal.md, privilege-escalation.md, signature-bypass.md, sql-injection.md, ssrf.md, hardcoded-secrets.md, deserialization.md, log-injection.md, weak-randomness.md 均存在于 `references/security/`
- [x] **设计规约文件全部存在（3 类）** -- architecture.md, api-design.md, database.md 均存在于 `references/design/`
- [x] **实现规约文件全部存在（4 类）** -- naming.md, error-handling.md, concurrency.md, null-safety.md 均存在于 `references/implementation/`
- [x] **测试案例文件全部存在** -- `references/test-cases/` 下 security/（7 个）、design/（3 个）、implementation/（4 个）测试文件齐全
- [x] **Harness 核心模块已实现** -- harness/ 目录下 `__init__.py`, `decision_logger.py`, `feedback_manager.py`, `quality_monitor.py`, `cli.py` 全部存在且功能完整
- [x] **config/harness.yaml 存在且配置正确** -- 与 ai-review.md 描述的结构一致（harness.enabled, decision_logging, feedback, auto_improvement, quality_monitor）
- [x] **scan.py 正确集成 Harness 系统** -- `load_harness_config()`, `init_harness_components()`, `build_feedback_examples()` 函数均已实现，扫描时自动记录决策日志
- [x] **config.yaml 温度参数与文档一致** -- architecture.md 描述的温度配置（security: 0.1, quality: 0.2, performance: 0.1, architecture: 0.2, comprehensive: 0.1）与 config.yaml 实际内容完全一致
- [x] **Profile 文件齐全** -- `references/profiles/` 下 default.yaml, strict.yaml, minimal.yaml 均存在
- [x] **提示词文件齐全（5 种工作流）** -- `references/prompts/` 下 security-audit-prompt.md, code-quality-prompt.md, performance-review-prompt.md, architecture-review-prompt.md, ai-enhancer-prompt.md 均存在
- [x] **README.md 引用的所有文档文件均存在** -- docs/getting-started.md, docs/architecture.md, docs/project-structure.md, docs/rules.md, docs/ai-review.md, docs/validation.md, docs/advanced.md, references/subagent-contract.md, references/main-agent-contract.md, references/RULE-GENERATOR-GUIDE.md, .trae/skills/code-review/SKILL.md
- [x] **历史文档（docs/）全部存在** -- TECH-STACK.md, SUBAGENT-REVIEW-ARCHITECTURE.md, DIRECTORY-STRUCTURE.md, VERIFICATION_MATRIX.md, COMPLETION-REPORT.md, IMPLEMENTATION-PLAN.md, CLEANUP-REPORT.md, ITERATION-REPORT.md, SPECS-SUMMARY.md, WORKFLOW-UPDATE.md
- [x] **guides/ 离线安装文档存在** -- docs/guides/OFFLINE-INSTALL.md, docs/guides/SEMGREP-OFFLINE-INSTALL.md 均存在
- [x] **references/compiled/ 预编译缓存结构正确** -- manifest.json 及各子目录（security/, design/, implementation/, rules/）下的 .md.json 文件齐全
- [x] **Harness CLI 命令与文档一致** -- `list`, `feedback`, `stats` 三个子命令的参数和用法与 ai-review.md 描述一致
- [x] **工作空间机制正确** -- 工作空间创建在被扫描项目的 `.code-review/workspace/` 下，不污染工具项目

---

## 发现的问题

### 问题 1: [MEDIUM] getting-started.md 手动安装依赖列表不完整

- **文件**: `docs/getting-started.md` 第 72 行
- **描述**: 手动安装命令 `pip install pyyaml tree-sitter tree-sitter-java gitpython rich jinja2 pandas` 缺少 `tree-sitter-python` 和 `tree-sitter-javascript`。而 `requirements.txt` 中包含了这两个依赖。新开发者如果按手动安装指引操作，将缺少多语言 AST 解析能力。
- **建议修复**: 将手动安装命令更新为：
  ```bash
  pip install pyyaml tree-sitter tree-sitter-java tree-sitter-python tree-sitter-javascript gitpython rich jinja2 pandas
  ```
  或者在说明中注明 "手动安装仅列出核心依赖，完整列表请参考 requirements.txt"。

---

### 问题 2: [MEDIUM] getting-started.md 报告目录结构描述了实际不存在的文件

- **文件**: `docs/getting-started.md` 第 132-144 行
- **描述**: 报告目录结构示例中列出了 `decision-log.jsonl` 和 `scan-config.yaml` 两个文件，但实际运行 `scan.py` 后，工作区中并不生成这两个文件。实际工作区结构为：
  ```
  workspace/<scan_id>/
  ├── report/
  │   ├── report.json
  │   ├── report.md
  │   ├── summary.json
  │   └── subagent-review-task.md
  ├── cache/
  └── decisions/
      └── <timestamp>.json
  ```
  缺少 `decision-log.jsonl`（旧版按行追加格式已被替换为 `decisions/` 目录）和 `scan-config.yaml`（代码中未实现该功能）。同时，文档中也缺少对 `feedbacks.json` 和 `stats_cache.json`（Harness 启用时在工作区根目录生成）的描述。
- **建议修复**: 更新目录结构示例，移除 `decision-log.jsonl` 和 `scan-config.yaml`，补充 `feedbacks.json` 和 `stats_cache.json`（标注为 Harness 启用时生成）。

---

### 问题 3: [MEDIUM] ai-review.md 架构流程图引用了不存在的 `confidence_thresholds.yaml`

- **文件**: `docs/ai-review.md` 第 167-169 行
- **描述**: 架构总览 flowchart 中"监控层"引用了 `confidence_thresholds.yaml` 作为"按规则配置最低置信度"的配置文件，但项目中不存在此文件（`config/` 目录下仅有 `harness.yaml`）。该文件在代码中也无任何引用。流程图描述了一个实际不存在的组件，会误导开发者理解系统架构。
- **建议修复**: 在流程图中标注 `confidence_thresholds.yaml` 为"待实现"，或将其从架构图中移除，待功能实现后再补充。

---

### 问题 4: [MEDIUM] ai-review.md 架构流程图引用了不存在的 `auto_improver.py`

- **文件**: `docs/ai-review.md` 第 193-195 行
- **描述**: 架构总览 flowchart 中"反馈层"引用了 `auto_improver.py`（"根据反馈调整阈值"），但该文件在 `harness/` 目录中不存在，且 `harness/__init__.py` 也未导出该模块。虽然文档第 401-411 行的"待完成的工作"中已标注为低优先级未实现，但架构图将其画为已实现的组件（无"待实现"标注），产生矛盾。
- **建议修复**: 在架构流程图中用虚线框或标注（如 `[待实现]`）区分已实现和未实现的组件，避免混淆。

---

### 问题 5: [MEDIUM] ai-review.md 目录结构描述与实际代码不一致

- **文件**: `docs/ai-review.md` 第 306-325 行
- **描述**: 文档描述的 Harness 目录结构包含一个项目根目录下的 `data/` 目录（含 `decisions/`, `feedbacks.json`, `adjustments.json`, `stats_cache.json`），但实际项目中：
  1. 根目录下不存在 `data/` 目录
  2. 决策日志存储在**被扫描项目的工作区** `decisions/` 目录下（由 scan.py 动态指定路径）
  3. `feedbacks.json` 和 `stats_cache.json` 也存储在工作区目录下，而非 `data/`
  4. `adjustments.json` 不存在（auto_improver.py 未实现）
  
  实际运行时，scan.py 会将路径覆盖为工作空间目录（见 scan.py 第 430-432 行），因此 `data/` 目录只是默认回退路径，实际不会使用。
- **建议修复**: 更新目录结构描述，说明 `data/` 是默认回退路径，实际数据存储在被扫描项目的工作区中。可补充说明：
  ```
  注意：以上 data/ 路径为默认值。实际运行时，scan.py 会将所有数据路径
  重定向到被扫描项目的工作区目录下，避免污染工具项目。
  ```

---

### 问题 6: [LOW] ai-review.md 声称已删除 `builtin_engine_v2.py` 但文件仍存在

- **文件**: `docs/ai-review.md` 第 395 行
- **描述**: "已完成的工作 > 代码清理"部分明确写道 "删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"，但 `scripts/builtin_engine_v2.py` 实际仍存在于项目中。文档描述与代码现状矛盾，会让新开发者困惑。
- **建议修复**: 二选一：
  1. 真正删除 `scripts/builtin_engine_v2.py`（如果确实不再需要）
  2. 更新 ai-review.md，将 "删除" 改为 "保留但标记为实验性"

---

### 问题 7: [LOW] architecture.md 多引擎融合描述前后不一致

- **文件**: `docs/architecture.md`
- **描述**: 文档中存在不一致的引擎数量描述：
  - 第 131-142 行"融合策略"部分描述了**三引擎**流程（Semgrep -> Tree-sitter AST -> 内置正则 -> 去重合并）
  - 第 312-316 行架构总览 flowchart 中写的是"双引擎合并"
  - 第 384 行数据流说明也写的是"双引擎并行扫描（内置正则 + Semgrep）"
  - 第 419 行规约引擎层表格标题为"双引擎合并"
  
  Tree-sitter AST 引擎在融合策略中被列为独立引擎，但在架构总览中被归入差异分析层（Level 1），不参与规约引擎层的合并。这种分层关系在文档中未清晰说明，容易造成混淆。
- **建议修复**: 在规约引擎层明确说明"双引擎"指的是"内置正则 + Semgrep"，而 Tree-sitter AST 引擎属于差异分析层（提供调用图分析），不属于规约引擎层的融合范围。或者统一全文术语，避免"三引擎"和"双引擎"混用。

---

## 总结

- **通过项**: 21
- **问题数**: HIGH=0, MEDIUM=5, LOW=2

**整体评价**: 文档质量较好，核心功能描述准确，所有引用的文件（除已标注为待实现的组件外）均存在，scan.py 可正常运行并产出正确结果。主要问题集中在 ai-review.md 的架构描述与实际代码结构不一致（`data/` 目录、`confidence_thresholds.yaml`、`auto_improver.py`），以及 getting-started.md 的报告目录结构包含了已废弃的文件名。建议优先修复 5 个 MEDIUM 级别问题，以提升新开发者的上手体验。
