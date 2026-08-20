# 命名规范测试案例

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
