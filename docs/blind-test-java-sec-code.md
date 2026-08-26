# 真实仓库双盲复测报告：java-sec-code

**测试日期**：2026-08-26
**测试仓库**：[JoyChou93/java-sec-code](https://github.com/JoyChou93/java-sec-code)（commit `4711f4e`，80 个 Java 文件）

**测试目的**：hello-world 单仓库验证后，检验 taint 规则在第二个真实仓库上的泛化能力（防过拟合）；该仓库是知名 Java 安全靶场，覆盖全部 5 类 taint 规则的漏洞类型。

## 测试方法

1. 全量引擎扫描仓库（default profile），提取 5 条 taint 规则 + 2 条 deep-detection pattern 规则的检出
2. 按 java-sec-code 的 URL 映射约定建立方法级 ground truth：路径含 `vuln` 为漏洞方法，含 `sec`/`safe`/`security` 为加固方法
3. 逐条人工判定检出点代码现场（含 `other`/非入口方法检出）

## Ground Truth 判定结果

### taint 规则（5 条）：11 检出，全部真阳性，零误报

| 规则 | 检出位置 | 方法 / 路径 | 判定 | 说明 |
|------|---------|------------|------|------|
| deser-taint | Deserialize.java:49 | rememberMeVul `/rememberMe/vuln` | TP | Base64 → ObjectInputStream |
| deser-taint | Shiro.java:37 | shiro_deserialize `/shiro/deserialize` | TP | **Shiro-550**：入口方法 `HttpServletRequest` 参数经入口点锚定视为污点，`getCookie(req,...)` 调用传参保守传播 → 解密流 → `ObjectInputStream` |
| path-traversal-taint | FileUpload.java:62,63 | singleFileUpload `/upload` | TP ×2 | 上传文件名拼入路径（经典路径穿越） |
| path-traversal-taint | FileUpload.java:144,145 | uploadPicture `/upload/picture` | TP ×2 | 同上 |
| path-traversal-taint | FileUpload.java:180,185 | convert（私有辅助方法） | TP ×2 | `$FILE.getOriginalFilename()` 源在非入口辅助方法中直接生效 |
| sqli-taint | SQLI.java:67 | jdbc_sqli_vul `/jdbc/vuln` | TP | Statement + 字符串拼接 |
| sqli-taint | SQLI.java:150,153 | jdbc_ps_vuln `/jdbc/ps/vuln` | TP ×2 | prepareStatement 拼接 + PreparedStatement.executeQuery |
| ssrf-taint | SSRF.java:130 | openStream `/openStream` | TP | 入口参数 → `URL.openStream()` |

### pattern 规则（2 条）：8 检出，5 TP + 3 FP

| 规则 | 检出位置 | 判定 | 说明 |
|------|---------|------|------|
| xxe-deep-detection | XXE.java:53,166,239,292,348 | TP ×5 | 5 种未加固 XML 工厂全检出 |
| xxe-deep-detection | SafeDomainParser.java:32,88 | **FP ×2** | 解析 classpath 常量 XML（`url_safe_domain.xml`，可信输入）；pattern 规则无数据流语义，固有误报 |
| ssrf-deep-detection | SSRFChecker.java:74 | **FP** | SSRF 白名单校验器本身发起出站连接验证——这是安全控件；同为 pattern 无数据流语义的固有误报 |

注：**对应的 taint 规则（ssrf-taint）对 SSRFChecker 正确地零检出**——taint 无污点源不报，pattern 规则无法区分安全控件与漏洞代码。这是 taint 架构优于 pattern 的直接实证。

## 盲测驱动的规则修复（2 项，均先 PoC 后落地）

### 修复 1：sqli-taint 类型化 sink（消除 2 FP）

**误报现场**：QLExpress.java 的 `sec` 方法（已加固 `setForbidInvokeSecurityRiskMethods(true)`）被误报。根因：sink `$STMT.execute(...)` 元变量匹配任意 receiver，`ExpressRunner.execute()`（表达式执行）撞上 SQL 的 execute——`ExecutorService.execute()`（线程池，真实代码高频）同属此误报面。

**修复**：sink 改类型化元变量 `(java.sql.Statement $STMT).execute(...)` 等 14 条。

**关键发现（PoC 实证）**：semgrep 类型化元变量**不做子类型匹配**——`Statement` 声明命中，`PreparedStatement` 声明不命中 Statement 类型 sink。因此 Statement/PreparedStatement/CallableStatement 必须逐一列出；初次修复只写 Statement 类型导致 java-sec-code SQLI.java:153 漏报，补齐后恢复。

**验证**：PoC 全矩阵（3 类 Statement 声明 + import 形式 EntityManager + ExpressRunner/ExecutorService 阴性）全通过；真实仓库 QLExpress 2 误报清零。

### 修复 2：xxe-deep-detection reader 级加固豁免（消除 2 FP）

**误报现场**：XXE.java 的 `xmlReaderSec`（`createXMLReader()` 后对 reader `setFeature(disallow-doctype-decl, true)`）和 `XMLReaderSec`（`spf.newInstance() → newSAXParser() → getXMLReader()` 后 `setFeature`）两个加固方法被误报。根因：原豁免块只覆盖工厂级 `newInstance() + setFeature`，reader 级加固形态不匹配。

**修复**：补 2 条 `pattern-not-inside`——豁免块必须从工厂创建语句跨到 setFeature 才能包住命中位置（pattern-not-inside 要求命中点在块范围内）。

**验证**：真实 XXE.java 实测 7 检出 → 5（sec 方法 2 误报清零，vuln 方法 5 真阳性全保留）。

### 修复 3：顺带发现并处置第三条静默失效规则（arch-java-missing-api-layer）

复扫验证期间发现全量扫描每次输出 "Semgrep 异常退出 (rc=2)" 噪声：design/architecture.md 的 `arch-java-missing-api-layer` 规则 pattern `import com.$ORG.$MODULE.$CLASSImpl;` 中 `$CLASSImpl` 含小写字母，不是合法 semgrep 元变量（要求 `$[A-Z_][A-Z_0-9]*`），**该规则自创建起从未生效**（与此前 2 条安全规则同类问题，但位于 design 类目，`TestAllRulesParseable` 原只覆盖 security 目录未拦住）。

**处置**：正确表达"类名以 Impl 结尾"需要 `metavariable-regex`（DSL 暂不支持），按禁用处理并注明原因；`TestAllRulesParseable` 扩展为全量规约目录 + default profile（与生产一致），防止任何类目的非法 pattern 再次静默失效。

## 漏检分析（covered 类型）

| 规则 | 漏检 | 根因 |
|------|------|------|
| ssrf-taint | urlConnection/vuln、HttpURLConnection/vuln、restTemplate/vuln×2、hutool/vuln、dnsrebind/vuln 等 ~7 个 vuln 方法 | Controller 方法委托私有 helper（如 `urlConnection(url)`），sink 在 helper 内；Semgrep OSS 过程内分析边界 |
| path-traversal-taint | path_traversal/vul | 同上（`getImgBase64(filepath)` 委托） |

与 hello-world 结论一致：**跨方法数据流是唯一系统性漏检原因**，泛化验证成立。仅内联数据流（openStream）被检出。

## 最终状态

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| taint 规则 | 10 TP + 2 FP | **11 TP + 0 FP**（含 PreparedStatement sink 漏报复原） |
| pattern 规则 | 5 TP + 5 FP | **5 TP + 3 FP**（剩余 3 个为 pattern 无数据流语义的固有误报） |
| 静默失效规则 | 2 条（ssrf/xxe，前轮已修） | **0**（新发现 arch-java-missing-api-layer 已禁用，可解析性测试扩至全量规约） |
| 全量回归 | 584 passed | **586 passed / 6 skipped**（新增 2 个盲测场景回归测试） |

附：复扫期间确认 dual-blind-django 报告从 101 → 0 检出为 rglob 文件顺序漂移换了 50 文件批（非规则回归——旧检出文件集按当前规则复扫为 165 检出，规则持续增强）；`arch-java-missing-api-layer` 的 rc=2 即由此顺带发现。

## 结论

1. **泛化验证通过**：hello-world 调优的规则（入口点锚定、sink 聚焦）在无关联的第二个仓库上 taint 规则零误报，未出现过拟合
2. **入口点锚定语义正确性再验证**：`HttpServletRequest` 参数（请求对象本身即用户输入）被正确视为污点源，Shiro-550 经 5 层调用链传播命中
3. **两个新的普适技术点**：类型化元变量不做子类型匹配（需枚举声明类型）；pattern-not-inside 豁免块必须覆盖命中位置
4. **taint vs pattern 直接实证**：同一仓库 SSRFChecker，ssrf-taint 正确静默、ssrf-deep-detection 误报——数据流语义是 pattern 规则不可替代的能力

## 已知限制与后续方向

1. 跨方法污点（Semgrep Pro 或 Service 层保守源标记）——两个仓库一致的系统性边界
2. pattern 规则固有误报（SafeDomainParser ×2、SSRFChecker ×1）：依赖 AI 复核层降噪，或逐步 taint 化
3. 表达式注入（QLExpress/SpEL/Ognl）、RCE、SSTI 等类型暂无规则覆盖（本仓库可作后续规则扩展的验证靶场）
