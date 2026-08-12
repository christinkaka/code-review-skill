# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269, 188, 218
- **严重度**: CRITICAL
- **类型**: CSRF + CORS（组合漏洞）
- **描述**: CSRF 保护被全局禁用（`http.csrf(CsrfConfigurer::disable)`），同时 CORS 默认配置为 `allowedOriginPatterns("*")` 且 `allowCredentials(true)`。更关键的是，应用配置了 `formLogin()`（第 373 行）和 `rememberMe()`（第 337-351 行，有效期 14 天），两者均基于 Cookie 认证。根据组合漏洞规则 1（CSRF 禁用 + CORS `*` + `allowCredentials=true` + form login/remember-me = CRITICAL），攻击者可构造恶意网页，以已认证用户的 Cookie 身份向 Stirling-PDF 发送任意 state-changing 请求。Spring 框架在使用 `allowedOriginPatterns("*")` 时会回显请求的 Origin（而非返回字面量 `*`），从而绕过浏览器的 CORS 限制，使 `allowCredentials=true` 生效。此组合漏洞影响所有已登录用户，攻击者可通过管理员账户执行任意操作（包括数据库导入/导出、用户管理、文件处理等）。
- **代码片段**:
```java
// 第 269 行 - CSRF 全局禁用
http.csrf(CsrfConfigurer::disable);

// 第 188 行 - CORS 默认允许所有来源
cfg.setAllowedOriginPatterns(List.of("*"));

// 第 218 行 - 允许携带凭证
cfg.setAllowCredentials(true);

// 第 337-351 行 - remember-me 基于 Cookie 认证（14 天有效期）
http.rememberMe(
    rememberMeConfigurer ->
        rememberMeConfigurer
            .tokenRepository(persistentTokenRepository())
            .tokenValiditySeconds(14 * 24 * 60 * 60)
            .userDetailsService(userDetailsService)
            .useSecureCookie(true)
            .rememberMeParameter("remember-me")
            .rememberMeCookieName("remember-me")
            .alwaysRemember(false));

// 第 373 行 - form login 基于 Cookie 认证
http.formLogin(
    formLogin ->
        formLogin.loginPage("/login")
            .loginProcessingUrl("/perform_login")
            ...);
```
- **修复建议**:
  1. 启用 CSRF 保护，至少对 state-changing 的 API 端点（POST/PUT/DELETE）启用 CSRF Token 验证。如果 API 使用 JWT 认证（无 Cookie），可仅对 `/api/**` 路径禁用 CSRF，但必须保留对 form login 端点的 CSRF 保护。
  2. 将 CORS `allowedOriginPatterns` 的默认值从 `"*"` 改为具体的受信来源列表（如 `["http://localhost:8080"]`），并在 `settings.yml` 中要求管理员显式配置。
  3. 如果必须使用 `allowCredentials(true)`，则绝不能使用 `"*"` 作为 allowedOrigin，应使用具体的域名白名单。

---

### 问题 2
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 74, 116, 136-143
- **严重度**: HIGH
- **类型**: SSRF
- **描述**: `urlToPdf` 端点接受用户提供的 URL，通过 `fetchRemoteHtml` 方法使用 Java `HttpClient` 获取远程 HTML 内容，然后交给 WeasyPrint 渲染为 PDF。URL 验证仅检查格式（HTTP/HTTPS 正则匹配）和可达性（HTTP 状态码），但未验证目标 IP 地址。攻击者可构造指向内网 IP（如 `http://192.168.1.1/`、`http://10.0.0.1/`）或云元数据服务（`http://169.254.169.254/latest/meta-data/`）的 URL，实现 SSRF 攻击。此外，WeasyPrint 渲染引擎本身具有网络访问能力，HTML 中的 `<img src="...">`、`<link href="...">`、CSS `@import` 等资源引用会被 WeasyPrint 主动加载，形成二次 SSRF 通道。虽然代码检查了 `file://` 协议（第 118 行），但未阻止对内网 HTTP 服务的访问。
- **代码片段**:
```java
// 第 74 行 - 用户提供的 URL
String URL = request.getUrlInput();

// 第 88-91 行 - 仅验证格式，未验证目标 IP
boolean patternValid = RegexPatternUtils.getInstance().getHttpUrlPattern().matcher(URL).matches();
boolean generalValid = GeneralUtils.isValidURL(URL);
if (!patternValid && !generalValid) { ... }

// 第 116 行 - 直接获取远程 HTML（无内网 IP 检查）
String htmlContent = fetchRemoteHtml(URL);

// 第 136-143 行 - WeasyPrint 渲染（具有网络访问能力）
List<String> command = new ArrayList<>();
command.add(runtimePathConfig.getWeasyPrintPath());
command.add(tempHtmlInput.toString());
command.add("--base-url");
command.add(URL);  // base-url 使 WeasyPrint 可解析相对 URL
command.add("--pdf-forms");
command.add(tempOutputFile.toString());
```
- **修复建议**:
  1. 在 `fetchRemoteHtml` 之前，解析 URL 的主机名并验证其 IP 地址不属于私有网段（RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16）、环回地址（127.0.0.0/8）、链路本地地址（169.254.0.0/16）和保留地址。
  2. 使用 DNS 解析后的 IP 进行验证（防止 DNS rebinding），并在 HttpClient 层面限制连接目标。
  3. 考虑对 WeasyPrint 使用沙箱化网络环境（如通过 `unshare --net` 或 Docker 网络策略限制出站连接）。
  4. 在传递给 WeasyPrint 的 HTML 中，移除或替换所有非安全来源的外部资源引用。

---

### 问题 3
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: CRITICAL
- **类型**: HardcodedSecret
- **描述**: 当未在配置中指定初始管理员凭据且数据库中不存在用户时，系统自动创建默认管理员账户，用户名为 `"admin"`，密码为 `"stirling"`。这是硬编码的默认管理员凭据，任何知道此默认值的人都可以使用管理员权限登录系统。在公网部署的场景下，这是一个极其严重的安全风险，因为默认凭据广为人知（在项目的文档和 Docker 镜像中均有记录）。结合问题 1 的 CSRF + CORS 漏洞，攻击者甚至可以通过构造恶意网页直接以管理员身份执行任意操作。
- **代码片段**:
```java
// 第 154-155 行 - 硬编码默认管理员凭据
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
  1. 移除硬编码的默认密码。首次启动时，应强制要求用户通过环境变量（如 `SPRING_SECURITY_USER_PASSWORD`）或初始化向导设置管理员密码。
  2. 如果必须保留默认凭据，应在首次登录后强制修改密码（代码中已有 `firstLogin(true)` 标记，但需确保前端强制密码修改流程不可跳过）。
  3. 在启动日志中打印醒目警告，提示用户立即修改默认密码。
  4. 考虑在检测到公网部署时拒绝使用默认凭据启动。

---

### 问题 4
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 64-66
- **严重度**: HIGH
- **类型**: XSS
- **描述**: `CustomHtmlSanitizer.sanitize()` 方法通过 `applicationProperties.getSystem().isDisableSanitize()` 配置项可以完全绕过 HTML 净化。当 `disableSanitize` 设为 `true` 时，所有 HTML 内容将不经任何净化直接返回，包括 `<script>` 标签、事件处理器（`onerror`、`onload`）、`javascript:` URL 等所有 XSS 载荷。同样的 `disableSanitize` 开关也影响 `SvgSanitizer`（第 59 行）和 `OfficeDocumentSanitizer`（第 80 行），意味着一个配置项同时禁用了三类净化器。虽然此配置仅管理员可通过 `settings.yml` 修改（非用户可控），但其影响范围广泛，一旦启用将完全暴露 XSS 攻击面。
- **代码片段**:
```java
// CustomHtmlSanitizer.java 第 64-66 行
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java 第 59-62 行（同样受影响）
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java 第 80-83 行（同样受影响）
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**:
  1. 移除 `disableSanitize` 全局开关，或将其拆分为细粒度控制（分别控制 HTML、SVG、Office 文档的净化）。
  2. 如果保留此开关，应在启用时输出醒目的安全警告日志。
  3. 考虑添加运行时检测：当 `disableSanitize=true` 且系统检测到公网访问时，自动重新启用净化。
  4. 在管理界面中为此配置项添加明确的安全风险提示。

---

### 问题 5
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 20-22
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath` 方法将用户可控的 `fileId` 参数直接传入 `Path.of(tempDirPath).resolve(fileId)`，未进行任何路径穿越检查。攻击者可以提供包含 `../` 的 `fileId`（如 `../../etc/passwd`），使解析后的路径指向 `tempDirPath` 之外的任意文件。与 `DatabaseService.getBackupFilePath`（正确实现了 `startsWith` 检查）不同，此方法缺少关键的路径前缀验证。如果返回的 `Path` 被用于文件读取或写入操作（如 `FileInputStream` / `FileOutputStream`），将导致任意文件读取或写入。根据 V3 判定规则，路径直接用于文件 I/O 且无检查，至少为 HIGH。
- **代码片段**:
```java
// 第 20-22 行 - 无路径穿越检查
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
    // 缺少: if (!filePath.startsWith(Path.of(tempDirPath))) throw ...
}
```
- **修复建议**:
  1. 在 `resolve` 之后添加路径前缀验证：
     ```java
     public Path resolveFilePath(String fileId) {
         Path basePath = Path.of(tempDirPath).toAbsolutePath().normalize();
         Path filePath = basePath.resolve(fileId).toAbsolutePath().normalize();
         if (!filePath.startsWith(basePath)) {
             throw new SecurityException("Path traversal detected: " + fileId);
         }
         return filePath;
     }
     ```
  2. 对 `fileId` 进行字符白名单验证（仅允许字母、数字、连字符、下划线）。
  3. 审查所有调用 `resolveFilePath` 的代码，确保返回的路径不会被用于未授权的文件操作。

---

### 问题 6
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218
- **严重度**: MEDIUM
- **类型**: CORS
- **描述**: CORS 配置默认使用 `allowedOriginPatterns("*")` 并设置 `allowCredentials(true)`。虽然在 Spring 框架中 `allowedOriginPatterns("*")` 会回显请求来源（而非返回字面量 `*`），使浏览器实际接受携带凭证的请求，但这构成了严重的安全配置不当。当管理员配置了具体的 `system.corsAllowedOrigins` 后，此问题可缓解。但在默认部署（未配置 CORS 来源）下，任意外部域均可携带用户 Cookie 发起跨域请求。此问题与问题 1（CSRF 禁用）形成组合，进一步放大了跨域攻击的风险。
- **代码片段**:
```java
// 第 181-192 行
if (configuredOrigins != null && !configuredOrigins.isEmpty()) {
    cfg.setAllowedOriginPatterns(configuredOrigins);
} else {
    // 默认允许所有来源
    cfg.setAllowedOriginPatterns(List.of("*"));
    log.info("No CORS allowed origins configured ... allowing all origins.");
}

// 第 218 行
cfg.setAllowCredentials(true);
```
- **修复建议**:
  1. 默认配置不应使用 `"*"`。如果未配置 `corsAllowedOrigins`，应默认仅允许同源请求（即不设置 `allowedOrigins`），或要求管理员在启动前显式配置。
  2. 当 `allowCredentials=true` 时，必须在文档和启动日志中强调不能与 `"*"` 一起使用。
  3. 添加启动时校验：如果检测到 `allowCredentials=true` 且 `allowedOriginPatterns` 包含 `"*"`，输出 ERROR 级别日志。

---

### 问题 7
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 337-351
- **严重度**: MEDIUM
- **类型**: Session
- **描述**: Remember-me 令牌有效期设置为 14 天（`14 * 24 * 60 * 60 = 1,209,600` 秒）。在此有效期内，即使用户已关闭浏览器，攻击者仍可通过窃取 remember-me Cookie 来冒充用户。14 天的有效期超过了 V3 标准中 MEDIUM 级别的阈值（>7 天）。此外，remember-me Cookie 与 CSRF 禁用（问题 1）组合使用，进一步增加了跨站请求伪造的风险窗口。
- **代码片段**:
```java
// 第 337-351 行
http.rememberMe(
    rememberMeConfigurer ->
        rememberMeConfigurer
            .tokenRepository(persistentTokenRepository())
            .tokenValiditySeconds(14 * 24 * 60 * 60)  // 14 天
            .userDetailsService(userDetailsService)
            .useSecureCookie(true)
            .rememberMeParameter("remember-me")
            .rememberMeCookieName("remember-me")
            .alwaysRemember(false));
```
- **修复建议**:
  1. 将 remember-me 有效期缩短至 7 天以内（推荐 24-48 小时）。
  2. 添加 remember-me 令牌的 IP 绑定或设备指纹验证。
  3. 在用户执行敏感操作时，要求重新认证（step-up authentication）。
  4. 提供管理员功能，允许批量撤销所有 remember-me 令牌。

---

### 问题 8
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 476-479
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: IP 速率限制过滤器被配置为每 IP 1,000,000 次请求（`maxRequestsPerIp = 1000000`），这在实际场景中相当于没有速率限制。代码注释（第 299-302 行）表明此过滤器因 Spring Security 异步分派 bug 而被禁用，但同时保留了极高的限制值作为"占位"。这意味着暴力破解密码、自动化 CSRF 攻击、API 滥用等均不受速率限制约束。结合默认管理员凭据（问题 3），攻击者可无限制地尝试登录。
- **代码片段**:
```java
// 第 476-479 行
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    // Example limit TODO add config level
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
```
- **修复建议**:
  1. 将速率限制设置为合理值（如每 IP 每分钟 60 次请求，登录端点每 IP 每分钟 5 次）。
  2. 修复 Spring Security 异步分派 bug，重新启用速率限制过滤器。
  3. 对登录端点实施独立的、更严格的速率限制。
  4. 考虑使用渐进式延迟（progressive delay）策略应对登录失败。

---

### 问题 9
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java`
- **行号**: 106
- **严重度**: LOW
- **类型**: PathTraversal
- **描述**: `StampController.addStamp` 方法对 PDF 文件名和印章图片文件名进行了路径穿越检查（检查 `..` 和 `/`），但未检查反斜杠 `\`。在 Windows 系统上，`\` 也是路径分隔符，攻击者可使用 `..\\` 绕过此检查。不过，经分析 `pdfFileName` 和 `stampImageName` 仅用于显示目的（嵌入 PDF 印章文本和生成输出文件名），不用于文件系统路径构造，因此实际路径穿越风险较低。根据 V3 判定规则，检查了 `..` 但未检查 `\`，但文件名仅用于显示，故评为 LOW。
- **代码片段**:
```java
// 第 106 行 - 仅检查 .. 和 /，未检查 \
if (pdfFileName.contains("..") || pdfFileName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(
        "error.invalid.filepath", "Invalid PDF file path: " + pdfFileName);
}

// 第 121-129 行 - 同样的不完整检查
if (stampImageName == null
        || stampImageName.contains("..")
        || stampImageName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(...);
}
```
- **修复建议**:
  1. 添加反斜杠检查：`pdfFileName.contains("\\")`。
  2. 更好的做法是使用 `Filenames.toSimpleFileName()` 对文件名进行完整净化。
  3. 由于文件名仅用于显示，风险较低，但仍建议修复以保持防御一致性。

---

### 问题 10
- **文件**: `app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java`
- **行号**: 491-537
- **严重度**: LOW
- **类型**: CommandInjection
- **描述**: `ProcessExecutor.validateCommand` 方法对命令参数进行了基本安全检查（检查 null 字节、换行符、可执行文件路径穿越），但未对命令参数进行完整的白名单验证。可执行文件路径检查仅在包含 `/` 或 `\` 时才验证文件是否存在（第 519 行），对于纯名称（如 `"gs"`、`"qpdf"`）依赖 PATH 解析。虽然当前所有调用方均使用列表参数（非 shell 执行），且参数来自内部逻辑或经过数值转换的用户输入，但 `validateCommand` 作为安全边界方法，其验证不够完整。如果未来有新的调用方未正确过滤用户输入，可能引入命令注入风险。
- **代码片段**:
```java
// 第 491-537 行 - 基本验证但非白名单
private void validateCommand(List<String> command) {
    // 检查 null 字节和换行符
    for (String arg : command) {
        if (arg.indexOf('\0') >= 0 || arg.indexOf('\n') >= 0 || arg.indexOf('\r') >= 0) {
            throw new IllegalArgumentException("Command contains invalid characters");
        }
    }
    // 仅对包含路径分隔符的可执行文件检查存在性
    if (executable.contains("/") || executable.contains("\\")) {
        // ... 验证文件存在
    }
    // 对于相对路径（如 "gs", "qpdf"），依赖 PATH 解析
}
```
- **修复建议**:
  1. 为可执行文件实现白名单验证，仅允许预定义的安全命令（如 `gs`、`qpdf`、`pdftohtml`、`weasyprint` 等）。
  2. 对命令参数添加长度限制和字符白名单。
  3. 使用 `RuntimePathConfig` 中配置的完整路径替代 PATH 解析，确保执行的是预期的二进制文件。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 3 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 2 |
| **总计** | **10** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| SQLi | 0 |
| XSS | 1 |
| XXE | 0 |
| PathTraversal | 2 |
| CommandInjection | 1 |
| SSRF | 1 |
| FileUpload | 0 |
| HardcodedSecret | 1 |
| CSRF | 1 |
| CORS | 1 |
| Auth | 1 |
| Session | 1 |

---

## 正面发现

1. **XML 外部实体（XXE）防护完善**: `SvgSanitizer.parseSecurely()` 和 `OfficeDocumentSanitizer.parseSecurely()` 均正确禁用了所有外部实体和 DTD 加载，包括 `FEATURE_SECURE_PROCESSING`、`disallow-doctype-decl`、`external-general-entities`、`external-parameter-entities`、`load-external-dtd`，并设置了 `setXIncludeAware(false)` 和 `setExpandEntityReferences(false)`。`TransformerFactory` 同样设置了 `FEATURE_SECURE_PROCESSING`。

2. **命令执行使用列表参数**: 所有外部进程调用（WeasyPrint、Ghostscript、QPDF、pdftohtml、LibreOffice、Python/OpenCV）均使用 `ProcessBuilder` 的列表参数形式，避免了 shell 注入风险。未使用 `shell=True` 或字符串拼接命令。

3. **数据库操作使用参数化查询**: `DatabaseService` 中的所有 SQL 操作均使用 `PreparedStatement` 和参数化查询（`stmt.setString(1, ...)`），未发现 SQL 字符串拼接。此外，`validateSqlContent` 方法实现了 SQL 白名单/黑名单双重验证，防止恶意 SQL 通过备份导入执行。

4. **凭据加密实现规范**: `CredentialEncryption` 使用 AES-256-GCM（认证加密），密钥通过 `SecureRandom` 生成 12 字节 IV，密钥文件使用 0600 权限（仅所有者读写），支持环境变量和密钥文件两种密钥来源，集群模式下强制要求共享密钥。

5. **SVG 净化器实现全面**: `SvgSanitizer` 移除了危险元素（`script`、`foreignobject`、`iframe`、`object`、`embed` 等）、事件处理器属性（`on*`）、`javascript:` 和 `data:` 危险 URL，并对 URL 属性进行 SSRF 检查。URL 规范化处理了多层 URL 编码和 null 字节。

6. **SVG 覆盖工具阻止外部资源加载**: `SvgOverlayUtil` 中的 `UserAgent` 实现正确阻止了所有外部资源加载（仅允许 `data:` URI），有效防止了 SVG 中的 SSRF 和信息泄露。

7. **备份文件路径安全**: `DatabaseService.getBackupFilePath` 正确实现了路径穿越防护（`normalize()` + `startsWith` 检查），`isValidFileName` 方法对文件名进行了全面的非法字符检查。

8. **临时文件管理**: 项目广泛使用 `TempFileManager` 和 `TempFile` 进行临时文件的创建和清理，`try-with-resources` 模式确保文件在使用后正确释放。

9. **Office 文档净化**: `OfficeDocumentSanitizer` 使用 `ZipSecurity.createHardenedInputStream` 防止 Zip Bomb 攻击，并剥离 OOXML 外部关系和 ODF 外部 href 属性，防止 LibreOffice 处理时的 SSRF。

10. **文件名净化**: `ConvertWebsiteToPDF.convertURLToFileName` 和 `PipelineProcessor` 中使用 `Filenames.toSimpleFileName()`（pixee 安全库）对文件名进行净化，防止路径穿越。

---

## 关键风险总结

1. **CSRF + CORS + Cookie 认证组合漏洞 (CRITICAL)**: 这是最严重的安全问题。CSRF 全局禁用 + CORS 默认允许所有来源 + 允许携带凭证 + form login/remember-me Cookie 认证，构成了完整的跨站请求伪造攻击链。攻击者可构造恶意网页，以任意已登录用户（包括管理员）的身份执行所有操作。此漏洞无需用户交互（仅需访问恶意页面），影响所有启用登录功能的部署。

2. **SSRF 漏洞 - URL 转 PDF 功能 (HIGH)**: URL 转 PDF 功能允许用户提供的 URL 指向内网服务和云元数据端点（169.254.169.254）。WeasyPrint 渲染引擎本身具有网络访问能力，形成二次 SSRF 通道。在云环境部署中，攻击者可通过此漏洞获取实例元数据、IAM 凭据等敏感信息。

3. **硬编码默认管理员凭据 (CRITICAL)**: 默认管理员账户 `admin/stirling` 在代码中硬编码。虽然设置了 `firstLogin=true` 标记以提示修改密码，但如果用户忽略此提示或自动化部署未处理此流程，系统将长期暴露已知凭据。结合 CSRF 漏洞，攻击者可远程利用此凭据获取完全控制权。

4. **disableSanitize 全局净化绕过 (HIGH)**: 单一配置项可同时禁用 HTML、SVG 和 Office 文档三类净化器。虽然仅管理员可配置，但其影响范围过大，一旦误启用将完全暴露 XSS 和 SVG 攻击面。

5. **路径穿越 - FileOrUploadService (HIGH)**: `resolveFilePath` 方法缺少路径前缀验证，可能导致任意文件读取/写入。具体影响取决于调用方如何使用返回的路径。

---

## 评审完成确认

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用组合漏洞判定规则（CSRF + CORS + Cookie 认证 = CRITICAL）

### 文件覆盖确认

| # | 文件 | 已审查 | 发现问题 |
|---|------|--------|----------|
| 1 | `ConvertWebsiteToPDF.java` | 是 | SSRF (HIGH) |
| 2 | `StampController.java` | 是 | PathTraversal (LOW) |
| 3 | `CompressController.java` | 是 | 无直接问题（安全使用 ProcessExecutor） |
| 4 | `SvgOverlayUtil.java` | 是 | 无问题（良好安全实践） |
| 5 | `FileOrUploadService.java` | 是 | PathTraversal (HIGH) |
| 6 | `CustomHtmlSanitizer.java` | 是 | XSS (HIGH) |
| 7 | `SvgSanitizer.java` | 是 | XSS（同 disableSanitize 开关，归入问题 4） |
| 8 | `OfficeDocumentSanitizer.java` | 是 | XSS（同 disableSanitize 开关，归入问题 4） |
| 9 | `ProcessExecutor.java` | 是 | CommandInjection (LOW) |
| 10 | `CredentialEncryption.java` | 是 | 无问题（良好安全实践） |
| 11 | `InitialSecuritySetup.java` | 是 | HardcodedSecret (CRITICAL) |
| 12 | `SecurityConfiguration.java` | 是 | CSRF+CORS (CRITICAL), CORS (MEDIUM), Session (MEDIUM), Auth (MEDIUM) |
| 13 | `DatabaseController.java` | 是 | 无直接问题（ADMIN 权限保护 + 路径验证完善） |
| 14 | `DatabaseService.java` | 是 | 无问题（参数化查询 + 路径验证 + SQL 白名单） |
| 15 | `DesktopClientUtils.java` | 是 | 无问题（仅检测客户端类型和配置过期时间） |
| 16 | `ExtractImageScansController.java` | 是 | 无直接问题（安全使用 ProcessExecutor） |
| 17 | `PDFToFile.java` | 是 | 无直接问题（安全使用 ProcessExecutor + 文件名净化） |
| 18 | `PipelineProcessor.java` | 是 | 无直接问题（使用 pixee 安全库净化文件名） |

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Zeta
