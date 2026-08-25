# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 13 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session, HttpFirewall）

---

## 发现的问题

### 问题 1
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269, 188, 218
- **严重度**: HIGH
- **类型**: CSRF/CORS
- **描述**: CSRF 保护被完全禁用（第 269 行），CORS 配置允许所有来源（`allowedOriginPatterns("*")`，第 188 行）且允许凭证（`allowCredentials(true)`，第 218 行），应用使用 Cookie 认证（remember-me cookie，第 336 行）。此组合形成完整的跨域攻击链：攻击者可以从恶意网站发起跨域请求，浏览器会自动携带用户的认证 Cookie，从而执行未授权操作。
- **代码片段**:
```java
// 第 269 行：CSRF 被完全禁用
http.csrf(CsrfConfigurer::disable);

// 第 188 行：允许所有来源
cfg.setAllowedOriginPatterns(List.of("*"));

// 第 218 行：允许凭证
cfg.setAllowCredentials(true);

// 第 336 行：使用 Cookie 认证
.deleteCookies("JSESSIONID", "remember-me", "stirling_jwt");
```
- **修复建议**: 
  1. 启用 CSRF 保护，使用 `CsrfConfigurer` 的默认配置或配置 CSRF token 存储
  2. 将 CORS `allowedOriginPatterns` 配置为具体的可信来源列表，禁止使用 `"*"`
  3. 如果必须允许凭证，则 `allowedOriginPatterns` 不能为 `"*"`

### 问题 2
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`, `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java`, `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java`
- **行号**: CustomHtmlSanitizer.java:66, SvgSanitizer.java:59, OfficeDocumentSanitizer.java:80
- **严重度**: HIGH
- **类型**: XSS
- **描述**: 三个净化器类均检查 `applicationProperties.getSystem().isDisableSanitize()` 配置项，当该配置为 `true` 时，所有 HTML/SVG/Office 文档净化被完全绕过。攻击者可以上传包含恶意 JavaScript 的 HTML/SVG 文件，或包含外部实体引用的 Office 文档，导致 XSS 攻击或信息泄露。即使仅管理员可配置，该配置的影响范围过大，违反最小权限原则。
- **代码片段**:
```java
// CustomHtmlSanitizer.java 第 66 行
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java 第 59 行
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java 第 80 行
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**: 
  1. 移除 `disableSanitize` 配置项，或将其限制为仅在开发环境生效
  2. 如果必须保留该配置，应添加额外的安全控制（如需要重启应用、记录审计日志）
  3. 考虑提供细粒度的净化控制，而非全局开关

### 问题 3
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath` 方法直接使用 `Path.resolve(fileId)` 解析用户输入的文件 ID，未进行任何路径验证或规范化。攻击者可以提供包含 `../` 的文件 ID，实现路径穿越，访问或修改服务器上的任意文件。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```
- **修复建议**: 
  1. 对 `fileId` 进行路径规范化：`Path normalizedPath = Path.of(tempDirPath).resolve(fileId).normalize()`
  2. 验证规范化后的路径仍在基础目录内：`if (!normalizedPath.startsWith(tempDirPath)) throw new SecurityException("Path traversal detected")`
  3. 参考 `DatabaseService.getBackupFilePath()` 的实现（第 477-480 行）

### 问题 4
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269, 478
- **严重度**: MEDIUM
- **类型**: CSRF/Auth
- **描述**: CSRF 保护被完全禁用（第 269 行），且速率限制过滤器被注释掉（第 299-304 行），实际限制值为 1000000 请求（第 478 行），相当于无限制。此组合使得暴力破解攻击成为可能：攻击者可以无限制地尝试登录，且无需 CSRF token。
- **代码片段**:
```java
// 第 269 行：CSRF 被禁用
http.csrf(CsrfConfigurer::disable);

// 第 299-304 行：速率限制过滤器被注释掉
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op) and raw Filter
// impl causes Spring Security async dispatch bug (response already committed
// errors on StreamingResponseBody endpoints). Re-enable once converted to
// OncePerRequestFilter with proper config-driven limits.
// .addFilterBefore(rateLimitingFilter,
// UsernamePasswordAuthenticationFilter.class)

// 第 478 行：限制值为 1000000
int maxRequestsPerIp = 1000000;
```
- **修复建议**: 
  1. 启用 CSRF 保护
  2. 修复 `IPRateLimitingFilter` 的 Spring Security 异步分发问题，重新启用速率限制
  3. 将速率限制值降低到合理水平（如 100 请求/分钟）
  4. 为登录端点配置更严格的速率限制（如 5 次失败/分钟）

### 问题 5
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **描述**: 代码中硬编码了默认管理员凭据 `admin`/`stirling`（第 154-155 行）。虽然该凭据仅在未配置初始管理员时创建，且设置了 `firstLogin=true` 标志，但如果用户未修改默认凭据，攻击者可以使用这些凭据获得管理员权限。
- **代码片段**:
```java
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";

    if (userService.findByUsernameIgnoreCase(defaultUsername).isEmpty()) {
        // ... 创建管理员用户
    }
}
```
- **修复建议**: 
  1. 在首次登录时强制要求修改默认密码
  2. 在应用启动时检测默认凭据并显示警告
  3. 考虑使用随机生成的初始密码，并在启动日志中输出
  4. 添加文档说明必须修改默认凭据

### 问题 6
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 116, 175-201
- **严重度**: MEDIUM
- **类型**: SSRF
- **描述**: `fetchRemoteHtml` 方法使用 `HttpClient` 获取用户提供的 URL 内容，但未验证目标 IP 地址是否为内网地址。攻击者可以提供指向内网资源的 URL（如 `http://127.0.0.1`、`http://169.254.169.254`、`http://10.0.0.1`），访问内部服务或云元数据 API。
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
- **修复建议**: 
  1. 在发起请求前解析 URL 的主机名，验证解析后的 IP 地址不是内网地址
  2. 阻止以下 IP 范围：`127.0.0.0/8`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`
  3. 使用 SSRF 保护服务（如 `SsrfProtectionService`）验证 URL
  4. 限制允许的协议为 `http` 和 `https`

### 问题 7
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 36
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `SAXSVGDocumentFactory` 创建 SVG 文档时未显式禁用外部实体。虽然 Batik 的 `UserAgent` 在渲染阶段阻止了外部资源加载，但 XML 解析阶段仍可能受到 XXE 攻击，导致本地文件读取或 SSRF。
- **代码片段**:
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```
- **修复建议**: 
  1. 在创建 `SAXSVGDocumentFactory` 后，配置底层 XML 解析器禁用外部实体：
     ```java
     factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
     factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
     factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
     ```
  2. 参考 `SvgSanitizer.parseSecurely()` 的实现（第 84-100 行）

### 问题 8
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 315-344, 401-427, 716-739, 742-749
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: 代码使用 MD5 算法生成图像哈希（第 315-344 行、401-427 行、716-739 行）。虽然 MD5 仅用于非安全场景（图像去重），但 MD5 已被证明存在碰撞攻击，不推荐用于任何新代码。
- **代码片段**:
```java
private static byte[] generateMD5(byte[] data) {
    try {
        MessageDigest md = MessageDigest.getInstance("MD5");
        return md.digest(data); // Get the MD5 hash of the image bytes
    } catch (NoSuchAlgorithmException e) {
        throw ExceptionUtils.createMd5AlgorithmException(e);
    }
}
```
- **修复建议**: 
  1. 将 MD5 替换为 SHA-256 或其他安全的哈希算法
  2. 如果性能是关键考虑，可以使用 BLAKE3 或 SHA-3
  3. 添加注释说明哈希算法仅用于非安全场景

### 问题 9
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 165-169
- **严重度**: LOW
- **类型**: HttpFirewall
- **描述**: `HttpFirewall` 配置允许参数值中包含换行符（`\r`、`\n`），这可能导致 HTTP 响应拆分攻击。正则表达式 `[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*` 明确允许了控制字符中的 `\r` 和 `\n`。
- **代码片段**:
```java
// Allow non-ASCII characters and newlines in parameter values.
Pattern allowedParamChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*");
firewall.setAllowedParameterValues(
        parameterValue ->
                parameterValue != null
                        && allowedParamChars.matcher(parameterValue).matches());
```
- **修复建议**: 
  1. 从正则表达式中移除 `\\r\\n`，禁止参数值中包含换行符
  2. 使用更严格的正则表达式：`[\\p{IsAssigned}&&[^\\p{IsControl}]]*`
  3. 参考 `setAllowedHeaderValues` 的配置（第 161 行），该配置已正确禁止控制字符

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题。所有 SQL 查询均使用 `PreparedStatement` 参数化查询，未发现字符串拼接或 MyBatis `${}` 占位符 |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 2（disableSanitize 配置可禁用净化器） |
| 3. XML 外部实体 (XXE) | 已检查 | 问题 7（SAXSVGDocumentFactory 未禁用外部实体） |
| 4. 路径穿越 | 已检查 | 问题 3（FileOrUploadService.resolveFilePath 无验证） |
| 5. 命令注入 | 已检查 | 无问题。ProcessExecutor 使用 `ProcessBuilder` 列表形式，避免了 shell 注入；validateCommand 方法验证了命令参数 |
| 6. SSRF | 已检查 | 问题 6（ConvertWebsiteToPDF 未验证内网 IP） |
| 7. 文件上传/下载 | 已检查 | 无问题。文件上传接口验证了文件类型和文件名；DatabaseController 的 SQL 文件导入有 SQL 内容验证 |
| 8. 硬编码密钥/密码 | 已检查 | 问题 5（默认管理员凭据）、问题 8（MD5 用于非安全场景） |
| 9. CSRF 保护 | 已检查 | 问题 1（CSRF 禁用 + CORS * + allowCredentials + Cookie 认证，合并为 HIGH）、问题 4（CSRF 禁用 + 速率限制禁用，合并为 MEDIUM） |
| 10. CORS 配置 | 已检查 | 已合并到问题 1（CORS * + allowCredentials + CSRF 禁用 + Cookie 认证） |
| 11. 认证授权 | 已检查 | 已合并到问题 4（CSRF 禁用 + 速率限制禁用） |
| 12. 会话管理 | 已检查 | 无问题。JWT token 有效期配置合理（Web 用户默认值、桌面客户端 30 天）；remember-me cookie 配置了 secure 标志 |
| 13. HttpFirewall | 已检查 | 问题 9（允许参数值中包含换行符） |

---

## 18 文件评审覆盖确认

| 文件 | 已评审 | 涉及问题 |
|------|--------|----------|
| `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java` | 是 | 问题 6（SSRF） |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java` | 是 | 问题 8（MD5） |
| `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java` | 是 | 问题 7（XXE） |
| `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java` | 是 | 问题 3（路径穿越） |
| `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java` | 是 | 问题 2（disableSanitize） |
| `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java` | 是 | 问题 2（disableSanitize） |
| `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java` | 是 | 问题 2（disableSanitize） |
| `app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/integration/crypto/CredentialEncryption.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java` | 是 | 问题 5（硬编码凭据） |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java` | 是 | 问题 1（CSRF+CORS）、问题 4（CSRF+速率限制）、问题 9（HttpFirewall） |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/service/DatabaseService.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/ExtractImageScansController.java` | 是 | 无问题 |
| `app/common/src/main/java/stirling/software/common/util/PDFToFile.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/pipeline/PipelineProcessor.java` | 是 | 无问题 |

---

## 严重度确认清单

- [x] 所有 disableSanitize 问题标记为 HIGH（问题 2）
- [x] 所有 CORS `*` + allowCredentials 标记为 HIGH（已合并到问题 1）
- [x] 所有 Path.resolve 无验证标记为 HIGH（问题 3）
- [x] 所有硬编码管理员凭据标记为 MEDIUM（问题 5）
- [x] 所有 SSRF 未验证内网 IP 标记为 MEDIUM（问题 6）
- [x] 所有 SAXSVGDocumentFactory 未禁用外部实体标记为 MEDIUM（问题 7）
- [x] 所有速率限制禁用标记为 MEDIUM（已合并到问题 4）
- [x] 所有 MD5/SHA1 标记为 LOW（问题 8）
- [x] 所有 HttpFirewall 换行符标记为 LOW（问题 9）
- [x] CSRF + CORS + Cookie 认证合并为 1 个 HIGH（问题 1）
- [x] CSRF + 速率限制合并为 1 个 MEDIUM（问题 4）
- [x] 同一配置影响多个文件合并为 1 个问题（问题 2：disableSanitize 影响 3 个文件）

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 2 |
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
| HardcodedSecret | 2 |
| CSRF | 2（问题 1、4） |
| CORS | 1（已合并到问题 1） |
| Auth | 1（已合并到问题 4） |
| Session | 0 |
| HttpFirewall | 1 |

---

## 正面发现

1. **SQL 注入防护完善**: `DatabaseService` 使用 `PreparedStatement` 参数化查询，并实现了 SQL 内容验证（白名单 + 黑名单），有效防止 SQL 注入攻击

2. **XXE 防护到位**: `SvgSanitizer` 和 `OfficeDocumentSanitizer` 的 XML 解析器配置了完整的外部实体禁用特性，遵循安全最佳实践

3. **命令注入防护**: `ProcessExecutor.validateCommand()` 方法验证了命令参数，检查空字节、换行符和路径穿越，有效防止命令注入

4. **加密实现规范**: `CredentialEncryption` 使用 AES-256-GCM 算法，正确生成随机 IV，密钥管理支持环境变量和密钥文件，符合安全标准

5. **路径穿越防护**: `DatabaseService.getBackupFilePath()` 实现了路径规范化和前缀验证，有效防止路径穿越攻击

6. **文件上传验证**: `StampController` 验证了文件名中的路径穿越字符（`..`、`/`），`DatabaseController` 验证了备份文件名格式

7. **SSRF 防护基础**: `SsrfProtectionService` 已在代码中集成，用于验证 HTML 和 SVG 中的 URL，为 SSRF 防护提供了基础

---

## 关键风险总结

1. **跨域攻击链（HIGH）**: CSRF 禁用 + CORS 允许所有来源 + 允许凭证 + Cookie 认证，形成完整的跨域攻击链，攻击者可以从恶意网站执行未授权操作

2. **净化器全局开关（HIGH）**: `disableSanitize` 配置可禁用所有 HTML/SVG/Office 文档净化，一旦启用将导致 XSS 和信息泄露风险

3. **路径穿越（HIGH）**: `FileOrUploadService.resolveFilePath()` 未验证用户输入，攻击者可以访问服务器上的任意文件

4. **SSRF 风险（MEDIUM）**: `ConvertWebsiteToPDF` 未验证内网 IP，攻击者可以访问内部服务或云元数据 API

5. **暴力破解风险（MEDIUM）**: CSRF 禁用 + 速率限制失效，攻击者可以无限制地尝试登录

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Mu
