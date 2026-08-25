# Stirling-PDF 安全评审报告 (V7)

> **评审标准**: 标准化评审指令 V7 (2026-08-12)
> **评审项目**: Stirling-PDF
> **评审范围**: 18 个核心文件
> **评审者**: Agent Nu
> **评审日期**: 2026-08-12

---

## 一、评审概述

本次评审严格按照 V7 标准化评审指令，对 Stirling-PDF 项目的 18 个核心文件进行安全评审。评审覆盖 13 个安全维度，应用严重度锁定规则、组合漏洞规则和问题合并规则。

---

## 二、发现问题汇总

| # | 漏洞类型 | 严重度 | 问题描述 | 涉及文件 |
|---|---------|--------|---------|---------|
| 1 | CSRF + CORS + Cookie 认证 | **HIGH** | CSRF 禁用 + CORS `*` + `allowCredentials(true)` + Cookie 认证组合漏洞 | SecurityConfiguration.java |
| 2 | XSS | **HIGH** | `disableSanitize` 配置可禁用全部 HTML/SVG/Office 文档净化器 | CustomHtmlSanitizer.java, SvgSanitizer.java, OfficeDocumentSanitizer.java |
| 3 | 路径遍历 | **HIGH** | `Path.resolve(userInput)` 无验证，用户可控 fileId 直接解析 | FileOrUploadService.java |
| 4 | SSRF | **MEDIUM** | URL-to-PDF 转换未验证内网 IP 地址 | ConvertWebsiteToPDF.java |
| 5 | XXE | **MEDIUM** | `SAXSVGDocumentFactory` 未禁用外部实体特性 | SvgOverlayUtil.java |
| 6 | 硬编码凭据 | **MEDIUM** | 默认管理员凭据 admin/stirling 硬编码 | InitialSecuritySetup.java |
| 7 | CSRF + 速率限制 | **MEDIUM** | CSRF 禁用 + 速率限制禁用/极高值组合漏洞 | SecurityConfiguration.java |
| 8 | HttpFirewall | **LOW** | HttpFirewall 允许参数值中包含换行符 `\r\n` | SecurityConfiguration.java |
| 9 | 弱哈希算法 | **LOW** | MD5 用于图像去重哈希（非安全场景也须报告） | CompressController.java |

### 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 2 |
| **合计** | **9** |

---

## 三、问题详情

### 问题 #1: CSRF 禁用 + CORS `*` + `allowCredentials(true)` + Cookie 认证 [HIGH]

**漏洞类型**: CSRF + CORS + Cookie 认证组合漏洞
**严重度**: HIGH（组合漏洞锁定）
**应用规则**: 组合漏洞规则 -- CSRF 禁用 + CORS `*` + `allowCredentials(true)` + Cookie 认证 = 1 个 HIGH

**涉及文件**:
- `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`

**代码片段**:

CSRF 禁用（第 269 行）:
```java
http.csrf(CsrfConfigurer::disable);
```

CORS 允许所有来源（第 188 行）:
```java
cfg.setAllowedOriginPatterns(List.of("*"));
```

允许凭证（第 218 行）:
```java
cfg.setAllowCredentials(true);
```

Cookie 认证（第 336 行）:
```java
.deleteCookies("JSESSIONID", "remember-me", "stirling_jwt");
```

**分析**: CSRF 保护被完全禁用，同时 CORS 配置允许所有来源（`*`）并允许携带凭证（`allowCredentials(true)`），应用使用 Cookie（JSESSIONID、remember-me）进行身份认证。攻击者可以构造恶意网页，利用受害者的浏览器自动携带认证 Cookie 发起跨域请求，执行未授权操作（如上传文件、修改设置、导入数据库等）。

**修复建议**:
1. 启用 CSRF 保护，至少对状态变更操作（POST/PUT/DELETE）要求 CSRF Token
2. 将 CORS `allowedOriginPatterns` 配置为具体的可信来源，不使用 `*`
3. 如果必须允许所有来源，则不应设置 `allowCredentials(true)`

---

### 问题 #2: `disableSanitize` 配置可禁用全部净化器 [HIGH]

**漏洞类型**: XSS / 净化器绕过
**严重度**: HIGH（严重度锁定规则 -- `disableSanitize` 可禁用净化器）
**应用规则**: 同一配置（`disableSanitize`）影响多个文件 = 算 1 个问题

**涉及文件**:
- `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java`
- `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java`

**代码片段**:

CustomHtmlSanitizer.java（第 65-66 行）:
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```

SvgSanitizer.java（第 59-61 行）:
```java
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("SVG sanitization disabled by configuration");
    return svgBytes;
}
```

OfficeDocumentSanitizer.java（第 80-82 行）:
```java
if (applicationProperties.getSystem().isDisableSanitize()) {
    log.debug("Office document sanitization disabled by configuration");
    return documentBytes;
}
```

**分析**: 三个净化器（HTML、SVG、Office 文档）均受 `disableSanitize` 配置控制。当该配置启用时，所有输入内容将绕过安全净化直接处理，可能导致：
- XSS 攻击（通过恶意 HTML/SVG 注入）
- SSRF（通过 SVG/Office 文档中的外部引用）
- 任意代码执行（通过 Office 文档中的恶意宏或外部实体）

**修复建议**:
1. 移除 `disableSanitize` 全局开关，或将其限制为仅限开发/测试环境
2. 在生产环境中强制启用净化，不允许通过配置关闭
3. 如需性能优化，提供细粒度的净化级别而非完全禁用

---

### 问题 #3: `Path.resolve(userInput)` 无验证 [HIGH]

**漏洞类型**: 路径遍历
**严重度**: HIGH（严重度锁定规则 -- `Path.resolve(userInput)` 无验证）

**涉及文件**:
- `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`

**代码片段**:

```java
@Value("${stirling.tempDir:/tmp/stirling-files}")
private String tempDirPath;

public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```

**分析**: `resolveFilePath()` 方法将用户可控的 `fileId` 参数直接传递给 `Path.resolve()`，没有任何路径遍历检查。攻击者可以传入 `../../etc/passwd` 等值来访问服务器上的任意文件。该方法被其他服务调用时，可能导致敏感文件读取或任意文件写入。

**修复建议**:
1. 对 `fileId` 进行严格验证，拒绝包含 `..`、`/`、`\` 等路径分隔符的输入
2. 解析后验证最终路径是否仍在 `tempDirPath` 目录下
3. 使用白名单机制限制允许访问的文件 ID 格式

---

### 问题 #4: SSRF -- URL-to-PDF 未验证内网 IP [MEDIUM]

**漏洞类型**: SSRF
**严重度**: MEDIUM（严重度锁定规则 -- SSRF 未验证内网 IP）

**涉及文件**:
- `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`

**代码片段**:

URL 验证逻辑（第 88-103 行）:
```java
boolean patternValid =
        RegexPatternUtils.getInstance().getHttpUrlPattern().matcher(URL).matches();
boolean generalValid = GeneralUtils.isValidURL(URL);
if (!patternValid && !generalValid) {
    // ... reject
} else if (!GeneralUtils.isURLReachable(URL)) {
    // ... reject
}
```

fetchRemoteHtml 方法直接请求用户提供的 URL（第 175-201 行）:
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
    HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    // ...
}
```

**分析**: URL 验证仅检查格式（是否为合法 HTTP URL）和可达性，但未验证目标 IP 是否为内网地址。攻击者可以传入以下 URL：
- `http://169.254.169.254/latest/meta-data/` -- 获取云实例元数据
- `http://127.0.0.1:8080/admin` -- 访问内部服务
- `http://10.0.0.1/` -- 探测内网

此外，虽然 `file:` scheme 被阻止，但 WeasyPrint 渲染下载的 HTML 时可能加载其他内部资源。

**修复建议**:
1. 在 URL 验证中增加内网 IP 检查（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 127.0.0.0/8）
2. 对 DNS 解析后的 IP 地址进行二次验证（防止 DNS Rebinding）
3. 考虑使用 SSRF 保护服务（如项目中已有的 `SsrfProtectionService`）

---

### 问题 #5: `SAXSVGDocumentFactory` 未禁用外部实体 [MEDIUM]

**漏洞类型**: XXE
**严重度**: MEDIUM（严重度锁定规则 -- `SAXSVGDocumentFactory` 未禁用外部实体）

**涉及文件**:
- `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`

**代码片段**:

```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);

SVGDocument svgDoc;
try (ByteArrayInputStream inputStream = new ByteArrayInputStream(svgBytes)) {
    svgDoc = factory.createSVGDocument("file:///overlay.svg", inputStream);
}
```

UserAgent 层面的外部资源阻止（第 43-56 行）:
```java
UserAgent userAgent = new UserAgentAdapter() {
    @Override
    public void checkLoadExternalResource(ParsedURL resourceURL, ParsedURL docURL) {
        if (resourceURL != null && "data".equals(resourceURL.getProtocol())) {
            return;
        }
        throw new SecurityException("External resource loading is disabled...");
    }
};
```

**分析**: `SAXSVGDocumentFactory` 在创建 XML 解析器时，未显式禁用外部实体相关特性（如 `http://xml.org/sax/features/external-general-entities` 和 `http://xml.org/sax/features/external-parameter-entities`）。虽然 Batik 的 UserAgent 在资源加载层面进行了阻止，但 XML 解析器本身仍可能处理外部实体声明，存在 XXE 风险。相比之下，`SvgSanitizer.java` 中的 `parseSecurely()` 方法正确设置了所有 XXE 防护特性。

**修复建议**:
1. 在 `SAXSVGDocumentFactory` 上设置安全特性，禁用外部实体处理
2. 参考 `SvgSanitizer.parseSecurely()` 的实现方式
3. 在解析前对 SVG 内容进行预处理，移除 DOCTYPE 声明

---

### 问题 #6: 硬编码默认管理员凭据 [MEDIUM]

**漏洞类型**: 硬编码凭据
**严重度**: MEDIUM（严重度锁定规则 -- 硬编码管理员凭据）

**涉及文件**:
- `app/proprietary/src/main/java/stirling/software/proprietary/security/InitialSecuritySetup.java`

**代码片段**:

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
        log.info("Default admin user created: {}", defaultUsername);
    }
}
```

**分析**: 当系统未配置初始管理员用户且数据库中不存在任何用户时，自动创建用户名为 `admin`、密码为 `stirling` 的默认管理员账户。这些凭据是公开已知的，如果管理员未在使用前修改密码，攻击者可以利用这些默认凭据获取管理员权限。日志中也记录了用户名（第 167 行），增加了信息泄露风险。

**修复建议**:
1. 在首次启动时强制要求设置管理员密码，不使用硬编码默认值
2. 生成随机密码并在控制台输出一次，强制用户修改
3. 至少添加首次登录强制修改密码的机制（当前 `firstLogin=true` 可能已有此逻辑，但默认凭据本身仍不应硬编码）

---

### 问题 #7: CSRF 禁用 + 速率限制禁用 [MEDIUM]

**漏洞类型**: CSRF + 速率限制组合漏洞
**严重度**: MEDIUM（组合漏洞锁定）
**应用规则**: 组合漏洞规则 -- CSRF 禁用 + 速率限制禁用 = 1 个 MEDIUM

**涉及文件**:
- `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`

**代码片段**:

速率限制过滤器被注释掉（第 299-304 行）:
```java
// TODO: IPRateLimitingFilter disabled (limit is 1M, no-op) and raw Filter
// impl causes Spring Security async dispatch bug (response already committed
// errors on StreamingResponseBody endpoints). Re-enable once converted to
// OncePerRequestFilter with proper config-driven limits.
// .addFilterBefore(rateLimitingFilter,
//         UsernamePasswordAuthenticationFilter.class)
```

速率限制值极高（第 477-479 行）:
```java
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
```

**分析**: 速率限制过滤器被完全注释掉（未注册到过滤器链中），即使注册，1,000,000 请求的限制也等同于无限制。结合 CSRF 保护被禁用，攻击者可以不受限制地发起自动化攻击（暴力破解、CSRF 攻击、资源耗尽等），而不会触发任何速率限制机制。

**修复建议**:
1. 将 `IPRateLimitingFilter` 转换为 `OncePerRequestFilter` 并重新启用
2. 将速率限制值降低到合理水平（如每分钟 60 次）
3. 提供配置驱动的速率限制设置

---

### 问题 #8: HttpFirewall 允许参数值中包含换行符 [LOW]

**漏洞类型**: HttpFirewall 配置
**严重度**: LOW（严重度锁定规则 -- HttpFirewall 允许换行符）

**涉及文件**:
- `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`

**代码片段**:

```java
@Bean
public HttpFirewall httpFirewall() {
    StrictHttpFirewall firewall = new StrictHttpFirewall();
    Pattern allowedChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]]*");
    firewall.setAllowedHeaderValues(
            headerValue -> headerValue != null && allowedChars.matcher(headerValue).matches());

    // Allow non-ASCII characters and newlines in parameter values.
    Pattern allowedParamChars = Pattern.compile("[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*");
    firewall.setAllowedParameterValues(
            parameterValue ->
                    parameterValue != null
                            && allowedParamChars.matcher(parameterValue).matches());
    return firewall;
}
```

**分析**: `setAllowedParameterValues` 的正则表达式 `[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*` 显式允许了 `\r`（回车）和 `\n`（换行）字符。`StrictHttpFirewall` 默认拒绝这些控制字符。允许参数值中包含换行符可能导致：
- HTTP 响应拆分攻击
- HTTP 请求走私
- 日志注入

注意：Header 值的正则表达式正确地排除了控制字符，仅参数值存在问题。

**修复建议**:
1. 移除参数值正则表达式中的 `\\r\\n`，使用与 Header 相同的严格模式
2. 如果确实需要支持换行符，仅在特定参数上使用白名单而非全局放宽

---

### 问题 #9: MD5 用于图像去重哈希 [LOW]

**漏洞类型**: 弱哈希算法
**严重度**: LOW（V7 强制要求 -- MD5/SHA1 用于任何场景必须单独报告）

**涉及文件**:
- `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`

**代码片段**:

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

MD5 被以下方法调用用于图像去重：
- `generateImageHash()` -- 生成图像像素数据哈希（第 335-336 行）
- `generateMaskHash()` -- 生成遮罩哈希（第 417 行）
- `generateDecodeParamsHash()` -- 生成解码参数哈希（第 735-736 行）
- `ImageIdentity.generateMetadataHash()` -- 生成元数据哈希（第 807-808 行）

**分析**: MD5 是已知的弱哈希算法，存在碰撞攻击。虽然此处仅用于图像去重（非安全场景），但 V7 规则要求必须作为独立 LOW 问题报告。使用 MD5 进行去重存在哈希碰撞导致不同图像被误判为相同的理论风险。

**修复建议**:
1. 将 MD5 替换为 SHA-256 等更安全的哈希算法
2. 如果性能是关键考虑，可使用 SHA-256 的截断版本或 BLAKE3

---

## 四、13 维度评审覆盖确认

| # | 评审维度 | 结论 | 发现问题 |
|---|---------|------|---------|
| 1 | SQL 注入 (SQLi) | **未发现** | DatabaseService 使用 PreparedStatement 参数化查询，SQL 白名单/黑名单验证完善 |
| 2 | 跨站脚本 (XSS) | **发现 HIGH** | `disableSanitize` 可禁用全部净化器（问题 #2） |
| 3 | XML 外部实体 (XXE) | **发现 MEDIUM** | `SAXSVGDocumentFactory` 未禁用外部实体特性（问题 #5） |
| 4 | 路径遍历 (Path Traversal) | **发现 HIGH** | `FileOrUploadService.resolve()` 无验证（问题 #3） |
| 5 | 命令注入 (Command Injection) | **未发现** | ProcessExecutor 使用 ProcessBuilder（非 shell），validateCommand 进行输入验证 |
| 6 | 服务端请求伪造 (SSRF) | **发现 MEDIUM** | URL-to-PDF 未验证内网 IP（问题 #4） |
| 7 | 文件上传 (File Upload) | **未发现** | StampController 有文件名验证，ImageIO 安全读取，TempFile 管理临时文件 |
| 8 | 硬编码密钥/凭据 (HardcodedSecret) | **发现 MEDIUM + LOW** | 默认管理员凭据（问题 #6）；MD5 使用（问题 #9） |
| 9 | CSRF | **发现 HIGH（组合）** | CSRF 完全禁用，参与组合漏洞（问题 #1） |
| 10 | CORS | **发现 HIGH（组合）** | `allowedOriginPatterns("*")` + `allowCredentials(true)`，参与组合漏洞（问题 #1） |
| 11 | 认证 (Auth) | **发现 MEDIUM** | 硬编码默认管理员凭据（问题 #6） |
| 12 | 会话管理 (Session) | **未发现** | 使用 STATELESS 策略，Remember-me 配置安全（secure cookie），JWT 认证正常 |
| 13 | HttpFirewall | **发现 LOW** | 参数值允许换行符 `\r\n`（问题 #8） |

---

## 五、18 文件评审覆盖确认

| # | 文件路径 | 已评审 | 发现问题 |
|---|---------|--------|---------|
| 1 | `app/core/.../converters/ConvertWebsiteToPDF.java` | Yes | SSRF（问题 #4） |
| 2 | `app/core/.../misc/StampController.java` | Yes | 无独立问题 |
| 3 | `app/core/.../misc/CompressController.java` | Yes | MD5 使用（问题 #9） |
| 4 | `app/core/.../utils/SvgOverlayUtil.java` | Yes | XXE（问题 #5） |
| 5 | `app/common/.../service/FileOrUploadService.java` | Yes | 路径遍历（问题 #3） |
| 6 | `app/common/.../util/CustomHtmlSanitizer.java` | Yes | 净化器可禁用（问题 #2） |
| 7 | `app/common/.../util/SvgSanitizer.java` | Yes | 净化器可禁用（问题 #2） |
| 8 | `app/common/.../util/OfficeDocumentSanitizer.java` | Yes | 净化器可禁用（问题 #2） |
| 9 | `app/common/.../util/ProcessExecutor.java` | Yes | 无独立问题 |
| 10 | `app/proprietary/.../crypto/CredentialEncryption.java` | Yes | 无独立问题 |
| 11 | `app/proprietary/.../security/InitialSecuritySetup.java` | Yes | 硬编码凭据（问题 #6） |
| 12 | `app/proprietary/.../configuration/SecurityConfiguration.java` | Yes | CSRF+CORS+Cookie（问题 #1）；速率限制（问题 #7）；HttpFirewall（问题 #8） |
| 13 | `app/proprietary/.../controller/api/DatabaseController.java` | Yes | 无独立问题 |
| 14 | `app/proprietary/.../service/DatabaseService.java` | Yes | 无独立问题 |
| 15 | `app/proprietary/.../util/DesktopClientUtils.java` | Yes | 无独立问题 |
| 16 | `app/core/.../misc/ExtractImageScansController.java` | Yes | 无独立问题 |
| 17 | `app/common/.../util/PDFToFile.java` | Yes | 无独立问题 |
| 18 | `app/core/.../pipeline/PipelineProcessor.java` | Yes | 无独立问题 |

**覆盖率**: 18/18 (100%)

---

## 六、严重度确认清单

### 步骤 1: 检查严重度锁定

- [x] `disableSanitize` 问题标记为 HIGH? -- **是**（问题 #2）
- [x] `allowedOriginPatterns("*")` + `allowCredentials(true)` 标记为 HIGH? -- **是**（问题 #1 组合的一部分）
- [x] `Path.resolve(userInput)` 无验证标记为 HIGH? -- **是**（问题 #3）
- [x] 硬编码管理员凭据标记为 MEDIUM? -- **是**（问题 #6）
- [x] SSRF 未验证内网 IP 标记为 MEDIUM? -- **是**（问题 #4）
- [x] `SAXSVGDocumentFactory` 未禁用外部实体标记为 MEDIUM? -- **是**（问题 #5）
- [x] 速率限制禁用标记为 MEDIUM? -- **是**（问题 #7 组合的一部分）
- [x] 所有 MD5/SHA1 作为独立 LOW 问题报告? -- **是**（问题 #9）
- [x] HttpFirewall 换行符标记为 LOW? -- **是**（问题 #8）

### 步骤 2: 检查组合漏洞

- [x] CSRF 禁用 + CORS `*` + `allowCredentials=true` + Cookie 认证合并为 1 个 HIGH? -- **是**（问题 #1）
- [x] CSRF 禁用 + 速率限制禁用合并为 1 个 MEDIUM? -- **是**（问题 #7）

### 步骤 3: 检查问题合并

- [x] 同一配置影响多个文件合并为 1 个问题? -- **是**（`disableSanitize` 影响 3 个净化器文件 = 问题 #2）
- [x] 不同配置导致相同漏洞分开报告? -- **是**（SSRF 和 XXE 是不同配置导致的独立问题）

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
- [x] MD5/SHA1 已作为独立 LOW 问题报告（V7 新增）

---

## 八、各维度详细分析

### 维度 1: SQL 注入 (SQLi)

**结论: 未发现**

- `DatabaseService.java` 全程使用 `PreparedStatement` 参数化查询（`RUNSCRIPT FROM ?`、`SCRIPT SIMPLE COLUMNS DROP to ?`）
- SQL 导入功能实施了白名单 + 黑名单双重验证机制
- `ALLOWED_PATTERNS` 白名单仅允许标准 DDL/DML 操作
- `DENIED_PATTERNS` 黑名单阻止危险函数（`FILE_READ`、`FILE_WRITE`、`CSVREAD`、`CSVWRITE`、`RUNSCRIPT` 等）
- `stripStringLiterals()` 方法在检查前剥离字符串字面量，防止绕过

### 维度 2: 跨站脚本 (XSS)

**结论: 发现 HIGH**

- `CustomHtmlSanitizer.java` 使用 OWASP HTML Sanitizer 进行净化，但 `disableSanitize` 开关可完全绕过
- `SvgSanitizer.java` 有完善的危险元素/属性清理逻辑，但同样受 `disableSanitize` 控制
- `StampController.java` 的印章文本直接渲染到 PDF，不经过 HTML 处理，无 XSS 风险
- 详见问题 #2

### 维度 3: XML 外部实体 (XXE)

**结论: 发现 MEDIUM**

- `SvgSanitizer.parseSecurely()` 正确设置了所有 XXE 防护特性
- `OfficeDocumentSanitizer.parseSecurely()` 同样正确配置
- `SvgOverlayUtil.java` 使用 `SAXSVGDocumentFactory` 但未设置 XXE 防护特性，仅依赖 Batik UserAgent 层面的资源加载阻止
- 详见问题 #5

### 维度 4: 路径遍历 (Path Traversal)

**结论: 发现 HIGH**

- `FileOrUploadService.resolveFilePath()` 直接将用户输入传递给 `Path.resolve()`，无任何验证
- `DatabaseService.getBackupFilePath()` 正确实施了路径遍历检查（`filePath.startsWith(BACKUP_DIR)`）
- `DatabaseController.downloadFile()` 验证文件名格式（`backup_*.sql`）
- `StampController` 检查文件名中的 `..` 和 `/`
- `PipelineProcessor.generateInputFiles()` 检查路径遍历
- 详见问题 #3

### 维度 5: 命令注入 (Command Injection)

**结论: 未发现**

- `ProcessExecutor` 使用 `ProcessBuilder`（非 shell 执行），命令参数以列表形式传递
- `validateCommand()` 方法验证：空字节、换行符、路径遍历
- `ConvertWebsiteToPDF` 的 WeasyPrint 命令参数来自配置和临时文件路径
- `ExtractImageScansController` 的 Python 命令参数来自请求参数，但以列表元素传递
- `CompressController` 的 Ghostscript/QPDF 命令参数来自内部逻辑

### 维度 6: 服务端请求伪造 (SSRF)

**结论: 发现 MEDIUM**

- `ConvertWebsiteToPDF.fetchRemoteHtml()` 直接请求用户提供的 URL，无内网 IP 验证
- URL 验证仅检查格式和可达性，不检查目标 IP 范围
- `file:` scheme 被正确阻止
- `CustomHtmlSanitizer` 和 `SvgSanitizer` 使用 `SsrfProtectionService` 进行 URL 验证
- 详见问题 #4

### 维度 7: 文件上传 (File Upload)

**结论: 未发现**

- `StampController` 验证文件名不含 `..` 和 `/`
- `ImageIO.read()` 安全读取图像数据
- `DatabaseController` 使用 `Files.createTempFile()` 安全处理上传文件
- `ZipSecurity.createHardenedInputStream()` 在 `OfficeDocumentSanitizer` 中防止 Zip Bomb
- `PDFToFile` 使用 `Filenames.toSimpleFileName()` 清理文件名

### 维度 8: 硬编码密钥/凭据 (HardcodedSecret)

**结论: 发现 MEDIUM + LOW**

- `InitialSecuritySetup.createDefaultAdminUser()` 硬编码 `admin/stirling`
- `CredentialEncryption` 正确从配置/环境变量/密钥文件获取密钥，支持 AES-256-GCM
- `CompressController.generateMD5()` 使用 MD5 哈希（详见问题 #9）
- `DatabaseService.verifyBackup()` 使用 SHA-256（安全）

### 维度 9: CSRF

**结论: 发现 HIGH（作为组合漏洞的一部分）**

- `SecurityConfiguration` 第 269 行完全禁用 CSRF: `http.csrf(CsrfConfigurer::disable)`
- 所有状态变更操作（POST/PUT/DELETE）均无 CSRF 保护
- 与 CORS `*` + `allowCredentials(true)` + Cookie 认证组合为 HIGH

### 维度 10: CORS

**结论: 发现 HIGH（作为组合漏洞的一部分）**

- 默认配置: `cfg.setAllowedOriginPatterns(List.of("*"))`
- 凭证允许: `cfg.setAllowCredentials(true)`
- 支持配置自定义来源，但默认为全开
- 与 CSRF 禁用 + Cookie 认证组合为 HIGH

### 维度 11: 认证 (Auth)

**结论: 发现 MEDIUM**

- 默认管理员凭据 `admin/stirling` 硬编码
- `CredentialEncryption` 实现正确（AES-256-GCM，SecureRandom IV，密钥文件权限 0600）
- JWT 认证过滤器正确配置
- `DesktopClientUtils` 基于 User-Agent 检测桌面客户端，授予更长 token 有效期（合理设计）

### 维度 12: 会话管理 (Session)

**结论: 未发现**

- 主安全链使用 `SessionCreationPolicy.STATELESS`
- SAML 链使用 `SessionCreationPolicy.IF_REQUIRED`（合理）
- Remember-me 配置安全: `useSecureCookie(true)`，14 天有效期
- 注销时正确清除 Cookie: `deleteCookies("JSESSIONID", "remember-me", "stirling_jwt")`
- 使用 `NullRequestCache` 防止请求缓存泄露

### 维度 13: HttpFirewall

**结论: 发现 LOW**

- Header 值正确排除控制字符: `[\\p{IsAssigned}&&[^\\p{IsControl}]]*`
- 参数值显式允许 `\r\n`: `[\\p{IsAssigned}&&[^\\p{IsControl}]\\r\\n]*`
- 这与 `StrictHttpFirewall` 的默认行为不一致，存在 HTTP 响应拆分/请求走私风险
- 详见问题 #8

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Nu
**评审标准**: V7 (标准化评审指令)
