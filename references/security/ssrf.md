# SSRF - Java URL 连接使用用户输入

> URL 连接使用用户输入未做白名单校验，存在 SSRF 风险。

```yaml
id: ssrf-java-url-connection
languages: [java]
severity: ERROR
cwe: CWE-918
owasp: A10:2021
```

## 问题说明

攻击者可以通过构造恶意 URL 让服务器访问内网资源（如 `http://169.254.169.254/` 获取云元数据）。

## 检测模式

```pattern
new URL($USER_INPUT).openConnection()
```

```pattern
URL $URL = new URL($USER_INPUT);
...
$URL.openConnection();
```

```pattern-not
if (isAllowedUrl($USER_INPUT)) { ... }
```

```pattern-not
if (!$SET.contains($URL.getHost())) { ... }
```

```pattern-not
URL $URL = new URL($USER_INPUT);
...
if (!$SET.contains($URL.getHost())) { ... }
...
$URL.openConnection();
```

---

# SSRF - Java HttpClient 请求用户可控 URL

> HttpClient 请求用户可控 URL，存在 SSRF 风险。

```yaml
id: ssrf-java-http-client
languages: [java]
severity: ERROR
cwe: CWE-918
```

## 检测模式

```pattern
URI.create($USER_INPUT)
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
