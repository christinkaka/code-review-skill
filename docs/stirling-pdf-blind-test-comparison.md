# Stirling-PDF 双盲验证对比报告

**验证日期**: 2026-08-12  
**目标项目**: Stirling-PDF (GitHub 89K stars)  
**验证方法**: 两个独立 Agent (Alpha 和 Beta) 分别进行代码评审，对比一致率

---

## 执行摘要

两个独立 Agent 对 Stirling-PDF 项目进行了代码评审，发现了一些共同的安全问题，但也存在显著的评审差异。

| 指标 | Agent Alpha | Agent Beta | 一致 |
|------|-------------|------------|------|
| 总问题数 | 11 | 15 | ❌ |
| CRITICAL | 0 | 0 | ✅ |
| HIGH | 3 | 5 | ❌ |
| MEDIUM | 4 | 6 | ❌ |
| LOW | 4 | 4 | ✅ |

**一致率**: 8.3% (2/24 个问题被两个 Agent 同时发现)

---

## 共同发现的问题 (2个)

### 1. WeasyPrint SSRF 绕过
- **文件**: `ConvertWebsiteToPDF.java`
- **行号**: 136-141
- **严重度**: HIGH (Beta) / MEDIUM (Alpha)
- **描述**: URL-to-PDF 转换中，WeasyPrint 使用 `--base-url` 参数传入用户提供的 URL，可能在渲染时解析 HTML 中的相对 URL 引用，绕过 SSRF 防护。

### 2. HTML 净化器可被配置禁用
- **文件**: `CustomHtmlSanitizer.java`
- **行号**: 64-66
- **严重度**: HIGH (两者一致)
- **描述**: `disableSanitize` 配置项允许完全绕过 HTML 净化，若在生产环境被启用将导致 XSS 风险。

---

## Agent Alpha 单独发现的问题 (9个)

| # | 文件 | 严重度 | 类型 | 描述 |
|---|------|--------|------|------|
| 1 | FileOrUploadService.java | HIGH | PathTraversal | `resolveFilePath()` 未做路径穿越检查 |
| 2 | SvgSanitizer.java | HIGH | XSS | `disableSanitize` 绕过 SVG 净化 |
| 3 | OfficeDocumentSanitizer.java | MEDIUM | XSS | `disableSanitize` 绕过 Office 文档净化 |
| 4 | SvgOverlayUtil.java | MEDIUM | DoS | 缺少 SVG 渲染超时保护 |
| 5 | FileOrUploadService.java | MEDIUM | HardcodedSecret | 硬编码临时目录路径 `/tmp/stirling-files` |
| 6 | CredentialEncryption.java | LOW | HardcodedSecret | 加密密钥可通过 Spring 属性配置 |
| 7 | StampController.java | LOW | PathTraversal | 文件名路径穿越检查不完整 |
| 8 | ProcessExecutor.java | LOW | CommandInjection | 命令白名单缺失 |
| 9 | CompressController.java | LOW | Weak Crypto | 使用 MD5 弱哈希算法 |

---

## Agent Beta 单独发现的问题 (13个)

| # | 文件 | 严重度 | 类型 | 描述 |
|---|------|--------|------|------|
| 1 | InitialSecuritySetup.java | HIGH | HardcodedSecret | 硬编码默认管理员凭据 (admin/stirling) |
| 2 | SecurityConfiguration.java | HIGH | XSS | CSRF 保护完全禁用 |
| 3 | SecurityConfiguration.java | HIGH | XSS | CORS 配置不当 (允许所有来源+凭据) |
| 4 | SecurityConfiguration.java | MEDIUM | HardcodedSecret | IP 速率限制被禁用 (1M 次请求) |
| 5 | SecurityConfiguration.java | MEDIUM | XSS | X-Frame-Options 在登录禁用时也被禁用 |
| 6 | ExtractImageScansController.java | MEDIUM | PathTraversal | 文件名扩展名边界检查不完整 |
| 7 | PDFToFile.java | MEDIUM | CommandInjection | PDF 转 HTML 命令注入风险 |
| 8 | DatabaseController.java | MEDIUM | PathTraversal | 数据库删除接口使用 GET 方法 |
| 9 | ConvertWebsiteToPDF.java | MEDIUM | SSRF | URL 协议黑名单不完整 |
| 10 | DesktopClientUtils.java | LOW | HardcodedSecret | 桌面客户端检测依赖 User-Agent |
| 11 | DatabaseController.java | LOW | SSRF | 数据库导入错误信息泄露 |
| 12 | PipelineProcessor.java | LOW | PathTraversal | Pipeline 路径穿越检查不完整 |
| 13 | DatabaseService.java | LOW | SQLi | SQL 验证正则表达式不可靠 |

---

## 一致率分析

### 按严重度分布

| 严重度 | Alpha | Beta | 共同 | 一致率 |
|--------|-------|------|------|--------|
| HIGH | 3 | 5 | 2 | 40% |
| MEDIUM | 4 | 6 | 0 | 0% |
| LOW | 4 | 4 | 0 | 0% |

### 按漏洞类型分布

| 类型 | Alpha | Beta | 共同 | 一致率 |
|------|-------|------|------|--------|
| XSS | 3 | 4 | 1 | 20% |
| PathTraversal | 3 | 4 | 0 | 0% |
| SSRF | 1 | 3 | 1 | 25% |
| HardcodedSecret | 2 | 3 | 0 | 0% |
| CommandInjection | 1 | 1 | 0 | 0% |
| DoS | 1 | 0 | 0 | 0% |
| Weak Crypto | 1 | 0 | 0 | 0% |
| SQLi | 0 | 1 | 0 | 0% |

---

## 差异分析

### 1. 评审范围差异
- **Alpha**: 评审了约 50 个核心 Java 文件
- **Beta**: 评审了 20+ 个关键文件 (controller, service, util)

### 2. 关注点差异
- **Alpha**: 更关注 XSS 防护绕过、路径穿越、DoS 风险
- **Beta**: 更关注认证授权、CSRF、CORS、配置安全

### 3. 严重度判断差异
- **WeasyPrint SSRF**: Alpha 判定为 MEDIUM，Beta 判定为 HIGH
- **disableSanitize**: 两者都判定为 HIGH (一致)

### 4. 独特发现
- **Alpha 独特**: SVG/Office 净化绕过、SVG 渲染 DoS、临时目录硬编码
- **Beta 独特**: 硬编码管理员凭据、CSRF 禁用、CORS 配置不当、IP 速率限制禁用

---

## 结论

### 一致率评估
- **总体一致率**: 8.3% (2/24)
- **HIGH 级别一致率**: 40% (2/5)
- **MEDIUM 级别一致率**: 0% (0/10)
- **LOW 级别一致率**: 0% (0/8)

### 验证结论
1. **评审标准不统一**: 两个 Agent 的评审标准和关注点存在显著差异
2. **覆盖范围不同**: Alpha 更关注输入验证和净化，Beta 更关注认证授权和配置
3. **严重度判断不一致**: 同样的问题可能被归类为不同的严重度
4. **互补性强**: 两个 Agent 的发现互补，合计发现了更多问题

### 改进建议
1. **统一评审标准**: 明确各类漏洞的严重度判定标准
2. **扩大评审范围**: 确保覆盖所有关键模块
3. **增加交叉验证**: 对 HIGH 级别问题进行二次确认
4. **建立问题分类体系**: 统一漏洞类型分类标准

---

## 附录

### 评审报告文件
- Agent Alpha 报告: `docs/stirling-pdf-blind-test-alpha.md`
- Agent Beta 报告: `docs/stirling-pdf-blind-test-beta.md`
- 对比报告: `docs/stirling-pdf-blind-test-comparison.md` (本文件)

### 验证环境
- 验证时间: 2026-08-12
- 验证工具: code-review-skill (commit 3ca194b)
- 验证范围: Stirling-PDF 项目 (GitHub 89K stars)
- 验证语言: Java

---

> **最后更新**: 2026-08-12  
> **验证结论**: 双盲验证完成，一致率 8.3%，两个 Agent 的发现互补性强
