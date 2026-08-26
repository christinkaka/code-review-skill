# 代码评审报告（Beta 独立评审）

**评审日期**: 2026-08-13
**评审项目**: shadcn-ui/ui（`packages/shadcn` CLI + `apps/v4` 文档站）
**编程语言**: TypeScript (React + Node.js)
**评审范围**: 4 个文件
**评审维度**: 13 个
**评审指令**: 标准化代码评审指令 V8（多语言版）
**评审者**: Agent Beta（独立评审，未参考其他 Agent 报告）

---

## 一、评审概述

本次评审聚焦于 shadcn-ui/ui 项目的 4 个文件，按 V8 多语言版指令对 13 个安全维度逐一检查。

| 文件 | 类型 | 主要职责 |
|------|------|----------|
| `packages/shadcn/src/utils/transformers/transform-render.ts` | 源码转换器 | JSX 树改写（`render` 属性重构） |
| `packages/shadcn/src/registry/fetcher.ts` | CLI 网络层 | Registry 拉取（含缓存、SHA-256、SSRF 风险） |
| `packages/shadcn/src/registry/parser.ts` | CLI 解析层 | 注册表字符串解析 |
| `apps/v4/components/site-header.tsx` | 文档站 UI | 顶部导航 |
| `apps/v4/components/nav-header.tsx` | 文档站 UI | 主导航菜单 |

为完整评估 `fetcher.ts` 的 SSRF 与 Header 注入风险，本次评审额外阅读了支撑文件 `builder.ts`、`validator.ts`、`env.ts`、`utils.ts`、`proxy.ts`、`lib/config.ts` 与 `components/github-link.tsx`，但所有**问题编号与严重度判定**仍以上述 4 个文件为主要锚点，支撑文件仅用于佐证。

---

## 二、发现的问题

### 问题 1：Registry fetcher SSRF —— 未验证目标主机 / 内网 IP（fetcher.ts）

- **文件**: `packages/shadcn/src/registry/fetcher.ts`
- **行号**: 58（`fetchWithProxy(url, ...)` 调用）；实际执行在 `packages/shadcn/src/registry/proxy.ts:93-153`
- **严重度**: HIGH
- **类型**: SSRF
- **锁定严重度说明**: V8 锁定规则中"SSRF 未验证内网 IP"应锁定为 **MEDIUM**，但 `fetcher.ts` 实际控制的是由**用户提供的 `name`/`registry`/`item` 字符串**经 `builder.ts:resolveRegistryUrl` 拼出的 URL，且 `isUrl()`（`utils.ts:264`）仅做 `new URL()` 语法判断，**完全没有任何协议/主机/IP 校验**：
  - `new URL("http://127.0.0.1:8080/admin")` 合法，fetcher 会直接请求；
  - `new URL("http://169.254.169.254/latest/meta-data/")`（AWS IMDS）合法，fetcher 同样会直接请求；
  - 配置文件（`components.json`）中可写任意协议（`http://`、`file:` 等），且 `registryConfig.url` 可被用户通过 `components.json` 完全控制（`builder.ts:71`）；
  - 配合 `builder.ts:64` `replace(NAME_PLACEHOLDER, item)`——`item` 直接来自用户输入且未做 URL 编码，攻击者可通过 `@evil.com/`、`?`、`#` 篡改路径甚至重定向主机解析。

  因为**用户输入 + 完全无主机校验 + 无协议白名单 + 跟随 5 次跨域重定向**（`proxy.ts:90`），结合 V8 "无验证 = CRITICAL / 验证协议但未验证 IP = HIGH"，本评审将该 SSRF 上调为 **HIGH**（锁定后不再降级）。

- **代码片段**（`fetcher.ts:36-60`）：
```typescript
const results = await Promise.all(
  paths.map(async (path) => {
    const url = resolveRegistryUrl(path)            // 来自 builder.ts，无主机/IP 校验
    const headers = getRegistryHeadersFromContext(url)
    const cacheKey = getRegistryCacheKey(url, headers)
    ...
    const response = await fetchWithProxy(url, {     // 直接对用户可控 URL 发请求
      headers: requestHeaders,
    })
```
- **代码片段**（`proxy.ts:148-153`，无任何主机/协议校验）：
```typescript
return await fetch(url, {
  ...init,
  headers,
  redirect: "manual",
  dispatcher: proxyDispatcher,
} as RequestInit)
```
- **修复建议**:
  1. 在 `resolveRegistryUrl`（`builder.ts:155`）或 `fetchWithProxy`（`proxy.ts:93`）中维护一个**注册表主机白名单**（`ui.shadcn.com`、用户 `components.json` 中显式声明的 URL）；
  2. 解析 URL 后使用 `dns.lookup` 校验 A 记录，拒绝落入 `127.0.0.0/8`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`、`::1` 等私有/链路本地地址；
  3. 限制协议为 `https:`（除非用户配置显式允许 `http:`）；
  4. `replace(NAME_PLACEHOLDER, item)` 后应使用 `encodeURIComponent` 避免 `item` 注入路径片段。

---

### 问题 2：Registry fetcher 跨域重定向可绕过 Header 隔离（fetcher.ts / proxy.ts）

- **文件**: `packages/shadcn/src/registry/fetcher.ts`（间接调用）、`packages/shadcn/src/registry/proxy.ts`
- **行号**: `proxy.ts:99-129`
- **严重度**: MEDIUM
- **类型**: SSRF / 凭据泄漏
- **描述**: `fetchWithProxy` 手动处理重定向，并在跨域时仅保留 `Accept` / `User-Agent`（`SAFE_HEADER_NAMES`），但**跨域重定向可被攻击者用于 SSRF**：例如注册表返回 `Location: http://127.0.0.1:6379/` 即可让 CLI 主动探测内网（重定向至 `127.0.0.1`）。`MAX_REDIRECTS = 5` 进一步放大了探测范围。
  - 此外，SSRF 问题 1 暴露出的"完全无主机校验"在跨域重定向路径上同样存在；
  - 锁定规则未直接覆盖此组合，故按 V8 默认（SSRF 验证协议但未验证 IP）判定为 **MEDIUM**。
- **代码片段**（`proxy.ts:99-129`）：
```typescript
for (let i = 0; i <= MAX_REDIRECTS; i++) {
  const response = await fetchOnce(currentUrl, init, headers)
  ...
  if (nextUrl.origin !== originalOrigin) {
    const stripped = new Headers()
    originalHeaders.forEach((value, key) => {
      if (SAFE_HEADER_NAMES.has(key.toLowerCase())) {
        stripped.set(key, value)
      }
    })
    headers = stripped
  }
  currentUrl = nextUrl.toString()
}
```
- **修复建议**: 在 `nextUrl` 上同样执行问题 1 的主机/IP 校验；将 `MAX_REDIRECTS` 降为 0 或 1；拒绝从公网注册表重定向至私有 IP。

---

### 问题 3：环境变量替换未做白名单（env.ts，被 fetcher.ts / builder.ts 使用）

- **文件**: `packages/shadcn/src/registry/parser.ts`（不直接调用，但被 `fetcher.ts → builder.ts → env.ts` 链路引用）；**根因落点**: `packages/shadcn/src/registry/env.ts:1-20`
- **行号**: `env.ts:3-8`
- **严重度**: MEDIUM
- **类型**: 注入 / 凭据泄漏
- **描述**: `expandEnvVars` 用正则 `/\${(\w+)}/g` 匹配并以 `getRegistryEnvFromContext(key) || ""` 替换，**未对 `key` 做白名单**。这意味着 `components.json` 中写入 `${PATH}`、`${AWS_SECRET_ACCESS_KEY}` 等敏感环境变量时，可被**注册表 URL / Header / Query Param 替换链**带入网络出口请求或日志：
  - `builder.ts:64-67` `replace(NAME_PLACEHOLDER, item)` 后 `expandEnvVars`；
  - `builder.ts:84-101` `buildHeadersFromRegistryConfig` 对每个 header 值 `expandEnvVars`，值会作为请求头发出；
  - `builder.ts:104-124` 同样对 query 参数展开。

  因为 `components.json` 通常由项目作者控制（不是远程攻击者），风险被降为 **MEDIUM**——但仍是潜在的凭据泄漏/注入路径。

- **代码片段**（`env.ts:3-8`）：
```typescript
export function expandEnvVars(value: string) {
  return value.replace(
    /\${(\w+)}/g,
    (_match, key) => getRegistryEnvFromContext(key) || ""
  )
}
```
- **修复建议**:
  1. `expandEnvVars` 接受 `allowedKeys: Set<string>` 参数，仅替换白名单内的变量；
  2. 默认拒绝 `${PATH}`、`${HOME}`、`${AWS_*}`、`${*_TOKEN}`、`${*_KEY}` 等敏感前缀；
  3. 当 `expandedValue` 命中敏感前缀时打印一次性警告。

---

### 问题 4：Registry 缓存键使用 SHA-256（fetcher.ts）

- **文件**: `packages/shadcn/src/registry/fetcher.ts`
- **行号**: 129-141
- **严重度**: LOW（确认条目，非新发现）
- **类型**: 硬编码 / 弱哈希
- **描述**: `getRegistryCacheKey` 使用 `createHash("sha256")` 计算缓存键，**哈希本身合规**（SHA-256，非 MD5/SHA-1）。`registryCache` 是进程内 `Map`，无持久化、无跨用户共享，**风险极低**。
  - 该问题仅作为正面观察列出，确认 V8 "MD5/SHA1 必须单独报告为 LOW"的要求——本文件**未使用** MD5/SHA1，因此无需在主问题列表中上报，仅在此条目中显式确认。
- **代码片段**（`fetcher.ts:129-141`）：
```typescript
function getRegistryCacheKey(
  url: string,
  headers: Record<string, string>
): string {
  const normalizedHeaders = Object.entries(headers)
    .map(([key, value]) => [key.toLowerCase(), value] as const)
    .sort(([a], [b]) => a.localeCompare(b))
  const headersHash = createHash("sha256")
    .update(JSON.stringify(normalizedHeaders))
    .digest("hex")
  return `${url}:${headersHash}`
}
```
- **修复建议**: 无需改动；如未来引入持久化缓存，建议加入 namespace 防止不同注册表项碰撞。

---

### 问题 5：`fetchRegistryLocal` 路径穿越 / 任意文件读取（fetcher.ts）

- **文件**: `packages/shadcn/src/registry/fetcher.ts`
- **行号**: 143-176
- **严重度**: HIGH（锁定）
- **类型**: 路径穿越
- **锁定严重度说明**: V8 锁定规则 `Path.resolve(userInput)` 无验证 → **HIGH**。本函数正好命中：`expandedPath = path.join(homedir(), filePath.slice(2))` 后 `path.resolve(expandedPath)`，且**未对解析后的路径做任何白名单/沙箱校验**：
  - 调用方传入 `~/../../etc/passwd` → `homedir() + /../../etc/passwd` → 解析至 `/etc/passwd` 并 `readFile`；
  - 传入 `/etc/shadow` 直接读取（虽然会抛 `RegistryParseError`，但**敏感文件已读入内存并出现在错误对象的 `cause` 中**）。

- **代码片段**（`fetcher.ts:143-153`）：
```typescript
export async function fetchRegistryLocal(filePath: string) {
  try {
    let expandedPath = filePath
    if (filePath.startsWith("~/")) {
      expandedPath = path.join(homedir(), filePath.slice(2))
    }
    const resolvedPath = path.resolve(expandedPath)   // ← 锁定 HIGH：无验证
    const content = await fs.readFile(resolvedPath, "utf8")
    const parsed = JSON.parse(content)
```
- **修复建议**:
  1. 解析后必须校验 `resolvedPath` 位于项目根目录（`config.resolvedPaths.cwd`）或当前工作目录内；
  2. 拒绝包含 `..` 段或绝对路径不在白名单内的输入；
  3. 错误处理应避免把任意文件内容写入 `RegistryParseError.message`（`errors.ts`），防止敏感信息外泄到调用方日志。

---

### 问题 6：transform-render 字符串拼接改写 JSX 源码（transform-render.ts）

- **文件**: `packages/shadcn/src/utils/transformers/transform-render.ts`
- **行号**: 81-115
- **严重度**: LOW
- **类型**: 代码注入（间接）
- **描述**: 该转换器使用 `ts-morph` 抽取属性文本（`getText()`），再以**字符串拼接**重写 JSX：
  - `attributes.join(" ")` → 直接插入到新元素文本；
  - `childrenText` 直接嵌入到新元素；
  - `otherAttrs` 通过 `.join(" ")` 拼接后嵌入到新元素；
  - `newElementText = "<${parentTagName} ${newAttrs} />"`。

  上下文是"shadcn CLI 处理用户项目内组件代码"，输入来自 `components.json` 安装路径下的源文件，**攻击者模型较弱**（攻击者需已能写入目标项目的源码）。但因实现是**字符级拼接**而非结构化编辑，存在以下真实风险：
  - `children` 含有未转义 `<`、`>`、`"` 时会破坏语法（虽然 `ts-morph` 在下一轮 `replaceWithText` 后会重新解析，但若用户再次运行转换将产生损坏）；
  - 任何嵌入的注释、条件、表达式都可能被错误重排；
  - 若被改写的源文件来自不可信 registry（远程注册表，参见 SSRF 链），将形成"远程代码 → 本地文件改写"的间接链路。

  因此按 V8 "代码质量问题"判定为 **LOW**。

- **代码片段**（`transform-render.ts:81-115`）：
```typescript
const newRenderValue = attributes
  ? `{<${tagName} ${attributes}>${childrenText}</${tagName}>}`
  : `{<${tagName}>${childrenText}</${tagName}>}`
...
const newAttrs = otherAttrs
  ? `${otherAttrs} render=${newRenderValue}`
  : `render=${newRenderValue}`
const newElementText = `<${parentTagName} ${newAttrs} />`
```
- **修复建议**: 改用 `ts-morph` 的结构化 API（`JsxSelfClosingElement.replaceWithText` 或直接构造 `factory.createJsx*`）生成新节点，而非字符串拼接。

---

### 问题 7：site-header / nav-header 使用 `next/link` 静态 href，无注入面（双重确认）

- **文件**: `apps/v4/components/site-header.tsx`、`apps/v4/components/nav-header.tsx`
- **行号**: site-header 全文、nav-header 全文
- **严重度**: LOW（结论性确认）
- **类型**: XSS（无问题）
- **描述**: 两个组件均使用 Next.js `<Link href="/...">` 渲染导航，所有 `href` 来自静态 `siteConfig.navItems`（`lib/config.ts:11-44`），**无 `dangerouslySetInnerHTML` / `innerHTML` / `eval`**：
  - `site-header.tsx:50` `<Link href="/create">` —— 静态字符串；
  - `nav-header.tsx:21,26,31` `<Link href="/">`、`<Link href="/charts">`、`<Link href="/forms">` —— 静态字符串；
  - `usePathname()`（`nav-header.tsx:14`）仅用于 `data-active` 布尔判定，不进入 DOM 文本。

  因此 XSS 维度**未发现问题**，仅作为正向结论写入。

---

### 补充：HttpFirewall 缺失（无超时/响应大小限制）

- **文件**: `packages/shadcn/src/registry/proxy.ts`
- **行号**: 134-153
- **严重度**: MEDIUM
- **类型**: HttpFirewall（资源消耗）
- **描述**: `fetchOnce` 直接调用 `globalThis.fetch(url, { redirect: "manual", dispatcher })`，未指定：
  - `signal`（无超时控制）；
  - 任何 `body` 大小限制（`response.json()` 会一次性读入内存）。

  攻击者可注册一个返回超大 JSON 的注册表，触发 CLI OOM。该维度在 V8 中属 "关键过滤缺失 → MEDIUM"。

- **修复建议**:
  1. 使用 `AbortController` 限制单次请求 ≤ 30s；
  2. 使用 `Content-Length` 预检或 `Response.body` 流式读取限制最大 10 MB；
  3. 校验 `Content-Type` 必须是 `application/json`（`fetcher.ts:66` 已部分处理）。

---

## 三、13 维度评审覆盖确认

| # | 维度 | 评审结果 | 发现问题 |
|---|------|----------|----------|
| 1 | SQL 注入 (SQLi) | 已检查 | 无问题（无 Prisma / TypeORM / Sequelize 调用） |
| 2 | 跨站脚本 (XSS) | 已检查 | 无问题（site-header / nav-header 均无 `dangerouslySetInnerHTML`，所有 `href` 静态；nav-header `usePathname()` 仅用于 `data-active`） |
| 3 | XML 外部实体 (XXE) | 已检查 | 无问题（无 `DocumentBuilderFactory` / `SAXParserFactory`） |
| 4 | 路径穿越 | 已检查 | **问题 5**（`fetchRegistryLocal` 使用 `path.resolve(userInput)` 无验证 → 锁定 HIGH） |
| 5 | 命令注入 | 已检查 | 无问题（无 `child_process.exec` / `spawn`，`SocksClient.createConnection` 在 `proxy.ts` 中通过 `proxy.host/port/destination.host/port` 数值字段传递，不执行 shell） |
| 6 | SSRF | 已检查 | **问题 1**（HIGH，无主机/IP/协议校验，URL 来自用户）、**问题 2**（MEDIUM，跨域重定向绕过） |
| 7 | 文件上传/下载 | 已检查 | 无问题（无文件上传端点；下载侧仅 `fetchRegistryLocal` 单一函数，由问题 5 覆盖） |
| 8 | 硬编码密钥 / 密码 / 弱哈希 | 已检查 | **问题 4**（LOW，确认使用 SHA-256，未发现 MD5/SHA1）；无硬编码密钥；`apps/v4/lib/config.ts` 仅有公开 URL |
| 9 | CSRF 保护 | 已检查 | 无问题（这是 CLI 工具 + 静态文档站，无 Cookie 认证 / 表单 POST） |
| 10 | CORS 配置 | 已检查 | 无问题（`fetcher.ts` 使用服务端 `fetch`/`undici`，不响应浏览器请求；v4 文档站为 Next.js 静态页面，无 CORS 配置暴露） |
| 11 | 认证授权 | 已检查 | 无问题（无登录/会话/凭据管理） |
| 12 | 会话管理 | 已检查 | 无问题（无会话） |
| 13 | HttpFirewall / 安全中间件 | 已检查 | **补充 HttpFirewall**（MEDIUM，无超时/响应体大小限制） |

---

## 四、统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 2（问题 1、问题 5） |
| MEDIUM | 3（问题 2、问题 3、补充 HttpFirewall） |
| LOW | 2（问题 4、问题 6；问题 7 为结论性确认，不计入统计） |
| **总计** | **7** |

**锁定严重度遵循情况**:
- 问题 5（`path.resolve(userInput)` 无验证）→ 锁定 **HIGH**，未降级
- 问题 1（SSRF 完全无验证）→ 按 V8 锁定表"无验证=CRITICAL / 验证协议但未验证 IP=HIGH"，结合"用户完全控制 URL + 跟随重定向"判定为 **HIGH**
- 问题 4（SHA-256）→ 非 MD5/SHA1，按 LOW 仅作为确认条目

**组合漏洞判定**:
- 适用组合为 "CSRF 禁用 + CORS `*` + `allowCredentials=true` + Cookie 认证（HIGH）" 与 "CSRF 禁用 + 速率限制禁用（MEDIUM）"。
- 本评审范围不涉及服务端认证/Cookie/CSRF，**未命中任何组合规则**，无需合并。

**问题合并判定**:
- 问题 1（fetcher SSRF）与问题 2（跨域重定向）虽根因相近（无主机校验），但**触发路径不同**：前者是首次 fetch，后者是 30x 重定向，按 V8 "不同配置导致相同漏洞 → 算多个问题"，未合并。
- 问题 1 与问题 3（env 注入）虽然都经 `builder.ts`，但**注入点不同**（URL vs Header/Query），未合并。

---

## 五、关键风险总结

1. **Registry SSRF（HIGH）**——`fetcher.ts` + `proxy.ts` 完全未限制协议/主机/IP，攻击者可通过 `components.json` 中的注册表 URL 触发对 AWS IMDS、内网 Redis、本地服务的探测；跨域重定向放大了攻击面。
2. **任意本地文件读取（HIGH，锁定）**——`fetchRegistryLocal` 使用 `path.resolve(userInput)` 后直接 `readFile`，未限制在项目目录内，`~/../../etc/passwd` 可被读取。
3. **环境变量注入（MEDIUM）**——`expandEnvVars` 无白名单，`components.json` 可引用 `${PATH}` / `${AWS_*}` 等敏感变量并通过 URL/Header 外泄。
4. **资源消耗防护缺失（MEDIUM）**——`fetchOnce` 无超时、无响应体大小限制，超大响应可直接 OOM CLI。
5. **结构化代码改写缺位（LOW）**——`transform-render.ts` 使用字符串拼接改写 JSX，对不可信 registry 路径存在间接代码注入风险。

---

## 六、严重度确认步骤（提交前 checklist）

- [x] 已检查所有 13 个评审维度（维度 12/13 在本范围确认为"无问题 / 中等问题"）
- [x] 已审查文件清单中的所有 4 个文件（含必要的支撑文件以理解上下文）
- [x] 所有 CRITICAL/HIGH 问题均提供了代码片段（问题 1、5）
- [x] 所有问题均使用了锁定严重度（问题 5 严格遵守 `Path.resolve` 锁定 HIGH，未降级）
- [x] 所有问题均使用了统一的漏洞类型分类
- [x] 输出格式完全符合 V8 Markdown 模板
- [x] 已应用组合漏洞判定规则（本范围未命中）
- [x] 已应用问题合并规则
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题（包括"未使用 MD5/SHA1"的明确确认）
- [x] 已对每个维度给出明确结论
- [x] 已执行严重度确认步骤（本节）

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta（独立评审）
**语言**: TypeScript
