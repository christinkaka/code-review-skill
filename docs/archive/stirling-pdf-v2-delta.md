# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: CRITICAL
- **类型**: HardcodedSecret
- **描述**: 硬编码默认管理员凭据。当未配置初始管理员时，系统自动创建用户名为 "admin"、密码为 "stirling" 的管理员账户，且密码在代码中明文硬编码。攻击者可直接使用此默认凭据获取系统管理员权限，完全控制应用。虽然设置了 `firstLogin(true)` 标记，但代码中未强制要求用户首次登录时修改密码。
- **代码片段**:
```java
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";
    
    if (userService.findByUsernameIgnoreCase(defaultUsername).isEmpty()) {
        // ... 创建管理员账户
    }
}
```
- **修复建议**: 
  1. 移除硬编码的默认凭据，改为在首次启动时强制用户设置管理员账户
  2. 如果必须保留默认凭据，应在首次登录时强制修改密码
  3. 在日志和文档中明确警告默认凭据的存在
  4. 考虑使用环境变量或配置文件提供初始凭据

### 问题 2
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 20-22
- **严重度**: CRITICAL
- **类型**: PathTraversal
- **描述**: 路径穿越漏洞。`resolveFilePath()` 方法直接将用户输入的 `fileId` 参数拼接到路径中，未进行任何路径规范化或验证。攻击者可输入 `../../etc/passwd` 等恶意路径，访问服务器上的任意文件。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```
- **修复建议**:
```java
public Path resolveFilePath(String fileId) {
    Path basePath = Path.of(tempDirPath).toAbsolutePath().normalize();
    Path resolvedPath = basePath.resolve(fileId).normalize();
    
    if (!resolvedPath.startsWith(basePath)) {
        throw new SecurityException("Path traversal attempt detected");
    }
    return resolvedPath;
}
```

### 问题 3
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269
- **严重度**: CRITICAL
- **类型**: CSRF
- **描述**: CSRF 保护完全禁用。`http.csrf(CsrfConfigurer::disable)` 禁用了所有端点的 CSRF 保护。结合问题 4 中的 CORS 配置（允许任意源携带凭证），攻击者可以构造恶意网页，诱导已认证用户访问，从而以用户身份执行任意操作（如上传文件、修改设置、删除数据等）。
- **代码片段**:
```java
http.csrf(CsrfConfigurer::disable);
```
- **修复建议**:
  1. 对基于会话认证的端点启用 CSRF 保护
  2. 仅对 API 端点（使用 JWT 或 API Key 认证）禁用 CSRF
  3. 使用 Spring Security 的 `csrf()` 默认配置，或配置 CSRF token 存储

### 问题 4
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218
- **严重度**: CRITICAL
- **类型**: CORS
- **描述**: CORS 配置允许任意源携带凭证访问。默认配置 `setAllowedOriginPatterns(List.of("*"))` 允许任何来源的跨域请求，且 `setAllowCredentials(true)` 允许携带认证凭证（Cookie）。此配置与 CSRF 禁用相结合，使得跨站请求伪造攻击成为可能。
- **代码片段**:
```java
CorsConfiguration cfg = new CorsConfiguration();
if (configuredOrigins != null && !configuredOrigins.isEmpty()) {
    cfg.setAllowedOriginPatterns(configuredOrigins);
} else {
    cfg.setAllowedOriginPatterns(List.of("*"));  // 允许任意源
}
// ...
cfg.setAllowCredentials(true);  // 允许携带凭证
```
- **修复建议**:
  1. 移除通配符 `*` 配置，要求明确指定允许的源
  2. 在生产环境中，仅允许受信任的域名
  3. 当 `allowCredentials=true` 时，不能使用通配符源

### 问题 5
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 175-200
- **严重度**: HIGH
- **类型**: SSRF
- **描述**: 服务端请求伪造（SSRF）漏洞。`fetchRemoteHtml()` 方法接受用户提供的 URL 并发起 HTTP 请求，但未验证目标 IP 地址。攻击者可指定内网地址（如 `http://169.254.169.254/latest/meta-data/` 访问 AWS 元数据，或 `http://127.0.0.1:8080/` 访问内部服务），从而访问内部网络资源。
- **代码片段**:
```java
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
- **修复建议**:
  1. 验证 URL 目标 IP，禁止访问私有 IP 范围（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 127.0.0.0/8）
  2. 禁止访问元数据服务 IP（169.254.169.254）
  3. 使用白名单机制，仅允许访问公共互联网地址
  4. 考虑使用代理服务器隔离外部请求

### 问题 6
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java`
- **行号**: 106-109, 121-129
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: 不完整的路径穿越检查。代码检查了 `..` 和以 `/` 开头的路径，但未检查反斜杠 `\`（Windows 路径分隔符）和 URL 编码的变体（如 `%2e%2e%2f`）。虽然当前代码中文件名未直接用于文件读取操作，但不完整的检查可能在后续代码变更中引入风险。
- **代码片段**:
```java
String pdfFileName = pdfFile.getOriginalFilename();
if (pdfFileName.contains("..") || pdfFileName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(
            "error.invalid.filepath", "Invalid PDF file path: " + pdfFileName);
}
// ...
String stampImageName = stampImage.getOriginalFilename();
if (stampImageName == null || stampImageName.contains("..") 
        || stampImageName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(
            "error.invalidFormat", "Invalid {0} format: {1}", 
            "stamp image file path", stampImageName);
}
```
- **修复建议**:
```java
private void validateFileName(String fileName) {
    if (fileName == null || fileName.isEmpty()) {
        throw new IllegalArgumentException("File name cannot be empty");
    }
    // 检查各种路径穿越模式
    if (fileName.contains("..") || fileName.contains("/") 
            || fileName.contains("\\")) {
        throw new IllegalArgumentException("Invalid file name: " + fileName);
    }
    // URL 解码后再次检查
    try {
        String decoded = URLDecoder.decode(fileName, StandardCharsets.UTF_8);
        if (decoded.contains("..") || decoded.contains("/") 
                || decoded.contains("\\")) {
            throw new IllegalArgumentException("Invalid file name");
        }
    } catch (Exception e) {
        throw new IllegalArgumentException("Invalid file name encoding");
    }
}
```

### 问题 7
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 64-67
- **严重度**: HIGH
- **类型**: XSS
- **描述**: HTML 净化可通过配置完全绕过。`disableSanitize` 配置项允许完全禁用 HTML 净化，当此配置启用时，所有用户输入的 HTML 将未经净化直接处理，可能导致存储型或反射型 XSS 攻击。
- **代码片段**:
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```
- **修复建议**:
  1. 移除 `disableSanitize` 配置选项，或仅在开发环境中可用
  2. 在生产环境中强制启用 HTML 净化
  3. 如果必须保留此选项，添加明确的警告日志和安全检查
  4. 考虑使用更细粒度的配置，允许自定义净化规则而非完全禁用

### 问题 8
- **文件**: `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java`
- **行号**: 59-62
- **严重度**: HIGH
- **类型**: XSS
- **描述**: SVG 净化可通过配置完全绕过。与问题 7 相同，`disableSanitize` 配置项允许完全禁用 SVG 净化。SVG 文件可能包含 `<script>` 标签、事件处理器（如 `onload`）等恶意内容，禁用净化将导致 XSS 攻击。
- **代码片段**:
```java
public byte[] sanitize(byte[] svgBytes) throws IOException {
    // ...
    if (applicationProperties.getSystem().isDisableSanitize()) {
        log.debug("SVG sanitization disabled by configuration");
        return svgBytes;
    }
    // ...
}
```
- **修复建议**: 同问题 7

### 问题 9
- **文件**: `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java`
- **行号**: 80-83
- **严重度**: HIGH
- **类型**: XSS
- **描述**: Office 文档净化可通过配置完全绕过。与问题 7、8 相同，`disableSanitize` 配置项允许完全禁用 Office 文档（如 DOCX、XLSX）净化。Office 文档可能包含外部引用、宏或其他恶意内容。
- **代码片段**:
```java
public byte[] sanitize(byte[] documentBytes, String extension) throws IOException {
    // ...
    if (applicationProperties.getSystem().isDisableSanitize()) {
        log.debug("Office document sanitization disabled by configuration");
        return documentBytes;
    }
    // ...
}
```
- **修复建议**: 同问题 7

### 问题 10
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 742-749
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **描述**: 使用 MD5 弱哈希算法。`generateMD5()` 方法使用 MD5 算法生成图像哈希，用于图像去重。MD5 已被证明存在碰撞漏洞，不应用于安全敏感场景。虽然此处仅用于图像去重而非密码存储，但仍建议使用更安全的哈希算法。
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
- **修复建议**:
  1. 使用 SHA-256 替代 MD5
  2. 如果性能是关键考虑，可使用更快的非加密哈希（如 MurmurHash）用于去重
  3. 在代码注释中明确说明此哈希仅用于去重，不用于安全目的

### 问题 11
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 35-41
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: SVG 解析可能存在 XXE 风险。`SAXSVGDocumentFactory` 创建 SVG 文档时，未显式配置 XXE 防护。虽然通过自定义 `UserAgent` 阻止了外部资源加载，但 XML 解析器本身可能仍易受 XXE 攻击（如通过 DOCTYPE 声明）。
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
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

// 配置 XXE 防护
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```

### 问题 12
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java`
- **行号**: 104-105, 113
- **严重度**: MEDIUM
- **类型**: FileUpload
- **描述**: 文件上传未验证文件类型。PDF 文件和印章图像上传时未验证 MIME 类型或文件扩展名。攻击者可上传恶意文件（如包含恶意 PDF 漏洞利用代码的文件），虽然 PDFBox 库本身有一定的安全防护，但缺乏文件类型验证增加了攻击面。
- **代码片段**:
```java
MultipartFile pdfFile = request.getFileInput();
String pdfFileName = pdfFile.getOriginalFilename();
// 未验证 pdfFile.getContentType() 或文件扩展名

MultipartFile stampImage = request.getStampImage();
// 未验证 stampImage.getContentType() 是否为图像类型
```
- **修复建议**:
```java
// 验证 PDF 文件类型
String pdfContentType = pdfFile.getContentType();
if (pdfContentType == null || !pdfContentType.equals("application/pdf")) {
    throw new IllegalArgumentException("Only PDF files are allowed");
}

// 验证印章图像类型
String imageContentType = stampImage.getContentType();
if (imageContentType == null || !imageContentType.startsWith("image/")) {
    throw new IllegalArgumentException("Only image files are allowed");
}
```

### 问题 13
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java`
- **行号**: 42-88
- **严重度**: MEDIUM
- **类型**: FileUpload
- **描述**: 数据库备份文件上传未严格验证。`importDatabase` 端点接受 SQL 文件上传，虽然后端有 SQL 内容验证（白名单/黑名单机制），但未在上传时验证文件扩展名或 MIME 类型。攻击者可上传非 SQL 文件，虽然内容验证会阻止恶意 SQL，但增加了不必要的处理开销。
- **代码片段**:
```java
@PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE, 
        value = "import-database")
public ResponseEntity<?> importDatabase(
        @RequestParam("fileInput") MultipartFile file) throws IOException {
    if (file == null || file.isEmpty()) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(/* ... */);
    }
    // 未验证文件扩展名或 MIME 类型
    Path tempTemplatePath = Files.createTempFile("backup_", ".sql");
    try (InputStream in = file.getInputStream()) {
        Files.copy(in, tempTemplatePath, StandardCopyOption.REPLACE_EXISTING);
        boolean importSuccess = databaseService.importDatabaseFromUI(tempTemplatePath);
        // ...
    }
}
```
- **修复建议**:
```java
String fileName = file.getOriginalFilename();
if (fileName == null || !fileName.toLowerCase().endsWith(".sql")) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(Map.of("error", "invalidFileType", 
                    "message", "Only .sql files are allowed"));
}
```

### 问题 14
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 336-351
- **严重度**: LOW
- **类型**: Session
- **描述**: Remember-me 令牌有效期过长。Remember-me 功能配置的令牌有效期为 14 天（`14 * 24 * 60 * 60` 秒），虽然对于某些应用场景是可接受的，但较长的有效期增加了令牌被盗用的风险窗口。
- **代码片段**:
```java
http.rememberMe(rememberMeConfigurer ->
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
  1. 考虑将有效期缩短至 7 天或更短
  2. 实现令牌撤销机制
  3. 在敏感操作时要求重新认证
  4. 提供用户界面查看和撤销活跃的 remember-me 令牌

### 问题 15
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java`
- **行号**: 60-67
- **严重度**: LOW
- **类型**: Session
- **描述**: 桌面客户端令牌有效期过长。桌面客户端（Tauri/Electron）默认令牌有效期为 30 天（`DEFAULT_DESKTOP_TOKEN_EXPIRY_MINUTES`），基于 User-Agent 字符串检测桌面客户端。User-Agent 可被伪造，攻击者可伪装为桌面客户端获取更长的令牌有效期。
- **代码片段**:
```java
public static boolean isDesktopClient(HttpServletRequest request) {
    String userAgent = request.getHeader("User-Agent");
    if (userAgent == null) {
        return false;
    }
    String userAgentLower = userAgent.toLowerCase();
    boolean hasTauri = userAgentLower.contains("tauri");
    boolean hasStirling = userAgentLower.contains("stirlingpdf-desktop");
    boolean hasElectron = userAgentLower.contains("electron");
    boolean isDesktop = hasTauri || hasStirling || hasElectron;
    return isDesktop;
}

public static int getDesktopTokenExpiryMinutes(
        ApplicationProperties applicationProperties) {
    int configuredMinutes = applicationProperties.getSecurity()
            .getJwt().getDesktopTokenExpiryMinutes();
    return configuredMinutes > 0 ? configuredMinutes 
            : JwtConstants.DEFAULT_DESKTOP_TOKEN_EXPIRY_MINUTES; // 30 天
}
```
- **修复建议**:
  1. 不依赖 User-Agent 进行安全决策
  2. 考虑使用更可靠的客户端标识机制（如客户端证书）
  3. 缩短桌面客户端令牌有效期，或实现令牌刷新机制

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 4 |
| HIGH | 5 |
| MEDIUM | 4 |
| LOW | 2 |
| **总计** | **15** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| SQLi | 0 |
| XSS | 3 |
| XXE | 1 |
| PathTraversal | 2 |
| CommandInjection | 0 |
| SSRF | 1 |
| FileUpload | 2 |
| HardcodedSecret | 2 |
| CSRF | 1 |
| CORS | 1 |
| Auth | 0 |
| Session | 2 |

---

## 正面发现

1. **SQL 注入防护良好**: `DatabaseService` 使用 `PreparedStatement` 和参数化查询，并实现了 SQL 内容验证（白名单/黑名单机制），有效防止 SQL 注入攻击。

2. **命令注入防护完善**: `ProcessExecutor` 使用列表参数构建命令（`List<String>`），而非字符串拼接，并对命令参数进行验证（检查空字节、换行符、路径穿越），有效防止命令注入。`ConvertWebsiteToPDF`、`CompressController`、`ExtractImageScansController`、`PDFToFile` 等控制器均通过 `ProcessExecutor` 执行外部命令，所有用户输入均作为列表元素传递，未使用 `shell=True`。

3. **XXE 防护到位**: `SvgSanitizer` 和 `OfficeDocumentSanitizer` 在 XML 解析时正确配置了全面的 XXE 防护，包括禁用外部实体、外部参数实体、外部 DTD 加载，以及禁用 XInclude 和实体引用展开。`TransformerFactory` 也配置了 `FEATURE_SECURE_PROCESSING`。

4. **凭证加密实现良好**: `CredentialEncryption` 使用 AES-256-GCM 加密存储的凭证，密钥管理支持环境变量和配置文件，并为密钥文件设置了严格的文件权限（0600 owner-only）。

5. **路径穿越检查（部分）**: `DatabaseService.getBackupFilePath()` 正确实现了路径穿越检查，使用 `normalize()` 和 `startsWith()` 验证路径。`PipelineProcessor.generateInputFiles()` 也对文件名进行了路径穿越检查。

6. **SSRF 防护（部分）**: `ConvertWebsiteToPDF` 检查了 HTML 内容中的 `file:` 协议引用（包括 HTML 实体编码和百分号编码的变体），防止通过 HTML 内容访问本地文件。`fetchRemoteHtml()` 使用 `Redirect.NEVER` 禁止重定向跟随。

7. **临时文件管理**: 多处代码使用 `TempFile` 和 `TempFileManager` 进行临时文件管理，配合 try-with-resources 确保文件在使用后正确清理。

8. **访问控制**: `DatabaseController` 使用 `@PreAuthorize("hasRole('ADMIN')")` 限制管理功能仅对管理员开放。`SecurityConfiguration` 配置了完整的认证和授权机制，支持表单登录、OAuth2、SAML2 多种认证方式。

9. **SVG 外部资源加载防护**: `SvgOverlayUtil` 通过自定义 `UserAgent` 的 `checkLoadExternalResource` 方法阻止 SVG 加载外部资源（仅允许 `data:` URI），有效防止 SVG 中的 SSRF 攻击。

10. **Office 文档净化**: `OfficeDocumentSanitizer` 对 OOXML 和 ODF 文档进行深度净化，剥离外部关系引用和 href 属性，防止 LibreOffice 等处理工具被利用发起 SSRF 攻击。使用 `ZipSecurity.createHardenedInputStream` 防止 Zip 炸弹。

---

## 关键风险总结

1. **CRITICAL - 默认管理员凭据硬编码** (`InitialSecuritySetup.java`): 系统使用硬编码的默认管理员凭据（admin/stirling），攻击者可直接使用此凭据获取系统完全控制权。这是最严重的安全问题，必须立即修复。

2. **CRITICAL - CSRF 保护完全禁用 + CORS 配置不当** (`SecurityConfiguration.java`): CSRF 保护被完全禁用，且默认 CORS 配置允许任意源携带凭证（`allowedOriginPatterns=*` + `allowCredentials=true`）。这两个问题结合使得跨站请求伪造攻击成为可能，攻击者可诱导已认证用户执行任意操作。

3. **CRITICAL - 路径穿越漏洞** (`FileOrUploadService.java`): `resolveFilePath()` 直接将用户输入拼接到路径中，无任何路径规范化或前缀验证，攻击者可访问服务器上的任意文件。

4. **HIGH - SSRF 漏洞** (`ConvertWebsiteToPDF.java`): `fetchRemoteHtml()` 接受用户指定的 URL 并发起 HTTP 请求，但未验证目标 IP 地址。攻击者可访问内部网络资源，包括云环境元数据服务（169.254.169.254）。

5. **HIGH - HTML/SVG/Office 文档净化可被配置禁用** (`CustomHtmlSanitizer.java`, `SvgSanitizer.java`, `OfficeDocumentSanitizer.java`): `disableSanitize` 配置项允许完全禁用所有输入净化功能，可能导致 XSS 攻击。此配置选项在生产环境中极其危险。

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Alpha
