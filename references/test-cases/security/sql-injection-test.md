# SQL 注入测试案例

## 违规代码 - Java Statement 字符串拼接 SQL

```java
protected void doGet(HttpServletRequest request, HttpServletResponse response)
        throws ServletException, IOException {
    String userId = request.getParameter("id");
    String sql = "SELECT * FROM users WHERE id = " + userId;
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery(sql);
}
```

**预期命中**: `sqli-taint`
**文件类型**: `.java`

---

## 违规代码 - Java 请求参数直接流入 execute

```java
protected void doPost(HttpServletRequest request, HttpServletResponse response)
        throws ServletException, IOException {
    String name = request.getParameter("name");
    Statement stmt = conn.createStatement();
    stmt.execute("SELECT * FROM users WHERE name = '" + name + "'");
}
```

**预期命中**: `sqli-taint`
**文件类型**: `.java`

---

## 正确代码 - Java PreparedStatement 参数绑定

```java
protected void doGet(HttpServletRequest request, HttpServletResponse response)
        throws ServletException, IOException {
    String userId = request.getParameter("id");
    String sql = "SELECT * FROM users WHERE id = ?";
    PreparedStatement ps = conn.prepareStatement(sql);
    ps.setString(1, userId);
    ResultSet rs = ps.executeQuery();
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Java 常量 SQL 执行

```java
public List<User> listAll() throws SQLException {
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery("SELECT * FROM users");
    // ...
}
```

**预期命中**: 无
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
