# 验收标准细化文档

> 基于 IMPLEMENTATION-PLAN.md 和市场调研报告，细化 Semgrep 集成、AI 增强评审、定期扫描调度三个模块的验收标准。
>
> 版本: v1.0 | 日期: 2026-07-28

---

## 目录

- [一、Semgrep 集成模块（P0）](#一semgrep-集成模块p0)
  - [AC1: Markdown 规约规则可被 Semgrep 正确执行](#ac1-markdown-规约规则可被-semgrep-正确执行)
  - [AC2: Agent-dev 仓库 XXE 漏洞检出](#ac2-agent-dev-仓库-xxe-漏洞检出)
  - [AC3: nas_backup 仓库 Python 安全风险检出](#ac3-nas_backup-仓库-python-安全风险检出)
  - [AC4: 扫描耗时性能达标](#ac4-扫描耗时性能达标)
- [二、AI 增强评审模块（P1）](#二ai-增强评审模块p1)
  - [AC1: 误报率降低 > 30%](#ai-ac1-误报率降低--30)
  - [AC2: 修复建议包含具体代码片段](#ai-ac2-修复建议包含具体代码片段)
  - [AC3: AI 评审耗时 < 60s](#ai-ac3-ai-评审耗时--60s)
  - [AC4: LLM 不可用时自动降级](#ai-ac4-llm-不可用时自动降级)
- [三、定期扫描调度模块（P2）](#三定期扫描调度模块p2)
  - [AC1: Cron 定时自动扫描](#sched-ac1-cron-定时自动扫描)
  - [AC2: 扫描完成 Webhook 通知](#sched-ac2-扫描完成-webhook-通知)
  - [AC3: 手动触发扫描](#sched-ac3-手动触发扫描)
  - [AC4: 扫描失败告警通知](#sched-ac4-扫描失败告警通知)
- [四、审计 Checklist 汇总](#四审计-checklist-汇总)

---

## 一、Semgrep 集成模块（P0）

> 对应市场调研能力域：自定义规约体系（YAML 规则 DSL）、安全漏洞检测（OWASP Top 10 全覆盖）、跨文件数据流分析。
>
> 核心实现文件：`scripts/rule_engine.py`（`MarkdownRuleParser` + `RuleEngine`）

---

### AC1: Markdown 规约规则可被 Semgrep 正确执行

**验收标准**：从 `references/security/xxe.md` 解析出的规则能被 Semgrep 正确执行，生成的 YAML 符合 Semgrep schema，且 `pattern` / `pattern-not` 代码块被正确转换。

#### 测试场景 AC1-TS1: XXE 规约解析与 Semgrep YAML 转换

**测试前置条件**：
- 环境：Python 3.9+，已安装 `pyyaml` 依赖
- Semgrep 已安装（`semgrep --version` 返回版本号）
- 规约文件 `references/security/xxe.md` 存在且内容完整（包含至少 5 条规则：`xxe-java-document-builder`、`xxe-java-sax-parser`、`xxe-java-xml-reader`、`xxe-java-unmarshaller`、`xxe-python-lxml`）

**测试步骤**：
1. 实例化 `MarkdownRuleParser`，调用 `parse_file("references/security/xxe.md")`
2. 验证返回的规则列表包含至少 5 条规则
3. 验证每条规则包含 `id`、`languages`、`severity`、`patterns` 字段
4. 验证 `xxe-java-document-builder` 规则的 `patterns` 包含 1 个 `pattern` 类型和 1 个 `pattern-not` 类型
5. 实例化 `RuleEngine`（使用 `default` profile），调用 `_rules_to_semgrep()`
6. 验证输出的 YAML 结构符合 Semgrep schema（顶层为 `rules` 列表，每条规则包含 `id`、`message`、`severity`、`languages`、`pattern`/`patterns`）
7. 将生成的 YAML 写入临时文件，执行 `semgrep --config <temp_file> --validate` 验证规则合法性

**预期结果**：
- `parse_file()` 返回规则数量 >= 5
- `xxe-java-document-builder` 规则的 patterns 数量 = 2（1 个 pattern + 1 个 pattern-not）
- `_rules_to_semgrep()` 输出的 YAML 通过 `semgrep --validate` 校验（exit code = 0）
- 每条 Semgrep 规则的 `languages` 字段与原始规则一致（`[java]` 或 `[python]`）

**测试数据准备**：
- 规约文件：`references/security/xxe.md`（已存在，包含 XXE 相关 6 条规则）
- Profile 配置：`references/profiles/default.yaml`（已存在，`security/*.yaml` 路径启用）

**自动化实现提示**：
```python
# tests/test_semgrep_integration.py::test_xxe_rule_parsing_and_semgrep_yaml
def test_xxe_rule_parsing_and_semgrep_yaml():
    parser = MarkdownRuleParser()
    rules = parser.parse_file("references/security/xxe.md")
    assert len(rules) >= 5
    # 验证 pattern/pattern-not 结构
    doc_builder_rule = next(r for r in rules if r["id"] == "xxe-java-document-builder")
    pattern_types = [p["type"] for p in doc_builder_rule["patterns"]]
    assert "pattern" in pattern_types
    assert "pattern-not" in pattern_types
    # 验证 Semgrep YAML 转换
    engine = RuleEngine(specs_dir="references", profile=load_profile("default"))
    semgrep_rules = engine._rules_to_semgrep()
    assert "rules" in semgrep_rules
    assert len(semgrep_rules["rules"]) >= 5
    # 验证 Semgrep 可接受（需要 semgrep 安装）
    # subprocess.run(["semgrep", "--config", temp_file, "--validate"])
```

---

#### 测试场景 AC1-TS2: 多规约文件批量解析与规则完整性

**测试前置条件**：
- 环境：同 AC1-TS1
- `references/security/` 目录下存在 8 个 Markdown 规约文件（xxe.md、xss.md、authorization.md、path-traversal.md、privilege-escalation.md、signature-bypass.md、sql-injection.md、ssrf.md）
- `references/implementation/` 目录下存在 4 个 Markdown 规约文件
- `references/design/` 目录下存在 2 个 Markdown 规约文件

**测试步骤**：
1. 使用 `default` profile 实例化 `RuleEngine`
2. 验证 `_load_rules()` 加载的规则总数 >= 30（安全规约约 30 条 + 实现规约约 10 条 + 设计规约约 5 条）
3. 验证每条规则都包含 `id` 字段且不为空
4. 验证所有规则的 `id` 无重复
5. 调用 `_rules_to_semgrep()` 后验证每条 Semgrep 规则都包含 `pattern` 或 `patterns` 字段
6. 验证安全类规则的 `severity` 为 `ERROR`（按 `default` profile 配置）

**预期结果**：
- 总规则数量 >= 30
- 规则 ID 无重复（`len(set(ids)) == len(ids)`）
- 所有规则的 `pattern`/`patterns` 字段非空
- 安全规约的 severity 全部为 `ERROR`

**测试数据准备**：
- 规约目录：`references/`（完整目录结构）
- Profile 配置：`references/profiles/default.yaml`

**自动化实现提示**：
```python
# tests/test_semgrep_integration.py::test_multi_spec_batch_parsing
def test_multi_spec_batch_parsing():
    profile = load_profile("default", "references")
    engine = RuleEngine(specs_dir="references", profile=profile)
    assert len(engine.rules) >= 30
    rule_ids = [r["id"] for r in engine.rules if r.get("id")]
    assert len(set(rule_ids)) == len(rule_ids), "存在重复规则 ID"
    semgrep_rules = engine._rules_to_semgrep()
    for rule in semgrep_rules["rules"]:
        assert "pattern" in rule or "patterns" in rule
```

---

#### 测试场景 AC1-TS3: Semgrep JSON 输出解析与结构化问题生成

**测试前置条件**：
- 环境：同 AC1-TS1
- 准备一个包含已知 XXE 漏洞的临时 Java 文件（从 `references/test-cases/security/xxe-test.md` 中提取违规代码样本）

**测试步骤**：
1. 在临时目录创建 `VulnerableParser.java`，内容为 xxe-test.md 中的违规代码（`DocumentBuilderFactory` 未禁用外部实体）
2. 使用 `RuleEngine._run_with_semgrep()` 扫描该临时目录
3. 验证返回的问题列表非空
4. 验证每个问题包含完整字段：`rule_id`、`category`、`severity`、`file`、`line`、`end_line`、`message`、`code_snippet`
5. 验证命中规则 ID 为 `xxe-java-document-builder`
6. 验证 `category` 字段为 `security`（通过 `_get_category()` 推断）

**预期结果**：
- 问题列表长度 >= 1
- 第一个问题的 `rule_id` == `xxe-java-document-builder`
- 第一个问题的 `severity` == `ERROR`
- 第一个问题的 `category` == `security`
- `code_snippet` 包含 `DocumentBuilderFactory` 关键字

**测试数据准备**：
- 测试代码文件来源：`references/test-cases/security/xxe-test.md` 第一段违规代码
- 临时 Java 文件：`/tmp/test-ac1/VulnerableParser.java`

---

### AC2: Agent-dev 仓库 XXE 漏洞检出

**验收标准**：对 Agent-dev 仓库扫描，能检出 XXE 漏洞（预期命中 `xxe-java-document-builder`），且检出数量 >= 2。

#### 测试场景 AC2-TS1: agentserver 仓库 XXE 全量扫描

**测试前置条件**：
- 环境：Python 3.9+，Semgrep 已安装
- agentserver 仓库已 clone 到本地（路径通过环境变量 `AGENTSERVER_REPO` 配置，默认 `./repos/agentserver`）
- 仓库中包含 Java 源文件（`.java`）
- `references/security/xxe.md` 规约文件可用

**测试步骤**：
1. 实例化 `RuleEngine`，加载 `default` profile（包含 `security/*.md` 规则）
2. 调用 `engine.run(repo_path=agentserver_repo, changed_files=all_java_files)`
3. 从结果中筛选 `rule_id` 以 `xxe-java-` 开头的问题
4. 统计各规则的命中数量
5. 验证 `xxe-java-document-builder` 命中数量 >= 2
6. 验证所有 XXE 问题的 `severity` == `ERROR`
7. 验证每个问题的 `file` 字段指向实际存在的 `.java` 文件

**预期结果**：
- XXE 相关检出总数 >= 2
- `xxe-java-document-builder` 规则至少命中 2 处
- 所有 XXE 问题的 severity 为 `ERROR`
- 每个问题的文件路径在仓库中真实存在

**测试数据准备**：
- 版本库：agentserver（Java 项目）
- 扫描范围：全仓库 `.java` 文件
- 规约：`references/security/xxe.md`

**自动化实现提示**：
```python
# tests/test_semgrep_integration.py::test_agentserver_xxe_detection
@pytest.mark.skipif(not is_semgrep_available(), reason="Semgrep not installed")
def test_agentserver_xxe_detection():
    repo_path = os.environ.get("AGENTSERVER_REPO", "./repos/agentserver")
    if not os.path.isdir(repo_path):
        pytest.skip("agentserver repo not available")
    profile = load_profile("default", "references")
    engine = RuleEngine(specs_dir="references", profile=profile)
    java_files = [{"path": f} for f in find_java_files(repo_path)]
    issues = engine.run(repo_path, java_files)
    xxe_issues = [i for i in issues if i["rule_id"].startswith("xxe-java-")]
    assert len(xxe_issues) >= 2, f"Expected >= 2 XXE issues, got {len(xxe_issues)}"
    doc_builder_hits = [i for i in xxe_issues if i["rule_id"] == "xxe-java-document-builder"]
    assert len(doc_builder_hits) >= 2
```

---

#### 测试场景 AC2-TS2: agentserver 仓库签名绕过检出

**测试前置条件**：
- 同 AC2-TS1
- agentserver 仓库中包含签名相关代码（使用 `MD5withRSA` 等弱算法或硬编码密钥）

**测试步骤**：
1. 实例化 `RuleEngine`，加载 `default` profile
2. 调用 `engine.run()` 扫描 agentserver 仓库
3. 从结果中筛选 `rule_id` 以 `sig-java-` 开头的问题
4. 验证签名绕过检出数量 >= 1
5. 验证命中规则包含 `sig-java-weak-algorithm` 或 `sig-java-hardcoded-key`

**预期结果**：
- 签名绕过相关检出 >= 1
- 命中规则 ID 属于 `{sig-java-weak-algorithm, sig-java-hardcoded-key}` 之一

**测试数据准备**：
- 版本库：agentserver（Java 项目）
- 规约：`references/security/signature-bypass.md`

---

#### 测试场景 AC2-TS3: 测试案例库精确匹配验证

**测试前置条件**：
- 环境：同 AC2-TS1
- 测试案例目录 `references/test-cases/security/` 可用
- 从每个测试案例 `.md` 文件中提取违规代码样本，生成对应的源语言临时文件

**测试步骤**：
1. 遍历 `references/test-cases/security/` 下所有 `-test.md` 文件
2. 对每个文件，提取所有"违规代码"块及其预期命中规则 ID
3. 将违规代码写入临时文件（按语言选择扩展名：`.java`、`.py`、`.js`）
4. 使用 `RuleEngine` 扫描临时目录
5. 验证每个违规代码样本至少命中预期规则
6. 同时提取"正确代码"块，验证不命中任何规则

**预期结果**：
- 违规代码样本命中率 = 100%（每个违规样本至少命中 1 条预期规则）
- 正确代码样本误命中率 = 0%（不应命中任何规则）

**测试数据准备**：
- 测试案例：`references/test-cases/security/xxe-test.md`、`xss-test.md`、`privilege-escalation-test.md`、`path-traversal-test.md`、`signature-bypass-test.md`、`ssrf-test.md`、`sql-injection-test.md`、`authorization-test.md`

---

### AC3: nas_backup 仓库 Python 安全风险检出

**验收标准**：对 nas_backup 仓库扫描，能检出 Python 安全风险（eval/os.system），检出数量 >= 3。

#### 测试场景 AC3-TS1: nas_backup 仓库提权漏洞扫描

**测试前置条件**：
- 环境：Python 3.9+，Semgrep 已安装
- nas_backup 仓库已 clone 到本地（路径通过环境变量 `NAS_BACKUP_REPO` 配置，默认 `./repos/nas_backup`）
- 仓库中包含 Python 源文件（`.py`）

**测试步骤**：
1. 实例化 `RuleEngine`，加载 `default` profile
2. 调用 `engine.run(repo_path=nas_backup_repo, changed_files=all_python_files)`
3. 从结果中筛选 `rule_id` 以 `priv-python-` 开头的问题
4. 统计各规则命中数量：`priv-python-eval`、`priv-python-os-system`、`priv-python-exec`、`priv-python-subprocess-shell`
5. 验证提权类问题总数 >= 3
6. 验证至少命中 `priv-python-eval` 和 `priv-python-os-system` 中的各 1 个

**预期结果**：
- Python 提权类问题总数 >= 3
- `priv-python-eval` 命中 >= 1
- `priv-python-os-system` 命中 >= 1

**测试数据准备**：
- 版本库：nas_backup（Python 项目）
- 扫描范围：全仓库 `.py` 文件
- 规约：`references/security/privilege-escalation.md`

**自动化实现提示**：
```python
# tests/test_semgrep_integration.py::test_nas_backup_python_security_detection
@pytest.mark.skipif(not is_semgrep_available(), reason="Semgrep not installed")
def test_nas_backup_python_security_detection():
    repo_path = os.environ.get("NAS_BACKUP_REPO", "./repos/nas_backup")
    if not os.path.isdir(repo_path):
        pytest.skip("nas_backup repo not available")
    profile = load_profile("default", "references")
    engine = RuleEngine(specs_dir="references", profile=profile)
    py_files = [{"path": f} for f in find_python_files(repo_path)]
    issues = engine.run(repo_path, py_files)
    priv_issues = [i for i in issues if i["rule_id"].startswith("priv-python-")]
    assert len(priv_issues) >= 3, f"Expected >= 3 Python priv issues, got {len(priv_issues)}"
    eval_hits = [i for i in priv_issues if i["rule_id"] == "priv-python-eval"]
    os_system_hits = [i for i in priv_issues if i["rule_id"] == "priv-python-os-system"]
    assert len(eval_hits) >= 1
    assert len(os_system_hits) >= 1
```

---

#### 测试场景 AC3-TS2: nas_backup 仓库路径穿越与 SSRF 扫描

**测试前置条件**：
- 同 AC3-TS1
- nas_backup 仓库中包含文件操作（`open()`）或网络请求（`requests.get()`）相关代码

**测试步骤**：
1. 实例化 `RuleEngine`，加载 `default` profile
2. 调用 `engine.run()` 扫描 nas_backup 仓库
3. 从结果中筛选 `rule_id` 以 `path-python-` 或 `ssrf-python-` 开头的问题
4. 验证路径穿越或 SSRF 类问题至少命中 1 个
5. 验证问题的 `file` 字段指向 `.py` 文件
6. 验证问题的 `code_snippet` 包含相关危险函数调用（`open(` 或 `requests.get(`）

**预期结果**：
- 路径穿越 + SSRF 类问题总数 >= 1
- 所有问题的文件类型为 `.py`

**测试数据准备**：
- 版本库：nas_backup（Python 项目）
- 规约：`references/security/path-traversal.md`、`references/security/ssrf.md`

---

#### 测试场景 AC3-TS3: opencode 仓库 TypeScript 安全风险扫描

**测试前置条件**：
- 环境：Python 3.9+，Semgrep 已安装
- opencode 仓库已 clone 到本地（路径通过环境变量 `OPENCODE_REPO` 配置，默认 `./repos/opencode`）
- 仓库中包含 TypeScript/JavaScript 源文件

**测试步骤**：
1. 实例化 `RuleEngine`，加载 `default` profile
2. 调用 `engine.run()` 扫描 opencode 仓库
3. 从结果中筛选 `rule_id` 以 `xss-js-` 或 `priv-js-` 或 `ssrf-js-` 开头的问题
4. 验证 XSS/提权/SSRF 类问题总数 >= 2
5. 验证至少命中以下规则之一：`xss-js-innerhtml`、`xss-js-eval`、`priv-js-child-process`

**预期结果**：
- TypeScript/JavaScript 安全问题总数 >= 2
- 至少命中 `xss-js-innerhtml` 或 `xss-js-eval` 之一

**测试数据准备**：
- 版本库：opencode（TypeScript 项目）
- 扫描范围：全仓库 `.ts`、`.js` 文件
- 规约：`references/security/xss.md`、`references/security/privilege-escalation.md`、`references/security/ssrf.md`

---

### AC4: 扫描耗时性能达标

**验收标准**：扫描耗时 < 30s（单仓库 < 1000 文件），内存占用 < 512MB。

#### 测试场景 AC4-TS1: 单仓库扫描性能基准测试

**测试前置条件**：
- 环境：Python 3.9+，Semgrep 已安装
- 任一测试仓库（agentserver / nas_backup / opencode）可用
- 仓库文件数量 < 1000

**测试步骤**：
1. 记录开始时间 `t0 = time.time()`
2. 实例化 `RuleEngine`，加载 `default` profile
3. 调用 `engine.run()` 扫描目标仓库
4. 记录结束时间 `t1 = time.time()`
5. 计算耗时 `duration = t1 - t0`
6. 验证 `duration < 30` 秒
7. 使用 `tracemalloc` 或 `resource` 模块监控峰值内存，验证 < 512MB

**预期结果**：
- 扫描耗时 < 30 秒
- 峰值内存占用 < 512MB
- 扫描结果非空（验证功能正常的同时测量性能）

**测试数据准备**：
- 版本库：nas_backup（文件数量相对较少，适合性能基准测试）
- 如无真实仓库，使用 `references/test-cases/` 下所有测试案例生成的临时目录

**自动化实现提示**：
```python
# tests/test_semgrep_integration.py::test_scan_performance
@pytest.mark.skipif(not is_semgrep_available(), reason="Semgrep not installed")
def test_scan_performance():
    repo_path = os.environ.get("NAS_BACKUP_REPO", "./repos/nas_backup")
    if not os.path.isdir(repo_path):
        pytest.skip("nas_backup repo not available")
    file_count = count_files(repo_path)
    if file_count > 1000:
        pytest.skip(f"Repo has {file_count} files, exceeds 1000 limit")
    profile = load_profile("default", "references")
    engine = RuleEngine(specs_dir="references", profile=profile)
    all_files = [{"path": f} for f in find_all_source_files(repo_path)]
    start = time.time()
    issues = engine.run(repo_path, all_files)
    duration = time.time() - start
    assert duration < 30, f"Scan took {duration:.1f}s, exceeds 30s limit"
    assert len(issues) > 0, "Expected some issues to be found"
```

---

#### 测试场景 AC4-TS2: Semgrep 不可用时的降级性能测试

**测试前置条件**：
- 环境：Python 3.9+，**Semgrep 未安装**（或 PATH 中不可用）
- 测试仓库可用

**测试步骤**：
1. 确认 `semgrep` 命令不可用（`_semgrep_available()` 返回 `False`）
2. 记录开始时间
3. 使用内置模式匹配引擎（`_run_with_builtin()`）扫描目标仓库
4. 记录结束时间
5. 验证内置引擎扫描耗时 < 30 秒（内置引擎应比 Semgrep 更快）
6. 验证结果非空

**预期结果**：
- 内置引擎扫描耗时 < 30 秒
- 扫描结果非空（可能比 Semgrep 结果少，但核心问题应能检出）
- 无异常抛出

**测试数据准备**：
- 版本库：nas_backup 或任意包含 Python 文件的目录
- 无需 Semgrep 安装

---

#### 测试场景 AC4-TS3: Semgrep 超时处理

**测试前置条件**：
- 环境：Python 3.9+，Semgrep 已安装
- 配置 `semgrep.timeout` 为一个极短的时间（如 1 秒），或使用一个超大仓库

**测试步骤**：
1. 修改配置将 Semgrep 超时设为 1 秒（`config.yaml` 中 `semgrep.timeout: 1`）
2. 调用 `engine.run()` 扫描一个较大仓库
3. 验证 `subprocess.TimeoutExpired` 被捕获
4. 验证返回空列表（而非抛出异常）
5. 验证日志中记录了 "Semgrep 扫描超时" 错误信息

**预期结果**：
- 超时时不抛出未处理异常
- 返回空问题列表 `[]`
- 日志包含超时警告信息

**测试数据准备**：
- 配置文件：临时修改的 `config.yaml`（`semgrep.timeout: 1`）
- 版本库：任意可用仓库

---

## 二、AI 增强评审模块（P1）

> 对应市场调研能力域：AI 辅助评审（参考 Open Code Review 的确定性 + Agent 混合架构，误报率 11%）。
>
> 核心实现文件：`scripts/ai_reviewer.py`（`AIReviewer`）

---

### AI-AC1: 误报率降低 > 30%

**验收标准**：对 Semgrep 扫描结果调用 AI 评审，误报率降低 > 30%。

#### 测试场景 AI-AC1-TS1: Mock LLM 误报过滤效果验证

**测试前置条件**：
- 环境：Python 3.9+，无需真实 LLM API
- 准备一组包含已知误报的扫描结果（至少 10 个问题，其中 5 个为真实问题，5 个为误报）
- Mock LLM API 响应：对真实问题返回 `is_valid: true, confidence: 0.9`，对误报返回 `is_valid: false, confidence: 0.2`

**测试步骤**：
1. 构造 10 个模拟问题（5 个真实 + 5 个误报），每个问题包含 `rule_id`、`file`、`line`、`message`、`code_snippet`
2. 构造 `diff_result` 和 `call_graph` 模拟数据
3. Mock `AIReviewer._call_llm()` 方法，返回预定义的 JSON 响应
4. 调用 `ai_reviewer.review(issues, diff_result, call_graph)`
5. 统计过滤后的问题数量
6. 计算误报率降低比例：`(原始误报数 - 剩余误报数) / 原始误报数`
7. 验证误报率降低 > 30%

**预期结果**：
- AI 评审后剩余问题数 <= 7（过滤掉至少 3 个误报）
- 误报率降低比例 > 30%
- 真实问题（`is_valid: true`）全部保留

**测试数据准备**：
- 模拟扫描结果：基于 `references/test-cases/security/xxe-test.md` 中的违规代码和正确代码构造
- Mock 响应：硬编码的 JSON 数组

**自动化实现提示**：
```python
# tests/test_ai_reviewer_e2e.py::test_false_positive_reduction
def test_false_positive_reduction():
    # 构造 10 个问题（5 真实 + 5 误报）
    issues = build_test_issues(count=10, real_count=5)
    # Mock LLM 响应
    mock_response = build_mock_ai_response(issues, real_indices=[0,1,2,3,4])
    reviewer = AIReviewer(config={"llm": {"url": "http://mock", "api_key_env": "TEST_KEY"}, "confidence_threshold": 0.7})
    with patch.object(reviewer, '_call_llm', return_value=mock_response):
        os.environ["TEST_KEY"] = "test-key"
        result = reviewer.review(issues, mock_diff_result(), mock_call_graph())
    assert len(result) <= 7
    # 误报率降低 > 30%
    fp_reduction = (5 - (len(result) - 5)) / 5  # 简化计算
    assert fp_reduction > 0.3
```

---

#### 测试场景 AI-AC1-TS2: 不同置信度阈值下的过滤效果

**测试前置条件**：
- 同 AI-AC1-TS1
- Mock LLM 返回不同置信度分数（0.3、0.5、0.7、0.9）

**测试步骤**：
1. 构造 5 个问题，Mock LLM 返回的置信度分别为 0.3、0.5、0.7、0.9、0.95
2. 设置 `confidence_threshold = 0.7`
3. 调用 `ai_reviewer.review()`
4. 验证只有置信度 >= 0.7 的问题被保留（3 个）
5. 修改 `confidence_threshold = 0.5`，重新执行
6. 验证只有置信度 >= 0.5 的问题被保留（4 个）

**预期结果**：
- `threshold=0.7` 时，保留 3 个问题（置信度 0.7、0.9、0.95）
- `threshold=0.5` 时，保留 4 个问题（置信度 0.5、0.7、0.9、0.95）
- 过滤行为严格按阈值执行

**测试数据准备**：
- 模拟问题列表（5 个）
- Mock LLM 响应（不同置信度）

---

### AI-AC2: 修复建议包含具体代码片段

**验收标准**：AI 生成的修复建议包含具体代码片段（非纯文本描述）。

#### 测试场景 AI-AC2-TS1: AI 修复建议代码片段验证

**测试前置条件**：
- 环境：Python 3.9+
- 准备 3 个已知安全问题（XXE、提权、XSS 各 1 个）
- Mock LLM 返回包含代码片段的 `enhanced_fix` 字段

**测试步骤**：
1. 构造 3 个问题（`xxe-java-document-builder`、`priv-python-eval`、`xss-js-innerhtml`）
2. Mock LLM 响应，每个问题的 `enhanced_fix` 包含代码片段（如 `factory.setFeature(...)` 等）
3. 调用 `ai_reviewer.review()`
4. 验证每个问题的 `fix` 字段被更新为 AI 增强版本
5. 验证 `fix` 字段包含代码特征（如 `{`、`}`、`(`、`)`、`;` 等代码符号，或长度 > 50 字符）
6. 统计包含代码片段的修复建议占比

**预期结果**：
- 100% 的修复建议包含代码片段（3/3）
- 每个 `fix` 字段至少包含 1 行可识别的代码（含缩进、函数调用等）

**测试数据准备**：
- 模拟问题：基于 `references/test-cases/security/` 中的违规代码
- Mock LLM 响应：参考规约文件中的"正确示例"代码作为 `enhanced_fix`

---

#### 测试场景 AI-AC2-TS2: 原始规则 fix 字段保留与增强

**测试前置条件**：
- 环境：Python 3.9+
- 准备 1 个问题，其原始规则已包含 `fix` 字段（来自 `references/security/xxe.md` 中 `xxe-java-document-builder` 的修复代码）
- Mock LLM 返回新的 `enhanced_fix`

**测试步骤**：
1. 构造 1 个问题，设置原始 `fix` 为规约中定义的修复代码
2. Mock LLM 返回不同的 `enhanced_fix`
3. 调用 `ai_reviewer.review()`
4. 验证问题的 `fix` 被更新为 AI 增强版本（而非保留原始版本）
5. 再次测试：Mock LLM 返回空的 `enhanced_fix`
6. 验证问题的 `fix` 保留原始值

**预期结果**：
- 当 AI 提供增强修复时，`fix` 字段被更新
- 当 AI 未提供增强修复时，原始 `fix` 字段不被覆盖

**测试数据准备**：
- 原始 fix 来源：`references/security/xxe.md` 中 `xxe-java-document-builder` 的 `fix` 字段

---

### AI-AC3: AI 评审耗时 < 60s

**验收标准**：AI 评审耗时 < 60s（批量 20 个问题）。

#### 测试场景 AI-AC3-TS1: 批量 20 问题 AI 评审性能测试

**测试前置条件**：
- 环境：Python 3.9+
- 准备 20 个模拟安全问题
- Mock LLM API（设置响应延迟 50ms 模拟网络延迟）

**测试步骤**：
1. 构造 20 个模拟问题
2. Mock `_call_llm()` 方法，每次调用延迟 50ms 后返回预定义 JSON
3. 记录开始时间
4. 调用 `ai_reviewer.review(issues, diff_result, call_graph)`
5. 记录结束时间
6. 验证总耗时 < 60 秒
7. 验证 LLM 被调用的次数（20 个问题应分 1 批，batch_size=20）

**预期结果**：
- 总耗时 < 60 秒（Mock 场景下应 < 5 秒）
- LLM 调用次数 = 1（20 个问题在 1 个批次内）

**测试数据准备**：
- 20 个模拟问题（混合安全类别）

**自动化实现提示**：
```python
# tests/test_ai_reviewer_e2e.py::test_ai_review_performance
def test_ai_review_performance():
    issues = build_test_issues(count=20)
    reviewer = AIReviewer(config={"llm": {"url": "http://mock", "api_key_env": "TEST_KEY"}, "confidence_threshold": 0.7})
    mock_resp = build_mock_ai_response(issues)
    def slow_call_llm(prompt):
        time.sleep(0.05)
        return mock_resp
    with patch.object(reviewer, '_call_llm', side_effect=slow_call_llm):
        os.environ["TEST_KEY"] = "test-key"
        start = time.time()
        result = reviewer.review(issues, mock_diff_result(), mock_call_graph())
        duration = time.time() - start
    assert duration < 60, f"AI review took {duration:.1f}s, exceeds 60s limit"
```

---

#### 测试场景 AI-AC3-TS2: 超大批量（50 问题）分批处理验证

**测试前置条件**：
- 同 AI-AC3-TS1
- 准备 50 个模拟问题（超过 batch_size=20）

**测试步骤**：
1. 构造 50 个模拟问题
2. Mock `_call_llm()` 方法
3. 调用 `ai_reviewer.review()`
4. 验证 LLM 被调用 3 次（50 / 20 = 2.5，向上取整为 3 批）
5. 验证总耗时 < 60 秒
6. 验证所有 50 个问题都被处理（结果列表中的问题来自所有批次）

**预期结果**：
- LLM 调用次数 = 3（批次 20 + 20 + 10）
- 总耗时 < 60 秒
- 所有问题均被处理

**测试数据准备**：
- 50 个模拟问题

---

### AI-AC4: LLM 不可用时自动降级

**验收标准**：LLM 不可用时自动降级，返回原始结果。

#### 测试场景 AI-AC4-TS1: 无 API Key 时降级

**测试前置条件**：
- 环境：Python 3.9+
- 环境变量中**未设置** `OPENAI_API_KEY`
- 配置 `ai_review.llm.api_key_env: "OPENAI_API_KEY"`

**测试步骤**：
1. 确保 `os.environ` 中不包含 `OPENAI_API_KEY`
2. 实例化 `AIReviewer`，配置中包含 `api_key_env: "OPENAI_API_KEY"`
3. 调用 `_is_available()`
4. 验证返回 `False`
5. 准备 5 个模拟问题
6. 调用 `ai_reviewer.review(issues, diff_result, call_graph)`
7. 验证返回的问题列表与输入完全一致（未做任何过滤）
8. 验证日志中包含 "AI 评审不可用" 警告信息

**预期结果**：
- `_is_available()` 返回 `False`
- `review()` 返回与输入相同的问题列表（`len(result) == len(issues)`）
- 返回的问题内容与输入完全一致（未被过滤或修改）

**测试数据准备**：
- 无需真实 API Key
- 5 个模拟问题

**自动化实现提示**：
```python
# tests/test_ai_reviewer_e2e.py::test_llm_unavailable_fallback
def test_llm_unavailable_fallback():
    os.environ.pop("OPENAI_API_KEY", None)
    reviewer = AIReviewer(config={"llm": {"url": "http://api.openai.com", "api_key_env": "OPENAI_API_KEY"}})
    assert reviewer._is_available() == False
    issues = build_test_issues(count=5)
    result = reviewer.review(issues, mock_diff_result(), mock_call_graph())
    assert len(result) == len(issues)
    assert result == issues  # 完全一致
```

---

#### 测试场景 AI-AC4-TS2: LLM API 超时/异常时降级

**测试前置条件**：
- 环境：Python 3.9+
- API Key 已配置（`_is_available()` 返回 `True`）
- Mock `_call_llm()` 抛出异常（模拟网络超时）

**测试步骤**：
1. 配置有效的 API Key 环境变量
2. 实例化 `AIReviewer`
3. Mock `_call_llm()` 方法抛出 `urllib.error.URLError("Connection timed out")`
4. 准备 5 个模拟问题
5. 调用 `ai_reviewer.review()`
6. 验证返回的问题列表与输入完全一致（降级为原始结果）
7. 验证日志中包含 "LLM 调用失败" 错误信息

**预期结果**：
- 异常不向上传播
- 返回原始问题列表（5 个问题全部保留）
- 日志记录了 LLM 调用失败的信息

**测试数据准备**：
- Mock 异常：`urllib.error.URLError`
- 5 个模拟问题

---

#### 测试场景 AI-AC4-TS3: LLM 返回无效 JSON 时降级

**测试前置条件**：
- 环境：Python 3.9+
- API Key 已配置
- Mock `_call_llm()` 返回无效 JSON 字符串

**测试步骤**：
1. Mock `_call_llm()` 返回 `"This is not a JSON response"`
2. 准备 5 个模拟问题
3. 调用 `ai_reviewer.review()`
4. 验证 `_parse_response()` 捕获 `json.JSONDecodeError`
5. 验证返回原始问题列表
6. 验证日志中包含 "AI 响应解析失败" 警告信息

**预期结果**：
- JSON 解析失败时不抛出异常
- 返回原始问题列表
- 日志记录了 JSON 解析失败的信息

**测试数据准备**：
- Mock LLM 响应：`"This is not a JSON response"`（无效 JSON）

---

## 三、定期扫描调度模块（P2）

> 对应市场调研能力域：定期扫描调度（CI 定时触发、Webhook 事件触发）、结果聚合展示。
>
> 核心实现文件（待实现）：`scripts/scheduler.py`、`scripts/notifier.py`

---

### SCHED-AC1: Cron 定时自动扫描

**验收标准**：配置 `schedule.cron: "0 2 * * *"` 后，每天凌晨 2 点自动扫描。

#### 测试场景 SCHED-AC1-TS1: Cron 表达式解析与下次执行时间计算

**测试前置条件**：
- 环境：Python 3.9+
- `scripts/scheduler.py` 已实现 `Scheduler` 类
- 配置文件 `config.yaml` 中 `schedule.cron: "0 2 * * *"`

**测试步骤**：
1. 实例化 `Scheduler`，传入配置 `{"schedule": {"cron": "0 2 * * *"}}`
2. 调用 `Scheduler.parse_cron("0 2 * * *")`
3. 验证解析结果：`minute=0, hour=2, day_of_month=*, month=*, day_of_week=*`
4. 调用 `scheduler.get_next_run_time()` 获取下次执行时间
5. 验证下次执行时间的 `hour == 2` 且 `minute == 0`
6. 验证下次执行时间 > 当前时间

**预期结果**：
- Cron 表达式被正确解析为 5 个字段
- 下次执行时间为最近的凌晨 2:00
- 解析结果与标准 cron 语义一致

**测试数据准备**：
- 配置：`{"schedule": {"cron": "0 2 * * *"}}`

**自动化实现提示**：
```python
# tests/test_scheduler.py::test_parse_cron_expression
def test_parse_cron_expression():
    scheduler = Scheduler(config={"schedule": {"cron": "0 2 * * *"}})
    cron = scheduler.parse_cron("0 2 * * *")
    assert cron.minute == 0
    assert cron.hour == 2
    assert cron.day_of_month == "*"
    assert cron.month == "*"
    assert cron.day_of_week == "*"
    next_run = scheduler.get_next_run_time()
    assert next_run.hour == 2
    assert next_run.minute == 0
    assert next_run > datetime.now()
```

---

#### 测试场景 SCHED-AC1-TS2: 无效 Cron 表达式错误处理

**测试前置条件**：
- 同 SCHED-AC1-TS1

**测试步骤**：
1. 实例化 `Scheduler`
2. 调用 `Scheduler.parse_cron("invalid cron")`
3. 验证抛出 `ValueError` 或返回错误信息
4. 调用 `Scheduler.parse_cron("60 25 32 13 8")`（超出范围的值）
5. 验证抛出 `ValueError` 或返回错误信息
6. 调用 `Scheduler.parse_cron("")`（空字符串）
7. 验证抛出 `ValueError`

**预期结果**：
- 无效格式：抛出 `ValueError`，消息包含 "Invalid cron expression"
- 超出范围：抛出 `ValueError`，消息包含具体字段名
- 空字符串：抛出 `ValueError`

**测试数据准备**：
- 无效 Cron 表达式列表：`["invalid cron", "60 25 32 13 8", ""]`

---

#### 测试场景 SCHED-AC1-TS3: Cron 定时触发扫描执行

**测试前置条件**：
- 环境：Python 3.9+
- `Scheduler` 类和 `ScanRunner` 类已实现
- 使用 `unittest.mock` 模拟扫描执行

**测试步骤**：
1. 实例化 `Scheduler`，配置 cron 为每分钟执行（`"* * * * *"`）
2. Mock `ScanRunner.run()` 方法
3. 启动调度器（`scheduler.start()`），使用线程或 asyncio
4. 等待最多 90 秒（等待 cron 触发）
5. 验证 `ScanRunner.run()` 被调用至少 1 次
6. 停止调度器（`scheduler.stop()`）

**预期结果**：
- `ScanRunner.run()` 在 cron 触发时被调用
- 调用次数 >= 1
- 调度器可正常停止

**测试数据准备**：
- 配置：`{"schedule": {"cron": "* * * * *"}}`（每分钟触发，用于测试）
- Mock 的 `ScanRunner`

---

### SCHED-AC2: 扫描完成 Webhook 通知

**验收标准**：配置 `schedule.notify: true` 后，扫描完成发送 Webhook 通知。

#### 测试场景 SCHED-AC2-TS1: Webhook 通知发送成功

**测试前置条件**：
- 环境：Python 3.9+
- `scripts/notifier.py` 已实现 `Notifier` 类
- 配置 `schedule.notify: true`，`schedule.notify_method: "webhook"`，`schedule.notify_target: "http://localhost:9999/webhook"`
- 使用 `http.server` 或 Mock 启动本地 Webhook 接收服务

**测试步骤**：
1. 启动本地 HTTP 服务（端口 9999），记录收到的请求
2. 实例化 `Notifier`，传入配置
3. 构造扫描结果数据（包含 `total_issues: 5, critical: 2, high: 3`）
4. 调用 `notifier.send_webhook(scan_result)`
5. 验证 HTTP 请求已发送（本地服务收到 1 个 POST 请求）
6. 验证请求方法为 `POST`
7. 验证请求 `Content-Type` 为 `application/json`
8. 验证请求体包含扫描结果数据（`total_issues`、`critical`、`high`）

**预期结果**：
- 本地服务收到 1 个 POST 请求
- `Content-Type` == `application/json`
- 请求体 JSON 包含 `total_issues: 5`、`critical: 2`

**测试数据准备**：
- 本地 Webhook 接收服务（`http://localhost:9999/webhook`）
- 模拟扫描结果：`{"total_issues": 5, "critical": 2, "high": 3, "repo": "agentserver"}`

**自动化实现提示**：
```python
# tests/test_notifier.py::test_send_webhook_success
def test_send_webhook_success():
    received_requests = []
    server = start_mock_webhook(port=9999, received=received_requests)
    try:
        notifier = Notifier(config={"notify_method": "webhook", "notify_target": "http://localhost:9999/webhook"})
        scan_result = {"total_issues": 5, "critical": 2, "high": 3, "repo": "agentserver"}
        notifier.send_webhook(scan_result)
        assert len(received_requests) == 1
        req = received_requests[0]
        assert req["method"] == "POST"
        assert "application/json" in req["content_type"]
        assert req["body"]["total_issues"] == 5
    finally:
        server.stop()
```

---

#### 测试场景 SCHED-AC2-TS2: Webhook 目标不可达时的错误处理

**测试前置条件**：
- 环境：Python 3.9+
- Webhook 目标 URL 不可达（如 `http://localhost:19999/webhook`，端口未监听）

**测试步骤**：
1. 实例化 `Notifier`，配置目标为不可达 URL
2. 调用 `notifier.send_webhook(scan_result)`
3. 验证不抛出未处理异常
4. 验证日志中包含 "Webhook 发送失败" 错误信息
5. 验证方法返回 `False` 或错误状态

**预期结果**：
- 不抛出未处理异常（`ConnectionRefusedError` 被捕获）
- 日志记录了发送失败信息
- 返回失败状态

**测试数据准备**：
- 不可达 URL：`http://localhost:19999/webhook`

---

#### 测试场景 SCHED-AC2-TS3: Webhook 通知内容格式验证

**测试前置条件**：
- 同 SCHED-AC2-TS1
- 准备包含完整字段的扫描报告

**测试步骤**：
1. 构造完整扫描报告（包含 `scan_info`、`issues`、`summary`）
2. 调用 `notifier.send_webhook(scan_result)`
3. 验证请求体 JSON 包含以下字段：
   - `timestamp`（ISO 8601 格式）
   - `repo`（仓库名称）
   - `total_issues`（总问题数）
   - `critical_count`、`high_count`、`medium_count`、`low_count`
   - `top_issues`（前 5 个最严重问题摘要）

**预期结果**：
- 请求体包含所有必需字段
- `timestamp` 格式为 ISO 8601
- `top_issues` 按 severity 降序排列

**测试数据准备**：
- 完整扫描报告（包含多种 severity 的问题）

---

### SCHED-AC3: 手动触发扫描

**验收标准**：支持手动触发 `python scripts/scan.py --trigger`。

#### 测试场景 SCHED-AC3-TS1: CLI --trigger 参数执行扫描

**测试前置条件**：
- 环境：Python 3.9+
- `scripts/scan.py` 支持 `--trigger` 参数
- 至少一个测试仓库可用

**测试步骤**：
1. 执行命令 `python scripts/scan.py --repo <test-repo> --base master --target HEAD --trigger`
2. 验证命令退出码为 0
3. 验证标准输出包含 "扫描完成" 或类似成功信息
4. 验证报告文件已生成（在 `report/` 目录下）
5. 验证报告文件包含有效 JSON 或 Markdown 内容

**预期结果**：
- 退出码 = 0
- 标准输出包含扫描完成信息
- 报告文件已生成且内容非空

**测试数据准备**：
- 测试仓库：任意包含 Git 历史的仓库
- 输出目录：`/tmp/test-ac3-report/`

**自动化实现提示**：
```python
# tests/test_scheduler_e2e.py::test_manual_trigger
def test_manual_trigger():
    result = subprocess.run(
        ["python", "scripts/scan.py", "--repo", test_repo, "--base", "master", "--target", "HEAD", "--trigger", "--output", "/tmp/test-ac3-report/"],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0
    assert "扫描完成" in result.stdout or "scan" in result.stdout.lower()
    assert os.path.isdir("/tmp/test-ac3-report/")
```

---

#### 测试场景 SCHED-AC3-TS2: 无变更时手动触发

**测试前置条件**：
- 环境：同 SCHED-AC3-TS1
- 测试仓库的 `master` 和 `HEAD` 指向同一提交（无差异）

**测试步骤**：
1. 创建一个临时 Git 仓库，仅有 1 个提交
2. 执行 `python scripts/scan.py --repo <temp-repo> --base master --target master --trigger`
3. 验证退出码为 0
4. 验证输出包含 "无代码变更" 或类似信息

**预期结果**：
- 退出码 = 0（正常退出，非错误）
- 输出提示无变更
- 不生成报告文件（或生成空报告）

**测试数据准备**：
- 临时 Git 仓库（1 个提交，无分支差异）

---

### SCHED-AC4: 扫描失败告警通知

**验收标准**：扫描失败时发送告警通知。

#### 测试场景 SCHED-AC4-TS1: 扫描异常触发告警

**测试前置条件**：
- 环境：Python 3.9+
- `ScanRunner` 和 `Notifier` 已实现
- 配置 `schedule.notify: true`
- Mock Webhook 服务可用

**测试步骤**：
1. 实例化 `ScanRunner`，配置中启用通知
2. Mock `run_scan()` 方法抛出 `RuntimeError("Semgrep crashed")`
3. Mock `Notifier.send_webhook()` 方法，记录调用
4. 调用 `scan_runner.run()`
5. 验证 `Notifier.send_webhook()` 或 `Notifier.send_alert()` 被调用
6. 验证告警内容包含错误信息 "Semgrep crashed"
7. 验证告警级别为 `CRITICAL` 或 `ERROR`

**预期结果**：
- 告警通知被发送
- 告警内容包含异常信息
- 告警级别为 `CRITICAL` 或 `ERROR`

**测试数据准备**：
- Mock 异常：`RuntimeError("Semgrep crashed")`
- Mock Webhook 服务

**自动化实现提示**：
```python
# tests/test_scheduler.py::test_scan_failure_triggers_alert
def test_scan_failure_triggers_alert():
    notifier = Mock(spec=Notifier)
    runner = ScanRunner(config={"schedule": {"notify": True}}, notifier=notifier)
    with patch.object(runner, 'run_scan', side_effect=RuntimeError("Semgrep crashed")):
        runner.run()
    assert notifier.send_alert.called or notifier.send_webhook.called
    call_args = notifier.send_alert.call_args or notifier.send_webhook.call_args
    assert "Semgrep crashed" in str(call_args)
```

---

#### 测试场景 SCHED-AC4-TS2: 告警通知包含诊断信息

**测试前置条件**：
- 同 SCHED-AC4-TS1
- 扫描失败时包含堆栈信息

**测试步骤**：
1. Mock `run_scan()` 抛出带有完整堆栈的异常
2. 调用 `scan_runner.run()`
3. 验证告警通知包含以下诊断信息：
   - 错误类型（`RuntimeError`）
   - 错误消息
   - 时间戳
   - 仓库名称（如果可获取）
4. 验证告警通知不包含敏感信息（如 API Key）

**预期结果**：
- 告警包含错误类型和消息
- 告警包含时间戳
- 告警不包含敏感信息

**测试数据准备**：
- Mock 异常（带堆栈）
- 配置中模拟包含 API Key（验证不泄露）

---

#### 测试场景 SCHED-AC4-TS3: 连续失败时的告警限流

**测试前置条件**：
- 环境：Python 3.9+
- 配置告警限流（如 5 分钟内最多发送 1 次告警）

**测试步骤**：
1. 实例化 `ScanRunner`，配置告警限流间隔 300 秒
2. 连续 3 次 Mock 扫描失败
3. 每次失败后调用 `scan_runner.run()`
4. 验证告警通知仅发送 1 次（第 1 次失败时）
5. 第 2、3 次失败时告警被限流跳过
6. 验证日志中包含 "告警限流" 信息

**预期结果**：
- 3 次失败仅发送 1 次告警
- 日志记录了限流信息
- 不丢失失败记录（日志中记录了所有失败）

**测试数据准备**：
- 配置：`{"schedule": {"notify": true, "alert_throttle_seconds": 300}}`

---

## 四、审计 Checklist 汇总

> 以下 Checklist 供用户审计勾兑使用，对应 IMPLEMENTATION-PLAN.md 第四章。

### Phase 1: Semgrep 集成

#### 验收测试（ATDD）

| AC | 测试场景 | 状态 | 备注 |
|----|----------|------|------|
| AC1 | AC1-TS1: XXE 规约解析与 Semgrep YAML 转换 | [ ] | |
| AC1 | AC1-TS2: 多规约文件批量解析与规则完整性 | [ ] | |
| AC1 | AC1-TS3: Semgrep JSON 输出解析与结构化问题生成 | [ ] | |
| AC2 | AC2-TS1: agentserver 仓库 XXE 全量扫描 | [ ] | 需 Semgrep |
| AC2 | AC2-TS2: agentserver 仓库签名绕过检出 | [ ] | 需 Semgrep |
| AC2 | AC2-TS3: 测试案例库精确匹配验证 | [ ] | 需 Semgrep |
| AC3 | AC3-TS1: nas_backup 仓库提权漏洞扫描 | [ ] | 需 Semgrep |
| AC3 | AC3-TS2: nas_backup 仓库路径穿越与 SSRF 扫描 | [ ] | 需 Semgrep |
| AC3 | AC3-TS3: opencode 仓库 TypeScript 安全风险扫描 | [ ] | 需 Semgrep |
| AC4 | AC4-TS1: 单仓库扫描性能基准测试 | [ ] | 需 Semgrep |
| AC4 | AC4-TS2: Semgrep 不可用时的降级性能测试 | [ ] | 无需 Semgrep |
| AC4 | AC4-TS3: Semgrep 超时处理 | [ ] | 需 Semgrep |

#### 真实仓库验证

| 仓库 | 验证项 | 预期 | 状态 |
|------|--------|------|------|
| agentserver | XXE 漏洞检出 | >= 2 个 | [ ] |
| agentserver | 签名绕过检出 | >= 1 个 | [ ] |
| nas_backup | eval/os.system 检出 | >= 3 个 | [ ] |
| opencode | innerHTML/eval 检出 | >= 2 个 | [ ] |

---

### Phase 2: AI 增强评审

#### 验收测试（ATDD）

| AC | 测试场景 | 状态 | 备注 |
|----|----------|------|------|
| AC1 | AI-AC1-TS1: Mock LLM 误报过滤效果验证 | [ ] | |
| AC1 | AI-AC1-TS2: 不同置信度阈值下的过滤效果 | [ ] | |
| AC2 | AI-AC2-TS1: AI 修复建议代码片段验证 | [ ] | |
| AC2 | AI-AC2-TS2: 原始规则 fix 字段保留与增强 | [ ] | |
| AC3 | AI-AC3-TS1: 批量 20 问题 AI 评审性能测试 | [ ] | |
| AC3 | AI-AC3-TS2: 超大批量（50 问题）分批处理验证 | [ ] | |
| AC4 | AI-AC4-TS1: 无 API Key 时降级 | [ ] | |
| AC4 | AI-AC4-TS2: LLM API 超时/异常时降级 | [ ] | |
| AC4 | AI-AC4-TS3: LLM 返回无效 JSON 时降级 | [ ] | |

#### 真实仓库验证

| 仓库 | 验证项 | 预期 | 状态 |
|------|--------|------|------|
| agentserver | AI 评审后误报率 | < 20%（基线 30%） | [ ] |
| nas_backup | AI 修复建议含代码片段占比 | >= 80% | [ ] |

---

### Phase 3: 定期扫描调度

#### 验收测试（ATDD）

| AC | 测试场景 | 状态 | 备注 |
|----|----------|------|------|
| AC1 | SCHED-AC1-TS1: Cron 表达式解析与下次执行时间计算 | [ ] | |
| AC1 | SCHED-AC1-TS2: 无效 Cron 表达式错误处理 | [ ] | |
| AC1 | SCHED-AC1-TS3: Cron 定时触发扫描执行 | [ ] | |
| AC2 | SCHED-AC2-TS1: Webhook 通知发送成功 | [ ] | |
| AC2 | SCHED-AC2-TS2: Webhook 目标不可达时的错误处理 | [ ] | |
| AC2 | SCHED-AC2-TS3: Webhook 通知内容格式验证 | [ ] | |
| AC3 | SCHED-AC3-TS1: CLI --trigger 参数执行扫描 | [ ] | |
| AC3 | SCHED-AC3-TS2: 无变更时手动触发 | [ ] | |
| AC4 | SCHED-AC4-TS1: 扫描异常触发告警 | [ ] | |
| AC4 | SCHED-AC4-TS2: 告警通知包含诊断信息 | [ ] | |
| AC4 | SCHED-AC4-TS3: 连续失败时的告警限流 | [ ] | |

#### 部署验证

| 验证项 | 状态 |
|--------|------|
| Cron 定时任务配置文档（docs/CRON-SETUP.md） | [ ] |
| Webhook 通知配置文档（docs/WEBHOOK-SETUP.md） | [ ] |
| 手动触发命令可用（`python scripts/scan.py --trigger`） | [ ] |

---

### 跨模块能力域对齐检查

> 对齐市场调研报告中的能力域分析，确保实现覆盖核心需求。

| 能力域（调研报告） | 覆盖模块 | 覆盖 AC | 状态 |
|-------------------|----------|---------|------|
| 分支 Diff 扫描 | Semgrep 集成 | AC2-TS1, AC3-TS1 | [ ] |
| 调用链/血缘分析 | Semgrep 集成（跨文件数据流） | AC1-TS1, AC2-TS3 | [ ] |
| 自定义规约体系 | Semgrep 集成 | AC1-TS1, AC1-TS2 | [ ] |
| 安全漏洞检测（OWASP Top 10） | Semgrep 集成 | AC2-TS1~TS3, AC3-TS1~TS3 | [ ] |
| AI 辅助评审（混合架构） | AI 增强评审 | AI-AC1~AC4 | [ ] |
| CI/CD 集成 | 定期扫描调度 | SCHED-AC1~AC4 | [ ] |
| 定期扫描调度 | 定期扫描调度 | SCHED-AC1, SCHED-AC3 | [ ] |

---

### 测试场景统计

| 模块 | AC 数量 | 测试场景总数 | 需 Semgrep | 可离线运行 |
|------|---------|-------------|-----------|-----------|
| Semgrep 集成 | 4 | 12 | 8 | 4 |
| AI 增强评审 | 4 | 9 | 0 | 9（全部 Mock） |
| 定期扫描调度 | 4 | 11 | 0 | 11（全部 Mock） |
| **合计** | **12** | **32** | **8** | **24** |
