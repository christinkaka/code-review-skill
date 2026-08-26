# 代码评审报告

**评审日期**: 2026-08-13
**评审项目**: YunaiV/ruoyi-vue-pro (yudao-module-infra)
**编程语言**: Java (Spring Boot)
**评审范围**: 15 个文件
**评审维度**: 13 个
**评审者**: Agent Alpha
**评审依据**: 标准化代码评审指令 V8 (多语言版)

---

## 评审范围文件清单

| 序号 | 文件路径 | 用途 |
|------|----------|------|
| 1 | `websocket/DemoWebSocketMessageListener.java` | WebSocket 消息监听器 |
| 2 | `framework/monitor/config/AdminServerConfiguration.java` | Spring Boot Admin 服务安全配置 |
| 3 | `framework/file/core/utils/FileTypeUtils.java` | 文件 MIME 类型识别 |
| 4 | `framework/file/core/utils/FilePathUtils.java` | 文件路径校验 |
| 5 | `framework/file/core/client/FileClientConfig.java` | 文件客户端配置接口 |
| 6 | `framework/file/core/client/ftp/FtpFileClientConfig.java` | FTP 客户端配置 |
| 7 | `framework/file/core/client/s3/S3FileClientConfig.java` | S3 客户端配置 |
| 8 | `framework/file/core/client/sftp/SftpFileClientConfig.java` | SFTP 客户端配置 |
| 9 | `framework/file/core/client/local/LocalFileClientConfig.java` | 本地文件客户端配置 |
| 10 | `framework/file/core/client/db/DBFileClientConfig.java` | DB 文件客户端配置 |
| 11 | `framework/file/config/YudaoFileAutoConfiguration.java` | 文件自动装配 |
| 12 | `framework/security/config/SecurityConfiguration.java` | Infra 模块安全配置 |
| 13 | `framework/web/config/InfraWebConfiguration.java` | Web/Swagger 配置 |
| 14 | `framework/codegen/config/CodegenConfiguration.java` | 代码生成配置 |
| 15 | `enums/config/ConfigTypeEnum.java` | 配置类型枚举 |

---

## 发现的问题

### 问题 1：Admin Server 默认凭据硬编码 (admin/admin)
- **文件**: `framework/monitor/config/AdminServerConfiguration.java`
- **行号**: 39-43
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **维度**: 8. 硬编码密钥/密码
- **描述**: Admin Server 用户名和密码使用 `@Value` 注解并设置默认值 `admin/admin`，如果运维未通过 `application.yml` 显式覆盖，将以默认弱凭据运行 Spring Boot Admin 监控端点。
- **代码片段**:
```java
@Value("${spring.boot.admin.client.username:admin}")
private String username;

@Value("${spring.boot.admin.client.password:admin}")
private String password;
```
- **修复建议**:
  1. 删除默认值，强制要求外部配置注入（`@Value("${spring.boot.admin.client.username}")`，无默认值）。
  2. 在 `@ConditionalOnProperty` 中校验关键属性是否已配置。
  3. 增加启动期日志告警，提示默认凭据风险。

---

### 问题 2：Admin Server Actuator 端点完全开放 (无认证)
- **文件**: `framework/security/config/SecurityConfiguration.java`
- **行号**: 27-28
- **严重度**: HIGH
- **类型**: Auth
- **维度**: 11. 认证授权
- **描述**: Infra 模块的 `SecurityConfiguration` 将 `/actuator` 与 `/actuator/**` 通过 `permitAll()` 全部放行，导致 Spring Boot Actuator 暴露的 `/env`、`/heapdump`、`/threaddump`、`/loggers`、`/metrics` 等敏感端点无需任何身份验证即可访问。结合 `AdminServerConfiguration` 的 CSRF `ignoringRequestMatchers(..., "/actuator/**")`，攻击者可远程读取环境变量（含数据库密码、Token 密钥）并获取 JVM 堆转储进行离线分析。
- **代码片段**:
```java
// Spring Boot Actuator 的安全配置
registry.requestMatchers("/actuator").permitAll()
        .requestMatchers("/actuator/**").permitAll();
```
- **修复建议**:
  1. 限制为白名单端点：`/actuator/health`、`/actuator/info` 等公开端点，其余端点强制 `authenticated()` 并要求 ADMIN 角色。
  2. 在 `application.yml` 中通过 `management.endpoints.web.exposure.include` 最小化暴露面，并禁用敏感端点 (`env`, `heapdump`, `threaddump`)。
  3. 对接公司统一身份认证（OAuth2/JWT）。

---

### 问题 3：Admin Server `/instances` 注册端点关闭 CSRF
- **文件**: `framework/monitor/config/AdminServerConfiguration.java`
- **行号**: 102-107
- **严重度**: MEDIUM
- **类型**: CSRF
- **维度**: 9. CSRF 保护
- **描述**: Admin Server 通过 `ignoringRequestMatchers` 对 `/instances` 与 `/actuator/**` 禁用 CSRF 保护。虽然 `/instances` 是 Admin Client 注册的接口，使用 HTTP Basic 认证，但 `csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())` 已将 CSRF Token 写入浏览器 Cookie，且 `/actuator/**` 已被全局放行（问题 2），从而放大了 CSRF 风险。攻击者可在管理员已登录 Admin UI 后构造跨站 POST 请求触发 Actuator 关闭/重启等高危操作。
- **代码片段**:
```java
.csrf(csrf -> csrf
        .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
        .ignoringRequestMatchers(
                adminSeverContextPath + "/instances",
                adminSeverContextPath + "/actuator/**"
        )
)
```
- **修复建议**:
  1. 仅对 `/instances` 单一精确路径关闭 CSRF（必须），不要连带 `/actuator/**`。
  2. `/instances` 注册要求使用独立 API Key（Spring Boot Admin 提供的 `spring.boot.admin.client.username/password` 之外的服务端 Access Token）。
  3. CSRF Token Cookie 设置 `HttpOnly=true`、`SameSite=Strict`。

---

### 问题 4：Admin Server CSP 配置包含 unsafe-inline 与 unsafe-eval
- **文件**: `framework/monitor/config/AdminServerConfiguration.java`
- **行号**: 109-118
- **严重度**: MEDIUM
- **类型**: XSS
- **维度**: 2. 跨站脚本 (XSS)
- **描述**: Content-Security-Policy 同时启用 `'unsafe-inline'` 和 `'unsafe-eval'`，几乎完全放弃了 CSP 对 XSS 的防护作用。即使 Admin UI 自身是受信脚本，也容易被攻击者通过 Actuator 端点（已 `permitAll`，见问题 2）注入内联脚本触发 XSS。
- **代码片段**:
```java
.contentSecurityPolicy(csp -> csp.policyDirectives(
        "default-src 'self'; "
                + "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                + "style-src 'self' 'unsafe-inline'; "
                + "frame-ancestors " + frameAncestors))
```
- **修复建议**:
  1. 移除 `'unsafe-eval'`，并为 Vue 生成的代码使用 nonce 或 hash 替代 `'unsafe-inline'`。
  2. 使用严格的 nonce-based CSP：`script-src 'self' 'nonce-{random}'`。
  3. 启用 Subresource Integrity（SRI）保护静态资源。

---

### 问题 5：Admin Server 路径匹配对空 context-path 退化为根路径
- **文件**: `framework/monitor/config/AdminServerConfiguration.java`
- **行号**: 36-37, 78, 83-97
- **严重度**: LOW
- **类型**: HttpFirewall
- **维度**: 13. HttpFirewall / 安全中间件
- **描述**: `adminSeverContextPath` 默认为 `""`（空字符串），导致 `securityMatcher("/**")` 实际匹配所有请求；`requestMatchers("/assets/**")` 也退化为匹配全站 `/assets/**`。当运维忘记配置 `spring.boot.admin.context-path` 时，Admin Server 的 SecurityFilterChain 会拦截整个应用而非仅 Admin 路径，造成意外的访问拒绝或与其他 FilterChain 的冲突。
- **代码片段**:
```java
@Value("${spring.boot.admin.context-path:''}")
private String adminSeverContextPath;
...
httpSecurity
        .securityMatcher(adminSeverContextPath + "/**")
```
- **修复建议**: 使用 `@ConditionalOnProperty(name = "spring.boot.admin.context-path")` 在未配置时禁用 Admin Server，或在启动时校验 `adminSeverContextPath` 非空。

---

### 问题 6：WebSocket 消息未做输入校验
- **文件**: `websocket/DemoWebSocketMessageListener.java`
- **行号**: 26-41
- **严重度**: LOW
- **类型**: XSS
- **维度**: 2. 跨站脚本 (XSS)
- **描述**: 监听器直接转发 `message.getText()` 与 `message.getToUserId()` 给前端，未对消息内容做长度限制、字符过滤或敏感词校验。攻击者可利用合法 WebSocket 会话发送超长消息（DoS）或在前端 `v-html` 渲染时触发 XSS。
- **代码片段**:
```java
DemoReceiveMessage toMessage = new DemoReceiveMessage().setFromUserId(fromUserId)
        .setText(message.getText()).setSingle(true);
```
- **修复建议**:
  1. 对 `text` 字段做长度上限（如 4 KB）与字符白名单校验。
  2. 配合前端使用纯文本渲染，避免在 Admin UI 中使用 `v-html`。

---

### 问题 7：FTP/SFTP 客户端明文密码字段未隐藏
- **文件**:
  - `framework/file/core/client/ftp/FtpFileClientConfig.java` (行 49-50)
  - `framework/file/core/client/sftp/SftpFileClientConfig.java` (行 49-50)
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **维度**: 8. 硬编码密钥/密码
- **描述**: `FtpFileClientConfig#password` 与 `SftpFileClientConfig#password` 字段未使用 `@JsonIgnore` 注解。结合 `FileClientConfig` 上的 `@JsonTypeInfo(use = JsonTypeInfo.Id.CLASS)`，当配置序列化为 JSON 存入数据库时，密码会以明文形式持久化，可被 DBA 或备份泄漏直接读取。
- **代码片段**:
```java
@NotEmpty(message = "密码不能为空")
private String password;
```
- **修复建议**:
  1. 在 `password` 字段上添加 `@JsonIgnore`（参考 `S3FileClientConfig#accessSecret` 同样建议添加）。
  2. 加密存储：使用 Jasypt 或公司 KMS 对敏感字段加密落库。
  3. 在响应 VO 中显式脱敏。

---

### 问题 8：S3 accessSecret 字段明文持久化
- **文件**: `framework/file/core/client/s3/S3FileClientConfig.java`
- **行号**: 67-68
- **严重度**: HIGH
- **类型**: HardcodedSecret
- **维度**: 8. 硬编码密钥/密码
- **描述**: `accessSecret` 字段缺少 `@JsonIgnore`，在 `FileClientConfig` 的 Jackson 多态序列化（`@JsonTypeInfo(use = JsonTypeInfo.Id.CLASS)`）下会以明文形式写入数据库。任何能访问数据库的运维/DBA/审计员均能拿到 S3 主密钥，从而获取对象存储完全控制权。
- **代码片段**:
```java
@NotNull(message = "accessSecret 不能为空")
private String accessSecret;
```
- **修复建议**:
  1. 添加 `@JsonIgnore`（与 `S3FileClientConfig` 内的 `isDomainValid` 同样已使用 `@JsonIgnore` 思路一致）。
  2. 在数据库存储时加密字段值，读取时使用专用解密 Bean。
  3. 审计日志记录 accessSecret 访问。

---

### 问题 9：Jackson 多态反序列化引入反序列化风险
- **文件**: `framework/file/core/client/FileClientConfig.java`
- **行号**: 11-15
- **严重度**: MEDIUM
- **类型**: HardcodedSecret
- **维度**: 8. 硬编码密钥/密码
- **描述**: `@JsonTypeInfo(use = JsonTypeInfo.Id.CLASS)` 启用了基于 `@class` 属性的 Jackson 多态反序列化。如果应用通过 HTTP 接口或消息中间件接收未受信的 JSON 输入并直接反序列化为 `FileClientConfig`，攻击者可通过构造 `@class: "org.springframework.context.support.ClassPathXmlApplicationContext"` 等 Gadget 链触发远程代码执行（RCE）。
- **代码片段**:
```java
@JsonTypeInfo(use = JsonTypeInfo.Id.CLASS)
public interface FileClientConfig {
}
```
- **修复建议**:
  1. 改用 `JsonTypeInfo.Id.NAME` + `JsonSubTypes` 显式枚举允许类型，避免任意类加载。
  2. 反序列化前对输入做严格白名单校验。
  3. 使用 Jackson `activateDefaultTyping` 时配置 `PolymorphicTypeValidator`。

---

### 问题 10：文件下载端点未做权限控制
- **文件**: `framework/security/config/SecurityConfiguration.java`
- **行号**: 32
- **严重度**: HIGH
- **类型**: Auth
- **维度**: 11. 认证授权
- **描述**: `/infra/file/*/get/**` 路径使用 `permitAll()` 放行，结合 `FileTypeUtils#writeAttachment` 直接通过 `response.getOutputStream()` 输出文件内容，可被未授权用户枚举访问私有文件。若攻击者猜测路径或从日志中获取 URL，可下载全部 `infra/file` 存储资源。
- **代码片段**:
```java
// 文件读取
registry.requestMatchers(buildAdminApi("/infra/file/*/get/**")).permitAll();
```
- **修复建议**:
  1. 默认要求鉴权，使用签名 URL（带过期时间 + HMAC 签名）。
  2. 公开文件应在数据库标记 `publicRead=true` 后才允许 `permitAll()`。
  3. 增加 Referer/Origin 校验防盗链。

---

### 问题 11：Druid 监控端点完全开放
- **文件**: `framework/security/config/SecurityConfiguration.java`
- **行号**: 30
- **严重度**: HIGH
- **类型**: Auth
- **维度**: 11. 认证授权
- **描述**: `/druid/**` 全部 `permitAll()`，Druid 监控默认会暴露 SQL 执行记录、Session 信息、Web 应用统计等敏感数据，且 Druid 历史漏洞（如配置注入、未授权访问）较多。
- **代码片段**:
```java
// Druid 监控
registry.requestMatchers("/druid/**").permitAll();
```
- **修复建议**:
  1. 仅在内网环境开放 `/druid/**`，公网必须要求 ADMIN 角色。
  2. 在 Druid `StatViewServlet` 中配置 `loginUsername/loginPassword` 与 `allow` IP 白名单。

---

### 问题 12：Swagger UI 与 API 文档完全开放
- **文件**: `framework/security/config/SecurityConfiguration.java`
- **行号**: 22-25
- **严重度**: MEDIUM
- **类型**: Auth
- **维度**: 11. 认证授权
- **描述**: Swagger UI、API 文档、WebJars 全部 `permitAll()`，暴露完整后端接口契约，攻击者可借此快速构造攻击向量并绕过鉴权盲测。
- **代码片段**:
```java
registry.requestMatchers("/v3/api-docs/**").permitAll()
        .requestMatchers("/webjars/**").permitAll()
        .requestMatchers("/swagger-ui.html").permitAll()
        .requestMatchers("/swagger-ui/**").permitAll();
```
- **修复建议**: 生产环境关闭 Swagger，或限制为 `dev/staging` profile 并要求 Basic 认证。

---

### 问题 13：HttpFirewall 未自定义配置
- **文件**: `framework/web/config/InfraWebConfiguration.java`
- **行号**: 1-23
- **严重度**: LOW
- **类型**: HttpFirewall
- **维度**: 13. HttpFirewall / 安全中间件
- **描述**: Infra 模块的 Web 配置仅注册了 Swagger GroupedOpenApi，未配置 `StrictHttpFirewall`，依赖框架默认行为。默认配置允许 URL 中包含分号/反斜杠，可能被攻击者用于绕过安全检测或触发 Tomcat 解析差异。
- **修复建议**: 在框架层显式注册 `StrictHttpFirewall` Bean，禁用 `allowSemicolon`、`allowUrlEncodedDoubleSlash`、`allowBackSlash`。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 (SQLi) | 已检查 | 无问题（本次范围无 SQL 代码） |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 4 (CSP unsafe-inline/eval)、问题 6 (WebSocket 文本) |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题（本次范围无 XML 解析代码） |
| 4. 路径穿越 | 已检查 | 无问题（`FilePathUtils.isPathValid` 实现完整，覆盖绝对路径/盘符/`..`/空段） |
| 5. 命令注入 | 已检查 | 无问题（本次范围无 `Runtime.exec` / `ProcessBuilder`） |
| 6. SSRF | 已检查 | 无问题（`@URL` 注解校验格式但未限制内网 IP，归入下一行说明） |
| 7. 文件上传/下载 | 已检查 | 问题 10（下载端点未授权） |
| 8. 硬编码密钥/密码 | 已检查 | 问题 1 (admin/admin)、问题 7 (FTP/SFTP password)、问题 8 (S3 accessSecret)、问题 9 (Jackson 多态) |
| 9. CSRF 保护 | 已检查 | 问题 3（Admin CSRF 关闭面过大） |
| 10. CORS 配置 | 已检查 | 无问题（本次范围未出现 CORS 配置；按 V8 锁定规则，未见 `allowedOriginPatterns("*")` + `allowCredentials(true)` 组合，不触发锁定 HIGH） |
| 11. 认证授权 | 已检查 | 问题 2 (Actuator)、问题 10 (文件下载)、问题 11 (Druid)、问题 12 (Swagger) |
| 12. 会话管理 | 已检查 | 无问题（本次范围未出现 Session/Token 配置） |
| 13. HttpFirewall | 已检查 | 问题 5（context-path 空值）、问题 13（未自定义 StrictHttpFirewall） |

### 维度补充说明

- **维度 6 SSRF**: `FtpFileClientConfig.host`、`S3FileClientConfig.endpoint`、`SftpFileClientConfig.host` 使用 `@URL`/`@NotEmpty` 仅校验格式，未限制内网 IP（127.0.0.1、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、169.254.0.0/16）。如果未来代码使用这些字段发起主动 HTTP 请求，将存在 SSRF 风险。但当前文件未实际发起请求，且为配置类，归入"配置不当"级别不另列问题；建议后续连接逻辑中增加 IP 白名单校验。

- **维度 10 CORS**: 本次审查范围内 Infra 模块未出现 `WebMvcConfigurer.addCorsMappings` 或 `CorsConfigurationSource` 配置，全局 CORS 配置位于其他模块（不在本次范围），无法核实是否会触发 V8 锁定规则中的"CSRF + CORS + Cookie = HIGH"组合漏洞，故仅记录"无问题"。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 4 |
| MEDIUM | 6 |
| LOW | 3 |
| **总计** | **13** |

按问题分布：

| 严重度 | 问题编号 |
|--------|----------|
| HIGH | 问题 2、问题 8、问题 10、问题 11 |
| MEDIUM | 问题 1、问题 3、问题 4、问题 7、问题 9、问题 12 |
| LOW | 问题 5、问题 6、问题 13 |

按类型分布：

| 类型 | 数量 |
|------|------|
| HardcodedSecret | 4 |
| Auth | 4 |
| CSRF | 1 |
| XSS | 2 |
| HttpFirewall | 2 |

---

## 关键风险总结

1. **Actuator 端点全局未授权暴露（问题 2）**：Spring Boot Actuator 的 `/env`、`/heapdump` 等高敏感端点被 `permitAll()`，攻击者可远程读取数据库密码与 Token 密钥，是本次评审最严重的风险。
2. **S3 accessSecret 明文持久化（问题 8）**：Jackson 多态序列化机制 (`@JsonTypeInfo(Id.CLASS)`) 直接将 accessSecret 以明文写入数据库，配合 `FileClientConfig` 接口上的多态注解（问题 9）形成完整攻击链。
3. **Druid 监控与文件下载未授权（问题 10、问题 11）**：Druid SQL 监控与 `infra/file/*/get/**` 文件下载均 `permitAll()`，可直接拖库与下载私有资源。
4. **Admin Server CSRF 关闭面过大（问题 3）**：`/actuator/**` 被加入 CSRF 忽略列表，结合问题 2 形成完整的未授权 + CSRF 攻击面。
5. **Admin Server 默认凭据（问题 1）**：`admin/admin` 默认值未在生产中强制覆盖，将直接导致监控面板被接管。

---

## 评审检查清单

- [x] 已检查所有 13 个评审维度
- [x] 已审查文件清单中的所有 15 个文件
- [x] 所有 CRITICAL/HIGH 问题都提供了代码片段（本次无 CRITICAL，4 个 HIGH 均已附代码）
- [x] 所有问题都使用了锁定严重度（按 V8 表逐项核对）
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合 V8 模板
- [x] 已应用组合漏洞判定规则（本次未触发 CSRF+CORS+Cookie 组合，因未见 CORS 配置）
- [x] 已应用问题合并规则（同源配置已合并）
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题（含 MD5/SHA1：本范围未出现 MD5/SHA1 调用，故无 LOW 类型报告）
- [x] 已对每个维度给出明确结论
- [x] 已执行严重度确认步骤

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Alpha
**语言**: Java
