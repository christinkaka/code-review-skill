# SSRF 测试案例

## 违规代码 - Java 请求参数流入出站请求

```java
public String fetchUrl(HttpServletRequest request) throws IOException {
    String userUrl = request.getParameter("url");
    URL url = new URL(userUrl);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    // read response...
}
```

**预期命中**: `ssrf-taint`
**文件类型**: `.java`

---

## 违规代码 - Java HttpClient 请求用户可控 URL

```java
public String fetch(HttpServletRequest request) throws Exception {
    String userUrl = request.getParameter("url");
    HttpRequest req = HttpRequest.newBuilder()
        .uri(URI.create(userUrl))
        .build();
    return client.send(req, HttpResponse.BodyHandlers.ofString()).body();
}
```

**预期命中**: `ssrf-taint`
**文件类型**: `.java`

---

## 正确代码 - Java 常量 URL 出站请求

```java
public String fetchConst() throws IOException {
    URL url = new URL("https://api.example.com/v1/health");
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    // read response...
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 违规代码 - Python requests.get

```python
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.text
```

**预期命中**: `ssrf-python-requests`
**文件类型**: `.py`

---

## 违规代码 - Node.js fetch

```javascript
async function fetchData(url) {
    const response = await fetch(url);
    return response.text();
}
```

**预期命中**: `ssrf-js-fetch`
**文件类型**: `.js`

---

## 正确代码 - Java URL 白名单校验

```java
private static final Set<String> ALLOWED_HOSTS = Set.of("api.example.com");

public String fetchUrl(HttpServletRequest request) throws IOException {
    String userUrl = request.getParameter("url");
    URL url = new URL(userUrl);
    if (!ALLOWED_HOSTS.contains(url.getHost())) {
        throw new SecurityException("URL not allowed");
    }
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    // read response...
}
```

**预期命中**: 无
**文件类型**: `.java`
