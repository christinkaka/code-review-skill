# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218
- **严重度**: HIGH
- **类型**: CORS
- **描述**: CORS 配置默认允许所有来源（`allowedOriginPatterns("*")`）且同时启用 `allowCredentials(true)`。当 `system.corsAllowedOrigins` 未在 settings.yml 中配置时，任何外部网站均可向本应用发起携带认证凭据（Cookie、JWT 令牌）的跨域请求。攻击者可构造恶意网页，利用受害者的已认证会话调用任意 API 端点，包括文件上传、数据库管理等敏感操作。虽然浏览器对 `allowedOriginPatterns("*")` + `allowCredentials(true)` 的组合存在一定限制，但 `allowedOriginPatterns` 不同于 `allowedOrigins`，Spring 会将请求的 Origin 头原样回显，从而绕过浏览器的 CORS 检查。
- **代码片段**:
```java
// 第 188 行
cfg.setAllowedOriginPatterns(List.of("*"));
// 第 218 行
cfg.setAllowCredentials(true);
```
- **修复建议**: 将默认 CORS 来源从 `"*"` 改为 `"SAMEORIGIN"` 或空列表（仅允许同源）。若必须支持跨域，要求管理员在 settings.yml 中显式配置具体的可信来源列表，并在代码中对 `allowCredentials(true)` 与通配符来源的组合进行运行时校验，禁止两者同时生效。

---

### 问题 2
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 65-66
- **严重度**: HIGH
- **类型**: XSS
- **描述**: HTML 净化、SVG 净化（SvgSanitizer）和 Office 文档净化（OfficeDocumentSanitizer）均可通过同一个配置项 `applicationProperties.getSystem().isDisableSanitize()` 完全禁用。当 `disableSanitize` 设为 `true` 时，所有 HTML/SVG/Office 文档的净化逻辑被跳过，恶意内容可原样传入后续处理链。根据 V5 标准，净化/验证可被配置禁用，即使仅管理员可配置，也必须报告为 HIGH。此配置影响 3 个净化器（CustomHtmlSanitizer、SvgSanitizer、OfficeDocumentSanitizer），按合并规则（规则 1：同一配置影响多个文件）算 1 个问题。
- **代码片段**:
```java
// CustomHtmlSanitizer.java 第 65-66 行
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java 第 59-61 行
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java 第 80-82 行
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**: 移除 `disableSanitize` 全局开关，或将其作用范围限制为非生产环境。若必须保留此开关，应增加额外的安全防护层（如 WAF 规则、输入大小限制），并在管理界面中显示明确的安全警告。同时考虑对不同净化器使用独立的开关，避免一个配置禁用所有防护。

---

### 问题 3
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath` 方法将用户提供的 `fileId` 直接传入 `Path.of(tempDirPath).resolve(fileId)`，未进行任何路径穿越检查。攻击者可传入 `../../etc/passwd` 等值，使解析后的路径指向 `tempDirPath` 之外的任意文件。与 DatabaseService.getBackupFilePath 不同（后者有 normalize + startsWith 验证），此方法完全没有路径验证逻辑。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```
- **修复建议**: 对 `fileId` 进行路径规范化后验证其是否仍在 `tempDirPath` 目录内：
```java
public Path resolveFilePath(String fileId) {
    Path baseDir = Path.of(tempDirPath).normalize().toAbsolutePath();
    Path resolved = baseDir.resolve(fileId).normalize().toAbsolutePath();
    if (!resolved.startsWith(baseDir)) {
        throw new SecurityException("Path traversal detected");
    }
    return resolved;
}
```

---

### 问题 4
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **描述**: 默认管理员账户使用硬编码的用户名 `"admin"` 和密码 `"stirling"` 进行初始化。虽然此默认账户仅在无现有用户且未配置初始登录凭据时创建，但弱默认密码在管理员未及时修改的情况下可被攻击者直接利用。与问题 1（CORS 默认配置）组合，攻击者可从外部网络使用默认凭据登录管理后台。
- **代码片段**:
```java
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";
    // ...
}
```
- **修复建议**: 在首次启动时强制要求用户设置管理员密码，而非使用硬编码默认值。若必须提供默认凭据，应在登录时检测是否为默认密码并强制修改，同时在日志和管理界面中显示安全警告。

---

### 问题 5
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269
- **严重度**: MEDIUM
- **类型**: CSRF
- **描述**: CSRF 保护被完全禁用（`http.csrf(CsrfConfigurer::disable)`）。虽然主 API 链使用 STATELESS 会话策略和 JWT 令牌认证（浏览器不会自动在跨域请求中附加自定义 Header 中的 JWT），但应用同时配置了基于 Cookie 的 remember-me 认证（14 天有效期）和表单登录处理端点 `/perform_login`。对于依赖 Cookie 的认证流程，禁用 CSRF 使得跨站请求伪造攻击成为可能。结合问题 1 的 CORS 配置（允许所有来源 + 凭据），攻击者可构造恶意页面发起跨域请求，利用受害者的 Cookie 认证执行状态变更操作。
- **代码片段**:
```java
http.csrf(CsrfConfigurer::disable);
```
- **修复建议**: 对 API 端点可保持 CSRF 禁用（因使用 JWT Header 认证），但对基于 Cookie 认证的端点（如 `/perform_login`、`/logout`、remember-me 相关端点）启用 CSRF 保护。可使用 Spring Security 的 `CsrfConfigurer` 配合 `ignoringRequestMatchers` 仅对 API 路径禁用。

---

### 问题 6
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 35-36
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `SAXSVGDocumentFactory` 创建 SVG 文档时未显式禁用外部实体（DTD、外部通用实体、外部参数实体）。虽然 Batik 的 `SAXSVGDocumentFactory` 可能有一定的默认防护，且后续渲染阶段通过自定义 `UserAgent.checkLoadExternalResource` 阻止了外部资源加载，但 XML 解析阶段本身未进行 XXE 防护。恶意 SVG 输入可在解析阶段触发外部实体解析，导致信息泄露或 SSRF。根据 V5 标准，XML 解析器未显式禁用外部实体必须报告为 MEDIUM。
- **代码片段**:
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```
- **修复建议**: 在创建 `SAXSVGDocumentFactory` 后，显式禁用外部实体和 DTD：
```java
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);
// 通过底层 XMLReader 设置安全特性
factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

---

### 问题 7
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 175-201
- **严重度**: MEDIUM
- **类型**: SSRF
- **描述**: `fetchRemoteHtml` 方法使用 `HttpClient` 向用户提供的 URL 发起 HTTP GET 请求。虽然代码进行了 URL 格式验证（`RegexPatternUtils` + `GeneralUtils.isValidURL`）和可达性检查（`GeneralUtils.isURLReachable`），并禁用了重定向跟随（`Redirect.NEVER`），但未显式验证目标 URL 是否指向内部网络地址（如 `127.0.0.0/8`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`、`::1` 等）。攻击者可使服务器向内部网络发起请求，探测内部服务或获取云环境元数据（如 `http://169.254.169.254/latest/meta-data/`）。
- **代码片段**:
```java
private String fetchRemoteHtml(String url) throws IOException, InterruptedException {
    HttpClient client =
            HttpClient.newBuilder()
                    .followRedirects(HttpClient.Redirect.NEVER)
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

    HttpRequest request =
            HttpRequest.newBuilder(URI.create(url))
                    .timeout(Duration.ofSeconds(20))
                    .GET()
                    .header("User-Agent", "Stirling-PDF/URL-to-PDF")
                    .build();

    HttpResponse<String> response =
            client.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    // ...
}
```
- **修复建议**: 在发起 HTTP 请求前，解析 URL 的主机名并验证其 IP 地址不属于内部网络范围。可使用 `InetAddress.getByName(host)` 获取 IP 后检查是否为 loopback、link-local 或私有地址。同时考虑集成 `SsrfProtectionService`（项目中已有此服务）进行统一的 SSRF 防护。

---

### 问题 8
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 478-479
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: 速率限制配置为极高值（1,000,000 请求），实质上等同于禁用。同时，`IPRateLimitingFilter` 在安全过滤链中被注释掉（第 299-304 行的 TODO 注释），完全未生效。应用缺乏任何有效的速率限制保护，使得暴力破解密码、枚举用户名、API 滥用等攻击不受约束。根据 V5 标准，速率限制配置为极高值或被禁用必须报告为 MEDIUM。
- **代码片段**:
```java
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    // Example limit TODO add config level
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}

// 第 299-304 行（过滤链中注释掉）
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op) and raw Filter
// impl causes Spring Security async dispatch bug...
// .addFilterBefore(rateLimitingFilter,
// UsernamePasswordAuthenticationFilter.class)
```
- **修复建议**: 将速率限制配置为合理值（如每分钟 60 次请求），并将 `IPRateLimitingFilter` 重新启用到安全过滤链中。对认证端点（`/login`、`/perform_login`、`/api/v1/auth/*`）应设置更严格的限制（如每分钟 5-10 次）。将速率限制值改为通过配置文件管理，而非硬编码。

---

### 问题 9
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 742-748
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: `generateMD5` 方法使用 MD5 哈希算法生成图像标识哈希值（`generateImageHash`、`generateMaskHash`、`generateDecodeParamsHash`、`generateMetadataHash`）。虽然 MD5 在此仅用于图像去重（非安全场景），但 MD5 已被密码学界认定为不安全算法（存在碰撞攻击）。根据 V5 标准，使用 MD5 或 SHA1 必须报告为 LOW，即使仅用于非安全场景。
- **代码片段**:
```java
private static byte[] generateMD5(byte[] data) {
    try {
        MessageDigest md = MessageDigest.getInstance("MD5");
        return md.digest(data);
    } catch (NoSuchAlgorithmException e) {
        throw ExceptionUtils.createMd5AlgorithmException(e);
    }
}
```
- **修复建议**: 将 MD5 替换为更安全的哈希算法如 SHA-256。由于此处仅用于去重而非密码存储，替换不会影响功能。若考虑性能，可使用 SHA-256 的截断输出（如取前 16 字节）以平衡哈希长度和碰撞概率。

---

### 问题 10
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 165-169
- **严重度**: LOW
- **类型**: Auth
- **描述**: `HttpFirewall` 配置允许参数值中包含换行符（`\r` 和 `\n`）。虽然注释说明这是为了兼容反向代理（如 Authelia）设置的非 ASCII 头值，但允许参数值中的换行符可能在某些下游组件中导致 HTTP 响应拆分或日志注入。标准 `StrictHttpFirewall` 默认拒绝此类字符。
- **代码片段**:
```java
Pattern allowedParamChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*");
firewall.setAllowedParameterValues(
        parameterValue ->
                parameterValue != null
                        && allowedParamChars.matcher(parameterValue).matches());
```
- **修复建议**: 评估是否确实需要在参数值中允许换行符。若仅为头值兼容需求，应仅放宽 `setAllowedHeaderValues` 而不放宽 `setAllowedParameterValues`。若必须允许，应在所有消费用户输入的下游代码中确保换行符被正确转义。

---

## 12 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题 -- 所有 SQL 操作均使用 PreparedStatement 参数化查询（DatabaseService 中 RUNSCRIPT/SCRIPT 均使用 `?` 占位符），无字符串拼接 SQL |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 2（disableSanitize 可禁用全部 HTML/SVG/Office 净化） |
| 3. XML 外部实体 (XXE) | 已检查 | 问题 6（SvgOverlayUtil 的 SAXSVGDocumentFactory 未显式禁用外部实体） |
| 4. 路径穿越 | 已检查 | 问题 3（FileOrUploadService.resolveFilePath 无路径穿越验证） |
| 5. 命令注入 | 已检查 | 无问题 -- 所有外部命令通过 ProcessBuilder 列表形式构建，不使用 shell=True；ProcessExecutor.validateCommand 验证命令参数不含空字节和换行符 |
| 6. SSRF | 已检查 | 问题 7（ConvertWebsiteToPDF 的 fetchRemoteHtml 未验证目标 URL 是否为内部 IP） |
| 7. 文件上传/下载 | 已检查 | 无问题 -- DatabaseController 的导入端点有 ADMIN 权限保护且通过 SQL 白名单验证；下载端点限制 backup_*.sql 命名模式；DatabaseService.getBackupFilePath 有路径穿越检查 |
| 8. 硬编码密钥/密码 | 已检查 | 问题 4（默认管理员凭据 admin/stirling）、问题 9（MD5 哈希算法用于图像去重） |
| 9. CSRF 保护 | 已检查 | 问题 5（CSRF 被完全禁用，Cookie 认证流程缺乏 CSRF 防护） |
| 10. CORS 配置 | 已检查 | 问题 1（默认允许所有来源 + allowCredentials=true） |
| 11. 认证授权 | 已检查 | 问题 8（速率限制配置为 100 万且过滤链中被注释禁用） |
| 12. 会话管理 | 已检查 | 无问题 -- 主 API 链使用 STATELESS 策略；SAML 链使用 IF_REQUIRED；remember-me 配置 14 天有效期并启用 secure cookie；logout 正确清除会话和 Cookie |

---

## 18 文件评审覆盖确认

| 文件 | 已评审 | 涉及问题 |
|------|--------|----------|
| `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java` | 是 | 问题 7 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java` | 是 | 问题 9 |
| `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java` | 是 | 问题 6 |
| `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java` | 是 | 问题 3 |
| `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java` | 是 | 问题 2 |
| `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java` | 是 | 问题 2 |
| `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java` | 是 | 问题 2 |
| `app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/integration/crypto/CredentialEncryption.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java` | 是 | 问题 4 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java` | 是 | 问题 1, 5, 8, 10 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/service/DatabaseService.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/ExtractImageScansController.java` | 是 | 无问题 |
| `app/common/src/main/java/stirling/software/common/util/PDFToFile.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/pipeline/PipelineProcessor.java` | 是 | 无问题 |

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 5 |
| LOW | 2 |
| **总计** | **10** |

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
| HardcodedSecret | 2 |
| CSRF | 1 |
| CORS | 1 |
| Auth | 2 |
| Session | 0 |

---

## 正面发现

1. **SQL 注入防护完善**: DatabaseService 中所有 SQL 操作均使用 PreparedStatement 参数化查询，并实现了完善的 SQL 内容验证机制（白名单 + 黑名单），有效防止恶意 SQL 脚本通过备份导入执行。

2. **XML 解析安全**: SvgSanitizer 和 OfficeDocumentSanitizer 中的 DocumentBuilderFactory 正确配置了全部 XXE 防护特性（禁用 DTD、外部通用实体、外部参数实体、外部 DTD 加载），是良好的安全实践。

3. **命令注入防护**: ProcessExecutor 统一使用 ProcessBuilder 列表形式构建命令（非 shell 拼接），并实现了 validateCommand 方法验证命令参数不含空字节、换行符，且验证可执行文件路径不含路径穿越。

4. **凭据加密实现规范**: CredentialEncryption 使用 AES-256-GCM 算法，密钥支持配置、环境变量或自动生成文件三种来源，密钥文件权限设为 0600（仅所有者可读写），集群模式下强制要求共享密钥。

5. **SVG 安全渲染**: SvgOverlayUtil 通过自定义 UserAgent 的 checkLoadExternalResource 方法阻止 SVG 渲染阶段加载外部资源（仅允许 data: URI），有效防止 SVG 外部资源泄露。

6. **路径穿越防护（部分）**: DatabaseService.getBackupFilePath 正确实现了路径规范化 + startsWith 验证模式；PipelineProcessor.generateInputFiles 也对文件名进行了路径穿越检查。

7. **文件上传安全**: DatabaseController 的 SQL 导入端点有 ADMIN 权限保护（`@PreAuthorize("hasRole('ADMIN')")`），下载端点限制文件命名模式（`backup_*.sql`），防止任意文件下载。

8. **ZIP 安全处理**: OfficeDocumentSanitizer 使用 `ZipSecurity.createHardenedInputStream` 防止 ZIP 炸弹攻击。

9. **URL 安全策略**: CustomHtmlSanitizer 中的 SSRF_SAFE_URL_POLICY 通过 SsrfProtectionService 验证 HTML 中 URL 属性的安全性，SvgSanitizer 也对 SVG 中的 URL 属性进行了 SSRF 检查。

---

## 关键风险总结

1. **CORS 配置错误（HIGH）**: 默认允许所有来源 + 凭据的组合是最严重的发现。任何外部网站可利用受害者的认证会话调用 API，可能导致数据泄露或未授权操作。需立即修复默认配置。

2. **净化开关可全局禁用（HIGH）**: `disableSanitize` 配置可完全禁用 HTML、SVG 和 Office 文档的所有安全净化，使应用暴露于 XSS、SVG 攻击和外部实体注入等风险。应移除此全局开关或限制为仅非生产环境可用。

3. **路径穿越漏洞（HIGH）**: FileOrUploadService.resolveFilePath 完全缺乏路径验证，允许攻击者访问服务器上的任意文件。需立即添加路径规范化和前缀验证。

4. **CSRF + CORS 组合风险（HIGH 组合）**: CSRF 禁用（问题 5）与 CORS 配置错误（问题 1）组合形成完整攻击链。攻击者可从任意外部网站发起携带认证凭据的跨域请求，且无 CSRF 令牌验证。建议优先修复此组合漏洞。

5. **SSRF 缺乏内部 IP 验证（MEDIUM）**: URL 转 PDF 功能允许服务器向任意 URL 发起请求，未验证目标是否为内部网络地址。攻击者可探测内部服务或获取云元数据。

---

## 评审检查清单

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用组合漏洞判定规则（问题 1 + 问题 5 形成 CSRF + CORS 组合链）
- [x] 已应用问题合并规则（问题 2 合并 CustomHtmlSanitizer/SvgSanitizer/OfficeDocumentSanitizer 的 disableSanitize 为 1 个问题）
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题
- [x] 已对每个维度给出明确结论

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Kappa
