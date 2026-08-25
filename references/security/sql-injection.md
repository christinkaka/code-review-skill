# SQL 注入 - 用户可控数据流入 SQL 执行（数据流分析）

> 用户可控数据（HTTP 请求参数/头）经赋值、字符串拼接传播后流入 SQL 执行 API 或 SQL 构造 API。基于 Semgrep taint 模式做过程内数据流追踪，PreparedStatement 参数绑定（setString 等）作为净化器切断污点传播。

```yaml
id: sqli-taint
languages: [java]
severity: ERROR
cwe: CWE-89
owasp: A03:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流
- **污点汇聚**：SQL 执行 API（execute、executeQuery、executeUpdate、prepareStatement）
- **净化器**：PreparedStatement 参数绑定（setString、setInt、setLong、setObject 等）

`request.getParameter("id")` 之后 `"SELECT ... WHERE id = " + userId` 流入 `executeQuery` 命中（污点随字符串拼接传播）；
`conn.prepareStatement("SELECT ... WHERE id = ?")` + `ps.setString(1, userId)` 不报（setString 切断污点）；
常量 SQL 字符串无污点源，不报。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
```

```pattern-sinks
$STMT.execute(...)
$STMT.executeQuery(...)
$STMT.executeUpdate(...)
$CONN.prepareStatement(...)
```

```pattern-sanitizers
$PS.setString(...)
$PS.setInt(...)
$PS.setLong(...)
$PS.setFloat(...)
$PS.setDouble(...)
$PS.setBoolean(...)
$PS.setDate(...)
$PS.setTime(...)
$PS.setTimestamp(...)
$PS.setObject(...)
```

---

# SQL 注入 - MyBatis ${} 占位符滥用（已重构 - 限定真实 MyBatis 上下文）

> MyBatis 使用 ${} 占位符直接拼接变量，存在 SQL 注入风险。
> 注意：2026-08-25 盲评实测，旧模式 `\$\{[a-zA-Z_.]+\}`（languages: [java]）
> 在 spring-boot 全库 4/4 误报——命中的全是 Maven `@Parameter("${project...}")`
> 属性插值与 Spring `@Value` 表达式，与 SQL 无关。MyBatis ${} 注入的真实
> 发生地是 XML mapper 的 SQL 标签文本与 @Select 系注解字符串，故拆分为
> 两条定向规则。

```yaml
id: sqli-java-mybatis-dollar
languages: [java]
severity: ERROR
cwe: CWE-89
enabled: false
```

## 检测模式（已停用）

```pattern-regex
\$\{[a-zA-Z_.]+\}
```

---

# SQL 注入 - MyBatis 注解 ${} 占位符

> MyBatis @Select/@Update/@Insert/@Delete 注解字符串中使用 ${} 拼接变量。

```yaml
id: sqli-java-mybatis-annotation
languages: [java]
severity: ERROR
cwe: CWE-89
```

## 违规示例

```java
@Select("SELECT * FROM users WHERE id = ${id}")
User findById(@Param("id") long id);
```

## 正确示例

```java
@Select("SELECT * FROM users WHERE id = #{id}")
User findById(@Param("id") long id);
```

## 检测模式

```pattern-regex
@(?:Select|Update|Insert|Delete)\s*(?:\([^)]*value\s*=\s*)?\(?\"[^\"]*\$\{[a-zA-Z_.]+\}
```

---

# SQL 注入 - MyBatis XML mapper ${} 占位符

> MyBatis XML mapper 的 select/update/insert/delete 标签文本中使用 ${} 拼接。

```yaml
id: sqli-xml-mybatis-dollar
languages: [xml]
severity: ERROR
cwe: CWE-89
```

## 违规示例

```xml
<select id="findUser">
    SELECT * FROM users WHERE name = ${name}
</select>
```

## 正确示例

```xml
<select id="findUser">
    SELECT * FROM users WHERE name = #{name}
</select>
```

## 检测模式

```pattern-regex
(?:SELECT|select|INSERT|insert|UPDATE|update|DELETE|delete)[^<>]*\$\{[a-zA-Z_.]+\}
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
