# 并发安全 - SimpleDateFormat 作为 static 共享变量

> SimpleDateFormat 非线程安全，不应作为 static 共享变量。

```yaml
id: conc-java-unsafe-simpledateformat
languages: [java]
severity: ERROR
category: implementation
```

## 违规示例

```java
static SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
```

## 正确示例

```java
static final DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd");
```

## 检测模式

```pattern
static SimpleDateFormat $FMT = ...;
```

---

# 并发安全 - HashMap 作为 static 共享变量

> HashMap 作为 static 共享变量非线程安全。

```yaml
id: conc-java-unsafe-hashmap
languages: [java]
severity: ERROR
category: implementation
```

## 正确示例

```java
static Map<String, Object> cache = new ConcurrentHashMap<>();
```

## 检测模式

```pattern
static Map<$K, $V> $MAP = new HashMap<>();
```

```pattern-not
static Map<$K, $V> $MAP = new ConcurrentHashMap<>();
```

---

# 并发安全 - 双重检查锁定缺少 volatile

> 双重检查锁定模式需要 volatile 修饰字段，否则可能因指令重排导致问题。

```yaml
id: conc-java-double-checked-locking
languages: [java]
severity: ERROR
category: implementation
```

## 正确示例

```java
private volatile Singleton instance;
```

## 检测模式

```pattern
if ($FIELD == null) {
  synchronized ($LOCK) {
    if ($FIELD == null) {
      $FIELD = new $TYPE(...);
    }
  }
}
```

---

# 并发安全 - Python global 修改全局变量

> 使用 global 修改全局变量，在多线程/异步环境中可能导致竞态条件。

```yaml
id: conc-python-global-mutable
languages: [python]
severity: WARNING
category: implementation
```

## 检测模式

```pattern
global $VAR
$VAR = ...
```
