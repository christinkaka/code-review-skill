# 扫描报告

## 扫描概况

- **扫描时间**：2026-07-28 16:24:48
- **扫描引擎**：双引擎（内置正则 + Semgrep v1.171.0）
- **扫描文件数**：18
- **检出问题数**：48
- **扫描耗时**：1.80 秒
- **规约 Profile**：default（83 条规则已加载，2 个规约文件缺失）
- **规约文件缺失**：`design/api-design.md`、`design/database.md`

### 引擎统计

| 指标 | 数量 |
|------|------|
| 内置引擎检出 | 10 |
| Semgrep 引擎检出 | 43 |
| 两个引擎都检出 | 3 |
| 仅内置引擎检出 | 5 |
| 仅 Semgrep 检出 | 40 |

> **注意**：原始 `dual_engine.py` 存在路径 bug（`cwd` 和扫描根路径重复导致 Semgrep 报 "Invalid scanning root" 错误），本次扫描通过修正路径后执行。Semgrep 引擎报告 25 条规则解析错误（主要因元变量格式不兼容，如 `$org`、`$name` 等）。

## 检出问题详情

| # | 文件 | 行号 | 规则 ID | 严重等级 | 检出引擎 | 描述 |
|---|------|------|---------|----------|----------|------|
| 1 | java/path-traversal/Safe.java | 24 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 2 | java/path-traversal/Safe.java | 25 | path-write-traversal | CRITICAL | semgrep | 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件 |
| 3 | java/path-traversal/Safe.java | 32 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 4 | java/path-traversal/Safe.java | 47 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 5 | java/path-traversal/Vulnerable.java | 11 | path-traversal-pattern | WARNING | builtin | 检测代码中是否包含路径穿越模式（`../`、`..\\`、`%2e%2e%2f` 等） |
| 6 | java/path-traversal/Vulnerable.java | 26 | path-traversal-pattern | WARNING | builtin | 检测代码中是否包含路径穿越模式 |
| 7 | java/path-traversal/Vulnerable.java | 27 | path-write-traversal | CRITICAL | semgrep | 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件 |
| 8 | java/path-traversal/Vulnerable.java | 28 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 9 | java/path-traversal/Vulnerable.java | 35 | path-traversal-pattern | WARNING | builtin | 检测代码中是否包含路径穿越模式 |
| 10 | java/path-traversal/Vulnerable.java | 36 | path-traversal-pattern | WARNING | 双引擎 | 检测代码中是否包含路径穿越模式 |
| 11 | java/path-traversal/Vulnerable.java | 37 | path-write-traversal | CRITICAL | semgrep | 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件 |
| 12 | java/path-traversal/Vulnerable.java | 38 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 13 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder | ERROR | semgrep | XML 解析器未禁用外部实体，攻击者可通过构造恶意 XML 读取服务器文件或发起 SSRF 攻击 |
| 14 | java/xxe/Vulnerable.java | 22 | xxe-java-document-builder-usage | ERROR | semgrep | DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体 |
| 15 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder | ERROR | semgrep | XML 解析器未禁用外部实体，攻击者可通过构造恶意 XML 读取服务器文件或发起 SSRF 攻击 |
| 16 | java/xxe/Vulnerable.java | 29 | xxe-java-document-builder-usage | ERROR | semgrep | DocumentBuilder 解析 XML 输入，但 DocumentBuilderFactory 未禁用外部实体 |
| 17 | python/command-injection/safe.py | 18 | priv-python-subprocess-run | ERROR | semgrep | subprocess.run() 使用用户输入，存在命令注入风险 |
| 18 | python/command-injection/safe.py | 30 | priv-python-subprocess-run | ERROR | semgrep | subprocess.run() 使用用户输入，存在命令注入风险 |
| 19 | python/command-injection/safe.py | 42 | priv-python-subprocess-run | ERROR | semgrep | subprocess.run() 使用用户输入，存在命令注入风险 |
| 20 | python/command-injection/safe.py | 53 | priv-python-subprocess-popen | ERROR | semgrep | subprocess.Popen() 使用用户输入，存在命令注入风险 |
| 21 | python/command-injection/vulnerable.py | 22 | priv-python-subprocess-run | ERROR | semgrep | subprocess.run() 使用用户输入，存在命令注入风险 |
| 22 | python/command-injection/vulnerable.py | 30 | priv-python-os-system | ERROR | 双引擎 | os.system() 执行用户可控命令，存在命令注入风险 |
| 23 | python/command-injection/vulnerable.py | 37 | priv-python-subprocess-popen | ERROR | semgrep | subprocess.Popen() 使用用户输入，存在命令注入风险 |
| 24 | python/path-traversal/safe.py | 26 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 25 | python/path-traversal/safe.py | 26 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 26 | python/path-traversal/safe.py | 39 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 27 | python/path-traversal/safe.py | 39 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 28 | python/path-traversal/safe.py | 52 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 29 | python/path-traversal/safe.py | 52 | path-write-traversal | CRITICAL | semgrep | 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件 |
| 30 | python/path-traversal/vulnerable.py | 6 | path-traversal-pattern | WARNING | builtin | 检测代码中是否包含路径穿越模式 |
| 31 | python/path-traversal/vulnerable.py | 23 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 32 | python/path-traversal/vulnerable.py | 23 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 33 | python/path-traversal/vulnerable.py | 29 | path-traversal-pattern | WARNING | builtin | 检测代码中是否包含路径穿越模式 |
| 34 | python/path-traversal/vulnerable.py | 30 | path-traversal-pattern | WARNING | 双引擎 | 检测代码中是否包含路径穿越模式 |
| 35 | python/path-traversal/vulnerable.py | 32 | path-config-traversal | HIGH | semgrep | 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件 |
| 36 | python/path-traversal/vulnerable.py | 32 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 37 | python/path-traversal/vulnerable.py | 40 | path-read-traversal | ERROR | semgrep | 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件 |
| 38 | python/path-traversal/vulnerable.py | 40 | path-write-traversal | CRITICAL | semgrep | 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件 |
| 39 | python/xxe/vulnerable.py | 14 | xxe-python-lxml | WARNING | semgrep | lxml.etree.parse() 默认可能解析外部实体，建议使用 defusedxml 替代 |
| 40 | typescript/ssrf/safe.ts | 40 | ssrf-js-fetch | WARNING | semgrep | fetch 请求用户可控 URL（服务端），存在 SSRF 风险 |
| 41 | typescript/ssrf/safe.ts | 82 | ssrf-js-fetch | WARNING | semgrep | fetch 请求用户可控 URL（服务端），存在 SSRF 风险 |
| 42 | typescript/ssrf/vulnerable.ts | 22 | ssrf-js-fetch | WARNING | semgrep | fetch 请求用户可控 URL（服务端），存在 SSRF 风险 |
| 43 | typescript/ssrf/vulnerable.ts | 44 | ssrf-js-fetch | WARNING | semgrep | fetch 请求用户可控 URL（服务端），存在 SSRF 风险 |
| 44 | typescript/ssrf/vulnerable.ts | 59 | ssrf-js-fetch | WARNING | semgrep | fetch 请求用户可控 URL（服务端），存在 SSRF 风险 |
| 45 | typescript/xss/safe.ts | 20 | xss-js-innerhtml | ERROR | semgrep | innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险 |
| 46 | typescript/xss/safe.ts | 68 | xss-js-innerhtml | ERROR | semgrep | innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险 |
| 47 | typescript/xss/vulnerable.ts | 21 | xss-js-innerhtml | ERROR | semgrep | innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险 |
| 48 | typescript/xss/vulnerable.ts | 30 | xss-js-document-write | ERROR | semgrep | document.write() 直接写入用户输入，存在 XSS 风险 |

## 按规则统计

| 规则 ID | 检出数 | 严重等级 | 类别 |
|---------|--------|----------|------|
| path-read-traversal | 8 | ERROR | security |
| path-config-traversal | 8 | HIGH | security |
| path-traversal-pattern | 7 | WARNING | security |
| path-write-traversal | 5 | CRITICAL | security |
| ssrf-js-fetch | 5 | WARNING | security |
| priv-python-subprocess-run | 4 | ERROR | security |
| xxe-java-document-builder | 2 | ERROR | security |
| xxe-java-document-builder-usage | 2 | ERROR | security |
| priv-python-subprocess-popen | 2 | ERROR | security |
| xss-js-innerhtml | 3 | ERROR | security |
| priv-python-os-system | 1 | ERROR | security |
| xxe-python-lxml | 1 | WARNING | security |
| xss-js-document-write | 1 | ERROR | security |
| **合计** | **48** | | |

## 按文件统计

| 文件 | 检出数 | 涉及规则 |
|------|--------|----------|
| python/path-traversal/vulnerable.py | 9 | path-traversal-pattern, path-config-traversal, path-read-traversal, path-write-traversal |
| java/path-traversal/Vulnerable.java | 8 | path-traversal-pattern, path-write-traversal, path-config-traversal |
| python/path-traversal/safe.py | 6 | path-config-traversal, path-read-traversal, path-write-traversal |
| java/path-traversal/Safe.java | 4 | path-read-traversal, path-write-traversal, path-config-traversal |
| java/xxe/Vulnerable.java | 4 | xxe-java-document-builder, xxe-java-document-builder-usage |
| python/command-injection/safe.py | 4 | priv-python-subprocess-run, priv-python-subprocess-popen |
| typescript/ssrf/vulnerable.ts | 3 | ssrf-js-fetch |
| python/command-injection/vulnerable.py | 3 | priv-python-subprocess-run, priv-python-os-system, priv-python-subprocess-popen |
| typescript/ssrf/safe.ts | 2 | ssrf-js-fetch |
| typescript/xss/safe.ts | 2 | xss-js-innerhtml |
| typescript/xss/vulnerable.ts | 2 | xss-js-innerhtml, xss-js-document-write |
| python/xxe/vulnerable.py | 1 | xxe-python-lxml |
| **合计** | **48** | |

## 按严重等级统计

| 严重等级 | 检出数 | 占比 |
|----------|--------|------|
| CRITICAL | 5 | 10.4% |
| ERROR | 23 | 47.9% |
| HIGH | 12 | 25.0% |
| WARNING | 8 | 16.7% |
| **合计** | **48** | 100% |

## 按语言统计

| 语言 | 文件数 | 检出数 |
|------|--------|--------|
| Java | 4 | 16 |
| Python | 6 | 23 |
| TypeScript | 4 | 9 |

## 可能的误报分析

以下检出可能为误报，需要人工确认：

1. **Safe.java / Safe.java / safe.ts / safe.py 中的检出**：Safe 文件中的检出（共 18 个）可能是误报，因为这些文件中的代码可能已包含安全防护措施（如路径校验、HTML 转义等），但规则的模式匹配未能识别这些防护措施。具体包括：
   - `java/path-traversal/Safe.java`：4 个检出 -- 路径穿越规则在 Safe 代码中触发，可能因 Safe 代码中仍保留了 `request.getParameter` 等模式
   - `python/command-injection/safe.py`：4 个检出 -- subprocess 调用虽然使用了 `shell=False` 或列表参数，但规则仅匹配函数调用模式
   - `python/path-traversal/safe.py`：6 个检出 -- 路径操作虽包含 `os.path.basename` 等安全过滤，但规则匹配了更上层的代码模式
   - `typescript/ssrf/safe.ts`：2 个检出 -- fetch 调用虽包含 URL 校验逻辑，但规则匹配了 fetch 调用本身
   - `typescript/xss/safe.ts`：2 个检出 -- innerHTML 赋值虽在安全上下文中，但规则直接匹配赋值模式

2. **path-traversal-pattern 在注释中匹配**：部分 `path-traversal-pattern` 规则的检出匹配到了代码注释中的 `../` 字符串（如 `java/path-traversal/Vulnerable.java` 第 11 行、`python/path-traversal/vulnerable.py` 第 6 行），属于误报。

## Semgrep 规则解析错误

Semgrep 报告 25 条规则解析错误，主要原因：
- 元变量格式不兼容：如 `$org`、`$name`、`$param`、`$item` 等不符合 Semgrep 的元变量命名规范
- 模式语法错误：如 `@RestController` 注解模式无法被 Java 解析器识别
- 受影响的规则类别：架构规约（arch-*）、API 设计规约（api-*）、数据库规约（db-*）、命名规约（naming-*）等

这些规则仅能通过内置正则引擎执行，Semgrep 引擎无法处理。
