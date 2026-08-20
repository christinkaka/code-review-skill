# 并发安全测试案例

## 违规代码 - SimpleDateFormat 作为 static

```java
public class DateUtils {
    static SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");

    public static String format(Date date) {
        return sdf.format(date);
    }
}
```

**预期命中**: `conc-java-unsafe-simpledateformat`
**文件类型**: `.java`

---

## 违规代码 - HashMap 作为 static 共享变量

```java
public class CacheManager {
    static Map<String, Object> cache = new HashMap<>();

    public static void put(String key, Object value) {
        cache.put(key, value);
    }
}
```

**预期命中**: `conc-java-unsafe-hashmap`
**文件类型**: `.java`

---

## 违规代码 - 双重检查锁定缺少 volatile

```java
public class Singleton {
    private static Singleton instance;

    public static Singleton getInstance() {
        if (instance == null) {
            synchronized (Singleton.class) {
                if (instance == null) {
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}
```

**预期命中**: `conc-java-double-checked-locking`
**文件类型**: `.java`

---

## 正确代码 - 使用 DateTimeFormatter

```java
public class DateUtils {
    static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    public static String format(LocalDate date) {
        return date.format(formatter);
    }
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - 使用 ConcurrentHashMap

```java
public class CacheManager {
    static Map<String, Object> cache = new ConcurrentHashMap<>();

    public static void put(String key, Object value) {
        cache.put(key, value);
    }
}
```

**预期命中**: 无
**文件类型**: `.java`
