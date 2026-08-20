# 代码评审报告 - opencode 仓库

**扫描时间**: 2026-07-28T13:29:25.722588
**扫描仓库**: /Users/chris/dev/git/opencode
**扫描策略**: ai-enhanced
**规约 Profile**: default
**扫描引擎**: 正则模式匹配（Semgrep 不可用）
**扫描耗时**: 2.13s

## 扫描摘要

| 指标 | 数值 |
|------|------|
| 扫描文件数 | 1894 |
| 总问题数 | 124 |
| 误报过滤 | 47 |
| CRITICAL | 8 |
| HIGH | 0 |
| MEDIUM | 116 |
| LOW | 0 |

### 按类别分布

| 类别 | 数量 |
|------|------|
| security | 124 |

### 按规则分布

| 规则 ID | 数量 |
|---------|------|
| `ssrf-js-fetch` | 115 |
| `xss-js-innerhtml` | 8 |
| `xss-js-function-constructor` | 1 |

## 问题详情

### ssrf-js-fetch (115 处)

**AI 分析**: fetch/axios 请求如果 URL 来源可控（用户输入、外部配置），攻击者可构造请求访问内网资源（如 http://169.254.169.254/ 获取云元数据），导致 SSRF 漏洞。客户端代码风险较低，服务端代码风险较高。

**修复建议**:
```
// URL 白名单校验
const ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com'];
function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ALLOWED_HOSTS.includes(parsed.hostname);
  } catch { return false; }
}
if (isSafeUrl(targetUrl)) { fetch(targetUrl); }
```

| 文件 | 行号 | 严重度 | 代码片段 |
|------|------|--------|----------|
| `sdks/vscode/src/extension.ts` | 78 | WARNING | `await fetch(`http://localhost:${port}/app`)` |
| `sdks/vscode/src/extension.ts` | 94 | WARNING | `await fetch(`http://localhost:${port}/tui/append-prompt`, {` |
| `.opencode/tool/github-triage.ts` | 23 | WARNING | `const response = await fetch(`https://api.github.com${endpoint}`, {` |
| `.opencode/tool/github-pr-search.ts` | 4 | WARNING | `const response = await fetch(`https://api.github.com${endpoint}`, {` |
| `script/stats.ts` | 11 | WARNING | `const response = await fetch("https://us.i.posthog.com/i/v0/e/", {` |
| `script/stats.ts` | 57 | WARNING | `const response = await fetch(`https://api.npmjs.org/downloads/range/2020-01-01:$...` |
| `script/stats.ts` | 78 | WARNING | `const response = await fetch(url)` |
| `script/github/close-prs.ts` | 275 | WARNING | `const response = await fetch(` |
| `script/github/close-prs.ts` | 296 | WARNING | `const response = await fetch(path.startsWith("https://") ? path : `https://api.g...` |
| `script/github/close-issues.ts` | 30 | WARNING | `const comment = await fetch(`${base}/comments`, {` |
| `script/github/close-issues.ts` | 37 | WARNING | `const patch = await fetch(base, {` |
| `script/github/close-issues.ts` | 52 | WARNING | `const res = await fetch(` |
| `github/index.ts` | 377 | WARNING | `response = await fetch("https://api.opencode.ai/exchange_github_app_token_with_p...` |
| `github/index.ts` | 386 | WARNING | `response = await fetch("https://api.opencode.ai/exchange_github_app_token", {` |
| `github/index.ts` | 465 | WARNING | `const res = await fetch(url, {` |
| `github/index.ts` | 509 | WARNING | `const response = await fetch(`${server.url}/event`)` |
| `github/index.ts` | 1044 | WARNING | `await fetch("https://api.github.com/installation/token", {` |
| `packages/llm/script/recording-cost-report.ts` | 219 | WARNING | `const models = (await (await fetch(MODELS_DEV_URL)).json()) as JsonRecord` |
| `packages/core/src/plugin/provider/google-vertex.ts` | 52 | WARNING | `: fetch(input, { ...init, headers })` |
| `packages/enterprise/src/core/storage.ts` | 16 | WARNING | `const response = await client.fetch(`${base}/${path}`)` |
| ... 还有 95 处 | | | |

### xss-js-function-constructor (1 处)

**AI 分析**: 规则 xss-js-function-constructor 检测到潜在安全问题，建议人工确认。

**修复建议**:
```
避免使用 new Function()，改用静态方法或 JSON.parse()
```

| 文件 | 行号 | 严重度 | 代码片段 |
|------|------|--------|----------|
| `packages/opencode/src/cli/cmd/debug/agent.ts` | 109 | WARNING | `return new Function(`return (${trimmed})`)()` |

### xss-js-innerhtml (8 处)

**AI 分析**: innerHTML 直接赋值可将任意 HTML 注入到 DOM 中。如果赋值的来源包含用户输入或外部数据，攻击者可注入 <script> 标签或事件处理器，在其他用户的浏览器中执行恶意代码（DOM 型 XSS）。

**修复建议**:
```
// 方案 1: 使用 textContent 替代
element.textContent = userInput;

// 方案 2: 使用 DOMPurify 消毒
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

| 文件 | 行号 | 严重度 | 代码片段 |
|------|------|--------|----------|
| `packages/ui/src/pierre/file-find.ts` | 137 | ERROR | `el.innerHTML = ""` |
| `packages/ui/src/components/icon.tsx` | 133 | ERROR | `svg.innerHTML = Object.entries(icons)` |
| `packages/ui/src/components/markdown.tsx` | 91 | ERROR | `svg.innerHTML = path` |
| `packages/ui/src/components/markdown.tsx` | 299 | ERROR | `container.innerHTML = ""` |
| `packages/ui/src/components/markdown.tsx` | 308 | ERROR | `temp.innerHTML = content` |
| `packages/ui/src/components/file.tsx` | 495 | ERROR | `opts.viewer.container.innerHTML = ""` |
| `packages/app/src/components/file-tree.tsx` | 98 | ERROR | `image.innerHTML = (icon as SVGElement).outerHTML + (text as HTMLSpanElement).out...` |
| `packages/app/src/components/prompt-input.tsx` | 485 | ERROR | `editorRef.innerHTML = ""` |

## 效果验证

### 检出能力验证

| 检测项 | 检出数量 | 状态 |
|--------|----------|------|
| innerHTML 使用 | 8 | PASS |
| eval 使用 | 0 | FAIL |
| SSRF (fetch/axios) | 115 | PASS |
| dangerouslySetInnerHTML | 0 | FAIL |

### AI 增强验证

- 误报过滤数: 47
- 误报率: 27.5%
- 所有真实问题均包含 AI 分析说明和修复建议
- 修复建议包含具体代码示例
