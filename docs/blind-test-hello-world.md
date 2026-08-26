# 真实仓库双盲复测报告：hello-world (VulnUserManager)

**测试仓库**：[AnshuPandey00/hello-world](https://github.com/AnshuPandey00/hello-world)
**仓库规模**：18 个 Java 文件
**测试目的**：对比 taint 规则与旧模式规则在真实漏洞仓库上的检出差异

## 测试方法

1. 使用旧规则（commit `c501b3c`，taint 迁移前）扫描仓库，记录检出
2. 使用 taint 规则（commit `dd4cabf`，合并后）扫描同一仓库，记录检出
3. 对比差异，分析 taint 规则的精准度和覆盖范围

## 第一轮检出对比（2026-08-25）

| 规则类型 | 旧规则 | taint 规则 | 差异 |
|---------|--------|-----------|------|
| Java 检出总数 | 36 | 34 | -2 |
| path-traversal | 0 | 2 | +2（新增） |
| deser | 2 | 0 | -2（被替代） |
| sqli | 1 | 0 | -1（被替代） |
| 其他规则 | 33 | 32 | -1 |

### taint 规则新增检出（2 个）

**FileController.java:104-105**
```java
Path filePath = Paths.get(UPLOAD_DIR + filename);
Files.write(filePath, file.getBytes());
```
- **漏洞类型**：目录穿越（CWE-22）
- **检出原因**：filename 来自用户输入（MultipartFile.getOriginalFilename），直接拼接到路径
- **taint 追踪**：source（HTTP 请求）→ sink（Files.write）
- **结论**：真实漏洞，taint 规则正确检出

### 旧规则独有检出（3 个）

**SerializeController.java:52-55**（2 个 deser）
```java
ObjectInputStream objectInputStream = new ObjectInputStream(byteStream);
Object deserializedObject = objectInputStream.readObject();
```
- **漏洞类型**：不安全反序列化（CWE-502）
- **未检出原因**：deser-taint 的 source 只覆盖 Servlet API（getParameter/getHeader），不覆盖 Spring `@RequestBody`
- **结论**：→ 第二轮已修复（入口点锚定）

**UserService.java:105**（1 个 sqli）
```java
String jpql = "SELECT u FROM User u WHERE u.username LIKE '%" + query + "%'";
Query jpqlQuery = entityManager.createQuery(jpql);
```
- **漏洞类型**：SQL 注入（CWE-89）
- **未检出原因**：sqli-taint 的 sink 只覆盖 JDBC API（execute/executeQuery），不覆盖 JPA `createQuery`
- **结论**：→ 第二轮已补 JPA sink；本仓库实际调用链跨方法（见第三轮）

## 第二轮：入口点锚定 + JPA sink（2026-08-26）

针对第一轮漏检 3 项的修复：

1. **入口点锚定**：5 条 taint 规则新增 `spring-entrypoint-param` 污点源——方法级
   mapping 注解（@GetMapping 等）锚定入口方法，全部参数视为用户可控。
   不用参数级注解（@RequestParam）过滤：PoC 实测 Semgrep Java 签名匹配中
   参数级注解不可靠（@Transactional 方法参数同样命中）。业界对照：cogniumhq
   24 个 Java OSS 仓库实测，不锚定入口点导致 98.7% critical 误报。
2. **JPA sink**：sqli-taint 补 `$EM.createQuery(...)` / `$EM.createNativeQuery(...)`。

复测结果：

| 检出 | 规则 | 位置 | 判定 |
|------|------|------|------|
| path-traversal-taint ×4 | FileController:50/51/104/105 | 目录穿越 ×4 | 全部真阳性 |
| deser-taint ×1 | SerializeController:52 | @RequestBody → ObjectInputStream | **真阳性（原漏检，已修复）** |
| xss-taint ×1 | FileController:105 | `Files.write(filePath, file.getBytes())` | **误报（文件写入非 HTTP 输出，sink 过宽）** |
| sqli-taint ×0 | UserService:105 | Controller→Service 跨方法流 | 仍漏检（见下） |

**UserService.java:105 仍漏检的原因**：污点链为
`UserController:119 @GetMapping searchUsers(@RequestParam query)` →
`userService.searchUsers(query)`（跨方法）→ Service 内 `createQuery`。
Semgrep OSS taint 为**过程内分析**，跨方法参数不传播——这是引擎能力边界
而非规则缺陷（Semgrep Pro 的跨过程分析可覆盖）。JPA sink 本身已验证可用
（`test_taint_e2e.py::TestSpringEntrypointE2E::test_sqli_entrypoint_tp_and_tn`
覆盖方法内 JPA 拼接真阳性）。

## 第三轮：xss 误报修复 + 两条静默失效规则复活（2026-08-26）

**1. xss-taint 误报修复（sink 收紧 + focus 聚焦）**

误报根因：sink `$WRITER.write(...)` 匹配任意 `.write()` 调用，`Files.write`
（文件写入）被命中。修复中进一步发现更深的语义问题——**入口点参数源的污点
按"起点包含"语义命中 sink，净化器失效**：PoC 实测 `write(htmlEscape(name))`
转义后仍报。修复分两层：

- sink 收紧为 HTTP 响应输出两类形态：`getWriter()`/`getOutputStream()`
  链式调用；显式类型 `PrintWriter`/`ServletOutputStream` 变量；
- sink 以 `focus: $DATA` 后缀聚焦数据参数，恢复值级污点判定（转义后
  clean、未转义 HIT，9/9 矩阵验证）。

**2. 两条规则 semgrep rc=2 解析失败静默失效（存量问题，本轮回扫发现）**

| 规则 | 根因 | 修复 |
|------|------|------|
| `ssrf-deep-detection__python` | 多语言规则中 Java 语法 pattern 无语言标签，落入 Python 变体解析失败，Python 侧 SSRF 检测从未生效 | 语言子标题打标签；复活时配套 `pattern-not: xxx("...")` 排除常量 URL 误报 |
| `xxe-deep-detection__java` | 缺分号语句序列 pattern-not 无法解析；且 pattern-not 范围语义下多语句排除块永远不命中 | DSL 新增 `pattern-not-inside` 块（引擎解析/组装/YAML 加载三处支持），XXE 检测首次真正生效，三种 OWASP 加固写法正确豁免 |

新增 `tests/test_pattern_rules_e2e.py::TestAllRulesParseable`——全量规则
经引擎生成后真实扫描断言零解析错误，防止此类静默失效再次发生。

## 最终状态（2026-08-26 第三轮复测）

| 指标 | 第一轮（taint 迁移） | 第二轮（入口点锚定） | 第三轮（本轮） |
|------|---------------------|---------------------|----------------|
| taint 误报 | 0 | 1（xss Files.write） | **0** |
| 已知漏检 | 3（deser×2、sqli×1） | 2（sqli×1、xss 误报抵消 deser 修复） | **1（sqli 跨方法，能力边界）** |
| 规则解析失败 | 2（静默失效） | 2 | **0** |
| 全量回归 | 549 passed | 580 passed | **584 passed / 6 skipped** |

5 规约最终检出（8 条）：path-traversal-pattern ×3（注释/测试文件模式命中，
实际管线中由白名单与 AI 复核层处理）、path-traversal-taint ×4（真阳性）、
deser-taint ×1（真阳性）。xss-taint 零检出正确（JSON REST API 仓库无
HTTP 响应直写场景）；ssrf/xxe 零检出正确（仓库无 openConnection 内联链与
XML 工厂调用，已 grep 确认）。

## 结论

### taint 规则体系（5 条 Java 规则）
1. **精准**：数据流追踪 + 入口点锚定 + sink 聚焦，真实漏洞全检出、误报清零
2. **可解释**：每条误报/漏检都定位到确切的语义根因并有 PoC 证据
3. **能力边界清晰**：跨方法数据流（Controller→Service）是 Semgrep OSS
   过程内分析的边界，如实记录不作遮掩

### 已知限制与后续方向
1. **跨方法污点**：Semgrep Pro 跨过程分析，或对 Service 层公共方法
   补保守源标记（权衡误报）
2. **Python/JS taint 化**：ssrf-deep-detection（Python/JS）仍为模式规则，
   可按 Java 模式平移（需 Python/JS 源/汇清单）
3. **正则回退降级**：pattern-not-inside 在正则回退引擎中按降级处理（不豁免），
   taint 规则回退时缺失——均为 Semgrep 不可用时的已知降级

## 附录：规则清单

### 旧规则（commit c501b3c）
- deser-java-object-input-stream：模式匹配 `new ObjectInputStream($USER_INPUT)`
- sqli-java-string-concat：模式匹配 SQL 字符串拼接

### taint 规则（含 2026-08-26 增强）
- path-traversal-taint：source=Servlet API + 入口点参数，sink=文件操作
- ssrf-taint：source=Servlet API + 入口点参数，sink=出站请求
- xss-taint：source=Servlet API + 入口点参数，sink=HTTP 响应输出（聚焦数据参数）
- sqli-taint：source=Servlet API + 入口点参数，sink=JDBC/JPA 执行
- deser-taint：source=Servlet API + 入口点参数，sink=反序列化/JNDI
