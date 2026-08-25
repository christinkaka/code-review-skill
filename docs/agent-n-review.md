# Agent N 文档验证报告（第 1 轮）

## 验证通过项

- [x] requirements.txt 依赖完整 -- getting-started.md 列出的 8 个包（pyyaml, tree-sitter, tree-sitter-java, tree-sitter-python, tree-sitter-javascript, gitpython, rich, jinja2, pandas）与 requirements.txt 完全一致
- [x] scan.py 命令可以在文档指定的目录下运行 -- `scripts/scan.py` 存在且可执行，`--full-scan`、`--workflow`、`--trigger`、`--profile` 等参数均有定义
- [x] scripts/ 目录文件列表与 architecture.md 描述一致 -- 12 个 .py 文件全部存在（scan.py, diff_analyzer.py, call_graph.py, rule_engine.py, rule_compiler.py, builtin_engine_v2.py, ai_reviewer.py, report_generator.py, harness.py, scheduler.py, notifier.py, test_rules.py）
- [x] 规约文件全部存在 -- references/design/（3 组）、references/implementation/（4 组）、references/security/（12 组）、references/rules/（1 组），每组含 .md + .yaml
- [x] references/profiles/ 包含 3 个 Profile（default.yaml, strict.yaml, minimal.yaml）
- [x] references/prompts/ 包含 5 个工作流提示词 + README.md，与 architecture.md 描述一致
- [x] references/test-cases/ 结构完整（security/、design/、implementation/ 三个子目录）
- [x] Harness 系统核心文件全部存在 -- config/harness.yaml、harness/（5 个 .py 文件）、scripts/harness.py
- [x] config.yaml 温度参数配置与 architecture.md 描述一致（security: 0.1, quality: 0.2 等）
- [x] 文档中引用的所有主要文件路径均存在 -- .trae/skills/code-review/SKILL.md, references/subagent-contract.md, references/main-agent-contract.md, references/RULE-GENERATOR-GUIDE.md, docs/ 下所有 .md 文件, docs/guides/ 离线安装指南, docs/reports/ 历史报告
- [x] 工作空间机制描述与代码匹配 -- scan.py 确实在被扫描项目的 `.code-review/workspace/<scan_id>/` 下创建工作空间
- [x] references/compiled/ 预编译缓存目录存在，结构与 architecture.md 描述一致
- [x] test-validation/ 测试验证数据存在，包含 java/python/typescript 三种语言的测试用例
- [x] offline-packages/ 和 semgrep-offline-packages/ 离线包目录存在
- [x] install-offline.sh、download-offline-packages.sh 存在

## 发现的问题

### 问题 1: [严重度 HIGH]
- 文件: `scripts/scan.py`（第 576 行）、`docs/architecture.md`（第 149 行）
- 描述: `--output` 参数是死代码。scan.py 的 argparse 定义了 `--output` 参数（`parser.add_argument("--output", default="report", help="报告输出目录")`），但代码中从未读取 `args.output`。实际输出目录始终由 workspace 机制决定（`output_dir = workspace["report_dir"]`，第 349 行）。然而 architecture.md 的命令示例仍使用 `--output report/multi-engine/`，scan.py 文件头注释（第 4 行）和用法示例（第 562 行）也包含 `--output`。新开发者会误以为可以通过此参数控制输出目录。
- 建议修复: 方案 A：删除 `--output` 参数定义及所有文档引用，统一使用 workspace 机制。方案 B：恢复 `--output` 的实际功能，允许用户覆盖默认输出路径。

### 问题 2: [严重度 MEDIUM]
- 文件: `docs/ai-review.md`（"代码清理"章节，第 395 行）
- 描述: ai-review.md 声称"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"，但该文件实际仍存在于 `scripts/builtin_engine_v2.py`。文档描述与代码现状矛盾，会误导开发者以为该文件已被清理。
- 建议修复: 如果该文件确实应该删除，则执行删除；如果仍有保留价值，则修改 ai-review.md 中的描述，移除"已删除"的声明。

### 问题 3: [严重度 MEDIUM]
- 文件: `docs/ai-review.md`（架构图"约束层"，第 167-169 行）
- 描述: 架构图中约束层 C2 引用了 `confidence_thresholds.yaml`（"按规则配置最低置信度"），但项目中不存在此文件。搜索整个仓库未找到任何名为 `confidence_thresholds.yaml` 的文件。该文件既不在 `config/` 也不在 `harness/` 目录中。
- 建议修复: 如果该文件属于待开发功能，应在架构图中标注"待实现"；如果功能已合并到其他配置文件（如 harness.yaml），应更新架构图中的引用。

### 问题 4: [严重度 MEDIUM]
- 文件: `docs/architecture.md`（"多引擎融合架构"章节 vs "规约引擎层"章节）
- 描述: 引擎描述自相矛盾。"多引擎融合架构"章节（第 119-186 行）描述三引擎融合：Semgrep + Tree-sitter AST + 内置正则，并给出融合策略和优先级（AST > Semgrep > Regex）。但后面"规约引擎层"的"术语说明"（第 421 行）又称"双引擎"指"内置正则 + Semgrep"，Tree-sitter AST 属于差异分析层，不参与规约引擎层。两处描述对 Tree-sitter AST 的定位完全不同，新开发者会感到困惑。
- 建议修复: 统一引擎分类描述。建议在"多引擎融合架构"章节明确说明 Tree-sitter AST 的双重角色：在差异分析层提供调用图构建，在规约引擎层提供精确语法分析扫描。或者重新组织章节结构，避免同一术语在不同层次有不同含义。

### 问题 5: [严重度 MEDIUM]
- 文件: `docs/getting-started.md`（"查看报告"章节，第 132-142 行）
- 描述: 报告目录结构描述不完整。getting-started.md 的目录树只列出了 `report/`、`cache/`、`decisions/` 三个子目录，但 architecture.md 的工作空间结构（第 213-214 行）和 scan.py 代码（第 431-432 行）还会在工作空间根目录创建 `feedbacks.json` 和 `stats_cache.json`。这两个文件在 getting-started.md 中完全未提及。
- 建议修复: 在 getting-started.md 的目录树中补充 `feedbacks.json` 和 `stats_cache.json`，与 architecture.md 保持一致。

### 问题 6: [严重度 LOW]
- 文件: `README.md`（"目录结构（顶层）"章节，第 106-119 行）
- 描述: 顶层目录结构遗漏多个实际存在的目录和文件。缺少：`data/`（运行时数据目录）、`offline-packages/`（核心离线依赖包）、`semgrep-offline-packages/`（Semgrep 离线依赖包）、`download-offline-packages.sh`（离线包下载脚本）、`install-semgrep-offline.sh`（Semgrep 离线安装 Unix 脚本）、`install-semgrep-offline.ps1`（Semgrep 离线安装 Windows 脚本）。
- 建议修复: 补充遗漏的目录和文件到 README.md 的目录结构中。

### 问题 7: [严重度 LOW]
- 文件: `docs/architecture.md`（"项目结构"章节，第 479-521 行）
- 描述: 项目结构遗漏文件。列出了 `install-offline.sh` 和 `download-offline-packages.sh`，但未列出实际存在于项目根目录的 `install-semgrep-offline.sh` 和 `install-semgrep-offline.ps1`。
- 建议修复: 在项目结构中补充 `install-semgrep-offline.sh` 和 `install-semgrep-offline.ps1`。

### 问题 8: [严重度 LOW]
- 文件: `docs/ai-review.md`（"目录结构"章节，第 306-325 行）
- 描述: `data/` 目录结构描述与实际行为不一致。ai-review.md 描述 `data/` 目录下包含 `feedbacks.json`、`adjustments.json`、`stats_cache.json` 等文件，但实际 scan.py 在运行时会将这些文件重定向到工作空间目录（scan.py 第 431-432 行覆盖了 harness.yaml 中的路径配置）。实际 `data/` 目录几乎为空（仅有空的 `decisions/` 子目录）。同时 harness.yaml 中配置的默认路径（`data/decisions`、`data/feedbacks.json` 等）在运行时全部被覆盖，配置文件的默认值实际不生效。
- 建议修复: 在 ai-review.md 的目录结构说明中注明 `data/` 目录的默认路径会被 scan.py 运行时覆盖为工作空间路径。或者更新 harness.yaml 的默认配置，使其与实际行为一致。

## 总结

- 通过项: 15
- 问题数: HIGH=1, MEDIUM=4, LOW=3
- 总体评价: 文档整体质量较好，核心文件结构、依赖说明、规约文件、Harness 系统描述基本准确。主要问题集中在：(1) `--output` 死参数会误导使用者（HIGH）；(2) 代码清理声明与实际不符、架构图中引用不存在的文件、引擎描述自相矛盾、报告目录结构不完整（4 个 MEDIUM）；(3) 顶层目录结构遗漏、data/ 目录描述与实际行为不一致（3 个 LOW）。
