# 异常处理 - Java 空 catch 块

> 空的 catch 块会吞掉异常，导致问题难以排查。

```yaml
id: err-java-empty-catch
languages: [java]
severity: WARNING
category: implementation
```

## 违规示例

```java
try {
    doSomething();
} catch (Exception e) {
    // 什么都不做
}
```

## 正确示例

```java
try {
    doSomething();
} catch (Exception e) {
    log.error("Operation failed", e);
    throw new BusinessException(e);
}
```

## 检测模式

```pattern
try {
  ...
} catch ($EXCEPTION $E) {
}
```

---

# 异常处理 - Java 捕获通用 Exception 未记录日志

> 捕获通用 Exception 未记录日志，建议捕获具体异常类型或至少记录日志。

```yaml
id: err-java-catch-generic
languages: [java]
severity: WARNING
category: implementation
```

## 检测模式

```pattern
catch (Exception $E) {
  ...
}
```

```pattern-not
catch (Exception $E) {
  log.error(...);
  ...
}
```

---

# 异常处理 - Java finally 块中抛出异常

> finally 块中抛出异常会覆盖 try 块中的原始异常，导致信息丢失。

```yaml
id: err-java-throw-in-finally
languages: [java]
severity: ERROR
category: implementation
```

## 检测模式

```pattern
finally {
  ...
  throw $EXCEPTION;
}
```

---

# 异常处理 - Python 裸 except

> 使用裸 except 会捕获所有异常（包括 SystemExit、KeyboardInterrupt）。

```yaml
id: err-python-bare-except
languages: [python]
severity: WARNING
category: implementation
```

## 正确示例

```python
except (ValueError, TypeError) as e:
    log.error(f"Operation failed: {e}")
```

## 检测模式

```pattern-regex
except\s*:
```

---

# 异常处理 - Python except 块中 pass

> except 块中使用 pass 吞掉异常，建议至少记录日志。

```yaml
id: err-python-silent-except
languages: [python]
severity: WARNING
category: implementation
```

## 检测模式

```pattern
try:
  ...
except:
  pass
```
