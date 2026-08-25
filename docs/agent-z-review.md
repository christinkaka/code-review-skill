# Agent Z 文档验证报告（第 7 轮）

## 验证通过项

- [x] **builtin_engine_v2.py 状态描述已一致为"保留并集成"** — `docs/ai-review.md` 第 398 行明确写为"保留并集成 scripts/builtin_engine_v2.py（Tree-sitter AST 引擎，已集成到 rule_engine.py 中，作为多引擎融合架构的 AST 引擎组件，参与生产扫描流程）"，与 `architecture.md`（第 421、505 行）、`project-structure.md`（第 32 行）描述一致；`scripts/builtin_engine_v2.py` 文件实际存在，`scripts/rule_engine.py` 第 28 行主动 `from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
- [x] **scan.py 命令示例已完全移除 `--output` 参数** — `README.md`（第 77、80 行）、`getting-started.md`（第 107、115-119、125 行）、`architecture.md`（第 149、231 行）的 `scan.py` 命令示例均不再使用 `--output`，与工作空间机制的实际行为一致。
- [x] **architecture.md 验证案例已移除 `--output`** — 第 149 行命令为 `python3 scripts/scan.py --repo test-validation/ --full-scan`，不含 `--output` 参数。
- [x] **auto_improver.py 在 Mermaid 流程图中已标注为"待实现"** — `ai-review.md` 第 193 行 `F2` 节点写为 `auto_improver.py（待实现）`，与文字描述（第 404-408 行"待完成的工作 > 阶段 3：自动改进"）一致；`harness/` 目录中实际不含该文件（仅含 `__init__.py`、`cli.py`、`decision_logger.py`、`feedback_manager.py`、`quality_monitor.py`）。
- [x] **data/ 目录描述已添加说明** — `ai-review.md` 第 318 行已标注 `data/                         # 默认回退路径（实际运行时被覆盖到工作空间）`，并对每个子文件说明实际运行时写到工作空间；`adjustments.json` 标注"（待实现，auto_improver.py 未创建前不会生成）"。
- [x] **getting-started.md 工作空间目录结构与实际一致** — 第 132-143 行展示的报告、缓存、决策日志等子目录与 `scan.py` 的 `create_workspace()` 实现一致。
- [x] **architecture.md 项目结构与实际 scripts/ 目录一致** — 第 499-511 行列出 12 个脚本文件（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py），与实际 scripts/ 目录内容完全匹配。
- [x] **README.md 顶层目录结构与实际一致** — scripts/、references/、harness/、config/、docs/、tests/、test-validation/ 等顶层目录描述与实际目录结构一致。

## 发现的问题

### 问题 1: [严重度 HIGH] scan.py 中 `--output` 死参数仍未完全移除

- 文件: `/Users/chris/dev/git/code-review-skill/scripts/scan.py`
- 描述: argparse 中仍定义 `--output` 参数（默认值 `"report"`），但 `args.output` 在 `run_scan()` 中从未被读取（grep `args.output` 返回 0 结果）。实际输出目录由工作空间机制 `workspace["report_dir"]` 决定，输出到 `<被扫描项目>/.code-review/workspace/<scan_id>/report/`。文件第 4 行模块 docstring 已不再使用 `--output`，第 562 行 epilog 也已不再展示 `--output`，但 argparse 的参数定义仍存在，用户传入 `--output` 后不会报错但也不会生效，形成静默忽略的死参数。验证任务要求"scan.py 是否已完全移除 `--output` 参数"，从严格意义上答案仍为否：文档示例已移除，但 argparse 参数定义未移除。
- 建议修复: 三选一：
  - (a)（推荐）从 `scripts/scan.py` 删除 `parser.add_argument("--output", ...)` 定义，彻底清理死参数
  - (b) 在 `run_scan()` 中添加对 `args.output` 的废弃警告（`logger.warning("--output 参数已废弃，报告输出到工作空间目录")`）
  - (c) 恢复 `--output` 实际功能，允许用户覆盖默认输出目录

### 问题 2: [严重度 MEDIUM] advanced.md CI/CD 示例 artifact 路径未更新

- 文件: `/Users/chris/dev/git/code-review-skill/docs/advanced.md`
- 描述: 第 21-44 行 GitHub Actions 示例中，`scan.py` 命令本身已不再使用 `--output`（第 36 行：`python scripts/scan.py --repo . --base master --target HEAD`），但配套的 `actions/upload-artifact` 步骤（第 38-43 行）仍按已废弃的路径配置：
  ```yaml
  - uses: actions/upload-artifact@v4
    with:
      name: review-report
      path: |
        report/
        test-report.json
  ```
  实际报告输出到 `<被扫描项目>/.code-review/workspace/<scan_id>/report/`，在 GitHub Actions 上下文中，`scan.py --repo .` 表示被扫描项目就是当前仓库，仓库根目录下不存在 `report/` 目录，artifact 上传步骤会找不到 `report/` 文件。`test-report.json` 由于 `scripts/test_rules.py --output` 实际写入 `test-report.json`（test_rules.py 第 216、258-261 行支持 `--output`），该路径有效；但 `report/` 路径仍属错误。CI/CD 集成按本文档操作将导致 artifact 上传失败（仅上传 `test-report.json`）。
- 建议修复: 将 artifact 上传路径改为实际工作空间路径：
  ```yaml
  - uses: actions/upload-artifact@v4
    with:
      name: review-report
      path: |
        .code-review/workspace/*/report/
        test-report.json
  ```
  或在文档中说明：由于实际路径依赖 scan_id 通配符，建议使用 `actions/upload-artifact@v4` 的 `path:` 通配符。

### 问题 3: [严重度 LOW] ai-review.md 测试文件明细仍不完整

- 文件: `/Users/chris/dev/git/code-review-skill/docs/ai-review.md`
- 描述: 第 385-393 行"测试覆盖"章节显式列出 7 个测试文件的测试数量（test_diff_analyzer.py、test_call_graph.py、test_report_generator.py、test_rule_compiler.py、test_scan.py、test_ai_reviewer.py、test_profile_completeness.py），其余测试文件被一句话概括为"其他测试文件（test_ai_reviewer_e2e.py、test_harness.py 等）: 248 个测试"。但实际 `tests/` 目录共有 15 个测试文件，被略去未单独列出的还有：
  - `test_markdown_parser.py`
  - `test_notifier.py`
  - `test_rule_engine.py`
  - `test_scheduler.py`
  - `test_scheduler_e2e.py`
  - `test_semgrep_integration.py`
  
  这 6 个文件未被单独点名，也未单独给出测试数量，新开发者无法了解每个测试文件的覆盖范围。验证任务要求"测试文件明细是否已补充完整"，从严格意义上答案仍为部分：主要文件已展开，但仍有 6 个测试文件被笼统归入"其他"。
- 建议修复: 补充剩余 6 个测试文件及其测试数量，例如：
  ```
  - test_ai_reviewer.py: 19 个测试
  - test_ai_reviewer_e2e.py: X 个测试
  - test_call_graph.py: 6 个测试
  - test_diff_analyzer.py: 8 个测试
  - test_harness.py: X 个测试
  - test_markdown_parser.py: X 个测试
  - test_notifier.py: X 个测试
  - test_profile_completeness.py: 4 个测试
  - test_report_generator.py: 6 个测试
  - test_rule_compiler.py: 9 个测试
  - test_rule_engine.py: X 个测试
  - test_scan.py: 14 个测试
  - test_scheduler.py: X 个测试
  - test_scheduler_e2e.py: X 个测试
  - test_semgrep_integration.py: X 个测试
  ```
  并更新总数，确保 `pytest tests/ --collect-only -q` 输出与文档一致。

### 问题 4: [严重度 LOW] docs/guides/SEMGREP-OFFLINE-INSTALL.md 仍使用 `--output` 参数

- 文件: `/Users/chris/dev/git/code-review-skill/docs/guides/SEMGREP-OFFLINE-INSTALL.md`
- 描述: 第 106 行仍使用 `python scripts/scan.py ... --output report/`，与已废弃的 `--output` 行为不符。`docs/WORKFLOW-UPDATE.md`（第 184、207 行）和 `docs/SUBAGENT-REVIEW-ARCHITECTURE.md`（第 93 行）作为历史文档也保留 `--output` 用法，这些属于历史归档可不修改；但 `SEMGREP-OFFLINE-INSTALL.md` 仍属使用指南类文档，建议一并清理或加废弃说明。
- 建议修复: 在 `SEMGREP-OFFLINE-INSTALL.md` 第 106 行替换为工作空间路径示例，或在示例上方加注释说明 `--output` 已废弃、实际输出到 `.code-review/workspace/<scan_id>/report/`。

## 总结

- 通过项: 8
- 问题数: HIGH=1, MEDIUM=1, LOW=2