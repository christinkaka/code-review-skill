# 反序列化漏洞 - Java 不安全反序列化

> 使用 ObjectInputStream 反序列化不可信数据，攻击者可构造恶意序列化对象执行远程代码（RCE）。

```yaml
id: deser-java-object-input-stream
languages: [java]
severity: CRITICAL
cwe: CWE-502
owasp: A08:2021
```

## 风险说明

Java 反序列化漏洞可导致远程代码执行（RCE），攻击者可：
- 执行任意系统命令
- 获取服务器控制权
- 横向移动攻击内网

## 违规示例

```java
// 直接反序列化用户输入
ObjectInputStream ois = new ObjectInputStream(userInput);
Object obj = ois.readObject();  // 攻击者可构造恶意序列化对象
```

```java
// RMI/JNDI 反序列化
InitialContext ctx = new InitialContext();
Object obj = ctx.lookup(userInput);  // JNDI 注入
```

## 正确示例

```java
// 使用白名单校验反序列化类
ObjectInputStream ois = new ObjectInputStream(userInput) {
    @Override
    protected Class<?> resolveClass(ObjectStreamClass desc) throws IOException, ClassNotFoundException {
        String className = desc.getName();
        // 只允许安全的类
        if (!className.startsWith("com.myapp.safe.")) {
            throw new InvalidClassException("Unauthorized deserialization attempt");
        }
        return super.resolveClass(desc);
    }
};
```

## 检测模式

```pattern
new ObjectInputStream($USER_INPUT)
```

```pattern
$STREAM.readObject()
```

---

# 反序列化漏洞 - Python pickle 不安全反序列化

> 使用 pickle 反序列化不可信数据，攻击者可构造恶意 pickle 数据执行任意代码。

```yaml
id: deser-python-pickle
languages: [python]
severity: CRITICAL
cwe: CWE-502
owasp: A08:2021
```

## 风险说明

Python pickle 反序列化漏洞可导致任意代码执行，攻击者可：
- 执行任意 Python 代码
- 获取服务器控制权
- 读取/修改系统文件

## 违规示例

```python
import pickle

# 直接反序列化用户输入
data = pickle.loads(user_input)  # 攻击者可构造恶意 pickle 数据
```

```python
# 反序列化文件
with open(user_file, 'rb') as f:
    data = pickle.load(f)  # 文件内容不可信
```

## 正确示例

```python
import json

# 使用 JSON 替代 pickle（更安全）
data = json.loads(user_input)
```

```python
# 如果必须使用 pickle，使用签名验证
import hmac
import hashlib

def verify_pickle(data, signature, secret):
    expected = hmac.new(secret, data, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid signature")
    return pickle.loads(data)
```

## 检测模式

```pattern
pickle.loads($USER_INPUT)
```

```pattern
pickle.load($FILE)
```

---

# 反序列化漏洞 - Node.js 不安全反序列化

> 使用 node-serialize 或 serialize-to-js 反序列化不可信数据，可导致远程代码执行。

```yaml
id: deser-node-serialize
languages: [javascript, typescript]
severity: CRITICAL
cwe: CWE-502
owasp: A08:2021
```

## 违规示例

```javascript
const serialize = require('node-serialize');

// 直接反序列化用户输入
const obj = serialize.unserialize(userInput);  // 攻击者可构造恶意数据
```

## 正确示例

```javascript
// 使用 JSON.parse 替代
const obj = JSON.parse(userInput);
```

## 检测模式

```pattern
serialize.unserialize($USER_INPUT)
```

---

# SSRF - 服务端请求伪造（深度检测）

> 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。

```yaml
id: ssrf-deep-detection
languages: [java, python, javascript, typescript]
severity: CRITICAL
cwe: CWE-918
owasp: A10:2021
```

## 风险说明

SSRF 可导致：
- 访问内网资源（127.0.0.1、192.168.x.x）
- 读取云元数据（169.254.169.254）
- 扫描内网端口
- 攻击内网服务

## 违规示例

### Java
```java
// 用户可控 URL
String url = request.getParameter("url");
URL urlObj = new URL(url);
HttpURLConnection conn = (HttpURLConnection) urlObj.openConnection();
```

### Python
```python
# 用户可控 URL
url = request.args.get('url')
response = requests.get(url)  # 攻击者可传入 http://169.254.169.254/
```

## 正确示例

```java
// URL 白名单校验
String url = request.getParameter("url");
URL urlObj = new URL(url);

// 1. 协议限制（只允许 http/https）
if (!urlObj.getProtocol().matches("https?")) {
    throw new SecurityException("Invalid protocol");
}

// 2. 内网 IP 限制
InetAddress addr = InetAddress.getByName(urlObj.getHost());
if (addr.isLoopbackAddress() || addr.isSiteLocalAddress()) {
    throw new SecurityException("Internal network access denied");
}

// 3. 云元数据 IP 限制
if (urlObj.getHost().equals("169.254.169.254")) {
    throw new SecurityException("Cloud metadata access denied");
}
```

## 检测模式

> 2026-08-25 盲评修正：Java 侧 `new URL($USER_INPUT)` 裸构造不产生网络
> 流量（如注册 Tomcat 静态资源），误报实测 2/2。SSRF 的判别信号是
> **连接建立**（openConnection / send），而非 URL 对象构造。

```pattern
new URL($USER_INPUT).openConnection()
```

```pattern
requests.get($USER_INPUT)
```

```pattern
requests.post($USER_INPUT)
```

```pattern
fetch($USER_INPUT)
```

```pattern
axios.get($USER_INPUT)
```

---

# XXE - XML 外部实体注入（深度检测）

> XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。

```yaml
id: xxe-deep-detection
languages: [java, python]
severity: CRITICAL
cwe: CWE-611
owasp: A05:2021
```

## 风险说明

XXE 可导致：
- 读取服务器文件（/etc/passwd）
- 发起 SSRF 攻击
- 拒绝服务（Billion Laughs）

## 违规示例

### Java
```java
// DocumentBuilderFactory 未禁用外部实体
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(userInput);
```

### Python
```python
# lxml 未禁用外部实体
from lxml import etree
tree = etree.parse(user_input)
```

## 正确示例

```java
// 禁用外部实体
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

## 检测模式

> 2026-08-25 盲评修正：工厂创建后紧邻设置 disallow-doctype-decl /
> secure-processing 属 OWASP 推荐加固写法（实测 2/2 误报），以
> pattern-not 豁免。

```pattern
DocumentBuilderFactory.newInstance()
```

```pattern
SAXParserFactory.newInstance()
```

```pattern
XMLReaderFactory.createXMLReader()
```

```pattern
etree.parse($USER_INPUT)
```

```pattern-not
$F = $FACTORY.newInstance()
...
$F.setFeature("...disallow-doctype-decl...", true)
```

```pattern-not
$F = $FACTORY.newInstance()
...
$F.setFeature("...secure-processing...", true)
```
