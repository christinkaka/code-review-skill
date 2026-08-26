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
(?i)(password|secret|api_?key|token|api_?secret)\s*=\s*["'][^"']{8,}["']
```

最小长度 8 字符：排除 `BLANK_TOKEN = 'BLANK'` 等短值占位符（2026-08-26 降噪）。

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

```pattern-regex
(?i)String\s+\w*(password|passwd|secret|api_?key|apikey|token|credential)\w*\s*=\s*"[^"]+"
```

两层降噪设计（2026-08-24，P0 数学理论降噪）：
- **结构层（本 pattern）**：变量名包含敏感关键词，正则只做候选预筛，不设经验长度阈值
- **数学层（noise_theory.py 熵门控）**：对候选字面量做确定性判决
  - Shannon 熵 + Miller-Madow 有限样本修正：Ĥ_MM = Ĥ + (K-1)/(2n·ln2)
  - 字符集分层检验：hex/base62/base64/符号混合字符集 H_MM ≥ 3.5 bits/char（均匀抽取的估计余量）
  - 总熵门限：n·H_MM ≥ 32 bits（低于 2^32 暴力破解边界的弱凭据不报）
  - 自然字符集（含空白文案）与 `${}` 模板占位符直接拒绝
  - 理论依据与已知局限详见 `scripts/noise_theory.py` 模块文档
