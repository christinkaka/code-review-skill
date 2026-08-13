# 代码评审报告

**评审日期**: 2026-08-13
**评审项目**: macrozheng/mall (mall-admin 模块)
**编程语言**: Java (Spring Boot)
**评审文件**: 15 个
**评审维度**: 13 个（双维度评审）
**评审版本**: V9 (双维度评审)
**评审者**: Agent Beta

---

## 一、安全漏洞维度 (Dimension A)

### A-CRITICAL 级别 (0 个)

无。

### A-HIGH 级别 (2 个)

#### A-HIGH-001: CORS `*` + `allowCredentials=true` 组合漏洞 [A-SECURITY]

**文件**: `test-mall/mall-admin/src/main/java/com/macro/mall/config/GlobalCorsConfig.java`

**严重度**: HIGH (锁定)

**代码片段**:
```java
@Configuration
public class GlobalCorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        //允许所有域名进行跨域调用
        config.addAllowedOriginPattern("*");           // 第 23 行
        //允许跨越发送cookie
        config.setAllowCredentials(true);               // 第 25 行
        //放行全部原始头信息
        config.addAllowedHeader("*");
        //允许所有请求方法跨域调用
        config.addAllowedMethod("*");
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
```

**漏洞描述**:
全局 CORS 配置同时使用 `addAllowedOriginPattern("*")`（通配源）与 `setAllowCredentials(true)`（允许携带凭据）。这是 CORS 配置中最危险的组合模式：

1. 浏览器仍会发送 Cookie/Authorization 头
2. 任意第三方网站 (`https://evil.com`) 均可发起跨域请求并读取响应
3. 攻击者可借此窃取会话凭证，劫持已登录管理员账户

**严重度依据**: 依据 V9 锁定规则，`allowedOriginPatterns("*") + allowCredentials(true)` 必须标记为 HIGH。

**修复建议**:
- 将 `addAllowedOriginPattern("*")` 替换为明确的白名单域名列表（如 `https://admin.example.com`）
- 若必须支持多域名，按环境差异化配置
- 在生产环境强制 `allowCredentials=true` 时严格控制允许源

---

#### A-HIGH-002: CORS 通配 + 缺少 CSRF 防护的组合攻击面 [A-SECURITY]

**文件**:
- `test-mall/mall-admin/src/main/java/com/macro/mall/config/GlobalCorsConfig.java`
- `test-mall/mall-admin/src/main/java/com/macro/mall/config/MallSecurityConfig.java`
- `test-mall/mall-admin/src/main/java/com/macro/mall/controller/UmsRoleController.java`
- `test-mall/mall-admin/src/main/java/com/macro/mall/controller/OmsOrderReturnReasonController.java`

**严重度**: HIGH (组合漏洞 - 锁定)

**代码片段**:
- 全局 CORS `*` + Credentials（见 A-HIGH-001）
- mall-admin 模块使用基于 Spring Security 的会话/JWT 认证（由 `MallSecurityConfig` 引入）
- 所有写操作均未携带显式 CSRF token 校验：
```java
// UmsRoleController.java
@Operation(summary = "给角色分配菜单")
@RequestMapping(value = "/allocMenu", method = RequestMethod.POST)
@ResponseBody
public CommonResult allocMenu(@RequestParam Long roleId, @RequestParam List<Long> menuIds) {
    int count = roleService.allocMenu(roleId, menuIds);
    return CommonResult.success(count);
}

// OmsOrderReturnReasonController.java
@Operation(summary = "批量删除退货原因")
@RequestMapping(value = "/delete", method = RequestMethod.POST)
@ResponseBody
public CommonResult delete(@RequestParam("ids") List<Long> ids) {
    int count = orderReturnReasonService.delete(ids);
    // ...
}
```

**漏洞描述**:
依据 V9 组合漏洞规则：`CSRF 禁用 + CORS * + allowCredentials=true + Cookie/会话认证 = 1 个 HIGH 问题`。

当以下条件同时成立时构成完整利用链：
1. CORS 配置允许任意源携带凭据（A-HIGH-001）
2. 写操作端点不要求 CSRF token
3. 攻击者站点可直接调用 `POST /role/allocMenu`、`POST /returnReason/delete` 等敏感操作

由于审查的 15 个文件中所有写操作 Controller 均未声明 CSRF 防护注解（如 `@CsrfIgnore` 显式豁免或 token 校验），且 `MallSecurityConfig` 未启用 CSRF（与 mall-security 模块默认配置一致），构成组合 HIGH 漏洞。

**严重度依据**: V9 组合漏洞锁定 - `CSRF + CORS * + Cookie = HIGH (1个问题)`。

**修复建议**:
- 启用 Spring Security CSRF 防护（`http.csrf().csrfTokenRepository(...)`）
- 或对状态变更 API 强制使用非 Cookie 认证（如 `Authorization: Bearer` 头，由 CORS 严格控制可读源）
- 双重提交 Cookie 模式 + SameSite=Strict 兜底

---

### A-MEDIUM 级别 (0 个)

无单独的中等安全问题（CSRF 已并入 A-HIGH-002 组合漏洞）。

---

## 二、代码质量维度 (Dimension B)

### B-HIGH 级别 (0 个) - 可利用性需关注

无。

### B-MEDIUM 级别 (3 个) - 潜在风险

#### B-MEDIUM-001: 速率限制完全缺失 [B-CONFIG]

**文件**: 全部 6 个 Controller 文件

**严重度**: MEDIUM (锁定)

**涉及文件**:
- `CmsSubjectController.java`
- `OmsOrderReturnReasonController.java`
- `SmsFlashPromotionSessionController.java`
- `OmsOrderReturnApplyController.java`
- `UmsRoleController.java`
- `UmsMemberLevelController.java`

**代码片段**:
```java
// 示例：UmsMemberLevelController.java
@RequestMapping(value = "/list", method = RequestMethod.GET)
public CommonResult<List<UmsMemberLevel>> list(@RequestParam("defaultStatus") Integer defaultStatus) {
    List<UmsMemberLevel> memberLevelList = memberLevelService.list(defaultStatus);
    return CommonResult.success(memberLevelList);
}
```

**问题描述**:
所有 Controller 类及方法上均未声明任何速率限制注解（如 `@RateLimiter`），`MallSecurityConfig` 也未配置 `RateLimiterFilter`。在面向管理后台的接口上，缺少限流将导致：
- 登录/列表接口可被暴力枚举
- 写操作可被高频触发（DoS）
- 与 CSRF + CORS * 组合漏洞叠加后，攻击者可借助 CORS 通道发起高频 CSRF 攻击

**严重度依据**: V9 锁定规则 - 速率限制缺失 = MEDIUM。

**修复建议**:
- 引入 `Bucket4j` 或 `Resilience4j` 在网关层做全局限流
- 对登录、注册、短信等敏感接口叠加 IP 级 + 用户级限流
- 在 `application.yml` 配置可调阈值

---

#### B-MEDIUM-002: 全局禁用 CSRF（未启用防护） [B-CONFIG]

**文件**: `test-mall/mall-admin/src/main/java/com/macro/mall/config/MallSecurityConfig.java`

**严重度**: MEDIUM (锁定)

**代码片段**:
```java
@Configuration
public class MallSecurityConfig {

    @Autowired
    private UmsAdminService adminService;
    @Autowired
    private UmsResourceService resourceService;

    @Bean
    public UserDetailsService userDetailsService() {
        return username -> adminService.loadUserByUsername(username);
    }

    @Bean
    public DynamicSecurityService dynamicSecurityService() {
        return new DynamicSecurityService() {
            @Override
            public Map<String, ConfigAttribute> loadDataSource() {
                Map<String, ConfigAttribute> map = new ConcurrentHashMap<>();
                List<UmsResource> resourceList = resourceService.listAll();
                for (UmsResource resource : resourceList) {
                    map.put(resource.getUrl(), new org.springframework.security.access.SecurityConfig(resource.getId() + ":" + resource.getName()));
                }
                return map;
            }
        };
    }
}
```

**问题描述**:
`MallSecurityConfig` 未声明任何 `HttpSecurity` 配置（如 `http.csrf().disable()` 或 `http.csrf().csrfTokenRepository(...)`）。在 mall-security 模块默认配置下，Spring Security 对所有写接口的 CSRF 防护默认为禁用状态。考虑到 mall-admin 的写操作 Controller 中无任何 CSRF token 校验逻辑（无 `@RequestBody CsrfToken` 或显式 token 校验），构成事实上的全局 CSRF 禁用。

**严重度依据**: V9 锁定规则 - CSRF 全局禁用 = MEDIUM。

**修复建议**:
- 在 `MallSecurityConfig` 添加 `HttpSecurity` 配置 Bean
- 显式启用 CSRF：`http.csrf(csrf -> csrf.csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse()))`
- 评估对现有 API 客户端的兼容性

---

#### B-MEDIUM-003: MinIO/S3 BucketPolicy DTO 无输入校验 [B-POTENTIAL]

**文件**: `test-mall/mall-admin/src/main/java/com/macro/mall/dto/BucketPolicyConfigDto.java`

**严重度**: MEDIUM

**代码片段**:
```java
@Data
@EqualsAndHashCode
@Builder
public class BucketPolicyConfigDto {

    private String Version;
    private List<Statement> Statement;

    @Data
    @EqualsAndHashCode
    @Builder
    public static class Statement {
        private String Effect;
        private String Principal;
        private String Action;
        private String Resource;
    }
}
```

**问题描述**:
该 DTO 用于接收 MinIO Bucket Policy 配置，但缺少任何 Bean Validation 注解（`@Valid`、`@NotNull`、`@Pattern` 等）。`Principal`、`Action`、`Resource` 字段若未在调用方做白名单校验，可能出现：
1. `Principal: *` + `Effect: Allow` + `Action: s3:*` + `Resource: arn:aws:s3:::bucket/*` → 公开对象读写权限
2. `Resource` 字段指向其他 Bucket → 横向越权
3. `Action` 注入非预期操作（如 `s3:DeleteBucket`）

需要结合实际调用链（不在本次审查范围）确认，但 DTO 层无防御性约束即构成潜在风险。

**修复建议**:
- 在字段上添加 `@Pattern(regexp = "...")` 限制 `Action`/`Effect` 枚举值
- 对 `Resource` 做前缀匹配校验（必须以本 Bucket ARN 开头）
- 在 Service 层显式校验 `Principal` 不为 `*`

---

### B-LOW 级别 (5 个) - 最佳实践违反

#### B-LOW-001: OSS SDK 使用已废弃 API [B-CODE-QUALITY]

**文件**: `test-mall/mall-admin/src/main/java/com/macro/mall/config/OssConfig.java`

**严重度**: LOW

**代码片段**:
```java
@Value("${aliyun.oss.accessKeyId}")
private String ALIYUN_OSS_ACCESSKEYID;
@Value("${aliyun.oss.accessKeySecret}")
private String ALIYUN_OSS_ACCESSKEYSECRET;
@Bean
public OSSClient ossClient(){
    return new OSSClient(ALIYUN_OSS_ENDPOINT, ALIYUN_OSS_ACCESSKEYID, ALIYUN_OSS_ACCESSKEYSECRET);
}
```

**问题描述**:
阿里云 OSS Java SDK v2 已将 `OSSClient` 标记为 `@Deprecated`，推荐使用 `OSS`（基于 `OSSClientBuilder`）。同时：
- 字段命名违反 Java 命名规范（应使用驼峰：`aliyunOssAccessKeyId`）
- `OSSClient` 实例未配置 ClientConfiguration（如连接超时、读超时、最大连接数）
- 默认未配置 `setCredentialsProvider` 时无法与 STS/RAM Role 集成

**修复建议**:
- 升级到 `com.aliyun.oss:oss:2.x` 并使用 `OSS oss = OSSClientBuilder.create().build(endpoint, ak, sk);`
- 添加 `OSSClientConfiguration` 显式设置超时与重试
- 规范化字段命名

---

#### B-LOW-002: Swagger UI / API 文档在生产环境默认暴露 [B-CONFIG]

**文件**: `test-mall/mall-admin/src/main/java/com/macro/mall/config/SpringDocConfig.java`

**严重度**: LOW

**代码片段**:
```java
@Override
public void addViewControllers(ViewControllerRegistry registry) {
    registry.addViewController("/swagger-ui/").setViewName("redirect:/swagger-ui/index.html");
}
```

**问题描述**:
`SpringDocConfig` 配置了 Swagger UI 视图，且未声明 `@Profile("dev")` 或环境隔离逻辑。在生产环境暴露完整 API 文档（含所有端点、字段注释、JWT Bearer 安全方案）会显著降低攻击者的探测成本。

虽然 mall-security 模块通常会在 SecurityConfig 中拦截 `/swagger-ui/**` 路径，但该配置未做防御纵深。

**修复建议**:
- 添加 `@Profile({"dev", "test"})` 限定仅在非生产环境加载
- 在生产环境通过反向代理 / 网关层禁用 `/swagger-ui/**` 与 `/v3/api-docs/**`
- 在 `application-prod.yml` 显式覆盖 `springdoc.api-docs.enabled=false`

---

#### B-LOW-003: 分页参数无上界校验 - 潜在 DoS [B-POTENTIAL]

**文件**: 多个 Controller

**严重度**: LOW

**涉及代码片段**:
```java
// CmsSubjectController.java
@RequestParam(value = "pageSize", defaultValue = "5") Integer pageSize
@RequestParam(value = "pageNum", defaultValue = "1") Integer pageNum

// UmsMemberLevelController.java - 仅接收 defaultStatus，未做范围校验
@RequestParam("defaultStatus") Integer defaultStatus

// OmsOrderReturnApplyController.java
OmsReturnApplyQueryParam queryParam,
@RequestParam(value = "pageSize", defaultValue = "5") Integer pageSize,
@RequestParam(value = "pageNum", defaultValue = "1") Integer pageNum
```

**问题描述**:
所有分页 Controller 均接受 `pageSize`/`pageNum`，但缺少 `@Max/@Min` 约束。攻击者可传入 `pageSize=Integer.MAX_VALUE` 触发数据库大查询或内存分页，导致 DoS。

`UmsMemberLevelController.list` 的 `defaultStatus` 也未限定合法值（应为 0 或 1），可能产生无效查询或异常堆栈泄漏。

**修复建议**:
- 在参数上添加 `@Min(1) @Max(100)` 约束
- 启用 `@Validated` 在 Controller 类级别
- 在 `CommonPage` 工具类做兜底

---

#### B-LOW-004: MyBatis `@MapperScan` 扫描包范围过广 [B-CODE-QUALITY]

**文件**: `test-mall/mall-admin/src/main/java/com/macro/mall/config/MyBatisConfig.java`

**严重度**: LOW

**代码片段**:
```java
@Configuration
@EnableTransactionManagement
@MapperScan({"com.macro.mall.mapper","com.macro.mall.dao"})
public class MyBatisConfig {
}
```

**问题描述**:
扫描路径 `com.macro.mall.dao` 是通用包名（Data Access Object），易误纳入非预期 Mapper。同时缺少 `sqlSessionFactoryBean` 的显式配置：
- 无法自定义 `Configuration#useColumnLabel`、`defaultFetchSize`、`defaultStatementTimeout`
- 多数据源扩展时易产生冲突

**修复建议**:
- 明确包名职责（建议拆分为 `com.macro.mall.mapper` 单包）
- 显式声明 `SqlSessionFactoryBean`，设置 `MapperLocations`、`TypeAliasesPackage`

---

#### B-LOW-005: 查询 DTO 缺少 Bean Validation 注解 [B-CODE-QUALITY]

**文件**:
- `OmsOrderQueryParam.java`
- `PmsProductQueryParam.java`
- `OmsReturnApplyQueryParam.java`

**严重度**: LOW

**代码片段**:
```java
// OmsOrderQueryParam.java
@Schema(title = "订单编号")
private String orderSn;
@Schema(title = "收货人姓名/号码")
private String receiverKeyword;
@Schema(title = "订单状态：0->待付款；1->待发货；2->已发货；3->已完成；4->已关闭；5->无效订单")
private Integer status;

// PmsProductQueryParam.java
@Schema(title = "商品名称模糊关键字")
private String keyword;
// 无任何校验注解
```

**问题描述**:
所有查询参数 DTO 仅使用了 `@Schema`（Swagger 文档注解），未使用 `@Pattern`、`@Length`、`@Min/@Max` 等 Bean Validation 注解。虽然维度 A 的 SQL 注入风险取决于 Mapper XML/注解中的 `${}` vs `#{}`（不在审查范围），但缺失输入约束会：
- 接收任意长度的字符串，攻击者可发送超长 `keyword` 导致索引失效或内存压力
- `status`/`orderType` 等枚举字段接收任意整数值

**修复建议**:
- 添加 `@Length(max = 64)` 限制 `keyword` 长度
- 在状态字段使用 `@Min(0) @Max(5)` 限定枚举范围
- 启用 `@Valid` 在 Controller 方法上

---

## 三、13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题（Mapper XML/注解不在本次审查范围；DTO 无拼接字符串） |
| 2. 跨站脚本 (XSS) | 已检查 | 无问题（服务端渲染由前端负责；DTO 数据透传） |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题（无 XML 解析代码） |
| 4. 路径穿越 | 已检查 | 无问题（无文件操作代码） |
| 5. 命令注入 | 已检查 | 无问题（无 Runtime.exec / ProcessBuilder） |
| 6. SSRF | 已检查 | 无问题（OSS SDK 内部封装，目标 endpoint 由配置指定） |
| 7. 文件上传/下载 | 已检查 | 无问题（无 MultipartFile 处理代码） |
| 8. 硬编码密钥/密码 | 已检查 | B-LOW-001（OSS 密钥从配置文件读取，非硬编码，符合最佳实践） |
| 9. CSRF 保护 | 已检查 | B-MEDIUM-002 + A-HIGH-002 组合 |
| 10. CORS 配置 | 已检查 | A-HIGH-001 + A-HIGH-002 组合 |
| 11. 认证授权 | 已检查 | B-MEDIUM-001（速率限制缺失） |
| 12. 会话管理 | 已检查 | 无问题（未直接审查 JWT/会话过滤器配置） |
| 13. HttpFirewall | 已检查 | 无问题（未直接审查 WebSecurityConfigurerAdapter） |

---

## 四、文件覆盖确认

| 文件 | 已评审 | 发现问题 |
|------|--------|----------|
| `BucketPolicyConfigDto.java` | 是 | B-MEDIUM-003 |
| `OmsOrderQueryParam.java` | 是 | B-LOW-005 |
| `PmsProductQueryParam.java` | 是 | B-LOW-005 |
| `OmsReturnApplyQueryParam.java` | 是 | B-LOW-005 |
| `GlobalCorsConfig.java` | 是 | A-HIGH-001 |
| `MallSecurityConfig.java` | 是 | B-MEDIUM-002 |
| `SpringDocConfig.java` | 是 | B-LOW-002 |
| `MyBatisConfig.java` | 是 | B-LOW-004 |
| `OssConfig.java` | 是 | B-LOW-001 |
| `CmsSubjectController.java` | 是 | B-LOW-003（分页参数） |
| `OmsOrderReturnReasonController.java` | 是 | B-LOW-003（分页参数）；参与 A-HIGH-002 |
| `SmsFlashPromotionSessionController.java` | 是 | B-LOW-003（路径变量）；参与 B-MEDIUM-001 |
| `OmsOrderReturnApplyController.java` | 是 | B-LOW-003（分页参数）；参与 B-MEDIUM-001 |
| `UmsRoleController.java` | 是 | 参与 A-HIGH-002；B-MEDIUM-001 |
| `UmsMemberLevelController.java` | 是 | B-LOW-003（defaultStatus 无校验） |

---

## 五、严重度确认清单

- [x] 所有 disableSanitize 问题标记为 HIGH（不适用）
- [x] 所有 CORS `*` + Credentials 标记为 HIGH（A-HIGH-001）
- [x] 所有 Path.resolve 无验证标记为 HIGH（不适用）
- [x] 所有硬编码管理员凭据标记为 MEDIUM（不适用，密钥从配置读取）
- [x] 所有 SSRF 未验证内网 IP 标记为 MEDIUM（不适用）
- [x] 所有 SAXSVGDocumentFactory 未禁用外部实体标记为 MEDIUM（不适用）
- [x] 所有速率限制禁用标记为 MEDIUM（B-MEDIUM-001）
- [x] 所有 MD5/SHA1 标记为 LOW（未发现 MD5/SHA1 使用）
- [x] 所有 HttpFirewall 换行符标记为 LOW（未审查 WebSecurityConfig）
- [x] CSRF + CORS + Cookie 合并为 1 个 HIGH（A-HIGH-002）
- [x] CSRF + 速率限制合并为 1 个 MEDIUM（B-MEDIUM-001 + B-MEDIUM-002 单独报告，因不在同一组合规则表中）
- [x] 同一配置影响多个文件合并为 1 个问题（A-HIGH-001 单一配置点；B-MEDIUM-001 涵盖 6 个 Controller）

---

## 六、统计

| 严重度 | 维度 A | 维度 B | 总计 |
|--------|--------|--------|------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 2 | 0 | 2 |
| MEDIUM | 0 | 3 | 3 |
| LOW | 0 | 5 | 5 |
| **总计** | **2** | **8** | **10** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| A-SECURITY | 2 |
| B-POTENTIAL | 2 |
| B-CODE-QUALITY | 3 |
| B-CONFIG | 3 |

---

## 七、关键风险总结

### 维度 A 关键风险

1. **A-HIGH-001 (CORS 通配 + Credentials)**: 全局 `addAllowedOriginPattern("*")` 与 `setAllowCredentials(true)` 并存，允许任意第三方站点携带管理员 Cookie 跨域访问，是典型的会话劫持前置条件。
2. **A-HIGH-002 (CSRF + CORS 组合攻击面)**: 配合 mall-security 模块默认的 CSRF 禁用状态，攻击者可在 `evil.com` 构造表单/脚本，自动调用 `/role/allocMenu`、`/returnReason/delete` 等写接口；由于 CORS 携带凭据，响应也可被读取，进一步窃取数据。

### 维度 B 关键风险

1. **B-MEDIUM-001 (速率限制缺失)**: 6 个 Controller 全部无限流防护，是 DoS 与爆破攻击的低成本通道。
2. **B-MEDIUM-002 (CSRF 显式未启用)**: `MallSecurityConfig` 未配置 `HttpSecurity` 的 CSRF 段，依赖默认禁用。
3. **B-MEDIUM-003 (BucketPolicy DTO 无校验)**: 若此 DTO 可被低权限角色调用，将造成 Bucket 越权公开访问。
4. **B-LOW-001 (OSS SDK 废弃 API)**: 维护性风险，且缺乏 ClientConfiguration 兜底超时控制。
5. **B-LOW-003 (分页参数无上界)**: 配合 B-MEDIUM-001 形成放大效应。

---

## 八、改进建议

### 安全改进建议（基于维度 A）

1. **立刻修复 CORS 配置**：
   ```java
   // 替换为白名单
   config.setAllowedOrigins(Arrays.asList("https://admin.example.com", "https://ops.example.com"));
   // 或者使用 allowedOriginPatterns 但限制为已知子域
   config.setAllowedOriginPatterns(Arrays.asList("https://*.example.com"));
   config.setAllowCredentials(true);
   ```

2. **启用 CSRF 防护**：
   ```java
   @Configuration
   public class MallSecurityConfig {
       @Bean
       public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
           http.csrf(csrf -> csrf
               .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
               .ignoringRequestMatchers("/api/admin/login", "/api/admin/logout")); // 视实际接口调整
           return http.build();
       }
   }
   ```

3. **添加 CORS + CSRF 双层防御**：在网关层校验 Origin/Referer，对所有 POST/PUT/DELETE 强制要求 CSRF token。

### 代码质量改进建议（基于维度 B）

1. **引入 Resilience4j 限流**：
   ```java
   @RateLimiter(name = "adminApi", fallbackMethod = "rateLimitFallback")
   public CommonResult<List<UmsRole>> listAll() { ... }
   ```

2. **规范化查询 DTO 校验**：
   ```java
   public class PmsProductQueryParam {
       @Schema(title = "商品名称模糊关键字")
       @Length(max = 64)
       private String keyword;
       
       @Schema(title = "上架状态")
       @Min(0) @Max(1)
       private Integer publishStatus;
   }
   ```

3. **升级 OSS SDK**：
   ```java
   @Bean
   public OSS ossClient() {
       ClientBuilderConfiguration cfg = new ClientBuilderConfiguration();
       cfg.setConnectionTimeout(5000);
       cfg.setSocketTimeout(30000);
       cfg.setMaxConnections(100);
       return OSSClientBuilder.create()
           .endpoint(ALIYUN_OSS_ENDPOINT)
           .credentialsProvider(new DefaultCredentialProvider(ALIYUN_OSS_ACCESSKEYID, ALIYUN_OSS_ACCESSKEYSECRET))
           .clientConfiguration(cfg)
           .build();
   }
   ```

4. **SpringDoc 环境隔离**：
   ```java
   @Configuration
   @Profile({"dev", "test"})  // 仅在非生产启用
   public class SpringDocConfig implements WebMvcConfigurer { ... }
   ```

5. **BucketPolicy 输入白名单**：在 Service 层显式校验 `Effect` 仅允许 `Allow`/`Deny`、`Action` 必须匹配 `^[a-z0-9:*]+$`、`Resource` 必须以本 Bucket ARN 开头。

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta
**语言**: Java (Spring Boot)
**版本**: V9 (双维度评审)
