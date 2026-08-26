# SSRF - 用户可控 URL 流入出站请求（数据流分析）

> 用户可控数据（HTTP 请求参数/头）经赋值、拼接、URL/URI 构造传播后流入真实发起出站请求的 API。基于 Semgrep taint 模式做过程内数据流追踪，替代纯模式匹配。

```yaml
id: ssrf-taint
languages: [java]
severity: ERROR
cwe: CWE-918
owasp: A10:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流
- **污点汇聚**：真实发起出站请求的 API（openConnection、openStream、HttpClient send）。
  沿用 2026-08-25 盲评修正结论：`new URL(...)` / `URI.create(...)` 为纯解析构造，
  不产生网络流量，不作为汇聚点，常量 URL 场景不报。
- **净化器**：约定式校验函数（isAllowedUrl/isSafeUrl/validateUrl）与
  host 白名单校验（`Set.contains(url.getHost())`）。

`new URL(userInput)` 之后的 `url.openConnection()` 命中（污点随对象传播）；
`new URL("https://api.example.com")` 常量 URL 无污点源，不报；
经 `isAllowedUrl(...)` 或 host 白名单校验后的请求不报。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
spring-entrypoint-param
```

```pattern-sinks
$URL.openConnection(...)
$URL.openStream(...)
$CLIENT.send(...)
$CLIENT.sendAsync(...)
```

```pattern-sanitizers
isAllowedUrl(...)
isSafeUrl(...)
validateUrl(...)
$SET.contains($URL.getHost())
```

---

# SSRF - Python requests 请求用户可控 URL

> requests 请求用户可控 URL，存在 SSRF 风险。

```yaml
id: ssrf-python-requests
languages: [python]
severity: ERROR
cwe: CWE-918
```

## 检测模式

```pattern
requests.get($USER_INPUT, ...)
```

```pattern-not
if is_safe_url($USER_INPUT): ...
```

---

# SSRF - Python urllib 请求用户可控 URL

> urllib 请求用户可控 URL，存在 SSRF 风险。

```yaml
id: ssrf-python-urllib
languages: [python]
severity: ERROR
cwe: CWE-918
```

## 检测模式

```pattern
urllib.request.urlopen($USER_INPUT)
```

---

# SSRF - JavaScript fetch 请求用户可控 URL

> fetch 请求用户可控 URL（服务端），存在 SSRF 风险。

```yaml
id: ssrf-js-fetch
languages: [javascript, typescript]
severity: WARNING
cwe: CWE-918
```

## 检测模式

```pattern
fetch($URL, ...)
```

```pattern-not
$URL.includes("localhost")
```

```pattern-not
$URL.includes("127.0.0.1")
```

```pattern-not
allowedDomains.includes(...)
```

```pattern-not
if (!$URL.startsWith("https://")) { ... }
```

```pattern-not
ALLOWED_HOSTS.has($X)
```

```pattern-not
allowedHosts.has($X)
```

---

# SSRF - fetch 请求使用不完整过滤

> fetch 请求仅做简单字符串检查（如 includes("localhost")），可被 127.0.0.1、0.0.0.0 等绕过，存在 SSRF 风险。

```yaml
id: ssrf-js-fetch-weak-filter
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-918
```

## 违规示例

```javascript
if (url.includes("localhost")) {
    throw new Error("Blocked");
}
return await fetch(url);  // 可被 127.0.0.1 绕过
```

## 检测模式

```pattern
if ($URL.includes("localhost")) { ... }
...
fetch($URL, ...)
```

---

# SSRF - JavaScript axios 请求用户可控 URL

> axios 请求用户可控 URL（服务端），存在 SSRF 风险。

```yaml
id: ssrf-js-axios
languages: [javascript, typescript]
severity: WARNING
cwe: CWE-918
```

## 检测模式

```pattern
axios.get($USER_INPUT, ...)
```

---

# SSRF - Node.js http.get 请求用户可控 URL

> http.get() 请求用户可控 URL，存在 SSRF 风险。

```yaml
id: ssrf-js-http-get
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-918
```

## 违规示例

```javascript
const http = require('http');
const url = req.body.url;
http.get(url, (res) => { ... });  // 危险：用户可控 URL
```

## 正确示例

```javascript
const http = require('http');
const allowedDomains = ['api.example.com'];
const urlObj = new URL(url);
if (!allowedDomains.includes(urlObj.hostname)) {
    throw new Error('Domain not allowed');
}
http.get(url, (res) => { ... });
```

## 检测模式

```pattern
http.get($USER_INPUT, ...)
```
