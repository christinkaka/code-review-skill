# 安全防护模式识别修复报告

## 修复概述

为现有安全规则增加安全防护模式识别，消除安全文件的误报。通过系统性测试发现 Semgrep `pattern-not` 的匹配限制后，采用 `metavariable-regex` + `pattern-not` 组合方案实现有效的安全防护识别。

## 技术方案说明

### Semgrep pattern-not 匹配机制

经过系统性测试验证，Semgrep 的 `pattern-not` 仅在以下条件同时满足时才能抑制检出：

1. `pattern-not` 匹配的代码 AST 节点与主 `pattern` 匹配的节点**完全相同**
2. `pattern-not` 中的所有元变量均已绑定，且绑定值与实际代码一致

**不工作的场景**：
- 安全防护代码在不同的 AST 节点（如单独一行 `file.getCanonicalPath()`）
- 元变量未在主 pattern 中绑定（如 `$FILE.getCanonicalPath()` 中的 `$FILE`）
- `pattern-not-inside` 对顺序语句（非嵌套结构）无效

**工作的场景**：
- `pattern-not` 匹配同一表达式的不同形式（如 `subprocess.run([$ARG, ...], ...)` 排除列表参数）
- `pattern-not` 使用已绑定元变量（如 `subprocess.run($CMD, shell=False, ...)` 中 `$CMD` 已绑定）

### 最终方案

| 技术 | 适用场景 | 示例 |
|------|----------|------|
| `metavariable-regex` (负向前瞻) | 检查元变量是否包含安全防护函数调用 | `(?!.*DOMPurify\.sanitize).*` |
| `pattern-not` (同节点匹配) | 排除同一表达式的不同形式 | `subprocess.run([$ARG, ...], ...)` |
| `pattern-not` (已绑定元变量) | 排除同一命令的特定参数形式 | `subprocess.run($CMD, shell=False, ...)` |

## 修复的规则列表

### 1. path-traversal.yaml (4 条规则)

| 规则 ID | 语言 | 新增防护识别 | 技术 |
|---------|------|-------------|------|
| `path-java-file-input` | Java | `getCanonicalPath()`, `getCanonicalFile()`, `.normalize()` | metavariable-regex |
| `path-traversal-java-file` | Java | `getCanonicalPath()`, `getCanonicalFile()`, `.normalize()` | metavariable-regex |
| `path-python-open` | Python | `os.path.realpath()`, `os.path.abspath()`, `.resolve()` | metavariable-regex |
| `path-traversal-python-os-path-join` | Python | `os.path.realpath()`, `.resolve()` | metavariable-regex |

### 2. privilege-escalation.yaml (2 条规则)

| 规则 ID | 语言 | 新增防护识别 | 技术 |
|---------|------|-------------|------|
| `priv-python-subprocess-run` | Python | 列表参数形式, `shell=False`, `shlex.quote()` | pattern-not + metavariable-regex |
| `priv-python-subprocess-popen` | Python | 列表参数形式, `shlex.quote()` | pattern-not + metavariable-regex |

### 3. ssrf.yaml (1 条规则)

| 规则 ID | 语言 | 新增防护识别 | 技术 |
|---------|------|-------------|------|
| `ssrf-js-fetch` | JS/TS | `localhost` 检查, `127.0.0.1` 检查, `allowedDomains` 白名单 | metavariable-regex |

### 4. xss.yaml (1 条规则)

| 规则 ID | 语言 | 新增防护识别 | 技术 |
|---------|------|-------------|------|
| `xss-js-innerhtml` | JS/TS | `DOMPurify.sanitize()`, `encodeHtml()` | metavariable-regex |

## 新增安全防护模式汇总

### Java 路径穿越防护 (3 个模式)
```
(?!.*getCanonicalPath)(?!.*getCanonicalFile)(?!.*\.normalize\(\)).*
```
- `getCanonicalPath()` - 获取规范路径
- `getCanonicalFile()` - 获取规范文件
- `.normalize()` - 路径规范化

### Python 路径穿越防护 (3 个模式)
```
(?!.*os\.path\.realpath)(?!.*os\.path\.abspath)(?!.*\.resolve\(\)).*
```
- `os.path.realpath()` - 解析真实路径
- `os.path.abspath()` - 解析绝对路径
- `pathlib.Path().resolve()` - 路径解析

### Python 命令注入防护 (3 个模式)
```
pattern-not: subprocess.run([$ARG, ...], ...)     # 列表参数
pattern-not: subprocess.run($CMD, shell=False, ...) # 显式禁用 shell
metavariable-regex: (?!.*shlex\.quote).*           # shlex 转义
```

### JavaScript/TypeScript SSRF 防护 (3 个模式)
```
(?!.*localhost)(?!.*127\.0\.0\.1)(?!.*allowedDomains).*
```
- `localhost` 检查
- `127.0.0.1` 检查
- `allowedDomains` 域名白名单

### JavaScript/TypeScript XSS 防护 (2 个模式)
```
(?!.*DOMPurify\.sanitize)(?!.*encodeHtml).*
```
- `DOMPurify.sanitize()` - HTML 净化
- `encodeHtml()` - HTML 编码

## 验证结果

### 规则语法验证

| 规则文件 | 规则数 | 验证结果 |
|---------|--------|---------|
| path-traversal.yaml | 11 | PASS |
| privilege-escalation.yaml | 12 | PASS |
| ssrf.yaml | 8 | PASS |
| xss.yaml | 9 | PASS |
| 其他 7 个安全规则文件 | 34 | PASS |
| **总计** | **74** | **全部通过** |

**规则解析成功率：11/11 (100%)**

### 误报消除效果

| 测试场景 | 修复前误报数 | 修复后误报数 | 消除数 |
|---------|-------------|-------------|--------|
| Python 命令注入 (safe.py) | 5 | 2 | 3 |
| TypeScript XSS (safe.ts) | 2 | 1 | 1 |
| Java 路径穿越 (Safe.java) | 2 | 2 | 0 |
| Python 路径穿越 (safe.py) | 4 | 4 | 0 |
| TypeScript SSRF (safe.ts) | 2 | 2 | 0 |
| **总计** | **15** | **11** | **4** |

### 漏报检查

| 测试场景 | 漏洞检出数 | 状态 |
|---------|-----------|------|
| Java 路径穿越 (Vulnerable.java) | 3 | 全部检出 |
| Python 路径穿越 (vulnerable.py) | 7 | 全部检出 |
| Python 命令注入 (vulnerable.py) | 6 | 全部检出 |
| TypeScript SSRF (vulnerable.ts) | 4 | 全部检出 |
| TypeScript XSS (vulnerable.ts) | 3 | 全部检出 |

**漏洞检出率：无漏报，所有已知漏洞代码均被正确检出。**

## 已知限制

1. **跨行安全防护检测**：`metavariable-regex` 仅检查被捕获元变量的文本内容。当安全防护代码在单独一行（如 `filepath = os.path.realpath(user_input)` 后接 `open(filepath, "r")`），由于 `open()` 的参数是 `filepath` 而非 `os.path.realpath(...)`，正则无法匹配。此类场景需要数据流分析（taint tracking）才能完整覆盖。

2. **SSRF 白名单检测**：当前正则检查 URL 变量文本中是否包含 `localhost`、`127.0.0.1`、`allowedDomains` 等关键词。对于通过独立函数进行 URL 校验的场景（如 `if (!ALLOWED_HOSTS.has(url))`），无法自动识别。

3. **正则表达式精度**：负向前瞻正则 `(?!.*pattern).*` 基于文本匹配，可能产生边界情况。例如，变量名恰好包含 `realpath` 字符串但实际未调用该函数的情况。

## 修改的文件

- `/code-review-skill/references/security/path-traversal.yaml`
- `/code-review-skill/references/security/privilege-escalation.yaml`
- `/code-review-skill/references/security/ssrf.yaml`
- `/code-review-skill/references/security/xss.yaml`
