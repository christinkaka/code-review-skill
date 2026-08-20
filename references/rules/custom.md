# 自定义规则 - 硬编码密码

> 疑似硬编码密码，请使用配置中心或环境变量管理敏感配置。

```yaml
id: custom-hardcoded-password
languages: [java, python, javascript, typescript]
severity: HIGH
category: custom
```

## 问题说明

密码、密钥等敏感信息不应硬编码在源码中，应使用配置中心（如 Nacos、Apollo）或环境变量管理。

## 违规示例

```java
String password = "mySecret123";  // 危险：硬编码密码
String api_key = "sk-abc123";     // 危险：硬编码 API 密钥
```

```python
password = "mySecret123"  # 危险：硬编码密码
secret = "my-secret-key"  # 危险：硬编码密钥
```

## 正确示例

```java
// 使用环境变量或配置中心
String password = System.getenv("DB_PASSWORD");
String apiKey = configService.getProperty("api.key");
```

```python
import os
password = os.getenv("DB_PASSWORD")
api_key = os.getenv("API_KEY")
```

## 检测模式

```pattern-regex
(password|secret|api_key)\s*=\s*["'][^"']+["']
```

---

# 自定义规则 - 日志中打印敏感信息

> 日志中疑似打印敏感信息（密码/Token），请进行脱敏处理。

```yaml
id: custom-log-sensitive-data
languages: [java]
severity: WARNING
category: custom
```

## 违规示例

```java
log.info("User login: password=" + password);
log.debug("API token: " + token);
```

## 正确示例

```java
log.info("User login: password=***");
log.debug("API token: {}***", token.substring(0, 4));
```

## 检测模式

```pattern
log.info("..." + $PASSWORD + "...");
```

```pattern
log.debug("..." + $TOKEN + "...");
```

---

# 自定义规则模板（使用说明）

> 在此文件中添加团队特有的业务规则。
> 复制以下模板，修改 id、pattern 和 message 即可添加新规则。
> 注意：此模板不用于实际检测，仅作为添加新规则的参考。
>
> 模板格式：
> ```
> # 规则标题
> > 一句话说明
> ```yaml
> id: custom-your-rule-id
> languages: [java]
> severity: WARNING
> ```
> ## 检测模式
> ```pattern
> your_pattern_here
> ```
> ```
