# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269
- **严重度**: CRITICAL
- **类型**: CSRF
- **描述**: CSRF 保护被全局禁用 (`http.csrf(CsrfConfigurer::disable)`)，同时应用配置了 form login（第 373-388 行）和 remember-me（第 337-351 行），两者均基于 Cookie 认证。根据组合漏洞规则，CSRF 禁用 + formLogin/rememberMe = CRITICAL。攻击者可构造恶意页面，以已认证用户身份执行任意 state-changing 操作（如上传文件、删除数据库备份、修改配置等）。
- **代码片段**:
```java
// 第 269 行 - CSRF 全局禁用
http.csrf(CsrfConfigurer::disable);

// 第 337-351 行 - remember-me 基于 Cookie 认证
http.rememberMe(
    rememberMeConfigurer ->
        rememberMeConfigurer
            .tokenRepository(persistentTokenRepository())
            .tokenValiditySeconds(14 * 24 * 60 * 60) // 14 天
            .userDetailsService(userDetailsService)
            .useSecureCookie(true)
            .rememberMeParameter("remember-me")
            .rememberMeCookieName("remember-me")
            .alwaysRemember(false));

// 第 373-388 行 - form login
http.formLogin(
    formLogin ->
        formLogin
            .loginPage("/login")
            .loginProcessingUrl("/perform_login")
            .successHandler(...)
            .failureHandler(...)
            .permitAll());
```
- **修复建议**: 启用 CSRF 保护，至少对非 API 端点启用。如果 API 端点使用 JWT 无状态认证可豁免 CSRF，则应仅对 `/api/**` 路径禁用 CSRF，而非全局禁用。对于 form login 和 remember-me 端点，必须启用 CSRF Token 验证。

---

### 问题 2
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218
- **严重度**: CRITICAL
- **类型**: CORS
- **描述**: CORS 配置默认允许所有来源 (`allowedOriginPatterns = "*"`)，且 `allowCredentials = true`。结合问题 1 中 CSRF 全局禁用和 form login/remember-me Cookie 认证，满足组合漏洞规则 1（CSRF 禁用 + CORS `*` + `allowCredentials=true` + formLogin/rememberMe = CRITICAL）。攻击者可从任意恶意网站以已认证用户身份发起跨域请求，执行任意操作。
- **代码片段**:
```java
// 第 188 行 - 默认允许所有来源
cfg.setAllowedOriginPatterns(List.of("*"));

// 第 218 行 - 允许携带凭据
cfg.setAllowCredentials(true);
```
- **修复建议**: 在 `settings.yml` 中配置明确的 `system.corsAllowedOrigins` 白名单，移除默认的 `*` 通配符。当未配置时不应默认允许所有来源，而应拒绝所有跨域请求或仅允许同源。

---

### 问题 3
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`
- **行号**: 154-155
- **严重度**: CRITICAL
- **类型**: HardcodedSecret
- **描述**: 默认管理员账户使用硬编码的用户名 `admin` 和密码 `stirling`。在应用首次启动且未配置初始凭据时，会自动创建此管理员账户。如果部署者未修改默认密码，攻击者可直接使用 `admin:stirling` 登录获取管理员权限，完全控制应用。
- **代码片段**:
```java
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
    }
}
```
- **修复建议**: 移除硬编码默认密码。首次启动时应强制用户设置管理员密码，或生成随机密码并输出到安全位置（如控制台一次性显示）。至少应在日志中输出醒目警告，提示用户立即修改默认密码。

---

### 问题 4
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 116-144, 175-201
- **严重度**: HIGH
- **类型**: SSRF
- **描述**: URL 转 PDF 功能存在 SSRF 漏洞。虽然初始 URL 验证确保为 HTTP/HTTPS 协议，且 `fetchRemoteHtml()` 禁用了重定向跟随，但获取的 HTML 内容会被传递给 WeasyPrint 进行渲染。WeasyPrint 在渲染过程中会主动获取 HTML 中引用的所有外部资源（CSS、图片、字体等），这些资源请求不受任何 SSRF 防护限制。攻击者可在 HTML 中嵌入指向内网 IP（如 `169.254.169.254` 云元数据服务、`10.0.0.0/8`、`192.168.0.0/16`）的资源引用，实现内网探测和敏感信息获取。代码仅检查了 `file:` 协议引用，未对 HTTP 资源 URL 的目标 IP 进行验证。
- **代码片段**:
```java
// 第 116 行 - 获取远程 HTML
String htmlContent = fetchRemoteHtml(URL);

// 第 118 行 - 仅检查 file: 协议
if (containsDisallowedUriScheme(htmlContent)) {
    // 拒绝...
}

// 第 135-144 行 - WeasyPrint 渲染时会获取 HTML 中所有外部资源
List<String> command = new ArrayList<>();
command.add(runtimePathConfig.getWeasyPrintPath());
command.add(tempHtmlInput.toString());
command.add("--base-url");
command.add(URL);  // 用户控制的 base URL
command.add("--pdf-forms");
command.add(tempOutputFile.toString());

ProcessExecutor.getInstance(ProcessExecutor.Processes.WEASYPRINT)
        .runCommandWithOutputHandling(command);
```
- **修复建议**: 1) 在 WeasyPrint 渲染前，解析 HTML 中所有外部资源 URL 并验证目标 IP 不属于内网地址段；2) 考虑使用网络命名空间或防火墙规则限制 WeasyPrint 进程的网络访问；3) 禁止 `--base-url` 指向内网地址。

---

### 问题 5
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 64-66
- **严重度**: HIGH
- **类型**: XSS
- **描述**: HTML 净化器可通过 `applicationProperties.getSystem().isDisableSanitize()` 配置项完全禁用。当该配置为 `true` 时，`sanitize()` 方法直接返回原始 HTML，不做任何净化处理。如果此配置可被普通用户修改（如通过管理界面），攻击者可关闭净化后注入恶意脚本。即使仅管理员可配置，禁用净化也会导致所有 HTML 输出暴露于 XSS 攻击。
- **代码片段**:
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```
- **修复建议**: 移除 `disableSanitize` 全局开关，或将其限制为仅管理员可通过安全配置修改，并在修改时输出安全警告。建议对所有 HTML 输入强制执行净化，不提供完全禁用的选项。

---

### 问题 6
- **文件**: `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java`
- **行号**: 59-61
- **严重度**: HIGH
- **类型**: XSS
- **描述**: SVG 净化器同样可通过 `disableSanitize` 配置完全禁用。当禁用时，用户提交的 SVG 内容不经过任何安全检查，可直接包含 `<script>`、`<foreignObject>`、事件处理器等恶意内容，导致存储型或反射型 XSS 攻击。
- **代码片段**:
```java
public byte[] sanitize(byte[] svgBytes) throws IOException {
    if (applicationProperties.getSystem().isDisableSanitize()) {
        log.debug("SVG sanitization disabled by configuration");
        return svgBytes;  // 直接返回未净化的 SVG
    }
    // ... 净化逻辑
}
```
- **修复建议**: 同问题 5，SVG 净化不应被完全禁用。建议移除此配置开关，或确保即使配置禁用，仍执行基础安全检查（如移除 `<script>` 标签和事件处理器）。

---

### 问题 7
- **文件**: `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java`
- **行号**: 80-83
- **严重度**: HIGH
- **类型**: XSS
- **描述**: Office 文档净化器可通过 `disableSanitize` 配置完全禁用。当禁用时，用户上传的 OOXML/ODF 文档中的外部关系引用和 href 不会被清理，可能导致 LibreOffice 处理时发起 SSRF 请求或执行其他恶意操作。
- **代码片段**:
```java
public byte[] sanitize(byte[] documentBytes, String extension) throws IOException {
    if (applicationProperties.getSystem().isDisableSanitize()) {
        log.debug("Office document sanitization disabled by configuration");
        return documentBytes;  // 直接返回未净化的文档
    }
    // ... 净化逻辑
}
```
- **修复建议**: 同问题 5/6，Office 文档净化不应被完全禁用。建议至少保留对外部关系引用的清理。

---

### 问题 8
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath()` 方法直接将用户提供的 `fileId` 参数传递给 `Path.resolve()` 进行路径拼接，未进行任何路径穿越检查（如检查 `..`、进行 `normalize()` 或验证 `startsWith()` 前缀）。攻击者可通过传入 `../../etc/passwd` 等值访问任意系统文件。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);  // 无任何路径验证
}
```
- **修复建议**: 添加路径规范化 (`normalize()`) 和前缀验证 (`startsWith(baseDir)`)：
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

---

### 问题 9
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 35-41
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `SAXSVGDocumentFactory` 创建 XML 文档时未显式禁用外部实体（XXE）。虽然 Apache Batik 的渲染层通过自定义 `UserAgent` 限制了外部资源加载（第 43-56 行），但 XML 解析阶段（`factory.createSVGDocument()`）本身未配置 XXE 防护。如果上游 SVG 净化被禁用或绕过，攻击者可通过构造恶意 SVG 进行 XXE 攻击。与 `SvgSanitizer` 和 `OfficeDocumentSanitizer` 中的全面 XXE 防护形成对比，此处存在防御缺口。
- **代码片段**:
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);
// 未配置 XXE 防护
SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```
- **修复建议**: 在创建 `SAXSVGDocumentFactory` 后，配置底层 XMLReader 禁用外部实体：
```java
factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

---

### 问题 10
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`、`SvgSanitizer.java`、`OfficeDocumentSanitizer.java`
- **行号**: CustomHtmlSanitizer:65, SvgSanitizer:59, OfficeDocumentSanitizer:80
- **严重度**: MEDIUM
- **类型**: XSS
- **描述**: 三个净化器均依赖同一个 `disableSanitize` 全局配置开关。这意味着存在一个单一故障点：一旦该配置被设为 `true`，所有 HTML、SVG 和 Office 文档的净化保护将同时失效。这违反了纵深防御原则。根据 V3 判定规则，净化可被配置禁用但仅管理员可配置时为 MEDIUM。
- **修复建议**: 为每种文件类型设置独立的净化开关，而非全局单一开关。增加审计日志记录净化被禁用的事件。

---

### 问题 11
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/service/DatabaseService.java`
- **行号**: 489-514
- **严重度**: MEDIUM
- **类型**: SQLi
- **描述**: `executeDatabaseScript()` 方法通过 H2 数据库的 `RUNSCRIPT FROM ?` 执行用户上传的 SQL 文件。虽然有 `validateSqlContent()` 方法进行 SQL 内容验证（使用白名单和黑名单模式），但黑名单方式 inherently 无法覆盖所有危险函数。此外，`sanitizeSql()` 方法的注释 `// TODO: I feel like this should re-evaluated` 表明开发者自身对 SQL 净化逻辑的安全性存在疑虑。验证后还通过内存数据库进行备份验证（`verifyBackup`），提供了一定的纵深防御。
- **代码片段**:
```java
private void executeDatabaseScript(Path scriptPath) {
    validateSqlContent(scriptPath);  // SQL 内容验证
    if (!verifyBackup(scriptPath)) {  // 备份验证
        throw new IllegalArgumentException("Backup verification failed");
    }
    String query = "RUNSCRIPT from ?;";
    try (Connection conn = dataSource.getConnection();
         PreparedStatement stmt = conn.prepareStatement(query)) {
        stmt.setString(1, scriptPath.toString());
        stmt.execute();  // 执行用户上传的 SQL
    }
}
```
- **修复建议**: 1) 考虑使用 H2 的 `RUNSCRIPT` 内置安全模式或限制执行权限；2) 将黑名单方式改为更严格的白名单方式，仅允许已知安全的 SQL 语句结构；3) 在内存数据库验证阶段检测实际执行的副作用。

---

### 问题 12
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/ExtractImageScansController.java`
- **行号**: 150-171
- **严重度**: MEDIUM
- **类型**: CommandInjection
- **描述**: Python 脚本调用中，用户请求参数（`angleThreshold`、`tolerance`、`minArea`、`minContourArea`、`borderSize`）通过 `String.valueOf()` 转换为字符串后作为命令行参数传递。虽然这些参数在请求模型中通常定义为数值类型，但如果类型验证不充分，攻击者可注入包含空格或特殊字符的参数值，导致参数注入。ProcessExecutor 的 `validateCommand()` 方法检查了 null 字节和换行符，但未检查空格和其他 shell 特殊字符。
- **代码片段**:
```java
List<String> command = new ArrayList<>(Arrays.asList(
    pythonVersion,
    splitPhotosScript.toAbsolutePath().toString(),
    images.get(i),
    tempDir.toString(),
    "--angle_threshold",
    String.valueOf(request.getAngleThreshold()),  // 用户输入
    "--tolerance",
    String.valueOf(request.getTolerance()),        // 用户输入
    "--min_area",
    String.valueOf(request.getMinArea()),          // 用户输入
    "--min_contour_area",
    String.valueOf(request.getMinContourArea()),   // 用户输入
    "--border_size",
    String.valueOf(request.getBorderSize())));     // 用户输入
```
- **修复建议**: 在传递参数前显式验证所有数值参数为合法数字（如使用 `Double.parseDouble()` 验证），拒绝非数值输入。

---

### 问题 13
- **文件**: `app/common/src/main/java/stirling/software/common/util/PDFToFile.java`
- **行号**: 96-109, 198-205
- **严重度**: MEDIUM
- **类型**: CommandInjection
- **描述**: `pdftohtml` 命令调用中，`pdfBaseName` 来源于用户上传文件的原始文件名（经 `Filenames.toSimpleFileName()` 处理后）。虽然 `Filenames.toSimpleFileName()` 会剥离路径组件，但文件名中的特殊字符（如以 `-` 开头的文件名）可能被解释为命令行选项，导致参数注入。同样的模式在 `processPdfToHtml()` 和 `processPdfToOfficeFormat()` 中重复出现。
- **代码片段**:
```java
String originalPdfFileName = Filenames.toSimpleFileName(inputFile.getOriginalFilename());
String pdfBaseName = originalPdfFileName;
if (originalPdfFileName.contains(".")) {
    pdfBaseName = originalPdfFileName.substring(0, originalPdfFileName.lastIndexOf('.'));
}

List<String> command = new ArrayList<>(Arrays.asList(
    "pdftohtml", "-s", "-noframes", "-c",
    tempInputFile.getAbsolutePath(),
    pdfBaseName));  // 用户控制的文件名作为命令参数
```
- **修复建议**: 对 `pdfBaseName` 进行额外验证，确保其不以 `-` 开头，或仅包含字母数字和安全字符。可使用 `--` 分隔符防止参数注入。

---

### 问题 14
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java`
- **行号**: 106-109
- **严重度**: MEDIUM
- **类型**: PathTraversal
- **描述**: PDF 文件名和印章图片文件名的路径穿越检查不完整。仅检查了 `..` 和以 `/` 开头，但未检查反斜杠 `\`。在 Windows 系统上，`..` 可能被编码为其他形式，或使用 `\` 作为路径分隔符进行路径穿越。不过，这些文件名在代码中仅用于显示目的（印章文本替换、日志记录），不直接用于文件系统操作，降低了实际风险。
- **代码片段**:
```java
String pdfFileName = pdfFile.getOriginalFilename();
if (pdfFileName.contains("..") || pdfFileName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(
            "error.invalid.filepath", "Invalid PDF file path: " + pdfFileName);
}
// 未检查反斜杠 \
```
- **修复建议**: 添加反斜杠检查：`pdfFileName.contains("\\")`。或使用 `Filenames.toSimpleFileName()` 进行统一文件名净化。

---

### 问题 15
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 476-479
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: IP 速率限制过滤器的限制值设置为 1,000,000（一百万）次请求，注释标注为 `TODO`。此限制值实质上等于无速率限制，无法有效防御暴力破解、DDoS 或自动化攻击。代码注释也表明此功能因 Spring Security async dispatch bug 已被注释禁用。
- **代码片段**:
```java
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    // Example limit TODO add config level
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
```
- **修复建议**: 配置合理的速率限制值（如每分钟 60-120 次请求），并通过配置文件支持动态调整。修复 Spring Security async dispatch 问题后重新启用此过滤器。

---

### 问题 16
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/controller/api/DatabaseController.java`
- **行号**: 144
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: `deleteFile()` 端点使用 HTTP GET 方法执行删除操作（state-changing 操作）。结合 CSRF 全局禁用（问题 1），攻击者可通过构造简单的图片标签 `<img src="https://target/api/database/delete/backup_xxx.sql">` 诱导已认证管理员删除数据库备份。GET 请求无需 CSRF token，使得攻击更加简单。
- **代码片段**:
```java
@Hidden
@Operation(summary = "Delete a database backup file")
@GetMapping("/delete/{fileName}")  // GET 方法执行删除操作
public ResponseEntity<?> deleteFile(@PathVariable String fileName) {
    // ...
    databaseService.deleteBackupFile(fileName);
    // ...
}
```
- **修复建议**: 将删除操作改为 HTTP DELETE 或 POST 方法，并在启用 CSRF 后确保此类 state-changing 操作受到 CSRF 保护。

---

### 问题 17
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 315-344, 742-748
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: 使用 MD5 哈希算法进行图片去重（`generateMD5()` 方法）。MD5 已被证明存在碰撞漏洞，不适合安全敏感场景。但在此上下文中，MD5 仅用于图片内容去重的哈希计算（非安全场景），不影响认证、加密或数据完整性验证。
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
- **修复建议**: 考虑使用 SHA-256 替代 MD5 进行哈希计算，以避免潜在的碰撞问题。但鉴于当前用途为非安全场景，优先级较低。

---

### 问题 18
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java`
- **行号**: 60-67
- **严重度**: LOW
- **类型**: Session
- **描述**: 桌面客户端（Tauri/Electron）的 JWT 令牌默认有效期为 30 天（43200 分钟）。虽然桌面客户端使用 OS 级加密密钥链存储令牌，但 30 天的有效期仍增加了令牌被盗用的风险窗口。User-Agent 检测基于客户端自报的字符串，理论上可被伪造。
- **代码片段**:
```java
public static int getDesktopTokenExpiryMinutes(ApplicationProperties applicationProperties) {
    int configuredMinutes =
            applicationProperties.getSecurity().getJwt().getDesktopTokenExpiryMinutes();
    return configuredMinutes > 0
            ? configuredMinutes
            : JwtConstants.DEFAULT_DESKTOP_TOKEN_EXPIRY_MINUTES; // 30 天
}
```
- **修复建议**: 考虑缩短默认令牌有效期（如 7 天），并配合 refresh token 机制实现无感续期。对桌面客户端身份验证增加更多检测维度。

---

### 问题 19
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/pipeline/PipelineProcessor.java`
- **行号**: 346-349
- **严重度**: LOW
- **类型**: PathTraversal
- **描述**: `generateInputFiles(File[])` 方法中的路径穿越检查使用 `Path.of(file.getName()).normalize()` 后检查是否以 `..` 开头。此检查仅对文件名（非完整路径）进行规范化，如果文件名本身为 `..`，检查会生效，但对更复杂的路径穿越模式（如 `foo/../../etc/passwd`）可能不完整。不过，此方法处理的是内部生成的文件数组，非直接用户输入，实际风险较低。
- **代码片段**:
```java
Path normalizedPath = Path.of(file.getName()).normalize();
if (normalizedPath.startsWith("..")) {
    throw new SecurityException(
            "Potential path traversal attempt in file name: " + file.getName());
}
```
- **修复建议**: 使用更完整的路径验证方案，如验证规范化后的完整路径是否在预期目录内。

---

### 问题 20
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 337-351
- **严重度**: LOW
- **类型**: Session
- **描述**: Remember-me 令牌有效期设置为 14 天（`14 * 24 * 60 * 60 = 1209600` 秒）。根据 V3 标准，14 天在可接受范围内，但偏长。结合 CSRF 禁用（问题 1），14 天内的 remember-me Cookie 可被 CSRF 攻击利用。
- **代码片段**:
```java
http.rememberMe(
    rememberMeConfigurer ->
        rememberMeConfigurer
            .tokenRepository(persistentTokenRepository())
            .tokenValiditySeconds(14 * 24 * 60 * 60) // 14 天
            .userDetailsService(userDetailsService)
            .useSecureCookie(true)
            .rememberMeParameter("remember-me")
            .rememberMeCookieName("remember-me")
            .alwaysRemember(false));
```
- **修复建议**: 考虑缩短 remember-me 有效期至 7 天，并在启用 CSRF 后此风险会显著降低。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 3 |
| HIGH | 5 |
| MEDIUM | 8 |
| LOW | 4 |
| **总计** | **20** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| SQLi | 1 |
| XSS | 4 |
| XXE | 1 |
| PathTraversal | 3 |
| CommandInjection | 2 |
| SSRF | 1 |
| FileUpload | 0 |
| HardcodedSecret | 2 |
| CSRF | 1 |
| CORS | 1 |
| Auth | 2 |
| Session | 2 |

---

## 正面发现

1. **全面的 XXE 防护**：`SvgSanitizer.parseSecurely()` 和 `OfficeDocumentSanitizer.parseSecurely()` 方法均配置了完整的 XXE 防护措施，禁用了外部实体、外部参数实体、外部 DTD 加载和 XInclude，是良好的安全实践。

2. **ProcessExecutor 的命令验证**：`ProcessExecutor.validateCommand()` 方法对命令参数进行了多层验证，包括 null 字节检查、换行符检查、路径穿越检查和可执行文件存在性验证，提供了良好的命令注入防护。

3. **SQL 内容验证**：`DatabaseService.validateSqlContent()` 方法使用白名单+黑名单双重策略验证上传的 SQL 文件内容，并在执行前通过内存数据库进行备份验证，体现了纵深防御思想。

4. **AES-256-GCM 加密**：`CredentialEncryption` 使用 AES-256-GCM 算法加密存储的凭据，密钥管理支持环境变量、配置属性和自动生成密钥文件，且密钥文件设置了 0600 权限（仅所有者可读写），是良好的密钥管理实践。

5. **SVG 净化器**：`SvgSanitizer` 实现了全面的 SVG 安全净化，包括移除危险元素（`<script>`、`<foreignObject>`、`<iframe>` 等）、事件处理器属性、JavaScript URL 和 data URL，并结合 SSRF 保护服务验证外部 URL。

6. **文件路径验证**：`DatabaseService.getBackupFilePath()` 正确实现了路径穿越防护（`normalize()` + `startsWith()` 验证），`DatabaseService.isValidFileName()` 对文件名进行了全面的非法字符检查。

7. **数据库备份文件验证**：`DatabaseController.downloadFile()` 验证文件名必须以 `backup_` 开头且以 `.sql` 结尾，限制了下载范围。

8. **URL 格式验证**：`ConvertWebsiteToPDF` 对 `file:` 协议进行了多层编码检测（HTML 实体解码、百分号解码、大小写归一化），防止编码绕过。

9. **临时文件管理**：项目广泛使用 `TempFile` 和 `TempFileManager` 进行临时文件的自动清理，使用 `try-with-resources` 确保资源释放，减少了信息泄露风险。

10. **密码加密存储**：`InitialSecuritySetup` 中的管理员密码通过 `userService.saveUserCore()` 存储，结合 `PasswordEncoder`（在 `SecurityConfiguration` 中注入），密码应经过哈希处理后存储。

---

## 关键风险总结

1. **[CRITICAL] CSRF + CORS + Cookie 认证组合漏洞**：CSRF 全局禁用 + CORS 默认允许所有来源并携带凭据 + form login/remember-me 基于 Cookie 认证，构成了完整的攻击链。攻击者可从任意恶意网站以已认证用户身份执行任意操作。这是最严重的安全风险，需要立即修复。

2. **[CRITICAL] 硬编码默认管理员凭据**：默认管理员账户 `admin:stirling` 硬编码在源代码中。如果部署者未修改默认密码，任何人都可以获取管理员权限。结合 CSRF 漏洞，攻击面进一步扩大。

3. **[HIGH] SSRF 通过 WeasyPrint 渲染**：URL 转 PDF 功能中，WeasyPrint 渲染引擎可获取 HTML 中引用的内网资源，不受任何 SSRF 防护限制。可被用于探测内网服务、获取云元数据（如 AWS/GCP/Azure 的实例凭据）。

4. **[HIGH] 全局净化禁用开关**：`disableSanitize` 配置项可同时禁用 HTML、SVG 和 Office 文档的净化保护，形成单一故障点。一旦禁用，所有用户输入将未经净化直接处理，导致 XSS 和注入攻击风险。

5. **[HIGH] 路径穿越漏洞**：`FileOrUploadService.resolveFilePath()` 方法直接拼接用户输入到路径中，无任何路径穿越检查，可能导致任意文件读取或写入。

---

## 评审检查清单

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用组合漏洞判定规则（CSRF + CORS + Cookie 认证 = CRITICAL）

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Epsilon
