# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `SecurityConfiguration.java`, `SecurityConfiguration.java`
- **行号**: 269, 188, 218, 337-351, 373-388
- **严重度**: CRITICAL
- **类型**: CSRF + CORS + Cookie 认证（组合漏洞）
- **描述**: 根据组合漏洞规则，以下多个漏洞形成完整攻击链：
  1. **CSRF 完全禁用**（第 269 行）：`http.csrf(CsrfConfigurer::disable)` 全局禁用了 CSRF 保护。
  2. **CORS 默认允许所有来源**（第 188 行）：当 `system.corsAllowedOrigins` 未配置时，默认使用 `cfg.setAllowedOriginPatterns(List.of("*"))` 允许任意来源。
  3. **allowCredentials=true**（第 218 行）：`cfg.setAllowCredentials(true)` 允许跨域请求携带凭据（Cookie）。
  4. **基于 Cookie 的认证**（第 337-351 行、第 373-388 行）：配置了 `rememberMe()`（基于 Cookie）和 `formLogin()`（基于 Cookie 的会话认证）。

  **攻击场景**：攻击者可以在恶意网站上构造跨域请求，由于 CSRF 保护被禁用、CORS 允许所有来源且允许携带凭据，浏览器会自动附加受害者的会话 Cookie。攻击者可以诱导已登录的用户访问恶意页面，以受害者身份执行任意操作（如修改密码、上传文件、管理数据库等）。整个攻击无需用户交互（除访问恶意页面外），攻击步骤简单，无需特殊条件。

  根据 V4 组合漏洞规则：CSRF 禁用 + CORS `*` + `allowCredentials=true` + formLogin/rememberMe = **1 个 CRITICAL 组合漏洞**。

- **代码片段**:
```java
// SecurityConfiguration.java 第 269 行 - CSRF 禁用
http.csrf(CsrfConfigurer::disable);

// SecurityConfiguration.java 第 186-192 行 - CORS 默认允许所有来源
} else {
    cfg.setAllowedOriginPatterns(List.of("*"));
    log.info("No CORS allowed origins configured in settings.yml"
            + " (system.corsAllowedOrigins); allowing all origins.");
}

// SecurityConfiguration.java 第 218 行 - 允许携带凭据
cfg.setAllowCredentials(true);

// SecurityConfiguration.java 第 337-351 行 - rememberMe（Cookie 认证）
http.rememberMe(rememberMeConfigurer ->
    rememberMeConfigurer
        .tokenRepository(persistentTokenRepository())
        .tokenValiditySeconds(14 * 24 * 60 * 60)
        .userDetailsService(userDetailsService)
        .useSecureCookie(true)
        .rememberMeParameter("remember-me")
        .rememberMeCookieName("remember-me")
        .alwaysRemember(false));

// SecurityConfiguration.java 第 373-388 行 - formLogin（Cookie 认证）
http.formLogin(formLogin ->
    formLogin.loginPage("/login")
        .loginProcessingUrl("/perform_login")
        .successHandler(...)
        .failureHandler(...)
        .permitAll());
```
- **修复建议**:
  1. 启用 CSRF 保护：移除 `http.csrf(CsrfConfigurer::disable)`，使用 Spring Security 默认的 CSRF 保护或配置 `CookieCsrfTokenRepository`。
  2. 配置具体的 CORS 允许来源：将默认值从 `*` 改为空列表或要求管理员显式配置。
  3. 如果必须使用 `allowCredentials=true`，则不允许 `allowedOriginPatterns` 为 `*`，应配置具体的可信来源。
  4. 如果 CSRF 确实需要禁用（如纯 API 场景），则不应同时启用 `formLogin()` 和 `rememberMe()` 等基于 Cookie 的认证方式。

### 问题 2
- **文件**: `InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: CRITICAL
- **类型**: HardcodedSecret
- **描述**: 默认管理员用户凭据被硬编码在源代码中。当系统首次启动且未配置初始管理员凭据时，会自动创建用户名为 `admin`、密码为 `stirling` 的管理员账户。虽然设置了 `firstLogin=true` 标志提示用户修改密码，但该账户在密码被修改前完全可用，且管理员权限为最高权限（`Role.ADMIN`）。这是一个广为人知的默认凭据，攻击者可直接利用获取管理员权限，无需用户交互。

- **代码片段**:
```java
// InitialSecuritySetup.java 第 153-168 行
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";

    if (userService.findByUsernameIgnoreCase(defaultUsername).isEmpty()) {
        Team team = teamService.getOrCreateDefaultTeam();
        SaveUserRequest.Builder builder =
                SaveUserRequest.builder()
                        .username(defaultUsername)
                        .password(defaultPassword)
                        .team(team)
                        .role(Role.ADMIN.getRoleId())
                        .firstLogin(true);
        userService.saveUserCore(builder.build());
        log.info("Default admin user created: {}", defaultUsername);
    }
}
```
- **修复建议**:
  1. 移除硬编码的默认凭据，改为在首次启动时强制要求管理员设置凭据（如通过环境变量或交互式设置向导）。
  2. 如果必须保留默认凭据，应在首次登录时强制修改密码（阻止其他操作直到密码被修改）。
  3. 在启动日志中增加醒目的安全警告，提示用户立即修改默认密码。
  4. 考虑生成随机密码并输出到安全的配置文件中。

### 问题 3
- **文件**: `CustomHtmlSanitizer.java`, `SvgSanitizer.java`, `OfficeDocumentSanitizer.java`
- **行号**: 64-66, 59-61, 80-83
- **严重度**: HIGH
- **类型**: XSS
- **描述**: 根据 V4 问题合并规则 1，同一配置项 `disableSanitize` 影响多个文件，算 1 个问题。`applicationProperties.getSystem().isDisableSanitize()` 配置项可同时禁用三类净化器（HTML 净化、SVG 净化、Office 文档净化）。当该配置被启用时：
  - `CustomHtmlSanitizer` 直接返回未净化的 HTML，允许任意脚本执行。
  - `SvgSanitizer` 跳过 SVG 净化，允许嵌入恶意脚本、事件处理器和外部引用。
  - `OfficeDocumentSanitizer` 跳过 Office 文档净化，允许保留外部引用和恶意内容。

  根据 V4 标准，即使仅管理员可配置，影响范围过大，一旦启用将完全暴露攻击面，严重度为 HIGH。

- **代码片段**:
```java
// CustomHtmlSanitizer.java 第 64-66 行
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java 第 59-61 行
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
- **修复建议**:
  1. 移除 `disableSanitize` 全局开关，或将其拆分为独立的细粒度控制（如 `disableHtmlSanitize`、`disableSvgSanitize`、`disableOfficeSanitize`）。
  2. 如果必须保留全局开关，应增加额外的安全警告和确认机制。
  3. 考虑在禁用净化时增加日志审计和告警机制。

### 问题 4
- **文件**: `ConvertWebsiteToPDF.java`
- **行号**: 74, 175-201
- **严重度**: HIGH
- **类型**: SSRF
- **描述**: `urlToPdf` 端点接受用户提供的 URL，通过 `fetchRemoteHtml()` 方法使用 `HttpClient` 发起服务端请求。URL 验证仅检查格式有效性（`RegexPatternUtils.getHttpUrlPattern()` 和 `GeneralUtils.isValidURL()`），但未验证目标 IP 地址。攻击者可以提供内网地址（如 `http://169.254.169.254/latest/meta-data/`、`http://10.0.0.1/`、`http://localhost:8080/admin`）来访问内部服务、云元数据服务或本地网络资源。

  虽然代码中有 `file:` 协议检测（`containsDisallowedUriScheme`），但这仅检测 HTML 内容中的 `file:` 引用，并不限制初始 URL 的目标 IP。`fetchRemoteHtml()` 设置了 `followRedirects(HttpClient.Redirect.NEVER)` 防止重定向绕过，但直接的内网访问仍然可行。

  根据 V4 标准，验证了协议（仅允许 http/https）但未验证 IP，可访问内网，严重度为 HIGH。如果可以访问云元数据服务（169.254.169.254），至少为 HIGH。

- **代码片段**:
```java
// ConvertWebsiteToPDF.java 第 74 行 - 用户输入的 URL
String URL = request.getUrlInput();

// ConvertWebsiteToPDF.java 第 88-91 行 - 仅验证格式，未验证目标 IP
boolean patternValid =
        RegexPatternUtils.getInstance().getHttpUrlPattern().matcher(URL).matches();
boolean generalValid = GeneralUtils.isValidURL(URL);
if (!patternValid && !generalValid) {
    // ... 拒绝
}

// ConvertWebsiteToPDF.java 第 175-201 行 - 发起服务端请求
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
  1. 在发起请求前解析 URL 的主机名，验证目标 IP 不属于私有地址范围（RFC 1918）、链路本地地址（169.254.0.0/16）、回环地址（127.0.0.0/8）等。
  2. 使用 DNS 解析后的 IP 进行验证，防止 DNS rebinding 攻击（可考虑 DNS 固定或使用安全的 DNS 解析库）。
  3. 考虑使用白名单机制限制允许访问的域名或 IP 范围。
  4. 可参考已有的 `SsrfProtectionService`（在其他组件中使用）来统一 SSRF 防护策略。

### 问题 5
- **文件**: `FileOrUploadService.java`
- **行号**: 20-22
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath` 方法直接将用户可控的 `fileId` 参数通过 `Path.resolve()` 拼接到基础目录，未进行任何路径规范化、前缀验证或危险字符检查。攻击者可以提供包含 `..` 的文件 ID（如 `../../etc/passwd`）来访问基础目录之外的任意文件。

  根据 V4 标准，路径直接用于 `FileInputStream` / `FileOutputStream`，至少为 HIGH。该方法作为 `@Service` 公开方法，可被任何控制器调用，一旦 `fileId` 来源于用户输入，即可造成任意文件读取或写入。

- **代码片段**:
```java
// FileOrUploadService.java 第 17-22 行
@Value("${stirling.tempDir:/tmp/stirling-files}")
private String tempDirPath;

public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
    // 无 normalize()、无前缀验证、无危险字符检查
}
```
- **修复建议**:
  1. 对 `fileId` 进行路径规范化并验证结果仍在基础目录内：
     ```java
     public Path resolveFilePath(String fileId) {
         Path basePath = Path.of(tempDirPath).normalize().toAbsolutePath();
         Path resolved = basePath.resolve(fileId).normalize().toAbsolutePath();
         if (!resolved.startsWith(basePath)) {
             throw new SecurityException("Path traversal detected");
         }
         return resolved;
     }
     ```
  2. 验证 `fileId` 不包含 `..`、`/`、`\` 等危险字符。
  3. 考虑使用白名单机制限制文件 ID 的格式（如仅允许 UUID 格式）。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 2 |
| HIGH | 3 |
| MEDIUM | 0 |
| LOW | 0 |
| **总计** | **5** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| SQLi | 0 |
| XSS | 1 |
| XXE | 0 |
| PathTraversal | 1 |
| CommandInjection | 0 |
| SSRF | 1 |
| FileUpload | 0 |
| HardcodedSecret | 1 |
| CSRF | 1 (组合漏洞) |
| CORS | 1 (组合漏洞) |
| Auth | 0 |
| Session | 0 |

> 注：CSRF 和 CORS 已按 V4 组合漏洞规则合并为问题 1（CRITICAL），在类型分布中各计 1 次，但实际为 1 个问题。

---

## 正面发现

1. **XML 外部实体防护完善**：`SvgSanitizer.java`（第 86-99 行）和 `OfficeDocumentSanitizer.java`（第 279-289 行）中的 `DocumentBuilderFactory` 均正确禁用了所有外部实体和 DTD：
   - `disallow-doctype-decl = true`
   - `external-general-entities = false`
   - `external-parameter-entities = false`
   - `load-external-dtd = false`
   - `setXIncludeAware(false)`
   - `setExpandEntityReferences(false)`

2. **命令注入防护良好**：`ProcessExecutor.java` 使用 `ProcessBuilder` 列表参数（非 shell 模式），并在 `validateCommand()` 方法中验证了所有参数的 null 字节、换行符和路径穿越。所有调用方（`ConvertWebsiteToPDF`、`CompressController`、`ExtractImageScansController`、`PDFToFile`）均使用列表参数传递命令。

3. **SQL 注入防护完善**：`DatabaseService.java` 中所有 SQL 操作均使用 `PreparedStatement` 参数化查询（如 `RUNSCRIPT FROM ?`、`SCRIPT SIMPLE COLUMNS DROP to ?`）。此外还实现了 SQL 内容验证机制（`validateSqlContent`），使用白名单和黑名单模式双重检查导入的 SQL 内容。

4. **SVG 外部资源加载防护**：`SvgOverlayUtil.java` 中的 `UserAgent` 重写 `checkLoadExternalResource` 方法，仅允许 `data:` URI（内联数据），阻止所有外部资源加载，有效防止了 SVG 中的 SSRF 和信息泄露。

5. **凭证加密实现规范**：`CredentialEncryption.java` 使用 AES-256-GCM 算法，密钥通过配置属性、环境变量或自动生成的密钥文件获取。密钥文件以 0600 权限（仅所有者可读写）创建，IV 使用 `SecureRandom` 生成。

6. **数据库备份文件路径防护**：`DatabaseService.getBackupFilePath()` 正确实现了路径规范化和前缀验证（`normalize()` + `startsWith(BACKUP_DIR)`），有效防止路径穿越。`deleteBackupFile()` 还额外验证了文件名中的危险字符。

7. **数据库端点权限控制**：`DatabaseController.java` 使用 `@PreAuthorize("hasRole('ADMIN')")` 注解限制所有端点仅管理员可访问。

8. **临时文件管理**：项目广泛使用 `TempFile` 和 `TempFileManager` 进行临时文件生命周期管理，通过 `try-with-resources` 模式确保文件清理。

---

## 关键风险总结

1. **CSRF + CORS + Cookie 认证组合漏洞（CRITICAL）**：CSRF 保护全局禁用、CORS 默认允许所有来源且允许携带凭据、同时使用 formLogin 和 rememberMe 基于 Cookie 认证。攻击者可通过恶意网站以受害者身份执行任意操作。这是最严重的风险，因为攻击简单且无需特殊条件。

2. **硬编码默认管理员凭据（CRITICAL）**：默认管理员账户 `admin/stirling` 硬编码在源代码中，首次启动后立即可用。攻击者可直接利用获取系统完全控制权。

3. **`disableSanitize` 全局安全开关（HIGH）**：单一配置项可同时禁用 HTML、SVG 和 Office 文档三类净化器，影响范围过大。一旦启用，系统将完全暴露于 XSS 和恶意内容攻击。

4. **URL 转 PDF 功能的 SSRF 漏洞（HIGH）**：仅验证 URL 格式而不验证目标 IP，攻击者可利用此漏洞访问内网服务、云元数据端点或本地资源。

5. **FileOrUploadService 路径穿越漏洞（HIGH）**：`resolveFilePath` 方法无任何路径验证，直接将用户输入拼接到基础路径，可导致任意文件读取或写入。

---

## 评审检查清单

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用组合漏洞判定规则（CSRF + CORS + Cookie 认证合并为 1 个 CRITICAL 组合漏洞）
- [x] 已应用问题合并规则（disableSanitize 影响 3 个文件合并为 1 个 HIGH 问题）
- [x] 评审深度达到标准要求

### 文件覆盖确认

| # | 文件 | 已审查 | 发现问题 |
|---|------|--------|----------|
| 1 | `ConvertWebsiteToPDF.java` | 是 | SSRF |
| 2 | `StampController.java` | 是 | 无 |
| 3 | `CompressController.java` | 是 | 无 |
| 4 | `SvgOverlayUtil.java` | 是 | 无 |
| 5 | `FileOrUploadService.java` | 是 | PathTraversal |
| 6 | `CustomHtmlSanitizer.java` | 是 | XSS（合并） |
| 7 | `SvgSanitizer.java` | 是 | XSS（合并） |
| 8 | `OfficeDocumentSanitizer.java` | 是 | XSS（合并） |
| 9 | `ProcessExecutor.java` | 是 | 无 |
| 10 | `CredentialEncryption.java` | 是 | 无 |
| 11 | `InitialSecuritySetup.java` | 是 | HardcodedSecret |
| 12 | `SecurityConfiguration.java` | 是 | CSRF + CORS（组合） |
| 13 | `DatabaseController.java` | 是 | 无 |
| 14 | `DatabaseService.java` | 是 | 无 |
| 15 | `DesktopClientUtils.java` | 是 | 无 |
| 16 | `ExtractImageScansController.java` | 是 | 无 |
| 17 | `PDFToFile.java` | 是 | 无 |
| 18 | `PipelineProcessor.java` | 是 | 无 |

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Theta
