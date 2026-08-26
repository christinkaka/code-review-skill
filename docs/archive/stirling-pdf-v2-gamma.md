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
- **描述**: 默认管理员凭据 `admin/stirling` 硬编码在源代码中。当未配置 `initialLogin` 用户名和密码时，系统会自动创建使用硬编码凭据的管理员账户。攻击者可直接使用 `admin:stirling` 登录系统获取管理员权限，导致完全控制应用。虽然设置了 `firstLogin=true` 标记，但这仅是应用层面的提示，不阻止 API 访问，且密码在源代码中公开可见。
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
        log.info("Default admin user created: {}", defaultUsername);
    }
}
```
- **修复建议**: 移除硬编码的默认凭据。在首次启动时强制要求用户设置管理员密码，或从环境变量/密钥管理服务中读取初始凭据。若必须提供默认值，应生成随机密码并输出到安全日志或控制台，强制用户首次登录时修改。

---

### 问题 2
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 269
- **严重度**: HIGH
- **类型**: CSRF
- **描述**: CSRF 保护被全局禁用 (`http.csrf(CsrfConfigurer::disable)`)。该应用同时支持基于 Cookie 的表单登录和 Remember-Me 功能（第 337-351 行配置了 `rememberMeConfigurer`），这些均依赖 Cookie 进行身份验证，因此容易受到 CSRF 攻击。攻击者可以构造恶意页面，以已认证用户的身份发起状态变更请求（如修改密码、导入数据库等）。虽然 API 端点使用 JWT（STATELESS 会话策略），但表单登录端点 `/perform_login` 和 `/logout` 仍使用 Cookie 认证，禁用 CSRF 对这些端点构成直接威胁。
- **代码片段**:
```java
http.csrf(CsrfConfigurer::disable);
```
- **修复建议**: 不应全局禁用 CSRF。对于 JWT 认证的 API 端点，可通过 `CsrfConfigurer.ignoringRequestMatchers()` 仅对 `/api/**` 路径禁用 CSRF，同时保留对表单登录和基于 Cookie 的端点的 CSRF 保护。

---

### 问题 3
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 188, 218
- **严重度**: HIGH
- **类型**: CORS
- **描述**: 当未在 `settings.yml` 中配置 `system.corsAllowedOrigins` 时，CORS 默认允许所有来源 (`*`)，同时设置了 `allowCredentials=true`（第 218 行）。`allowedOriginPatterns=*` 与 `allowCredentials=true` 的组合允许任意第三方网站携带用户凭证（Cookie、Authorization 头）发起跨域请求，可导致跨域数据窃取。虽然现代浏览器会拒绝 `Origin: *` + `allowCredentials: true` 的组合，但 `setAllowedOriginPatterns("*")` 会将请求的 Origin 回显，从而绕过浏览器限制。
- **代码片段**:
```java
// 第 188 行：默认允许所有来源
cfg.setAllowedOriginPatterns(List.of("*"));
log.info("No CORS allowed origins configured in settings.yml"
        + " (system.corsAllowedOrigins); allowing all origins.");

// 第 218 行：允许携带凭证
cfg.setAllowCredentials(true);
```
- **修复建议**: 移除通配符默认值。当未配置 CORS 来源时，应默认拒绝所有跨域请求或仅允许同源请求。要求管理员在 `settings.yml` 中显式配置受信任的来源列表。绝不应将 `*` 与 `allowCredentials=true` 组合使用。

---

### 问题 4
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath` 方法直接将用户提供的 `fileId` 参数传递给 `Path.resolve()` 而没有任何路径穿越检查。攻击者可传入 `../../etc/passwd` 或 `../../../etc/shadow` 等值来读取服务器上的任意文件。没有对解析后的路径进行 `normalize()` 处理，也没有验证结果路径是否仍在 `tempDirPath` 目录下（缺少 `startsWith()` 检查）。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```
- **修复建议**: 对 `fileId` 进行路径净化处理：(1) 提取文件名部分 (`Path.of(fileId).getFileName()`)；(2) 对解析后的路径调用 `normalize()` 并验证 `startsWith(Path.of(tempDirPath))`；(3) 拒绝包含 `..`、`/`、`\` 的输入。

---

### 问题 5
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 88-91, 175-200
- **严重度**: MEDIUM
- **类型**: SSRF
- **描述**: URL 验证逻辑不完整，存在 SSRF 风险。首先，URL 有效性检查使用 OR 逻辑（第 91 行），只要 regex 或 `GeneralUtils.isValidURL()` 任一通过即可，降低了验证强度。其次，`fetchRemoteHtml` 方法（第 175-200 行）使用 `HttpClient` 直接请求用户提供的 URL，虽然禁用了重定向跟随（`Redirect.NEVER`），但未验证目标 IP 地址，攻击者可通过 DNS 重绑定或使用指向内网 IP（如 `http://127.0.0.1`、`http://169.254.169.254`、`http://10.0.0.x`）的 URL 访问内部服务。此外，仅检查了 `file:` scheme，未阻止其他危险 scheme。
- **代码片段**:
```java
// 第 88-91 行：OR 逻辑降低了验证强度
boolean patternValid =
        RegexPatternUtils.getInstance().getHttpUrlPattern().matcher(URL).matches();
boolean generalValid = GeneralUtils.isValidURL(URL);
if (!patternValid && !generalValid) {
    // 拒绝...
}

// 第 176-180 行：直接请求用户 URL，无内网 IP 验证
HttpClient client =
        HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NEVER)
                .connectTimeout(Duration.ofSeconds(10))
                .build();
```
- **修复建议**: (1) 将 URL 验证改为 AND 逻辑，要求同时通过 regex 和通用验证；(2) 在请求前解析 URL 的主机名，验证其 IP 地址不属于私有网段（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、127.0.0.0/8、169.254.0.0/16）；(3) 仅允许 `http:` 和 `https:` scheme。

---

### 问题 6
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 35-36
- **严重度**: MEDIUM
- **类型**: XXE
- **描述**: `SAXSVGDocumentFactory` 在创建时未配置 XXE 防护。与 `SvgSanitizer.java` 和 `OfficeDocumentSanitizer.java` 中完善的 XML 安全配置不同，此处直接创建了 `SAXSVGDocumentFactory` 而未在底层 SAX 解析器上设置 `FEATURE_SECURE_PROCESSING`、禁用外部实体等安全特性。虽然第 43-56 行通过自定义 `UserAgent` 阻止了外部资源加载（提供了部分缓解），但 XML 解析器层面仍可能处理外部实体，存在信息泄露风险。
- **代码片段**:
```java
String parser = XMLResourceDescriptor.getXMLParserClassName();
SAXSVGDocumentFactory factory = new SAXSVGDocumentFactory(parser);
// 未设置任何 XXE 防护特性
```
- **修复建议**: 在创建 `SAXSVGDocumentFactory` 后，通过其底层解析器设置安全特性：禁用 `DOCTYPE` 声明、禁用外部通用实体和外部参数实体。可参考 `SvgSanitizer.parseSecurely()` 中的实现方式。

---

### 问题 7
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/service/DatabaseService.java`
- **行号**: 489-514, 523-571
- **严重度**: MEDIUM
- **类型**: SQLi
- **描述**: 数据库备份导入功能执行用户上传的 SQL 文件。虽然实现了 SQL 内容验证（拒绝模式 + 允许模式双重检查），但验证逻辑存在可绕过的缺陷：(1) 允许模式按分号分割语句后逐一匹配，但 SQL 值内部可能包含分号（即使在字符串字面量剥离后），导致合法语句被错误分割；(2) `stripStringLiterals` 使用简单正则 `'([^']|'')*'` 来移除字符串字面量，但可能被编码技巧绕过；(3) H2 数据库的 `RUNSCRIPT` 以完全权限执行，一旦验证被绕过，攻击者可获得数据库完全控制权。`DatabaseController` 要求 ADMIN 角色限制了攻击面，但仍构成权限提升风险。
- **代码片段**:
```java
// 第 541-555 行：按分号分割的允许模式检查
String[] statements = normalizedContent.split(";");
for (String statement : statements) {
    statement = statement.trim();
    if (statement.isEmpty()) continue;
    boolean isAllowed = false;
    for (Pattern allowedPattern : ALLOWED_PATTERNS) {
        if (allowedPattern.matcher(statement).find()) {
            isAllowed = true;
            break;
        }
    }
    if (!isAllowed) {
        throw new IllegalArgumentException(
                "SQL script contains unrecognized or disallowed SQL statements.");
    }
}
```
- **修复建议**: (1) 使用更健壮的 SQL 解析器而非简单的正则表达式和分号分割；(2) 考虑在受限的数据库用户权限下执行导入；(3) 仅允许通过应用自身的备份机制生成的文件进行导入（验证文件签名或校验和）；(4) 在独立的临时数据库实例中验证导入结果后再应用到生产数据库。

---

### 问题 8
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 64-66
- **严重度**: MEDIUM
- **类型**: XSS
- **描述**: `disableSanitize` 配置项可完全绕过 OWASP HTML 净化器。当 `applicationProperties.getSystem().isDisableSanitize()` 返回 `true` 时，用户输入的 HTML 将原样返回，不经过任何净化处理。攻击者可注入任意 JavaScript 代码（如 `<script>alert(1)</script>`、`<img onerror=...>`），导致存储型或反射型 XSS 攻击。同样的 `disableSanitize` 旁路也存在于 `SvgSanitizer.java`（第 59 行）和 `OfficeDocumentSanitizer.java`（第 80 行），形成系统性的安全弱点。
- **代码片段**:
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```
- **修复建议**: (1) 移除 `disableSanitize` 选项，或将其限制为仅在开发/测试环境中可用（通过 `@Profile("dev")` 注解）；(2) 如果必须保留，应增加额外的安全控制，如要求管理员权限才能修改此配置，并在启用时记录安全审计日志。

---

### 问题 9
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/util/DesktopClientUtils.java`
- **行号**: 34-51
- **严重度**: MEDIUM
- **类型**: Auth
- **描述**: 桌面客户端检测完全依赖 `User-Agent` 请求头，该值由客户端控制，可被任意伪造。攻击者只需在请求中设置 `User-Agent: Tauri` 或 `User-Agent: Electron`，即可获得桌面客户端的延长令牌过期时间（默认 30 天，而 Web 客户端通常短得多）。这允许攻击者在窃取短期令牌后，通过伪造 User-Agent 获取长期有效的凭证，显著增加了令牌泄露的影响范围。
- **代码片段**:
```java
public static boolean isDesktopClient(HttpServletRequest request) {
    String userAgent = request.getHeader("User-Agent");
    if (userAgent == null) return false;
    String userAgentLower = userAgent.toLowerCase();
    boolean hasTauri = userAgentLower.contains("tauri");
    boolean hasStirling = userAgentLower.contains("stirlingpdf-desktop");
    boolean hasElectron = userAgentLower.contains("electron");
    boolean isDesktop = hasTauri || hasStirling || hasElectron;
    return isDesktop;
}
```
- **修复建议**: 不应仅依赖 User-Agent 进行安全决策。可结合其他信号进行综合判断，如自定义请求头（需桌面客户端使用固定密钥签名）、客户端证书、或 OAuth 客户端凭据流等更可靠的桌面认证方式。

---

### 问题 10
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java`
- **行号**: 106-108
- **严重度**: LOW
- **类型**: PathTraversal
- **描述**: PDF 文件名和图片文件名的路径穿越检查不完整，仅检查了 `..` 和以 `/` 开头的情况，未检查反斜杠 `\`（Windows 路径分隔符）。不过，经分析 `pdfFileName` 仅用于响应头的文件名生成（第 209 行 `GeneralUtils.generateFilename()`），不用于文件系统操作，因此实际风险有限。
- **代码片段**:
```java
if (pdfFileName.contains("..") || pdfFileName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(
            "error.invalid.filepath", "Invalid PDF file path: " + pdfFileName);
}
```
- **修复建议**: 补充反斜杠检查 `pdfFileName.contains("\\")`，或使用 `io.github.pixee.security.Filenames.toSimpleFileName()` 进行完整的文件名净化（项目中其他位置已使用此方法）。

---

### 问题 11
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 742-748
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: 使用 MD5 哈希算法生成图像标识哈希值。MD5 已被证实存在碰撞漏洞，不应用于安全敏感场景。不过在此场景中，MD5 仅用于图像去重标识（`ImageIdentity` 类），不涉及密码存储或完整性验证，因此安全风险较低。
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
- **修复建议**: 考虑使用 SHA-256 替代 MD5 作为图像哈希算法，以遵循密码学最佳实践。由于此处不涉及安全认证，当前风险可接受。

---

### 问题 12
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/security/configuration/SecurityConfiguration.java`
- **行号**: 477-479
- **严重度**: LOW
- **类型**: Auth
- **描述**: IP 速率限制过滤器被配置为极高的限制值（1,000,000 次请求），实质上等同于无限制。代码注释（第 299-303 行）明确指出该过滤器已被禁用（"TODO: IPRateLimitingFilter disabled"），且由于 Spring Security 异步调度 bug 而未注册到过滤器链中。这使得应用缺乏有效的暴力破解防护和 DDoS 缓解能力。
- **代码片段**:
```java
@Bean
public IPRateLimitingFilter rateLimitingFilter() {
    // Example limit TODO add config level
    int maxRequestsPerIp = 1000000;
    return new IPRateLimitingFilter(maxRequestsPerIp, maxRequestsPerIp);
}
```
- **修复建议**: (1) 将速率限制配置化，允许管理员设置合理的限制值（如每分钟 60 次）；(2) 修复 Spring Security 异步调度 bug，重新启用速率限制过滤器；(3) 对登录端点实施更严格的速率限制。

---

## 未发现问题

以下维度在审查的 18 个文件中未发现安全问题：

### 命令注入 (Command Injection)
- `ProcessExecutor.java` 使用 `ProcessBuilder` 与列表参数（非 `shell=True`），避免了 shell 注入。
- `validateCommand()` 方法（第 491-538 行）对命令参数进行了全面验证：检查 null 字节、换行符、路径穿越，并验证可执行文件的存在性。
- 所有命令（WeasyPrint、Ghostscript、QPDF、pdftohtml、LibreOffice、Python/OpenCV）均通过列表方式构建，用户输入仅作为独立参数传入，不存在拼接注入的可能。

### 不安全的文件上传/下载 (FileUpload)
- `DatabaseController.java` 的 `downloadFile` 方法（第 197 行）验证了文件名模式（`backup_*.sql`）。
- `DatabaseService.java` 的 `getBackupFilePath` 方法（第 477-481 行）包含路径穿越检查（`startsWith(BACKUP_DIR)`）。
- `DatabaseService.java` 的 `isValidFileName` 方法（第 600-612 行）对文件名进行了特殊字符过滤。
- `PDFToFile.java` 使用 `Filenames.toSimpleFileName()` 净化文件名。
- `PipelineProcessor.java` 的 `generateInputFiles` 方法（第 346-349 行）检查了路径穿越。

### 会话管理 (Session)
- `SecurityConfiguration.java` 配置了合理的会话管理策略：API 使用 `STATELESS`，SAML 使用 `IF_REQUIRED`。
- Remember-Me 令牌有效期为 14 天（第 341-342 行），在合理范围内。
- 会话注销逻辑完整（第 323-336 行），清除了认证信息、使会话失效、删除了相关 Cookie。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 5 |
| LOW | 3 |
| **总计** | **12** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| SQLi | 1 |
| XSS | 1 |
| XXE | 1 |
| PathTraversal | 2 |
| CommandInjection | 0 |
| SSRF | 1 |
| FileUpload | 0 |
| HardcodedSecret | 2 |
| CSRF | 1 |
| CORS | 1 |
| Auth | 2 |
| Session | 0 |

---

## 正面发现

1. **完善的 XML 安全配置**: `SvgSanitizer.java` 和 `OfficeDocumentSanitizer.java` 中的 XML 解析器均配置了全面的 XXE 防护，包括禁用 DOCTYPE 声明、外部通用实体、外部参数实体和外部 DTD 加载。

2. **安全的命令执行架构**: `ProcessExecutor.java` 采用了安全的命令执行模式：使用 `ProcessBuilder` 列表参数避免 shell 注入，`validateCommand()` 方法对命令参数进行全面验证，信号量机制控制并发执行，超时保护防止进程挂起。

3. **高质量的加密实现**: `CredentialEncryption.java` 使用 AES-256-GCM（认证加密），密钥管理支持配置、环境变量和自动生成三种方式，自动生成的密钥文件设置了 0600 权限（仅所有者可读写），使用 `SecureRandom` 生成 IV。

4. **SVG 安全处理**: `SvgSanitizer.java` 实现了全面的 SVG 净化：移除危险元素（script、foreignObject、iframe 等）、移除事件处理属性（on* 属性）、检测 JavaScript/data URI、结合 SSRF 保护服务验证 URL。

5. **Office 文档净化**: `OfficeDocumentSanitizer.java` 对 OOXML/ODF 文档进行 zip 安全处理（使用 `ZipSecurity.createHardenedInputStream` 防止 zip 炸弹），剥离外部关系引用防止 SSRF。

6. **SQL 注入防御**: `DatabaseService.java` 使用 `PreparedStatement` 进行参数化查询（第 297 行、第 502-504 行），并对导入的 SQL 文件实施了拒绝模式 + 允许模式双重验证。

7. **文件名净化**: 多处使用了 `io.github.pixee.security.Filenames.toSimpleFileName()` 进行文件名净化（`PDFToFile.java`、`PipelineProcessor.java`），`ConvertWebsiteToPDF.java` 中对 URL 转文件名的处理也非常严格。

8. **备份文件路径保护**: `DatabaseService.getBackupFilePath()` 实现了路径穿越检测（`normalize()` + `startsWith()` 验证），`isValidFileName()` 过滤了多种特殊字符。

---

## 关键风险总结

1. **[CRITICAL] 硬编码默认管理员凭据** (`InitialSecuritySetup.java:154-155`): 默认管理员密码 `stirling` 硬编码在源代码中，任何能访问源码的攻击者均可获取管理员权限。这是最直接、最易利用的高危漏洞。

2. **[HIGH] CSRF 保护全局禁用** (`SecurityConfiguration.java:269`): 在存在基于 Cookie 认证（表单登录 + Remember-Me）的情况下全局禁用 CSRF，使得攻击者可以已认证用户身份执行任意操作（包括数据库导入等高危操作）。

3. **[HIGH] CORS 配置允许所有来源 + 凭证** (`SecurityConfiguration.java:188,218`): 默认的 `allowedOriginPatterns=*` 与 `allowCredentials=true` 组合，允许任意网站发起携带用户凭证的跨域请求，可导致数据窃取。

4. **[HIGH] 路径穿越漏洞** (`FileOrUploadService.java:21`): `resolveFilePath()` 方法直接使用用户输入解析文件路径，无任何穿越检查，可读取服务器任意文件。

5. **[MEDIUM] 安全净化可被配置绕过** (`CustomHtmlSanitizer.java:64-66`, `SvgSanitizer.java:59`, `OfficeDocumentSanitizer.java:80`): `disableSanitize` 配置项可完全禁用 HTML/SVG/Office 文档的安全净化，形成系统性的安全弱点，一旦启用将暴露于 XSS 和 SVG-based 攻击。

---

## 评审检查清单

- [x] 已检查所有 12 个评审维度
- [x] 已审查文件清单中的所有 18 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段
- [x] 所有问题都使用了统一的严重度判定标准
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合要求

---

**评审完成时间**: 2026-08-12
**评审者**: Agent Gamma
