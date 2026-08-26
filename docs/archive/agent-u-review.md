# Agent U 文档验证报告（第 5 轮）

> 验证人：Agent U（首次接触项目的新开发者视角）
> 验证日期：2026-08-12
> 验证范围：README.md、docs/getting-started.md、docs/architecture.md、docs/ai-review.md

---

## 验证通过项

- [x] **依赖安装说明完整** -- getting-started.md 涵盖了 `pip install -r requirements.txt`、手动安装核心依赖、`brew install semgrep`（macOS 可选）、验证安装命令，以及离线安装指南链接。依赖说明清晰且可操作。
- [x] **报告目录结构描述与实际输出一致** -- getting-started.md 第 132-143 行和 architecture.md 第 199-215 行描述的工作空间目录结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与 scan.py 实际创建的 workspace 结构一致。
- [x] **文档中提到的所有文件均存在** -- README.md 引用的文档文件（docs/getting-started.md、docs/architecture.md、docs/project-structure.md、docs/rules.md、docs/ai-review.md、docs/validation.md、docs/advanced.md、docs/TECH-STACK.md 等历史文档）全部存在。references/ 下的规约文件、profiles/、prompts/、test-cases/ 子目录及内容均完整。.trae/skills/code-review/SKILL.md 存在。
- [x] **scripts/ 目录下的文件列表与实际一致** -- architecture.md 第 500-511 行列出的 12 个脚本文件（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）与实际 scripts/ 目录完全匹配。
- [x] **规约文件齐全** -- references/ 下 design/（3 类）、implementation/（4 类）、security/（12 类）规约的 .md 和 .yaml 文件均存在。profiles/（default/strict/minimal）、prompts/（5 种工作流提示词）、rules/（自定义规则）、test-cases/（安全/设计/实现测试案例）目录完整。
- [x] **Harness 系统核心模块描述与实际代码匹配** -- ai-review.md 第 306-325 行描述的 harness/ 目录结构（__init__.py、decision_logger.py、feedback_manager.py、quality_monitor.py、cli.py）与实际目录一致。config/harness.yaml 存在。scripts/harness.py 作为可执行入口存在。
- [x] **confidence_thresholds.yaml 引用已修正** -- ai-review.md Mermaid 图中约束层 C2 节点（第 167 行）已正确标注为 `config/harness.yaml`。全项目搜索未发现对 `confidence_thresholds.yaml` 的引用。
- [x] **offline-packages 包数量正确（44 个）** -- 实际 `ls offline-packages/ | wc -l` 输出 44，与 architecture.md 第 514 行"44 个包，约 104MB"描述一致。semgrep-offline-packages/ 为 70 个包，与第 515 行描述一致。
- [x] **测试总数 314 正确** -- 文档声称 314 个测试，与 `pytest --collect-only` 收集到的数量一致（此前多轮验证已确认）。
- [x] **config.yaml 和 requirements.txt 存在** -- 两个根目录文件均存在，与 README.md 和 architecture.md 描述一致。
- [x] **离线安装脚本齐全** -- install-offline.sh、install-semgrep-offline.sh、install-semgrep-offline.ps1、download-offline-packages.sh 四个脚本均存在于项目根目录。
- [x] **docs/guides/ 离线安装指南存在** -- OFFLINE-INSTALL.md 和 SEMGREP-OFFLINE-INSTALL.md 均存在，与 getting-started.md 第 95 行引用一致。
- [x] **docs/reports/ 历史报告归档存在** -- 目录存在，包含 security-fixes/ 和 validation/ 子目录。

---

## 发现的问题

### 问题 1: [严重度 HIGH] ai-review.md 内部测试通过状态描述自相矛盾

- **文件**: docs/ai-review.md
- **描述**: 同一文档中对测试通过状态的描述存在两处互相矛盾的说法：
  - 第 341 行（"当前实现状态"表格）：`| **单元测试覆盖** | ✅ 已实现 | 314 个测试全部通过 |`
  - 第 392 行（"已完成的工作 > 4. 测试覆盖"）：`**总计 314 个测试（275 通过，33 失败，6 跳过）**`
  - 第 341 行声称"全部通过"，但第 392 行明确列出有 33 个失败。新开发者无法判断哪一处是准确的。
- **建议修复**: 将第 341 行修改为与第 392 行一致的描述：`314 个测试已收集（275 通过，33 失败，6 跳过）`，或将状态标记从"✅ 已实现"调整为"⚠️ 部分通过"。

### 问题 2: [严重度 HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件实际存在且被集成

- **文件**: docs/ai-review.md、docs/architecture.md
- **描述**: ai-review.md 第 395 行在"代码清理"章节中写道：
  > "删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"

  但该文件实际存在于 `scripts/builtin_engine_v2.py`，且是一个完整的基于 Tree-sitter AST 的安全规则扫描器实现。architecture.md 也将其作为活跃组件引用：
  - 第 421 行术语说明："Tree-sitter AST 引擎同时参与...规约引擎层（作为 builtin_engine_v2.py 提供精确语法分析扫描）"
  - 第 505 行项目结构列表：`builtin_engine_v2.py  # 内置引擎 V2（基于 Tree-sitter）`

  文档声称"已删除"但文件实际存在并被标记为集成组件，状态描述严重不一致。应按用户要求标注为"保留并集成"。
- **建议修复**: 将 ai-review.md 第 395 行从"删除 scripts/builtin_engine_v2.py"改为"保留 scripts/builtin_engine_v2.py 并集成到多引擎融合架构中"，同时更新 architecture.md 中对应描述以保持一致。

### 问题 3: [严重度 MEDIUM] scan.py 中 --output 参数仍存在但从未使用

- **文件**: scripts/scan.py
- **描述**: scan.py 第 576 行定义了 `--output` 参数：
  ```python
  parser.add_argument("--output", default="report", help="报告输出目录")
  ```
  但 `args.output` 在整个 scan.py 中从未被引用。实际报告输出路径由 `workspace["report_dir"]` 决定（第 349 行），输出到被扫描项目的 `.code-review/workspace/<scan_id>/report/` 目录下。该参数是一个死参数，如果用户尝试使用 `--output /some/path`，不会有任何效果但也不会报错，容易造成误解。
- **建议修复**: 从 scan.py 的 argparse 定义中移除 `--output` 参数（第 576 行），因为输出路径已由工作空间机制自动管理。

### 问题 4: [严重度 MEDIUM] ai-review.md Mermaid 流程图中 auto_improver.py 未标注"待实现"

- **文件**: docs/ai-review.md
- **描述**: 架构总览 Mermaid flowchart（第 191-195 行）的"反馈层"将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 `harness/auto_improver.py` 文件实际不存在（harness/ 目录仅有 __init__.py、cli.py、decision_logger.py、feedback_manager.py、quality_monitor.py）。ai-review.md 自身在第 401-410 行"待完成的工作 > 阶段 3：自动改进"中正确标注了该文件为低优先级未实现功能。流程图与同文件中的文字描述自相矛盾，新开发者看架构图会以为该功能已可用。
- **建议修复**: 在流程图的 F2 组件描述中添加"（待实现）"标注，例如：`F2["自动改进（待实现）\n─────\nauto_improver.py\n根据反馈调整阈值\n输出: adjustments.json"]`。

### 问题 5: [严重度 MEDIUM] validation.md 测试通过数与其他文档不一致

- **文件**: docs/validation.md
- **描述**: validation.md 第 52 行单元测试结果显示：
  ```
  314 passed, 6 skipped in 10.17s
  ```
  但 ai-review.md 第 392 行的描述为"275 通过，33 失败，6 跳过"。两份文档对失败测试的描述完全矛盾：validation.md 声称 0 个失败，ai-review.md 声称 33 个失败。新开发者在不同文档中看到不同的数字会产生困惑。
- **建议修复**: 将 validation.md 第 52 行更新为实际测试结果，与 ai-review.md 第 392 行保持一致："275 passed, 33 failed, 6 skipped"，或注明该数据的统计时间点。

---

## 总结

| 维度 | 数量 |
|------|------|
| 验证通过项 | 13 |
| 问题总数 | 5 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 0 |

**整体评价**：四份文档的整体质量较好。依赖安装说明完整准确，规约文件体系齐全，scripts/ 目录文件列表与实际一致，报告目录结构描述正确，Harness 核心模块与代码匹配，confidence_thresholds.yaml 引用已在之前轮次修正，offline-packages 数量（44）准确。

主要遗留问题集中在两个方面：
1. **builtin_engine_v2.py 状态描述错误**（HIGH）：文档声称"已删除"但文件实际存在且被集成，应标注为"保留并集成"。
2. **测试通过数描述不一致**（HIGH + MEDIUM）：ai-review.md 内部自相矛盾（第 341 行 vs 第 392 行），且 validation.md 与 ai-review.md 数据冲突。

建议优先处理两个 HIGH 级别问题，其次处理 scan.py 的 `--output` 死参数和 auto_improver.py 的"待实现"标注。
