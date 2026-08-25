# 子Agent盲评任务：代码评审检出精确率验证

对下列每条检出，读取源码上下文，独立判断是真阳性(TP)还是误报(FP)。

判断标准：该代码在真实生产环境中是否构成所标注的安全/正确性问题。
框架代码、测试代码、常量拼接(无用户输入)、有上下游校验的情况判 FP。

## 待评清单

### 1. [deser-java-object-input-stream] CRITICAL
- 规则含义: 反序列化：ObjectInputStream 反序列化不可信数据
- 文件: repos/spring-boot/module/spring-boot-devtools/src/main/java/org/springframework/boot/devtools/restart/server/HttpRestartServer.java
- 行号: 80

### 2. [deser-java-object-input-stream] CRITICAL
- 规则含义: 反序列化：ObjectInputStream 反序列化不可信数据
- 文件: repos/spring-boot/core/spring-boot/src/main/java/org/springframework/boot/logging/logback/SpringBootJoranConfigurator.java
- 行号: 342

### 3. [xxe-deep-detection] CRITICAL
- 规则含义: XXE：XML 外部实体解析
- 文件: repos/spring-boot/module/spring-boot-jooq/src/main/java/org/springframework/boot/jooq/autoconfigure/JooqAutoConfiguration.java
- 行号: 165

### 4. [xxe-deep-detection] CRITICAL
- 规则含义: XXE：XML 外部实体解析
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/main/java/org/springframework/boot/maven/AbstractPackagerMojo.java
- 行号: 234

### 5. [ssrf-java-url-connection] ERROR
- 规则含义: SSRF：URLConnection 用户可控目标
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/launch/PropertiesLauncher.java
- 行号: 219

### 6. [ssrf-java-url-connection] ERROR
- 规则含义: SSRF：URLConnection 用户可控目标
- 文件: repos/spring-boot/module/spring-boot-jetty/src/main/java/org/springframework/boot/jetty/servlet/JasperInitializer.java
- 行号: 147

### 7. [sig-java-verify-skip] ERROR
- 规则含义: 验签跳过：verify 返回值被忽略
- 文件: repos/spring-boot/module/spring-boot-cloudfoundry/src/main/java/org/springframework/boot/cloudfoundry/autoconfigure/actuate/endpoint/servlet/TokenValidator.java
- 行号: 97

### 8. [sig-java-verify-skip] ERROR
- 规则含义: 验签跳过：verify 返回值被忽略
- 文件: repos/spring-boot/module/spring-boot-cloudfoundry/src/main/java/org/springframework/boot/cloudfoundry/autoconfigure/actuate/endpoint/reactive/TokenValidator.java
- 行号: 105

### 9. [hardcoded-password] ERROR
- 规则含义: 硬编码密码
- 文件: repos/spring-boot/module/spring-boot-security/src/test/java/org/springframework/boot/security/autoconfigure/UserDetailsServiceAutoConfigurationTests.java
- 行号: 193

### 10. [hardcoded-password] ERROR
- 规则含义: 硬编码密码
- 文件: repos/spring-boot/module/spring-boot-security/src/test/java/org/springframework/boot/security/autoconfigure/ReactiveUserDetailsServiceAutoConfigurationTests.java
- 行号: 146

### 11. [conc-java-unsafe-hashmap] ERROR
- 规则含义: 并发安全：非线程安全集合在并发上下文使用
- 文件: repos/spring-boot/core/spring-boot-docker-compose/src/main/java/org/springframework/boot/docker/compose/core/DockerCli.java
- 行号: 47

### 12. [err-java-throw-in-finally] ERROR
- 规则含义: finally 中抛出异常掩盖原始异常
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/net/protocol/nested/NestedUrlConnection.java
- 行号: 219

### 13. [sqli-java-string-concat] ERROR
- 规则含义: SQL 字符串拼接注入
- 文件: repos/spring-boot/module/spring-boot-jdbc/src/main/java/org/springframework/boot/jdbc/DatabaseDriver.java
- 行号: 51

### 14. [xss-js-outerhtml] ERROR
- 规则含义: XSS：outerHTML 赋值
- 文件: repos/spring-boot/smoke-test/spring-boot-smoke-test-web-groovy-templates/src/main/resources/static/js/jquery-1.7.2.js
- 行号: 6153
