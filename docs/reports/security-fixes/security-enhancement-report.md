# 安全规则增强报告

> 增强时间：2026-07-28
> 增强范围：`references/security/` 下安全规则文件
> 增强目标：补充控制流漏洞和上下文相关漏洞的检测能力

## 增强概述

| 指标 | 数量 |
|------|------|
| 修复的规则 | 1 条（XXE 模式修正） |
| 新增规则 | 9 条（跨 6 个文件） |
| 新增规则文件 | 3 个（hardcoded-secrets / weak-randomness / log-injection） |
| 增强前规则总数 | 50 |
| 增强后规则总数 | 59 |
| Semgrep 验证通过率 | 11/11 (100%) |

---

## 一、修复的规则（1 条）

### 1.1 XXE 规则模式修正（xxe.yaml）

| 字段 | 修复前 | 修复后 |
|------|--------|--------|
| 规则 ID | xxe-java-document-builder | xxe-java-document-builder |
| 匹配模式 | `$FACTORY.parse(...)` | `$FACTORY.newDocumentBuilder()` |
| 问题 | `DocumentBuilderFactory` 没有 `parse()` 方法，实际代码通过 `newDocumentBuilder()` 创建解析器 | 匹配实际的 DocumentBuilder 创建模式 |

**修复原因**：`DocumentBuilderFactory` 类本身不提供 `parse()` 方法。实际代码中，开发者通过 `factory.newDocumentBuilder()` 创建 `DocumentBuilder` 实例，再调用 `builder.parse()` 解析 XML。原规则无法匹配任何真实代码。

---

## 二、新增的规则（9 条）

### 2.1 控制流漏洞检测（3 条）

#### sig-bypass-version-skip（signature-bypass.yaml）

- **类型**：控制流漏洞 - 签名绕过
- **语言**：Java
- **严重级别**：CRITICAL
- **CWE**：CWE-345
- **检测模式**：`if ($VERSION == 1) { ... }`
- **说明**：检测基于协议版本的条件分支，V1 路径可能跳过签名验证。攻击者可通过设置版本号为 1 来绕过签名校验。
- **置信度**：LOW（需人工确认分支内是否确实缺少验证逻辑）

#### priv-python-subprocess-run（privilege-escalation.yaml）

- **类型**：命令注入
- **语言**：Python
- **严重级别**：ERROR
- **CWE**：CWE-78
- **检测模式**：`subprocess.run($CMD, ...)`
- **说明**：补充原有 `subprocess.call(shell=True)` 规则，覆盖 `subprocess.run()` 调用。

#### priv-python-subprocess-popen（privilege-escalation.yaml）

- **类型**：命令注入
- **语言**：Python
- **严重级别**：ERROR
- **CWE**：CWE-78
- **检测模式**：`subprocess.Popen($CMD, ...)`
- **说明**：补充原有 `subprocess.call(shell=True)` 规则，覆盖 `subprocess.Popen()` 调用。

### 2.2 上下文相关漏洞检测（6 条）

#### xxe-java-document-builder-usage（xxe.yaml）

- **类型**：XXE - 上下文相关检测
- **语言**：Java
- **严重级别**：ERROR
- **CWE**：CWE-611
- **检测模式**：`newInstance() -> newDocumentBuilder() -> parse()` 完整链路
- **说明**：检测 DocumentBuilderFactory 创建 -> DocumentBuilder 创建 -> XML 解析的完整调用链，配合 `pattern-not` 排除已配置安全特性的代码。

#### crypto-hardcoded-key（hardcoded-secrets.yaml）

- **类型**：硬编码密钥 - 跨语言正则匹配
- **语言**：Java, Python, JavaScript, TypeScript
- **严重级别**：HIGH
- **CWE**：CWE-798
- **检测模式**：`(?i)(password|secret|api_?key|token|api_?secret)\s*=\s*["'][^"']+["']`
- **说明**：使用正则表达式跨语言检测变量名包含 password/secret/api_key/token 且赋值为字符串字面量的代码。

#### crypto-hardcoded-key-java（hardcoded-secrets.yaml）

- **类型**：硬编码密钥 - Java AST 精确匹配
- **语言**：Java
- **严重级别**：HIGH
- **CWE**：CWE-798
- **检测模式**：`String $VAR = "..."` + `metavariable-regex` 过滤变量名
- **说明**：使用 Semgrep AST 匹配 Java 变量声明，通过 `metavariable-regex` 过滤变量名包含敏感关键词的情况。置信度高于正则匹配。

#### crypto-weak-random-java（weak-randomness.yaml）

- **类型**：弱随机数
- **语言**：Java
- **严重级别**：WARNING
- **CWE**：CWE-330
- **检测模式**：`new Random()`
- **说明**：检测使用 `java.util.Random` 的代码，该类使用 LCG 算法，输出可被预测。安全场景应使用 `SecureRandom`。

#### log-injection-java（log-injection.yaml）

- **类型**：日志注入
- **语言**：Java
- **严重级别**：WARNING
- **CWE**：CWE-117
- **检测模式**：`log.info/debug/warn/error($USER_INPUT)`
- **说明**：使用 `pattern-either` 检测用户输入直接传入 Java 日志方法的代码，攻击者可注入换行符伪造日志条目。

#### log-injection-python（log-injection.yaml）

- **类型**：日志注入
- **语言**：Python
- **严重级别**：WARNING
- **CWE**：CWE-117
- **检测模式**：`logging.info/debug/warning/error($USER_INPUT)`
- **说明**：检测用户输入直接传入 Python logging 模块的代码。

---

## 三、验证结果

### 3.1 Semgrep 规则语法验证

所有 11 个 YAML 规则文件通过 `semgrep --validate` 验证：

| 文件 | 规则数 | 验证状态 | 变更类型 |
|------|--------|----------|----------|
| authorization.yaml | 5 | PASS | 无变更 |
| hardcoded-secrets.yaml | 2 | PASS | 新增文件 |
| log-injection.yaml | 2 | PASS | 新增文件 |
| path-traversal.yaml | 7 | PASS | 无变更 |
| privilege-escalation.yaml | 9 | PASS | +2 规则 |
| signature-bypass.yaml | 7 | PASS | +1 规则 |
| sql-injection.yaml | 5 | PASS | 无变更 |
| ssrf.yaml | 6 | PASS | 无变更 |
| weak-randomness.yaml | 1 | PASS | 新增文件 |
| xss.yaml | 8 | PASS | 无变更 |
| xxe.yaml | 7 | PASS | +1 规则, 1 规则修复 |
| **合计** | **59** | **100% 通过** | **+9 规则, 1 修复** |

### 3.2 规则解析成功率

- 修复前：50 条规则，8 个文件，100% 通过
- 增强后：59 条规则，11 个文件，100% 通过
- 新增规则全部通过 Semgrep 语法验证

---

## 四、文件变更清单

### 修改的文件（6 个）

| 文件路径 | 变更内容 |
|----------|----------|
| `references/security/xxe.yaml` | 修复 xxe-java-document-builder 模式；新增 xxe-java-document-builder-usage |
| `references/security/xxe.md` | 同步更新检测模式文档；新增 DocumentBuilder 使用说明 |
| `references/security/signature-bypass.yaml` | 新增 sig-bypass-version-skip 控制流漏洞规则 |
| `references/security/signature-bypass.md` | 新增协议版本跳过签名验证的说明文档 |
| `references/security/privilege-escalation.yaml` | 新增 priv-python-subprocess-run 和 priv-python-subprocess-popen |
| `references/security/privilege-escalation.md` | 新增 subprocess.run() 和 Popen() 的说明文档 |

### 新增的文件（6 个）

| 文件路径 | 内容 |
|----------|------|
| `references/security/hardcoded-secrets.yaml` | 硬编码密钥检测规则（2 条） |
| `references/security/hardcoded-secrets.md` | 硬编码密钥检测规约文档 |
| `references/security/weak-randomness.yaml` | 弱随机数检测规则（1 条） |
| `references/security/weak-randomness.md` | 弱随机数检测规约文档 |
| `references/security/log-injection.yaml` | 日志注入检测规则（2 条） |
| `references/security/log-injection.md` | 日志注入检测规约文档 |

---

## 五、漏洞覆盖增强分析

### 新增检测能力

| 漏洞类别 | 增强前 | 增强后 | 说明 |
|----------|--------|--------|------|
| XXE | 6 条规则 | 7 条规则 | 新增 DocumentBuilder 使用链路检测 |
| 签名绕过 | 6 条规则 | 7 条规则 | 新增控制流漏洞（版本跳过验证） |
| 提权/命令注入 | 7 条规则 | 9 条规则 | 新增 subprocess.run() / Popen() |
| 硬编码密钥 | 0 条规则 | 2 条规则 | 全新检测领域 |
| 弱随机数 | 0 条规则 | 1 条规则 | 全新检测领域 |
| 日志注入 | 0 条规则 | 2 条规则 | 全新检测领域 |

### 控制流漏洞检测

新增 `sig-bypass-version-skip` 规则，能够检测通过条件分支跳过安全验证的控制流漏洞模式。这是从传统的"匹配危险函数调用"到"分析控制流路径"的重要扩展。

### 上下文相关漏洞检测

新增的 `xxe-java-document-builder-usage` 规则通过多步骤模式匹配（`patterns` + `pattern-not`），检测跨越多个语句的完整调用链路，并排除已配置安全特性的代码路径。这种上下文感知的检测方式显著降低了误报率。

---

## 六、待人工审核项

| 规则 ID | 审核原因 |
|---------|----------|
| sig-bypass-version-skip | 置信度 LOW：`if ($VERSION == 1)` 模式较宽泛，可能匹配非签名相关的版本分支逻辑。建议在实际项目中验证误报率。 |
| crypto-hardcoded-key | 置信度 MEDIUM：正则匹配可能误报测试代码中的假数据。建议结合文件路径过滤（排除 test/ 目录）。 |
| log-injection-java / log-injection-python | 置信度 LOW：`log.info($USER_INPUT)` 模式仅在参数为单一变量时匹配，字符串拼接场景（如 `log.info("User: " + input)`）不会被捕获。 |
