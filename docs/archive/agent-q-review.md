# Agent Q 文档验证报告（第 3 轮）

> 验证人：Agent Q（首次接触项目的新开发者视角）
> 验证日期：2026-08-12
> 验证范围：README.md、docs/getting-started.md、docs/architecture.md、docs/ai-review.md

---

## 验证通过项

- [x] **依赖安装说明完整** -- requirements.txt 存在于项目根目录，getting-started.md 列出了所有核心依赖（pyyaml、jinja2、gitpython、rich、tree-sitter 系列、pandas）及可选依赖（semgrep），并提供了验证安装命令。实际依赖与文档描述一致。
- [x] **getting-started.md 的 scan.py 命令示例已移除 --output** -- 第 107、115-119、125 行的命令示例均不再使用 `--output` 参数，与工作空间机制的实际行为一致。
- [x] **architecture.md 验证案例命令已移除 --output** -- 第 149 行命令为 `python3 scripts/scan.py --repo test-validation/ --full-scan`，不含 `--output`。
- [x] **报告目录结构描述与实际输出一致** -- getting-started.md 第 132-143 行描述的 `.code-review/workspace/<scan_id>/` 目录结构（report/、cache/、decisions/、feedbacks.json、stats_cache.json）与 scan.py 中 `create_workspace()` 函数的实际行为完全匹配。
- [x] **scripts/ 目录下的文件列表与实际一致** -- architecture.md 第 499-511 行所列的 12 个脚本文件（scan.py、diff_analyzer.py、call_graph.py、rule_engine.py、rule_compiler.py、builtin_engine_v2.py、ai_reviewer.py、report_generator.py、harness.py、scheduler.py、notifier.py、test_rules.py）与实际 scripts/ 目录内容完全一致。
- [x] **规约文件全部存在** -- references/ 下的 design/（3 类）、implementation/（4 类）、security/（12 类）规约的 .md 和 .yaml 文件均存在；profiles/（default/strict/minimal）均存在；prompts/（5 种工作流提示词）均存在；test-cases/ 均存在。
- [x] **Harness 系统核心文件描述与实际代码匹配** -- harness/ 目录包含 __init__.py、decision_logger.py、feedback_manager.py、quality_monitor.py、cli.py，与 ai-review.md 第 310-315 行描述完全一致。config/harness.yaml 存在且包含决策日志、反馈、自动改进、质量监控四部分配置。
- [x] **confidence_thresholds.yaml 引用已修正** -- ai-review.md 的 Mermaid 图中 C2 节点已标注为 `config/harness.yaml`，不再引用不存在的 `confidence_thresholds.yaml`。architecture.md 中同样无此引用。全项目搜索未发现对 `confidence_thresholds.yaml` 的引用。
- [x] **offline-packages 包数量正确** -- 实际文件数为 44 个，与 architecture.md 第 514 行描述"44 个包"一致。semgrep-offline-packages 为 70 个包，与第 515 行描述一致。
- [x] **README.md 文档链接有效** -- README.md 中引用的所有文档文件（getting-started.md、architecture.md、project-structure.md、rules.md、ai-review.md、subagent-contract.md、SKILL.md、validation.md、advanced.md、main-agent-contract.md、RULE-GENERATOR-GUIDE.md 及历史文档）均实际存在。
- [x] **单元测试数量描述准确** -- ai-review.md 声称"314 个测试全部通过"，实际运行 `pytest --collect-only` 确认收集到 314 个测试，数量匹配。
- [x] **工作空间机制描述准确** -- architecture.md 第 192-251 行对工作空间机制的描述（创建位置、目录结构、优势）与 scan.py 中 `create_workspace()` 的实际实现一致。工作空间确实创建在被扫描项目的 `.code-review/workspace/` 下。

---

## 发现的问题

### 问题 1: [HIGH] ai-review.md 声称已删除 builtin_engine_v2.py 但文件实际存在且已集成

- **文件**: docs/ai-review.md 第 395 行
- **描述**: ai-review.md 第 395 行在"代码清理"章节中写道："删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但该文件实际存在于 `scripts/builtin_engine_v2.py`，并且被 `scripts/rule_engine.py` 第 28 行导入使用（`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`），说明该引擎已集成到扫描流程中。architecture.md 第 505 行也在项目结构中将 builtin_engine_v2.py 列为 scripts/ 下的正常组件，没有任何"已删除"或"实验性"标注。新开发者阅读 ai-review.md 后会认为该文件已被删除，但实际去查找时发现它存在且被使用，产生严重困惑。
- **建议修复**: 将 ai-review.md 第 395 行从"删除 scripts/builtin_engine_v2.py"改为"保留 scripts/builtin_engine_v2.py（已集成到 rule_engine.py 作为内置 AST 引擎）"。如果确实曾计划删除但后来恢复了，应更新描述以反映最终状态。

### 问题 2: [MEDIUM] scan.py 中 --output 参数为死参数，代码内置文档仍在使用

- **文件**: scripts/scan.py 第 4 行、第 562 行、第 576 行
- **描述**: scan.py 在 argparse 中定义了 `--output` 参数（第 576 行，默认值 `"report"`），但 `args.output` 在整个代码中从未被读取（经全文件搜索确认）。实际输出始终写入被扫描项目下的 `.code-review/workspace/<scan_id>/report/`。虽然 getting-started.md 和 architecture.md 的主要示例已修正，但 scan.py 自身的模块 docstring（第 4 行）仍写 `--output report/`，`--help` 示例（第 562 行）也展示 `--output report/`。新开发者运行 `python scripts/scan.py --help` 后会看到包含 `--output` 的示例，按照操作后输出位置与预期完全不同。
- **建议修复**: (1) 从 scan.py 第 4 行 docstring 中移除 `--output report/`；(2) 从第 562 行 epilog 示例中移除 `--output report/`；(3) 从第 576 行删除 `--output` 参数定义，或添加 deprecation 说明并注释实际输出由工作空间管理。

### 问题 3: [MEDIUM] ai-review.md Mermaid 流程图中 auto_improver.py 未标注"待实现"

- **文件**: docs/ai-review.md 第 191-195 行
- **描述**: 架构总览 Mermaid flowchart 的"反馈层"将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 `harness/auto_improver.py` 文件不存在（经 Glob 搜索确认），ai-review.md 自身在第 399-410 行"待完成的工作"中也正确标注了该文件为"阶段 3：自动改进（优先级：低）"，即尚未实现。流程图中没有任何"待实现"标注，与文字描述自相矛盾。新开发者看架构图会以为该功能已可用。
- **建议修复**: 在 F2 组件描述中添加"（待实现）"标注，例如：`F2["自动改进（待实现）\n─────\nauto_improver.py\n根据反馈调整阈值\n输出: adjustments.json"]`。

### 问题 4: [MEDIUM] ai-review.md 目录结构章节中 data/ 描述与实际运行时行为不一致

- **文件**: docs/ai-review.md 第 306-325 行
- **描述**: ai-review.md 的"目录结构"章节展示运行时数据存放在项目根目录的 `data/` 下：
  ```
  ├── data/                         # 运行时数据（.gitignore）
  │   ├── decisions/                # 决策日志（按扫描批次）
  │   ├── feedbacks.json            # 用户反馈
  │   ├── adjustments.json          # 调整记录
  │   └── stats_cache.json          # 统计缓存
  ```
  但实际 scan.py 在运行时会将这些路径重定向到工作空间目录：
  - `decisions/` → `<workspace>/decisions/`（scan.py 第 430 行）
  - `feedbacks.json` → `<workspace>/feedbacks.json`（scan.py 第 431 行）
  - `stats_cache.json` → `<workspace>/stats_cache.json`（scan.py 第 432 行）
  
  这与 getting-started.md 第 132-143 行的描述一致（均展示为工作空间内的子目录），但 ai-review.md 的目录结构章节描述的是 harness 组件的默认路径（不经过 scan.py 覆盖时的路径），容易造成混淆。此外，`adjustments.json` 被列出但由于 auto_improver.py 未实现，该文件永远不会生成。
- **建议修复**: 在目录结构章节添加注释说明这些是 harness 组件的默认路径，实际扫描时会被 scan.py 重定向到工作空间目录。对 `adjustments.json` 添加"（待实现，auto_improver.py 未创建前不会生成）"标注。

### 问题 5: [LOW] advanced.md 和 validation.md 仍使用已废弃的 --output 参数

- **文件**: docs/advanced.md 第 36 行，docs/validation.md 第 61、64 行
- **描述**: 虽然 getting-started.md 和 architecture.md 的主要示例已移除 `--output`，但 advanced.md 第 36 行（CI/CD 集成示例）和 validation.md 第 61、64 行（验证命令示例）仍在使用 `--output report/`。这些文档中的命令不会报错（因为参数仍被 argparse 接受），但输出位置与 `--output` 指定的路径不同。此外，多个历史文档（COMPLETION-REPORT.md、SUBAGENT-REVIEW-ARCHITECTURE.md、WORKFLOW-UPDATE.md、VERIFICATION_MATRIX.md）也包含 `--output` 引用。
- **建议修复**: 将 advanced.md 和 validation.md 中的 `--output report/` 移除或替换为实际输出路径说明。历史文档可考虑添加注释标明 `--output` 已废弃。

### 问题 6: [LOW] architecture.md 规约引擎层描述与多引擎融合描述存在术语不一致

- **文件**: docs/architecture.md 第 301-317 行 vs 第 119-143 行
- **描述**: architecture.md 的 Mermaid 架构图中，"规约引擎层"只包含两个引擎（内置正则 + Semgrep），并附有术语说明（第 421 行）："本文档中'双引擎'指规约引擎层的'内置正则 + Semgrep'。Tree-sitter AST 引擎属于差异分析层"。但同一文档的"多引擎融合架构"章节（第 119-143 行）明确将 Tree-sitter AST 列为三个扫描引擎之一，融合策略中第 2 步就是"Tree-sitter AST 引擎扫描"。实际上 `builtin_engine_v2.py`（基于 Tree-sitter）被 `rule_engine.py` 导入用于扫描。架构图将 Tree-sitter 仅放在"差异分析层"会给新开发者造成它不参与规则扫描的印象，与多引擎融合章节矛盾。
- **建议修复**: 在 Mermaid 图的规约引擎层中增加 Tree-sitter AST 引擎节点，或在术语说明中补充："Tree-sitter AST 同时参与差异分析层（调用图构建）和规约引擎层（作为内置引擎 V2 参与扫描），详见多引擎融合架构章节"。

---

## 总结

- **通过项**: 12
- **问题数**: HIGH=1, MEDIUM=3, LOW=2
- **整体评价**: 文档整体质量较高。核心入门文档（getting-started.md）和架构文档（architecture.md）的主要示例和描述与实际代码行为一致。依赖安装说明完整，规约文件齐全，Harness 系统描述与实际代码匹配，offline-packages 数量正确，confidence_thresholds.yaml 引用已修正。主要问题集中在：(1) ai-review.md 关于 builtin_engine_v2.py 的删除声明与实际状态严重矛盾（HIGH）；(2) scan.py 代码内置文档仍包含死参数 --output（MEDIUM）；(3) ai-review.md 的 auto_improver.py 在流程图中缺少"待实现"标注（MEDIUM）；(4) ai-review.md 的 data/ 目录结构描述与实际工作空间行为不一致（MEDIUM）。
