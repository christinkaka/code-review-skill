# 代码评审报告

**评审日期**: 2026-08-12
**评审范围**: Stirling-PDF - 18 个文件
**评审维度**: 12 个（SQLi, XSS, XXE, PathTraversal, CommandInjection, SSRF, FileUpload, HardcodedSecret, CSRF, CORS, Auth, Session）

---

## 发现的问题

### 问题 1
- **文件**: `SecurityConfiguration.java`, `CustomHtmlSanitizer.java`, `SvgSanitizer.java`, `OfficeDocumentSanitizer.java`
- **行号**: SecurityConfiguration.java: 269, 188, 218, 337-351, 373; CustomHtmlSanitizer.java: 64-66; SvgSanitizer.java: 59-61; OfficeDocumentSanitizer.java: 80-83
- **严重度**: CRITICAL
- **类型**: CSRF + CORS + Cookie 认证（组合漏洞）
- **描述**: 根据组合漏洞规则，以下多个漏洞形成完整的攻击链，合并为 1 个 CRITICAL 组合漏洞：

  1. **CSRF 完全禁用**: `http.csrf(CsrfConfigurer::disable)`（第 269 行）对所有 SecurityFilterChain 全局禁用了 CSRF 保护。
  2. **CORS 允许所有来源**: 当 `system.corsAllowedOrigins` 未配置时（默认情况），`cfg.setAllowedOriginPatterns(List.of("*"))`（第 188 行）允许任意来源发起跨域请求。
  3. **CORS 允许携带凭证**: `cfg.setAllowCredentials(true)`（第 218 行）允许跨域请求携带 Cookie。
  4. **基于 Cookie 的认证**: 配置了 `formLogin()`（第 373 行）和 `rememberMe()`（第 337-351 行），均依赖 Cookie 进行身份认证。remember-me Cookie 有效期为 14 天。

  **攻击场景**: 攻击者在恶意网站 `evil.com` 上构造一个页面，该页面通过 JavaScript 向 Stirling-PDF 实例发起跨域 POST 请求（如上传文件、修改配置、导入数据库等）。由于 CORS 允许 `*` 来源且 `allowCredentials=true`，浏览器会自动附带用户的认证 Cookie（JSESSIONID / remember-me）。由于 CSRF 保护被完全禁用，请求将被成功处理。攻击者可以以受害者身份执行任意操作，包括上传恶意文件、导入数据库备份、删除文件等。

  **影响范围**: 所有通过 Cookie 认证的用户（包括 remember-me 自动登录的用户）。攻击无需用户交互（用户只需访问恶意页面即可被利用），可导致未授权操作执行。

- **代码片段**:
```java
// SecurityConfiguration.java - CSRF 禁用（第 269 行）
http.csrf(CsrfConfigurer::disable);

// SecurityConfiguration.java - CORS 默认允许所有来源（第 186-191 行）
} else {
    cfg.setAllowedOriginPatterns(List.of("*"));
    log.info("No CORS allowed origins configured in settings.yml"
            + " (system.corsAllowedOrigins); allowing all origins.");
}

// SecurityConfiguration.java - CORS 允许凭证（第 218 行）
cfg.setAllowCredentials(true);

// SecurityConfiguration.java - formLogin 基于 Cookie 认证（第 373-388 行）
http.formLogin(
        formLogin ->
                formLogin.loginPage("/login")
                        .loginProcessingUrl("/perform_login")
                        ...);

// SecurityConfiguration.java - rememberMe 基于 Cookie 认证（第 337-351 行）
http.rememberMe(rememberMeConfigurer ->
        rememberMeConfigurer
                .tokenRepository(persistentTokenRepository())
                .tokenValiditySeconds(14 * 24 * 60 * 60) // 14 天
                .userDetailsService(userDetailsService)
                .useSecureCookie(true)
                .rememberMeParameter("remember-me")
                .rememberMeCookieName("remember-me")
                .alwaysRemember(false));

// CustomHtmlSanitizer.java - 净化可被配置禁用（第 64-66 行）
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java - 净化可被配置禁用（第 59-61 行）
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java - 净化可被配置禁用（第 80-83 行）
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**:
  1. 启用 CSRF 保护：移除 `http.csrf(CsrfConfigurer::disable)`，使用 Spring Security 默认的 CSRF Token 机制。对于 API 端点，可考虑仅对 Cookie 认证的请求启用 CSRF 校验。
  2. 配置明确的 CORS 来源：将 `system.corsAllowedOrigins` 配置为具体的受信域名列表，避免使用 `*` 通配符。
  3. 如果必须使用 `allowCredentials=true`，则 `allowedOrigins` 绝不能为 `*`，必须使用 `setAllowedOrigins()` 指定具体来源。
  4. 移除 `disableSanitize` 配置项，或将其限制为仅在开发环境中可用，生产环境禁止禁用净化。

---

### 问题 2
- **文件**: `InitialSecuritySetup.java`
- **行号**: 153-168
- **严重度**: CRITICAL
- **类型**: HardcodedSecret
- **描述**: 当系统未配置初始管理员凭据（`security.initialLogin.username/password`）且数据库中无用户时，`createDefaultAdminUser()` 方法使用硬编码的用户名 `"admin"` 和密码 `"stirling"` 创建管理员账户。该账户具有 `ADMIN` 角色，拥有系统最高权限。虽然设置了 `firstLogin=true` 标记（可能触发首次登录修改密码），但如果管理员未登录或部署后未立即修改密码，任何人都可使用此默认凭据获取管理员权限。

  **攻击场景**: 攻击者在部署了 Stirling-PDF 的服务器上尝试使用 `admin`/`stirling` 登录。如果管理员未修改默认密码（或尚未首次登录），攻击者将直接获得管理员权限，可执行所有管理操作，包括导入/导出数据库、管理用户、修改系统配置等。

  **影响范围**: 所有未在部署后立即修改默认管理员密码的实例。可导致完全的系统控制权限泄露。

- **代码片段**:
```java
// InitialSecuritySetup.java（第 153-168 行）
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
  1. 移除硬编码的默认管理员凭据。如果未配置初始凭据，应在启动时强制要求设置，或在首次访问 Web 界面时通过安装向导创建管理员账户。
  2. 如果必须保留默认凭据作为后备方案，应生成随机密码并输出到启动日志或配置文件中，而非使用固定的弱密码。
  3. 添加启动时警告日志，提醒管理员立即修改默认密码。

---

### 问题 3
- **文件**: `CustomHtmlSanitizer.java`, `SvgSanitizer.java`, `OfficeDocumentSanitizer.java`
- **行号**: CustomHtmlSanitizer.java: 64-66; SvgSanitizer.java: 59-61; OfficeDocumentSanitizer.java: 80-83
- **严重度**: HIGH
- **类型**: XSS
- **描述**: 根据问题合并规则 1（同一配置影响多个文件），`disableSanitize` 配置项（`applicationProperties.getSystem().isDisableSanitize()`）可同时禁用三类净化器：HTML 净化（CustomHtmlSanitizer）、SVG 净化（SvgSanitizer）和 Office 文档净化（OfficeDocumentSanitizer）。当此配置启用时，所有用户提交的 HTML、SVG 和 Office 文档内容将完全绕过净化处理，直接传递给下游处理组件。

  根据 V4 标准，即使仅管理员可配置，净化可被配置禁用仍为 HIGH（影响范围过大，一旦启用将完全暴露攻击面）。

  **攻击场景**: 当管理员启用 `disableSanitize` 后，攻击者可在上传的 SVG 文件中嵌入 `<script>alert(document.cookie)</script>` 等恶意代码。由于 SVG 净化被禁用，恶意脚本将被保留。当其他用户查看包含此 SVG 的 PDF 时，脚本可能在浏览器中执行，导致 XSS 攻击。类似地，HTML 内容中的恶意脚本也不会被过滤。

  **影响范围**: 所有上传和处理 HTML/SVG/Office 文档的用户。需要管理员先启用 `disableSanitize` 配置（特定条件），但一旦启用，所有用户均受影响。

- **代码片段**:
```java
// CustomHtmlSanitizer.java（第 64-66 行）
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}

// SvgSanitizer.java（第 59-61 行）
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}

// OfficeDocumentSanitizer.java（第 80-83 行）
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```
- **修复建议**:
  1. 移除 `disableSanitize` 配置项，净化应始终启用。
  2. 如果确实需要为性能或兼容性原因提供禁用选项，应将其限制为仅在开发/测试环境中可用（通过 Spring Profile 限制），生产环境禁止禁用。
  3. 在配置变更时记录审计日志，并在管理界面显示安全警告。

  注：此问题与问题 1 中引用的净化器代码有重叠，但问题 1 是 CSRF+CORS+Cookie 组合漏洞，此问题独立关注 XSS 净化禁用风险，两者类型不同，分别计数。

---

### 问题 4
- **文件**: `ConvertWebsiteToPDF.java`
- **行号**: 72-173, 175-201
- **严重度**: HIGH
- **类型**: SSRF
- **描述**: `urlToPdf()` 端点接受用户提供的 URL，首先通过 `fetchRemoteHtml()` 获取 HTML 内容，然后将 HTML 写入临时文件并通过 WeasyPrint 命令转换为 PDF。虽然初始 HTTP 请求禁用了重定向跟随（`HttpClient.Redirect.NEVER`），且仅检查了 `file:` scheme（`containsDisallowedUriScheme()`），但存在两个 SSRF 风险点：

  1. **WeasyPrint 资源加载**: WeasyPrint 在渲染 HTML 时会加载所有引用的外部资源（CSS、图片、字体等），这些请求不受初始 `fetchRemoteHtml()` 的安全控制。攻击者可构造 HTML 页面引用内部网络资源（如 `http://169.254.169.254/latest/meta-data/`），WeasyPrint 将获取这些资源并将其嵌入到生成的 PDF 中。
  2. **URL 验证不验证 IP**: `GeneralUtils.isValidURL()` 和 `RegexPatternUtils.getHttpUrlPattern()` 仅验证 URL 格式，不验证目标 IP 地址。攻击者可使用 `http://169.254.169.254/` 或 `http://10.0.0.1/` 等内网地址。`GeneralUtils.isURLReachable()` 同样不验证 IP。

  **攻击场景**: 攻击者向 `/api/v1/convert/url/pdf` 端点提交 URL `http://169.254.169.254/latest/meta-data/iam/security-credentials/`。服务器获取该 URL 的 HTML 内容（可能返回 AWS 元数据），然后通过 WeasyPrint 转换。如果元数据服务返回 HTML 格式的内容，攻击者可在生成的 PDF 中获取敏感的云凭证信息。另一种方式是攻击者托管一个包含 `<img src="http://169.254.169.254/...">` 的页面，WeasyPrint 在渲染时会获取该内部资源。

  **影响范围**: 可访问云元数据服务（169.254.169.254）和内网服务。根据 V4 标准，可访问云元数据服务至少为 HIGH。

- **代码片段**:
```java
// ConvertWebsiteToPDF.java（第 72-74 行）- 用户输入 URL
public ResponseEntity<?> urlToPdf(@ModelAttribute UrlToPdfRequest request)
        throws IOException, InterruptedException {
    String URL = request.getUrlInput();

    // ConvertWebsiteToPDF.java（第 88-91 行）- URL 验证仅检查格式，不验证 IP
    boolean patternValid =
            RegexPatternUtils.getInstance().getHttpUrlPattern().matcher(URL).matches();
    boolean generalValid = GeneralUtils.isValidURL(URL);
    if (!patternValid && !generalValid) { ... }

    // ConvertWebsiteToPDF.java（第 175-200 行）- 初始 HTTP 获取
    private String fetchRemoteHtml(String url) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NEVER) // 不跟随重定向
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(20)).GET()
                .header("User-Agent", "Stirling-PDF/URL-to-PDF")
                .build();
        // ... 无 IP 地址验证
    }

    // ConvertWebsiteToPDF.java（第 135-144 行）- WeasyPrint 处理，可加载外部资源
    List<String> command = new ArrayList<>();
    command.add(runtimePathConfig.getWeasyPrintPath());
    command.add(tempHtmlInput.toString());
    command.add("--base-url");
    command.add(URL);  // 用户控制的 base URL
    command.add("--pdf-forms");
    command.add(tempOutputFile.toString());
    ProcessExecutor.getInstance(ProcessExecutor.Processes.WEASYPRINT)
            .runCommandWithOutputHandling(command);

    // ConvertWebsiteToPDF.java（第 203-210 行）- 仅检查 file: scheme
    private boolean containsDisallowedUriScheme(String htmlContent) {
        // 仅检测 file: scheme，不检测 http://169.254.169.254 等内网 URL
        String normalized = normalizeForSchemeDetection(htmlContent);
        return FILE_SCHEME_PATTERN.matcher(normalized).find();
    }
```
- **修复建议**:
  1. 在 URL 验证阶段添加 IP 地址检查，拒绝内网 IP 段（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 127.0.0.0/8 等）。
  2. 使用 DNS 解析后验证 IP，防止 DNS rebinding 攻击。
  3. 为 WeasyPrint 配置网络隔离（如通过环境变量限制其网络访问），或使用代理拦截其外部资源请求。
  4. 考虑在 HTML 内容中移除或替换所有外部资源引用后再传递给 WeasyPrint。

---

### 问题 5
- **文件**: `FileOrUploadService.java`
- **行号**: 20-22
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath()` 方法直接将 `fileId` 参数通过 `Path.of(tempDirPath).resolve(fileId)` 解析为文件路径，未进行任何路径规范化（normalize）、前缀验证（startsWith）或危险字符检查。如果 `fileId` 包含路径穿越序列（如 `../../etc/passwd`），则返回的路径将超出 `tempDirPath` 目录范围。

  根据 V4 标准，路径直接用于 `FileInputStream` / `FileOutputStream` 至少为 HIGH。该方法作为公共工具方法，可被多个控制器调用，如果任何调用方将用户输入直接传递给 `fileId` 参数，即可导致任意文件读取或写入。

  **攻击场景**: 如果某个控制器调用 `resolveFilePath("../../etc/passwd")`，返回的路径将是 `<tempDirPath>/../../etc/passwd`，即 `/etc/passwd`。攻击者可通过此方法读取服务器上的任意文件。

  **影响范围**: 取决于该方法的调用方。作为公共服务方法，其风险在于为不安全的调用提供了便利。

- **代码片段**:
```java
// FileOrUploadService.java（第 20-22 行）
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
    // 无 normalize()、无 startsWith() 验证、无危险字符检查
}
```
- **修复建议**:
  1. 添加路径规范化和前缀验证：
  ```java
  public Path resolveFilePath(String fileId) {
      Path filePath = Path.of(tempDirPath).resolve(fileId).normalize();
      if (!filePath.startsWith(Path.of(tempDirPath).normalize())) {
          throw new SecurityException("Path traversal detected");
      }
      return filePath;
  }
  ```
  2. 验证 `fileId` 不包含 `..`、`/`、`\` 等危险字符。
  3. 考虑使用 UUID 作为 fileId，避免用户可控的路径片段。

---

### 问题 6
- **文件**: `SvgOverlayUtil.java`
- **行号**: 35-41
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `overlaySvgOnPage()` 方法使用 Batik 的 `SAXSVGDocumentFactory` 解析用户提供的 SVG 字节数据。与 `SvgSanitizer.parseSecurely()` 和 `OfficeDocumentSanitizer.parseSecurely()` 不同（两者均显式禁用了外部实体和 DTD），`SAXSVGDocumentFactory` 未显式配置 XXE 防护特性。

  虽然 Batik 的 `SAXSVGDocumentFactory` 在现代版本中可能默认禁用部分外部实体处理，且 `UserAgent` 的 `checkLoadExternalResource()` 方法阻止了渲染阶段的外部资源加载，但 XML 解析阶段的实体展开行为取决于底层 XML 解析器的默认配置，存在不确定性。

  **攻击场景**: 攻击者构造包含外部实体声明的 SVG 文件（如 `<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>`），如果底层 XML 解析器未默认禁用外部实体，实体值可能在解析时被展开并嵌入到 SVG 文档中。

  **影响范围**: 需要底层 XML 解析器未默认禁用外部实体（特定条件）。即使实体展开，`checkLoadExternalResource` 仍会阻止网络资源加载，但 `file:` scheme 的本地文件读取可能不受此限制。

- **代码片段**:
```java
// SvgOverlayUtil.java（第 35-41 行）
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
// 对比 SvgSanitizer.parseSecurely()（第 86-96 行）- 显式禁用所有外部实体
// DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
// factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
// factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
// factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
// factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```
- **修复建议**:
  1. 在创建 `SAXSVGDocumentFactory` 后，通过其底层 XMLReader 设置 XXE 防护特性：
  ```java
  SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);
  factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
  factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
  factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
  ```
  2. 或者在解析前使用 `SvgSanitizer.sanitize()` 对 SVG 进行净化处理。

---

### 问题 7
- **文件**: `SecurityConfiguration.java`
- **行号**: 476-479
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: `rateLimitingFilter()` Bean 配置的 IP 速率限制为每 IP 1,000,000 次请求（`maxRequestsPerIp = 1000000`），这在实际中相当于禁用了速率限制。代码注释（第 299-302 行）也确认了这一点：`IPRateLimitingFilter disabled (limit is 1M, no-op)`。同时，该过滤器在 `configureSecurity()` 方法中被注释掉（第 303-304 行），实际上未被添加到过滤器链中。

  虽然速率限制不属于 12 个标准评审维度之一，但作为认证授权（Auth）的补充安全控制，其缺失意味着系统对暴力破解、凭据填充和拒绝服务攻击缺乏防护。结合 CSRF 禁用和默认管理员凭据问题，系统面临更高的被入侵风险。

  **影响范围**: 所有暴露在网络中的端点，特别是登录端点 `/perform_login` 和 API 端点。

- **代码片段**:
```java
// SecurityConfiguration.java（第 476-479 行）
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    // Example limit TODO add config level
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}

// SecurityConfiguration.java（第 299-304 行）- 过滤器被注释掉
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op) and raw Filter
// impl causes Spring Security async dispatch bug...
// .addFilterBefore(rateLimitingFilter,
//         UsernamePasswordAuthenticationFilter.class)
```
- **修复建议**:
  1. 将速率限制配置化，通过 `applicationProperties` 读取合理的限制值（如每 IP 每分钟 60 次请求）。
  2. 修复 Spring Security 异步分发兼容性问题，将 `IPRateLimitingFilter` 转换为 `OncePerRequestFilter`。
  3. 对登录端点实施更严格的速率限制（如每 IP 每分钟 5 次登录尝试）。

---

### 问题 8
- **文件**: `CompressController.java`
- **行号**: 315-344, 401-427, 742-749
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: `CompressController` 中的 `ImageIdentity` 类使用 MD5 哈希算法进行图片去重标识（`generateImageHash()`、`generateMaskHash()`、`generateMetadataHash()` 等方法）。MD5 是一种已被证明不安全的哈希算法，存在已知的碰撞攻击。

  然而，在此场景中 MD5 仅用于图片内容去重（非安全场景），不用于密码存储、令牌生成或完整性校验等安全目的。攻击者虽然可以构造具有相同 MD5 哈希的不同图片来绕过去重逻辑，但这不会导致安全漏洞，仅影响压缩效率。

  根据 V4 标准，使用 MD5 用于去重（非安全场景）为 LOW。

- **代码片段**:
```java
// CompressController.java（第 742-749 行）
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
  1. 考虑使用 SHA-256 替代 MD5 进行图片去重哈希，以获得更好的碰撞抗性。
  2. 如果性能是关注点，当前 MD5 用于去重可以接受，但应在注释中明确标注其不应用于安全目的。

---

## 12 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查所有 SQL 操作。DatabaseService 使用 PreparedStatement 参数化查询，SQL 导入前有白名单/黑名单验证。 | 无问题 |
| 2. 跨站脚本 (XSS) | 已检查所有净化器。发现 disableSanitize 配置可禁用三类净化器。 | 问题 3 (HIGH) |
| 3. XML 外部实体 (XXE) | 已检查所有 XML 解析。SvgSanitizer 和 OfficeDocumentSanitizer 配置完善；SvgOverlayUtil 未显式禁用。 | 问题 6 (MEDIUM) |
| 4. 路径穿越 | 已检查所有文件路径操作。FileOrUploadService.resolveFilePath() 无任何验证；DatabaseService 有完整验证。 | 问题 5 (HIGH) |
| 5. 命令注入 | 已检查所有 ProcessBuilder/Runtime.exec 调用。ProcessExecutor 使用列表参数并验证 null 字节/换行符。 | 无问题 |
| 6. SSRF | 已检查所有 HTTP 请求。ConvertWebsiteToPDF 的 URL 验证不检查 IP 地址，WeasyPrint 可加载内网资源。 | 问题 4 (HIGH) |
| 7. 文件上传/下载 | 已检查所有文件上传接口。文件类型通过处理库隐式验证，DatabaseController 有 ADMIN 权限控制和 SQL 内容验证。 | 无问题 |
| 8. 硬编码密钥/密码 | 已检查所有凭据和密钥。InitialSecuritySetup 硬编码默认管理员密码；CompressController 使用 MD5（非安全场景）。 | 问题 2 (CRITICAL), 问题 8 (LOW) |
| 9. CSRF 保护 | 已检查 CSRF 配置。全局禁用 CSRF，且存在 formLogin 和 rememberMe。 | 问题 1 (CRITICAL, 组合) |
| 10. CORS 配置 | 已检查 CORS 配置。默认允许所有来源 + allowCredentials=true。 | 问题 1 (CRITICAL, 组合) |
| 11. 认证授权 | 已检查认证配置。默认管理员凭据硬编码；速率限制实质禁用。 | 问题 2 (CRITICAL), 问题 7 (MEDIUM) |
| 12. 会话管理 | 已检查会话配置。remember-me 14 天（已纳入组合漏洞分析）；桌面令牌 30 天有 OS 级保护。 | 无独立问题 |

---

## 18 文件评审覆盖确认

| 文件 | 已评审 | 涉及问题 |
|------|--------|----------|
| `ConvertWebsiteToPDF.java` | 是 | 问题 4 (SSRF) |
| `StampController.java` | 是 | 无问题 |
| `CompressController.java` | 是 | 问题 8 (LOW) |
| `SvgOverlayUtil.java` | 是 | 问题 6 (XXE) |
| `FileOrUploadService.java` | 是 | 问题 5 (PathTraversal) |
| `CustomHtmlSanitizer.java` | 是 | 问题 1 (组合), 问题 3 (XSS) |
| `SvgSanitizer.java` | 是 | 问题 1 (组合), 问题 3 (XSS) |
| `OfficeDocumentSanitizer.java` | 是 | 问题 1 (组合), 问题 3 (XSS) |
| `ProcessExecutor.java` | 是 | 无问题 |
| `CredentialEncryption.java` | 是 | 无问题 |
| `InitialSecuritySetup.java` | 是 | 问题 2 (HardcodedSecret) |
| `SecurityConfiguration.java` | 是 | 问题 1 (组合), 问题 7 (Auth) |
| `DatabaseController.java` | 是 | 无问题 |
| `DatabaseService.java` | 是 | 无问题 |
| `DesktopClientUtils.java` | 是 | 无问题 |
| `ExtractImageScansController.java` | 是 | 无问题 |
| `PDFToFile.java` | 是 | 无问题 |
| `PipelineProcessor.java` | 是 | 无问题 |

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 2 |
| HIGH | 3 |
| MEDIUM | 2 |
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
| CSRF | 1 (组合漏洞，含 CORS + Cookie 认证) |
| CORS | 0 (已纳入组合漏洞) |
| Auth | 1 |
| Session | 0 |

---

## 正面发现

1. **XML 解析安全配置完善**: `SvgSanitizer.parseSecurely()` 和 `OfficeDocumentSanitizer.parseSecurely()` 均正确禁用了所有外部实体（external-general-entities、external-parameter-entities）、DTD 加载（disallow-doctype-decl）和 XInclude，是 XXE 防护的最佳实践。

2. **命令注入防护到位**: `ProcessExecutor.validateCommand()` 对所有命令参数验证 null 字节、换行符和回车符，检查可执行文件路径穿越，使用列表参数（非 shell=True），是命令注入防护的良好实现。

3. **凭据加密实现规范**: `CredentialEncryption` 使用 AES-256-GCM 加密存储的凭据，密钥通过配置/环境变量/自动生成文件获取，密钥文件权限设置为 0600（仅所有者可读写），集群模式强制共享密钥。

4. **数据库备份 SQL 验证**: `DatabaseService.validateSqlContent()` 使用白名单+黑名单双重验证机制，在 SQL 脚本执行前检查危险操作（如 `FILE_WRITE`、`CREATE ALIAS`、`RUNSCRIPT` 等），并在内存数据库中预验证备份文件。

5. **路径穿越防护**: `DatabaseService.getBackupFilePath()` 正确使用了 `normalize()` + `startsWith()` 验证模式，`isValidFileName()` 检查了所有危险字符。`PipelineProcessor.generateInputFiles()` 也进行了路径穿越检查。

6. **SSRF 防护服务**: 项目实现了 `SsrfProtectionService` 用于 URL 安全验证，在 `CustomHtmlSanitizer` 和 `SvgSanitizer` 中被引用，体现了对 SSRF 风险的认知。

7. **Zip 安全输入流**: `OfficeDocumentSanitizer` 使用 `ZipSecurity.createHardenedInputStream()` 防止 Zip Bomb 攻击。

8. **文件名净化**: 多处使用 `io.github.pixee.security.Filenames.toSimpleFileName()` 和 `GeneralUtils.convertToFileName()` 对用户提供的文件名进行净化。

---

## 关键风险总结

1. **CSRF + CORS + Cookie 认证组合漏洞 (CRITICAL)**: 这是最严重的风险。CSRF 全局禁用 + CORS 默认允许所有来源 + allowCredentials=true + formLogin/rememberMe 的组合，使得攻击者可以通过恶意网站以受害者身份执行任意操作。此漏洞无需用户交互即可利用（用户仅需访问恶意页面），影响所有通过 Cookie 认证的用户。

2. **默认管理员硬编码凭据 (CRITICAL)**: `admin`/`stirling` 的默认管理员凭据在所有未配置初始凭据的实例中生效。如果部署后未及时修改，攻击者可直接获取系统最高权限。

3. **SSRF 可访问云元数据服务 (HIGH)**: URL-to-PDF 转换功能未验证目标 IP 地址，攻击者可利用 WeasyPrint 的资源加载能力访问云元数据服务（169.254.169.254）和内网服务，可能泄露云凭证和内部数据。

4. **disableSanitize 配置可禁用所有净化器 (HIGH)**: 单一配置项可同时禁用 HTML、SVG 和 Office 文档三类净化器，即使仅管理员可配置，影响范围过大。

5. **FileOrUploadService 路径穿越 (HIGH)**: `resolveFilePath()` 方法无任何路径验证，如果调用方传入用户可控的 fileId，可导致任意文件读取。

---

## 评审检查清单

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用组合漏洞判定规则（问题 1: CSRF + CORS + Cookie 认证 = 1 个 CRITICAL 组合漏洞）
- [x] 已应用问题合并规则（问题 3: disableSanitize 影响 3 个净化器 = 1 个 HIGH 问题）
- [x] 评审深度达到标准要求（CRITICAL/HIGH 逐行审查，MEDIUM 检查关键路径，LOW 快速审查）

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Eta
