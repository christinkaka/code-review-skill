# 代码评审报告

**评审日期**: 2026-08-13
**评审项目**: macrozheng/mall
**编程语言**: Java (Spring Boot)
**评审范围**: 15 个文件
**评审维度**: 13 个
**评审者**: Agent Beta
**评审指令**: 标准化评审指令 V8 (多语言版)

---

## 一、评审概要

本次评审针对 mall-admin 模块中 4 个 DTO、5 个 Config、6 个 Controller 文件进行安全审计。为准确评估 CSRF / CORS 组合漏洞,评审扩展核查了 mall-security 模块中的 `SecurityConfig.java` 与 `JwtTokenUtil.java`、以及 mall-admin 的 `application.yml`(项目内必需上下文)。

主要发现:
- **1 个组合漏洞(HIGH)**:CSRF 禁用 + CORS `*` + allowCredentials=true。
- **1 个组合漏洞(MEDIUM)**:CSRF 禁用 + 速率限制缺失(认证接口与业务接口均无)。
- **1 个 MEDIUM**:JWT secret 在 `application.yml` 中硬编码默认值(`mall-admin-secret`),密钥强度不足。
- **1 个 MEDIUM**:JWT 有效期 604800 秒(7 天)未启用刷新 Token 黑名单/吊销机制,且无 token 轮换。
- **2 个 LOW**:HTTP 会话相关最佳实践违反;缺失 HttpFirewall 自定义。

---

## 二、严重度确认步骤(提交前)

执行 V8 要求的严重度确认步骤:

1. **CSRF 维度**:确认 `mall-security/.../SecurityConfig.java:56` 显式 `.csrf(AbstractHttpConfigurer::disable)`。
2. **CORS 维度**:确认 `mall-admin/.../GlobalCorsConfig.java:23-25` 使用 `addAllowedOriginPattern("*")` + `setAllowCredentials(true)`。
3. **组合判定**:CSRF 禁用 + CORS `*` + allowCredentials=true → **组合漏洞,锁定 HIGH**(V8 规则)。
4. **认证方式**:mall-admin 使用 **JWT 无状态认证**(Authorization Header,非 Cookie 认证)。但 Spring Security CSRF 默认仅针对 Cookie/Session 认证启用保护,本系统因 JWT + STATELESS,严格意义上攻击者无法通过浏览器自动携带凭证。但项目同时开启了 `allowCredentials=true` 的 `*` 通配,任何 Origin 都可携带凭据,该模式即使在 JWT Header 模式下仍允许跨源携带敏感 Header 的攻击面,且代码中多个 Controller 同时为 `/admin/register`、`/admin/login` 白名单,加剧了凭据盗用风险。**因此仍按 V8 锁定规则按 HIGH 报告,但需说明认证方式非 Cookie**,由 CSRF 风险降为 CORS 凭据跨域风险为主。
5. **速率限制**:未发现任何限流中间件/拦截器/过滤器配置 → 触发 CSRF + 速率限制组合 MEDIUM。
6. **MD5/SHA1**:在 15 个文件 + 项目全局 grep 均未发现 `MessageDigest.getInstance("MD5"/"SHA-1")` 调用 → 本批文件无需报告 MD5/SHA1,但须在覆盖确认表中明确说明已检查。
7. **SQL 注入**:Controller 仅作为参数透传层,无字符串拼接 → MyBatis 配置文件未包含在本批次,按"未在本批次内发现"处理。
8. **组合规则应用**:CSRF + CORS `*` + allowCredentials=true 合并为 1 个 HIGH 问题;CSRF + 速率限制合并为 1 个 MEDIUM 问题。

---

## 三、发现的问题

### 问题 1:组合漏洞 - CSRF 禁用 + CORS 通配 + 凭据允许
- **文件**:
  - `test-mall/mall-admin/src/main/java/com/macro/mall/config/GlobalCorsConfig.java` (行 23-25)
  - `test-mall/mall-security/src/main/java/com/macro/mall/security/config/SecurityConfig.java` (行 56)
- **行号**: GlobalCorsConfig.java 第 23-25 行 / SecurityConfig.java 第 56 行
- **严重度**: **HIGH**(组合漏洞,V8 锁定)
- **类型**: CORS + CSRF 组合
- **描述**:
  项目同时启用了两个高风险配置:CORS 使用 `addAllowedOriginPattern("*")` 通配所有源,并允许跨域携带凭据 `setAllowCredentials(true)`;Spring Security 显式禁用 CSRF 保护(`.csrf(AbstractHttpConfigurer::disable)`)。在 V8 规则下,即便本项目采用 JWT 无状态认证(非传统 Cookie 认证,削弱了浏览器自动携带凭据的 CSRF 风险),CORS 通配 + 凭据允许仍允许任意来源的页面携带凭据(Authorization Header 等)访问后台 API,后台管理员/会员接口面临跨源凭据盗用与跨源请求伪造风险。
- **代码片段**:
```java
// GlobalCorsConfig.java:20-32
@Bean
public CorsFilter corsFilter() {
    CorsConfiguration config = new CorsConfiguration();
    //允许所有域名进行跨域调用
    config.addAllowedOriginPattern("*");
    //允许跨越发送cookie
    config.setAllowCredentials(true);
    //放行全部原始头信息
    config.addAllowedHeader("*");
    //允许所有请求方法跨域调用
    config.addAllowedMethod("*");
    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/**", config);
    return new CorsFilter(source);
}
```
```java
// SecurityConfig.java:55-56 (mall-security)
//关闭跨站请求防护
.csrf(AbstractHttpConfigurer::disable)
```
- **修复建议**:
  1. 将 `addAllowedOriginPattern("*")` 替换为白名单(例如 `config.addAllowedOrigin("https://admin.example.com")`)。
  2. 后台管理 API 不应允许跨源携带凭据;若必须支持 CORS,严格限制 Origin 白名单。
  3. 即使使用 JWT,仍建议为管理后台启用 CSRF Token(双提交 Cookie 模式)或验证 `Origin/Referer` Header。

---

### 问题 2:组合漏洞 - CSRF 禁用 + 速率限制缺失
- **文件**:
  - `test-mall/mall-security/src/main/java/com/macro/mall/security/config/SecurityConfig.java`(CSRF 禁用)
  - 缺失文件:`SecurityConfig.java` 中无 `RateLimiterFilter` / `InterceptorRegistration.addInterceptors(...)` 限流配置 / 无 Bucket4j / 无 Redis 限流
- **行号**: SecurityConfig.java 第 56 行
- **严重度**: **MEDIUM**(组合漏洞,V8 锁定)
- **类型**: CSRF + 速率限制
- **描述**:
  CSRF 保护被显式禁用,但项目未引入任何速率限制中间件、限流拦截器或限流过滤器。结合后台管理登录接口 `/admin/login`、注册接口 `/admin/register`、Swagger UI 接口、Actuator、Druid 等均处于安全白名单(参见 `mall-admin/src/main/resources/application.yml:33-50`),这些高频攻击面同时缺少 CSRF 防护与速率限制,存在登录爆破、注册接口滥用、Actuator 信息泄露放大等风险。V8 规则下,CSRF 禁用与速率限制禁用必须合并报告为 1 个 MEDIUM 问题。
- **代码片段**:
```java
// SecurityConfig.java:55-56 (mall-security)
//关闭跨站请求防护
.csrf(AbstractHttpConfigurer::disable)
```
```yaml
# mall-admin/src/main/resources/application.yml:33-50 (上下文)
secure:
  ignored:
    urls: #安全路径白名单
      - /swagger-ui/
      - /v3/api-docs/*
      - /actuator/**
      - /druid/**
      - /admin/login
      - /admin/register
      - /admin/info
      - /admin/logout
      - /minio/upload
      - /aliyun/oss/policy
```
- **修复建议**:
  1. 引入 Bucket4j + Redis 实现接口级速率限制(尤其登录/注册)。
  2. 移除 `/actuator/**` 与 `/druid/**` 的白名单(或限制内网访问)。
  3. 重新启用 CSRF Token(双提交 Cookie 模式)以与限流形成纵深防御。

---

### 问题 3:JWT Secret 硬编码默认值(密钥强度不足)
- **文件**: `test-mall/mall-admin/src/main/resources/application.yml`(行 21)
- **行号**: 21
- **严重度**: **MEDIUM**(硬编码密钥/默认值,锁定规则)
- **类型**: HardcodedSecret
- **描述**:
  `jwt.secret: mall-admin-secret` 直接以明文形式在配置文件中定义默认值。该值同时被 `JwtTokenUtil.getSigningKey()`(JwtTokenUtil.java:42-44)用作 HS512 HMAC 签名密钥。`mall-admin-secret` 长度仅 16 字符且为公开仓库默认值,任何获取源码的攻击者均可伪造任意管理员 JWT。同时密钥在仓库公开,导致密钥强度等于零,严重度锁定为 MEDIUM(V8:硬编码 API 密钥类配置)。
- **代码片段**:
```yaml
# application.yml:19-23
jwt:
  tokenHeader: Authorization #JWT存储的请求头
  secret: mall-admin-secret #JWT加解密使用的密钥
  expiration: 604800 #JWT的超期限时间(60*60*24*7)
  tokenHead: 'Bearer '  #JWT负载中拿到开头
```
```java
// JwtTokenUtil.java:42-44
private byte[] getSigningKey() {
    return secret.getBytes(StandardCharsets.UTF_8);
}
```
- **修复建议**:
  1. 使用环境变量或 Spring Cloud Config / Vault 管理 JWT 密钥,严禁仓库默认值。
  2. 密钥长度至少 256 bit(32 字节)随机生成。
  3. 通过 `application-prod.yml` 覆盖,生产环境强制从密钥管理服务注入。

---

### 问题 4:JWT 过期时间过长(7 天)+ 无吊销/黑名单机制
- **文件**: `test-mall/mall-admin/src/main/resources/application.yml`(行 22)
- **行号**: 22
- **严重度**: **MEDIUM**(V8:超时较长 >7 天锁定 MEDIUM)
- **类型**: Session(会话管理)
- **描述**:
  `jwt.expiration: 604800` 即 7 天。结合 `JwtTokenUtil.validateToken()`(行 94-97)仅校验签名与 `exp`,未引入 Redis 黑名单/版本号机制,token 一旦签发 7 天内不可强制吊销。配合硬编码密钥(问题 3),被盗 token 在有效期内可任意使用。V8 锁定规则:超时 >7 天 → MEDIUM。
- **代码片段**:
```yaml
# application.yml:22
  expiration: 604800 #JWT的超期限时间(60*60*24*7)
```
```java
// JwtTokenUtil.java:94-97
public boolean validateToken(String token, UserDetails userDetails) {
    String username = getUserNameFromToken(token);
    return username != null && username.equals(userDetails.getUsername()) && !isTokenExpired(token);
}
```
- **修复建议**:
  1. Access Token 有效期缩短至 15-30 分钟,Refresh Token 7 天并入库可吊销。
  2. 引入 Redis 黑名单支持登出/踢人/改密后失效所有 token。
  3. 关键操作(改密、分配角色)要求二次认证。

---

### 问题 5:缺失 StrictHttpFirewall 配置
- **文件**: 缺失文件(应位于 `mall-security/.../config/` 或自定义 `WebSecurityCustomizer`)
- **行号**: 不适用
- **严重度**: **LOW**(V8:HttpFirewall 配置不当)
- **类型**: HttpFirewall
- **描述**:
  mall-security 模块的 `SecurityConfig.java` 未配置 `StrictHttpFirewall`(项目全局 grep `StrictHttpFirewall` / `HttpFirewall` 0 命中)。默认 Spring Security `HttpFirewall` 允许 `%0d%0a`(CRLF)等特殊字符绕过部分反代/缓存层,导致 HTTP 响应拆分/缓存投毒风险较低但仍存在。
- **代码片段**: 无代码片段(缺失配置)
- **修复建议**:
```java
@Bean
public HttpFirewall httpFirewall() {
    StrictHttpFirewall firewall = new StrictHttpFirewall();
    firewall.setAllowUrlEncodedSlash(false);
    firewall.setAllowSemicolon(false);
    firewall.setAllowUrlEncodedPercent(false);
    return firewall;
}
```

---

### 问题 6:OSS AccessKey 使用 test/test 默认占位符
- **文件**: `test-mall/mall-admin/src/main/resources/application.yml`(行 73-74)
- **行号**: 73-74
- **严重度**: **LOW**(硬编码测试占位符)
- **类型**: HardcodedSecret
- **描述**:
  `aliyun.oss.accessKeyId: test` 与 `aliyun.oss.accessKeySecret: test` 在仓库中以明文占位符出现。虽然是占位符,但若部署时未通过环境变量覆盖,将直接以字面量 `"test"` 注入 `OSSClient`(OssConfig.java:22),触发 OSS 客户端初始化异常或被攻击者利用已知弱凭据。须作为 LOW 报告,提醒运维强制覆盖。
- **代码片段**:
```yaml
# application.yml:70-75
aliyun:
  oss:
    endpoint: oss-cn-shenzhen.aliyuncs.com
    accessKeyId: test
    accessKeySecret: test
```
- **修复建议**:
  1. 生产环境通过 `${ALIYUN_OSS_ACCESS_KEY_ID}` / `${ALIYUN_OSS_ACCESS_KEY_SECRET}` 环境变量注入。
  2. 删除仓库中的占位默认值,改为 `@Value("${aliyun.oss.accessKeyId:}")` 空字符串启动校验。

---

## 四、13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 (SQLi) | 已检查(Controller 层无拼接;MyBatis XML 不在本批次) | 无问题(本批次) |
| 2. 跨站脚本 (XSS) | 已检查(后端 Java,无模板渲染输出) | 无问题 |
| 3. XML 外部实体 (XXE) | 已检查(本批次无 XML 解析调用) | 无问题(本批次) |
| 4. 路径穿越 (Path Traversal) | 已检查(本批次无 File/Path 处理) | 无问题 |
| 5. 命令注入 (Command Injection) | 已检查(本批次无 Runtime.exec/ProcessBuilder) | 无问题 |
| 6. 服务端请求伪造 (SSRF) | 已检查(本批次无 URL.openConnection/HttpClient) | 无问题 |
| 7. 不安全的文件上传/下载 | 已检查(Controller 仅参数透传,上传在 Minio/Oss Controller,不在本批次;application.yml 限制 10MB) | 无问题(本批次) |
| 8. 硬编码密钥/密码 | 已检查(全局 grep `MessageDigest`/`MD5`/`SHA-1` 无命中) | 问题 3、问题 6 |
| 9. CSRF 保护 | 已检查(SecurityConfig.java:56 显式 disable) | 问题 1、问题 2 |
| 10. CORS 配置 | 已检查(GlobalCorsConfig.java) | 问题 1 |
| 11. 认证授权 | 已检查(无默认凭据硬编码;无速率限制;动态权限 OK) | 问题 2 |
| 12. 会话管理 (Session) | 已检查(JWT 过期 7 天;无黑名单) | 问题 4 |
| 13. HttpFirewall / 安全中间件 | 已检查(未配置 StrictHttpFirewall) | 问题 5 |

### MD5/SHA1 专项检查

- 项目全局 grep 结果:`MessageDigest.getInstance("MD5"/"SHA-1")` 0 命中。
- 本批次 15 个文件:未发现 MD5/SHA1 使用。
- **结论**:本次评审无需报告 MD5/SHA1 LOW 问题,但已严格按 V8 要求执行独立检查步骤。

---

## 五、统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 2 |
| **总计** | **6** |

---

## 六、关键风险总结

1. **问题 1(组合 HIGH)**:CSRF 禁用 + CORS `*` + allowCredentials=true。即便使用 JWT 而非 Cookie 认证,CORS 通配仍允许任意来源携带 Authorization Header 跨源访问后台 API,是后台管理接口面临的最大跨源凭据盗用风险。

2. **问题 2(组合 MEDIUM)**:CSRF 禁用 + 速率限制缺失。配合登录/注册/Actuator/Druid/Swagger 等白名单接口,缺少纵深防御,登录爆破与接口滥用风险显著。

3. **问题 3(MEDIUM)**:JWT 密钥 `mall-admin-secret` 在公开仓库以明文默认值硬编码,密钥强度等于零,任意攻击者可伪造管理员 JWT。

4. **问题 4(MEDIUM)**:JWT 7 天有效期且无吊销/黑名单机制,被盗 token 长期有效。

5. **问题 5/6(LOW)**:缺失 StrictHttpFirewall、OSS AccessKey 占位符未强制环境变量覆盖。

---

## 七、评审检查清单(V8 提交前确认)

- [x] 已检查所有 13 个评审维度
- [x] 已审查文件清单中的所有 15 个文件
- [x] 所有 HIGH 问题已提供代码片段(问题 1)
- [x] 所有 MEDIUM 问题已提供代码片段(问题 2、3、4)
- [x] 所有问题都使用了锁定严重度(禁止降级)
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合 V8 要求
- [x] 已应用组合漏洞判定规则(CSRF+CORS=HIGH 合并;CSRF+RateLimit=MEDIUM 合并)
- [x] 已应用问题合并规则(CORS 配置与 CSRF 禁用合并为 1 个组合问题)
- [x] 已报告所有 MEDIUM/LOW 问题
- [x] 已对每个维度给出明确结论(13 维度覆盖确认表)
- [x] 已执行严重度确认步骤(见第二节)
- [x] MD5/SHA1 已独立检查(0 命中,无需报告)

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta
**语言**: Java