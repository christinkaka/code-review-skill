# Agent X 文档验证报告（第 6 轮）

## 验证通过项

- [x] **ai-review.md 第 341 行测试数据描述准确** -- 第 341 行写"314 个测试（275 通过，33 失败，6 跳过）"，与第 392 行重复出现的数据一致，且与 pytest 汇总口径相符。
- [x] **ai-review.md 第 392 行测试数据描述准确** -- "总计 314 个测试（275 通过，33 失败，6 跳过）"在文中两次出现一致。
- [x] **validation.md 单元测试数据与 ai-review.md 一致** -- validation.md 第 53 行 `275 passed, 33 failed, 6 skipped in 10.17s`，与 ai-review.md 第 341/392 行的"275 通过 / 33 失败 / 6 跳过 / 共 314"完全一致。
- [x] **getting-started.md 与 architecture.md 的扫描命令示例不依赖 --output** -- getting-started.md 第 107、115-119、125 行命令与 architecture.md 第 149 行 `python3 scripts/scan.py --repo test-validation/ --full-scan` 均未使用 `--output` 参数，与工作空间机制的实际行为一致。
- [x] **README.md 顶层目录结构与实际 scripts/ 一致** -- README.md 第 108 行描述 `scripts/` 为扫描引擎目录，与 architecture.md 第 499-511 行详细列出的 12 个脚本（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）相匹配。
- [x] **architecture.md 对 builtin_engine_v2.py 的角色描述与现状一致** -- 第 421 行术语说明和第 505 行项目结构均将 builtin_engine_v2.py 标注为"已集成"的多引擎组件。
- [x] **getting-started.md 与 ai-review.md 字段约定一致** -- 两文档对 Harness 决策日志、feedbacks.json、stats_cache.json 等关键文件的描述一致。

## 发现的问题

### 问题 1: [严重度 HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件实际存在且已被集成（与"保留并集成"的期望状态不符）

- 文件: `docs/ai-review.md`（第 395 行附近）
- 描述: ai-review.md 在"已完成的工作 > 代码清理"部分（第 394-397 行）明确写道："删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但事实情况是：
  1. `scripts/builtin_engine_v2.py` 实际存在，文件 642 行完整代码（实测 `wc -l` 确认）。
  2. `scripts/rule_engine.py` 第 28 行主动导入它：`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
  3. `docs/architecture.md` 第 421 行术语说明和第 505 行项目结构都将其列为正式的多引擎融合组件（"基于 Tree-sitter"的补充引擎）。
  4. architecture.md 多引擎融合章节明确 Tree-sitter AST 引擎为"已集成"状态，其实现正是 builtin_engine_v2.py。

  按验证要点要求，builtin_engine_v2.py 应标注为"保留并集成"，但 ai-review.md 的描述与事实相反，会误导首次接触项目的开发者以为该文件已被清理。
- 建议修复: 修改 ai-review.md 第 395 行，将"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"改为"保留 scripts/builtin_engine_v2.py 并集成到多引擎融合架构中（作为 Tree-sitter AST 引擎组件，被 rule_engine.py 导入使用）"。同时核查"代码清理"章节中其他条目（如 dual_engine.py）是否同样存在描述与事实不符的情况。

### 问题 2: [严重度 MEDIUM] scan.py 的 --output 参数未完全移除，仍然是死参数

- 文件: `scripts/scan.py`（第 576 行）、`scripts/scan.py`（第 4 行模块 docstring）、`scripts/scan.py`（第 562 行 epilog 示例）
- 描述: 验证要点要求 `scan.py --output` 参数已完全移除，但实际代码中仍然存在三处引用：
  1. **scan.py 第 576 行** argparse 定义依然存在：`parser.add_argument("--output", default="report", help="报告输出目录")`
  2. **scan.py 第 4 行** 模块 docstring 仍写 `用法: python scripts/scan.py ... --output report/`
  3. **scan.py 第 562 行** `--help` epilog 示例中仍写 `--output report/`

  实测 `grep "args.output" scripts/scan.py` 返回 0 结果，说明该参数在 `run_scan()` 中从未被读取，实际报告输出由工作空间机制决定（第 349 行 `output_dir = workspace["report_dir"]`）。用户传入 `--output` 后会被静默忽略，不会报错但也不会有任何效果，造成使用误导。
- 建议修复: 方案 A（推荐）：删除 scan.py 第 576 行的 `--output` argparse 定义，同步清理第 4 行模块 docstring 和第 562 行 epilog 示例中的 `--output report/`。方案 B：在 `--output` 参数定义处添加 deprecation 警告并在 help 文本中说明输出已由工作空间自动管理。getting-started.md 和 architecture.md 的命令示例已正确移除 --output，但 scan.py 自身文档未同步。

### 问题 3: [严重度 MEDIUM] ai-review.md Mermaid 流程图中 auto_improver.py 未标注"待实现"，与同文件中的文字描述自相矛盾

- 文件: `docs/ai-review.md`（第 191-195 行 Mermaid 流程图 F2 节点）
- 描述: 验证要点要求 auto_improver.py 标注为待实现。文字部分（第 401-410 行"待完成的工作 > 阶段 3：自动改进（优先级：低）"）正确标注了该文件为尚未实现（修改文件清单列出 `harness/auto_improver.py`），且 `harness/` 目录中实际不存在该文件（实测 `ls harness/` 仅含 __init__.py、cli.py、decision_logger.py、feedback_manager.py、quality_monitor.py 五个文件）。

  然而 ai-review.md 第 191-195 行的 Mermaid 架构总览图"反馈层"中 F2 节点将 auto_improver.py 画为已实现组件，没有任何"待实现"标注：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```

  流程图与同文件的文字描述自相矛盾，新开发者看架构图会以为该功能已可用，与"待完成的工作"的明确标注不一致。
- 建议修复: 在 Mermaid 图的 F2 节点标题处添加"（待实现）"标注，例如：`F2["自动改进（待实现）
─────
harness/auto_improver.py
根据反馈调整阈值
输出: adjustments.json"]`。同时核查 Mermaid 图中是否存在其他类似的"已画但未实现"组件（如有应一并标注）。

### 问题 4: [严重度 LOW] ai-review.md 目录结构章节列出了"data/" 目录，但项目根目录不存在该目录

- 文件: `docs/ai-review.md`（第 306-325 行）
- 描述: ai-review.md 第 318 行描述 `data/  # 运行时数据（.gitignore）` 作为 harness 组件的运行时数据目录，并列出 `data/decisions/`、`data/feedbacks.json`、`data/adjustments.json`、`data/stats_cache.json` 四个子项。但实际：
  1. 项目根目录下不存在 `data/` 目录（该目录已被 .gitignore 排除，但代码层面的输出已被重定向）。
  2. `getting-started.md` 第 130-143 行描述实际输出路径为 `<被扫描项目>/.code-review/workspace/<scan_id>/decisions/`，与 ai-review.md 中的 `data/decisions/` 描述不同。
  3. `adjustments.json` 由于 auto_improver.py 未实现（见问题 3），永远不会生成，目录中列出该文件会误导新开发者。

  验证要点中虽未单列此项，但该问题与整体文档一致性相关，属于 ai-review.md 的内部不一致。
- 建议修复: 在 ai-review.md 目录结构章节顶部添加注释，说明这些是 harness 组件的默认配置路径，scan.py 在实际扫描时会将所有数据重定向到 `<被扫描项目>/.code-review/workspace/<scan_id>/` 目录下。对 `adjustments.json` 添加"（待实现，auto_improver.py 未创建前不会生成）"标注，或在自动改进功能实现前先从目录结构示例中移除。

## 总结

- **通过项**: 7
- **问题数**: HIGH=1, MEDIUM=2, LOW=1

**核心结论**：文档整体质量较好，validation.md 测试数据（275/33/6）与 ai-review.md 完全一致，工作空间机制描述与代码匹配。最关键的问题是 **问题 1（HIGH）**：ai-review.md 关于 `builtin_engine_v2.py` 被删除的记述与事实完全矛盾 -- 该文件不仅存在（642 行），而且被 `rule_engine.py` 主动导入并用于生产扫描流程，是"多引擎融合架构"中 Tree-sitter AST 引擎的实现载体。建议优先修复此问题，将描述统一为"保留并集成"状态。

其次建议处理 **问题 2-3（MEDIUM）**：--output 死参数在 scan.py 内置文档中仍被引用；auto_improver.py 在 Mermaid 图中缺少"待实现"标注，与文字描述矛盾。问题 4（LOW）为 ai-review.md 目录结构章节的次要不一致，可在后续整理中一并修复。
