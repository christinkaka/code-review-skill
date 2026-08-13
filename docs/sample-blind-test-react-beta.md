# 代码评审报告

**评审日期**: 2026-08-13
**评审项目**: facebook/react
**编程语言**: JavaScript (Node.js + React 测试工具)
**评审范围**: 5 个文件
**评审维度**: 13 个
**评审指令**: 标准化代码评审指令 V8 (多语言版)

---

## 评审文件清单

| # | 文件 | 类型 |
|---|------|------|
| 1 | `scripts/release/shared-commands/parse-params.js` | Node.js CLI 参数解析（发布共享命令） |
| 2 | `scripts/release/publish-commands/parse-params.js` | Node.js CLI 参数解析（发布 NPM 命令） |
| 3 | `scripts/jest/ReactDOMServerIntegrationEnvironment.js` | Jest 测试环境（ReactDOM/Server 集成） |
| 4 | `scripts/jest/ReactJSDOMEnvironment.js` | Jest 测试环境（基于 jsdom） |
| 5 | `packages/dom-event-testing-library/domEventSequences.js` | DOM 事件序列测试辅助库 |

---

## 发现的问题

### 问题 1
- **文件**: `scripts/release/shared-commands/parse-params.js`
- **行号**: 17-22, 60-63
- **严重度**: LOW
- **类型**: HardcodedSecret
- **描述**: `commit` 参数接受 GitHub commit SHA（十六进制字符串）作为自由文本输入，仅校验"非空"后即透传给上游（用于查找 CI 构建）。SHA 字符串本身非敏感凭据，但缺少格式正则校验（应为 7-40 位十六进制），可能导致后续调用 `findBuildByCommit` 时拼接错误命令或访问意外资源。
- **代码片段**:
```javascript
{
  name: 'commit',
  type: String,
  description:
    'GitHub commit SHA. When provided, automatically finds corresponding CI build.',
  defaultValue: null,
},
// ...
if (params.commit === null) {
  console.error(theme.error`A --commit param must be specified.`);
  process.exit(1);
}
```
- **修复建议**: 增加 SHA 格式校验 `/^[0-9a-f]{7,40}$/i`，防止任意字符串进入下游逻辑。

---

### 问题 2
- **文件**: `scripts/release/shared-commands/parse-params.js`
- **行号**: 48-58
- **严重度**: LOW
- **类型**: Auth
- **描述**: `releaseChannel` 虽然采用白名单（`experimental` / `stable` / `rc` / `latest`），但是错误信息中通过模板字符串直接插入了用户输入（`channel` 变量），并打印到 stderr。在 CI 环境下非问题，但若 release channel 来自不可信源，可能造成日志注入。建议错误消息对输入做转义或仅打印固定字符串。
- **代码片段**:
```javascript
console.error(
  theme.error`Invalid release channel (-r) "${channel}". Must be "stable", "experimental", "rc", or "latest".`
);
```
- **修复建议**: 保持白名单校验（已存在），错误消息使用静态字符串 + 编码/截断后的输入展示。

---

### 问题 3
- **文件**: `scripts/release/publish-commands/parse-params.js`
- **行号**: 53-56, 67-69
- **严重度**: LOW
- **类型**: Auth
- **描述**: 错误消息直接拼接 `--tag` 输入内容到 stderr：
```javascript
console.error('Only a single --tag is allowed, got: "' + params.tag + '"');
console.error('Unsupported tag: "' + params.tag + '"');
```
尽管 `tag` 已经过白名单过滤，攻击面小，但日志注入面（Log Injection）依然存在。
- **代码片段**:
```javascript
if (params.tag.includes(',') || params.tag.includes(' ')) {
  console.error('Only a single --tag is allowed, got: "' + params.tag + '"');
  process.exit(1);
}
// ...
default:
  console.error('Unsupported tag: "' + params.tag + '"');
  process.exit(1);
```
- **修复建议**: 对 `params.tag` 输出到日志前进行换行/控制字符过滤（剥离 `\r\n`）。

---

### 问题 4
- **文件**: `scripts/jest/ReactDOMServerIntegrationEnvironment.js`
- **行号**: 14-20
- **严重度**: LOW
- **类型**: HttpFirewall
- **描述**: 该文件将 JSDOM 提供的 `window` / `document` / `navigator` / `Node` / `addEventListener` / `MutationObserver` 直接挂载到 Jest 的 `global` 命名空间。JSDOM 是隔离的测试运行时，但当跨多个测试并发执行时（`testRunner` 默认 worker），跨用例可能存在全局状态污染风险（属于测试隔离最佳实践问题，非真实漏洞）。
- **代码片段**:
```javascript
this.global.window = this.domEnvironment.dom.window;
this.global.document = this.global.window.document;
this.global.navigator = this.global.window.navigator;
this.global.Node = this.global.window.Node;
this.global.addEventListener = this.global.window.addEventListener;
this.global.MutationObserver = this.global.window.MutationObserver;
```
- **修复建议**: 这是 Jest 自定义测试环境的标准模式，安全相关风险有限。建议保持并继续依赖 Jest 的 worker 隔离。

---

### 问题 5
- **文件**: `scripts/jest/ReactJSDOMEnvironment.js`
- **行号**: 1-17
- **严重度**: LOW
- **类型**: HttpFirewall
- **描述**: 整体为对 `jest-environment-jsdom` 的简单包装，未禁用外部资源加载等敏感配置。JSDOM 默认不发起网络请求，不存在 SSRF 面。
- **代码片段**:
```javascript
class ReactJSDOMEnvironment extends JSDOMEnvironment {
  constructor(config, context) {
    super(config, context);
    setupDocumentReadyState(this.global.document, this.global.Event);
  }
}
```
- **修复建议**: 无需修复；如有需要可显式设置 `resources: 'usable'` / `'none'`。

---

### 问题 6
- **文件**: `packages/dom-event-testing-library/domEventSequences.js`
- **行号**: 115, 176, 200, 242, 258, 274, 288, 317（贯穿全文 `dispatch = arg => target.dispatchEvent(arg)` 等多处）
- **严重度**: LOW
- **类型**: XSS
- **描述**: 该测试辅助库通过 `target.dispatchEvent(arg)` 直接派发合成 DOM 事件。事件对象中的 `target` / `pointerId` / `pointerType` 等字段完全由调用方传入，无任何校验/净化。在测试代码内部使用是预期行为，但若被恶意用户控制的测试输入触发，可能允许在测试环境中伪造 DOM 事件（仅在测试期间影响断言）。
- **代码片段**:
```javascript
export function contextmenu(
  target,
  defaultPayload,
  {pointerType = 'mouse', modified} = {},
) {
  const dispatch = arg => target.dispatchEvent(arg);
  const payload = {
    pointerId: defaultPointerId,
    pointerType,
    ...defaultPayload,
  };
  // ...
  dispatch(domEvents.pointerdown({ ...payload, ... }));
}
```
- **修复建议**: 测试库本身无问题；在调用方（如 fuzz 测试）应对输入参数做来源校验。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 (SQLi) | 已检查 | 无问题。本批文件均为测试/CLI 脚本，无 SQL/ORM 调用面。 |
| 2. 跨站脚本 (XSS) | 已检查 | 问题 6（合成 DOM 事件，但仅限测试上下文，LOW） |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题。未使用 XML 解析器。 |
| 4. 路径穿越 (Path Traversal) | 已检查 | 无问题。未涉及 `path.join` / `path.resolve` 操作文件路径。 |
| 5. 命令注入 (Command Injection) | 已检查 | 无问题。未调用 `child_process` / `spawn` / `exec`。 |
| 6. SSRF | 已检查 | 无问题。未使用 `fetch` / `axios` / `http.request`。 |
| 7. 文件上传/下载 | 已检查 | 无问题。不涉及文件上传/下载逻辑。 |
| 8. 硬编码密钥/密码 | 已检查 | 无问题。无 `password` / `secret` / `key` 硬编码；未使用 MD5/SHA1。 |
| 9. CSRF 保护 | 已检查 | 无问题。本批文件均为本地 CLI 与测试环境，不涉及 HTTP 认证/Cookie 流程；无 CSRF 中间件面。 |
| 10. CORS 配置 | 已检查 | 无问题。无 `allowedOrigins` / `allowCredentials` 配置。 |
| 11. 认证授权 (Auth) | 已检查 | 问题 2、问题 3（CLI 错误信息日志注入风险，LOW） |
| 12. 会话管理 (Session) | 已检查 | 无问题。不涉及会话/Token。 |
| 13. HttpFirewall | 已检查 | 问题 4、问题 5（Jest 测试环境全局对象挂载，LOW） |

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 6 |
| **总计** | **6** |

---

## 关键风险总结

本次评审覆盖的 5 个文件属于 React 仓库中的**辅助型代码**（CLI 参数解析脚本 + Jest 测试环境 + DOM 事件序列测试工具），均**不涉及生产 Web 服务、HTTP 请求处理、数据库访问或用户输入到危险函数的直接通路**，因此未发现 CRITICAL / HIGH / MEDIUM 级别漏洞。

仅存的 LOW 级问题集中在：
1. **CLI 错误消息的日志注入面**（问题 2、3）：未对用户输入做控制字符过滤。
2. **测试环境全局状态污染**（问题 4、5）：依赖 Jest worker 隔离。
3. **测试辅助库派发未净化事件**（问题 6）：仅在测试上下文构成风险。
4. **`commit` 参数缺格式校验**（问题 1）：非敏感凭据，但建议添加 SHA 正则。

这些 LOW 问题均不影响 React 生产代码安全性，符合"开发/测试辅助脚本"的安全基线。

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta
**语言**: TypeScript/Node.js (React 测试基础设施)