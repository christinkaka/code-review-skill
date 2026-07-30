# 日志注入 - 用户输入直接写入日志

> 用户输入直接写入日志，攻击者可注入伪造日志条目，干扰日志分析和审计。

```yaml
id: log-injection-java
languages: [java]
severity: WARNING
cwe: CWE-117
owasp: A09:2021
```

## 问题说明

当日志记录直接使用用户输入时，攻击者可以在输入中嵌入特殊字符（如换行符 `\n`、
回车符 `\r`）来：

- 注入伪造的日志条目，混淆审计追踪
- 模拟系统日志，误导安全分析人员
- 注入恶意脚本（如果日志在 Web 界面展示，可能导致存储型 XSS）
- 填充大量日志造成磁盘耗尽

## 违规示例

### Java
```java
String username = request.getParameter("username");
log.info("User login: " + username);
// 攻击者输入: admin\n[INFO] Admin password changed to hacker123
// 日志输出:
// User login: admin
// [INFO] Admin password changed to hacker123
```

### Python
```python
username = request.args.get('username')
logging.info(f"User login: {username}")
```

## 正确示例

```java
// 1. 移除换行符
String safeUsername = username.replaceAll("[\n\r]", "_");
log.info("User login: {}", safeUsername);

// 2. 使用参数化日志（SLF4J），避免字符串拼接
log.info("User login: {}", sanitize(username));

// 3. 使用 OWASP 日志编码器
log.info("User login: {}", Encode.forHtml(username));
```

```python
# 移除换行符
safe_username = username.replace('\n', '_').replace('\r', '_')
logging.info("User login: %s", safe_username)
```

## 检测模式

### Java
```pattern
log.info($USER_INPUT)
```
```pattern
log.debug($USER_INPUT)
```
```pattern
log.warn($USER_INPUT)
```
```pattern
log.error($USER_INPUT)
```

### Python
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
