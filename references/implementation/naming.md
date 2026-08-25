# 命名规范 - Java 布尔变量前缀（已停用 - 立规前提与主流约定相悖）

> 布尔变量建议使用 is/has/can/should 前缀。
> 注意：此规则已停用。实测依据（2026-08-25，spring-boot 双盲）：
> 1. 旧模式 `boolean $NAME = ...;` 命中所有布尔声明，含合规名
>    （如 `boolean isExcluded` 亦被标记），属全量误报；
> 2. spring-boot 185 个布尔字段中 0 个使用 is/has 前缀——JavaBeans
>    主流约定为字段 `active` + 访问器 `isActive()`，带前缀的字段名
>    反而违背主流风格；
> 3. 435 条声明中仅 19 条为语义空泛名，由替代规则
>    `naming-java-boolean-vague` 覆盖（噪音下降 95%）。

```yaml
id: naming-java-boolean-prefix
languages: [java]
severity: INFO
category: implementation
enabled: false
```

## 检测模式（已停用）

```pattern
boolean $NAME = ...;
```

---

# 命名规范 - Java 布尔变量语义空泛名

> 布尔变量名应表达判断语义（如 isActive、found、enabled、hasNext），
> 禁止使用 flag、tmp、b1 等无语义名称。空泛名迫使读者回溯赋值处
> 才能理解判断含义。

```yaml
id: naming-java-boolean-vague
languages: [java]
severity: INFO
category: implementation
```

## 违规示例

```java
boolean flag = true;
boolean tmp = false;
boolean b1 = list.isEmpty();
```

## 正确示例

```java
boolean isValid = true;
boolean found = false;
boolean isEmpty = list.isEmpty();
```

## 检测模式

```pattern-regex
\bboolean\s+(flag|flg|tmp|temp|ret|val|ok|bln|bool|bb|[bf]\d*)\s*[=;]
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
