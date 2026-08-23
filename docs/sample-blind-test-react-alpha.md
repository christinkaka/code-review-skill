# 代码评审报告

**评审日期**: 2026-08-13
**评审项目**: facebook/react
**编程语言**: JavaScript / TypeScript (Node.js + React)
**评审范围**: 5 个文件
**评审维度**: 13 个
**评审者**: Agent Alpha（独立评审，未参考任何已有报告）

---

## 评审范围

| # | 文件 | 类型 | 行数 |
|---|------|------|------|
| 1 | `scripts/release/shared-commands/parse-params.js` | 发布脚本 / CLI 参数解析 | 66 |
| 2 | `scripts/release/publish-commands/parse-params.js` | 发布脚本 / CLI 参数解析 | 72 |
| 3 | `scripts/jest/ReactDOMServerIntegrationEnvironment.js` | Jest 测试环境 | 33 |
| 4 | `scripts/jest/ReactJSDOMEnvironment.js` | Jest 测试环境 | 19 |
| 5 | `packages/dom-event-testing-library/domEventSequences.js` | DOM 事件测试库 | 361 |

---

## 文件用途速览

- `parse-params.js`（两个）：使用 `command-line-args` 解析 CLI 选项，对 `--releaseChannel`、`--tag` 等做白名单校验。
- `ReactDOMServerIntegrationEnvironment.js`：扩展 `jest-environment-node`，构造时通过内部 `ReactJSDOMEnvironment` 创建 jsdom DOM，并把 `window/document/navigator` 等挂到 `global`。
- `ReactJSDOMEnvironment.js`：扩展 `jest-environment-jsdom`，在构造时调用 `setupDocumentReadyState`。
- `domEventSequences.js`：根据指针类型（mouse / touch）合成 `pointerdown/pointerup/touchstart/click` 等事件序列，通过 `target.dispatchEvent` 派发。

---

## 发现的问题

经对 5 个文件逐行审查并交叉验证 13 个 V8 维度后，**未在评审范围内发现明确的安全漏洞**。

下列问题作为边界观察记录（属于代码质量 / 最佳实践层面，不构成 V8 严重度锁定规则所覆盖的漏洞）：

### 观察项 1（不计入严重度统计）
- **文件**: `scripts/release/shared-commands/parse-params.js`、`scripts/release/publish-commands/parse-params.js`
- **行号**: shared 48-58；publish 49-69
- **严重度**: LOW（最佳实践，未触发 V8 锁定规则）
- **类型**: Auth（输入校验）
- **描述**: 错误信息通过 `console.error` 直接回显用户输入的 `--releaseChannel` / `--tag` 值。在终端本地环境下无风险（值已在白名单中被拒绝），但若未来有调用方把这些错误流重定向到日志聚合系统并对外展示，可能反射少量非预期字符。建议改为对校验失败值做掩码处理。
- **代码片段**:
```javascript
// shared-commands/parse-params.js:55
console.error(
  theme.error`Invalid release channel (-r) "${channel}". Must be "stable", "experimental", "rc", or "latest".`
);

// publish-commands/parse-params.js:67
console.error('Unsupported tag: "' + params.tag + '"');
```
- **修复建议**: 仅在日志/错误信息中打印枚举值或脱敏值（如 `"x".repeat(len)`），不直接回显原始用户输入。

> 备注：此观察项不计入下方的"严重度统计"，因为它未触发任何 V8 严重度锁定规则（不属于禁用净化器、CORS * + credentials、Path.resolve 无验证、硬编码管理员凭据、SSRF 内网、SAX 实体、速率限制、MD5/SHA1、HttpFirewall 换行符中的任何一类）。

---

## 13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 (SQLi) | 已检查 | 无问题。5 个文件均未使用任何 SQL/ORM/查询构造器；`domEventSequences.js` 仅做对象合并与事件派发；两个 `parse-params.js` 仅做白名单字符串校验后返回，无 SQL 路径。 |
| 2. 跨站脚本 (XSS) | 已检查 | 无问题。检索整个 `scripts/` 与 `packages/dom-event-testing-library/` 均未发现 `dangerouslySetInnerHTML` / `innerHTML` / `outerHTML` / `document.write` / `v-html`（仅在 `scripts/error-codes/codes.json` 错误文案中出现 "dangerouslySetInnerHTML" 字面量，属错误信息字符串，不是代码执行点）。`domEventSequences.js` 仅创建普通 JS 对象并 `dispatchEvent`，未向 DOM 注入 HTML 字符串。 |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题。5 个文件均无 XML 解析器调用，无 `DocumentBuilderFactory` / `SAXParserFactory` / `XMLInputFactory` 调用。 |
| 4. 路径穿越 (Path Traversal) | 已检查 | 无问题。5 个文件中无 `path.resolve` / `path.join` 拼接用户输入并写入的代码；`ReactJSDOMEnvironment.js` / `ReactDOMServerIntegrationEnvironment.js` 仅是 Jest 环境类，没有文件系统操作。 |
| 5. 命令注入 (Command Injection) | 已检查 | 无问题。5 个文件均无 `child_process` 调用，无 `exec` / `spawn` / `execFile`。两个 `parse-params.js` 仅返回解析后的对象；`ReactJSDOMEnvironment.js` / `ReactDOMServerIntegrationEnvironment.js` 仅构造对象与设置全局；`domEventSequences.js` 仅做事件对象构造与 `dispatchEvent`。**说明**：评审范围外的 `scripts/release/shared-commands/download-build-artifacts.js`、`scripts/release/publish-commands/validate-skip-packages.js` 存在 `exec()` 字符串拼接命令的模式（`which ${name}`、`npm view ${dependency}@${version}`、`curl ...?head_sha=${commit}` 等），但它们不在本评审范围内，不计入本次问题列表。 |
| 6. SSRF | 已检查 | 无问题。5 个文件均无 `fetch` / `axios` / `https.request` / `http.request` 调用。**说明**：评审范围外的 `scripts/release/shared-commands/download-build-artifacts.js` 与 `scripts/tasks/generate-changelog/data.js` 含 SSRF 表面（GitHub API / NPM registry），不在本次评审范围。 |
| 7. 文件上传/下载 | 已检查 | 无问题。5 个文件均不处理上传/下载文件流；`ReactJSDOMEnvironment.js` / `ReactDOMServerIntegrationEnvironment.js` 不涉及文件 I/O。 |
| 8. 硬编码密钥/密码 | 已检查 | 无问题。检索 5 个文件未发现硬编码 `password` / `secret` / `token` / `api_key`。`scripts/release/ci-npmrc` 使用 `${NPM_TOKEN}` 占位符由环境变量注入（非硬编码），但该文件不在 5 个文件清单内。**MD5/SHA1 检查**：5 个文件无 `crypto.createHash` / `md5` / `sha1` 调用；项目根目录 `yarn.lock` 中 `md5@^2.2.1` 是传递依赖（与 `scripts/bench` 的 hacker-news benchmark 相关），不在评审范围。 |
| 9. CSRF 保护 | 已检查 | 无问题。5 个文件均为构建期 / 测试期 CLI 工具与测试环境，无 HTTP 服务监听，无表单提交，因此 CSRF 维度不适用。 |
| 10. CORS 配置 | 已检查 | 无问题。5 个文件未配置 CORS，无 `allowedOrigins` / `allowCredentials`；同上，无 HTTP 服务维度，CORS 不适用。 |
| 11. 认证授权 (Auth) | 已检查 | 无问题。5 个文件无登录/会话/令牌校验逻辑。`scripts/release/shared-commands/parse-params.js` 与 `scripts/release/publish-commands/parse-params.js` 对 CLI 选项做了白名单校验，但 CLI 工具不属于"认证授权"范畴；输入校验是良好实践，未发现授权绕过。 |
| 12. 会话管理 (Session) | 已检查 | 无问题。5 个文件无 Cookie / Session / Token 生命周期管理；该维度不适用。 |
| 13. HttpFirewall / 安全中间件 | 已检查 | 无问题。5 个文件无 Express/HTTP 中间件，无 `helmet` / `StrictHttpFirewall` 等配置点；该维度不适用。 |

---

## 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |
| **总计（计入 V8 锁定规则）** | **0** |

注：上述"观察项 1"作为边界观察项未计入统计，因为未触发任何 V8 严重度锁定规则。

---

## 严重度确认步骤（V8 强制）

- [x] CSRF + CORS + Cookie 组合检查：5 文件均无 HTTP 服务，组合不适用。
- [x] CSRF + 速率限制组合检查：同上，不适用。
- [x] `disableSanitize` 可禁用净化器锁定：未发现 `dangerouslySetInnerHTML` / `innerHTML` 等绕过净化器的代码，不适用。
- [x] `allowedOriginPatterns("*") + allowCredentials(true)` 锁定：未发现 CORS 配置，不适用。
- [x] `Path.resolve(userInput)` 无验证锁定：未发现文件路径处理，不适用。
- [x] 硬编码管理员凭据锁定：未发现硬编码凭据，不适用。
- [x] SSRF 未验证内网 IP 锁定：5 文件无 SSRF 表面，不适用。
- [x] `SAXSVGDocumentFactory` 未禁用外部实体锁定：5 文件无 XML 解析，不适用。
- [x] 速率限制禁用/极高值锁定：无 HTTP 服务，不适用。
- [x] MD5/SHA1 用于任何场景锁定：5 文件无 MD5/SHA1 使用，不适用。
- [x] HttpFirewall 允许换行符锁定：无 HTTP 服务，不适用。

---

## 评审边界与重要说明

1. **评审范围严格限定于 5 个文件**：本次评审未涉及 `scripts/release/` 目录下其他文件（如 `download-build-artifacts.js`、`validate-skip-packages.js`、`build-artifacts.js`、`publish-to-npm.js` 等）。如需扩展评审，建议下一轮重点覆盖这些文件，其中：
   - `scripts/release/shared-commands/download-build-artifacts.js`：`exec()` 字符串拼接 `${commit}`、`${REPO}`、`${WORKFLOW_ID}` 进入 `curl` 命令；同时执行 `which ${name}`；且从环境变量读取 `GH_TOKEN` 后通过 shell `-H` 头传递，存在命令注入与 token 泄漏到进程列表风险。
   - `scripts/release/publish-commands/validate-skip-packages.js`：`execRead(\`npm view ${dependency}@${version}\`)` 中 `${dependency}` / `${version}` 来自被遍历的 `package.json` 依赖字段（非直接用户输入，但若 `package.json` 被污染可触发命令注入）。
   - `scripts/release/publish-commands/publish-to-npm.js`：`spawnSync('npm', [...])` 使用列表参数，相对安全；`packagePath` 由 `join(cwd, 'build/node_modules', packageName)` 拼接，`packageName` 来自上游配置，存在路径穿越风险（应评估其锁定的允许列表）。
2. **未发现的维度说明**：CSRF、CORS、Session、Auth、HttpFirewall 在本评审范围（构建期 CLI + Jest 测试环境 + 浏览器事件序列库）内不适用，故均明确说明"无问题"而非"未检查"。
3. **独立评审声明**：本报告由 Agent Alpha 独立完成，未参考 `docs/` 目录下任何已有 blind-test / sample-blind-test 报告。

---

## 关键风险总结

本评审范围内的 5 个文件总体安全状况良好，未发现需立即修复的 V8 锁定规则覆盖的漏洞。

- 三个最值得后续跟进（**出范围**）的风险点：
  1. `scripts/release/shared-commands/download-build-artifacts.js` 中 `exec()` 字符串拼接命令 + SSRF（curl 任意 `commit` / `REPO`）。
  2. `scripts/release/publish-commands/validate-skip-packages.js` 中 `exec(\`npm view ${dependency}@${version}\`)` 的命令注入。
  3. `scripts/release/shared-commands/parse-params.js` 与 `scripts/release/publish-commands/parse-params.js` 在错误信息中回显原始用户输入的最佳实践改进（已记为观察项）。

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Alpha
**语言**: TypeScript / JavaScript (Node.js + React)
