# 代码评审报告

**生成时间**: 2026-08-06T17:40:22.475486
**扫描耗时**: 2.44s

## 扫描信息

| 项目 | 值 |
|------|-----|
| 仓库 | `test-validation/` |
| 基线分支 | `N/A` |
| 目标分支 | `N/A` |
| 规约 Profile | `default` |

## 变更统计

- 变更文件数: **18**
- 新增行数: **0**
- 删除行数: **0**

## 调用图分析

- 调用图节点: **19**
- 调用边: **11**
- 受影响方法: **19**

## 问题摘要

| 严重等级 | 数量 |
|----------|------|
| CRITICAL | 39 |
| HIGH | 37 |
| MEDIUM | 4 |
| LOW | 0 |
| **总计** | **80** |

### 按类别分布

| 类别 | 数量 |
|------|------|
| security | 76 |
| unknown | 4 |

## 详细问题列表

### 1. 🔴 [path-read-traversal]

- **文件**: `java/path-traversal/Safe.java`
- **行号**: 25
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 2. 🔴 [path-read-traversal]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 27
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 3. 🔴 [path-read-traversal]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 37
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 4. 🔴 [sqli-java-statement-concat]

- **文件**: `java/sqli/Vulnerable.java`
- **行号**: 30
- **严重等级**: ERROR
- **类别**: security
- **描述**: Statement 执行拼接 SQL，存在注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-89 A03:2021

### 5. 🔴 [sqli-java-string-concat]

- **文件**: `java/sqli/Vulnerable.java`
- **行号**: 33
- **严重等级**: ERROR
- **类别**: security
- **描述**: 字符串拼接构建 SQL 语句，存在 SQL 注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-89 A03:2021

### 6. 🔴 [sqli-java-statement-concat]

- **文件**: `java/sqli/Vulnerable.java`
- **行号**: 42
- **严重等级**: ERROR
- **类别**: security
- **描述**: Statement 执行拼接 SQL，存在注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-89 A03:2021

### 7. 🔴 [sqli-java-string-concat]

- **文件**: `java/sqli/Vulnerable.java`
- **行号**: 45
- **严重等级**: ERROR
- **类别**: security
- **描述**: 字符串拼接构建 SQL 语句，存在 SQL 注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-89 A03:2021

### 8. 🔴 [xss-java-servlet-output]

- **文件**: `java/xss/Vulnerable.java`
- **行号**: 28
- **严重等级**: ERROR
- **类别**: security
- **描述**: Servlet 响应直接写入用户输入未做 HTML 转义，存在反射型 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 9. 🔴 [xss-java-servlet-output]

- **文件**: `java/xss/Vulnerable.java`
- **行号**: 42
- **严重等级**: ERROR
- **类别**: security
- **描述**: Servlet 响应直接写入用户输入未做 HTML 转义，存在反射型 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 10. 🔴 [xxe-java-document-builder]

- **文件**: `java/xxe/Vulnerable.java`
- **行号**: 22
- **严重等级**: ERROR
- **类别**: security
- **描述**: DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 11. 🔴 [xxe-java-document-builder]

- **文件**: `java/xxe/Vulnerable.java`
- **行号**: 29
- **严重等级**: ERROR
- **类别**: security
- **描述**: DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 12. 🔴 [priv-python-subprocess-run]

- **文件**: `python/command-injection/safe.py`
- **行号**: 30
- **严重等级**: ERROR
- **类别**: security
- **描述**: subprocess.run() 使用用户输入，存在命令注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-78

### 13. 🔴 [priv-python-subprocess-run]

- **文件**: `python/command-injection/vulnerable.py`
- **行号**: 22
- **严重等级**: ERROR
- **类别**: security
- **描述**: subprocess.run() 使用用户输入，存在命令注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-78

### 14. 🔴 [priv-python-os-system]

- **文件**: `python/command-injection/vulnerable.py`
- **行号**: 30
- **严重等级**: ERROR
- **类别**: security
- **描述**: os.system() 执行用户可控命令，存在命令注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-78

### 15. 🔴 [priv-python-subprocess-popen]

- **文件**: `python/command-injection/vulnerable.py`
- **行号**: 37
- **严重等级**: ERROR
- **类别**: security
- **描述**: subprocess.Popen() 使用用户输入，存在命令注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-78

### 16. 🔴 [priv-python-check-output-shell-true]

- **文件**: `python/command-injection/vulnerable.py`
- **行号**: 46
- **严重等级**: ERROR
- **类别**: security
- **描述**: subprocess.check_output() 使用 shell=True 执行命令，存在命令注入风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-78

### 17. 🔴 [path-read-traversal]

- **文件**: `python/path-traversal/safe.py`
- **行号**: 26
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 18. 🔴 [path-read-traversal]

- **文件**: `python/path-traversal/safe.py`
- **行号**: 39
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 19. 🔴 [path-read-traversal]

- **文件**: `python/path-traversal/safe.py`
- **行号**: 52
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 20. 🔴 [path-read-traversal]

- **文件**: `python/path-traversal/vulnerable.py`
- **行号**: 23
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 21. 🔴 [path-read-traversal]

- **文件**: `python/path-traversal/vulnerable.py`
- **行号**: 32
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 22. 🔴 [path-read-traversal]

- **文件**: `python/path-traversal/vulnerable.py`
- **行号**: 40
- **严重等级**: ERROR
- **类别**: security
- **描述**: 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 23. 🔴 [xxe-python-lxml-parser]

- **文件**: `python/xxe/vulnerable.py`
- **行号**: 14
- **严重等级**: ERROR
- **类别**: security
- **描述**: lxml.etree.XMLParser() 使用默认配置，未禁用外部实体解析（resolve_entities 默认为 True），存在 XXE 漏洞。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611

### 24. 🔴 [xxe-python-lxml-parse]

- **文件**: `python/xxe/vulnerable.py`
- **行号**: 14
- **严重等级**: ERROR
- **类别**: security
- **描述**: lxml.etree.parse() 未传入安全解析器，使用默认配置解析 XML 文件，存在 XXE 漏洞。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611

### 25. 🔴 [xxe-python-lxml-resolve-entities]

- **文件**: `python/xxe/vulnerable.py`
- **行号**: 14
- **严重等级**: ERROR
- **类别**: security
- **描述**: 显式设置 resolve_entities=True，主动启用了外部实体解析，存在 XXE 漏洞。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611

### 26. 🔴 [ssrf-js-http-get]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 31
- **严重等级**: ERROR
- **类别**: security
- **描述**: http.get() 请求用户可控 URL，存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 27. 🔴 [ssrf-js-http-get]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 31
- **严重等级**: ERROR
- **类别**: security
- **描述**: http.get() 请求用户可控 URL，存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 28. 🔴 [ssrf-js-fetch-weak-filter]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 56
- **严重等级**: ERROR
- **类别**: security
- **描述**: fetch 请求仅做简单字符串检查（如 includes("localhost")），可被 127.0.0.1、0.0.0.0 等绕过，存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 29. 🔴 [ssrf-js-fetch-weak-filter]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 56
- **严重等级**: ERROR
- **类别**: security
- **描述**: fetch 请求仅做简单字符串检查（如 includes("localhost")），可被 127.0.0.1、0.0.0.0 等绕过，存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 30. 🔴 [xss-js-innerhtml]

- **文件**: `typescript/xss/safe.ts`
- **行号**: 68
- **严重等级**: ERROR
- **类别**: security
- **描述**: innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 31. 🔴 [xss-js-innerhtml]

- **文件**: `typescript/xss/safe.ts`
- **行号**: 68
- **严重等级**: ERROR
- **类别**: security
- **描述**: innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 32. 🔴 [xss-js-innerhtml]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 21
- **严重等级**: ERROR
- **类别**: security
- **描述**: innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 33. 🔴 [xss-js-innerhtml]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 21
- **严重等级**: ERROR
- **类别**: security
- **描述**: innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 34. 🔴 [xss-js-document-write]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 30
- **严重等级**: ERROR
- **类别**: security
- **描述**: document.write() 直接写入用户输入，存在 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 35. 🔴 [xss-js-document-write]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 30
- **严重等级**: ERROR
- **类别**: security
- **描述**: document.write() 直接写入用户输入，存在 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 36. 🔴 [xss-js-outerhtml]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 40
- **严重等级**: ERROR
- **类别**: security
- **描述**: outerHTML 直接赋值用户输入，存在 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 37. 🔴 [xss-js-outerhtml]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 40
- **严重等级**: ERROR
- **类别**: security
- **描述**: outerHTML 直接赋值用户输入，存在 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 38. 🔴 [xss-js-dangerouslysetinnerhtml]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 50
- **严重等级**: ERROR
- **类别**: security
- **描述**: dangerouslySetInnerHTML 使用用户输入，存在 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 39. 🔴 [xss-js-dangerouslysetinnerhtml]

- **文件**: `typescript/xss/vulnerable.ts`
- **行号**: 50
- **严重等级**: ERROR
- **类别**: security
- **描述**: dangerouslySetInnerHTML 使用用户输入，存在 XSS 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-79 A03:2021

### 40. ⚪ [crypto-hardcoded-key-java]

- **文件**: `java/path-traversal/Safe.java`
- **行号**: 18
- **严重等级**: HIGH
- **类别**: unknown
- **描述**: Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-798 A07:2021

### 41. ⚪ [path-write-traversal]

- **文件**: `java/path-traversal/Safe.java`
- **行号**: 25
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 42. ⚪ [path-config-traversal]

- **文件**: `java/path-traversal/Safe.java`
- **行号**: 32
- **严重等级**: HIGH
- **类别**: security
- **描述**: 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 43. ⚪ [crypto-hardcoded-key-java]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 20
- **严重等级**: HIGH
- **类别**: unknown
- **描述**: Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-798 A07:2021

### 44. ⚪ [path-write-traversal]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 27
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 45. ⚪ [path-config-traversal]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 28
- **严重等级**: HIGH
- **类别**: security
- **描述**: 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 46. 🟡 [path-traversal-pattern]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 36
- **严重等级**: WARNING
- **类别**: security
- **描述**: 检测代码中是否包含路径穿越模式（`../`、`..\`、`%2e%2e%2f` 等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 47. ⚪ [path-write-traversal]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 37
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 48. ⚪ [path-config-traversal]

- **文件**: `java/path-traversal/Vulnerable.java`
- **行号**: 38
- **严重等级**: HIGH
- **类别**: security
- **描述**: 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 49. ⚪ [crypto-hardcoded-key-java]

- **文件**: `java/sqli/Safe.java`
- **行号**: 30
- **严重等级**: HIGH
- **类别**: unknown
- **描述**: Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-798 A07:2021

### 50. ⚪ [crypto-hardcoded-key-java]

- **文件**: `java/sqli/Safe.java`
- **行号**: 43
- **严重等级**: HIGH
- **类别**: unknown
- **描述**: Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-798 A07:2021

### 51. ⚪ [xxe-deep-detection]

- **文件**: `java/xxe/Safe.java`
- **行号**: 19
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 52. ⚪ [xxe-deep-detection]

- **文件**: `java/xxe/Safe.java`
- **行号**: 31
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 53. ⚪ [xxe-deep-detection]

- **文件**: `java/xxe/Vulnerable.java`
- **行号**: 22
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 54. ⚪ [xxe-deep-detection]

- **文件**: `java/xxe/Vulnerable.java`
- **行号**: 29
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 55. ⚪ [path-write-traversal]

- **文件**: `python/path-traversal/safe.py`
- **行号**: 52
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 56. ⚪ [path-write-traversal]

- **文件**: `python/path-traversal/vulnerable.py`
- **行号**: 40
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-22 A01:2021

### 57. 🟡 [xxe-python-lxml]

- **文件**: `python/xxe/vulnerable.py`
- **行号**: 14
- **严重等级**: WARNING
- **类别**: security
- **描述**: lxml.etree.parse() 默认可能解析外部实体，建议使用 defusedxml 替代。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611

### 58. ⚪ [xxe-deep-detection]

- **文件**: `python/xxe/vulnerable.py`
- **行号**: 28
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-611 A05:2021

### 59. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 28
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 60. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 28
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 61. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 40
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 62. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 40
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 63. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 40
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 64. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 40
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 65. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 64
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 66. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 64
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 67. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 82
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 68. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 82
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 69. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 82
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 70. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/safe.ts`
- **行号**: 82
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 71. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 22
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 72. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 22
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 73. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 22
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 74. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 22
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 75. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 44
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 76. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 44
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 77. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 59
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 78. ⚪ [ssrf-deep-detection]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 59
- **严重等级**: CRITICAL
- **类别**: security
- **描述**: 服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918 A10:2021

### 79. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 59
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

### 80. 🟡 [ssrf-js-fetch]

- **文件**: `typescript/ssrf/vulnerable.ts`
- **行号**: 59
- **严重等级**: WARNING
- **类别**: security
- **描述**: fetch 请求用户可控 URL（服务端），存在 SSRF 风险。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-918

---
*报告由代码评审工具自动生成 | 2026-08-06 17:40:22*