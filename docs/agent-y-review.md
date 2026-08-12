# Agent Y 文档验证报告（第 7 轮）

## 验证方法

独立阅读 `README.md`、`docs/getting-started.md`、`docs/architecture.md`、`docs/ai-review.md` 四个文档，并对照实际代码（`scripts/scan.py`、`scripts/test_rules.py`、`scripts/rule_engine.py`、`harness/`）及目录结构进行核对。

---

## 验证通过项

- [x] **`builtin_engine_v2.py` 状态描述一致**:`ai-review.md` 第 398 行明确写为 "保留并集成 scripts/builtin_engine_v2.py（Tree-sitter AST 引擎，已集成到 rule_engine.py 中，作为多引擎融合架构的 AST 引擎组件，参与生产扫描流程）";`rule_engine.py` 第 28 行 `from builtin_engine_v2 import BuiltinEngineV2, TS_AVAILABLE` 确认已实际集成。
- [x] **`auto_improver.py` 标注为待实现**:`ai-review.md` 第 193 行 Mermaid 图中 F2 节点明确标注 `auto_improver.py（待实现）`,第 321 行的目录结构注释中也写 `adjustments.json # 调整记录（待实现,auto_improver.py 未创建前不会生成）`,第 404-413 行"待完成的工作"章节进一步说明 `harness/auto_improver.py` 尚未创建。三处标注一致。
- [x] **`data/` 目录描述已添加说明**:`ai-review.md` 第 318 行的目录结构以 `data/ # 默认回退路径（实际运行时被覆盖到工作空间）` 标注,且列出 `decisions/`、`feedbacks.json`、`adjustments.json`、`stats_cache.json` 四个子项,每个子项都用注释说明实际写到工作空间。仓库中 `data/decisions/` 目录确实存在（虽然为空）,与文档描述吻合。
- [x] **`tests/` 目录及测试统计正确**:`tests/` 实际包含 15 个测试文件（README/ACCEPTANCE/FEASIBILITY/conftest + 12 个 test_*.py）,pytest 收集 314 个测试全部吻合,与 `ai-review.md` 第 395 行 "完整 314 个测试分布在 15 个测试文件中" 一致。

---

## 发现的问题

### 问题 1: CI/CD 示例 artifact 路径仍使用已废弃的 `report/` 路径 [MEDIUM]
- 文件: `docs/advanced.md`
- 描述: 第 36-43 行的 GitHub Actions CI/CD 示例中:
  - 第 36 行 `scan.py` 命令已经不再使用 `--output`（已正确）
  - 第 37 行 `python scripts/test_rules.py --output test-report.json` 这个命令本身在 `test_rules.py` 中确实有 `--output` 参数（test_rules.py 第 216-219 行）,所以命令本身可执行
  - **但** 第 38-43 行的 `actions/upload-artifact` 步骤的 `path:` 配置为 `report/` 和 `test-report.json`。事实上 `scan.py` 实际输出报告到被扫描项目下的 `.code-review/workspace/<scan_id>/report/`,artifacts 上传步骤会找不到文件。`code-review-skill` 本身没有 `report/` 目录（仅在每个扫描工作空间下存在）。
- 建议修复: 将 artifact 路径修改为工作空间路径模式,例如:
  ```yaml
  - uses: actions/upload-artifact@v4
    with:
      name: review-report
      path: |
        .code-review/workspace/*/report/
        test-report.json
  ```
  或显式使用环境变量传递 scan_id。

### 问题 2: scan.py 模块 docstring 与 epilog 中的 `--output report/` 仍存在 [LOW]
- 文件: `scripts/scan.py`
- 描述: 虽然 `scan.py` 不存在 `--output` 参数定义（已通过 `grep parser.add_argument.*--output` 验证无匹配）,但 `scan.py` 第 4 行模块 docstring 仍写 `用法: python scripts/scan.py --repo <repo-path> --base master --target release/1.0 --profile default --output report/`,第 562 行 epilog 也展示 `--output report/`。`args.output` 在整个 scan.py 中未被引用,实际是 0 个 `parser.add_argument("--output"` 定义,但模块 help 文本仍误导。用户的验证点"scan.py 是否已完全移除 --output 参数"严格来说需分两层:参数定义已移除 ✅,但内置文档字符串仍残留 ❌。
- 建议修复: 从 `scan.py` 第 4 行 docstring 和第 562 行 epilog 中移除 `--output report/`,或者保留但添加注释说明该参数已废弃、输出由工作空间自动管理。

### 问题 3: 测试文件明细统计不完整（缺少 8 个文件） [LOW]
- 文件: `docs/ai-review.md`
- 描述: 第 385-393 行的测试覆盖明细仅列出了 7 个测试文件（test_diff_analyzer.py、test_call_graph.py、test_report_generator.py、test_rule_compiler.py、test_scan.py、test_ai_reviewer.py、test_profile_completeness.py）,其它合并为"其他测试文件...：248 个测试"。但实际 `tests/` 目录还有 8 个测试文件,各文件测试数量为: `test_rule_engine.py` 49 个、`test_semgrep_integration.py` 46 个、`test_scheduler_e2e.py` 45 个、`test_scheduler.py` 33 个、`test_markdown_parser.py` 28 个、`test_ai_reviewer_e2e.py` 28 个、`test_notifier.py` 15 个、`test_harness.py` 4 个,合计 248 个。其中 `test_rule_engine.py` 49、`test_semgrep_integration.py` 46、`test_scheduler_e2e.py` 45 都不小,应单独列出。
- 建议修复: 将明细行扩展为完整 15 个文件的逐项统计,或至少补充上述 8 项明细。"248 个其他"会掩盖主要组成。

### 问题 4: Mermaid F2 节点 "待实现" 标注位置不一致 [LOW]
- 文件: `docs/ai-review.md`
- 描述: 第 191-195 行的 Mermaid 反馈层 F2 节点虽然标注了 `auto_improver.py（待实现）`,但 F1 节点同时是已实现功能（harness.py feedback 已实现）,二者并列在"反馈层"子图里会让读者误以为 F2 也已就绪。另外第 307-325 行的目录结构展示 `harness/` 只包含 `__init__.py`、`decision_logger.py`、`feedback_manager.py`、`quality_monitor.py`、`cli.py` 5 个文件,但右侧的目录树中并未列出 `auto_improver.py`（哪怕标注为"待实现"）,与上文"待实现"标注相互呼应不够明显。
- 建议修复: 可选地在 Mermaid F2 节点加底色样式（如 `style F2 fill:#ffe0e0`）以视觉上区分待实现功能;或在目录结构注释中显式标注 `auto_improver.py（待实现,待创建）` 占位条目。

---

## 总结

- 通过项: 4
- 问题数: HIGH=0, MEDIUM=1, LOW=3

**核心结论**:四个文档严谨度较高,`builtin_engine_v2.py` 状态、`auto_improver.py` 待实现标注、`data/` 目录说明、测试数量统计这四项均通过验证。主要遗留问题是 `advanced.md` 的 CI/CD 示例 artifact 路径仍按已废弃的 `report/` 配置,可能导致实际 GitHub Actions 集成时上传失败;其它三项均为低优先级文档细节。建议下一轮优先修复问题 1（CI/CD 路径）,问题 2-4 可在文档下一轮整理时一并修订。
