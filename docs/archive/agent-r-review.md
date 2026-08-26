# Agent R 文档验证报告（第 3 轮）

> 验证人：Agent R（首次接触 code-review-skill 项目的新开发者视角）
> 验证日期：2026-08-12
> 验证范围：README.md、getting-started.md、architecture.md、ai-review.md

---

## 验证通过项

- [x] **依赖安装说明完整** -- getting-started.md 列出了所有核心依赖（pyyaml、tree-sitter 系列、gitpython、rich、jinja2、pandas），并说明了每个依赖的用途。requirements.txt 存在且可用于一键安装。
- [x] **报告目录结构描述与实际输出一致** -- getting-started.md 和 architecture.md 描述的工作空间结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与代码中 `create_workspace()` 函数的实际输出一致。
- [x] **scripts/ 目录下的文件列表与文档一致** -- architecture.md 第 499-511 行和 project-structure.md 第 27-39 行列出的 12 个脚本文件（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）与实际 scripts/ 目录完全匹配。
- [x] **规约文件全部存在** -- references/security/ 包含 12 个安全规约（.md + .yaml），references/design/ 包含 3 个设计规约，references/implementation/ 包含 4 个实现规约，references/rules/ 包含自定义规则，references/profiles/ 包含 3 个 Profile（default/strict/minimal），references/prompts/ 包含 5 个工作流提示词 + README。均与文档描述一致。
- [x] **Harness 系统核心模块描述与代码匹配** -- harness/ 目录包含 __init__.py、decision_logger.py、feedback_manager.py、quality_monitor.py、cli.py，与 ai-review.md 第 310-315 行描述完全一致。config/harness.yaml 存在且包含文档中描述的约束、反馈、自动改进、质量监控配置。
- [x] **confidence_thresholds.yaml 引用已修正** -- ai-review.md 架构总览 Mermaid 图中约束层 C2 已正确标注为 `config/harness.yaml`（第 167 行），不再引用不存在的独立配置文件 confidence_thresholds.yaml。
- [x] **offline-packages 包数量正确** -- 实际 offline-packages/ 目录包含 44 个 .whl 文件，与 architecture.md 第 514 行"44 个包，约 104MB"的描述一致。semgrep-offline-packages/ 包含 70 个包，与第 515 行描述一致。
- [x] **文档中提到的核心文件均存在** -- .trae/skills/code-review/SKILL.md、references/main-agent-contract.md、references/subagent-contract.md、references/RULE-GENERATOR-GUIDE.md、docs/guides/OFFLINE-INSTALL.md、docs/guides/SEMGREP-OFFLINE-INSTALL.md、config.yaml、requirements.txt、install-offline.sh、install-semgrep-offline.sh、install-semgrep-offline.ps1、download-offline-packages.sh 均存在。
- [x] **getting-started.md 的 scan.py 命令示例已移除 --output** -- 第 107、115-119、125 行的命令示例均不再使用 `--output` 参数，与工作空间机制的实际行为一致。
- [x] **architecture.md 验证案例已移除 --output** -- 第 149 行的验证案例命令 `python3 scripts/scan.py --repo test-validation/ --full-scan` 不再使用 --output 参数。

---

## 发现的问题

### 问题 1: [严重度 HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件实际存在且被活跃集成

- **文件**: `docs/ai-review.md` 第 395 行
- **描述**: "已完成的工作 > 代码清理"章节明确写道："删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但实际情况是：
  1. 文件 `scripts/builtin_engine_v2.py` 仍然存在，包含 584+ 行完整代码。
  2. `scripts/rule_engine.py` 第 28 行主动导入它：`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
  3. `docs/architecture.md` 第 505 行和 `docs/project-structure.md` 第 32 行均将其列为正式组件（"内置引擎 V2（基于 Tree-sitter）"/ "内置规则引擎（AST + 正则）"）。
  4. architecture.md 的多引擎融合架构描述中，Tree-sitter AST 引擎被标注为"已集成"的补充引擎，其实现正是 builtin_engine_v2.py。
  
  这是文档中最严重的矛盾。新开发者阅读 ai-review.md 会以为该文件已被清理且从未集成，但其他文档和代码都表明它是生产环境的活跃组件。这会导致开发者对该模块的认知完全混乱。
- **建议修复**: 删除 ai-review.md 第 395 行关于"删除 scripts/builtin_engine_v2.py"的描述。改为："builtin_engine_v2.py 已集成到 rule_engine.py 中，作为 Tree-sitter AST 引擎组件，参与多引擎融合扫描"。同时更新 ai-review.md 中 builtin_engine_v2.py 的状态描述为"已集成"。

### 问题 2: [严重度 MEDIUM] --output 参数是死参数但多处文档仍在引用

- **文件**: `scripts/scan.py` 第 4、562、576 行；`docs/advanced.md` 第 36 行；`docs/validation.md` 第 61、64 行
- **描述**: `scan.py` 在 argparse 中定义了 `--output` 参数（第 576 行，默认值 `"report"`），但 `args.output` 在整个代码中从未被读取（grep 搜索 `args.output` 返回 0 结果）。实际输出始终写入被扫描项目下的 `.code-review/workspace/<scan_id>/report/`。然而：
  - scan.py 的模块 docstring（第 4 行）仍写 `--output report/`
  - scan.py 的 --help epilog（第 562 行）展示 `--output report/`
  - advanced.md 第 36 行 CI/CD 示例使用 `--output report/`，且 artifact 上传路径也配置为 `report/`
  - validation.md 第 61、64 行稳定性验证示例使用 `--output report-round1/` 和 `--output report-round2/`
  
  用户按这些文档使用 `--output` 后不会收到任何错误，但输出位置与预期完全不同。特别是 advanced.md 的 CI/CD 示例会导致 artifact 上传步骤找不到报告文件。
- **建议修复**: 
  - 方案 A（推荐）：从 scan.py argparse 中删除 `--output` 参数定义，更新 docstring 和 epilog 示例，将 advanced.md 和 validation.md 中的命令示例改为使用工作空间路径。
  - 方案 B：恢复 `--output` 的实际功能，允许用户覆盖默认输出目录。

### 问题 3: [严重度 MEDIUM] ai-review.md Mermaid 流程图中 auto_improver.py 未标注"待实现"

- **文件**: `docs/ai-review.md` 第 191-195 行
- **描述**: 架构总览 Mermaid flowchart 中"反馈层"将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 `harness/auto_improver.py` 文件不存在。ai-review.md 自身在第 399-410 行"待完成的工作"中正确标注了该文件为"阶段 3：自动改进（优先级：低）"，即尚未实现。流程图与同文件中的文字描述自相矛盾。新开发者看架构图会以为该功能已可用。
- **建议修复**: 在流程图的 F2 组件描述中添加"（待实现）"标注，例如：`F2["自动改进（待实现）\n─────\nauto_improver.py\n根据反馈调整阈值\n输出: adjustments.json"]`。

### 问题 4: [严重度 MEDIUM] ai-review.md 与 validation.md 的测试数量不一致

- **文件**: `docs/ai-review.md` 第 392 行；`docs/validation.md` 第 52 行
- **描述**: ai-review.md 声称"总计 314 个测试全部通过"，但 validation.md 声称"267 passed, 6 skipped in 10.17s"。两个文档对测试数量的描述不一致，且都没有注明统计时间。新开发者运行测试后得到的数字可能与两份文档都不匹配，产生困惑。
- **建议修复**: 统一测试数量描述，或在数字旁注明统计日期。例如："截至 2026-08-11，314 个测试全部通过"。

### 问题 5: [严重度 LOW] ai-review.md data/ 目录描述未反映路径重定向修复

- **文件**: `docs/ai-review.md` 第 318-324 行
- **描述**: ai-review.md 的"目录结构"章节展示了 `data/` 目录包含 `feedbacks.json`、`adjustments.json`、`stats_cache.json` 等文件。但文档自身在第 355-358 行记录了 commit `9771579` 的修复："将 quality_monitor.cache_file 也重定向到工作空间目录"。这意味着这些文件的实际存储位置已被重定向到工作空间（被扫描项目下的 `.code-review/workspace/<scan_id>/`），而非 `data/` 目录。目录结构描述未反映这一变更。
- **建议修复**: 在 data/ 目录描述中加注说明，例如："data/ 目录为默认路径，实际运行时文件存储在工作空间目录下（见工作空间机制章节）"。

### 问题 6: [严重度 LOW] scan.py docstring 和 epilog 示例包含无效的 --output 参数

- **文件**: `scripts/scan.py` 第 4 行、第 562 行
- **描述**: scan.py 自身的模块 docstring 写 `用法: ... --output report/`，--help epilog 示例中也展示 `--output report/`。由于 `--output` 是死参数（同问题 2），这些内置文档会误导使用者。此问题与问题 2 关联，但修复点不同（修改的是代码中的文档字符串而非 markdown 文档）。
- **建议修复**: 从 docstring 和 epilog 示例中移除 `--output report/`，或在参数说明中标注该参数已废弃。

---

## 总结

- **通过项**: 10
- **问题数**: HIGH=1, MEDIUM=3, LOW=2

**整体评价**: 文档整体质量较好，核心架构描述、依赖说明、规约文件体系、工作空间机制、Harness 系统模块等关键内容与实际代码高度一致。confidence_thresholds.yaml 引用已在上一轮修正，offline-packages 数量（44）准确。

最关键的问题是 **问题 1（HIGH）**：ai-review.md 关于 `builtin_engine_v2.py` 被删除的记述与事实完全矛盾 -- 该文件不仅存在，而且被 rule_engine.py 主动导入并用于生产扫描流程，是"多引擎融合架构"中 Tree-sitter AST 引擎的实现载体。建议优先修复此问题，将所有相关描述统一为"已集成"状态。

其次建议处理 **问题 2-3（MEDIUM）**：`--output` 死参数在 advanced.md 和 validation.md 中仍被引用，可能导致 CI/CD 集成失败；auto_improver.py 在 Mermaid 图中缺少"待实现"标注，与文字描述矛盾。
