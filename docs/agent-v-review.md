# Agent V 文档验证报告（第 5 轮）

> 验证人：Agent V（首次接触项目的新开发者视角）
> 验证日期：2026-08-12
> 验证范围：README.md、getting-started.md、architecture.md、ai-review.md

---

## 验证通过项

- [x] **依赖安装说明完整** -- README.md 和 getting-started.md 的依赖安装步骤一致且完整：`pip install -r requirements.txt` + `brew install semgrep`（可选）。requirements.txt 中各依赖的说明与实际用途匹配。验证安装命令 `python -c "import yaml, git, jinja2, pandas; print('all ok')"` 可正常执行。
- [x] **报告目录结构描述与实际输出一致** -- getting-started.md 和 architecture.md 中描述的报告目录结构（report/report.json、report/report.md、report/summary.json、report/subagent-review-task.md、cache/、decisions/、feedbacks.json、stats_cache.json）与实际扫描输出的工作空间结构完全一致。
- [x] **文档中提到的所有文件均存在** -- 四份文档中通过相对路径引用的所有文件均已验证存在：docs/getting-started.md、docs/architecture.md、docs/ai-review.md、docs/project-structure.md、docs/rules.md、docs/validation.md、docs/advanced.md、docs/TECH-STACK.md、docs/SUBAGENT-REVIEW-ARCHITECTURE.md、docs/DIRECTORY-STRUCTURE.md、docs/VERIFICATION_MATRIX.md、docs/COMPLETION-REPORT.md、docs/IMPLEMENTATION-PLAN.md、docs/CLEANUP-REPORT.md、docs/ITERATION-REPORT.md、docs/SPECS-SUMMARY.md、docs/WORKFLOW-UPDATE.md、docs/guides/OFFLINE-INSTALL.md、docs/guides/SEMGREP-OFFLINE-INSTALL.md、references/subagent-contract.md、references/main-agent-contract.md、references/RULE-GENERATOR-GUIDE.md、.trae/skills/code-review/SKILL.md、config/harness.yaml。
- [x] **scripts/ 目录下的文件列表与实际一致** -- architecture.md 列出的 12 个脚本文件（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）与 scripts/ 目录实际文件完全一致。
- [x] **规约文件齐全** -- references/ 目录下规约文件体系完整：安全规约 12 类（authorization、deserialization、hardcoded-secrets、log-injection、path-traversal、privilege-escalation、signature-bypass、sql-injection、ssrf、weak-randomness、xss、xxe），设计规约 3 类（api-design、architecture、database），实现规约 4 类（concurrency、error-handling、naming、null-safety），Profile 配置 3 个（default、minimal、strict），提示词 5 个（ai-enhancer、architecture-review、code-quality、performance-review、security-audit），测试案例 14 个。所有 .md 规约均有对应的 .yaml 元数据文件。
- [x] **Harness 系统核心模块与代码匹配** -- ai-review.md 描述的 harness/ 目录结构（__init__.py、decision_logger.py、feedback_manager.py、quality_monitor.py、cli.py）与实际代码完全一致。config/harness.yaml 的配置结构（decision_logging、feedback、auto_improvement、quality_monitor）与文档描述匹配。CLI 命令（list、feedback、stats）在 harness.py 和 harness/cli.py 中均有实现。
- [x] **confidence_thresholds.yaml 引用已修正** -- 在四份文档中均未发现对 `confidence_thresholds.yaml` 的引用。ai-review.md Mermaid 图中约束层 C2 节点（第 167 行）已正确标注为 `config/harness.yaml`。全项目代码搜索也未发现对该文件名的引用。
- [x] **offline-packages 包数量正确** -- 实际文件数量为 44 个，architecture.md 第 514 行描述"核心离线依赖包（44 个包，约 104MB，支持多平台）"准确。semgrep-offline-packages 实际数量为 70 个，与文档描述一致。
- [x] **测试总数一致** -- 通过 `pytest tests/ --co -q` 确认收集到 314 个测试，与文档描述一致。实际运行结果：275 通过、33 失败、6 跳过，与 ai-review.md 第 392 行的记录一致。
- [x] **scan.py 命令可正常运行** -- `python scripts/scan.py --help` 可正常执行，输出完整的参数说明和使用示例。

---

## 发现的问题

### 问题 1: [HIGH] builtin_engine_v2.py 状态描述自相矛盾

- **文件**: ai-review.md 第 395 行、architecture.md 第 421 行和第 505 行
- **描述**: ai-review.md "已完成的工作"章节明确声称"删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"，但该文件实际仍存在于 `scripts/builtin_engine_v2.py`。与此同时，architecture.md 在项目结构树（第 505 行）中将其列为正式组件"内置引擎 V2（基于 Tree-sitter）"，并在术语说明（第 421 行）中描述其为多引擎融合架构的组成部分。两份文档一个说"已删除"、一个说"正在使用"，形成了直接矛盾。新开发者阅读 ai-review.md 会以为该文件不存在，但实际它在项目中；阅读 architecture.md 会以为它是正式集成组件，但 ai-review.md 又说它"从未集成"。
- **实际状态**: 文件存在于 `scripts/builtin_engine_v2.py`，architecture.md 将其作为项目结构的一部分列出。
- **建议修复**: 在 ai-review.md 中修正"删除 scripts/builtin_engine_v2.py"的描述，改为"保留 scripts/builtin_engine_v2.py 并集成到多引擎融合架构中"。同时确保 architecture.md 中对该文件的角色描述与 ai-review.md 一致。

### 问题 2: [MEDIUM] ai-review.md 内部测试描述自相矛盾

- **文件**: ai-review.md 第 341 行和第 392 行
- **描述**: 同一文档中对测试结果存在两个互相矛盾的描述。第 341 行"当前实现状态"表格中写道"314 个测试**全部通过**"，但第 392 行"已完成的工作 > 测试覆盖"中写道"总计 314 个测试（**275 通过，33 失败，6 跳过**）"。实际运行 pytest 结果为 275 passed, 33 failed, 6 skipped，与第 392 行一致。第 341 行的"全部通过"是错误描述。新开发者如果看到"全部通过"后自己运行测试发现 33 个失败，可能会误以为环境配置有问题。
- **建议修复**: 将第 341 行的"314 个测试全部通过"修正为"314 个测试（275 通过，33 失败，6 跳过）"，与第 392 行保持一致。

### 问题 3: [MEDIUM] auto_improver.py 在架构图中被当作现有组件展示

- **文件**: ai-review.md 第 191-195 行
- **描述**: ai-review.md 的架构总览 Mermaid 图中，反馈层 F2 节点将 `auto_improver.py` 作为已存在的组件展示（标注为"自动改进 -- auto_improver.py -- 根据反馈调整阈值 -- 输出: adjustments.json"），但该文件实际不存在（`harness/auto_improver.py` 未找到）。虽然在第 399-410 行"待完成的工作"章节中正确标注了 `harness/auto_improver.py` 为阶段 3 待实现功能（优先级：低），但架构图给人的印象是该组件已经就绪。此外，图中的虚线箭头 `F2 -.->|调整阈值| C2` 也暗示该功能链路已打通。
- **建议修复**: 在架构图的 F2 节点中标注 `auto_improver.py` 为"待实现"状态（例如在名称后加 `（待实现）` 后缀），或将该节点用虚线样式表示尚未实现，使图中文档与"待完成的工作"描述保持一致。

### 问题 4: [LOW] scan.py 中 --output 参数为死代码

- **文件**: scripts/scan.py 第 576 行
- **描述**: `scan.py` 的 argparse 定义中仍然保留了 `--output` 参数（`parser.add_argument("--output", default="report", help="报告输出目录")`），该参数会出现在 `--help` 输出中，用户可以看到并指定该参数。但在整个 scan.py 代码中，`args.output` 从未被引用 -- 报告实际输出到工作空间目录（`workspace["report_dir"]`）。这意味着用户传入的 `--output` 值会被无声忽略，不会有任何效果。虽然四份文档的示例命令中均未使用 `--output`（文档层面无问题），但参数本身的存在会误导尝试自定义输出目录的用户。
- **建议修复**: 移除 scan.py 第 576 行的 `parser.add_argument("--output", ...)` 定义，清理死代码。如果确实需要保留该参数以备将来使用，至少应在 help 文本中标注 `（暂未启用）`。

---

## 总结

| 维度 | 结果 |
|------|------|
| 通过项 | 10 |
| 问题数 | HIGH=1, MEDIUM=2, LOW=1 |
| 最严重问题 | builtin_engine_v2.py 状态描述自相矛盾（ai-review.md 称已删除，实际存在；architecture.md 列为正式组件） |
| 文档间一致性 | 存在冲突：ai-review.md 与 architecture.md 对 builtin_engine_v2.py 的描述矛盾 |
| 文档内一致性 | ai-review.md 内部测试结果描述矛盾（第 341 行 vs 第 392 行） |

**整体评价**: 四份文档的整体质量较好。依赖安装说明完整准确，规约文件体系齐全（12+3+4 类规约 + 3 Profile + 5 提示词），scripts/ 文件列表与实际一致，报告目录结构描述正确，Harness 核心模块与代码匹配，confidence_thresholds.yaml 引用已在之前轮次修正，offline-packages 数量（44）准确，测试数量（314 = 275 + 33 + 6）记录正确。主要问题集中在 builtin_engine_v2.py 的状态描述（文档间矛盾 + 与实际不符）和 ai-review.md 内部测试数据自相矛盾。建议优先修复 HIGH 级别的 builtin_engine_v2.py 状态描述问题。
