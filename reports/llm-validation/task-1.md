# 子Agent盲评任务：代码评审检出精确率验证

对下列每条检出，读取源码上下文，独立判断是真阳性(TP)还是误报(FP)。

判断标准：该代码在真实生产环境中是否构成所标注的安全/正确性问题。
框架代码、测试代码、常量拼接(无用户输入)、有上下游校验的情况判 FP。

## 待评清单

### 1. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 174

### 2. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/test-support/spring-boot-gradle-test-support/src/main/java/org/springframework/boot/testsupport/gradle/testkit/GradleBuild.java
- 行号: 175

### 3. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/JarIntegrationTests.java
- 行号: 371

### 4. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/JarIntegrationTests.java
- 行号: 320

### 5. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/test-support/spring-boot-gradle-test-support/src/main/java/org/springframework/boot/testsupport/gradle/testkit/GradleBuild.java
- 行号: 177

### 6. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/WarIntegrationTests.java
- 行号: 155

### 7. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 174

### 8. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 178

### 9. [sqli-java-mybatis-dollar] ERROR
- 规则含义: MyBatis ${} 注入：SQL 使用 $ 直接拼接参数
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/main/java/org/springframework/boot/maven/BuildImageMojo.java
- 行号: 82

### 10. [sqli-java-mybatis-dollar] ERROR
- 规则含义: MyBatis ${} 注入：SQL 使用 $ 直接拼接参数
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/main/java/org/springframework/boot/maven/BuildInfoMojo.java
- 行号: 73

### 11. [sqli-java-mybatis-dollar] ERROR
- 规则含义: MyBatis ${} 注入：SQL 使用 $ 直接拼接参数
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/launch/PropertiesLauncher.java
- 行号: 153

### 12. [sqli-java-mybatis-dollar] ERROR
- 规则含义: MyBatis ${} 注入：SQL 使用 $ 直接拼接参数
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/main/java/org/springframework/boot/maven/AbstractRunMojo.java
- 行号: 74

### 13. [sig-bypass-version-skip] CRITICAL
- 规则含义: 签名校验绕过：版本判断跳过签名验证
- 文件: repos/spring-boot/module/spring-boot-websocket/src/main/java/org/springframework/boot/websocket/autoconfigure/servlet/WebSocketMessagingAutoConfiguration.java
- 行号: 161

### 14. [sig-bypass-version-skip] CRITICAL
- 规则含义: 签名校验绕过：版本判断跳过签名验证
- 文件: repos/spring-boot/core/spring-boot/src/main/java/org/springframework/boot/env/ConfigTreePropertySource.java
- 行号: 249
