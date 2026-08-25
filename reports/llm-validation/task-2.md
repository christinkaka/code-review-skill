# 子Agent盲评任务：代码评审检出精确率验证

对下列每条检出，读取源码上下文，独立判断是真阳性(TP)还是误报(FP)。

判断标准：该代码在真实生产环境中是否构成所标注的安全/正确性问题。
框架代码、测试代码、常量拼接(无用户输入)、有上下游校验的情况判 FP。

## 待评清单

### 1. [sig-bypass-version-skip] CRITICAL
- 规则含义: 签名校验绕过：版本判断跳过签名验证
- 文件: repos/spring-boot/core/spring-boot-autoconfigure/src/main/java/org/springframework/boot/autoconfigure/condition/OnBeanCondition.java
- 行号: 194

### 2. [sig-bypass-version-skip] CRITICAL
- 规则含义: 签名校验绕过：版本判断跳过签名验证
- 文件: repos/spring-boot/loader/spring-boot-loader-tools/src/main/java/org/springframework/boot/loader/tools/LayersIndex.java
- 行号: 146

### 3. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/loader/spring-boot-loader-tools/src/main/java/org/springframework/boot/loader/tools/SizeCalculatingEntryWriter.java
- 行号: 64

### 4. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/zip/ZipContent.java
- 行号: 371

### 5. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/cli/spring-boot-cli/src/json-shade/java/org/springframework/boot/cli/json/JSONStringer.java
- 行号: 137

### 6. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/cli/spring-boot-cli/src/intTest/java/org/springframework/boot/cli/infrastructure/Versions.java
- 行号: 35

### 7. [ssrf-java-http-client] ERROR
- 规则含义: SSRF：用户可控 URL 发起服务端请求
- 文件: repos/spring-boot/module/spring-boot-rabbitmq/src/main/java/org/springframework/boot/rabbitmq/testcontainers/RabbitMqContainerConnectionDetailsFactory.java
- 行号: 71

### 8. [ssrf-java-http-client] ERROR
- 规则含义: SSRF：用户可控 URL 发起服务端请求
- 文件: repos/spring-boot/module/spring-boot-elasticsearch/src/main/java/org/springframework/boot/elasticsearch/autoconfigure/ElasticsearchRestClientConfigurations.java
- 行号: 309

### 9. [path-log-traversal] HIGH
- 规则含义: 日志路径穿越：日志内容含路径拼接
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 184

### 10. [path-log-traversal] HIGH
- 规则含义: 日志路径穿越：日志内容含路径拼接
- 文件: repos/spring-boot/module/spring-boot-web-server/src/testFixtures/java/org/springframework/boot/web/server/servlet/AbstractServletWebServerFactoryTests.java
- 行号: 1544

### 11. [ssrf-deep-detection] CRITICAL
- 规则含义: SSRF 深度检测
- 文件: repos/spring-boot/module/spring-boot-tomcat/src/main/java/org/springframework/boot/tomcat/servlet/TomcatServletWebServerFactory.java
- 行号: 553

### 12. [ssrf-deep-detection] CRITICAL
- 规则含义: SSRF 深度检测
- 文件: repos/spring-boot/module/spring-boot-tomcat/src/main/java/org/springframework/boot/tomcat/servlet/TomcatServletWebServerFactory.java
- 行号: 536

### 13. [xss-js-innerhtml] ERROR
- 规则含义: XSS：innerHTML 赋值用户可控内容
- 文件: repos/spring-boot/smoke-test/spring-boot-smoke-test-web-groovy-templates/src/main/resources/static/js/jquery-1.7.2.js
- 行号: 1572

### 14. [xss-js-innerhtml] ERROR
- 规则含义: XSS：innerHTML 赋值用户可控内容
- 文件: repos/spring-boot/smoke-test/spring-boot-smoke-test-web-groovy-templates/src/main/resources/static/js/jquery-1.7.2.js
- 行号: 6306
