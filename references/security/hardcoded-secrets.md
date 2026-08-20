# 硬编码密钥 - 敏感信息硬编码在源代码中

> 密码、密钥、令牌等敏感信息硬编码在源代码中，攻击者获取源码后可直接获取凭据。

```yaml
id: crypto-hardcoded-key
languages: [java, python, javascript, typescript]
severity: HIGH
cwe: CWE-798
owasp: A07:2021
```

## 问题说明

硬编码的敏感信息（密码、API 密钥、令牌）会随源代码一起分发，攻击者可通过以下方式获取：

- 代码仓库泄露或公开
- 反编译编译后的代码（如 Java .class 文件）
- 前端 JavaScript 代码直接可见

即使后续修改了密码，历史提交中仍可找到旧密钥。

## 违规示例

### Java
```java
String password = "admin123";
String apiKey = "sk-abc123def456";
String token = "eyJhbGciOiJIUzI1NiJ9...";
```

### Python
```python
password = "admin123"
api_key = 'sk-abc123def456'
secret = "my-secret-value"
```

### JavaScript / TypeScript
```javascript
const password = "admin123";
const apiKey = "sk-abc123def456";
```

## 正确示例

```java
// 使用环境变量
String password = System.getenv("DB_PASSWORD");

// 使用密钥管理服务
String apiKey = vaultClient.getSecret("api-key");
```

```python
# 使用环境变量
import os
password = os.environ.get("DB_PASSWORD")

# 使用配置管理
from django.conf import settings
api_key = settings.API_KEY
```

## 检测模式

```pattern-regex
(?i)(password|secret|api_?key|token|api_?secret)\s*=\s*["'][^"']+["']
```

---

# 硬编码密钥 - Java 字符串变量中的敏感信息

> Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。

```yaml
id: crypto-hardcoded-key-java
languages: [java]
severity: HIGH
cwe: CWE-798
owasp: A07:2021
```

## 检测模式

```pattern
String $VAR = "...";
```

使用 `metavariable-regex` 过滤变量名包含 `password`、`secret`、`api_key`、`token` 等关键词。
