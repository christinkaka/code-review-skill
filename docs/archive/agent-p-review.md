# Agent P 文档验证报告（第 2 轮）

> 验证者：Agent P（首次接触项目的新开发者视角）
> 验证日期：2026-08-12
> 验证范围：README.md、docs/getting-started.md、docs/architecture.md、docs/ai-review.md

---

## 验证通过项

- [x] **依赖安装说明完整** -- getting-started.md 列出了 requirements.txt 中的所有依赖（pyyaml、gitpython、rich、tree-sitter 系列、jinja2、pandas），并给出了手动安装和验证命令。requirements.txt 实际内容与文档描述一致。
- [x] **getting-started.md 的 scan.py 命令示例已移除 --output** -- 第 107、115-119、125 行的命令示例均不再使用 `--output` 参数，与工作空间机制的实际行为一致。
- [x] **报告目录结构描述与实际输出一致** -- getting-started.md 第 132-143 行描述的 `.code-review/workspace/<scan_id>/` 目录结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与 scan.py 的 `create_workspace()` 函数实际创建的目录结构一致。
- [x] **README.md 中链接的所有顶层文件均存在** -- config.yaml、requirements.txt、install-offline.sh、install-semgrep-offline.sh、install-semgrep-offline.ps1、download-offline-packages.sh 均在项目根目录中存在。
- [x] **README.md 中链接的所有文档文件均存在** -- docs/getting-started.md、docs/architecture.md、docs/ai-review.md、docs/project-structure.md、docs/rules.md、docs/validation.md、docs/advanced.md 以及历史文档（TECH-STACK.md、SUBAGENT-REVIEW-ARCHITECTURE.md 等）均存在。
- [x] **references/ 目录结构完整** -- design/（3 类）、implementation/（4 类）、security/（12 类）、rules/、profiles/（3 个 profile）、prompts/（5 个工作流提示词 + README）、test-cases/ 均存在且内容与文档描述匹配。
- [x] **Harness 系统文件完整** -- config/harness.yaml 存在；harness/ 目录下 __init__.py、decision_logger.py、feedback_manager.py、quality_monitor.py、cli.py 均存在，与 ai-review.md 第 307-316 行描述一致。
- [x] **harness.py CLI 命令与文档匹配** -- scripts/harness.py 作为 harness.cli 的入口，实际支持 list/feedback/stats 三个子命令，与 ai-review.md 第 262-278 行的 CLI 命令文档一致。
- [x] **config.yaml 温度参数与文档一致** -- config.yaml 中 review.subagent.temperature 的 5 个工作流配置值（security: 0.1, quality: 0.2, performance: 0.1, architecture: 0.2, comprehensive: 0.1）与 architecture.md 第 441-447 行的文档完全一致。
- [x] **单元测试数量描述正确** -- ai-review.md 声称 "314 个测试全部通过"，实际运行 `pytest tests/ --collect-only` 确认收集到 314 个测试。
- [x] **confidence_thresholds.yaml 引用已修正** -- ai-review.md 第 165-169 行的 Mermaid 图中 C2 节点已改为 `config/harness.yaml`，不再引用不存在的 `confidence_thresholds.yaml`。
- [x] **.trae/skills/code-review/SKILL.md 存在** -- README.md 和 architecture.md 引用的 Skill 入口文件存在。
- [x] **scripts/ 目录文件列表与 architecture.md 一致** -- architecture.md 第 499-511 行和 project-structure.md 第 27-39 行列出的 12 个文件与 scripts/ 目录实际内容完全匹配（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）。
- [x] **security 规约 12 类描述正确** -- architecture.md 第 491 行声称 "安全规约（12 类，覆盖 OWASP Top 10）"，实际 references/security/ 目录下确实有 12 个 .md/.yaml 文件对。
- [x] **semgrep-offline-packages 数量正确** -- architecture.md 第 515 行声称 "70 个包"，实际目录包含 70 个文件，匹配。

---

## 发现的问题

### 问题 1: [HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件实际存在且被集成

- **文件**: docs/ai-review.md 第 395 行
- **描述**: "已完成的工作 > 代码清理" 章节声称 "删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但实际情况是：
  1. 文件 `scripts/builtin_engine_v2.py` 仍然存在于 scripts/ 目录中。
  2. `scripts/rule_engine.py` 第 28 行导入了 `from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`。
  3. `scripts/rule_engine.py` 第 308-313 行在扫描流程中主动使用 `BuiltinEngineV2` 作为 "Tree-sitter AST 补充引擎"。
  4. architecture.md 第 505 行和 project-structure.md 第 32 行均将该文件列为项目结构的正式组成部分。

  该描述在两个事实上错误：文件未被删除，且引擎已被集成。新开发者会误以为这是一个应该被清理的死文件。

- **建议修复**: 删除 ai-review.md 第 395 行关于 "删除 scripts/builtin_engine_v2.py" 的描述。同时补充说明 builtin_engine_v2.py 当前作为 rule_engine.py 的 Tree-sitter AST 补充引擎被集成使用。

### 问题 2: [MEDIUM] architecture.md 验证案例中仍使用已废弃的 --output 参数

- **文件**: docs/architecture.md 第 149 行
- **描述**: 验证案例 1 的命令为：
  ```bash
  $ python3 scripts/scan.py --repo test-validation/ --full-scan --output report/multi-engine/
  ```
  但 `--output` 参数虽然在 scan.py 第 576 行仍有定义（`parser.add_argument("--output", default="report")`），实际代码逻辑中 `args.output` 从未被引用。报告输出目录现在由 `create_workspace()` 函数自动决定（输出到被扫描项目的 `.code-review/workspace/<scan_id>/report/`），`--output` 是一个无效的死参数。

  getting-started.md 中的命令示例已正确移除了 `--output`，但 architecture.md 和 scan.py 自身的文档字符串（第 4 行、第 562 行）仍在使用它。

- **建议修复**:
  1. architecture.md 第 149 行移除 `--output report/multi-engine/`。
  2. scan.py 第 4 行文档字符串和第 562 行 epilog 示例移除 `--output`。
  3. 考虑从 scan.py 第 576 行删除 `--output` 参数定义，或添加 deprecation 说明。

### 问题 3: [MEDIUM] offline-packages 包数量描述与实际不符

- **文件**: README.md 第 121 行、docs/architecture.md 第 514 行
- **描述**: 两处均声称 offline-packages/ 包含 "41 个包"，但实际目录中包含 44 个 .whl 文件。新开发者或审计者清点文件数量时会产生疑惑。
- **建议修复**: 将 "41 个包" 更新为 "44 个包"，或改为模糊描述如 "40+ 个包"。

### 问题 4: [MEDIUM] ai-review.md Mermaid 图中 auto_improver.py 未标注为待实现

- **文件**: docs/ai-review.md 第 191-195 行
- **描述**: 架构总览 Mermaid 图中"反馈层"将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 `harness/auto_improver.py` 文件不存在，文档第 399-410 行的"待完成的工作"也确认其为低优先级未实现功能。图中没有任何"待实现"标注，与文字描述矛盾。新开发者看架构图会以为该功能已可用。
- **建议修复**: 在 Mermaid 图中为 F2 节点添加"（待实现）"标注，例如：
  ```
  F2["自动改进（待实现）
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```

### 问题 5: [LOW] ai-review.md 代码示例标注"待实现"但引用的函数已存在

- **文件**: docs/ai-review.md 第 39、100、128 行
- **描述**: 三个 Python 代码示例均标注了 `# scan.py 中的逻辑（待实现）`，暗示这些函数尚未编写。但实际情况是：
  - `load_harness_config()` 已存在于 scan.py 第 185 行
  - `build_feedback_examples()` 已存在于 scan.py 第 325 行
  - 这两个函数在 scan.py 第 428、453 行被实际调用

  只有 `generate_subagent_prompt()` 确实不存在（其功能由 `ai_reviewer.py` 实现）。

  "待实现"标注会误导新开发者以为 Harness 集成的扫描端逻辑尚未编写。

- **建议修复**: 将第 39、100、128 行的 `# scan.py 中的逻辑（待实现）` 改为更准确的描述，如 `# scan.py 中的逻辑（示意代码，实际实现见 scan.py 第 N 行）`，并标注实际对应的函数名和行号。

---

## 总结

| 类别 | 数量 |
|------|------|
| 验证通过项 | 15 |
| HIGH 问题 | 1 |
| MEDIUM 问题 | 3 |
| LOW 问题 | 1 |
| **问题总计** | **5** |

**核心结论**：文档整体质量较好，大部分描述与实际代码一致。最关键的问题是 ai-review.md 中关于 `builtin_engine_v2.py` 被删除的记述与事实完全矛盾 -- 该文件不仅存在，而且被 rule_engine.py 主动导入并用于生产扫描流程。建议优先修复问题 1（HIGH），然后处理问题 2-4（MEDIUM），最后处理问题 5（LOW）。
