# 子Agent盲评任务（修复后复测）：精确率验证

对下列每条检出，读取源码上下文，独立判断是真阳性(TP)还是误报(FP)。

判断标准：该代码在真实生产环境中是否构成所标注的安全/正确性问题。
框架内部安全用法、常量拼接(无用户输入)、有上下游校验、受信配置源判 FP。

注意：本批检出已经过测试目录过滤，全部来自生产代码目录（src/main 等），
请不要以"测试代码"为由判 FP；请基于数据流和语义判断。

## 待评清单

### 1. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/cli/spring-boot-cli/src/intTest/java/org/springframework/boot/cli/infrastructure/CommandLineInvoker.java
- 行号: 87

### 2. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/main/java/org/springframework/boot/maven/AbstractPackagerMojo.java
- 行号: 202

### 3. [deser-java-object-input-stream] CRITICAL
- 规则含义: 反序列化：ObjectInputStream 反序列化不可信数据
- 文件: repos/spring-boot/module/spring-boot-devtools/src/main/java/org/springframework/boot/devtools/restart/server/HttpRestartServer.java
- 行号: 80

### 4. [deser-java-object-input-stream] CRITICAL
- 规则含义: 反序列化：ObjectInputStream 反序列化不可信数据
- 文件: repos/spring-boot/core/spring-boot/src/main/java/org/springframework/boot/logging/logback/SpringBootJoranConfigurator.java
- 行号: 342

### 5. [deser-java-object-input-stream] CRITICAL
- 规则含义: 反序列化：ObjectInputStream 反序列化不可信数据
- 文件: repos/spring-boot/core/spring-boot/src/main/java/org/springframework/boot/logging/logback/SpringBootJoranConfigurator.java
- 行号: 341

### 6. [path-log-traversal] HIGH
- 规则含义: 日志路径穿越：日志内容含路径拼接
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 184

### 7. [path-log-traversal] HIGH
- 规则含义: 日志路径穿越：日志内容含路径拼接
- 文件: repos/spring-boot/configuration-metadata/spring-boot-configuration-metadata-changelog-generator/src/main/java/org/springframework/boot/configurationmetadata/changelog/ChangelogWriter.java
- 行号: 59

### 8. [ssrf-java-url-connection] ERROR
- 规则含义: SSRF：用户可控 URL 发起服务端请求（含 openConnection）
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/launch/PropertiesLauncher.java
- 行号: 219

### 9. [ssrf-java-url-connection] ERROR
- 规则含义: SSRF：用户可控 URL 发起服务端请求（含 openConnection）
- 文件: repos/spring-boot/module/spring-boot-jetty/src/main/java/org/springframework/boot/jetty/servlet/JasperInitializer.java
- 行号: 147

### 10. [sig-java-verify-skip] ERROR
- 规则含义: 验签流程不完整：Signature initVerify+update 但未检查 verify 返回值
- 文件: repos/spring-boot/module/spring-boot-cloudfoundry/src/main/java/org/springframework/boot/cloudfoundry/autoconfigure/actuate/endpoint/servlet/TokenValidator.java
- 行号: 97

### 11. [sig-java-verify-skip] ERROR
- 规则含义: 验签流程不完整：Signature initVerify+update 但未检查 verify 返回值
- 文件: repos/spring-boot/module/spring-boot-cloudfoundry/src/main/java/org/springframework/boot/cloudfoundry/autoconfigure/actuate/endpoint/reactive/TokenValidator.java
- 行号: 105

### 12. [conc-java-unsafe-hashmap] ERROR
- 规则含义: 并发安全：非线程安全集合在并发上下文使用
- 文件: repos/spring-boot/core/spring-boot-docker-compose/src/main/java/org/springframework/boot/docker/compose/core/DockerCli.java
- 行号: 47

### 13. [err-java-throw-in-finally] ERROR
- 规则含义: finally 中抛出异常掩盖原始异常
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/net/protocol/nested/NestedUrlConnection.java
- 行号: 219

### 14. [sqli-java-string-concat] ERROR
- 规则含义: SQL 字符串拼接注入
- 文件: repos/spring-boot/module/spring-boot-jdbc/src/main/java/org/springframework/boot/jdbc/DatabaseDriver.java
- 行号: 51

### 15. [ssrf-deep-detection] CRITICAL
- 规则含义: SSRF：服务端请求伪造深度检测
- 文件: repos/spring-boot/module/spring-boot-jetty/src/main/java/org/springframework/boot/jetty/servlet/JasperInitializer.java
- 行号: 147
