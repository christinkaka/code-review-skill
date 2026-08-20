# 命名规范 - Java 布尔变量前缀

> 布尔变量建议使用 is/has/can/should 前缀，提高可读性。

```yaml
id: naming-java-boolean-prefix
languages: [java]
severity: INFO
category: implementation
```

## 正确示例

```java
boolean isActive = true;
boolean hasPermission = false;
boolean canExecute = true;
```

## 检测模式

```pattern
boolean $NAME = ...;
```

---

# 命名规范 - Python 类名

> Python 类名应使用 PascalCase。

```yaml
id: naming-python-class-case
languages: [python]
severity: INFO
category: implementation
```

## 违规示例

```python
class user_service:
    pass
```

## 正确示例

```python
class UserService:
    pass
```

## 检测模式

```pattern-regex
class\s+[a-z][a-zA-Z0-9_]*\s*[\(:]
```

---

# 命名规范 - Python 函数名（已禁用 - 误报率过高）

> Python 函数名应使用 snake_case。
> 注意：此规则已禁用，因为模式 `def $NAME(...)` 匹配所有函数定义，误报率过高。

```yaml
id: naming-python-function-case
languages: [python]
severity: INFO
category: implementation
enabled: false
```

## 检测模式

```pattern
def $NAME(...):
    ...
```

---

# 命名规范 - Java 常量未使用大写

> Java 常量（static final 字段）应使用 UPPER_SNAKE_CASE 命名。

```yaml
id: naming-java-constant-case
languages: [java]
severity: INFO
category: implementation
```

## 违规示例

```java
static final String maxRetryCount = "3";
static final String apiBaseUrl = "https://api.example.com";
```

## 正确示例

```java
static final String MAX_RETRY_COUNT = "3";
static final String API_BASE_URL = "https://api.example.com";
```

## 检测模式

```pattern-regex
static\s+final\s+(String|int|long|boolean|double|float|Integer|Long|Boolean|Double|Float)\s+[a-z][a-zA-Z0-9_]*\s*=
```
