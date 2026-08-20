# SQL 注入测试案例

## 违规代码 - Java 字符串拼接 SQL

```java
public User findUser(String userId) throws SQLException {
    String sql = "SELECT * FROM users WHERE id = " + userId;
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery(sql);
    // ...
}
```

**预期命中**: `sqli-java-string-concat`
**文件类型**: `.java`

---

## 违规代码 - Python f-string SQL

```python
def find_user(user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()
```

**预期命中**: `sqli-python-execute-format`
**文件类型**: `.py`

---

## 违规代码 - Python format() SQL

```python
def find_user(user_id):
    query = "SELECT * FROM users WHERE id = {}".format(user_id)
    cursor.execute(query)
    return cursor.fetchone()
```

**预期命中**: `sqli-python-execute-format`
**文件类型**: `.py`

---

## 正确代码 - Java PreparedStatement

```java
public User findUser(String userId) throws SQLException {
    String sql = "SELECT * FROM users WHERE id = ?";
    PreparedStatement ps = conn.prepareStatement(sql);
    ps.setString(1, userId);
    ResultSet rs = ps.executeQuery();
    // ...
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Python 参数化查询

```python
def find_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
```

**预期命中**: 无
**文件类型**: `.py`
