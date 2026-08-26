# 反序列化漏洞 - 用户可控数据流入反序列化/JNDI（数据流分析）

> 用户可控数据（HTTP 请求参数/头/流）经赋值、包装传播后流入 Java 反序列化或 JNDI 查找 API。基于 Semgrep taint 模式做过程内数据流追踪，替代纯模式匹配。

```yaml
id: deser-taint
languages: [java]
severity: CRITICAL
cwe: CWE-502
owasp: A08:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流
- **污点汇聚**：反序列化入口（`new ObjectInputStream(...)`）与 JNDI 查找
  （`$CTX.lookup(...)`，RCE 同类风险，旧模式规则未覆盖）
- **净化器**：无。反序列化的白名单防护（resolveClass 覆写、
  ObjectInputFilter）发生在流解析阶段而非数据流层面，taint 无法表达；
  此类场景由告警触发人工评审确认，不作静默豁免。

`request.getInputStream()` 直接流入 `new ObjectInputStream(...)` 命中；
请求参数经 `getBytes()`/`ByteArrayInputStream` 包装传播后命中（污点随包装传播）；
请求参数流入 `ctx.lookup(...)` 命中（JNDI 注入，新增覆盖）；
`new ObjectInputStream(new FileInputStream("config/data.ser"))` 常量文件无污点源，
不报；可信流上的 `readObject()` 不再作为独立告警（旧 deser-java-read-object
对所有 readObject 无差别告警，为已知误报源）。

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
new ObjectInputStream(...)
$CTX.lookup(...)
```

---

# 反序列化漏洞 - SnakeYAML 不安全构造器 load（数据流分析）

> 用户可控数据流入 SnakeYAML `Yaml.load(...)`。默认构造器的 Yaml 允许任意类型实例化（`!!javax.script.ScriptEngineManager` 即远程加载恶意 jar，java-sec-code Rce.java vuln/yarm 同型 PoC），污点直达 load 即反序列化 RCE。基于 Semgrep taint 模式做过程内数据流追踪。

```yaml
id: deser-yaml-taint
languages: [java]
severity: CRITICAL
cwe: CWE-502
owasp: A08:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流 + Spring 入口方法参数
- **污点汇聚**：`(org.yaml.snakeyaml.Yaml $Y).load(...)`——类型化元变量
  （Yaml 需显式 import，全限定名有效，同 sqli-taint 的 java.sql.Statement
  先例；避免 `$Y.load(...)` 撞上其他 load API）
- **加固豁免**：`new Yaml(new SafeConstructor())` 后的 load 不报——
  SafeConstructor 限制只实例化基础类型，任意类型构造被禁止。以
  pattern-sinks-not-inside 表达（QLExpress 全局安全策略同型）：
  豁免块从安全构造语句跨到 load 调用，包住 sink 命中点

**为何独立规则而非并入 deser-taint**：sink 排除块复合进规则内全部
sink——SafeConstructor 豁免不应作用于 ObjectInputStream/JNDI sink，
独立规则语义边界干净。

`new Yaml(); y.load(content)` 命中（默认构造器，任意类型可实例化）；
`new Yaml(new SafeConstructor()); y.load(content)` 不报（基础类型白名单）；
`y.load("a: 1")` 常量不报（无污点源）。

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
(org.yaml.snakeyaml.Yaml $Y).load(...)
```

```pattern-sinks-not-inside
new Yaml(new SafeConstructor(...));
...
$Y.load(...);
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
>
> 2026-08-26 修正一（解析失效）：本规则为多语言规则，但 Java 语法
> pattern 无语言标签落到 Python 变体上导致整条 `ssrf-deep-detection__python`
> 解析失败（semgrep rc=2，Python 侧 SSRF 检测静默失效）。以语言子标题
> 为 pattern 打语言标签：Java pattern 只进 Java 变体，requests 只进
> Python 变体；fetch/axios 保持无标签（各语言均可解析）。
>
> 2026-08-26 修正二（常量误报）：`$USER_INPUT` 元变量匹配任意表达式，
> 常量 URL 直连（`requests.get("https://api.example.com/health")`）
> 同样命中——实测复现。各 pattern 配套 pattern-not 排除字符串字面量
> 实参（semgrep `"..."` 匹配任意字符串字面量）；f-string/变量拼接
> 不受影响，仍正常检出。

### Java

```pattern
new URL($USER_INPUT).openConnection()
```

```pattern-not
new URL("...").openConnection()
```

### Python

```pattern
requests.get($USER_INPUT)
```

```pattern-not
requests.get("...")
```

```pattern
requests.post($USER_INPUT)
```

```pattern-not
requests.post("...")
```

### 通用

```pattern
fetch($USER_INPUT)
```

```pattern-not
fetch("...")
```

```pattern
axios.get($USER_INPUT)
```

```pattern-not
axios.get("...")
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
> secure-processing 属 OWASP 推荐加固写法（实测 2/2 误报），以排除
> 模式豁免。
>
> 2026-08-26 修正：原 pattern-not 块有两处缺陷——(1) 缺分号的语句序列
> 无法解析，整条 `xxe-deep-detection__java` 规则 rc=2 静默失效（XXE
> 检测从未生效）；(2) 即使可解析，pattern-not 要求与正向 pattern 范围
> 一致，多语句排除块永远不命中（semgrep 语义），应使用 pattern-not-inside。
> 另以语言子标题为 pattern 打标签，Java 语法排除块不再落入 Python 变体。
>
> 2026-08-26 补充（java-sec-code 盲测实证）：reader 级加固两种写法原豁免
> 不覆盖——(1) `createXMLReader()` 后对 reader 本身 setFeature（非工厂
> newInstance）；(2) `spf.newInstance() → newSAXParser() → getXMLReader()`
> 后 setFeature（豁免块需从工厂创建跨到 setFeature 才能包住命中位置）。
> 补两条 pattern-not-inside 后：XXE.java 7 检出 → 5（sec 方法 2 误报
> 清零，vuln 方法 5 真阳性全保留，真实文件实测）。

### Java

```pattern
DocumentBuilderFactory.newInstance()
```

```pattern
SAXParserFactory.newInstance()
```

```pattern
XMLReaderFactory.createXMLReader()
```

```pattern-not-inside
$F = $FACTORY.newInstance();
...
$F.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
```

```pattern-not-inside
$F = $FACTORY.newInstance();
...
$F.setFeature(javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING, true);
```

```pattern-not-inside
$F = $FACTORY.newInstance();
...
$F.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
```

```pattern-not-inside
$R = XMLReaderFactory.createXMLReader();
...
$R.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
```

```pattern-not-inside
$F = $FACTORY.newInstance();
...
$R = $P.getXMLReader();
...
$R.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
```

### Python

```pattern
etree.parse($USER_INPUT)
```
