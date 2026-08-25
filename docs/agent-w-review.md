# Agent W 文档验证报告（第 6 轮）

## 验证通过项

- [x] **ai-review.md 测试数据描述内部一致** — ai-review.md 第 341 行（"当前实现状态"表格）和第 392 行（"测试覆盖"明细）均描述为"314 个测试（275 通过，33 失败，6 跳过）"，两处数据完全一致。
- [x] **validation.md 测试数据与 ai-review.md 一致** — validation.md 第 52 行 `275 passed, 33 failed, 6 skipped in 10.17s` 与 ai-review.md 第 392 行"275 通过，33 失败，6 跳过"完全对应（仅表述形式不同：英文 pytest 输出 vs 中文描述），数值一致。
- [x] **auto_improver.py 在文字部分正确标注为待实现** — ai-review.md 第 401-410 行"待完成的工作 > 阶段 3：自动改进（优先级：低）"明确将 `harness/auto_improver.py` 标注为待实现项，实际 `harness/` 目录中确实不存在该文件（仅含 `__init__.py`、`cli.py`、`decision_logger.py`、`feedback_manager.py`、`quality_monitor.py`）。
- [x] **README.md、getting-started.md、architecture.md 中 scan.py 命令示例正确** — README.md（第 77、80 行）、getting-started.md（第 107、115-119、125 行）、architecture.md（第 149、231 行）的 scan.py 命令示例均未使用已废弃的 `--output` 参数，与实际工作空间机制一致。
- [x] **architecture.md 中 builtin_engine_v2.py 状态描述正确** — architecture.md 第 421 行术语说明将 builtin_engine_v2.py 描述为"Tree-sitter AST 引擎…作为 builtin_engine_v2.py 提供精确语法分析扫描"，第 505 行项目结构中标注为"内置引擎 V2（基于 Tree-sitter）"，且 rule_engine.py 第 28 行确实 `from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`，状态描述与代码一致。

## 发现的问题

### 问题 1: [严重度 HIGH]
- 文件: `docs/ai-review.md`（第 395 行）
- 描述: "已完成的工作 > 5. 代码清理"章节明确写道："删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但实际情况是：
  1. 文件 `scripts/builtin_engine_v2.py` 实际存在于 `scripts/` 目录中（文件头注释为"内置引擎 V2 - 基于 Tree-sitter AST 的安全规则扫描器"，约 580+ 行代码）。
  2. `scripts/rule_engine.py` 第 28 行主动导入该模块：`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
  3. `docs/architecture.md` 第 421 行术语说明和第 505 行项目结构均将 `builtin_engine_v2.py` 列为正式组件，并描述为"已集成"的 Tree-sitter AST 引擎。
  文档声称"已删除、从未集成"与代码现状及 architecture.md 描述完全矛盾，会严重误导新开发者。
- 建议修复: 将第 395 行从"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"修改为"保留 scripts/builtin_engine_v2.py（已集成到 rule_engine.py 中，作为 Tree-sitter AST 引擎组件参与多引擎融合扫描）"，与 architecture.md 第 421、505 行保持一致。

### 问题 2: [严重度 MEDIUM]
- 文件: `docs/ai-review.md`（第 191-195 行，架构总览 Mermaid flowchart 中"反馈层"的 F2 节点）
- 描述: 架构总览 Mermaid 图中"反馈层"将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 `harness/auto_improver.py` 文件实际不存在（经 LS harness/ 目录确认仅有 __init__.py、cli.py、decision_logger.py、feedback_manager.py、quality_monitor.py）。ai-review.md 自身在第 401-410 行"待完成的工作 > 阶段 3：自动改进（优先级：低）"中也正确标注了该文件为尚未实现。流程图与同文件中的文字描述自相矛盾，新开发者看架构图会误以为该功能已可用。
- 建议修复: 在流程图的 F2 组件描述中添加"（待实现）"标注，例如：`F2["自动改进（待实现）\n─────\nauto_improver.py\n根据反馈调整阈值\n输出: adjustments.json"]`，与第 401-410 行的"待完成的工作"描述保持一致。

### 问题 3: [严重度 MEDIUM]
- 文件: `scripts/scan.py`（第 576 行 argparse 定义，第 4 行模块 docstring，第 562 行 --help epilog）
- 描述: scan.py 在 argparse 中定义了 `--output` 参数（`parser.add_argument("--output", default="report", help="报告输出目录")`），但 `args.output` 在整个 scan.py 中从未被读取（仅 grep 到 `output_dir = workspace["report_dir"]` 和局部变量名 `output_dir`，没有 `args.output`）。实际输出目录由 `create_workspace()` 函数自动决定，输出到被扫描项目的 `.code-review/workspace/<scan_id>/report/`。然而 scan.py 自身的文档仍在使用该参数：
  1. 第 4 行模块 docstring：`用法: ... --output report/`
  2. 第 562 行 --help epilog：`python scripts/scan.py --repo ./my-project --base master --target HEAD --profile strict --output report/`
  3. 第 576 行 argparse 定义本身仍然存在
  用户按内置文档使用 `--output` 后不会收到任何错误，但输出位置与预期完全不同。
- 建议修复: 三选一：(a) 从第 576 行删除 `parser.add_argument("--output", ...)` 定义，从第 4 行 docstring 和第 562 行 epilog 中移除 `--output report/`，彻底清理死参数（推荐）；(b) 在 run_scan() 中添加对 `args.output` 的废弃警告（`logger.warning("--output 参数已废弃，报告输出到工作空间目录")`）；(c) 恢复 `--output` 实际功能，允许用户覆盖默认输出目录。

### 问题 4: [严重度 MEDIUM]
- 文件: `docs/advanced.md`（第 36-43 行，CI/CD 集成示例）
- 描述: CI/CD 集成示例中，`actions/upload-artifact` 步骤的 `path:` 配置为 `report/` 和 `test-report.json`，但 scan.py 实际将报告输出到 `.code-review/workspace/<scan_id>/report/`，artifact 上传步骤会找不到文件。虽然示例中 scan.py 命令本身已不再使用 `--output`（第 36 行），但配套的 artifact 路径仍按已废弃的 `report/` 路径配置，存在不自洽。
- 建议修复: 将 artifact 上传路径修改为工作空间路径模式，例如 `path: .code-review/workspace/*/report/`，或显式引用具体路径，与 scan.py 实际输出位置保持一致。

### 问题 5: [严重度 LOW]
- 文件: `docs/ai-review.md`（第 385-392 行，"已完成的工作 > 4. 测试覆盖"明细列表）
- 描述: 测试文件明细列表只列出 7 个测试文件、66 个测试（8+6+6+9+14+19+4=66），但第 392 行声称"总计 314 个测试"。差异达 248 个测试，明细严重不完整。tests/ 目录中实际包含更多测试文件（test_ai_reviewer_e2e.py、test_harness.py、test_markdown_parser.py、test_notifier.py、test_rule_engine.py、test_scheduler.py、test_scheduler_e2e.py、test_semgrep_integration.py 等），但文档中没有任何说明。总数 314 本身正确（与 pytest collect 一致），但明细列表严重不完整，给人留下数据不可靠的印象。
- 建议修复: 补全测试文件明细列表，或将描述改为"以上为主要测试文件的统计，完整 314 个测试分布在 15 个测试文件中，可通过 `pytest tests/ --collect-only -q` 查看完整列表"。

## 总结

- 通过项: 5
- 问题数: HIGH=1, MEDIUM=3, LOW=1