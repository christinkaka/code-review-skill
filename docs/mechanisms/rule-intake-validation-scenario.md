# 规则新增验证场景

> [首页](../../README.md) / [文档索引](../README.md) / [核心机制](../README.md#核心机制详解) / [测试体系](testing.md) / **规则新增验证场景**
>
> 场景编号：E2E-002  
> 验证目标：验证从 CWE 案例到 L3 规则的完整接入流水线（八步 SOP）  
> 示例类别：CWE-601 开放重定向（阶段一 A1 待扩展格）  
> 设计日期：2026-08-26

---

## 1. 场景概述

本场景验证规则接入 SOP 的完整执行路径，以 CWE-601（开放重定向）为具体案例，从零到 L3 走完八步流水线。重点验证：

1. **案例归集质量**：vuln/sec 成对用例是否完备
2. **PoC 矩阵验证**：预期 vs 实际是否 100% 一致
3. **规约落地规范**：Markdown DSL 是否符合骨架要求
4. **孪生产物一致性**：yaml 与 md 行为是否等价
5. **e2e 测试覆盖**：TP/TN 矩阵是否全断言
6. **靶场实测精确率**：java-sec-code 全量 TP/FP 判定
7. **能力地图更新**：等级与凭证是否正确登记
8. **全量回归**：无静默失效、无规则冲突

### 1.1 验证范围

| 步骤 | 验证内容 | 产出物 | 验收标准 |
|------|----------|--------|----------|
| 1. 案例归集 | CWE-601 官方定义 + 真实漏洞代码形态 | vuln/sec 代码对清单 | ≥ 3 对用例 |
| 2. 三元组提炼 | source/sink/sanitizer 提炼 | 三元组草案 | sanitizer 覆盖全部 sec 用例 |
| 3. PoC 矩阵 | 临时 semgrep yaml + 用例文件 | 实测矩阵 | 预期 vs 实际 100% 一致 |
| 4. 规约落地 | `references/security/open-redirect.md` | Markdown 规约 | 引擎编译无告警 |
| 5. 孪生 yaml | `references/security/open-redirect.yaml` | 静态孪生产物 | profile 完备性测试绿 |
| 6. e2e 测试 | `tests/test_open_redirect_e2e.py` | TP/TN 断言 | 单文件测试绿 |
| 7. 靶场实测 | java-sec-code 全量扫描 | TP/FP 记录 | 精确率 ≥ 95% |
| 8. 地图更新 | capability-map-data.yaml + 重生成 | 能力地图 | 全量回归绿 |

### 1.2 前置条件

- 已阅读 `docs/rule-intake-sop.md` 八步流水线
- 已阅读 `docs/extension-points.md` 七个扩展锚点
- 已查阅 `docs/capability-map.md` 确认 CWE-601 在 L0 待扩展格
- semgrep 已安装（PoC 矩阵验证必需）

---

## 2. 验证流程

### 步骤 1：案例归集与类别判定（15 分钟）

**目标**：收集 CWE-601 的真实漏洞代码形态，确认 vuln/sec 成对用例完备。

**操作**：

1. 检索 CWE-601 官方定义：
   ```bash
   # WebSearch: "CWE-601 URL Redirection to Untrusted Site"
   # 确认：用户可控 URL 参数流入重定向 API（sendRedirect/forward/redirect）
   ```

2. 收集真实漏洞代码形态（至少 3 种）：
   ```java
   // 形态 1：Servlet sendRedirect
   String url = request.getParameter("url");
   response.sendRedirect(url);  // vuln
   
   // 形态 2：Spring redirect: 前缀
   return "redirect:" + request.getParameter("url");  // vuln
   
   // 形态 3：Spring RedirectView
   return new RedirectView(request.getParameter("url"));  // vuln
   ```

3. 为每种形态找到对应的加固写法：
   ```java
   // 加固 1：白名单校验
   String url = request.getParameter("url");
   if (isAllowedDomain(url)) {
       response.sendRedirect(url);
   }
   
   // 加固 2：相对路径限制
   String url = request.getParameter("url");
   if (url.startsWith("/")) {
       response.sendRedirect(url);
   }
   
   // 加固 3：URL 解析后校验 host
   URI uri = new URI(url);
   if (trustedHosts.contains(uri.getHost())) {
       response.sendRedirect(url);
   }
   ```

4. 类别判定：
   ```bash
   grep -i "redirect" references/security/*.md
   ```
   预期：无现有规则覆盖 → 新建 `open-redirect.md`

**验收标准**：
- [ ] ≥ 3 种漏洞形态
- [ ] 每种形态有对应加固写法
- [ ] 能写出"污点从哪来到哪去"：`request.getParameter("url")` → `sendRedirect/redirect:`

---

### 步骤 2：三元组提炼（10 分钟）

**目标**：提炼 source/sink/sanitizer，标注 sink API 形态。

**操作**：

1. Source（用户可控入口）：
   ```
   $REQ.getParameter(...)
   $REQ.getHeader(...)
   $REQ.getQueryString()
   spring-entrypoint-param
   ```

2. Sink（危险汇聚）：
   ```
   (HttpServletResponse $RESP).sendRedirect(...)
   $RESP.sendRedirect(...)
   "redirect:" + $X
   new RedirectView(...)
   ```
   注意：`"redirect:" + $X` 是字符串拼接形态，需确认 semgrep 是否支持（PoC 实证）

3. Sanitizer（加固切断点）：
   ```
   $X.isAllowedDomain(...)
   $X.startsWith("/")
   $X.trustedHosts.contains(...)
   ```
   注意：sanitizer 必须带 receiver 元变量（语义陷阱 #4）

**验收标准**：
- [ ] sanitizer 列表覆盖全部 sec 用例
- [ ] sink 无与常见无害 API 同名的风险（如 `redirect:` 不是方法调用）

---

### 步骤 3：PoC 矩阵（20 分钟）

**目标**：临时目录写 semgrep yaml + 构造用例文件，预期 vs 实际 100% 一致。

**操作**：

1. 创建临时目录：
   ```bash
   mkdir -p /tmp/poc-redirect
   cd /tmp/poc-redirect
   ```

2. 写 semgrep 规则（`rule.yaml`）：
   ```yaml
   rules:
   - id: redirect-taint
     mode: taint
     message: 用户可控 URL 流入重定向 API
     severity: HIGH
     languages: [java]
     pattern-sources:
     - pattern: $REQ.getParameter(...)
     - pattern: $REQ.getHeader(...)
     pattern-sinks:
     - pattern: (HttpServletResponse $RESP).sendRedirect(...)
     - pattern: $RESP.sendRedirect(...)
     pattern-sanitizers:
     - pattern: $X.isAllowedDomain(...)
     - pattern: $X.startsWith(...)
   ```

3. 写用例文件（`Vuln.java` / `Safe.java`）：
   ```java
   // Vuln.java
   public class Vuln {
       public void doGet(HttpServletRequest req, HttpServletResponse resp) {
           String url = req.getParameter("url");
           resp.sendRedirect(url);  // 预期：命中
       }
   }
   
   // Safe.java
   public class Safe {
       public void doGet(HttpServletRequest req, HttpServletResponse resp) {
           String url = req.getParameter("url");
           if (isAllowedDomain(url)) {
               resp.sendRedirect(url);  // 预期：不命中
           }
       }
   }
   ```

4. 跑 semgrep 对照：
   ```bash
   semgrep --config rule.yaml Vuln.java Safe.java --json
   ```

5. 填写实测矩阵：
   | 用例 | 预期 | 实际 | 一致？ |
   |------|------|------|--------|
   | Vuln.java:5 | 命中 | 命中 | ✓ |
   | Safe.java:6 | 不命中 | 不命中 | ✓ |

6. 若不一致，回步骤 2 调整三元组（常见原因：sanitizer 无 receiver、sink 形态遗漏）

**验收标准**：
- [ ] 矩阵 100% 符合预期
- [ ] 任何不符合已记录原因并修复

---

### 步骤 4：规约落地（10 分钟）

**目标**：按锚点 ① 骨架写 `references/security/open-redirect.md`。

**操作**：

1. 创建规约文件：
   ```bash
   cp references/security/command-injection.md references/security/open-redirect.md
   ```

2. 编辑内容（替换 id/cwe/owasp/source/sink/sanitizer）：
   ```markdown
   # 开放重定向 - 用户可控 URL 流入重定向 API（数据流分析）

   > 用户可控 URL 参数未经白名单校验直接流入 `sendRedirect` 或 `redirect:` 前缀，
   > 导致钓鱼攻击或凭证泄露。基于 Semgrep taint 模式做过程内数据流追踪。

   ```yaml
   id: redirect-taint
   languages: [java]
   severity: HIGH
   cwe: CWE-601
   owasp: A01:2021
   ```

   ## 检测原理

   - **污点源**：Servlet 请求参数/头/查询串 + Spring 入口方法参数
   - **污点汇聚**：重定向 API 两类形态
     - 类型化声明 receiver：`(HttpServletResponse $RESP).sendRedirect(...)`
     - Spring `redirect:` 前缀（PoC 实证：字符串拼接形态 semgrep 不支持，
       需 pattern 规则补充）
   - **净化器**：白名单校验函数 `$X.isAllowedDomain(...)`——**必须带
     receiver 元变量**（语义陷阱 #4）

   ## 检测模式

   ```pattern-sources
   $REQ.getParameter(...)
   $REQ.getHeader(...)
   $REQ.getQueryString()
   spring-entrypoint-param
   ```

   ```pattern-sinks
   (HttpServletResponse $RESP).sendRedirect(...)
   $RESP.sendRedirect(...)
   ```

   ```pattern-sanitizers
   $X.isAllowedDomain(...)
   $X.startsWith(...)
   ```
   ```

3. 验证引擎编译：
   ```bash
   python3 -c "
   from scripts.rule_engine import RuleEngine
   engine = RuleEngine('references')
   rules = engine._load_rules()
   print(f'规则加载成功: {len(rules)} 条')
   "
   ```
   预期：无告警，规则数量 +1

**验收标准**：
- [ ] 规约文件存在且格式正确
- [ ] 引擎编译无告警
- [ ] yaml 元数据含 cwe/owasp

---

### 步骤 5：孪生 yaml + profile 注册（5 分钟）

**目标**：生成静态孪生产物，注册到 profile。

**操作**：

1. 生成孪生 yaml：
   ```bash
   python3 -c "
   from scripts.rule_engine import RuleEngine
   import yaml
   engine = RuleEngine('references')
   semgrep_rules = engine._rules_to_semgrep()
   with open('references/security/open-redirect.yaml', 'w') as f:
       yaml.dump(semgrep_rules, f, default_flow_style=False)
   "
   ```

2. 注册到 profile：
   ```bash
   echo "  - security/open-redirect" >> references/profiles/default.yaml
   ```

3. 验证 profile 完备性：
   ```bash
   python3 -m pytest tests/test_profile_completeness.py -v
   ```
   预期：测试绿

4. 验证孪生 yaml 行为一致：
   ```bash
   semgrep --config references/security/open-redirect.yaml /tmp/poc-redirect/Vuln.java --json
   ```
   预期：与步骤 3 的 PoC 矩阵一致

**验收标准**：
- [ ] 孪生 yaml 存在
- [ ] profile 完备性测试绿
- [ ] 孪生 yaml 行为与引擎一致

---

### 步骤 6：e2e 测试固化（15 分钟）

**目标**：按锚点 ⑥ 模板写 `tests/test_open_redirect_e2e.py`，TP/TN 矩阵全断言。

**操作**：

1. 创建测试文件：
   ```bash
   cp tests/test_command_injection_e2e.py tests/test_open_redirect_e2e.py
   ```

2. 编辑测试用例（替换 rule_id、代码样本、断言）：
   ```python
   import pytest
   from scripts.rule_engine import RuleEngine

   class TestOpenRedirectE2E:
       @pytest.fixture
       def engine(self):
           return RuleEngine('references')

       def test_vuln_sendRedirect(self, engine, tmp_path):
           code = '''
   import javax.servlet.http.*;
   public class Vuln {
       public void doGet(HttpServletRequest req, HttpServletResponse resp) {
           String url = req.getParameter("url");
           resp.sendRedirect(url);  // marker: vuln-sendRedirect
       }
   }
           '''
           f = tmp_path / "Vuln.java"
           f.write_text(code)
           issues = engine.run(repo_path=str(tmp_path), changed_files=["Vuln.java"])
           assert any("redirect-taint" in i.get("rule_id", "") for i in issues)

       def test_safe_isAllowedDomain(self, engine, tmp_path):
           code = '''
   import javax.servlet.http.*;
   public class Safe {
       public void doGet(HttpServletRequest req, HttpServletResponse resp) {
           String url = req.getParameter("url");
           if (isAllowedDomain(url)) {
               resp.sendRedirect(url);  // marker: safe-sanitizer
           }
       }
       private boolean isAllowedDomain(String u) { return true; }
   }
           '''
           f = tmp_path / "Safe.java"
           f.write_text(code)
           issues = engine.run(repo_path=str(tmp_path), changed_files=["Safe.java"])
           assert not any("redirect-taint" in i.get("rule_id", "") for i in issues)
   ```

3. 运行测试：
   ```bash
   python3 -m pytest tests/test_open_redirect_e2e.py -v
   ```
   预期：所有测试绿

**验收标准**：
- [ ] 测试文件存在
- [ ] TP/TN 矩阵全断言
- [ ] 单文件测试绿

---

### 步骤 7：靶场全量实测（20 分钟）

**目标**：java-sec-code 全量跑引擎路径，逐条 TP/FP 人工判定。

**操作**：

1. 运行扫描：
   ```bash
   python3 scripts/scan.py \
     --repo repos/java-sec-code/ \
     --base main \
     --target HEAD \
     --output report/redirect-test/ \
     --workflow security \
     --no-ai
   ```

2. 统计检出：
   ```bash
   python3 -c "
   import json
   d = json.load(open('report/redirect-test/report.json'))
   redirect_issues = [i for i in d['issues'] if 'redirect-taint' in i.get('rule_id', '')]
   print(f'开放重定向检出: {len(redirect_issues)}')
   for i in redirect_issues:
       print(f\"  {i['file']}:{i['line']} - {i['message']}\")
   "
   ```

3. 逐条人工判定 TP/FP：
   - 打开每个检出文件，确认是否为真实漏洞
   - 记录判定结果（TP/FP + 理由）

4. 计算精确率：
   ```python
   tp = 5  # 示例
   fp = 0
   precision = tp / (tp + fp) if (tp + fp) > 0 else 0
   print(f"精确率: {precision:.2%}")
   ```

5. 若有 FP，回步骤 2-4 调整三元组

**验收标准**：
- [ ] 靶场全量扫描完成
- [ ] 逐条 TP/FP 判定记录在案
- [ ] 精确率 ≥ 95%（FP 零容忍）

---

### 步骤 8：能力地图更新与收尾（10 分钟）

**目标**：登记等级与凭证，重生成能力地图，全量回归。

**操作**：

1. 编辑 `docs/capability-map-data.yaml`：
   ```yaml
   CWE-601:
     level: L3
     target_evidence: "java-sec-code: redirect-taint 5 TP + 0 FP"
   ```

2. 重生成能力地图：
   ```bash
   python3 scripts/gen_capability_map.py
   ```

3. 全量回归：
   ```bash
   python3 -m pytest tests/ -v --ignore=tests/test_semgrep_integration.py
   ```
   预期：所有测试绿

4. 更新架构文档：
   ```bash
   # 在 docs/architecture.md 追加批次记录
   echo "- 2026-08-26: CWE-601 开放重定向（redirect-taint）晋升 L3" >> docs/architecture.md
   ```

**验收标准**：
- [ ] 能力地图已更新
- [ ] 全量回归绿
- [ ] 架构文档已追加批次记录

---

## 3. 验证指标汇总

| 指标 | 目标值 | 测量方法 | 验收标准 |
|------|--------|----------|----------|
| vuln/sec 代码对数量 | ≥ 3 对 | 步骤 1 清单 | 步骤 1 通过 |
| PoC 矩阵一致性 | 100% | 步骤 3 矩阵 | 步骤 3 通过 |
| 引擎编译 | 无告警 | 步骤 4 验证 | 步骤 4 通过 |
| profile 完备性 | 测试绿 | 步骤 5 pytest | 步骤 5 通过 |
| e2e 测试覆盖 | TP/TN 全断言 | 步骤 6 pytest | 步骤 6 通过 |
| **靶场精确率** | **≥ 95%** | 步骤 7 统计 | **步骤 7 通过** |
| 全量回归 | 测试绿 | 步骤 8 pytest | 步骤 8 通过 |

---

## 4. 验收判定

### 4.1 通过条件

所有步骤验收标准达成，判定为**规则晋升 L3**。

### 4.2 部分通过条件

- 靶场精确率 ≥ 90% 但 < 95%：标记为**条件通过（L2）**，需优化三元组后重测
- e2e 测试部分断言缺失：标记为**条件通过（L2）**，需补全断言

### 4.3 失败条件

- PoC 矩阵一致性 < 100%：判定为**验证失败**，需回步骤 2 重提炼
- 靶场精确率 < 90%：判定为**验证失败**，需评估该类别是否适合静态检测
- 全量回归有失败：判定为**验证失败**，需排查规则冲突

---

## 5. 自检清单

完成本场景后，确认以下产出物齐全：

```
[ ] references/security/open-redirect.md        含实测行为合同
[ ] references/security/open-redirect.yaml      孪生产物，行为一致
[ ] references/profiles/default.yaml            已注册
[ ] tests/test_open_redirect_e2e.py             TP/TN 矩阵全断言
[ ] 靶场实测记录                                 TP/FP 判定在案
[ ] docs/capability-map-data.yaml               等级与凭证登记
[ ] docs/capability-map.md                      已重生成
[ ] 全量回归                                     绿
```

---

## 6. 相关文档

| 主题 | 文档 |
|------|------|
| 规则接入八步 SOP | [rule-intake-sop.md](../rule-intake-sop.md) |
| 七个扩展锚点 | [extension-points.md](../extension-points.md) |
| 能力地图与等级 | [capability-map.md](../capability-map.md) |
| Semgrep 语义陷阱 | [rule-mechanism.md](rule-mechanism.md#51-semgrep-语义陷阱清单踩坑沉淀) |
| 端到端代码评审验证 | [e2e-validation-scenario.md](e2e-validation-scenario.md) |
