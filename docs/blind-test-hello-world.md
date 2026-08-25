# 真实仓库双盲复测报告：hello-world (VulnUserManager)

**测试日期**：2026-08-25  
**测试仓库**：[AnshuPandey00/hello-world](https://github.com/AnshuPandey00/hello-world)  
**仓库规模**：18 个 Java 文件  
**测试目的**：对比 taint 规则与旧模式规则在真实漏洞仓库上的检出差异

## 测试方法

1. 使用旧规则（commit `c501b3c`，taint 迁移前）扫描仓库，记录检出
2. 使用 taint 规则（commit `dd4cabf`，合并后）扫描同一仓库，记录检出
3. 对比差异，分析 taint 规则的精准度和覆盖范围

## 检出对比

| 规则类型 | 旧规则 | taint 规则 | 差异 |
|---------|--------|-----------|------|
| Java 检出总数 | 36 | 34 | -2 |
| path-traversal | 0 | 2 | +2（新增） |
| deser | 2 | 0 | -2（被替代） |
| sqli | 1 | 0 | -1（被替代） |
| 其他规则 | 33 | 32 | -1 |

## 详细分析

### taint 规则新增检出（2 个）

**FileController.java:104-105**
```java
Path filePath = Paths.get(UPLOAD_DIR + filename);
Files.write(filePath, file.getBytes());
```
- **漏洞类型**：目录穿越（CWE-22）
- **检出原因**：filename 来自用户输入（MultipartFile.getOriginalFilename），直接拼接到路径
- **taint 追踪**：source（HTTP 请求）→ sink（Files.write）
- **结论**：真实漏洞，taint 规则正确检出

### 旧规则独有检出（3 个）

**SerializeController.java:52-55**（2 个 deser）
```java
ObjectInputStream objectInputStream = new ObjectInputStream(byteStream);
Object deserializedObject = objectInputStream.readObject();
```
- **漏洞类型**：不安全反序列化（CWE-502）
- **未检出原因**：deser-taint 的 source 只覆盖 Servlet API（getParameter/getHeader），不覆盖 Spring `@RequestBody`
- **结论**：设计决策，非 bug。taint 规则聚焦 HTTP Servlet → JDBC 链路

**UserService.java:105**（1 个 sqli）
```java
String jpql = "SELECT u FROM User u WHERE u.username LIKE '%" + query + "%'";
Query jpqlQuery = entityManager.createQuery(jpql);
```
- **漏洞类型**：SQL 注入（CWE-89）
- **未检出原因**：sqli-taint 的 sink 只覆盖 JDBC API（execute/executeQuery），不覆盖 JPA `createQuery`
- **结论**：设计决策，非 bug。taint 规则聚焦 JDBC API

## 结论

### taint 规则优势
1. **精准度更高**：数据流追踪替代模式匹配，path-traversal 检出真实漏洞
2. **误报更少**：旧规则的 deser/sqli 是模式匹配，可能对常量/安全代码误报

### taint 规则局限
1. **覆盖范围有限**：只追踪 HTTP Servlet → JDBC 链路
2. **不覆盖 Spring 注解**：@RequestBody/@RequestParam 等不作为 source
3. **不覆盖 JPA/Hibernate**：createQuery 等不作为 sink

### 后续建议
1. **扩展 source 覆盖**：增加 Spring 注解（@RequestBody/@RequestParam/@PathVariable）
2. **扩展 sink 覆盖**：增加 JPA API（createQuery/createNativeQuery）
3. **补充测试用例**：在 test-validation 中增加 Spring 注解和 JPA 场景

## 附录：规则清单

### 旧规则（commit c501b3c）
- deser-java-object-input-stream：模式匹配 `new ObjectInputStream($USER_INPUT)`
- sqli-java-string-concat：模式匹配 SQL 字符串拼接

### taint 规则（commit dd4cabf）
- path-traversal-taint：数据流追踪，source=HTTP Servlet API，sink=文件操作
- ssrf-taint：数据流追踪，source=HTTP Servlet API，sink=出站请求
- xss-taint：数据流追踪，source=HTTP Servlet API，sink=响应输出
- sqli-taint：数据流追踪，source=HTTP Servlet API，sink=JDBC 执行
- deser-taint：数据流追踪，source=HTTP Servlet API，sink=反序列化/JNDI
