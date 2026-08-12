# Stirling-PDF 安全评审报告 (V7)

> **评审标准**: 标准化评审指令 V7 (2026-08-12)  
> **评审者**: Agent Xi  
> **评审时间**: 2026-08-12  
> **项目**: Stirling-PDF  
> **评审文件数**: 18  

---

## 一、漏洞汇总统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 2 |
| **合计** | **9** |

---

## 二、详细发现

### HIGH-01: 路径遍历 -- Path.resolve(userInput) 无验证

**文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`  
**严重度**: HIGH (锁定)  
**漏洞类型**: 路径遍历 (Path Traversal)

**描述**:  
`resolveFilePath` 方法直接将用户可控的 `fileId` 参数传入 `Path.resolve()` 而没有任何路径遍历验证。攻击者可通过 `../` 等路径遍历序列访问服务器文件系统中的任意文件。

**代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```

**影响**: 攻击者可通过传入 `../../etc/passwd` 等值来读取服务器上的任意文件，可能导致敏感信息泄露。

**修复建议**: 对 `fileId` 进行路径遍历检查，验证 resolve 后的路径仍在 `tempDirPath` 目录下：
```java
public Path resolveFilePath(String fileId) {
    Path basePath = Path.of(tempDirPath).normalize();
    Path resolved = basePath.resolve(fileId).normalize();
    if (!resolved.startsWith(basePath)) {
        throw new SecurityException("Path traversal detected");
    }
    return resolved;
}
```

---

### HIGH-02: disableSanitize 可禁用所有净化器 (组合问题)

**文件**:  
- `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`  
- `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java`  
- `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java`  

**严重度**: HIGH (锁定)  
**漏洞类型**: 安全配置错误 -- 净化器可被禁用

**描述**:  
三个净化器（HTML 净化器、SVG 净化器、Office 文档净化器）均通过同一配置项 `applicationProperties.getSystem().isDisableSanitize()` 控制是否执行净化。当该配置设为 `true` 时，所有输入净化功能被完全绕过，恶意内容（XSS payload、恶意 SVG、含外部引用的 Office 文档）将直接传入后续处理流程。

**代码片段** (CustomHtmlSanitizer.java 第 64-67 行):
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```

**代码片段** (SvgSanitizer.java 第 59-62 行):
```java
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}
```

**代码片段** (OfficeDocumentSanitizer.java 第 80-83 行):
```java
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```

**影响**: 一旦该配置被启用（例如管理员误配置或攻击者通过其他漏洞修改配置），所有用户提交的文件将不经过任何安全净化，可能导致存储型 XSS、XXE、SSRF 等攻击。

**修复建议**: 移除 `disableSanitize` 全局开关，或将其限定为仅影响非安全相关的格式调整，确保安全净化不可被禁用。

---

### HIGH-03: CSRF 禁用 + CORS 允许所有来源 + allowCredentials + Cookie 认证 (组合漏洞)

**文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`  
**严重度**: HIGH (锁定 -- 组合漏洞)  
**漏洞类型**: CSRF + CORS 配置错误

**描述**:  
SecurityConfiguration 中存在以下安全配置组合：

1. **CSRF 完全禁用** (第 269 行): `http.csrf(CsrfConfigurer::disable)` -- 所有端点均无 CSRF 保护。
2. **CORS 默认允许所有来源** (第 188 行): 当未配置 `corsAllowedOrigins` 时，默认使用 `allowedOriginPatterns(List.of("*"))`。
3. **allowCredentials 设为 true** (第 218 行): `cfg.setAllowCredentials(true)` -- 允许跨域请求携带凭据。
4. **Cookie 认证**: 系统使用 `JSESSIONID`、`remember-me`、`stirling_jwt` 等 Cookie 进行身份认证 (第 336 行)。

根据 V7 组合漏洞规则，CSRF 禁用 + CORS `*` + allowCredentials=true + Cookie 认证 = 1 个 HIGH 问题。

**代码片段** (CSRF 禁用):
```java
http.csrf(CsrfConfigurer::disable);
```

**代码片段** (CORS 默认允许所有来源):
```java
} else {
    // Default to allowing all origins when nothing is configured
    cfg.setAllowedOriginPatterns(List.of("*"));
}
```

**代码片段** (allowCredentials):
```java
cfg.setAllowCredentials(true);
```

**影响**: 攻击者可在恶意网站上构造跨域请求，利用受害者的浏览器 Cookie 身份认证执行未授权操作（如修改密码、导入恶意数据库备份、删除文件等）。

**修复建议**: 
1. 启用 CSRF 保护，至少对状态修改操作（POST/PUT/DELETE）启用。
2. 将 CORS 默认策略改为不允许所有来源，要求管理员显式配置。
3. 当 `allowedOriginPatterns` 为 `*` 时，不应设置 `allowCredentials=true`。

---

### MEDIUM-01: SSRF -- URL 转 PDF 未验证内网 IP

**文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`  
**严重度**: MEDIUM (锁定)  
**漏洞类型**: 服务端请求伪造 (SSRF)

**描述**:  
`urlToPdf` 端点接受用户提供的 URL，通过 `fetchRemoteHtml()` 方法使用 `java.net.http.HttpClient` 获取远程 HTML 内容，然后传递给 WeasyPrint 转换为 PDF。URL 验证仅检查格式有效性和可达性，未验证目标地址是否为内网 IP。此外，WeasyPrint 在处理 HTML 时可能基于 HTML 内容中的 CSS/图片引用发起额外的内部网络请求，且代码未对 WeasyPrint 阶段的外部资源加载进行限制。

**代码片段** (URL 验证 -- 缺少内网 IP 检查):
```java
boolean patternValid = RegexPatternUtils.getInstance().getHttpUrlPattern().matcher(URL).matches();
boolean generalValid = GeneralUtils.isValidURL(URL);
if (!patternValid && !generalValid) {
    // ... reject
} else if (!GeneralUtils.isURLReachable(URL)) {
    // ... reject
}
```

**代码片段** (HttpClient 直接请求用户 URL):
```java
private String fetchRemoteHtml(String url) throws IOException, InterruptedException {
    HttpClient client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NEVER)
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    HttpRequest request = HttpRequest.newBuilder(URI.create(url))
            .timeout(Duration.ofSeconds(20))
            .GET()
            .build();
    HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
    // ...
}
```

**影响**: 攻击者可构造指向内网地址的 URL（如 `http://169.254.169.254/latest/meta-data/`、`http://192.168.1.1/`、`http://127.0.0.1:8080/`），通过生成的 PDF 获取内网服务信息（半盲 SSRF），或通过 WeasyPrint 的渲染能力获取内网页面内容。

**修复建议**: 在 URL 验证阶段增加内网 IP 检查，拒绝 RFC 1918 私有地址、链路本地地址、回环地址等。

---

### MEDIUM-02: SAXSVGDocumentFactory 未禁用外部实体

**文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`  
**严重度**: MEDIUM (锁定)  
**漏洞类型**: XML 外部实体注入 (XXE)

**描述**:  
`SAXSVGDocumentFactory` 在创建 SVG 文档时未禁用外部实体解析。虽然 Batik 的 BridgeContext 层通过自定义 UserAgent 阻止了外部资源加载，但 `SAXSVGDocumentFactory` 在 XML 解析阶段仍可能处理外部实体声明，存在 XXE 风险。

**代码片段** (第 35-41 行):
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```

**对比**: 同一项目中的 `SvgSanitizer.java` 在解析 XML 时正确禁用了外部实体：
```java
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

**影响**: 攻击者可通过构造恶意 SVG 文件，在 XML 解析阶段触发外部实体读取服务器文件或发起内部网络请求。

**修复建议**: 在创建 `SAXSVGDocumentFactory` 时设置安全特性以禁用外部实体解析，或在 XMLReader 层面配置安全特性。

---

### MEDIUM-03: 硬编码管理员默认凭据

**文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`  
**严重度**: MEDIUM (锁定)  
**漏洞类型**: 硬编码密钥/凭据 (HardcodedSecret)

**描述**:  
当系统无配置文件指定的管理员用户时，`createDefaultAdminUser()` 方法使用硬编码的用户名 `"admin"` 和密码 `"stirling"` 创建默认管理员账户。如果管理员未及时修改密码，攻击者可使用这组默认凭据登录系统。

**代码片段** (第 153-168 行):
```java
private void createDefaultAdminUser() throws SQLException, UnsupportedProviderException {
    String defaultUsername = "admin";
    String defaultPassword = "stirling";

    if (userService.findByUsernameIgnoreCase(defaultUsername).isEmpty()) {
        Team team = teamService.getOrCreateDefaultTeam();
        SaveUserRequest.Builder builder = SaveUserRequest.builder()
                .username(defaultUsername)
                .password(defaultPassword)
                .team(team)
                .role(Role.ADMIN.getRoleId())
                .firstLogin(true);
        userService.saveUserCore(builder.build());
    }
}
```

**影响**: 默认凭据 `admin/stirling` 是公开可知的，攻击者可直接使用此凭据尝试登录管理员账户。

**修复建议**: 
1. 首次登录时强制修改密码。
2. 生成随机初始密码并在启动日志中输出（仅首次启动）。
3. 在启动界面提示用户修改默认密码。

---

### MEDIUM-04: CSRF 禁用 + 速率限制禁用/极高值 (组合漏洞)

**文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`  
**严重度**: MEDIUM (锁定 -- 组合漏洞)  
**漏洞类型**: 安全配置错误 -- CSRF + 速率限制

**描述**:  
根据 V7 组合漏洞规则，CSRF 禁用 + 速率限制禁用 = 1 个 MEDIUM 问题。

1. **CSRF 完全禁用** (第 269 行): `http.csrf(CsrfConfigurer::disable)`
2. **速率限制实质禁用**: `IPRateLimitingFilter` 被配置为每 IP 1,000,000 次请求的极高限制 (第 478 行)，且该过滤器被注释掉未注册到过滤器链中 (第 299-304 行)。

**代码片段** (速率限制配置 -- 极高值):
```java
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    // Example limit TODO add config level
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
```

**代码片段** (过滤器被注释掉):
```java
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op) and raw Filter
// impl causes Spring Security async dispatch bug...
// .addFilterBefore(rateLimitingFilter,
//         UsernamePasswordAuthenticationFilter.class)
```

**影响**: 无 CSRF 保护且无有效速率限制，攻击者可对登录用户发起大规模跨站请求攻击（CSRF），或对登录端点发起暴力破解攻击。

**修复建议**: 
1. 启用 CSRF 保护。
2. 将速率限制转换为 `OncePerRequestFilter` 并配置合理的限制值。
3. 对登录端点设置更严格的速率限制。

---

### LOW-01: HttpFirewall 允许换行符

**文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`  
**严重度**: LOW (锁定)  
**漏洞类型**: HttpFirewall 配置错误

**描述**:  
`HttpFirewall` 配置中，参数值允许正则表达式包含 `\r` 和 `\n`（回车符和换行符），可能允许 HTTP 请求走私或日志注入攻击。

**代码片段** (第 165-169 行):
```java
// Allow non-ASCII characters and newlines in parameter values.
Pattern allowedParamChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*");
firewall.setAllowedParameterValues(
        parameterValue ->
                parameterValue != null
                        && allowedParamChars.matcher(parameterValue).matches());
```

**注意**: 头部值配置 (第 159 行) 正确排除了控制字符 `[\\p{IsAssigned}&&[^\\p{IsControl}]]*`，仅参数值配置存在此问题。

**影响**: 攻击者可能在参数值中注入换行符，用于 HTTP 请求走私或日志注入。

**修复建议**: 从参数值允许的正则表达式中移除 `\\r\\n`，与头部值配置保持一致。

---

### LOW-02: MD5 用于图像去重哈希

**文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`  
**严重度**: LOW (锁定 -- V7 必须单独报告)  
**漏洞类型**: 弱哈希算法 (MD5)

**描述**:  
`CompressController` 中使用 MD5 算法生成图像去重哈希值，用于识别 PDF 中的重复图像以进行压缩优化。涉及 4 个方法：`generateImageHash()`、`generateMaskHash()`、`generateDecodeParamsHash()` 和 `generateMetadataHash()`，均通过 `generateMD5()` 方法调用 `MessageDigest.getInstance("MD5")`。

**代码片段** (第 742-749 行):
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

**调用位置**:
- `generateImageHash()` (第 336 行) -- 生成图像像素数据哈希
- `generateMaskHash()` (第 417 行) -- 生成遮罩数据哈希
- `generateDecodeParamsHash()` (第 735-736 行) -- 生成解码参数哈希
- `generateMetadataHash()` (第 807-808 行) -- 生成元数据哈希

**影响**: MD5 已被证明存在碰撞攻击，虽然此处仅用于非安全场景（图像去重），但使用弱哈希算法不符合安全最佳实践。在极端情况下，攻击者可能构造碰撞图像绕过去重逻辑。

**修复建议**: 将 MD5 替换为 SHA-256 等更安全的哈希算法。

---

## 三、13 维度评审覆盖

### 维度 1: SQL 注入 (SQLi)

**结论**: 未发现 SQL 注入漏洞。

DatabaseService 中所有 SQL 操作均使用 `PreparedStatement` 和参数化查询。`validateSqlContent()` 方法对导入的 SQL 备份文件实施了白名单和黑名单双重验证。

### 维度 2: 跨站脚本 (XSS)

**结论**: 未发现直接 XSS 漏洞。

StampController 将用户文本渲染到 PDF 中（非 HTML 上下文），不构成 XSS 风险。CustomHtmlSanitizer 提供了 HTML 净化功能（但存在 disableSanitize 绕过问题，见 HIGH-02）。SvgSanitizer 移除了 SVG 中的事件处理属性和危险元素。

### 维度 3: XML 外部实体注入 (XXE)

**结论**: 发现 1 个 MEDIUM 级别问题。

SvgOverlayUtil 中的 `SAXSVGDocumentFactory` 未禁用外部实体 (MEDIUM-02)。SvgSanitizer 和 OfficeDocumentSanitizer 中的 XML 解析器已正确配置禁用外部实体。

### 维度 4: 路径遍历 (Path Traversal)

**结论**: 发现 1 个 HIGH 级别问题。

FileOrUploadService.resolveFilePath() 直接使用用户输入进行路径解析 (HIGH-01)。StampController 对文件名进行了 `..` 和前导 `/` 检查。DatabaseService.getBackupFilePath() 使用 normalize + startsWith 验证。PipelineProcessor.generateInputFiles() 使用 normalize + startsWith 验证。

### 维度 5: 命令注入 (Command Injection)

**结论**: 未发现命令注入漏洞。

ProcessExecutor 使用 `ProcessBuilder(List<String>)` 避免 shell 注入。`validateCommand()` 方法验证参数中的空字节、换行符和路径遍历。所有命令参数均来自受控配置或经过验证的用户输入。

### 维度 6: 服务端请求伪造 (SSRF)

**结论**: 发现 1 个 MEDIUM 级别问题。

ConvertWebsiteToPDF 接受用户 URL 并发起服务端请求，未验证内网 IP (MEDIUM-01)。CustomHtmlSanitizer 和 SvgSanitizer 通过 SsrfProtectionService 验证 URL。

### 维度 7: 文件上传 (File Upload)

**结论**: 未发现严重文件上传漏洞。

文件上传使用临时文件处理，文件名通过 `Filenames.toSimpleFileName()` 和自定义验证进行清理。OfficeDocumentSanitizer 使用 `ZipSecurity.createHardenedInputStream()` 防止 Zip Slip 攻击。

### 维度 8: 硬编码密钥/凭据 (HardcodedSecret)

**结论**: 发现 2 个问题 (1 个 MEDIUM + 1 个 LOW)。

InitialSecuritySetup 包含硬编码默认管理员凭据 (MEDIUM-03)。CompressController 使用 MD5 哈希算法 (LOW-02)。CredentialEncryption 使用 AES-256-GCM，密钥管理合理（支持配置、环境变量或自动生成密钥文件）。

### 维度 9: CSRF

**结论**: CSRF 完全禁用，与其他配置组合形成 HIGH 和 MEDIUM 级别问题。

SecurityConfiguration 第 269 行 `http.csrf(CsrfConfigurer::disable)` 全局禁用 CSRF。组合问题见 HIGH-03 和 MEDIUM-04。

### 维度 10: CORS

**结论**: CORS 默认配置过于宽松，与 CSRF 禁用组合形成 HIGH 级别问题。

默认 `allowedOriginPatterns("*")` + `allowCredentials(true)` (HIGH-03)。支持通过 `system.corsAllowedOrigins` 配置自定义来源。

### 维度 11: 认证 (Authentication)

**结论**: 认证机制整体安全，存在默认凭据问题。

系统支持用户名/密码、OAuth2、SAML2 多种认证方式。JWT 和 Cookie 认证并存。InitialSecuritySetup 使用硬编码默认管理员凭据 (MEDIUM-03)。

### 维度 12: 会话管理 (Session Management)

**结论**: 会话管理配置基本安全。

支持 STATELESS (JWT) 和 IF_REQUIRED (Session) 两种会话策略。Remember-me 配置使用安全 Cookie (`useSecureCookie(true)`)。退出时清除认证状态并删除 Cookie。

### 维度 13: HttpFirewall

**结论**: 发现 1 个 LOW 级别问题。

StrictHttpFirewall 的参数值允许正则表达式包含 `\r\n` (LOW-01)。头部值配置正确排除了控制字符。

---

## 四、13 维度评审覆盖确认

| # | 维度 | 是否检查 | 发现问题 | 严重度 |
|---|------|---------|---------|--------|
| 1 | SQL 注入 (SQLi) | 是 | 无 | -- |
| 2 | 跨站脚本 (XSS) | 是 | 无 (净化器绕过问题归入 HIGH-02) | -- |
| 3 | XML 外部实体注入 (XXE) | 是 | SAXSVGDocumentFactory 未禁用外部实体 | MEDIUM |
| 4 | 路径遍历 (Path Traversal) | 是 | Path.resolve(userInput) 无验证 | HIGH |
| 5 | 命令注入 (Command Injection) | 是 | 无 | -- |
| 6 | 服务端请求伪造 (SSRF) | 是 | URL 转 PDF 未验证内网 IP | MEDIUM |
| 7 | 文件上传 (File Upload) | 是 | 无 | -- |
| 8 | 硬编码密钥/凭据 (HardcodedSecret) | 是 | 硬编码管理员凭据 + MD5 使用 | MEDIUM + LOW |
| 9 | CSRF | 是 | CSRF 全局禁用 (组合问题) | HIGH + MEDIUM |
| 10 | CORS | 是 | 默认允许所有来源 (组合问题) | HIGH |
| 11 | 认证 (Authentication) | 是 | 默认管理员凭据 | MEDIUM |
| 12 | 会话管理 (Session Management) | 是 | 无 | -- |
| 13 | HttpFirewall | 是 | 参数值允许换行符 | LOW |

---

## 五、18 文件评审覆盖确认

| # | 文件 | 是否已审 | 发现问题 |
|---|------|---------|---------|
| 1 | `app/core/.../ConvertWebsiteToPDF.java` | 是 | SSRF (MEDIUM-01) |
| 2 | `app/core/.../StampController.java` | 是 | 无 |
| 3 | `app/core/.../CompressController.java` | 是 | MD5 (LOW-02) |
| 4 | `app/core/.../SvgOverlayUtil.java` | 是 | XXE (MEDIUM-02) |
| 5 | `app/common/.../FileOrUploadService.java` | 是 | 路径遍历 (HIGH-01) |
| 6 | `app/common/.../CustomHtmlSanitizer.java` | 是 | disableSanitize (HIGH-02) |
| 7 | `app/common/.../SvgSanitizer.java` | 是 | disableSanitize (HIGH-02) |
| 8 | `app/common/.../OfficeDocumentSanitizer.java` | 是 | disableSanitize (HIGH-02) |
| 9 | `app/common/.../ProcessExecutor.java` | 是 | 无 |
| 10 | `app/proprietary/.../CredentialEncryption.java` | 是 | 无 |
| 11 | `app/proprietary/.../InitialSecuritySetup.java` | 是 | 硬编码凭据 (MEDIUM-03) |
| 12 | `app/proprietary/.../SecurityConfiguration.java` | 是 | CSRF+CORS (HIGH-03), 速率限制 (MEDIUM-04), HttpFirewall (LOW-01) |
| 13 | `app/proprietary/.../DatabaseController.java` | 是 | 无 |
| 14 | `app/proprietary/.../DatabaseService.java` | 是 | 无 |
| 15 | `app/proprietary/.../DesktopClientUtils.java` | 是 | 无 |
| 16 | `app/core/.../ExtractImageScansController.java` | 是 | 无 |
| 17 | `app/common/.../PDFToFile.java` | 是 | 无 |
| 18 | `app/core/.../PipelineProcessor.java` | 是 | 无 |

---

## 六、严重度确认清单

### 步骤 1: 严重度锁定检查

- [x] `disableSanitize` 可禁用净化器 -> HIGH (HIGH-02)
- [x] `allowedOriginPatterns("*")` + `allowCredentials(true)` -> HIGH (HIGH-03 组合)
- [x] `Path.resolve(userInput)` 无验证 -> HIGH (HIGH-01)
- [x] 硬编码管理员凭据 -> MEDIUM (MEDIUM-03)
- [x] SSRF 未验证内网 IP -> MEDIUM (MEDIUM-01)
- [x] `SAXSVGDocumentFactory` 未禁用外部实体 -> MEDIUM (MEDIUM-02)
- [x] 速率限制禁用/极高值 -> MEDIUM (MEDIUM-04 组合)
- [x] MD5/SHA1 用于任何场景 -> LOW (LOW-02, 独立报告)
- [x] HttpFirewall 允许换行符 -> LOW (LOW-01)

### 步骤 2: 组合漏洞检查

- [x] CSRF 禁用 + CORS `*` + allowCredentials=true + Cookie 认证 -> 合并为 1 个 HIGH (HIGH-03)
- [x] CSRF 禁用 + 速率限制禁用 -> 合并为 1 个 MEDIUM (MEDIUM-04)

### 步骤 3: 问题合并检查

- [x] disableSanitize 同一配置影响 3 个文件 (CustomHtmlSanitizer, SvgSanitizer, OfficeDocumentSanitizer) -> 合并为 1 个 HIGH (HIGH-02)
- [x] CSRF + CORS + Cookie 认证同一文件 (SecurityConfiguration) -> 合并为 1 个 HIGH (HIGH-03)
- [x] CSRF + 速率限制同一文件 (SecurityConfiguration) -> 合并为 1 个 MEDIUM (MEDIUM-04)
- [x] MD5 同一文件 (CompressController) 多处使用 -> 合并为 1 个 LOW (LOW-02)

---

## 七、评审检查清单

- [x] 已检查所有 13 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了锁定严重度（禁止降级）
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求
- [x] 已应用组合漏洞判定规则
- [x] 已应用问题合并规则
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题
- [x] 已对每个维度给出明确结论
- [x] 已执行严重度确认步骤
- [x] MD5/SHA1 已作为独立 LOW 问题报告 (V7)

---

**评审完成时间**: 2026-08-12  
**评审者**: Agent Xi  
**评审标准**: 标准化评审指令 V7
