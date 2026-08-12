# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 13 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session, HttpFirewall）

---

## 发现的问题

### 问题 1
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 65-66
- **严重度**: HIGH
- **类型**: XSS
- **描述**: `disableSanitize` 配置项可完全禁用 HTML/SVG/Office 文档净化器。当 `applicationProperties.getSystem().isDisableSanitize()` 返回 `true` 时，`CustomHtmlSanitizer.sanitize()` 直接返回原始 HTML 而不做任何净化处理。同一配置项同时影响 `SvgSanitizer.sanitize()`（第 59 行）和 `OfficeDocumentSanitizer.sanitize()`（第 80 行），三个净化器全部被绕过。攻击者可提交包含恶意 JavaScript 的 HTML/SVG 内容，在受害者浏览器中执行任意脚本（存储型/反射型 XSS）。即使仅管理员可配置此选项，影响范围过大，按 V6 锁定规则标记为 HIGH，禁止降级。
- **代码片段**:
```java
// CustomHtmlSanitizer.java 第 64-67 行
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java 第 59-62 行
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java 第 80-83 行
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**: 移除 `disableSanitize` 全局开关，或将其限制为仅影响特定非关键场景。净化器应始终对用户上传的内容执行，不可通过配置完全禁用。如确需保留，应增加额外的安全约束（如仅对受信输入源跳过净化）。

---

### 问题 2
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218, 269
- **严重度**: HIGH
- **类型**: CSRF/CORS（组合漏洞）
- **描述**: CSRF 禁用 + CORS `allowedOriginPatterns("*")` + `allowCredentials(true)` + Cookie 认证形成完整跨域攻击链。具体分析：
  1. **CSRF 完全禁用**（第 269 行）：`http.csrf(CsrfConfigurer::disable)`
  2. **CORS 默认允许所有源**（第 188 行）：当 `settings.yml` 未配置 `corsAllowedOrigins` 时，默认使用 `allowedOriginPatterns(List.of("*"))`
  3. **allowCredentials=true**（第 218 行）：`cfg.setAllowCredentials(true)`
  4. **Cookie 认证**（第 336 行）：使用 `JSESSIONID`、`remember-me`、`stirling_jwt` 等 Cookie

  攻击者可从恶意网站发起跨域请求，浏览器会自动携带用户的认证 Cookie，从而以受害者身份执行任意操作（文件上传、数据库导入、密码修改等）。按 V6 组合漏洞规则，合并为 1 个 HIGH 问题，禁止降级。
- **代码片段**:
```java
// 第 188 行 - CORS 默认允许所有源
cfg.setAllowedOriginPatterns(List.of("*"));

// 第 218 行 - 允许携带凭据
cfg.setAllowCredentials(true);

// 第 269 行 - CSRF 完全禁用
http.csrf(CsrfConfigurer::disable);

// 第 336 行 - Cookie 认证
.deleteCookies("JSESSIONID", "remember-me", "stirling_jwt"));
```
- **修复建议**: (1) 启用 CSRF 保护，至少对 state-changing 操作（POST/PUT/DELETE）启用；(2) CORS 默认配置不应使用 `*`，应要求管理员显式配置允许的源；(3) 当 `allowCredentials=true` 时，`allowedOriginPatterns` 绝不应为 `*`。

---

### 问题 3
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 36
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `SAXSVGDocumentFactory` 创建 SVG 文档时未显式禁用外部实体（DOCTYPE、external-general-entities、external-parameter-entities）。虽然第 43-56 行的 `UserAgent` 在渲染阶段阻止了外部资源加载（`checkLoadExternalResource`），但初始 XML 解析阶段（第 40 行 `factory.createSVGDocument`）仍可能受到实体扩展攻击（Billion Laughs / XML Bomb）。按 V6 锁定规则，`SAXSVGDocumentFactory` 未禁用外部实体标记为 MEDIUM，禁止降级。
- **代码片段**:
```java
// 第 35-41 行 - 未禁用外部实体
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```
- **修复建议**: 在创建 `SAXSVGDocumentFactory` 后，通过设置底层 XMLReader 的属性来禁用外部实体：
```java
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

---

### 问题 4
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath()` 方法将用户可控的 `fileId` 参数直接传入 `Path.of(tempDirPath).resolve(fileId)`，未进行任何路径验证（无路径规范化、无前缀检查）。攻击者可传入 `../../etc/passwd` 等包含路径穿越序列的 `fileId`，访问临时目录之外的任意文件。按 V6 锁定规则，`Path.resolve(userInput)` 无验证标记为 HIGH，禁止降级。
- **代码片段**:
```java
// 第 20-22 行
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
    // 无路径规范化、无前缀验证
}
```
- **修复建议**: 对 `fileId` 进行路径规范化和前缀验证：
```java
public Path resolveFilePath(String fileId) {
    Path basePath = Path.of(tempDirPath).normalize().toAbsolutePath();
    Path resolved = basePath.resolve(fileId).normalize().toAbsolutePath();
    if (!resolved.startsWith(basePath)) {
        throw new SecurityException("Path traversal detected: " + fileId);
    }
    return resolved;
}
```

---

### 问题 5
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 175-201
- **严重度**: MEDIUM
- **类型**: SSRF
- **描述**: `fetchRemoteHtml()` 方法使用 `HttpClient` 获取用户提供的 URL 内容，但未验证目标 IP 地址是否为内网地址。虽然代码检查了 `file:` 协议（第 203-210 行 `containsDisallowedUriScheme`），并通过 `RegexPatternUtils` 和 `GeneralUtils.isValidURL()` 验证了 URL 格式，但未阻止对 `127.0.0.1`、`169.254.x.x`、`10.x.x.x`、`172.16-31.x.x`、`192.168.x.x` 等内网 IP 的请求。攻击者可利用此漏洞探测和访问内网服务。按 V6 锁定规则，SSRF 未验证内网 IP 标记为 MEDIUM，禁止降级。
- **代码片段**:
```java
// 第 175-201 行 - 未验证内网 IP
private String fetchRemoteHtml(String url) throws IOException, InterruptedException {
    HttpClient client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NEVER)
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    HttpRequest request = HttpRequest.newBuilder(URI.create(url))
            .timeout(Duration.ofSeconds(20))
            .GET()
            .header("User-Agent", "Stirling-PDF/URL-to-PDF")
            .build();

    HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    // ...
}
```
- **修复建议**: 在发起 HTTP 请求前，解析 URL 中的主机名并验证其 IP 地址不属于内网范围（RFC 1918 私有地址、环回地址、链路本地地址等）。可使用 DNS 解析后检查 IP 的方式，或引入 SSRF 保护服务（项目中已有 `SsrfProtectionService`）。

---

### 问题 6
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **描述**: `createDefaultAdminUser()` 方法中硬编码了默认管理员凭据：用户名 `admin`、密码 `stirling`。当未通过 `applicationProperties.getSecurity().getInitialLogin()` 配置初始管理员账号时，系统自动创建此默认管理员。该管理员具有 `ADMIN` 角色和完整权限。按 V6 锁定规则，硬编码管理员凭据标记为 MEDIUM，禁止降级。
- **代码片段**:
```java
// 第 153-155 行
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";
    // ...
}
```
- **修复建议**: (1) 首次启动时强制要求用户设置管理员密码，不使用硬编码默认值；(2) 如必须保留默认凭据，应在首次登录后强制修改密码，并在日志和管理界面中发出醒目警告；(3) 生成的默认密码应使用安全随机数。

---

### 问题 7
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 165-169
- **严重度**: LOW
- **类型**: HttpFirewall
- **描述**: `httpFirewall()` 方法中 `setAllowedParameterValues` 的正则表达式显式允许了 `\r`（CR）和 `\n`（LF）换行符。正则 `[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*` 在排除控制字符的同时又将 `\r` 和 `\n` 添加回来。虽然 `setAllowedHeaderValues`（第 161 行）正确排除了所有控制字符，但参数值中允许换行符可能被用于 HTTP 响应拆分攻击。按 V6 锁定规则，HttpFirewall 允许参数值换行符标记为 LOW。
- **代码片段**:
```java
// 第 165-169 行
Pattern allowedParamChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*");
firewall.setAllowedParameterValues(
        parameterValue ->
                parameterValue != null
                        && allowedParamChars.matcher(parameterValue).matches());
```
- **修复建议**: 从参数值允许字符集中移除 `\r` 和 `\n`，使用与 header 值相同的正则表达式：
```java
Pattern allowedParamChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]]*");
```

---

### 问题 8
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269, 476-479
- **严重度**: MEDIUM
- **类型**: Auth（组合漏洞：CSRF 禁用 + 速率限制禁用）
- **描述**: CSRF 保护完全禁用（第 269 行）与速率限制实质禁用组合形成暴力破解防护缺失。具体分析：
  1. **CSRF 完全禁用**（第 269 行）：`http.csrf(CsrfConfigurer::disable)`
  2. **速率限制被注释禁用**（第 300-304 行）：`IPRateLimitingFilter` 的注册代码被完全注释掉，并标注 `TODO`
  3. **速率限制值极高**（第 478-479 行）：`maxRequestsPerIp = 1000000`（100 万次请求），即使启用也形同虚设

  攻击者可不受限制地发起暴力破解攻击（如登录尝试、密码枚举）。按 V6 组合漏洞规则，CSRF 禁用 + 速率限制禁用合并为 1 个 MEDIUM 问题，禁止降级。
- **代码片段**:
```java
// 第 269 行 - CSRF 禁用
http.csrf(CsrfConfigurer::disable);

// 第 299-304 行 - 速率限制被注释禁用
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op) and raw Filter
// impl causes Spring Security async dispatch bug...
// .addFilterBefore(rateLimitingFilter,
//         UsernamePasswordAuthenticationFilter.class)

// 第 476-479 行 - 速率限制值极高
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
```
- **修复建议**: (1) 将 `IPRateLimitingFilter` 转换为 `OncePerRequestFilter` 并重新启用；(2) 将速率限制值降低到合理范围（如每分钟 60 次）；(3) 对登录端点实施更严格的速率限制（如每分钟 5 次）；(4) 将速率限制配置化，支持通过 `settings.yml` 调整。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题 - DatabaseService 全部使用 PreparedStatement 参数化查询，无 SQL 字符串拼接或 Statement.execute() |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 1（disableSanitize 绕过净化器，HIGH） |
| 3. XML 外部实体 (XXE) | 已检查 | 问题 3（SAXSVGDocumentFactory 未禁用外部实体，MEDIUM） |
| 4. 路径穿越 | 已检查 | 问题 4（FileOrUploadService Path.resolve 无验证，HIGH） |
| 5. 命令注入 | 已检查 | 无问题 - ProcessExecutor 使用 ProcessBuilder(List) 列表形式避免 shell 注入，validateCommand() 验证空字节和换行符，所有命令参数均为硬编码或临时文件路径 |
| 6. SSRF | 已检查 | 问题 5（ConvertWebsiteToPDF 未验证内网 IP，MEDIUM） |
| 7. 文件上传/下载 | 已检查 | 无问题 - StampController 验证文件名不含 `..` 和 `/`；DatabaseController 使用白名单验证（backup_ 前缀 + .sql 后缀）和路径穿越检测；DatabaseService.getBackupFilePath 有 normalize + startsWith 验证 |
| 8. 硬编码密钥/密码 | 已检查 | 问题 6（硬编码管理员凭据 admin/stirling，MEDIUM）；CompressController 使用 MD5 用于图像去重（非安全场景，LOW - 按合并规则归入问题 6 同一维度但不单独计数，因 MD5 仅用于内容哈希去重属于最佳实践违反） |
| 9. CSRF 保护 | 已检查 | 问题 2（CSRF 禁用参与跨域攻击链组合，HIGH）；问题 8（CSRF 禁用参与暴力破解防护缺失组合，MEDIUM） |
| 10. CORS 配置 | 已检查 | 问题 2（CORS * + allowCredentials + CSRF 禁用组合，HIGH） |
| 11. 认证授权 | 已检查 | 问题 8（速率限制禁用与 CSRF 禁用组合，MEDIUM） |
| 12. 会话管理 | 已检查 | 无问题 - 使用 SessionCreationPolicy.STATELESS（API 链）和 IF_REQUIRED（SAML 链）；RememberMe 14 天有效期合理；JWT 令牌有过期配置；Cookie 设置了 secure 标志 |
| 13. HttpFirewall | 已检查 | 问题 7（参数值允许换行符，LOW） |

---

## 18 文件评审覆盖确认

| 文件 | 已评审 | 涉及问题 |
|------|--------|----------|
| `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java` | 是 | 问题 5（SSRF） |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java` | 是 | 无问题（MD5 用于非安全场景的图像去重） |
| `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java` | 是 | 问题 3（XXE） |
| `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java` | 是 | 问题 4（路径穿越） |
| `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java` | 是 | 问题 1（XSS disableSanitize） |
| `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java` | 是 | 问题 1（XSS disableSanitize，同一配置） |
| `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java` | 是 | 问题 1（XSS disableSanitize，同一配置） |
| `app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/integration/crypto/CredentialEncryption.java` | 是 | 无问题 - AES-256-GCM 加密实现良好，密钥管理安全（0600 权限） |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java` | 是 | 问题 6（硬编码管理员凭据） |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java` | 是 | 问题 2（CSRF/CORS 组合）、问题 7（HttpFirewall）、问题 8（速率限制） |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java` | 是 | 无问题 - 有 @PreAuthorize("hasRole('ADMIN')") 保护，文件名验证完善 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/service/DatabaseService.java` | 是 | 无问题 - PreparedStatement 参数化查询，SQL 白名单验证，路径穿越防护完善 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/ExtractImageScansController.java` | 是 | 无问题 - 命令参数均为数值类型，ProcessBuilder 列表形式避免注入 |
| `app/common/src/main/java/stirling/software/common/util/PDFToFile.java` | 是 | 无问题 - 使用 Filenames.toSimpleFileName() 清理文件名，ProcessBuilder 列表形式 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/pipeline/PipelineProcessor.java` | 是 | 无问题 - 操作通过 apiDocService.isValidOperation() 验证，使用内部 API 调用 |

---

## 严重度确认清单

- [x] 所有 disableSanitize 问题标记为 HIGH -- 问题 1 标记为 HIGH，未降级
- [x] 所有 CORS `*` + allowCredentials 标记为 HIGH -- 问题 2 中 CORS `*` + allowCredentials + CSRF 禁用合并为 HIGH，未降级
- [x] 所有 Path.resolve 无验证标记为 HIGH -- 问题 4 标记为 HIGH，未降级
- [x] 所有硬编码管理员凭据标记为 MEDIUM -- 问题 6 标记为 MEDIUM，未降级
- [x] 所有 SSRF 未验证内网 IP 标记为 MEDIUM -- 问题 5 标记为 MEDIUM，未降级
- [x] 所有 SAXSVGDocumentFactory 未禁用外部实体标记为 MEDIUM -- 问题 3 标记为 MEDIUM，未降级
- [x] 所有速率限制禁用标记为 MEDIUM -- 问题 8 标记为 MEDIUM，未降级
- [x] 所有 MD5/SHA1 标记为 LOW -- CompressController 中 MD5 用于图像去重（非安全场景），属于 LOW 最佳实践违反，已在维度 8 说明，不单独计数
- [x] 所有 HttpFirewall 换行符标记为 LOW -- 问题 7 标记为 LOW，未降级
- [x] CSRF + CORS + Cookie 认证合并为 1 个 HIGH -- 问题 2 合并了 CSRF 禁用 + CORS `*` + allowCredentials(true) + Cookie 认证为 1 个 HIGH 问题
- [x] CSRF + 速率限制合并为 1 个 MEDIUM -- 问题 8 合并了 CSRF 禁用 + 速率限制禁用为 1 个 MEDIUM 问题
- [x] 同一配置影响多个文件合并为 1 个问题 -- 问题 1 将 `disableSanitize` 影响 CustomHtmlSanitizer/SvgSanitizer/OfficeDocumentSanitizer 三个文件合并为 1 个问题

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 1 |
| **总计** | **8** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| SQLi | 0 |
| XSS | 1 |
| XXE | 1 |
| PathTraversal | 1 |
| CommandInjection | 0 |
| SSRF | 1 |
| FileUpload | 0 |
| HardcodedSecret | 1 |
| CSRF | 0（已合并入问题 2 和问题 8） |
| CORS | 0（已合并入问题 2） |
| Auth | 1 |
| Session | 0 |
| HttpFirewall | 1 |

---

## 正面发现

1. **SQL 注入防护完善**: `DatabaseService` 全部使用 `PreparedStatement` 参数化查询，并实现了 SQL 内容白名单验证（`ALLOWED_PATTERNS`）和危险函数黑名单（`DENIED_PATTERNS`），有效防止了 SQL 注入攻击。

2. **XML 解析安全**: `SvgSanitizer` 和 `OfficeDocumentSanitizer` 中的 `DocumentBuilderFactory` 正确禁用了所有外部实体（FEATURE_SECURE_PROCESSING、disallow-doctype-decl、external-general-entities、external-parameter-entities、load-external-dtd），是 XXE 防护的最佳实践。

3. **命令注入防护**: `ProcessExecutor.validateCommand()` 实现了全面的命令验证：检查空字节、换行符、路径穿越，验证可执行文件存在性。所有 `ProcessBuilder` 调用均使用列表形式（非 shell 字符串），避免 shell 注入。

4. **凭据加密实现良好**: `CredentialEncryption` 使用 AES-256-GCM 算法，密钥文件权限设置为 0600（仅所有者可读写），支持环境变量和配置文件两种密钥来源，集群模式强制要求共享密钥。

5. **路径穿越防护**: `DatabaseService.getBackupFilePath()` 正确使用了 `normalize()` + `startsWith()` 双重验证；`DatabaseController` 的文件名验证（`isValidFileName`）排除了所有危险字符。

6. **SVG 安全处理**: `SvgSanitizer` 实现了全面的 SVG 净化：移除危险元素（script、foreignobject、iframe 等）、移除事件处理器属性、检测 JavaScript URL、多轮 URL 解码防止绕过、SSRF URL 验证。

7. **临时文件管理**: 项目广泛使用 `TempFile` + `TempFileManager` 进行临时文件生命周期管理，配合 try-with-resources 确保文件清理。

8. **Zip 安全处理**: `OfficeDocumentSanitizer` 使用 `ZipSecurity.createHardenedInputStream()` 防止 Zip Bomb 攻击。

---

## 关键风险总结

1. **[HIGH] disableSanitize 全局净化绕过**: 单一配置开关可同时禁用 HTML、SVG、Office 文档三个净化器，使系统完全暴露于 XSS 和 SVG 注入攻击。这是最严重的架构级风险，建议从根本上移除此全局开关。

2. **[HIGH] CSRF + CORS + Cookie 跨域攻击链**: CSRF 完全禁用、CORS 默认允许所有源并携带凭据，攻击者可从任意恶意网站以受害者身份执行操作。这是最容易被利用的高危漏洞组合。

3. **[HIGH] FileOrUploadService 路径穿越**: `Path.resolve(userInput)` 无任何验证，可直接访问服务器任意文件。此漏洞可被直接利用，无需特殊条件。

4. **[MEDIUM] SSRF 未验证内网 IP**: URL-to-PDF 功能可被利用探测和访问内网服务，获取内部系统信息或触发内部 API。

5. **[MEDIUM] 硬编码管理员凭据 + 速率限制缺失**: 默认 admin/stirling 凭据结合完全禁用的速率限制，使暴力破解攻击毫无阻碍。

---

## 评审完成时间

**评审完成时间**: 2026-08-12
**评审者**: Agent Lambda
