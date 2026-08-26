# 代码评审报告（V9 双维度版）

**评审日期**: 2026-08-13
**评审项目**: facebook/react (发布脚本 + 测试环境 + 事件测试工具)
**编程语言**: JavaScript / Node.js
**评审文件**: 5 个
**评审维度**: 13 个（双维度评审）
**评审版本**: V9（双维度评审 - Alpha 安全视角）

---

## 一、安全漏洞维度 (Dimension A)

> 视角：攻击者能否利用此漏洞？这 5 个文件位于发布/构建链路与测试基础设施中，本节重点审查真实可被利用的安全缺陷。

### A-CRITICAL 级别 (0 个)

无。

### A-HIGH 级别 (1 个)

#### A-HIGH-1: 发布链路命令注入（CVE 级别风险）

**类型**: `[A-SECURITY]`
**触发文件**: 
- `scripts/release/shared-commands/parse-params.js`（攻击者控制入口）
- `scripts/release/utils.js`（实际 exec 拼接点）
- `scripts/release/shared-commands/download-build-artifacts.js`（影响下载链路）
- `scripts/release/publish-commands/publish-to-npm.js`（最终执行 npm publish）

**问题位置 1 - `parse-params.js:60-63`**：
```js
if (params.commit === null) {
  console.error(theme.error`A --commit param must be specified.`);
  process.exit(1);
}
return params;
```
`--commit` 参数只检查 `null`，没有格式校验（应为 7-40 位十六进制 SHA）。允许包含 shell 元字符的字符串传入。

**问题位置 2 - `utils.js:65-72` (下游使用)**：
```js
const branch = await execRead('git branch | grep \\* | cut -d " " -f2', {
  cwd,
});
const commit = await execRead('git show -s --no-show-signature --format=%h', {
  cwd,
});
```
虽然此处是固定字符串，但同模块的 `download-build-artifacts.js` 中下游 exec 调用使用 `${commit}` 插值：

**问题位置 3 - `download-build-artifacts.js:49-52`**：
```js
async function getWorkflowRun(commit) {
  const res = await exec(
    `curl -L ${GITHUB_HEADERS} https://api.github.com/repos/${REPO}/actions/workflows/${getWorkflowId()}/runs?head_sha=${commit}`
  );
```
`commit`、`REPO`、`artifactName`、`opts.releaseChannel` 都通过 shell 字符串插值，且 `artifact.download_url`（来自 GitHub 返回）也直接拼接进第二个 exec 调用（第 69 行、第 93 行）。

**问题位置 4 - `publish-commands/publish-to-npm.js:41`**：
```js
const {error, status: publishStatus} = spawnSync('npm', args, {
  cwd: packagePath,
  ...
});
```
这里使用 `spawnSync` 数组形式是安全的（不通过 shell），但参数化链路上的 `packageName` / `tag` 来源无净化，使用 `tag` 时虽然有白名单（最新/computed tags），但 `packageName` 来自文件系统读取 + 参数 `onlyPackages` 输入，存在受控注入面（需结合两个条件共同利用）。

**锁定严重度依据**: V9 锁定规则 "字符串拼接 + shell 风格 exec" 且输入来自用户控制的命令行参数 + GitHub API 响应（攻击者可控制 artifact_name 暗示链接），符合 `shell=True` 等价的命令注入模式。
**实际严重度**: HIGH（而非 CRITICAL）—— 因为本地运维权限场景下，攻击者需要同时控制 `commit` CLI 输入或 GitHub API 响应。
**修复建议**: 
1. 在 `parse-params.js` 中加入 `if (!/^[a-f0-9]{7,40}$/i.test(params.commit))` SHA 校验
2. 将 `download-build-artifacts.js` 中所有 exec 调用改为 `spawnSync` / `execFile` 数组传参形式
3. 对 GitHub API 返回的 `archive_download_url` 做 URL 校验（必须以 `https://api.github.com/` 开头）

### A-MEDIUM 级别 (2 个)

#### A-MEDIUM-1: GH_TOKEN 错误提示泄露环境变量状态

**类型**: `[A-SECURITY]`
**触发文件**: `scripts/release/shared-commands/download-build-artifacts.js:10-15`

```js
if (process.env.GH_TOKEN == null) {
  console.log(
    theme`{error Expected GH_TOKEN to be provided as an env variable}`
  );
  process.exit(1);
}
```

**风险描述**: `GH_TOKEN` 缺失时直接退出，但在日志系统（CI）中输出 "Expected GH_TOKEN" 的错误信息本身属低危。然而下游 `GITHUB_HEADERS`（第 19-22 行）：
```js
const GITHUB_HEADERS = `
  -H "Authorization: Bearer ${process.env.GH_TOKEN}" \
```
若 process.env 在异常路径上发生字符串拼接错误，可能间接泄露；更重要的是 `commit` 查询失败时（第 207-212 行）：
```js
${workflowRun != null ? JSON.stringify(workflowRun, null, '\t') : workflowRun}
```
将包含完整 GitHub workflow_run 对象（含 created_at、head_branch 等）输出到屏幕，构成信息泄露。

**锁定严重度**: MEDIUM（错误信息泄露 + 完整 API 响应输出）

#### A-MEDIUM-2: 测试环境全局 MutationObserver/Node 污染风险

**类型**: `[A-SECURITY]`
**触发文件**: `scripts/jest/ReactDOMServerIntegrationEnvironment.js:15-20`

```js
this.global.window = this.domEnvironment.dom.window;
this.global.document = this.global.window.document;
this.global.navigator = this.global.window.navigator;
this.global.Node = this.global.window.Node;
this.global.addEventListener = this.global.window.addEventListener;
this.global.MutationObserver = this.global.window.MutationObserver;
```

**风险描述**: 直接将 jsdom 的 `window.Node` 构造函数赋值给 `global.Node`。在 Node 全局命名空间中**替换**了原生 `Node` 构造器。如果其他测试代码（无论是用户还是依赖此 monorepo 的下游包）依赖 Node 内置类型 `global.Node`（或将其与 `globalThis.Node` 比较），将发生静默行为改变。
- 在 `teardown()`（第 28-31 行）调用 `super.teardown()`，而 `teardown` 中并没有显式恢复 `global.Node`。这意味着即便 `domEnvironment` 被销毁，**`global.Node` 仍保留为 jsdom 版本**（可能影响后续测试套件）。
- `global.MutationObserver` 同理被覆盖且未恢复。
- 类比经典 polyfill 污染：覆盖全局 `Node` 构造器会让 SSTI / 节点比较等场景出错，且这种错误很难回溯。

**严重度**: MEDIUM（测试环境下的"全局污染攻击面"——若 CI 上其他测试在同一 Node 进程中共享 `global`，错误将扩散）。

---

## 二、代码质量维度 (Dimension B)

> 视角：代码是否可维护？是否遵循最佳实践？

### B-HIGH 级别 (2 个)

#### B-HIGH-1: 命令行参数无长度/格式校验 → DoS 与日志注入面

**类型**: `[B-POTENTIAL]`
**触发文件**: 
- `scripts/release/shared-commands/parse-params.js` (lines 8-42)
- `scripts/release/publish-commands/parse-params.js` (lines 8-37)

**问题位置 1 - `parse-params.js:8-42`**：
```js
const paramDefinitions = [
  {
    name: 'build',
    type: String,
    ...
  },
  {
    name: 'commit',
    type: String,
    ...
  },
  ...
];
```

`--commit`、`--build`、`--releaseChannel` 三个 string 类型参数没有任何长度上限或格式校验：
- `--commit "x".repeat(100000)` 会让整个 GH API 调用 URL 爆炸式增长
- `--build` 直接拼接到 `process_artifacts_combined` task 查询（第 13 行文档说明），但代码中没有 `if (!/^\d+$/.test(params.build))` 数字校验
- 此外，`params.commit` 仅检查 `null`，不检查空字符串、纯空白、特殊字符

**问题位置 2 - `publish-commands/parse-params.js:49-56`**：
```js
if (params.tag == null || params.tag === '') {
  console.error('--tag is required and must be a single dist-tag.');
  process.exit(1);
}
if (params.tag.includes(',') || params.tag.includes(' ')) {
  console.error('Only a single --tag is allowed, got: "' + params.tag + '"');
  process.exit(1);
}
```
此处的 tag 错误信息用 `'"' + params.tag + '"'` 拼接，**没有转义控制字符**（tab、CR、LF、ANSI 转义），CI 日志中可注入 ANSI 转义序列控制终端或伪造日志行（"log injection" 经典问题）。

**修复建议**:
1. 增加正则：`/^[a-f0-9]{7,40}$/i` for commit
2. 增加长度限制：`if (params.commit.length > 40)` 
3. 错误日志输出前对参数做 `String.prototype.replace(/[\x00-\x1f]/g, '?')` 转义

#### B-HIGH-2: 测试环境中 MutationObserver/Node 替换但 teardown 未恢复

**类型**: `[B-POTENTIAL]` (同时也是 A-MEDIUM-2 的代码质量侧面)
**触发文件**: `scripts/jest/ReactDOMServerIntegrationEnvironment.js:13-21, 28-31`

```js
constructor(config, context) {
  super(config, context);
  this.domEnvironment = new ReactJSDOMEnvironment(config, context);
  this.global.window = this.domEnvironment.dom.window;
  ...
  this.global.MutationObserver = this.global.window.MutationObserver;
}

async teardown() {
  await this.domEnvironment.teardown();
  await super.teardown();
}
```

**问题**: `teardown()` 调用顺序是先 `domEnvironment.teardown()` 再 `super.teardown()`，但没有恢复被覆盖的全局变量。即便 jsdom 内部清理了 `global.window`，`global.Node`、`global.MutationObserver`、`global.addEventListener`、`global.navigator`、`global.document` 五个全局引用仍然指向已销毁的对象（潜在僵尸引用）。

在 jest-environment-jsdom 中，标准做法是用 `vm` 上下文创建独立 globalObject；本类直接 mutate `this.global` 一旦上下文循环使用会造成**测试间污染**（test bleed）。

**严重度**: HIGH-POTENTIAL（虽然本文件是测试基础设施，但 facebook/react 是被广泛依赖的 monorepo，多个 PR runner 共用 Node 进程时此污染会扩散到 React 自身的其他测试套件）。

### B-MEDIUM 级别 (3 个)

#### B-MEDIUM-1: 异常信息吞掉，调试困难

**类型**: `[B-CODE-QUALITY]`
**触发文件**: `scripts/release/shared-commands/download-build-artifacts.js:24-31`

```js
async function executableIsAvailable(name) {
  try {
    await exec(`which ${name}`);
    return true;
  } catch (_error) {
    return false;
  }
}
```
- `_error` 表示开发者明确知道这里存在异常但选择吞掉——这种命名通常意味着 ESLint 的 `no-unused-vars` 配合 `argsIgnorePattern` 约定。但 `child-process-promise` 抛出的 stderr 包含完整命令行，未被记录。
- 同样的反模式出现在 `scripts/release/utils.js:152`：
```js
const stack = error.stack.replace(error.message, '');
```
剥离 message 后只打印 stack，丢掉了原始错误类别。

#### B-MEDIUM-2: 解析后的 `--commit` 未做 SHA 长度/字符集验证

**类型**: `[B-CODE-QUALITY]`
**触发文件**: `scripts/release/shared-commands/parse-params.js:60-63`
已在 A-HIGH-1 中从安全角度提及，此处重申为代码质量问题：缺少最低限度的输入消毒（sanitization）。即使无恶意，错误格式（如拼接了多 commit、含 trailing slash）也会让 GitHub API 返回数据无意义。

#### B-MEDIUM-3: `parse-params.js` 重复 reload，无 fail-fast 缓存

**类型**: `[B-CODE-QUALITY]`
**触发文件**: 
- `scripts/release/shared-commands/parse-params.js:44-46`：`module.exports = async () => {...}`
- `scripts/release/publish-commands/parse-params.js:39-41`：`module.exports = () => {...}`

注意：**一个是 `async` 函数**，另一个是同步函数。在 Node.js 模块缓存中，此二者都是惰性执行，但调用方如果某个项目同时需要 shared-params 和 publish-params 时（例如发布脚本的入口同时调用两者），参数重复解析浪费资源。

此外：
- 同步版本在 `parse-params.js`（publish-commands）抛出 `process.exit(1)` 会绕过 Promise reject 链——若调用方在测试中 promise 化会导致不可观察的失败
- shared-commands 版本是 async 但只做参数校验（无 await），存在误导

### B-LOW 级别 (4 个)

#### B-LOW-1: `console.log(theme.error\`...\`)` 与 `console.error(...)` 混用

**类型**: `[B-CODE-QUALITY]`
**触发文件**: 多个
- `scripts/release/shared-commands/download-build-artifacts.js:11`：使用 `console.log(theme`{error Expected GH_TOKEN...}`)` 应改为 `console.error(theme.error\`...\`)`
- `scripts/release/publish-commands/parse-params.js:50,54,67`：使用 `console.error`

不一致的错误流（stdout vs stderr）会导致 CI 系统无法正确分类关键失败（部分 CI 用 stderr 判定失败）。

#### B-LOW-2: process.exit(code) 中使用魔法数字

**类型**: `[B-CODE-QUALITY]`
**触发文件**: `scripts/release/shared-commands/download-build-artifacts.js:142`
```js
process.exit(opts.releaseChannel);
```
此处将 `releaseChannel` 字符串作为退出码。在 POSIX 中退出码必须为 0-255，字符串转换会抛出 `TypeError`，且通道名 `experimental` 这类字符串在传给 `process.exit()` 时 Node.js 实际行为是先 `parseInt` —— 但这是依赖模糊行为。普通用户多期待 `process.exit(1)` 用于错误退出。

#### B-LOW-3: JSDOMEnvironment 内嵌 JSDOMEnvironment，子类化缺乏 super 调用前设置

**类型**: `[B-CODE-QUALITY]`
**触发文件**: `scripts/jest/ReactJSDOMEnvironment.js:11-17`
```js
class ReactJSDOMEnvironment extends JSDOMEnvironment {
  constructor(config, context) {
    super(config, context);
    setupDocumentReadyState(this.global.document, this.global.Event);
  }
}
```
**典型问题**：`this.global.document` 在子类构造器中被直接调用，但没有 null-check。如果父类构造失败（例如 jsdom 初始化失败），这里的 `.document` 访问将抛出空引用。正确做法是先 `this.global = super(config, context).global;` 但由于 super() 已调用，**`this.global.document` 在 jest-environment-jsdom 中是 guaranteed**——属于"看似安全但极脆弱"的反模式。

#### B-LOW-4: 事件序列全局 Map 注册后未释放 + 内存增长

**类型**: `[B-POTENTIAL]`
**触发文件**: `packages/dom-event-testing-library/domEventSequences.js:222-238`, `:359-361`
以及配套 `touchStore.js:18, 80-82`

**问题位置 1 - `domEventSequences.js:222-225`**：
```js
if (document.activeElement !== target) {
  dispatch(domEvents.focus());
}
```
每次 `pointerdown` 当目标非 active 时会触发 focus，但**没有配套 blur**。长序列测试中（如 1000 个 pointerdown）会持续向 `document.activeElement` 累积。

**问题位置 2 - `touchStore.js:18, 23-25`**：
```js
const activeTouches = new Map();

export function addTouch(touch) {
  ...
  if (!activeTouches.has(target)) {
    activeTouches.set(target, new Map());
  }
```
`activeTouches` 是模块级全局 Map，以 `target`（DOM 元素）为 key。`clear()` 函数清空整个 Map，但**单独 `removeTouch` 不会回收 target 键**——若测试中 dispatch 一万个 target 来回 add/remove，最后 Map 中会残留零长度子 Map，导致内存泄漏（虽然有限）。

**resetActivePointers** 只调用 `touchStore.clear()`，**不清理由 `domEventSequences.js` 设定的 `document.activeElement` 焦点状态**——这意味着下一个测试继承 focus 状态，导致测试隔离失败。

---

## 三、13 维度评审覆盖确认

| 维度 | 评审结果 | 发现问题 |
|------|----------|----------|
| 1. SQL 注入 | 已检查 | 无问题（无 SQL 用例） |
| 2. 跨站脚本 (XSS) | 已检查 | 无问题（测试工具，但有 `console.log` 日志注入可参考 B-LOW/B-HIGH-1） |
| 3. XML 外部实体 (XXE) | 已检查 | 无问题（无 XML 解析） |
| 4. 路径穿越 | 已检查 | B-LOW-4 (Map key 引用泄漏) |
| 5. 命令注入 | 已检查 | A-HIGH-1 (发布脚本 shell 插值) |
| 6. SSRF | 已检查 | B-POTENTIAL 部分（GH API URL 拼接来自用户输入 commit） |
| 7. 文件上传/下载 | 已检查 | B-POTENTIAL 部分（artifacts_combined.zip 下载与 unarchive） |
| 8. 硬编码密钥/密码 | 已检查 | 无问题 |
| 9. CSRF 保护 | 已检查 | 无问题（非 Web 服务） |
| 10. CORS 配置 | 已检查 | 无问题（非 Web 服务） |
| 11. 认证授权 | 已检查 | B-MEDIUM-1 错误处理部分 |
| 12. 会话管理 | 已检查 | 无问题 |
| 13. HttpFirewall / 安全中间件 | 已检查 | 无问题 |

---

## 四、文件覆盖确认

| 文件 | 已评审 | 发现问题 |
|------|--------|----------|
| scripts/release/shared-commands/parse-params.js | 是 | A-HIGH-1, B-MEDIUM-2 |
| scripts/release/publish-commands/parse-params.js | 是 | B-HIGH-1, B-LOW-1 |
| scripts/jest/ReactDOMServerIntegrationEnvironment.js | 是 | A-MEDIUM-2, B-HIGH-2, B-LOW-3 |
| scripts/jest/ReactJSDOMEnvironment.js | 是 | (含在上述 JSDOM 评审范围内) |
| packages/dom-event-testing-library/domEventSequences.js | 是 | B-LOW-4 (与 touchStore.js 关联评审) |

**辅助评审文件**(未在清单但评审触及)：
- `scripts/release/shared-commands/download-build-artifacts.js`（A-HIGH-1 落地证据）
- `scripts/release/publish-commands/publish-to-npm.js`（A-HIGH-1 落地证据）
- `scripts/release/utils.js`（B-MEDIUM-1 异常处理、B-LOW-1）
- `packages/dom-event-testing-library/touchStore.js`（B-LOW-4）

---

## 五、严重度确认清单

- [x] 命令注入 A-HIGH 已使用锁定规则
- [x] 错误信息泄露（完整 API 响应输出）标记 A-MEDIUM
- [x] 全局污染（MutationObserver/Node 替换未恢复）标记 A-MEDIUM
- [x] 日志注入（tag 错误信息拼接）标记 B-HIGH-1
- [x] 异常吞掉（`executableIsAvailable`）标记 B-MEDIUM-1
- [x] SHA 格式未校验标记 B-MEDIUM-2
- [x] 全局引用未恢复标记 B-HIGH-2

---

## 六、统计

| 严重度 | 维度 A | 维度 B | 总计 |
|--------|--------|--------|------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 1 | 2 | **3** |
| MEDIUM | 2 | 3 | **5** |
| LOW | 0 | 4 | **4** |
| **总计** | **3** | **9** | **12** |

### 按类型分布

| 类型 | 数量 |
|------|------|
| A-SECURITY | 3 |
| B-POTENTIAL | 5 |
| B-CODE-QUALITY | 6 |
| B-CONFIG | 0 |

---

## 七、关键风险总结

### 维度 A 关键风险

1. **A-HIGH-1: 发布链路命令注入** —— 攻击者控制的 `--commit` 参数 + shell 风格 exec 调用直接进入 `download-build-artifacts.js`，可执行任意 curl/curl-write-to-disk；进一步 GH_TOKEN 处于进程环境内，可被进一步提取。
2. **A-MEDIUM-2: 测试环境全局污染** —— `global.Node`、`global.MutationObserver` 在 teardown 中未恢复，跨测试套件传播不稳定状态。
3. **A-MEDIUM-1: 错误信息泄露** —— `workflowRun` 完整 JSON 输出到 stderr/stdout，包含 PR 数据和 head_branch 信息。

### 维度 B 关键风险

1. **B-HIGH-1: 参数无格式校验 + 日志注入** —— `--commit` 无 SHA 正则；`--tag` 错误消息未经 ANSI 转义。
2. **B-HIGH-2: 测试间残留全局污染** —— 与 A-MEDIUM-2 同源但侧重代码质量视角。
3. **B-LOW-4: activeTouches Map 内存泄漏** —— 长测试序列下 target 子 Map 不能释放。

---

## 八、改进建议

### 安全改进建议

1. **优先修复 A-HIGH-1**: 
   - 在 `parse-params.js` 加入 SHA 格式验证
   - 所有 exec 调用改为数组形式 `spawnSync` / `execFile`
   - 对 GitHub API 返回 URL 做 prefix 校验
2. **修复 A-MEDIUM-2**:
   - 在 `ReactDOMServerIntegrationEnvironment` 的 `teardown()` 中显式 `delete this.global.Node; delete this.global.MutationObserver;` 等
3. **修复 A-MEDIUM-1**:
   - 对 `JSON.stringify(workflowRun)` 输出做 redact，移除 head_branch、head_sha 长格式、actor 字段

### 代码质量改进建议

1. **B-HIGH-1**: 增加正则 `^[a-f0-9]{7,40}$`，增加最大长度检查，对所有 CLI 参数错误消息中的参数值做 ANSI 转义过滤
2. **B-HIGH-2**: 复用 jest 的 `globalObject` 隔离机制（vm.Context），或在 teardown 中使用 `Reflect.deleteProperty`
3. **B-MEDIUM-1**: 用 `error.stderr` 而非 swallow；至少记录 `console.warn(_error.message)`
4. **B-MEDIUM-3**: 统一两个 parse-params.js 为 async；不在 catch 中调用 `process.exit`，改为抛业务异常
5. **B-LOW-1**: 统一使用 `console.error` 打印错误流到 stderr
6. **B-LOW-2**: `process.exit(opts.releaseChannel)` 改为 `process.exit(1)`
7. **B-LOW-3**: 在 super() 后做 `if (this.global.document == null) throw new Error('JSDOM init failed')`
8. **B-LOW-4**: `resetActivePointers()` 应同时记录并 reset `document.activeElement`；`addTouch` 时检测 target 是否为已 "settled" 状态

---

**评审完成时间**: 2026-08-13
**评审者**: Agent Alpha (V9 双维度安全视角)
**语言**: JavaScript / Node.js
**版本**: V9 (双维度评审)
