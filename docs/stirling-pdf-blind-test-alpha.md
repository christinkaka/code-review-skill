# Agent Alpha 独立评审报告 - Stirling-PDF

**评审日期**: 2026-08-12
**评审范围**: `test-stirling-pdf/` 项目 `app/core`, `app/common`, `app/proprietary`, `app/saas` 模块下的核心业务 Java 代码
**评审重点**: 安全问题 (SQLi, XSS, XXE, Path Traversal, Command Injection, SSRF, 不安全的文件上传/下载, 硬编码密钥/密码)
**评审文件数**: ~50 个核心 Java 文件 (controller, service, util 目录)

---

## 发现的问题

### 问题 1
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 20-21
- **严重度**: HIGH
- **类型**: PathTraversal
- **描述**: `resolveFilePath(String fileId)` 方法将用户提供的 `fileId` 直接通过 `Path.of(tempDirPath).resolve(fileId)` 拼接到基础目录路径中，未做任何路径穿越检查。攻击者可传入 `../../etc/passwd` 等值，使解析后的路径逃逸出 `tempDirPath` 目录，读取或操作服务器上的任意文件。
- **代码片段**:
```java
public Path resolveFilePath(String fileId) {
    return Path.of(tempDirPath).resolve(fileId);
}
```
- **修复建议**: 对 `fileId` 进行规范化后校验其是否仍在 `tempDirPath` 目录下：
```java
public Path resolveFilePath(String fileId) {
    Path base = Path.of(tempDirPath).toAbsolutePath().normalize();
    Path resolved = base.resolve(fileId).toAbsolutePath().normalize();
    if (!resolved.startsWith(base)) {
        throw new IllegalArgumentException("Invalid file ID");
    }
    return resolved;
}
```

---

### 问题 2
- **文件**: `app/common/src/main/java/stirling/software/common/util/CustomHtmlSanitizer.java`
- **行号**: 64-66
- **严重度**: HIGH
- **类型**: XSS
- **描述**: `sanitize()` 方法通过 `applicationProperties.getSystem().isDisableSanitize()` 配置项允许完全绕过 HTML 净化。当 `disableSanitize` 设为 `true` 时，用户提交的 HTML（包括 HTML-to-PDF 转换、EML-to-PDF 转换等场景）将不做任何 XSS 过滤直接处理。若此配置在生产环境被启用（例如为了处理特殊 HTML），所有经过 WeasyPrint 渲染的 HTML 内容中的恶意 `<script>`、`onerror` 等 XSS 载荷将被执行。
- **代码片段**:
```java
public String sanitize(String html) {
    boolean disableSanitize = applicationProperties.getSystem().isDisableSanitize();
    return disableSanitize ? html : POLICY.sanitize(html);
}
```
- **修复建议**: 移除此全局开关，或将其限制为仅在明确标记为内部/受信输入时使用。对于所有外部用户输入，应始终执行 HTML 净化。

---

### 问题 3
- **文件**: `app/common/src/main/java/stirling/software/common/util/SvgSanitizer.java`
- **行号**: 59
- **严重度**: HIGH
- **类型**: XSS
- **描述**: 与问题 2 相同模式的 `disableSanitize` 绕过也存在于 `SvgSanitizer` 中。SVG 文件可嵌入 `<script>` 标签和事件处理器，当净化被禁用时，恶意 SVG 内容可在 PDF 渲染过程中触发 XSS。
- **代码片段**:
```java
if (applicationProperties.getSystem().isDisableSanitize()) {
    // 直接返回原始 SVG，跳过净化
}
```
- **修复建议**: 同问题 2。

---

### 问题 4
- **文件**: `app/common/src/main/java/stirling/software/common/util/OfficeDocumentSanitizer.java`
- **行号**: 80
- **严重度**: MEDIUM
- **类型**: XSS
- **描述**: `OfficeDocumentSanitizer` 同样受 `disableSanitize` 配置影响。当禁用净化时，Office 文档（如 DOCX）中嵌入的恶意宏或脚本内容可能不被清理。
- **代码片段**:
```java
if (applicationProperties.getSystem().isDisableSanitize()) {
    // 跳过 Office 文档净化
}
```
- **修复建议**: 同问题 2，应始终对用户上传的 Office 文档进行安全净化。

---

### 问题 5
- **文件**: `app/core/src/main/java/stirling/software/SPDF/utils/SvgOverlayUtil.java`
- **行号**: 31-95
- **严重度**: MEDIUM
- **类型**: CommandInjection (DoS)
- **描述**: `overlaySvgOnPage()` 方法在处理用户提供的 SVG 时缺少渲染超时保护。对比同项目的 `SvgToPdf.java`（第 47 行定义了 30 秒超时），`SvgOverlayUtil` 直接调用 `builder.build(ctx, svgDoc)` 而无任何超时机制。攻击者可提交极端复杂的 SVG（如包含数百万个嵌套元素或递归引用），导致服务器线程永久阻塞，形成拒绝服务攻击。
- **代码片段**:
```java
// SvgOverlayUtil.java - 无超时保护
GraphicsNode rootNode = builder.build(ctx, svgDoc);  // 可能无限阻塞

// 对比 SvgToPdf.java - 有超时保护
private static final int RENDERING_TIMEOUT_SECONDS = 30;
Future<GraphicsNode> future = executor.submit(buildTask);
return future.get(RENDERING_TIMEOUT_SECONDS, TimeUnit.SECONDS);
```
- **修复建议**: 参照 `SvgToPdf.java` 的实现，为 SVG 渲染添加超时保护。

---

### 问题 6
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/converters/ConvertWebsiteToPDF.java`
- **行号**: 136-143
- **严重度**: MEDIUM
- **类型**: SSRF
- **描述**: URL-to-PDF 转换中，虽然初始 URL 通过了 `isValidURL()` 和 `isURLReachable()` 检查，且 HTML 内容检查了 `file:` scheme，但 WeasyPrint 被调用时传入了 `--base-url` 参数（原始 URL）。WeasyPrint 在渲染过程中会解析 HTML 中的相对 URL（如 CSS `@import`、`<link>`、`<img src>`），并通过 `--base-url` 解析为绝对 URL 进行网络请求。虽然 `containsDisallowedUriScheme()` 检查了 `file:` scheme，但未检查 WeasyPrint 可能发出的 HTTP 请求是否指向内部网络。若攻击者控制的页面包含指向 `http://169.254.169.254/` (云元数据) 或其他内部服务的相对路径引用，WeasyPrint 可能在渲染时访问这些资源。
- **代码片段**:
```java
command.add(runtimePathConfig.getWeasyPrintPath());
command.add(tempHtmlInput.toString());
command.add("--base-url");
command.add(URL);  // 攻击者控制的 URL 作为 base URL
command.add("--pdf-forms");
command.add(tempOutputFile.toString());
```
- **修复建议**: 考虑在 WeasyPrint 执行环境中禁用网络访问（如使用 `--base-url` 指向本地文件，或通过网络命名空间限制），或在 HTML 净化阶段移除所有外部资源引用。

---

### 问题 7
- **文件**: `app/common/src/main/java/stirling/software/common/service/FileOrUploadService.java`
- **行号**: 17
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **描述**: `tempDirPath` 使用 `@Value("${stirling.tempDir:/tmp/stirling-files}")` 硬编码了默认临时目录路径 `/tmp/stirling-files`。在共享的 Linux 系统上，`/tmp` 目录可被其他用户写入，可能导致符号链接攻击或临时文件竞争条件。此外，路径通过配置属性暴露，可能被意外覆盖。
- **代码片段**:
```java
@Value("${stirling.tempDir:/tmp/stirling-files}")
private String tempDirPath;
```
- **修复建议**: 使用 Java 的 `Files.createTempDirectory()` 或系统属性 `java.io.tmpdir` 获取安全的临时目录，并对创建的临时文件设置严格的文件权限（如 0600）。

---

### 问题 8
- **文件**: `app/proprietary/src/main/java/stirling/software/proprietary/integration/crypto/CredentialEncryption.java`
- **行号**: 50-51, 62-69
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: 加密密钥可通过 Spring 属性 `stirling.security.credentialEncryptionKey` 直接配置。Spring 属性值可能出现在日志、错误堆栈、actuator endpoints 或配置管理工具中，导致密钥泄露。虽然代码也支持环境变量（更安全的方式），但属性配置方式仍然是一个风险点。
- **代码片段**:
```java
public CredentialEncryption(
    @Value("${stirling.security.credentialEncryptionKey:}") String configuredKey,
    @Value("${cluster.enabled:false}") boolean clusterEnabled) {
    this.configuredKey = configuredKey;
```
- **修复建议**: 优先使用环境变量或外部密钥管理服务（如 Vault）来提供加密密钥。若必须使用属性配置，确保该属性被标记为敏感（如使用 Spring Cloud Config 的 encryption），并在日志中脱敏。

---

### 问题 9
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/StampController.java`
- **行号**: 106-109
- **严重度**: LOW
- **类型**: PathTraversal
- **描述**: `addStamp()` 方法对文件名的路径穿越检查仅检测了 `..` 和以 `/` 开头的情况，但未覆盖反斜杠 `\`（Windows 路径分隔符）以及 URL 编码的变体。在跨平台部署场景下，这可能被绕过。
- **代码片段**:
```java
if (pdfFileName.contains("..") || pdfFileName.startsWith("/")) {
    throw ExceptionUtils.createIllegalArgumentException(
        "error.invalid.filepath", "Invalid PDF file path: " + pdfFileName);
}
```
- **修复建议**: 使用 `io.github.pixee.security.Filenames.toSimpleFileName()` 对文件名进行净化（项目中其他地方已使用此方法），或同时检查反斜杠。

---

### 问题 10
- **文件**: `app/common/src/main/java/stirling/software/common/util/ProcessExecutor.java`
- **行号**: 491-537
- **严重度**: LOW
- **类型**: CommandInjection
- **描述**: `validateCommand()` 方法对命令参数进行了基本验证（检查 null 字节、换行符、路径穿越），但对绝对路径的检查仅验证文件是否存在和是否可执行，未验证该可执行文件是否在允许的白名单中。若攻击者能通过其他漏洞（如路径穿越）在服务器上放置恶意可执行文件，且知道其路径，则可能通过构造绝对路径来执行。不过，当前代码中命令列表是由服务端代码构建的，用户输入仅作为文件路径参数（如 `tempInputFile.toString()`），因此实际风险较低。
- **代码片段**:
```java
private void validateCommand(List<String> command) {
    // ...
    if (executable.contains("/") || executable.contains("\\")) {
        Path execPath;
        try {
            execPath = Path.of(executable);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid executable path: " + executable, e);
        }
        if (!Files.exists(execPath)) {
            throw new IllegalArgumentException("Command executable does not exist: " + executable);
        }
        // 仅检查存在性，未检查是否在白名单中
    }
}
```
- **修复建议**: 添加可执行文件路径白名单，仅允许预定义路径下的程序被执行。

---

### 问题 11
- **文件**: `app/core/src/main/java/stirling/software/SPDF/controller/api/misc/CompressController.java`
- **行号**: 742-748
- **严重度**: LOW
- **类型**: HardcodedSecret (Weak Crypto)
- **描述**: `generateMD5()` 方法使用 MD5 算法生成图像哈希用于去重。虽然此处 MD5 仅用于内容去重而非安全目的，但使用弱哈希算法可能在特定场景下导致哈希碰撞，使不同图像被误判为相同图像。这属于代码质量问题而非直接安全漏洞。
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
- **修复建议**: 对于内容去重场景，可考虑使用更强的哈希算法（如 SHA-256）或至少使用带碰撞检测的方案。

---

## 正面发现

评审过程中也发现了以下安全最佳实践：

1. **SSRF 防护完善**: `SsrfProtectionService` 实现了多层级的 SSRF 防护（OFF/MEDIUM/MAX），包括私有 IP 范围检测、云元数据端点防护、DNS rebinding 防护等。
2. **ZIP Slip 防护**: `FileToPdf.java` 和 `ZipExtractionUtils.java` 均使用了 `ZipSecurity.createHardenedInputStream()` 和路径规范化检查来防止 ZIP Slip 攻击。
3. **命令注入防护**: `ProcessExecutor.validateCommand()` 对命令参数进行了 null 字节、换行符和路径穿越检查。
4. **外部 API 路径控制**: `ExternalApiPaths.resolve()` 实现了严格的路径解析控制，防止 SSRF 和路径逃逸。
5. **凭证加密**: `CredentialEncryption` 使用 AES-256-GCM 加密存储的集成凭证，密钥文件设置了 0600 权限。
6. **HTML 净化**: `CustomHtmlSanitizer` 默认使用 OWASP HTML Sanitizer 进行 HTML 净化，并结合 SSRF 安全的 URL 策略。
7. **SVG 外部资源阻止**: `SvgToPdf` 和 `SvgOverlayUtil` 均通过自定义 `UserAgent` 阻止 SVG 加载外部资源。
8. **重定向跟随禁用**: `ExternalApiCaller` 和 `ConvertWebsiteToPDF` 中的 HTTP 客户端均禁用了自动重定向跟随。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 4 |
| **总计** | **11** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| PathTraversal | 3 |
| XSS | 3 |
| SSRF | 1 |
| CommandInjection (DoS) | 1 |
| HardcodedSecret | 2 |
| Weak Crypto | 1 |

### 关键风险总结

1. **最高风险**: `disableSanitize` 全局配置开关（问题 2/3/4）允许绕过所有 HTML/SVG/Office 文档净化，若在生产环境被错误启用，将导致严重的 XSS 风险。
2. **路径穿越**: `FileOrUploadService.resolveFilePath()`（问题 1）直接将用户输入拼接到文件路径中，是经典的路径穿越漏洞模式。
3. **DoS 风险**: `SvgOverlayUtil`（问题 5）缺少渲染超时保护，可能被恶意 SVG 触发拒绝服务。
