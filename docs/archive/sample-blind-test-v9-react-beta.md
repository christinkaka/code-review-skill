# 代码评审报告 - facebook/react（Beta Agent）

**评审日期**: 2026-08-13
**评审项目**: facebook/react
**编程语言**: JavaScript / Node.js (含 JSDOM 测试环境)
**评审文件**: 5 个
**评审维度**: 13 个（V9 双维度评审）
**评审者**: Agent Beta

---

## 评审说明

本报告为 V9 双维度标准化评审的 **Beta Agent** 独立评审结果。Beta Agent 侧重**代码质量、潜在风险、最佳实践违反**，同时仍按 V9 强制要求完成维度 A 的安全漏洞扫描。

本次评审范围为发布/构建脚本与测试环境代码（5 个文件），属于"辅助基础设施"范畴，并非主业务运行时代码，因此：
- **维度 A**：仅发现 1 处轻度安全隐患（无 CRITICAL/HIGH）
- **维度 B**：发现 8 项潜在风险与代码质量观察项（满足 V9"至少 3 项"强制要求）

---

## 一、安全漏洞维度 (Dimension A)

### A-CRITICAL 级别 (0 个)
无。

### A-HIGH 级别 (0 个)
无。

### A-MEDIUM 级别 (1 个)

#### A-MEDIUM-01: `parse-params.js` 中 `--commit` 参数未做 SHA 格式校验【A-SECURITY】

**文件**: `scripts/release/shared-commands/parse-params.js` (L60-63)

**代码片段**:
```javascript
if (params.commit === null) {
  console.error(theme.error`A --commit param must be specified.`);
  process.exit(1);
}

return params;
```

**风险说明**:
脚本仅校验 `--commit` 是否提供，**未校验 SHA 格式**（应为 7-40 位十六进制）。下游命令若使用 `params.commit` 拼接 shell 命令、URL 或文件路径（如 `git checkout $commit`、`curl https://api.github.com/commits/$commit`），缺乏白名单校验可能被注入恶意字符（虽因 SHA 通常使用字母数字，影响有限，但若下游脚本将其拼接至 shell 仍存在命令注入风险）。

**评级理由**:
- 在"严格 sha-only"用途下风险较低，但发布脚本是面向 CI/管理员的关键路径。
- 缺少正则校验（如 `/^[0-9a-f]{7,40}$/i`）违反输入校验最佳实践。
- 不锁死为 HIGH，因为没有直接证据证明下游存在 shell 拼接（受限于本批次审查范围）。

**修复建议**:
```javascript
if (params.commit === null) {
  console.error(theme.error`A --commit param must be specified.`);
  process.exit(1);
}
if (!/^[0-9a-f]{7,40}$/i.test(params.commit)) {
  console.error(theme.error`--commit must be a valid git SHA (7-40 hex characters).`);
  process.exit(1);
}
```

---

## 二、代码质量维度 (Dimension B)

### B-HIGH 级别 (0 个) - 可利用性需关注
无。

### B-MEDIUM 级别 (4 个) - 潜在风险

#### B-MEDIUM-01: `parse-params.js` (shared) 错误信息泄露用户输入回显【B-POTENTIAL】

**文件**: `scripts/release/shared-commands/parse-params.js` (L54-56)

**代码片段**:
```javascript
console.error(
  theme.error`Invalid release channel (-r) "${channel}". Must be "stable", "experimental", "rc", or "latest".`
);
```

**风险说明**:
错误日志未做转义直接回显用户输入。若 CI 终端日志被收集/分享（如 Slack 通知），理论上构成日志注入（log injection）。攻击者构造如 `experimental\n[FAKE LOG] Build deployed by admin` 可伪造日志条目。

**修复建议**:
对 `channel` 变量做白名单截断/清理，或在打印前用 `JSON.stringify` 转义控制字符。

---

#### B-MEDIUM-02: `publish-commands/parse-params.js` 错误信息同样未转义回显【B-POTENTIAL】

**文件**: `scripts/release/publish-commands/parse-params.js` (L54, L67)

**代码片段**:
```javascript
console.error('Only a single --tag is allowed, got: "' + params.tag + '"');
...
console.error('Unsupported tag: "' + params.tag + '"');
```

**风险说明**:
与 B-MEDIUM-01 同类问题。虽然该文件已通过 `params.tag.includes(',') || params.tag.includes(' ')` 拒绝含逗号/空格的输入，但**未拒绝换行符 (`\n` / `\r`)** 或 ANSI 转义序列（如 `\x1b[2J` 清屏）。攻击者仍可通过 `--tag $'\x1b[31mFAKE'` 注入 ANSI 颜色/控制序列，影响 CI 终端显示。

**修复建议**:
```javascript
const safeTag = JSON.stringify(params.tag);
console.error('Only a single --tag is allowed, got: ' + safeTag);
```

---

#### B-MEDIUM-03: `ReactDOMServerIntegrationEnvironment.js` 全局对象污染与潜在悬挂引用【B-POTENTIAL】

**文件**: `scripts/jest/ReactDOMServerIntegrationEnvironment.js` (L13-21)

**代码片段**:
```javascript
this.domEnvironment = new ReactJSDOMEnvironment(config, context);

this.global.window = this.domEnvironment.dom.window;
this.global.document = this.global.window.document;
this.global.navigator = this.global.window.navigator;
this.global.Node = this.global.window.Node;
this.global.addEventListener = this.global.window.addEventListener;
this.global.MutationObserver = this.global.window.MutationObserver;
```

**风险说明**:
1. **`teardown` 顺序与全局污染**：`teardown()` 中 `await this.domEnvironment.teardown()` 会销毁 JSDOM window，但**未清理 `this.global.window/document/...`** 引用。若测试在 `setup` 与 `teardown` 之间抛出异常被 Jest 跳过正常 teardown，全局引用将悬挂指向已销毁对象，可能导致后续测试用例读到失效引用并抛出 `TypeError: Cannot read properties of null (reading 'document')`。
2. **`addEventListener` 覆盖**：`this.global.addEventListener` 被替换为 JSDOM 版本，可能影响依赖原生 Node `EventEmitter` `addEventListener` 的其他库（如 `process` 上的监听器）。
3. **`MutationObserver` 跨环境泄漏**：未在 `teardown` 中恢复原始 `MutationObserver`。

**评级理由**: 在主路径下不会暴露（被 Jest 正确管理），但缺乏防御性编程，对自动化测试稳定性是中等风险。

**修复建议**:
```javascript
async teardown() {
  // 先恢复原始引用
  delete this.global.window;
  delete this.global.document;
  delete this.global.navigator;
  delete this.global.Node;
  delete this.global.addEventListener;
  delete this.global.MutationObserver;
  await this.domEnvironment.teardown();
  await super.teardown();
}
```

---

#### B-MEDIUM-04: `parse-params.js` (publish) 错误处理使用 `process.exit(1)` 而非抛错【B-CODE-QUALITY】

**文件**: `scripts/release/publish-commands/parse-params.js` (L51, L55, L68); `scripts/release/shared-commands/parse-params.js` (L57, L62)

**代码片段**:
```javascript
if (params.tag == null || params.tag === '') {
  console.error('--tag is required and must be a single dist-tag.');
  process.exit(1);
}
```

**风险说明**:
使用 `process.exit(1)` 直接终止进程的做法：
1. **不可被调用方捕获**：调用栈中如果存在 `try/catch` 或 Promise 链，难以优雅降级。
2. **跳过清理逻辑**：可能导致未完成的连接/文件句柄泄漏（虽然发布脚本通常一次性 CLI，影响较小）。
3. **测试困难**：单元测试时无法 mock 退出码。

**修复建议**:
抛出业务异常，由顶层 CLI 入口统一处理退出码：
```javascript
throw new InvalidArgumentError(`--tag is required, got ${JSON.stringify(params.tag)}`);
```

---

### B-LOW 级别 (4 个) - 最佳实践违反

#### B-LOW-01: `parse-params.js` (shared) 缺少 releaseChannel 长度上限校验【B-CODE-QUALITY】

**文件**: `scripts/release/shared-commands/parse-params.js` (L47-58)

**代码片段**:
```javascript
const channel = params.releaseChannel;
if (
  channel !== 'experimental' &&
  channel !== 'stable' &&
  channel !== 'rc' &&
  channel !== 'latest'
) {
  console.error(...);
  process.exit(1);
}
```

**风险说明**:
白名单虽然存在，但若用户传入超长字符串（如 1MB 字符串），`channel !== 'stable'` 比较本身没问题，但**直接回显到 stderr 仍会触发 O(n) 输出**。白名单应先做长度截断，或使用 `Set` 替代链式比较以提升可读性。

**修复建议**:
```javascript
const ALLOWED_CHANNELS = new Set(['experimental', 'stable', 'rc', 'latest']);
if (typeof channel !== 'string' || !ALLOWED_CHANNELS.has(channel)) { ... }
```

---

#### B-LOW-02: `parse-params.js` (publish) `tag` 白名单硬编码维护成本高【B-CODE-QUALITY】

**文件**: `scripts/release/publish-commands/parse-params.js` (L57-69)

**代码片段**:
```javascript
switch (params.tag) {
  case 'latest':
  case 'canary':
  case 'experimental':
  case 'backport':
  case 'alpha':
  case 'beta':
  case 'rc':
    break;
  default:
    console.error('Unsupported tag: "' + params.tag + '"');
    process.exit(1);
}
```

**风险说明**:
NPM dist-tag 白名单硬编码在源码中，新增 tag（如 `nightly`）需修改源码重新发布。建议配置化或从 `npm view <pkg> dist-tags` 动态拉取允许列表。

**修复建议**:
将白名单提升为模块常量 `const ALLOWED_TAGS = Object.freeze([...])`，并在包内集中导出。

---

#### B-LOW-03: `ReactJSDOMEnvironment.js` 未做资源清理与配置注入防御【B-CODE-QUALITY】

**文件**: `scripts/jest/ReactJSDOMEnvironment.js` (L11-17)

**代码片段**:
```javascript
class ReactJSDOMEnvironment extends JSDOMEnvironment {
  constructor(config, context) {
    super(config, context);
    setupDocumentReadyState(this.global.document, this.global.Event);
  }
}
```

**风险说明**:
1. **未重写 `teardown`**：依赖父类 JSDOM 环境自行清理。若父类 `jest-environment-jsdom` 未来版本变更清理策略，可能出现 window/document 句柄泄漏。
2. **未限制 `setupDocumentReadyState` 的副作用范围**：调用即修改全局 `Event` 与 `document.readyState`，应仅在必要时调用。

**修复建议**:
显式重写 `teardown` 并添加注释说明对父类实现的依赖：
```javascript
async teardown() {
  await super.teardown();
  // 显式断开 document 引用，避免悬挂
}
```

---

#### B-LOW-04: `domEventSequences.js` 测试辅助库存在 `Math` 除零与类型假设风险【B-CODE-QUALITY】

**文件**: `packages/dom-event-testing-library/domEventSequences.js` (L46-47)

**代码片段**:
```javascript
radiusX: width / 2,
radiusY: height / 2,
```

**风险说明**:
当调用方传入 `width: 0` 或 `height: 0` 时，半径为 0（无异常），但若传入 `null` 或非数字将产生 `NaN`。`NaN` 在浏览器 Touch 事件中会导致不可预测行为。

由于该文件是**测试辅助库**（不进入生产 bundle），实际安全风险接近 0，但属于代码质量隐患。

**修复建议**:
```javascript
const safeWidth = Number.isFinite(width) ? width : defaultPointerSize;
radiusX: safeWidth / 2,
```

---

## 三、13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无（本批次无 DB 代码） |
| 2. 跨站脚本 (XSS) | 已检查 | 无（测试库无 DOM 注入） |
| 3. XML 外部实体 (XXE) | 已检查 | 无（无 XML 解析） |
| 4. 路径穿越 | 已检查 | 无（无文件系统输入） |
| 5. 命令注入 | 已检查 | 无直接 `exec`，但 A-MEDIUM-01 涉及 SHA 未校验潜在间接注入 |
| 6. SSRF | 已检查 | 无（无网络请求逻辑） |
| 7. 文件上传/下载 | 已检查 | 无 |
| 8. 硬编码密钥/密码 | 已检查 | 无 |
| 9. CSRF 保护 | 已检查 | 不适用（无 Web 框架） |
| 10. CORS 配置 | 已检查 | 不适用（无服务端） |
| 11. 认证授权 | 已检查 | 不适用（无认证逻辑） |
| 12. 会话管理 | 已检查 | 不适用（无会话） |
| 13. HttpFirewall / 安全中间件 | 已检查 | 不适用（无中间件） |

**说明**: 本批次审查对象为发布脚本 + 测试环境/工具，与 1, 2, 3, 6, 7, 9, 10, 11, 12, 13 等运行时安全维度相关性低；但均已逐一确认"无问题"。

---

## 四、文件覆盖确认

| 文件 | 已评审 | 发现问题 |
|------|--------|----------|
| `scripts/release/shared-commands/parse-params.js` | 是 | A-MEDIUM-01, B-MEDIUM-01, B-LOW-01 |
| `scripts/release/publish-commands/parse-params.js` | 是 | B-MEDIUM-02, B-MEDIUM-04, B-LOW-02 |
| `scripts/jest/ReactDOMServerIntegrationEnvironment.js` | 是 | B-MEDIUM-03 |
| `scripts/jest/ReactJSDOMEnvironment.js` | 是 | B-LOW-03 |
| `packages/dom-event-testing-library/domEventSequences.js` | 是 | B-LOW-04 |

合计：**5/5 文件已覆盖**。

---

## 五、严重度确认清单

- [x] 已检查所有 13 个评审维度（多数维度为"不适用/无问题"）
- [x] 已审查文件清单中的所有文件（5/5）
- [x] 维度 A 和维度 B 都已报告
- [x] 所有维度 A 问题（A-MEDIUM-01）都提供了代码片段
- [x] 所有问题都已标注类型 [A-SECURITY/B-POTENTIAL/B-CODE-QUALITY]
- [x] 报告包含 8 个章节
- [x] 已应用组合漏洞判定规则（无适用组合）
- [x] 已应用问题合并规则（两个 parse-params.js 错误回显同类问题，**已合并**为 B-MEDIUM-01 + B-MEDIUM-02 两个独立问题，因分属不同文件且关注点不同——前者是 channel 白名单回显，后者是 tag 白名单回显）
- [x] 评审深度达到标准要求
- [x] 已报告所有维度 B 问题
- [x] 已对每个维度给出明确结论
- [x] 已执行严重度确认步骤
- [x] **至少 3 个观察项**（实际 9 个：1 个 A-MEDIUM + 4 个 B-MEDIUM + 4 个 B-LOW）
- [x] 每个问题标注了类型

---

## 六、统计

| 严重度 | 维度 A | 维度 B | 总计 |
|--------|--------|--------|------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 0 | 0 | 0 |
| MEDIUM | 1 | 4 | 5 |
| LOW | 0 | 4 | 4 |
| **总计** | **1** | **8** | **9** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| A-SECURITY | 1 |
| B-POTENTIAL | 4 |
| B-CODE-QUALITY | 5 |
| B-CONFIG | 0 |

---

## 七、关键风险总结

### 维度 A 关键风险
1. **A-MEDIUM-01**：`--commit` SHA 未做格式校验，下游若拼接 shell 命令存在间接命令注入风险。

### 维度 B 关键风险
1. **B-MEDIUM-03**：Jest 自定义环境 teardown 顺序可能导致悬挂引用，影响测试稳定性。
2. **B-MEDIUM-01/02**：发布脚本错误信息未转义用户输入，存在日志/ANSI 注入潜在风险。
3. **B-MEDIUM-04**：`process.exit(1)` 直接终止进程，不利于上层异常处理与单元测试。
4. **B-LOW-02/03**：白名单硬编码、teardown 缺失显式重写属于可维护性问题。

---

## 八、改进建议

### 安全改进建议（基于维度 A）

1. **强制 SHA 格式校验**：`scripts/release/shared-commands/parse-params.js` 的 `--commit` 参数应使用正则 `/^[0-9a-f]{7,40}$/i` 校验，失败时给出明确错误信息并退出。
2. **建立发布脚本输入白名单矩阵**：所有 CLI 参数（channel、tag、commit、package name）都应在 parse-params 层做严格白名单校验，避免下游误用。

### 代码质量改进建议（基于维度 B）

1. **统一日志转义规范**：建议封装 `safeLog(message)` 工具函数，自动用 `JSON.stringify` 转义控制字符与换行符，集中应用到所有 `console.error` 调用。
2. **Jest 自定义环境 teardown 标准化**：
   - 在 `teardown()` 中先恢复 `this.global.window/document/...` 引用，再调用子环境 teardown。
   - 显式重写 `teardown` 而非依赖父类，避免跨版本兼容性风险。
3. **错误处理范式迁移**：
   - 用业务异常（`InvalidArgumentError`）替代 `process.exit(1)`，由 CLI 顶层统一处理退出码。
   - 利于单元测试 mock 异常与断言。
4. **白名单配置化**：将 NPM dist-tag、release channel 等枚举值提取为独立常量文件，避免分散在多个 `parse-params.js` 中造成重复维护。
5. **添加 eslint 规则**：`no-process-exit`（禁止在库代码中调用 process.exit）、`no-restricted-syntax`（限制对 `global.window` 等的覆盖）。
6. **测试覆盖**：为 `parse-params.js` 添加单元测试，覆盖：
   - 长字符串输入（>1MB）
   - 控制字符/换行符/ANSI 序列输入
   - 各种畸形 SHA（短、长、非 hex）
7. **文档化依赖关系**：`ReactDOMServerIntegrationEnvironment.js` 中 `addEventListener`、`MutationObserver` 的全局覆盖应在 JSDoc 中标注"可能影响依赖原生 EventEmitter 的库"，便于未来维护者理解副作用。

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Beta
**语言**: JavaScript / Node.js
**版本**: V9 (双维度评审)