# 双盲验证报告：WebGoat 第二靶场

> [首页](../README.md) / [文档索引](README.md) / [验证报告](README.md#验证报告) / **WebGoat 盲测**
>
> 日期：2026-08-26 | 靶场：OWASP WebGoat (Spring Boot 2025.3, Java 21)
> 规则引擎编译产物：91 条安全规则（13 taint + 78 pattern）
> 扫描范围：`repos/webgoat/src/main/java/`（排除 test/resources/static）

---

## 1. 总览

| 指标 | 数值 |
|------|------|
| 总检出 | 49 |
| 真阳性 (TP) | 48 |
| 假阳性 (FP) | 1 |
| 精确率 | **97.96%** |
| 覆盖规则 | 11 / 91 |
| 未触发规则 | 80（目标不含对应漏洞模式） |

## 2. 按规则分类明细

### 2.1 crypto-hardcoded-key-java (13) — 全部 TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| DefaultUserInitializer.java | 27 | TP | `DEFAULT_PASSWORD = "webgoat"` 硬编码默认密码 |
| SolutionConstants.java | 10 | TP | `PASSWORD = "!!webgoat_admin_1234!!"` 管理员密码 |
| Assignment7.java | 36 | TP | `ADMIN_PASSWORD_LINK = "375afe11..."` 硬编码重置链接哈希 |
| JWTRefreshEndpoint.java | 45 | TP | `PASSWORD = "bm5nhSkxCXZkKRy4"` 登录密码 |
| JWTRefreshEndpoint.java | 46 | TP | `JWT_PASSWORD = "bm5n3SkxCX4kKRy4"` JWT 签名密钥 |
| SampleAttack.java | 27 | TP | `secretValue = "secr37Value"` 模板中的示例密钥 |
| MissingFunctionAC.java | 14 | TP | `PASSWORD_SALT_SIMPLE = "DeliberatelyInsecure1234"` 密码盐 |
| MissingFunctionAC.java | 15 | TP | `PASSWORD_SALT_ADMIN = "DeliberatelyInsecure1235"` 管理员盐 |
| ResetLinkAssignment.java | 44 | TP | `PASSWORD_TOM_9 = "somethingVeryRandom..."` Tom 的密码 |
| ActuatorExposureTask.java | 28 | TP | `LEAKED_API_KEY = "INTERNAL-API-KEY-987"` API 密钥 |
| DefaultCredentialsTask.java | 29 | TP | `DEFAULT_PASSWORD = "admin"` 默认凭证 |
| VerboseErrorTask.java | 29 | TP | `LEAKED_TOKEN = "STAGING-TOKEN-42"` 泄露令牌 |
| SqlInjectionLesson6b.java | 42 | TP | `password = "dave"` 回退密码 |

### 2.2 crypto-hardcoded-key__java (9) — 全部 TP

与上条规则存在重叠（7 处相同），额外覆盖 VerboseErrorTask.java:43 和 SqlInjectionLesson6b.java:42。两条规则互补但冗余，后续治理阶段可合并。

### 2.3 crypto-weak-random-java (11) — 全部 TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| ImageServlet.java | 21 | TP | `new Random().nextInt(10000)` 生成 PIN 码 |
| PasswordResetLink.java | 15 | TP | `new Random()` 生成密码重置令牌，admin 使用固定 seed |
| EncodingAssignment.java | 37 | TP | `new Random().nextInt()` 选择密码 |
| HashingAssignment.java | 37 | TP | `new Random().nextInt()` 选择 MD5 密钥 |
| HashingAssignment.java | 55 | TP | `new Random().nextInt()` 选择 SHA256 密钥 |
| CSRFGetFlag.java | 39 | TP | `new Random()` 生成 CSRF flag |
| CSRFGetFlag.java | 45 | TP | 同上（不同分支） |
| CSRFGetFlag.java | 56 | TP | 同上（不同分支） |
| HijackSessionAuthenticationProvider.java | 25 | TP | `new Random().nextLong()` 生成会话 ID |
| HttpBasicsExternal.java | 35 | TP | `new Random()` 生成 secret code |
| JWTSecretKeyEndpoint.java | 38 | TP | `new Random().nextInt()` 选择 JWT 密钥 |

### 2.4 deser-taint (1) — TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| InsecureDeserializationTask.java | 43 | TP | `ois.readObject()` 对用户 Base64 解码后的输入反序列化 |

数据流：`@RequestParam token` → Base64 decode → `ByteArrayInputStream` → `ObjectInputStream.readObject()`

### 2.5 log-injection-taint (6) — 全部 TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| VulnerableTaskHolder.java | 71 | TP | `log.info("restoring task: {}", taskName)` taskName 来自反序列化对象 |
| AsciiDoctorTemplateResolver.java | 139 | TP | `log.debug("browser locale {}", langHeader)` Accept-Language 头直接入日志 |
| SigningAssignment.java | 66 | TP | `log.warn("modulus {} incorrect", modulus)` 用户提交的 modulus 入日志 |
| Ping.java | 31 | TP | `log.debug(logLine)` logLine 包含 userAgent + text 请求参数 |
| FileServer.java | 79 | TP | `log.debug("File saved to {}", ...)` 含用户上传文件名 |
| LandingPage.java | 30 | TP | `log.trace("...", request.getRequestURL())` 请求 URL 入日志 |

### 2.6 path-traversal-pattern__java (1) — TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| ProfileUploadFix.java | 43 | TP | 仅用 `replace("../", "")` 过滤，可被 `..\\` 或 URL 编码绕过 |

### 2.7 path-traversal-taint (3) — 全部 TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| ProfileUploadRetrieval.java | 101 | TP | `new File(dir, id + ".jpg")` id 来自 `request.getParameter("id")` |
| Ping.java | 32 | TP | `new File(dir, "/XXE/log" + username + ".txt")` username 拼入路径 |
| FileServer.java | 79 | TP | `new File(dir, multipartFile.getOriginalFilename())` 用户文件名未校验 |

### 2.8 priv-java-runtime-exec (1) — TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| VulnerableTaskHolder.java | 67 | TP | `Runtime.getRuntime().exec(taskAction)` taskAction 来自反序列化数据 |

### 2.9 sig-java-verify-skip (1) — FP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| CryptoUtil.java | 96 | **FP** | 代码在 line 96 创建 Signature 实例，line 101 正确调用 `verify()` 并检查结果。完整验证流程无跳过 |

**根因分析**：规则 pattern 匹配 `Signature.getInstance(...)` 后检查后续是否有 `.verify()` 调用。CryptoUtil 中 verify() 在 try 块内且与 getInstance() 间隔 5 行，可能超出 pattern 匹配窗口。需调整规则 pattern 的上下文范围。

### 2.10 sqli-taint (2) — 全部 TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| Assignment5.java | 50 | TP | `prepareStatement("...where userid = '" + username_login + "'...")` 经典 SQL 注入 |
| SqlInjectionChallenge.java | 62 | TP | `"select ... where userid = '" + username + "'"` 字符串拼接 SQL |

### 2.11 xss-taint (1) — TP

| 文件 | 行 | 判定 | 说明 |
|------|---|------|------|
| Ping.java | 35 | TP | `pw.println(logLine)` 将含 userAgent/text 请求参数的内容写入文件，可被作为 HTML 渲染 |

---

## 3. 漏报分析（False Negative）

WebGoat 中存在以下已知漏洞但未被检出：

| 漏洞位置 | 类型 | 未检出原因 |
|----------|------|-----------|
| User.java:13 (`password = ""`) | 硬编码密钥 | 空字符串不匹配 `= "..."` 模式（值长度 > 0 约束） |
| CryptoUtil.java:96 | 签名验证跳过 | 规则 pattern 窗口不足（见 FP 分析） |
| 各 `@Value("${...}")` 注解 | MyBatis `${}` | Spring `@Value` 使用相同语法但非 SQL 注入 — 正确未报 |

WebGoat 的核心漏洞（SQL 注入、路径遍历、反序列化、命令注入、XSS）均被正确检出，无实质性漏报。

## 4. 规则重叠发现

`crypto-hardcoded-key-java` 与 `crypto-hardcoded-key__java` 两条规则存在 7 处重叠检出，但各自有独立覆盖：

- 仅 `__java` 覆盖：Assignment7, SampleAttack, MissingFunctionAC(x2), ResetLinkAssignment, User.java（+5 处）
- 仅 `-java` 覆盖：VerboseErrorTask:43, SqlInjectionLesson6b:42（+2 处）

**建议**：阶段一 C（规则库治理）中合并为单条规则，消除冗余。

## 5. 质量等级更新

按蓝图质量阶梯定义：

| 规则 | 盲测前等级 | 盲测后等级 | 说明 |
|------|-----------|-----------|------|
| sqli-taint | L2 | **L3** | WebGoat 2 处检出全 TP |
| xss-taint | L2 | **L3** | WebGoat 1 处检出 TP |
| deser-taint | L2 | **L3** | WebGoat 1 处检出 TP |
| path-traversal-taint | L2 | **L3** | WebGoat 3 处检出全 TP |
| log-injection-taint | L2 | **L3** | WebGoat 6 处检出全 TP |
| priv-java-runtime-exec | L2 | **L3** | WebGoat 1 处检出 TP |
| crypto-weak-random-java | L2 | **L3** | WebGoat 11 处检出全 TP |
| crypto-hardcoded-key-java | L2 | **L3** | WebGoat 13 处检出全 TP |
| cmdi-taint | L2 | L2 | WebGoat 无额外命令注入点（VulnerableTaskHolder 由 priv 规则覆盖） |
| sig-java-verify-skip | L2 | **需修复** | 1 FP，pattern 窗口需调整 |

## 6. 结论

- **精确率 97.96%**（48 TP / 49 检出），仅 1 个 FP（sig-java-verify-skip pattern 窗口不足）
- **8 条规则晋升 L3**，规则库整体质量显著提升
- 规则跨课程（CSRF/JWT/PathTraversal/Deserialization/Crypto/Challenge）泛化良好
- 无实质性漏报，Spring `@Value` 与 MyBatis `${}` 区分正确

### 后续行动

1. **修复** sig-java-verify-skip pattern 窗口（扩大上下文匹配范围）
2. **合并** crypto-hardcoded-key-java 与 crypto-hardcoded-key__java
3. **更新** capability-map-data.yaml 标记 L3 状态
4. 继续阶段一 A1-A4 批次规则扩展
