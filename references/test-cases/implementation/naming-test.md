# 命名规范测试案例

## 违规代码 - Java 布尔变量语义空泛名

```java
public class Job {
    public void run() {
        boolean flag = true;
        boolean tmp = false;
        boolean b1 = queue.isEmpty();
    }
}
```

**预期命中**: `naming-java-boolean-vague`
**文件类型**: `.java`

---

## 违规代码 - Java 常量未使用大写

```java
public class Config {
    static final String maxRetryCount = "3";
    static final String apiBaseUrl = "https://api.example.com";
}
```

**预期命中**: `naming-java-constant-case`
**文件类型**: `.java`

---

## 违规代码 - Python 类名未使用 PascalCase

```python
class user_service:
    def get_user(self, user_id):
        pass

class data_processor:
    def process(self, data):
        pass
```

**预期命中**: `naming-python-class-case`
**文件类型**: `.py`

---

## 正确代码 - Java 布尔变量命名语义明确

```java
public class Job {
    public void run() {
        boolean isValid = true;
        boolean found = false;
        boolean preserveTimestamps = config.isPreserveTimestamps();
    }
}
```

**预期命中**: 无（`naming-java-boolean-prefix` 已停用：JavaBeans 主流约定为字段无前缀 + 访问器带 is 前缀，spring-boot 185 个布尔字段 0 个带前缀）
**文件类型**: `.java`

---

## 正确代码 - Java 常量使用 UPPER_SNAKE_CASE

```java
public class Config {
    static final String MAX_RETRY_COUNT = "3";
    static final String API_BASE_URL = "https://api.example.com";
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Python 类名使用 PascalCase

```python
class UserService:
    def get_user(self, user_id):
        pass

class DataProcessor:
    def process(self, data):
        pass
```

**预期命中**: 无
**文件类型**: `.py`
