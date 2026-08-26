# 代码评审报告

**评审日期**: 2026-08-13
**评审项目**: vuejs/core (Vue.js 3 编译器 + SFC Playground)
**编程语言**: TypeScript (Vue.js 3)
**评审范围**: 7 个核心文件
**评审维度**: 13 个
**评审者**: Agent Beta
**版本**: V8 多语言版 (标准化评审指令)

---

## 项目概述

本次评审针对 Vue.js 3 编译器核心与 SFC Playground 的安全相关文件,包括:

- `packages-private/sfc-playground/src/` (3 个 dev-proxy 文件 + 1 个 download 文件)
- `packages/compiler-core/src/parser.ts` (HTML/SFC tokenizer 与 AST 构建器)
- `packages/compiler-sfc/src/parse.ts` (SFC 顶层解析器)
- `packages/compiler-sfc/src/template/transformAssetUrl.ts` (资源 URL 转换)

代码定位: Vue 编译器(运行于开发工具链中)+ 浏览器 Playground(运行于 iframe sandbox)。

---

## 发现的问题

### 问题 1: ZIP 文件路径遍历风险(下载项目功能)
- **文件**: `packages-private/sfc-playground/src/download/download.ts`
- **行号**: 31-38
- **严重度**: LOW
- **类型**: PathTraversal
- **描述**: `downloadProject` 函数使用 `store.getFiles()` 的所有文件键作为 ZIP 文件名,未对文件名进行规范化或白名单校验。若用户从 playground 编辑器中创建/导入一个以 `../`、`/`、绝对路径或特殊字符开头的文件名,JSZip 会将该名称作为 ZIP 内部路径使用。结合潜在的文件系统解压逻辑,可能造成 ZIP slip 漏洞。
- **代码片段**:
```typescript
const files = store.getFiles()
for (const file in files) {
  if (file !== 'import-map.json' && file !== 'tsconfig.json') {
    src.file(file, files[file])
  } else {
    zip.file(file, files[file])
  }
}
```
- **修复建议**: 在写入 ZIP 前对文件名进行白名单校验,过滤包含 `..`、`/`、`\`、绝对路径前缀等危险字符;或将其限制在 `src/` 目录下并显式拼接,例如 `src.file(path.basename(file), ...)`。

---

### 问题 2: 用户内容直接写入 ZIP(无净化)
- **文件**: `packages-private/sfc-playground/src/download/download.ts`
- **行号**: 31-38
- **严重度**: LOW
- **类型**: FileUpload (反向:文件生成)
- **描述**: `store.getFiles()` 返回的文件内容(用户/开发者在 playground 编辑器中编写的 SFC/JS/CSS)直接通过 `zip.file()` 写入压缩包,无大小限制、内容校验或恶意代码检测。若攻击者诱导用户下载或分享包含恶意脚本的 ZIP,可能造成下游受害者执行任意代码。
- **代码片段**:
```typescript
const blob = await zip.generateAsync({ type: 'blob' })
saveAs(blob, 'vue-project.zip')
```
- **修复建议**: 对内容大小设置上限(如单文件 1 MB,总大小 10 MB);对文件名与内容做 MIME/扩展名一致性校验;在文件名拼接时使用 `path.basename()` 限制;若 Playground 暴露"分享"接口,应在服务端重新生成并扫描。

---

### 问题 3: 资产 URL 转换中的路径段未规范化
- **文件**: `packages/compiler-sfc/src/template/transformAssetUrl.ts`
- **行号**: 138-154
- **严重度**: MEDIUM
- **类型**: SSRF / PathTraversal(组合)
- **描述**: 当 `options.base` 提供且 URL 以 `.` 开头时,代码使用 `path.posix.join(basePath, url.path + (url.hash || ''))` 拼接路径,未对 `url.path` 中的 `..` 段进行规范化,可能导致拼接结果越出 `basePath`。在浏览器打包场景下,该结果会被写入 `<img src=...>` 等属性的最终 URL,可能将浏览器重定向至意外的内网/外部地址(SSRF 客户端侧变体);在构建场景下,bundler 可能解析到项目目录之外的文件(路径穿越)。
- **代码片段**:
```typescript
attr.value.content =
  host +
  (path.posix || path).join(basePath, url.path + (url.hash || ''))
```
- **修复建议**: 在 `path.posix.join` 前使用 `path.posix.normalize` 并校验结果仍以 `basePath` 开头;拒绝任何包含 `..` 段的资产 URL;或在解析阶段直接将 `url.path` 限制为相对路径(不以 `/` 开头,且不含 `..`)。

---

### 问题 4: 浏览器构建中 `decodeEntities` 注入面
- **文件**: `packages/compiler-core/src/parser.ts`
- **行号**: 318-323(属性值路径)、126-130(插值路径)、594-600(文本节点)
- **严重度**: LOW
- **类型**: XSS(潜在)
- **描述**: 在 `__BROWSER__` 编译产物中,`decodeEntities` 默认为浏览器自带的实体解码器(由 `decodeHtmlBrowser.ts` 通过 `decoder.innerHTML = ...` 实现),对所有包含 `&` 的文本/属性值/插值进行解码。该实现本身安全(只读 `textContent`),但**调用面**将解码结果保留在 AST 节点的 `content` 字段,后续 codegen 会再次写入 DOM 文本节点。如果下游 codegen 路径未做 HTML 转义(在 `v-text` 等场景),理论上保留原始 HTML 字符的文本节点可能造成 XSS。本审查文件未直接包含 codegen 逻辑,但属于审查路径的薄弱环节。
- **代码片段**:
```typescript
if (__BROWSER__ && currentAttrValue.includes('&')) {
  currentAttrValue = currentOptions.decodeEntities!(
    currentAttrValue,
    true,
  )
}
```
- **修复建议**: 在文档中明确要求 codegen 阶段必须对所有动态插值使用 `escapeHtml`;`transformAssetUrl` 等已存在此类保护(`stringifyStatic.ts` 中 `escapeHtml`),需在所有 codegen 路径统一应用。

---

### 问题 5: 用户控制的内容未净化注入 `<script>`/`<style>` 文本节点
- **文件**: `packages/compiler-core/src/parser.ts`
- **行号**: 594-614(`onText`)
- **严重度**: LOW
- **类型**: XSS(潜在)
- **描述**: 当父标签为 `script` 或 `style` 时,`onText` 函数**跳过**实体解码与浏览器专用处理,直接保留原始文本。这是有意为之(`<script>` 中不应解码实体),但若 SFC 解析器对 `<script>` 内容不做进一步校验,可能允许开发者在模板字符串中嵌入任意 JS 后通过 dangerously-v-html 风格路径渲染。
- **代码片段**:
```typescript
function onText(content: string, start: number, end: number) {
  if (__BROWSER__) {
    const tag = stack[0] && stack[0].tag
    if (tag !== 'script' && tag !== 'style' && content.includes('&')) {
      content = currentOptions.decodeEntities!(content, false)
    }
  }
```
- **修复建议**: 此设计对编译器自身属合理,但建议在 SFC `<script>` 块解析时(`compiler-sfc/src/parse.ts`)对 `setup` 块加严 `lang` 白名单(如 `ts`, `js`, `tsx`, `jsx`),防止注入任意代码执行路径(已部分实现)。

---

### 问题 6: 解析器使用 `@babel/parser` 解析表达式(资源消耗 DoS)
- **文件**: `packages/compiler-core/src/parser.ts`
- **行号**: 990-1007
- **严重度**: LOW
- **类型**: 拒绝服务(资源消耗)
- **描述**: 表达式解析委托给 `@babel/parser`,默认开启 `typescript` 插件。Babel parser 对极深嵌套或病态表达式可能消耗大量 CPU/内存,在 Playground 中解析攻击者控制的 SFC 可能造成客户端浏览器卡死(并非远程 DoS,但若服务端 SSR 编译会被利用为慢速攻击)。
- **代码片段**:
```typescript
try {
  const plugins = currentOptions.expressionPlugins
  const options: BabelOptions = {
    plugins: plugins ? [...plugins, 'typescript'] : ['typescript'],
  }
  ...
  exp.ast = parseExpression(`(${content})`, options)
} catch (e: any) {
```
- **修复建议**: 在解析前对 `content` 长度设置上限(如 64 KB);对 AST 节点数或递归深度设置上限;或在 catch 块中除 `emitError` 外增加超时保护。

---

### 问题 7: HTML 实体解码使用 `innerHTML` sink
- **文件**: `packages/compiler-dom/src/decodeHtmlBrowser.ts`(非直接审查文件,但由 parser.ts 引用)
- **行号**: 10, 13
- **严重度**: MEDIUM
- **类型**: XSS(范围外的依赖)
- **描述**: 该文件由 `parser.ts` 在 `__BROWSER__` 模式下间接调用,使用 `decoder.innerHTML = raw` 解码任意输入字符串。虽然读取时只取 `textContent`,但 innerHTML sink 仍触发浏览器解析流程,可能执行嵌入的 `<script>`(现代浏览器对此有缓解,但仍存在 SVG/script in foreign content 等历史性绕过)。
- **代码片段**:
```typescript
decoder.innerHTML = `<div foo="${raw.replace(/"/g, '&quot;')}">`
return decoder.children[0].getAttribute('foo')!

decoder.innerHTML = raw
return decoder.textContent!
```
- **修复建议**: 使用 DOMParser(`new DOMParser().parseFromString('<body>'+raw, 'text/html')`)或纯文本解析库(`html-entities`)替代 innerHTML sink,以彻底避免 HTML 解析器副作用。

---

### 问题 8: VersionSelect 外部请求未限制协议/host
- **文件**: `packages-private/sfc-playground/src/VersionSelect.vue`(非直接审查文件,但与 Playground 生态相关)
- **行号**: 22-24
- **严重度**: MEDIUM
- **类型**: SSRF(客户端变体)
- **描述**: 直接对 `https://data.jsdelivr.com/v1/package/npm/${props.pkg}` 发起 `fetch`,`props.pkg` 来自 props 但在 sandbox Playground 上下文中可能受父页面或 URL 参数污染。若 `pkg` 被构造为包含 `@` 或域名前缀(如 `evil.com/redirect`),URL 可能被解析为攻击者控制的 host(SSRF 客户端变体 / CSRF via fetch)。Vue 3 编译器核心与 playground 不直接控制此文件,但属于生态边界。
- **代码片段**:
```typescript
const res = await fetch(
  `https://data.jsdelivr.com/v1/package/npm/${props.pkg}`,
)
```
- **修复建议**: 对 `pkg` 做强校验(如仅允许 `[a-z0-9-_.]` 字符);或固定白名单(`vue`, `typescript`);在生产构建中关闭动态 `pkg` 注入。

---

### 问题 9: `localStorage` 存储可预测键
- **文件**: `packages-private/sfc-playground/src/App.vue`、`Header.vue`
- **行号**: App.vue:21,101; Header.vue:61
- **严重度**: LOW
- **类型**: Session / 客户端持久化
- **描述**: `localStorage` 键 `vue-sfc-playground-auto-save`、`vue-sfc-playground-prefer-dark` 为固定明文,在 XSS 攻击下可被攻击者枚举或篡改;`autoSave` 状态由 `JSON.parse(localStorage.getItem(...) ?? 'true')` 直接解析,未捕获异常,可能因存储损坏导致初始化失败。
- **代码片段**:
```typescript
const initAutoSave: boolean = JSON.parse(
  localStorage.getItem(AUTO_SAVE_STORAGE_KEY) ?? 'true',
)
```
- **修复建议**: 将 `JSON.parse` 包裹在 try/catch 中;考虑对敏感配置(若有)使用 sessionStorage 或加前缀命名空间;不将可执行配置存入 localStorage。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题(项目不含数据库访问) |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 4、5、7(由 decodeHtmlBrowser.ts 引入的间接风险) |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题(项目无 XML 解析) |
| 4. 路径穿越 | 已检查 | 问题 1、3 |
| 5. 命令注入 | 已检查 | 无问题(无 child_process.exec/spawn) |
| 6. SSRF | 已检查 | 问题 3、8 |
| 7. 文件上传/下载 | 已检查 | 问题 1、2 |
| 8. 硬编码密钥/密码 | 已检查 | 无问题(代码中无 password/secret/apiKey 字符串,无 MD5/SHA1) |
| 9. CSRF 保护 | 已检查 | 无问题(纯前端 SPA,无服务端会话,未涉及 Cookie 认证) |
| 10. CORS 配置 | 已检查 | 无问题(无服务端 CORS 配置代码,fetch 调用未触发跨域凭证) |
| 11. 认证授权 | 已检查 | 无问题(无登录/会话模块,无速率限制需求) |
| 12. 会话管理 | 已检查 | 无问题(无服务端会话,无 token) |
| 13. HttpFirewall | 已检查 | 无问题(无 Express/Node 服务端中间件代码) |

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 6 |
| **总计** | **9** |

---

## 严重度确认步骤(已执行)

1. **锁定规则校验**:
   - 问题 1(PathTraversal):锁定 LOW(Vue 编译器运行在客户端 sandbox,且 ZIP 内部路径仅在用户本机解压时生效)
   - 问题 3(SSRF/PathTraversal):锁定 MEDIUM(锁定规则:`SSRF 未验证内网 IP = MEDIUM`)
   - 问题 4-7(XSS 相关):锁定 LOW(非直接由用户 HTML 注入触发,而是 codegen 间接路径)
   - 问题 8(SSRF):锁定 MEDIUM(无协议验证 + 动态 host)
   - MD5/SHA1:全文件搜索 `md5|sha1|createHash` → 无命中 → 单独报告为 N/A(无问题)

2. **组合漏洞判定**:
   - CSRF + CORS + Cookie 组合:**不适用**(纯客户端 SPA,无服务端)
   - CSRF + 速率限制组合:**不适用**
   - 同一 `download.ts` 的多个问题(1、2)未合并(同一文件多个同类问题 → 算多个问题,符合规则)

3. **问题合并**:
   - `decodeEntities` 相关问题分布于 `parser.ts` 与 `decodeHtmlBrowser.ts`,但因责任主体不同(前者为调用方,后者为实现方),分别报告。
   - `transformAssetUrl.ts` 的 SSRF 与路径穿越合并为单一问题(同一代码段导致两种利用)。

4. **13 维度全维度报告**:已逐一报告,无问题维度明确标注"无问题"。

---

## 关键风险总结

1. **问题 7(`decodeHtmlBrowser` 使用 `innerHTML` sink)** —— MEDIUM。该文件是浏览器构建路径中 `parser.ts` 解码 HTML 实体的底层实现,在客户端 Vue runtime 路径中持续被调用。建议迁移到 DOMParser 替代方案,从源头消除 innerHTML 解析副作用。

2. **问题 3(`transformAssetUrl` 路径拼接未规范化)** —— MEDIUM。该转换器在 SFC 模板编译时执行,影响所有使用 Vite/vue-loader 的 Vue 项目;`..` 段未过滤可能在构建产物中引入意外外部资源加载或越界文件读取。

3. **问题 8(Playground `VersionSelect` 外部 fetch 未限制 host)** —— MEDIUM。Playground 是公共部署入口,`fetch` 调用拼接动态 `pkg` 字符串可能被恶意 URL 污染,在受信任 origin 上发起意外的跨域请求。

4. **问题 1、2(download.ts ZIP 文件名与内容)** —— LOW。属于用户可控数据进入导出文件的常规风险,优先级低于上述三项,但应在分享/导出链路加固。

5. **问题 4-6、9** —— LOW。分别为 XSS 间接面、DoS 资源消耗、`localStorage` 解析稳定性,均为可接受风险但建议在文档与 lint 规则中固化防御策略。

---

## 评审检查清单

- [x] 已检查所有 13 个评审维度
- [x] 已审查文件清单中的所有 7 个核心文件 + 2 个相关引用文件(decodeHtmlBrowser.ts、VersionSelect.vue)
- [x] 所有 MEDIUM/HIGH 问题都提供了代码片段(本次无 CRITICAL/HIGH,所有 MEDIUM 均提供代码)
- [x] 所有问题都使用了锁定严重度(禁止降级)
- [x] 所有问题都使用了统一的漏洞类型分类
- [x] 输出格式完全符合 V8 要求
- [x] 已应用组合漏洞判定规则(本次不适用)
- [x] 已应用问题合并规则
- [x] 评审深度达到标准要求
- [x] 已报告所有 MEDIUM/LOW 问题(包括 MD5/SHA1 搜索结果)
- [x] 已对每个维度给出明确结论
- [x] 已执行严重度确认步骤

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta
**语言**: TypeScript / Vue.js 3
