# Agent S 文档验证报告（第 4 轮）

> 验证时间：2026-08-12
> 验证范围：README.md、docs/getting-started.md、docs/architecture.md、docs/ai-review.md
> 验证方式：独立阅读文档 + 交叉比对实际代码/目录结构/测试运行结果

---

## 验证通过项

- [x] **依赖安装说明完整** -- `requirements.txt` 列出了全部 7 个核心依赖（pyyaml、gitpython、rich、tree-sitter、tree-sitter-java、tree-sitter-python、tree-sitter-javascript、jinja2、pandas），`getting-started.md` 的手动安装命令与 `requirements.txt` 一致。
- [x] **getting-started.md 中的 scan.py 命令示例未使用 --output 参数** -- 三个扫描示例（全库扫描、分支差异扫描、指定 Profile）均不包含 `--output` 参数，与实际工作空间输出机制一致。
- [x] **报告目录结构描述与实际输出一致** -- `getting-started.md` 和 `architecture.md` 描述的工作空间结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与 `scan.py` 中 `create_workspace()` 函数的实际创建逻辑匹配。
- [x] **文档中提到的核心文件均存在** -- `.trae/skills/code-review/SKILL.md`、`references/subagent-contract.md`、`references/main-agent-contract.md`、`references/RULE-GENERATOR-GUIDE.md`、`config/harness.yaml`、`config.yaml`、`requirements.txt`、各安装脚本等全部存在。
- [x] **scripts/ 目录文件列表与 architecture.md 一致** -- architecture.md 第 499-511 行和 project-structure.md 列出的 12 个脚本文件（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）与实际 scripts/ 目录完全匹配。
- [x] **规约文件全部存在** -- references/ 下 design/（3 类）、implementation/（4 类）、security/（12 类）规约的 .md 和 .yaml 文件均存在，profiles/（default/strict/minimal）、prompts/（5 个工作流提示词 + README）、test-cases/、rules/ 目录结构完整。
- [x] **Harness 系统核心模块与描述匹配** -- `harness/` 目录包含 `__init__.py`、`decision_logger.py`、`feedback_manager.py`、`quality_monitor.py`、`cli.py`，与 ai-review.md 描述一致。`scripts/harness.py` 可执行脚本存在。`scan.py` 中 `load_harness_config()`、`init_harness_components()`、`build_feedback_examples()` 函数均已实现。
- [x] **confidence_thresholds.yaml 引用已修正** -- 在当前四份文档（README.md、getting-started.md、architecture.md、ai-review.md）中均未发现对 `confidence_thresholds.yaml` 的引用。ai-review.md Mermaid 图中约束层 C2 已正确标注为 `config/harness.yaml`。全项目代码搜索也未发现对该文件名的引用。
- [x] **auto_improver.py 标注为待实现** -- ai-review.md 第 401-410 行"待完成的工作 > 阶段 3：自动改进"明确列出 `harness/auto_improver.py` 为待实现项。实际 `harness/` 目录中确实不存在该文件。架构图中的 `auto_improver.py` 属于设计蓝图，文档标注清晰。
- [x] **offline-packages 包数量正确（44 个）** -- 实际 `ls offline-packages/ | wc -l` 结果为 44，architecture.md 第 514 行描述"44 个包"准确。semgrep-offline-packages 为 70 个包，与文档第 515 行描述一致。
- [x] **测试收集数量为 314** -- `pytest tests/ --collect-only -q` 输出 "314 tests collected"，与 ai-review.md 第 392 行"总计 314 个测试全部通过"中的数量一致（但"全部通过"存疑，见问题 3）。
- [x] **dual_engine.py 已删除** -- scripts/ 目录中不存在 `dual_engine.py`，与 ai-review.md 清理记录一致。
- [x] **diff_analyzer.py.bak 已删除** -- scripts/ 目录中不存在 `.bak` 备份文件。

---

## 发现的问题

### 问题 1: [严重度 HIGH] scan.py 的 `--output` 参数未完全移除

- **文件**: `scripts/scan.py`
- **描述**: `--output` 参数在 `scan.py` 中仍然存在三处引用：
  1. **第 4 行（文件头注释）**：`用法: python scripts/scan.py --repo <repo-path> --base master --target release/1.0 --profile default --output report/`
  2. **第 562 行（epilog 示例）**：`python scripts/scan.py --repo ./my-project --base master --target HEAD --profile strict --output report/`
  3. **第 576 行（argparse 定义）**：`parser.add_argument("--output", default="report", help="报告输出目录")`

  然而，`run_scan()` 函数中**从未使用** `args.output`。实际输出目录由工作空间机制决定（第 349 行：`output_dir = workspace["report_dir"]`）。这意味着用户传入 `--output` 参数会被静默忽略，不会有任何效果。

- **建议修复**:
  1. 删除第 576 行的 `parser.add_argument("--output", ...)` 定义
  2. 删除第 4 行和第 562 行文档注释中的 `--output report/` 示例
  3. 或者，如果希望保留向后兼容，可在 `run_scan()` 中添加对 `args.output` 的警告（`logger.warning("--output 参数已废弃，报告输出到工作空间目录")`）

### 问题 2: [严重度 HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件实际存在且已被集成

- **文件**: `docs/ai-review.md` 第 395 行
- **描述**: "已完成的工作 > 代码清理"章节明确写道：
  > "删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"

  但实际情况是：
  1. 文件 `scripts/builtin_engine_v2.py` 仍然存在，包含 642 行完整代码。
  2. `scripts/rule_engine.py` 第 28 行**主动导入**它：`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
  3. `rule_engine.py` 第 308-313 行在扫描流程中**实例化并使用**它：`ast_engine = BuiltinEngineV2()` -> `ast_engine.scan_repo(repo_path)`。
  4. `architecture.md` 第 421 行术语说明和第 505 行项目结构均将 `builtin_engine_v2.py` 列为正式组件，标注为"已集成"。

  文档中"删除"和"从未集成"的描述与代码事实完全矛盾，会严重误导新开发者。

- **建议修复**: 将 ai-review.md 第 395 行从：
  > "删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"

  改为：
  > "保留 scripts/builtin_engine_v2.py（已集成到 rule_engine.py 中，作为 Tree-sitter AST 引擎组件参与多引擎融合扫描）"

  同时补充说明其当前状态为"已集成"，与 architecture.md 的描述保持一致。

### 问题 3: [严重度 HIGH] ai-review.md 声称"314 个测试全部通过"，但实际有 33 个测试失败

- **文件**: `docs/ai-review.md` 第 341 行
- **描述**: 文档写道"单元测试覆盖 -- 314 个测试全部通过"。但实际执行 `python -m pytest tests/ -q` 的结果为：

  ```
  33 failed, 275 passed, 6 skipped in 11.35s
  ```

  失败测试分布在 4 个文件中：
  - **test_ai_reviewer_e2e.py**（28 个失败）：测试 mock 了 `_call_llm` 方法，但当前 `AIReviewer` 类不存在该方法。此外 `_is_available`、`review` 等属性也不存在。
  - **test_ai_reviewer.py**（3 个失败）：测试断言旧字段名 `is_valid`、`temperature`、`综合评审工作流` 出现在生成的任务描述中，但代码已统一为 `is_false_positive` 等新字段。
  - **test_rule_engine.py**（1 个失败）：`test_parse_semgrep_output` 断言相对路径，但实际返回绝对路径。
  - **test_scan.py**（1 个失败）：`test_run_scan_without_harness` 触发 `KeyError: 'decision_logging'`，说明 harness 配置结构变更后测试未同步更新。

  文档声称"全部通过"会误导开发者对代码质量的判断。

- **建议修复**:
  1. 将 ai-review.md 第 341 行更新为实际状态，例如："314 个测试已收集，275 个通过，33 个失败，6 个跳过"。
  2. 修复 33 个失败测试以匹配当前代码实现（特别是 `test_ai_reviewer_e2e.py` 中对已不存在的 `_call_llm` 方法的 mock，以及 `test_ai_reviewer.py` 中对旧字段名的断言）。

### 问题 4: [严重度 MEDIUM] ai-review.md "目录结构"章节的 data/ 描述与实际工作空间机制不一致

- **文件**: `docs/ai-review.md` 第 304-325 行
- **描述**: "目录结构"章节展示 `data/` 为项目根目录下的运行时数据目录：
  ```
  code-review-skill/
  ├── data/                         # 运行时数据（.gitignore）
  │   ├── decisions/                # 决策日志（按扫描批次）
  │   ├── feedbacks.json            # 用户反馈
  │   ├── adjustments.json          # 调整记录
  │   └── stats_cache.json          # 统计缓存
  ```

  但实际代码中（`scan.py` 第 430-432 行），harness 组件的存储路径已被重定向到**被扫描项目的工作空间目录**：
  ```python
  harness_config["harness"]["decision_logging"]["storage_dir"] = str(decisions_dir)
  harness_config["harness"]["feedback"]["storage_file"] = str(workspace["workspace_dir"] / "feedbacks.json")
  harness_config["harness"]["quality_monitor"]["cache_file"] = str(workspace["workspace_dir"] / "stats_cache.json")
  ```

  此外，第 372 行也写道"scan.py 记录每个问题的决策日志到 data/decisions/"，但实际写入的是工作空间的 `decisions/` 目录。

  这与 architecture.md 中"工作空间机制"章节的描述矛盾，也会让新开发者误以为数据存储在工具项目根目录下。

- **建议修复**: 将 ai-review.md "目录结构"章节中的 `data/` 部分标注为"默认配置路径（实际运行时由 scan.py 重定向到被扫描项目的工作空间目录）"，或直接更新为工作空间目录结构。将第 372 行"到 data/decisions/"改为"到工作空间的 decisions/ 目录"。

---

## 总结

| 维度 | 结果 |
|------|------|
| **通过项** | 13 |
| **问题数** | HIGH=3, MEDIUM=1, LOW=0 |
| **总计** | 17 个验证点 |

**整体评价**：四份文档的整体质量较好。依赖安装说明完整、规约文件体系齐全、scripts/ 文件列表与实际一致、offline-packages 数量（44）准确、confidence_thresholds.yaml 引用已修正、auto_improver.py 待实现标注正确、Harness 核心模块与代码匹配。

**最关键的 3 个 HIGH 问题**：
1. **scan.py 的 `--output` 参数**：argparse 定义仍在但从未使用，用户传入会被静默忽略（应彻底移除或添加废弃警告）。
2. **builtin_engine_v2.py 状态矛盾**：ai-review.md 声称"已删除、从未集成"，但该文件实际存在且被 rule_engine.py 主动导入并用于生产扫描，是"多引擎融合架构"中 Tree-sitter AST 引擎的实现载体。
3. **测试通过率不实**：文档声称"314 个测试全部通过"，但实际运行有 33 个失败（275 passed / 33 failed / 6 skipped），主要因为测试代码未跟上 ai_reviewer.py 字段重构和 harness 配置结构变更。
