请对以下代码扫描结果进行评审：

## 工作流
综合评审工作流

## 温度参数
temperature: 0.1

## 扫描结果
[
  {
    "rule_id": "crypto-hardcoded-key-java",
    "category": "unknown",
    "severity": "HIGH",
    "file": "java/path-traversal/Safe.java",
    "line": 18,
    "end_line": 18,
    "message": "Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-798",
      "owasp": "A07:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "java/path-traversal/Safe.java",
    "line": 25,
    "end_line": 25,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-write-traversal",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/path-traversal/Safe.java",
    "line": 25,
    "end_line": 25,
    "message": "文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-config-traversal",
    "category": "security",
    "severity": "HIGH",
    "file": "java/path-traversal/Safe.java",
    "line": 32,
    "end_line": 32,
    "message": "配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "crypto-hardcoded-key-java",
    "category": "unknown",
    "severity": "HIGH",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 20,
    "end_line": 20,
    "message": "Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-798",
      "owasp": "A07:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 27,
    "end_line": 27,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-write-traversal",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 27,
    "end_line": 27,
    "message": "文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-config-traversal",
    "category": "security",
    "severity": "HIGH",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 28,
    "end_line": 28,
    "message": "配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-traversal-pattern",
    "category": "security",
    "severity": "WARNING",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 36,
    "end_line": 36,
    "message": "检测代码中是否包含路径穿越模式（`../`、`..\\`、`%2e%2e%2f` 等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 37,
    "end_line": 37,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-write-traversal",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 37,
    "end_line": 37,
    "message": "文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-config-traversal",
    "category": "security",
    "severity": "HIGH",
    "file": "java/path-traversal/Vulnerable.java",
    "line": 38,
    "end_line": 38,
    "message": "配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "crypto-hardcoded-key-java",
    "category": "unknown",
    "severity": "HIGH",
    "file": "java/sqli/Safe.java",
    "line": 30,
    "end_line": 30,
    "message": "Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-798",
      "owasp": "A07:2021"
    }
  },
  {
    "rule_id": "crypto-hardcoded-key-java",
    "category": "unknown",
    "severity": "HIGH",
    "file": "java/sqli/Safe.java",
    "line": 43,
    "end_line": 43,
    "message": "Java 代码中将密码、密钥等敏感信息硬编码在 String 变量中。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-798",
      "owasp": "A07:2021"
    }
  },
  {
    "rule_id": "sqli-java-statement-concat",
    "category": "security",
    "severity": "ERROR",
    "file": "java/sqli/Vulnerable.java",
    "line": 30,
    "end_line": 34,
    "message": "Statement 执行拼接 SQL，存在注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-89",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "sqli-java-string-concat",
    "category": "security",
    "severity": "ERROR",
    "file": "java/sqli/Vulnerable.java",
    "line": 33,
    "end_line": 33,
    "message": "字符串拼接构建 SQL 语句，存在 SQL 注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-89",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "sqli-java-statement-concat",
    "category": "security",
    "severity": "ERROR",
    "file": "java/sqli/Vulnerable.java",
    "line": 42,
    "end_line": 47,
    "message": "Statement 执行拼接 SQL，存在注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-89",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "sqli-java-string-concat",
    "category": "security",
    "severity": "ERROR",
    "file": "java/sqli/Vulnerable.java",
    "line": 45,
    "end_line": 45,
    "message": "字符串拼接构建 SQL 语句，存在 SQL 注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-89",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-java-servlet-output",
    "category": "security",
    "severity": "ERROR",
    "file": "java/xss/Vulnerable.java",
    "line": 28,
    "end_line": 30,
    "message": "Servlet 响应直接写入用户输入未做 HTML 转义，存在反射型 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-java-servlet-output",
    "category": "security",
    "severity": "ERROR",
    "file": "java/xss/Vulnerable.java",
    "line": 42,
    "end_line": 44,
    "message": "Servlet 响应直接写入用户输入未做 HTML 转义，存在反射型 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xxe-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/xxe/Safe.java",
    "line": 19,
    "end_line": 19,
    "message": "XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "xxe-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/xxe/Safe.java",
    "line": 31,
    "end_line": 31,
    "message": "XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "xxe-java-document-builder",
    "category": "security",
    "severity": "ERROR",
    "file": "java/xxe/Vulnerable.java",
    "line": 22,
    "end_line": 24,
    "message": "DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "xxe-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/xxe/Vulnerable.java",
    "line": 22,
    "end_line": 22,
    "message": "XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "xxe-java-document-builder",
    "category": "security",
    "severity": "ERROR",
    "file": "java/xxe/Vulnerable.java",
    "line": 29,
    "end_line": 31,
    "message": "DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "xxe-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "java/xxe/Vulnerable.java",
    "line": 29,
    "end_line": 29,
    "message": "XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "priv-python-subprocess-run",
    "category": "security",
    "severity": "ERROR",
    "file": "python/command-injection/safe.py",
    "line": 30,
    "end_line": 32,
    "message": "subprocess.run() 使用用户输入，存在命令注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-78"
    }
  },
  {
    "rule_id": "priv-python-subprocess-run",
    "category": "security",
    "severity": "ERROR",
    "file": "python/command-injection/vulnerable.py",
    "line": 22,
    "end_line": 46,
    "message": "subprocess.run() 使用用户输入，存在命令注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-78"
    }
  },
  {
    "rule_id": "priv-python-os-system",
    "category": "security",
    "severity": "ERROR",
    "file": "python/command-injection/vulnerable.py",
    "line": 30,
    "end_line": 30,
    "message": "os.system() 执行用户可控命令，存在命令注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-78"
    }
  },
  {
    "rule_id": "priv-python-subprocess-popen",
    "category": "security",
    "severity": "ERROR",
    "file": "python/command-injection/vulnerable.py",
    "line": 37,
    "end_line": 46,
    "message": "subprocess.Popen() 使用用户输入，存在命令注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-78"
    }
  },
  {
    "rule_id": "priv-python-check-output-shell-true",
    "category": "security",
    "severity": "ERROR",
    "file": "python/command-injection/vulnerable.py",
    "line": 46,
    "end_line": 46,
    "message": "subprocess.check_output() 使用 shell=True 执行命令，存在命令注入风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-78"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "python/path-traversal/safe.py",
    "line": 26,
    "end_line": 26,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "python/path-traversal/safe.py",
    "line": 39,
    "end_line": 39,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "python/path-traversal/safe.py",
    "line": 52,
    "end_line": 52,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-write-traversal",
    "category": "security",
    "severity": "CRITICAL",
    "file": "python/path-traversal/safe.py",
    "line": 52,
    "end_line": 52,
    "message": "文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "python/path-traversal/vulnerable.py",
    "line": 23,
    "end_line": 23,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "python/path-traversal/vulnerable.py",
    "line": 32,
    "end_line": 32,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-read-traversal",
    "category": "security",
    "severity": "ERROR",
    "file": "python/path-traversal/vulnerable.py",
    "line": 40,
    "end_line": 40,
    "message": "文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "path-write-traversal",
    "category": "security",
    "severity": "CRITICAL",
    "file": "python/path-traversal/vulnerable.py",
    "line": 40,
    "end_line": 40,
    "message": "文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-22",
      "owasp": "A01:2021"
    }
  },
  {
    "rule_id": "xxe-python-lxml-parser",
    "category": "security",
    "severity": "ERROR",
    "file": "python/xxe/vulnerable.py",
    "line": 14,
    "end_line": 22,
    "message": "lxml.etree.XMLParser() 使用默认配置，未禁用外部实体解析（resolve_entities 默认为 True），存在 XXE 漏洞。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611"
    }
  },
  {
    "rule_id": "xxe-python-lxml",
    "category": "security",
    "severity": "WARNING",
    "file": "python/xxe/vulnerable.py",
    "line": 14,
    "end_line": 29,
    "message": "lxml.etree.parse() 默认可能解析外部实体，建议使用 defusedxml 替代。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611"
    }
  },
  {
    "rule_id": "xxe-python-lxml-parse",
    "category": "security",
    "severity": "ERROR",
    "file": "python/xxe/vulnerable.py",
    "line": 14,
    "end_line": 29,
    "message": "lxml.etree.parse() 未传入安全解析器，使用默认配置解析 XML 文件，存在 XXE 漏洞。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611"
    }
  },
  {
    "rule_id": "xxe-python-lxml-resolve-entities",
    "category": "security",
    "severity": "ERROR",
    "file": "python/xxe/vulnerable.py",
    "line": 14,
    "end_line": 37,
    "message": "显式设置 resolve_entities=True，主动启用了外部实体解析，存在 XXE 漏洞。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611"
    }
  },
  {
    "rule_id": "xxe-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "python/xxe/vulnerable.py",
    "line": 28,
    "end_line": 28,
    "message": "XML 解析器未禁用外部实体，攻击者可读取服务器文件或发起 SSRF。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-611",
      "owasp": "A05:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 28,
    "end_line": 28,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 28,
    "end_line": 28,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 40,
    "end_line": 40,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 40,
    "end_line": 40,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/safe.ts",
    "line": 40,
    "end_line": 40,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/safe.ts",
    "line": 40,
    "end_line": 40,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 64,
    "end_line": 64,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 64,
    "end_line": 64,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 82,
    "end_line": 82,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/safe.ts",
    "line": 82,
    "end_line": 82,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/safe.ts",
    "line": 82,
    "end_line": 82,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/safe.ts",
    "line": 82,
    "end_line": 82,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 22,
    "end_line": 22,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 22,
    "end_line": 22,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 22,
    "end_line": 22,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 22,
    "end_line": 22,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-http-get",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 31,
    "end_line": 36,
    "message": "http.get() 请求用户可控 URL，存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-http-get",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 31,
    "end_line": 36,
    "message": "http.get() 请求用户可控 URL，存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 44,
    "end_line": 47,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 44,
    "end_line": 47,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch-weak-filter",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 56,
    "end_line": 59,
    "message": "fetch 请求仅做简单字符串检查（如 includes(\"localhost\")），可被 127.0.0.1、0.0.0.0 等绕过，存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch-weak-filter",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 56,
    "end_line": 59,
    "message": "fetch 请求仅做简单字符串检查（如 includes(\"localhost\")），可被 127.0.0.1、0.0.0.0 等绕过，存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 59,
    "end_line": 59,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-deep-detection",
    "category": "security",
    "severity": "CRITICAL",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 59,
    "end_line": 59,
    "message": "服务端发起 HTTP 请求时使用用户可控的 URL，攻击者可访问内网资源或云元数据。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918",
      "owasp": "A10:2021"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 59,
    "end_line": 59,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "ssrf-js-fetch",
    "category": "security",
    "severity": "WARNING",
    "file": "typescript/ssrf/vulnerable.ts",
    "line": 59,
    "end_line": 59,
    "message": "fetch 请求用户可控 URL（服务端），存在 SSRF 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-918"
    }
  },
  {
    "rule_id": "xss-js-innerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/safe.ts",
    "line": 68,
    "end_line": 68,
    "message": "innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-innerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/safe.ts",
    "line": 68,
    "end_line": 68,
    "message": "innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-innerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 21,
    "end_line": 21,
    "message": "innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-innerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 21,
    "end_line": 21,
    "message": "innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-document-write",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 30,
    "end_line": 30,
    "message": "document.write() 直接写入用户输入，存在 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-document-write",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 30,
    "end_line": 30,
    "message": "document.write() 直接写入用户输入，存在 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-outerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 40,
    "end_line": 40,
    "message": "outerHTML 直接赋值用户输入，存在 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-outerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 40,
    "end_line": 40,
    "message": "outerHTML 直接赋值用户输入，存在 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-dangerouslysetinnerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 50,
    "end_line": 50,
    "message": "dangerouslySetInnerHTML 使用用户输入，存在 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  },
  {
    "rule_id": "xss-js-dangerouslysetinnerhtml",
    "category": "security",
    "severity": "ERROR",
    "file": "typescript/xss/vulnerable.ts",
    "line": 50,
    "end_line": 50,
    "message": "dangerouslySetInnerHTML 使用用户输入，存在 XSS 风险。",
    "code_snippet": "requires login",
    "metadata": {
      "cwe": "CWE-79",
      "owasp": "A03:2021"
    }
  }
]

## 变更文件
["python/xxe/safe.py", "python/xxe/vulnerable.py", "python/path-traversal/safe.py", "python/path-traversal/vulnerable.py", "python/command-injection/safe.py", "python/command-injection/vulnerable.py", "typescript/ssrf/vulnerable.ts", "typescript/ssrf/safe.ts", "typescript/xss/vulnerable.ts", "typescript/xss/safe.ts"]

## 历史反馈统计
基于过去的评审数据：
- 总反馈数: 4
- 确认（真实问题）: 2
- 误报: 2
- 不确定: 0
- 历史准确率: 50.0%

请参考历史反馈模式，提高评审准确性。

### 近期反馈示例
- 规则 `unknown`: 用户确认（真实问题）（AI 判断正确，确实是误报）
- 规则 `unknown`: 用户标记为误报（AI 判断错误，这是误报）
- 规则 `unknown`: 用户标记为误报（AI 判断正确，确实是误报）
- 规则 `unknown`: 用户确认（真实问题）（确认是真实问题）

## 评审要求
1. 分析每个问题的真实性（排除误报）
2. 评估问题的严重程度（0-1 之间的置信度）
3. 为真实问题生成具体的修复建议
4. 使用严谨的评审标准（温度 0.1）
5. 为每个判断提供决策理由和证据

## 输出格式
请以 JSON 数组格式返回评审结果，每个元素包含：
- "rule_id": 规则 ID（必须与输入一致）
- "is_valid": true/false（是否为真实问题）
- "confidence": 0.0-1.0（置信度）
- "enhanced_fix": 修复建议（包含具体代码）
- "analysis": 分析说明（包含决策理由）
- "evidence": 证据列表（引用具体代码行或上下文）

只返回 JSON 数组，不要其他内容。
