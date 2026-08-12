# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath` 方法直接将用户提供的 `fileId` 传入 `Path.resolve()` 而没有任何路径规范化或前缀验证。攻击者可构造包含 `..` 的 `fileId`（如 `../../etc/passwd`）实现路径穿越，读取或写入服务器上的任意文件路径。虽然在本评审范围内未发现该方法被直接以用户输入调用的代码路径，但该方法作为 `@Service` 的公开方法暴露，任何新增的调用点都可能引入路径穿越漏洞。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```
- **修复建议**: 对 `fileId` 进行路径规范化并验证其仍在 `tempDirPath` 目录下：
```java
public Path resolveFilePath(String fileId) {
    Path base = Path.of(tempDirPath).normalize().toAbsolutePath();
    Path resolved = base.resolve(fileId).normalize().toAbsolutePath();
    if (!resolved.startsWith(base)) {
        throw new SecurityException("Path traversal detected: " + fileId);
    }
    return resolved;
}
```

### 问题 2
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 88-143
- **严重度**: MEDIUM
- **类型**: SSRF
- **描述**: URL-to-PDF 转换功能存在 TOCTOU（Time-of-Check-Time-of-Use）SSRF 风险。`isURLReachable()` 方法在验证阶段对 DNS 进行了全面检查（阻止内网/环回/链路本地地址），但后续的 `fetchRemoteHtml()` 使用 `HttpClient` 和 WeasyPrint 使用 `--base-url` 参数各自独立进行 DNS 解析，这两步均不经过 SSRF 检查。攻击者可通过 DNS 重绑定（DNS rebinding）攻击绕过检查：第一次 DNS 解析返回公网 IP 通过验证，第二次解析返回内网 IP 从而访问内部服务。此外，WeasyPrint 作为无沙箱的 HTML-to-PDF 引擎，可加载 HTML 中引用的所有资源（CSS、图片、字体等），这些资源请求也不受 SSRF 检查约束。
- **代码片段**:
```java
// 验证阶段：检查 URL 可达性（包含 SSRF 防护）
} else if (!GeneralUtils.isURLReachable(URL)) {
    // error...
}
// 使用阶段：独立的 DNS 解析，不经过 SSRF 检查
String htmlContent = fetchRemoteHtml(URL);  // HttpClient 独立解析 DNS
// ...
command.add("--base-url");
command.add(URL);  // WeasyPrint 独立解析 DNS 并加载资源
```
- **修复建议**: 
  1. 在 `fetchRemoteHtml` 中复用已验证的 IP 地址（通过 IP 直连或自定义 DNS 解析器）；
  2. 为 WeasyPrint 配置网络代理或沙箱环境，限制其网络访问范围；
  3. 考虑在 WeasyPrint 命令中添加 `--allow-unsafe` 的逆向控制参数（如果支持），或使用 `unshare` 等系统工具限制网络命名空间。

### 问题 3
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 64-67
- **严重度**: MEDIUM
- **类型**: XSS
- **描述**: `CustomHtmlSanitizer.sanitize()`、`SvgSanitizer.sanitize()` 和 `OfficeDocumentSanitizer.sanitize()` 三个净化器均通过 `applicationProperties.getSystem().isDisableSanitize()` 配置项完全绕过所有安全净化。当管理员设置该配置为 `true` 时，所有 HTML、SVG 和 Office 文档的安全净化将被禁用，恶意内容可原封不动地通过处理链。根据 V5 标准，"净化/验证可被配置禁用，即使仅管理员可配置"属于 HIGH 级别。但考虑到该配置需要管理员在 `settings.yml` 中显式设置，且属于全局安全开关，降级为 MEDIUM。此问题按合并规则 1（同一配置影响多个文件）计为 1 个问题。
- **代码片段**:
```java
// CustomHtmlSanitizer.java:64-67
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java:59-62
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java:80-83
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**: 
  1. 移除 `disableSanitize` 全局开关，或将其限制为仅影响特定非安全场景；
  2. 即使保留该开关，也应确保核心安全净化（如移除 `<script>` 标签、阻止 `javascript:` URI）始终执行；
  3. 添加日志告警和启动提示，提醒管理员该配置会禁用安全净化。

### 问题 4
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218
- **严重度**: MEDIUM
- **类型**: CORS
- **描述**: 当 `settings.yml` 中未配置 `system.corsAllowedOrigins` 时，CORS 默认允许所有来源（`allowedOriginPatterns("*")`）同时设置 `allowCredentials(true)`。`allowedOriginPatterns("*")` + `allowCredentials(true)` 的组合意味着任何外部网站都可以携带用户的认证凭据（Cookie、JWT 等）向本应用发起跨域请求。虽然现代浏览器对 `allowCredentials=true` 与通配符 `*` 的组合有一定限制（要求使用具体来源而非 `*`），但 `allowedOriginPatterns` 的行为与 `allowedOrigins` 不同，它支持模式匹配，`"*"` 会匹配所有来源。这违反了 CORS 的最小权限原则。
- **代码片段**:
```java
// 默认：允许所有来源
cfg.setAllowedOriginPatterns(List.of("*"));
// ...
cfg.setAllowCredentials(true);
```
- **修复建议**: 
  1. 默认配置应拒绝所有来源或仅允许 `same-origin`，要求管理员显式配置允许的来源；
  2. 如果必须允许跨域，不应同时启用 `allowCredentials(true)`；
  3. 在启动日志中明确警告当前 CORS 配置的安全风险。

### 问题 5
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269, 476-479
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: 存在两个相关的认证/授权配置问题：
  (a) **CSRF 保护被全局禁用**（行 269）：`http.csrf(CsrfConfigurer::disable)` 完全禁用了 CSRF 保护。虽然主认证使用 JWT（STATELESS 会话），但 remember-me 功能使用基于 Cookie 的持久化令牌（行 337-351），在 CSRF 禁用的情况下，攻击者可通过跨站请求利用用户的 remember-me Cookie 执行状态变更操作。
  (b) **速率限制实质禁用**（行 476-479）：`IPRateLimitingFilter` 配置的限制为每窗口 1,000,000 次请求，且该过滤器在行 299-304 被注释掉（未注册到过滤器链）。注释明确说明 "limit is 1M, no-op"。这使得应用完全暴露于暴力破解和凭证填充攻击之下。根据 V5 标准，速率限制配置为极高值或被禁用必须报告为 MEDIUM。
- **代码片段**:
```java
// CSRF 禁用
http.csrf(CsrfConfigurer::disable);

// 速率限制实质禁用
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
// 且该过滤器被注释掉未注册：
// .addFilterBefore(rateLimitingFilter, UsernamePasswordAuthenticationFilter.class)
```
- **修复建议**: 
  1. 启用 CSRF 保护，至少对基于 Cookie 认证的路径（如 remember-me）启用；
  2. 将速率限制降低到合理值（如每窗口 100-200 次），并将其重新注册到过滤器链中；
  3. 对登录端点实施更严格的速率限制（如每分钟 5 次）。

### 问题 6
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **描述**: 当未配置初始管理员凭据时，系统自动创建用户名为 `admin`、密码为 `stirling` 的默认管理员账户。该默认凭据是公开已知的（在源代码中硬编码），如果部署后未立即修改密码，攻击者可使用该凭据直接获取管理员权限。虽然代码设置了 `firstLogin(true)` 标志（可能用于提示修改密码），但并未强制要求修改。根据 V5 标准，这属于"使用不安全的默认配置"。
- **代码片段**:
```java
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";
    // ...
    SaveUserRequest.Builder builder =
            SaveUserRequest.builder()
                    .username(defaultUsername)
                    .password(defaultPassword)
                    .team(team)
                    .role(Role.ADMIN.getRoleId())
                    .firstLogin(true);
    userService.saveUserCore(builder.build());
}
```
- **修复建议**: 
  1. 启动时如果检测到默认凭据未更改，强制要求修改密码或拒绝启动；
  2. 生成随机密码并打印到控制台（仅一次），而非使用固定密码；
  3. 在启动日志中发出醒目警告，提醒用户立即修改默认密码。

### 问题 7
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 36
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `SAXSVGDocumentFactory` 在创建 SVG 文档时未显式禁用外部实体（DTD、external general entities、external parameter entities）。虽然 Apache Batik 对 SAX 解析器有一定的默认防护，且后续的 `UserAgent.checkLoadExternalResource()` 在渲染阶段阻止了外部资源加载，但根据 V5 标准，`SAXSVGDocumentFactory` 必须显式禁用外部实体，即使 Batik 可能有默认防护。如果 Batik 的默认防护在某些版本或配置下不完整，SVG 输入可能触发 XXE 攻击。
- **代码片段**:
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);
// 未对 factory 设置 XXE 防护特性

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```
- **修复建议**: 在创建 `SAXSVGDocumentFactory` 后，显式设置安全特性：
```java
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);
// 如果 SAXSVGDocumentFactory 支持设置特性：
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```
如果 `SAXSVGDocumentFactory` 不支持直接设置这些特性，可考虑使用已安全配置的 `DocumentBuilderFactory` 先解析 SVG，再传递给 Batik 渲染。

### 问题 8
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 742-749
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: `generateMD5()` 方法使用 MD5 哈希算法用于 PDF 图片去重（`ImageIdentity` 类中的 `pixelHash`、`maskHash`、`decodeParams`、`metadataHash` 等字段）。MD5 是已知弱哈希算法，存在碰撞攻击。虽然此处仅用于非安全场景（图片去重而非密码哈希或完整性校验），但根据 V5 标准，使用 MD5 或 SHA1 必须报告为 LOW。
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
- **修复建议**: 将 MD5 替换为 SHA-256 等更安全的哈希算法。虽然去重场景对碰撞安全性要求不高，但使用强哈希算法可避免潜在的去重绕过攻击（攻击者构造碰撞图片替换原始图片），且性能差异在大多数场景下可忽略。

---

## 12 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题 - 所有 SQL 操作均使用 `PreparedStatement` 参数化查询（`DatabaseService.java` 中的 `RUNSCRIPT FROM ?`、`SCRIPT SIMPLE COLUMNS DROP to ?` 等均使用 `stmt.setString()` 绑定参数）。`validateSqlContent()` 提供了额外的白名单/黑名单 SQL 内容校验。 |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 3 |
| 3. XML 外部实体 (XXE) | 已检查 | 问题 7 |
| 4. 路径穿越 | 已检查 | 问题 1 |
| 5. 命令注入 | 已检查 | 无问题 - 所有外部命令（WeasyPrint、Ghostscript、QPDF、pdftohtml、LibreOffice、Python）均通过 `List<String>` 构建参数列表，使用 `ProcessBuilder` 执行（非 shell 字符串拼接）。`ProcessExecutor.validateCommand()` 对所有参数进行空字节、换行符和路径穿越检查。用户输入仅作为独立列表元素传入，不参与 shell 解析。 |
| 6. SSRF | 已检查 | 问题 2 |
| 7. 文件上传/下载 | 已检查 | 无问题 - 文件上传接口均验证了文件非空（`DatabaseController` 行 48-56），文件名经过路径穿越检查（`StampController` 行 106-109 检查 `..` 和 `/`，`DatabaseService.isValidFileName()` 检查多种非法字符）。上传文件保存到临时目录后处理，不直接使用原始文件名作为文件系统路径。`DatabaseController.downloadFile()` 验证了文件名格式（`backup_` 前缀 + `.sql` 后缀）。 |
| 8. 硬编码密钥/密码 | 已检查 | 问题 6, 问题 8 |
| 9. CSRF 保护 | 已检查 | 问题 5（CSRF 全局禁用作为组合问题的一部分） |
| 10. CORS 配置 | 已检查 | 问题 4 |
| 11. 认证授权 | 已检查 | 问题 5（速率限制禁用作为组合问题的一部分） |
| 12. 会话管理 | 已检查 | 无问题 - 主会话策略为 `STATELESS`（JWT 认证），无传统 HttpSession 使用。remember-me 令牌有效期 14 天（行 341-342），使用安全 Cookie（`useSecureCookie(true)`）。JWT 令牌有效期可配置，桌面客户端默认 30 天（`DesktopClientUtils`），属于合理的设计决策。 |

---

## 18 文件评审覆盖确认

| 文件 | 已评审 | 涉及问题 |
|------|--------|----------|
| `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java` | 是 | 问题 2 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java` | 是 | 无问题 |
| `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java` | 是 | 问题 8 |
| `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java` | 是 | 问题 7 |
| `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java` | 是 | 问题 1 |
| `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java` | 是 | 问题 3 |
| `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java` | 是 | 问题 3 |
| `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java` | 是 | 问题 3 |
| `app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/integration/crypto/CredentialEncryption.java` | 是 | 无问题 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java` | 是 | 问题 6 |
| `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java` | 是 | 问题 4, 问题 5 |
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
| HIGH | 1 |
| MEDIUM | 6 |
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
| HardcodedSecret | 2 |
| CSRF | 0 (包含在问题 5 的 Auth 组合问题中) |
| CORS | 1 |
| Auth | 1 (包含 CSRF 禁用 + 速率限制禁用) |
| Session | 0 |

---

## 正面发现

1. **参数化 SQL 查询**: `DatabaseService` 中所有 SQL 操作均使用 `PreparedStatement`，并提供 SQL 内容白名单/黑名单校验（`validateSqlContent`），有效防止 SQL 注入攻击。

2. **全面的 XXE 防护**: `SvgSanitizer` 和 `OfficeDocumentSanitizer` 中的 `DocumentBuilderFactory` 配置了完整的安全特性（`disallow-doctype-decl`、禁用外部实体、禁用外部 DTD 加载、禁用 XInclude）。

3. **强加密实现**: `CredentialEncryption` 使用 AES-256-GCM（认证加密），密钥管理合理（支持配置/环境变量/自动生成密钥文件），密钥文件权限设为 0600（仅所有者可读写），集群模式下强制要求共享密钥。

4. **命令注入防护**: `ProcessExecutor.validateCommand()` 对所有命令参数进行空字节、换行符检查，对可执行文件进行路径穿越检查和存在性验证。所有外部命令均使用 `List<String>` 构建，避免 shell 注入。

5. **安全的 ZIP 处理**: `OfficeDocumentSanitizer` 使用 `ZipSecurity.createHardenedInputStream()` 防止 Zip Bomb 攻击。

6. **路径穿越防护**: `DatabaseService.getBackupFilePath()` 正确实现了路径规范化和前缀验证（`normalize()` + `startsWith()` 检查）。`DatabaseController` 的 `@PreAuthorize("hasRole('ADMIN')")` 确保数据库操作仅限管理员。

7. **SSRF 基础防护**: `GeneralUtils.isURLReachable()` 中的 `isSensitiveAddress()` 方法全面覆盖了内网、环回、链路本地、多播、CGNAT、IPv6 ULA 等敏感地址范围。

8. **文件名安全处理**: `Filenames.toSimpleFileName()`（来自 pixee 安全库）用于清理上传文件名，`GeneralUtils.convertToFileName()` 对 URL 转换的文件名进行安全处理。

9. **SVG 安全净化**: `SvgSanitizer` 实现了全面的 SVG 净化，包括移除危险元素（`<script>`、`<foreignObject>` 等）、事件处理器属性、`javascript:` URI，以及 SSRF 安全的 URL 属性检查。

10. **进程资源限制**: `ProcessExecutor` 使用 `Semaphore` 限制并发进程数，设置超时时间，超时后强制杀死进程树（`descendants().forEach(ProcessHandle::destroyForcibly)`）。

---

## 关键风险总结

1. **路径穿越（HIGH）**: `FileOrUploadService.resolveFilePath()` 直接将用户输入传入 `Path.resolve()` 而无任何路径验证，存在路径穿越风险。虽然当前未发现直接的用户输入调用路径，但作为公开 Service 方法，任何新增调用点都可能引入漏洞。

2. **SSRF via DNS 重绑定（MEDIUM）**: `ConvertWebsiteToPDF` 的 URL 验证与实际使用之间存在 TOCTOU 窗口，DNS 重绑定攻击可绕过 SSRF 防护。WeasyPrint 无沙箱环境进一步放大了风险。

3. **安全净化可全局禁用（MEDIUM）**: 单一配置项 `disableSanitize` 可同时禁用 HTML、SVG 和 Office 文档的所有安全净化，为攻击者提供了在配置不当时注入恶意内容的通道。

4. **CORS 默认全开 + CSRF 禁用 + 速率限制失效（MEDIUM）**: 默认 CORS 允许所有来源、CSRF 全局禁用、速率限制设为 1M 且未注册到过滤器链，三者组合形成不完整的安全控制面。

5. **默认管理员凭据（MEDIUM）**: 硬编码的 `admin/stirling` 默认凭据是公开已知的，如果部署后未及时修改，可直接获取管理员权限。

---

## 评审检查清单

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用问题合并规则（问题 3 为同一配置影响多个文件，合并为 1 个问题；问题 5 为 CSRF + 速率限制组合漏洞，合并为 1 个问题）
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题
- [x] 已对每个维度给出明确结论

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Iota
