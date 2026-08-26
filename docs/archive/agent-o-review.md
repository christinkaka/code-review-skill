# Agent O 文档验证报告（第 2 轮）

> 验证人：Agent O（首次接触项目的独立开发者视角）
> 验证日期：2026-08-12
> 验证范围：README.md、docs/getting-started.md、docs/architecture.md、docs/ai-review.md
> 验证方法：逐条对照文档描述与实际代码/文件结构，实际运行 scan.py 验证输出

---

## 验证通过项

- [x] **依赖安装说明完整** -- getting-started.md 列出的手动安装命令（pyyaml, gitpython, tree-sitter, tree-sitter-java, tree-sitter-python, tree-sitter-javascript, rich, jinja2, pandas）覆盖了 requirements.txt 中所有依赖。semgrep 正确标注为可选。
- [x] **scan.py 能正常运行** -- `python scripts/scan.py --repo test-validation/ --full-scan --workflow security` 执行成功，耗时 2.56s，输出 70 个问题，Harness 正常启用。
- [x] **报告目录结构基本一致** -- 实际输出包含 report/（report.json, report.md, summary.json, subagent-review-task.md）和 decisions/，与 getting-started.md 描述的核心文件一致。
- [x] **文档中提到的所有核心文件均存在** -- config.yaml, requirements.txt, config/harness.yaml, harness/ 四个模块（decision_logger.py, feedback_manager.py, quality_monitor.py, cli.py）, scripts/ 全部 12 个脚本, references/ 下规约文件（12 个安全规约、3 个设计规约、4 个实现规约）、3 个 Profile（default/strict/minimal）、5 个提示词文件均存在。
- [x] **scripts/ 目录文件列表一致** -- architecture.md 列出的 12 个脚本文件（scan.py, diff_analyzer.py, call_graph.py, rule_engine.py, rule_compiler.py, builtin_engine_v2.py, ai_reviewer.py, report_generator.py, harness.py, scheduler.py, notifier.py, test_rules.py）与实际 scripts/ 目录完全一致。
- [x] **规约文件完整** -- 安全规约 12 类（与文档描述一致，覆盖 OWASP Top 10），设计规约 3 类（api-design, architecture, database），实现规约 4 类（concurrency, error-handling, naming, null-safety），自定义规则 1 类（custom）。每个 .md 规约都有对应的 .yaml 文件。
- [x] **Harness 系统核心模块描述与代码匹配** -- harness/ 目录包含 __init__.py, cli.py, decision_logger.py, feedback_manager.py, quality_monitor.py，与 ai-review.md 目录结构描述一致。DecisionLogger、FeedbackManager、QualityMonitor 三个类均已实现。
- [x] **Harness 实现状态表准确** -- ai-review.md 的"当前实现状态"表格中 12 项功能均标注为"已实现"，经代码验证属实（scan.py 确实读取 harness.yaml、写入决策日志、读取历史反馈、ai_reviewer.py 注入反馈）。
- [x] **confidence_thresholds.yaml 引用已修正** -- ai-review.md Mermaid 图中的约束层 C2 已正确标注为 `config/harness.yaml`，不再引用不存在的独立配置文件。
- [x] **test-cases/ 目录结构一致** -- references/test-cases/ 下包含 security/（7 个测试）、design/（3 个测试）、implementation/（4 个测试），与 architecture.md 描述一致。
- [x] **offline-packages/ 和 semgrep-offline-packages/ 存在** -- 离线安装包目录均存在，包含大量 .whl 文件。
- [x] **安装脚本文件均存在** -- install-offline.sh, install-semgrep-offline.sh, install-semgrep-offline.ps1, download-offline-packages.sh 均存在。
- [x] **.trae/skills/code-review/SKILL.md 存在** -- Skill 入口文件存在。
- [x] **getting-started.md 中的扫描命令示例正确** -- 文档中的命令示例（`python scripts/scan.py --repo ~/my-project --full-scan --workflow comprehensive`）未使用 --output 参数，与实际推荐用法一致。
- [x] **config.yaml 温度参数配置与文档一致** -- architecture.md 描述的温度参数（security: 0.1, quality: 0.2, performance: 0.1, architecture: 0.2, comprehensive: 0.1）与 config.yaml 实际配置完全一致。
- [x] **docs/reports/ 目录存在** -- README.md 中提到的 `docs/reports/` 历史报告归档目录确实存在，包含 security-fixes/ 和 validation/ 子目录。

---

## 发现的问题

### 问题 1: [HIGH] `--output` 参数是死参数但文档多处引用

- **文件**: architecture.md 第 149 行, scan.py 第 4 行/第 562 行/第 576 行
- **描述**: `scan.py` 在 argparse 中定义了 `--output` 参数（第 576 行，默认值 `"report"`），但 `args.output` 在整个代码中从未被读取。实际输出始终写入被扫描项目下的 `.code-review/workspace/<scan_id>/report/`。然而：
  - architecture.md 第 149 行的验证案例命令使用了 `--output report/multi-engine/`
  - scan.py 的 docstring（第 4 行）仍然写 `--output report/`
  - scan.py 的 --help 示例（第 562 行）展示 `--output report/`
  - 新开发者按照文档使用 `--output` 后，不会收到任何错误，但输出位置与预期完全不同
- **验证方法**: `grep "args.output" scripts/scan.py` 返回 0 条结果。实际运行 `python scripts/scan.py --repo test-validation/ --full-scan --workflow security` 后输出到 `test-validation/.code-review/workspace/2026-08-12_14-14-34_75ec/report/`。
- **建议修复**: 方案 A（推荐）：从 argparse 中删除 `--output` 参数定义，更新 scan.py docstring 和 --help 示例，在 architecture.md 验证案例中移除 `--output` 并注释实际输出路径。方案 B：恢复 `--output` 的实际功能，允许覆盖默认输出目录。

### 问题 2: [HIGH] ai-review.md 声称已删除 builtin_engine_v2.py，但文件存在且被活跃使用

- **文件**: ai-review.md 第 395 行
- **描述**: ai-review.md "代码清理"部分明确写道："删除 scripts/builtin_engine_v2.py（实验性 AST 引擎，从未集成）"。但实际上：
  - 文件 `scripts/builtin_engine_v2.py` 仍然存在（584+ 行完整代码）
  - `scripts/rule_engine.py` 第 28 行导入它：`from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE`
  - `rule_engine.py` 第 308-310 行使用它：`if BuiltinEngineV2 is not None and TS_AVAILABLE: ast_engine = BuiltinEngineV2()`
  - 它是多引擎融合架构中 AST 引擎的实际实现，architecture.md 正确列出了它
  - 实际扫描日志输出 "AST 引擎扫描完成: 18 个文件, 11 个问题" 证明它在工作
- **影响**: 新开发者会认为这个文件应该不存在，可能尝试"清理"它，导致 AST 引擎功能丢失。同时文档内部自相矛盾（ai-review.md 说删除，architecture.md 说在用）。
- **建议修复**: 删除 ai-review.md 第 395 行关于"删除 scripts/builtin_engine_v2.py"的描述。改为："builtin_engine_v2.py 已集成到 rule_engine.py 中，作为 AST 引擎组件"。

### 问题 3: [MEDIUM] ai-review.md 目录结构描述 `data/` 在项目根目录，但实际数据写入工作空间

- **文件**: ai-review.md 第 306-325 行
- **描述**: ai-review.md 的"目录结构"章节描述 `data/` 目录在项目根目录下：
  ```
  code-review-skill/
  ├── data/                         # 运行时数据（.gitignore）
  │   ├── decisions/                # 决策日志
  │   ├── feedbacks.json            # 用户反馈
  │   ├── adjustments.json          # 调整记录
  │   └── stats_cache.json          # 统计缓存
  ```
  但实际行为是：
  - `scan.py` 第 430-432 行将 harness 数据路径重定向到工作空间：`<repo>/.code-review/workspace/<scan_id>/`
  - 实际扫描输出中，decisions/ 在 `<repo>/.code-review/workspace/<scan_id>/decisions/`
  - 项目根目录下不存在 `data/` 目录
  - harness.yaml 默认配置（`data/decisions`, `data/feedbacks.json`）被 scan.py 运行时覆盖
  - `scripts/harness.py` CLI 工具使用默认的 `data/` 路径，无法读取 scan.py 写入工作空间的数据
- **影响**: 新开发者按照文档在项目根目录找 `data/` 目录会找不到。使用 harness.py CLI 工具时也会因路径不匹配而无法读取 scan.py 产生的决策日志。
- **建议修复**: 更新 ai-review.md 目录结构描述，说明 `data/` 是 harness 组件的默认路径，但 scan.py 会将数据重定向到被扫描项目的工作空间目录下。补充说明 CLI 工具与 scan.py 使用不同路径的注意事项。

### 问题 4: [MEDIUM] getting-started.md 对 feedbacks.json 和 stats_cache.json 的生成时机描述不准确

- **文件**: getting-started.md 第 142-143 行
- **描述**: getting-started.md 报告目录结构中标注：
  - `feedbacks.json  # 用户反馈记录（Harness 启用时生成）`
  - `stats_cache.json  # 统计缓存（Harness 启用时生成）`
  但实际验证发现：
  - 即使 Harness 已启用（扫描日志显示 "Harness: 决策日志已启用" 和 "Harness: 反馈管理已启用"），这两个文件也不会在工作空间中生成
  - `feedbacks.json` 仅在用户通过 `harness.py feedback` CLI 命令添加反馈时才会创建（FeedbackManager._save() 在 add_feedback() 中调用）
  - `stats_cache.json` 仅在 QualityMonitor.save_cache() 被显式调用时才会创建，但 scan.py 扫描流程中未调用此方法
  - 实际扫描后工作空间中只有 `report/` 和 `decisions/` 目录，没有这两个文件
- **建议修复**: 将注释修改为：
  - `feedbacks.json  # 用户反馈记录（用户通过 harness.py feedback 添加反馈后生成）`
  - `stats_cache.json  # 统计缓存（执行 harness.py stats 后生成）`

### 问题 5: [MEDIUM] ai-review.md Mermaid 流程图中 auto_improver.py 未标注"待实现"

- **文件**: ai-review.md 第 191-195 行
- **描述**: ai-review.md 的架构总览 flowchart 中，反馈层将 `auto_improver.py` 画为已实现的组件：
  ```
  F2["自动改进
  ─────
  auto_improver.py
  根据反馈调整阈值
  输出: adjustments.json"]
  ```
  但 ai-review.md 自身在第 401-410 行"待完成的工作"中正确标注了该文件为"阶段 3：自动改进（优先级：低）"，即尚未实现。`harness/` 目录中也不存在 `auto_improver.py` 文件。流程图与文字描述自相矛盾。
- **建议修复**: 在流程图的 F2 组件描述中添加"（待实现）"标注，例如：`F2["自动改进（待实现）\n─────\nauto_improver.py\n..."]`。

### 问题 6: [LOW] scan.py docstring 和 --help 示例包含无效的 --output 参数

- **文件**: scripts/scan.py 第 4 行、第 561-562 行
- **描述**: scan.py 的模块 docstring 写 `用法: ... --output report/`，--help 示例中也展示 `--output report/`。由于 `--output` 是死参数（同问题 1），这些内置文档会误导使用者。此问题与问题 1 关联，但修复点不同（修改的是代码中的文档字符串而非 markdown 文档）。
- **建议修复**: 从 docstring 和 --help 示例中移除 `--output report/`。

---

## 补充发现（非验证要点但值得注意）

### 发现 A: harness.py CLI 与 scan.py 的数据路径不一致

- **描述**: `scripts/harness.py` CLI 工具通过 `harness/cli.py` 使用 DecisionLogger/FeedbackManager 的默认路径（`data/decisions/`, `data/feedbacks.json`），但 scan.py 将数据写入被扫描项目的工作空间目录。这意味着 CLI 工具无法读取 scan.py 产生的决策日志和反馈数据。这是一个功能性 bug，不影响文档正确性，但影响 Harness 系统的可用性。

### 发现 B: architecture.md 验证案例数据与实际略有差异

- **描述**: architecture.md 第 156 行记录 "去重后 69 个问题"，但实际运行同样命令得到 70 个问题。这可能是 Semgrep 规则集版本差异导致，属于历史数据偏差，不影响架构描述的正确性。

---

## 总结

- **通过项**: 16
- **问题数**: HIGH=2, MEDIUM=3, LOW=1
- **总体评价**: 四份文档的核心架构描述、依赖说明、规约文件列表、Harness 实现状态等关键内容基本准确。confidence_thresholds.yaml 引用已修正，auto_improver.py 在文字描述中已正确标注为待实现。主要问题集中在两个方面：(1) `--output` 死参数在代码和多份文档中仍被引用（HIGH），会直接误导使用者；(2) ai-review.md 声称已删除 builtin_engine_v2.py 但该文件实际存在且被活跃使用（HIGH），造成文档内部自相矛盾。建议优先修复这两个 HIGH 级问题。
