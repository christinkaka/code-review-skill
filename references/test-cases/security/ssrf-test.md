# SSRF 测试案例

## 违规代码 - Java URL 连接

```java
public String fetchUrl(String userUrl) throws IOException {
    URL url = new URL(userUrl);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    // read response...
}
```

**预期命中**: `ssrf-java-url-connection`
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

public String fetchUrl(String userUrl) throws IOException {
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
