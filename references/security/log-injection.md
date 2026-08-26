# 日志注入 - 用户可控数据流入日志（数据流分析）

> 用户可控数据（HTTP 请求参数/头/请求体）流入日志调用。攻击者可注入换行符 + 伪造日志条目，干扰日志分析和审计；若日志聚合到 Web 界面展示，还可能形成存储型 XSS。基于 Semgrep taint 模式做过程内数据流追踪。

```yaml
id: log-injection-taint
languages: [java]
severity: WARNING
cwe: CWE-117
owasp: A09:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流 + Spring 入口方法参数
  （入口点参数对象本身是污点——`request.getUserPrincipal().getName()`、
  `WebUtils.getRequestBody(request)` 等以 request 为实参的不透明调用返回值
  均被污染，Semgrep 对含污点实参的调用按保守传播处理，跨方法场景部分覆盖）
- **污点汇聚**：SLF4J 五级日志调用的任意实参（`info/debug/warn/error/trace`）。
  sink 用方法名元变量 `$LOG.xxx(...)` 而非字面 `log.`：靶场实测两类接收者
  命名（`log`/`logger`）并存，字面 `log.` 漏掉全部 `logger.` 调用
  （java-sec-code 盲测：pattern 版仅 2 命中且无法区分常量实参，
  taint 版 36 命中全为真实用户数据流）
- **净化器**：换行剥离（`replaceAll("[\n\r]", ...)` 两种源码拼写）与
  OWASP Encoder（`Encode.forHtml`）。精确字面匹配——`replaceAll("a","b")`
  类无关替换不视为净化（实测仍报出，正确）

SLF4J 参数化日志 `log.info("{}", username)` 仍报：未净化实参原样落入
日志输出，占位符机制不做 CRLF 转义（java-sec-code Log4j.java 的
Log4Shell PoC 端点同型——`logger.error(token)` 直收 `@RequestMapping`
参数）；
`logger.error(e.toString())` 不报（异常消息无入口点污点流入，
java-sec-code XXE/SSRF 等 12 处实测零误报）；
`logger.info("Working directory: " + System.getProperty(...))` 不报
（环境属性非用户可控）。

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
$LOG.info(...)
$LOG.debug(...)
$LOG.warn(...)
$LOG.error(...)
$LOG.trace(...)
```

```pattern-sanitizers
$X.replaceAll("[\n\r]", ...)
$X.replaceAll("[\\n\\r]", ...)
org.owasp.encoder.Encode.forHtml(...)
```

## 违规示例

```java
String username = request.getParameter("username");
log.info("User login: " + username);
log.info("{}", username);  // 参数化也不净化 CRLF
// 攻击者输入: admin\n[INFO] Admin password changed to hacker123
// 日志输出:
// User login: admin
// [INFO] Admin password changed to hacker123
```

## 正确示例

```java
// 1. 移除换行符（两种拼写均被识别为净化器）
String safeUsername = username.replaceAll("[\n\r]", "_");
log.info("User login: {}", safeUsername);

// 2. 使用 OWASP 日志编码器
log.info("User login: {}", Encode.forHtml(username));
```

---

# 日志注入 - Python 用户输入写入日志

> Python logging 调用直接使用用户输入，存在日志伪造风险。

```yaml
id: log-injection-python
languages: [python]
severity: WARNING
cwe: CWE-117
owasp: A09:2021
```

## 检测模式

```pattern
logging.info($USER_INPUT)
```
```pattern
logging.debug($USER_INPUT)
```
```pattern
logging.warning($USER_INPUT)
```
```pattern
logging.error($USER_INPUT)
```

## 正确示例

```python
# 移除换行符
safe_username = username.replace('\n', '_').replace('\r', '_')
logging.info("User login: %s", safe_username)
```
