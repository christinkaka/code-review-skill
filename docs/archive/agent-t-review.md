# Agent T 文档验证报告（第 4 轮）

**验证人**: Agent T（首次接触项目的新开发者视角）
**验证日期**: 2026-08-12
**验证范围**: README.md, docs/getting-started.md, docs/architecture.md, docs/ai-review.md
**验证方式**: 独立阅读文档后，逐项与实际代码/文件结构交叉比对

---

## 验证通过项

- [x] **依赖安装说明完整** -- getting-started.md 列出的核心依赖（pyyaml, gitpython, rich, tree-sitter, tree-sitter-java, tree-sitter-python, tree-sitter-javascript, jinja2, pandas）与 requirements.txt 完全一致。验证命令 `python -c "import yaml, git, jinja2, pandas; print('all ok')"` 可正确执行。离线安装指南 guides/OFFLINE-INSTALL.md 和 guides/SEMGREP-OFFLINE-INSTALL.md 均存在。
- [x] **getting-started.md 的 scan.py 命令示例已移除 --output** -- 第 107、115-119、125 行的命令示例均不使用 `--output` 参数，与工作空间机制的实际行为一致。
- [x] **architecture.md 验证案例命令已移除 --output** -- 第 149 行命令为 `python3 scripts/scan.py --repo test-validation/ --full-scan`，不含 `--output`。
- [x] **报告目录结构描述与实际输出一致** -- getting-started.md 第 132-143 行和 architecture.md 第 200-214 行描述的工作空间目录结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与 scan.py 中 `create_workspace()` 函数的实际创建逻辑完全匹配。
- [x] **文档中提到的核心文件均存在** -- README.md 文档目录中链接的所有文件均已验证存在：getting-started.md, architecture.md, project-structure.md, rules.md, ai-review.md, validation.md, advanced.md, SKILL.md, references/subagent-contract.md, references/main-agent-contract.md, references/RULE-GENERATOR-GUIDE.md，以及历史文档（TECH-STACK.md, SUBAGENT-REVIEW-ARCHITECTURE.md 等 10 个文件）。
- [x] **scripts/ 目录下的文件列表与 architecture.md 一致** -- architecture.md 第 499-511 行列出 12 个脚本文件（scan.py, diff_analyzer.py, call_graph.py, rule_engine.py, rule_compiler.py, builtin_engine_v2.py, ai_reviewer.py, report_generator.py, harness.py, scheduler.py, notifier.py, test_rules.py），与实际 scripts/ 目录内容完全匹配。
- [x] **规约文件齐全** -- references/ 目录下 design/（3 个 .md）、implementation/（4 个 .md）、security/（12 个 .md）、rules/（1 个 .md）、profiles/（3 个 .yaml）、prompts/（5 个提示词 .md + README.md）、test-cases/（含 security/design/implementation 子目录共 14 个测试案例 + README.md）均存在且结构完整。
- [x] **Harness 系统模块描述与实际代码匹配** -- ai-review.md 描述的 harness/ 目录结构（__init__.py, decision_logger.py, feedback_manager.py, quality_monitor.py, cli.py）与实际 harness/ 目录完全一致。config/harness.yaml 存在且包含文档描述的约束、阈值、反馈等配置。scan.py 中 `load_harness_config()`、`init_harness_components()`、`build_feedback_examples()` 函数均存在且功能与文档描述一致。
- [x] **confidence_thresholds.yaml 引用已修正** -- ai-review.md Mermaid 图中约束层 C2 节点（第 167 行）已正确标注为 `config/harness.yaml`，不再引用不存在的 `confidence_thresholds.yaml`。全项目搜索未发现对 `confidence_thresholds.yaml` 的引用。
- [x] **offline-packages 包数量正确** -- 实际 offline-packages/ 目录包含 44 个 .whl 文件，architecture.md 第 514 行描述"44 个包"准确。semgrep-offline-packages/ 包含 70 个包，与第 515 行描述一致。
- [x] **测试总数 314 正确** -- `pytest tests/ --collect-only -q` 输出 "314 tests collected"，与 ai-review.md 第 341 行和第 392 行描述一致。
- [x] **dual_engine.py 已正确删除** -- ai-review.md 第 396 行声称删除了 `scripts/dual_engine.py`，经 Glob 搜索确认该文件确实不存在于项目中。

---

## 发现的问题

### 问题 1: [严重度 HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件实际存在且被活跃集成

- **文件**: docs/ai-review.md 第 395 行
- **描述**: "已完成的工作 > 代码清理"章节明确写道：
  > "删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"

  但实际情况是：
  1. 文件 `scripts/builtin_engine_v2.py` 仍然存在，包含 584+ 行完整代码。
  2. `scripts/rule_engine.py` 第 28 行主动导入它：`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
  3. architecture.md 第 505 行将其列为正式组件：`builtin_engine_v2.py  # 内置引擎 V2（基于 Tree-sitter）`。
  4. architecture.md 第 421 行术语说明中明确提到它参与规约引擎层的扫描。
  5. architecture.md 多引擎融合架构中，Tree-sitter AST 引擎被标注为"已集成"的补充引擎，其实现正是 builtin_engine_v2.py。

  文档声明与代码现状完全矛盾。新开发者读到这段记录会以为该文件已被清理，但实际上它是多引擎融合架构中的核心组件。

- **建议修复**: 将 ai-review.md 第 395 行从"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"改为"保留 scripts/builtin_engine_v2.py（已集成到 rule_engine.py 中，作为 Tree-sitter AST 引擎组件参与多引擎融合扫描）"。

### 问题 2: [严重度 MEDIUM] ai-review.md Mermaid 流程图中 auto_improver.py 未标注"待实现"

- **文件**: docs/ai-review.md 第 191-195 行
- **描述**: 架构总览 Mermaid flowchart 中"反馈层"将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 `harness/auto_improver.py` 文件不存在（经 Glob 搜索 `harness/` 目录确认仅有 __init__.py, cli.py, decision_logger.py, feedback_manager.py, quality_monitor.py）。ai-review.md 自身在第 399-410 行"待完成的工作"中也正确标注了该文件为"阶段 3：自动改进（优先级：低）"，即尚未实现。流程图与同文件中的文字描述自相矛盾。新开发者看架构图会以为该功能已可用。

- **建议修复**: 在 F2 组件描述中添加"（待实现）"标注：
  ```
  F2["自动改进（待实现）
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```

### 问题 3: [严重度 MEDIUM] scan.py 中 --output 参数为死参数，代码内置文档及 advanced.md CI/CD 示例仍在使用

- **文件**: scripts/scan.py 第 4、562、576 行；docs/advanced.md 第 42 行
- **描述**: `scan.py` 在 argparse 中定义了 `--output` 参数（第 576 行，默认值 `"report"`），但 `args.output` 在整个代码中从未被读取（grep 搜索 `args.output` 返回 0 结果）。实际输出始终写入被扫描项目下的 `.code-review/workspace/<scan_id>/report/`。然而：
  - 第 4 行模块 docstring 仍写 `用法: ... --output report/`
  - 第 562 行 `--help` epilog 示例展示 `--output report/`
  - advanced.md 第 42 行 CI/CD 示例中 artifact 上传路径配置为 `report/`，由于 `--output` 是死参数，实际报告输出在 `.code-review/workspace/<scan_id>/report/`，artifact 上传步骤会找不到报告文件

  getting-started.md 和 architecture.md 的命令示例已正确移除了 `--output`，但 scan.py 自身的内置文档和 advanced.md 仍在使用。

- **建议修复**:
  1. 从 scan.py 第 4 行 docstring 中移除 `--output report/`。
  2. 从第 562 行 epilog 示例中移除 `--output report/`。
  3. 从第 576 行删除 `--output` 参数定义，或添加 deprecation 说明并注明实际输出由工作空间管理。
  4. 将 advanced.md 第 42 行 artifact 路径从 `report/` 改为 `.code-review/` 开头的动态路径。

### 问题 4: [严重度 MEDIUM] ai-review.md 目录结构章节描述 `data/` 目录但未说明实际路径会被重定向

- **文件**: docs/ai-review.md 第 318-322 行
- **描述**: "目录结构"章节描述了项目根目录下的 `data/` 目录：
  ```
  ├── data/                         # 运行时数据（.gitignore）
  │   ├── decisions/                # 决策日志（按扫描批次）
  │   ├── feedbacks.json            # 用户反馈
  │   ├── adjustments.json          # 调整记录
  │   └── stats_cache.json          # 统计缓存
  ```
  但实际运行时，scan.py 第 430-432 行会将这些路径全部重定向到工作空间目录：
  ```python
  harness_config["harness"]["decision_logging"]["storage_dir"] = str(decisions_dir)
  harness_config["harness"]["feedback"]["storage_file"] = str(workspace["workspace_dir"] / "feedbacks.json")
  harness_config["harness"]["quality_monitor"]["cache_file"] = str(workspace["workspace_dir"] / "stats_cache.json")
  ```
  项目根目录下不存在 `data/` 目录。该章节描述的是 harness 组件的默认配置路径，而非实际运行时的输出位置。新开发者在项目根目录下找不到 `data/` 目录会感到困惑。此外，`adjustments.json` 由于 auto_improver.py 未实现，永远不会生成。

- **建议修复**: 在该目录结构上方或下方添加注释说明：这些是 harness 组件的默认配置路径（harness.yaml 中的值），实际扫描时 scan.py 会将所有数据重定向到被扫描项目的 `.code-review/workspace/<scan_id>/` 目录下。对 `adjustments.json` 添加"（待实现，auto_improver.py 未创建前不会生成）"标注。

### 问题 5: [严重度 LOW] ai-review.md 测试数量明细加总远小于 314

- **文件**: docs/ai-review.md 第 384-392 行
- **描述**: "测试覆盖"章节列出了 7 个测试文件的明细：
  - test_diff_analyzer.py: 8 个
  - test_call_graph.py: 6 个
  - test_report_generator.py: 6 个
  - test_rule_compiler.py: 9 个
  - test_scan.py: 14 个
  - test_ai_reviewer.py: 19 个
  - test_profile_completeness.py: 4 个
  - 明细加总: 66 个

  但总数声称是 314 个。tests/ 目录中实际有 15 个测试文件（含 conftest.py），未列出的文件包括：test_ai_reviewer_e2e.py、test_harness.py、test_markdown_parser.py、test_notifier.py、test_rule_engine.py、test_scheduler.py、test_scheduler_e2e.py、test_semgrep_integration.py。这些未列出的文件贡献了约 248 个测试，但文档中没有任何说明。

  总数 314 本身是正确的（与 pytest 输出一致），但明细列表严重不完整，给人留下数据不可靠的印象。

- **建议修复**: 补全测试文件明细列表，或将描述改为"以上为主要测试文件的统计，完整 314 个测试分布在 15 个测试文件中，可通过 `pytest tests/ --collect-only -q` 查看完整列表"。

---

## 总结

| 维度 | 结果 |
|------|------|
| **通过项** | 12 |
| **问题数** | HIGH=1, MEDIUM=3, LOW=1 |

**整体评价**: 文档整体质量较高。依赖安装说明完整准确，规约文件体系齐全，scripts/ 目录文件列表与实际一致，报告目录结构描述正确，Harness 系统模块描述与代码匹配，confidence_thresholds.yaml 引用已修正，offline-packages 数量（44）和测试数量（314）均准确。

最关键的问题是 **问题 1（HIGH）**：ai-review.md 关于 `builtin_engine_v2.py` 被删除的记述与事实完全矛盾 -- 该文件不仅存在，而且是多引擎融合架构中 Tree-sitter AST 引擎的实现载体，被 rule_engine.py 主动导入并用于生产扫描流程。建议优先修复此问题，将描述统一为"已集成"状态。

其次建议处理 **问题 2-3（MEDIUM）**：auto_improver.py 在 Mermaid 图中缺少"待实现"标注，与文字描述矛盾；`--output` 死参数在 scan.py 内置文档和 advanced.md CI/CD 示例中仍被引用，可能导致 CI/CD 集成时 artifact 路径错误。
