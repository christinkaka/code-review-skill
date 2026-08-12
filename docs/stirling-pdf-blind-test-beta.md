# Agent Beta 独立评审报告 - Stirling-PDF

**评审日期**: 2026-08-12
**评审范围**: `app/core/src/main/java/` 和 `app/common/src/main/java/` 及 `app/proprietary/src/main/java/` 下的核心业务代码
**评审重点**: controller、service、util 目录
**评审焦点**: 安全问题（SQLi、XSS、XXE、Path Traversal、Command Injection、SSRF、FileUpload、HardcodedSecret）

---

## 发现的问题

### 问题 1
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- 行号: 154-155
- 严重度: HIGH
- 类型: HardcodedSecret
- 描述: 默认管理员用户名和密码硬编码在源代码中。当没有配置初始用户时，系统会创建用户名为 "admin"、密码为 "stirling" 的默认管理员账户。攻击者可直接使用此凭据获取管理员权限。
- 代码片段:
```java
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";
    // ...
}
```

### 问题 2
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- 行号: 269
- 严重度: HIGH
- 类型: XSS
- 描述: CSRF 保护被完全禁用 (`http.csrf(CsrfConfigurer::disable)`)。这使得所有经过认证的 state-changing 请求（如修改设置、数据库导入/导出等）都可能受到跨站请求伪造攻击。虽然 API 端点可能使用 JWT 认证（一定程度上缓解此问题），但 form login 和 remember-me 功能仍然使用基于 cookie 的认证，这些端点直接暴露于 CSRF 风险中。
- 代码片段:
```java
http.csrf(CsrfConfigurer::disable);
```

### 问题 3
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- 行号: 186-188
- 严重度: HIGH
- 类型: XSS
- 描述: CORS 配置在未设置允许来源时默认允许所有来源 (`*`)，同时设置了 `setAllowCredentials(true)`。这意味着任何第三方网站都可以向该应用发送带有认证信息的跨域请求。虽然现代浏览器对 `allowCredentials=true` 与 `allowedOrigins=*` 的组合有所限制，但使用 `allowedOriginPatterns(List.of("*"))` 绕过了这一浏览器保护。
- 代码片段:
```java
cfg.setAllowedOriginPatterns(List.of("*"));
// ...
cfg.setAllowCredentials(true);
```

### 问题 4
- 文件: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- 行号: 136-141
- 严重度: HIGH
- 类型: SSRF
- 描述: URL-to-PDF 转换中，WeasyPrint 命令使用了 `--base-url` 参数传入用户提供的 URL。虽然初始 URL 经过了 SSRF 校验（检查私有地址范围），但 WeasyPrint 在渲染 HTML 时会根据 `--base-url` 解析 HTML 中的所有相对 URL 引用。如果下载的 HTML 内容中包含指向内部网络资源的相对路径（如 `<img src="/api/internal/secret">`），WeasyPrint 会向目标内部地址发起请求，从而绕过 SSRF 防护。此外，`fetchRemoteHtml()` 使用 `Redirect.NEVER` 不跟随重定向，但 WeasyPrint 自身在渲染时会跟随重定向，形成第二条绕过路径。
- 代码片段:
```java
List<String> command = new ArrayList<>();
command.add(runtimePathConfig.getWeasyPrintPath());
command.add(tempHtmlInput.toString());
command.add("--base-url");
command.add(URL);  // 用户提供的 URL 作为 base-url
command.add("--pdf-forms");
command.add(tempOutputFile.toString());
```

### 问题 5
- 文件: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- 行号: 64-66
- 严重度: HIGH
- 类型: XSS
- 描述: HTML 净化器可以通过配置项 `system.disableSanitize` 完全禁用。当此选项被启用时，所有 HTML 输入（包括 HTML-to-PDF 转换、EML-to-PDF 转换等）都不会经过任何净化处理，直接传递给 WeasyPrint 渲染。攻击者可以注入任意恶意 HTML 内容（包括外部资源引用、CSS 注入、表单钓鱼等）。
- 代码片段:
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```

### 问题 6
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- 行号: 476-479
- 严重度: MEDIUM
- 类型: HardcodedSecret
- 描述: IP 速率限制被设置为 1,000,000 次请求（实质上是无限制），并且该过滤器在代码中被注释掉未启用。这使得应用容易受到暴力破解攻击和拒绝服务攻击。代码注释表明这是由于 Spring Security 异步分发的 bug 导致的临时禁用。
- 代码片段:
```java
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
// 在 filterChain 配置中:
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op)
```

### 问题 7
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- 行号: 273-274
- 严重度: MEDIUM
- 类型: XSS
- 描述: 当登录功能被禁用时，X-Frame-Options 头也被自动禁用。这使得应用容易受到点击劫持（Clickjacking）攻击。攻击者可以将应用嵌入恶意网站的 iframe 中，诱导用户执行非预期操作。
- 代码片段:
```java
if (!loginEnabledValue) {
    http.headers(headers -> headers.frameOptions(FrameOptionsConfig::disable));
}
```

### 问题 8
- 文件: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/ExtractImageScansController.java`
- 行号: 79
- 严重度: MEDIUM
- 类型: PathTraversal
- 描述: 从用户上传的文件名中提取扩展名时未进行充分的边界检查。当文件名不包含 `.` 时，`fileName.lastIndexOf('.')` 返回 -1，导致 `fileName.substring(0)` 返回完整文件名作为扩展名。此扩展名后续用于创建临时文件路径，如果文件名包含路径分隔符或其他特殊字符，可能导致路径穿越。
- 代码片段:
```java
String fileName = inputFile.getOriginalFilename();
String extension = fileName.substring(fileName.lastIndexOf('.') + 1);
// ...
tempInputFile = tempFileManager.createManagedTempFile("." + extension);
```

### 问题 9
- 文件: `app/common/src/main/java/stirling/software/common/util/PDFToFile.java`
- 行号: 100-104, 198-201
- 严重度: MEDIUM
- 类型: CommandInjection
- 描述: PDF 转 HTML/Markdown 功能中，用户提供的文件名经过 `Filenames.toSimpleFileName()` 处理后直接作为 `pdftohtml` 命令的参数。虽然 `ProcessExecutor.validateCommand()` 会检查 null 字节和换行符，但文件名被用作 pdftohtml 的输出基础名，在某些情况下可能注入以 `-` 开头的参数名，被 pdftohtml 解释为命令行选项。
- 代码片段:
```java
String pdfBaseName = originalPdfFileName;
if (originalPdfFileName.contains(".")) {
    pdfBaseName = originalPdfFileName.substring(0, originalPdfFileName.lastIndexOf('.'));
}
List<String> command = new ArrayList<>(Arrays.asList(
    "pdftohtml", "-s", "-noframes", "-c",
    tempInputFile.getAbsolutePath(),
    pdfBaseName));  // 用户可控的文件名
```

### 问题 10
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java`
- 行号: 144-145
- 严重度: MEDIUM
- 类型: PathTraversal
- 描述: 数据库备份文件的删除接口使用 GET 方法并通过路径变量接收文件名。虽然 `DatabaseService.getBackupFilePath()` 有路径穿越检查，`isValidFileName()` 也做了基本的字符过滤，但使用 GET 方法进行状态变更操作（删除文件）违反 REST 安全原则，且可能被 CSRF 攻击利用（结合问题 2 的 CSRF 禁用）。
- 代码片段:
```java
@GetMapping("/delete/{fileName}")
public ResponseEntity<?> deleteFile(@PathVariable String fileName) {
    // ...
    databaseService.deleteBackupFile(fileName);
}
```

### 问题 11
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java`
- 行号: 34-51
- 严重度: LOW
- 类型: HardcodedSecret
- 描述: 桌面客户端检测完全依赖 User-Agent 头部信息。攻击者可以通过伪造 User-Agent 包含 "tauri"、"stirlingpdf-desktop" 或 "electron" 字符串来获得更长的 JWT token 过期时间（默认 30 天 vs 普通 web token），从而延长被盗凭据的有效期。
- 代码片段:
```java
public static boolean isDesktopClient(HttpServletRequest request) {
    String userAgent = request.getHeader("User-Agent");
    String userAgentLower = userAgent.toLowerCase();
    boolean hasTauri = userAgentLower.contains("tauri");
    boolean hasStirling = userAgentLower.contains("stirlingpdf-desktop");
    boolean hasElectron = userAgentLower.contains("electron");
    return hasTauri || hasStirling || hasElectron;
}
```

### 问题 12
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java`
- 行号: 78-87
- 严重度: LOW
- 类型: SSRF
- 描述: 数据库导入错误信息中直接包含了异常的完整消息 (`e.getMessage()`)，可能泄露数据库内部结构、文件路径等敏感信息。虽然此端点需要 ADMIN 角色，但信息泄露仍违反了纵深防御原则。
- 代码片段:
```java
} catch (Exception e) {
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(java.util.Map.of(
            "error", "failedImportFile",
            "message", "Failed to import database: " + e.getMessage()));
}
```

### 问题 13
- 文件: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- 行号: 58-59
- 严重度: MEDIUM
- 类型: SSRF
- 描述: URL-to-PDF 转换中对 `file:` 协议的检测使用黑名单方式（正则匹配），仅阻止了 `file:` scheme。但 WeasyPrint 还支持其他潜在的危险 scheme（如 `data:` URI 等），这些未被过滤。黑名单方式本质上不如白名单安全，可能存在绕过风险。
- 代码片段:
```java
private static final Pattern FILE_SCHEME_PATTERN =
    Pattern.compile("(?<![a-z0-9_])file\\s*:(?:/{1,3}|%2f|%5c|%3a|&#x2f;|&#47;)");

private boolean containsDisallowedUriScheme(String htmlContent) {
    // 只检测 file: 协议
    return FILE_SCHEME_PATTERN.matcher(normalized).find();
}
```

### 问题 14
- 文件: `app/core/src/main/java/stirling/software/SPDF/controller/api/pipeline/PipelineProcessor.java`
- 行号: 346-349
- 严重度: LOW
- 类型: PathTraversal
- 描述: Pipeline 处理器中对文件名的路径穿越检查只检测了 `..` 前缀，但 `Path.of(file.getName()).normalize()` 在 normalize 后可能不会以 `..` 开头（例如当文件名是绝对路径时）。此检查可以被绕过。不过由于此方法处理的是已经写入临时目录的文件，实际风险较低。
- 代码片段:
```java
Path normalizedPath = Path.of(file.getName()).normalize();
if (normalizedPath.startsWith("..")) {
    throw new SecurityException(
        "Potential path traversal attempt in file name: " + file.getName());
}
```

### 问题 15
- 文件: `app/proprietary/src/main/java/stirling/software/proprietary/security/service/DatabaseService.java`
- 行号: 523-571
- 严重度: LOW
- 类型: SQLi
- 描述: 数据库备份导入的 SQL 验证逻辑使用正则表达式匹配来检测危险 SQL 操作。虽然使用了白名单+黑名单双重检查，并去除了注释和字符串字面量，但正则表达式解析 SQL 本质上是不可靠的。精心构造的 SQL 可能绕过正则检测。不过由于使用了 `PreparedStatement` 的 `RUNSCRIPT from ?` 来执行，且验证在 H2 数据库环境下运行，实际风险有所降低。
- 代码片段:
```java
private void validateSqlContent(Path scriptPath) {
    String content = Files.readString(scriptPath);
    String normalizedContent = sanitizeSql(content);
    String codeOnly = stripStringLiterals(normalizedContent);
    for (Pattern deniedPattern : DENIED_PATTERNS) {
        if (deniedPattern.matcher(codeOnly).find()) {
            throw new IllegalArgumentException("SQL script contains disallowed operations");
        }
    }
    // 白名单检查...
}
```

---

## 正面发现（安全防护措施）

在评审过程中也发现了多处良好的安全实践：

1. **ProcessExecutor 命令验证** (`ProcessExecutor.java:491-538`): 对所有命令参数进行了 null 字节、换行符和路径穿越检查，有效防止了命令注入。
2. **SSRF 防护** (`GeneralUtils.java:300-371`): `isURLReachable()` 方法实现了全面的私有/保留 IP 地址检查，包括 IPv4 和 IPv6 的处理。
3. **ZIP 文件安全** (`FileToPdf.java:84-96`): 使用了 `ZipSecurity.createHardenedInputStream()` 和路径穿越检查来防止 Zip Slip 攻击。
4. **HTML 净化** (`CustomHtmlSanitizer.java`): 默认启用 OWASP HTML Sanitizer，并集成了 SSRF 安全的 URL 策略。
5. **数据库备份路径安全** (`DatabaseService.java:475-482`): `getBackupFilePath()` 实现了路径穿越检查。
6. **文件名净化** (`GeneralUtils.java` 和 `Filenames.toSimpleFileName()`): 多处使用了 Pixee Security 库的文件名净化功能。
7. **外部 API 调用安全** (`ExternalApiCaller.java`): 禁止跟随重定向，并在 dispatch 时重新验证目标主机。
8. **敏感字段脱敏** (`AdminSettingsController.java:888-958`): 对设置 API 中的密码、密钥等敏感字段进行了掩码处理。

---

## 统计
- 总问题数: 15
- CRITICAL: 0
- HIGH: 5
- MEDIUM: 6
- LOW: 4

## 评审文件清单

### Controller 层（已评审）
- `ConvertWebsiteToPDF.java` - URL 转 PDF（SSRF 风险）
- `ConvertHtmlToPDF.java` - HTML 转 PDF
- `ConvertPDFToHtml.java` - PDF 转 HTML
- `ConvertEmlToPDF.java` - 邮件转 PDF
- `OCRController.java` - OCR 处理
- `RepairController.java` - PDF 修复
- `MetadataController.java` - 元数据编辑
- `ExtractImageScansController.java` - 图片扫描提取
- `AttachmentController.java` - 附件管理
- `PipelineController.java` - 管道处理
- `AdminSettingsController.java` - 管理设置
- `DatabaseController.java` - 数据库管理

### Service 层（已评审）
- `PipelineProcessor.java` - 管道处理器
- `DatabaseService.java` - 数据库服务
- `KeyPersistenceService.java` - JWT 密钥持久化
- `InitialSecuritySetup.java` - 初始安全设置
- `ExternalApiCaller.java` - 外部 API 调用

### Util/Config 层（已评审）
- `ProcessExecutor.java` - 进程执行器
- `GeneralUtils.java` - 通用工具类
- `FileToPdf.java` - 文件转 PDF
- `CustomHtmlSanitizer.java` - HTML 净化器
- `PDFToFile.java` - PDF 转文件
- `DesktopClientUtils.java` - 桌面客户端检测
- `SecurityConfiguration.java` - 安全配置
