# SQL 注入 - Java 字符串拼接构建 SQL

> 字符串拼接构建 SQL 语句，存在 SQL 注入风险。

```yaml
id: sqli-java-string-concat
languages: [java]
severity: ERROR
cwe: CWE-89
owasp: A03:2021
```

## 违规示例

```java
String sql = "SELECT * FROM users WHERE id = " + userId;
Statement stmt = conn.createStatement();
stmt.execute(sql);
```

## 正确示例

```java
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setString(1, userId);
ps.execute();
```

## 检测模式

```pattern-regex
"(SELECT|INSERT|UPDATE|DELETE)[\s\S]*?"\s*\+\s*\w+
```

---

# SQL 注入 - Java Statement 执行拼接 SQL

> Statement 执行拼接 SQL，存在注入风险。

```yaml
id: sqli-java-statement-execute
languages: [java]
severity: ERROR
cwe: CWE-89
```

## 检测模式

```pattern
Statement $STMT = ...;
...
$STMT.execute("..." + $VAR + "...");
```

---

# SQL 注入 - Java Statement 执行拼接 SQL (executeQuery)

> Statement 执行拼接 SQL，存在注入风险。

```yaml
id: sqli-java-statement-concat
languages: [java]
severity: ERROR
cwe: CWE-89
owasp: A03:2021
```

## 违规示例

```java
Statement stmt = conn.createStatement();
String sql = "SELECT * FROM users WHERE id = " + userId;
stmt.executeQuery(sql);  // 危险：SQL 注入
```

## 正确示例

```java
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setString(1, userId);
ps.executeQuery();
```

## 检测模式

```pattern
Statement $STMT = ...;
...
$STMT.executeQuery($SQL);
```

---

# SQL 注入 - MyBatis ${} 占位符滥用

> MyBatis 使用 ${} 占位符直接拼接变量，存在 SQL 注入风险。

```yaml
id: sqli-java-mybatis-dollar
languages: [java]
severity: ERROR
cwe: CWE-89
```

## 正确示例

使用 `#{}` 参数化占位符替代 `${}`。

## 检测模式

```pattern-regex
\$\{[a-zA-Z_.]+\}
```

---

# SQL 注入 - Python 字符串格式化构建 SQL

> Python 使用字符串格式化/拼接构建 SQL，存在注入风险。

```yaml
id: sqli-python-execute-format
languages: [python]
severity: ERROR
cwe: CWE-89
```

## 违规示例

```python
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

## 正确示例

```python
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

## 检测模式

```pattern
$CURSOR.execute("...".format(...))
```

```pattern
$CURSOR.execute(f"...")
```

```pattern
$CURSOR.execute("..." + ... + "...")
```

```pattern
$QUERY = "...".format(...);
...
$CURSOR.execute($QUERY)
```

---

# SQL 注入 - SQLAlchemy raw query 字符串拼接

> SQLAlchemy raw query 使用字符串拼接，存在注入风险。

```yaml
id: sqli-python-raw-query
languages: [python]
severity: ERROR
cwe: CWE-89
```

## 检测模式

```pattern
$ENGINE.execute("..." + ...)
```
