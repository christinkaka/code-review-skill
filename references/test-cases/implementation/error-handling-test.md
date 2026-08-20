# 异常处理测试案例

## 违规代码 - Java 空 catch 块

```java
public void processFile(String path) {
    try {
        File file = new File(path);
        // process file...
    } catch (IOException e) {
    }
}
```

**预期命中**: `err-java-empty-catch`
**文件类型**: `.java`

---

## 违规代码 - Java finally 中抛出异常

```java
public void process() {
    try {
        doSomething();
    } catch (Exception e) {
        log.error("Error", e);
    } finally {
        cleanup();
        throw new RuntimeException("Force close");
    }
}
```

**预期命中**: `err-java-throw-in-finally`
**文件类型**: `.java`

---

## 违规代码 - Python 裸 except

```python
def process_data(data):
    try:
        result = parse(data)
    except:
        pass
    return result
```

**预期命中**: `err-python-bare-except`, `err-python-silent-except`
**文件类型**: `.py`

---

## 正确代码 - Java 记录日志并重新抛出

```java
public void processFile(String path) {
    try {
        File file = new File(path);
        // process file...
    } catch (IOException e) {
        log.error("Failed to process file: {}", path, e);
        throw new BusinessException("File processing failed", e);
    }
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Python 捕获具体异常

```python
def process_data(data):
    try:
        result = parse(data)
    except (ValueError, TypeError) as e:
        log.error(f"Parse failed: {e}")
        raise
    return result
```

**预期命中**: 无
**文件类型**: `.py`
