# 子Agent盲评任务（修复后复测）：精确率验证

对下列每条检出，读取源码上下文，独立判断是真阳性(TP)还是误报(FP)。

判断标准：该代码在真实生产环境中是否构成所标注的安全/正确性问题。
框架内部安全用法、常量拼接(无用户输入)、有上下游校验、受信配置源判 FP。

注意：本批检出已经过测试目录过滤，全部来自生产代码目录（src/main 等），
请不要以"测试代码"为由判 FP；请基于数据流和语义判断。

## 待评清单

### 1. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 174

### 2. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/integration-test/spring-boot-server-integration-tests/src/intTest/java/org/springframework/boot/context/embedded/IdeApplicationLauncher.java
- 行号: 117

### 3. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/module/spring-boot-webmvc/src/main/java/org/springframework/boot/webmvc/autoconfigure/JspTemplateAvailabilityProvider.java
- 行号: 65

### 4. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/integration-test/spring-boot-server-integration-tests/src/intTest/java/org/springframework/boot/context/embedded/BootRunApplicationLauncher.java
- 行号: 101

### 5. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/integration-test/spring-boot-server-integration-tests/src/intTest/java/org/springframework/boot/context/embedded/BootRunApplicationLauncher.java
- 行号: 74

### 6. [path-write-traversal] CRITICAL
- 规则含义: 路径穿越写入：用户可控输入未校验即拼入文件写入路径
- 文件: repos/spring-boot/integration-test/spring-boot-server-integration-tests/src/intTest/java/org/springframework/boot/context/embedded/IdeApplicationLauncher.java
- 行号: 86

### 7. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 174

### 8. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 178

### 9. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/build-plugin/spring-boot-maven-plugin/src/intTest/java/org/springframework/boot/maven/MavenBuild.java
- 行号: 183

### 10. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/integration-test/spring-boot-server-integration-tests/src/intTest/java/org/springframework/boot/context/embedded/BootRunApplicationLauncher.java
- 行号: 78

### 11. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/module/spring-boot-devtools/src/main/java/org/springframework/boot/devtools/restart/server/RestartServer.java
- 行号: 105

### 12. [path-read-traversal] ERROR
- 规则含义: 路径穿越读取：用户可控输入未校验即拼入文件读取路径
- 文件: repos/spring-boot/module/spring-boot-web-server/src/main/java/org/springframework/boot/web/server/servlet/SessionStoreDirectory.java
- 行号: 51

### 13. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/loader/spring-boot-loader-tools/src/main/java/org/springframework/boot/loader/tools/SizeCalculatingEntryWriter.java
- 行号: 64

### 14. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/loader/spring-boot-loader/src/main/java/org/springframework/boot/loader/zip/ZipContent.java
- 行号: 371

### 15. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/cli/spring-boot-cli/src/json-shade/java/org/springframework/boot/cli/json/JSONStringer.java
- 行号: 137

### 16. [path-config-traversal] HIGH
- 规则含义: 配置路径穿越：配置值拼入文件路径可能导致越权访问
- 文件: repos/spring-boot/cli/spring-boot-cli/src/intTest/java/org/springframework/boot/cli/infrastructure/Versions.java
- 行号: 35
