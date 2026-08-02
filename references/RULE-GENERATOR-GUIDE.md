# 规则生成指南

本文档指导如何将自然语言规则描述转换为 Semgrep 可执行的 pattern。

## 规则文件格式

每个规则文件是一个 Markdown 文件，包含以下部分：

```markdown
# 规则名称 - 简要描述

> 一句话描述问题

```yaml
id: <category>-<language>-<name>
languages: [<language>]
severity: ERROR
cwe: CWE-XXX
owasp: AXX:2021
```

## 违规示例

```<language>
// 违规代码
```

## 正确示例

```<language>
// 正确代码
```

## 检测模式

```pattern
<semgrep pattern>
```

```pattern-not
<exclusion pattern>
```
```

## Semgrep Pattern 语法

### 基本语法

- `$VAR`：匹配任意变量名
- `...`：匹配任意代码（包括空）
- `<... ...>`：匹配任意参数列表

### Pattern 类型

1. **pattern**：精确匹配代码模式
   ```pattern
   Statement $STMT = ...;
   ...
   $STMT.execute("..." + $VAR + "...");
   ```

2. **pattern-regex**：正则表达式匹配
   ```pattern-regex
   "(SELECT|INSERT|UPDATE|DELETE)[\s\S]*?"\s*\+\s*\w+
   ```

3. **pattern-not**：排除模式（减少误报）
   ```pattern-not
   $FACTORY.setFeature("...", true);
   ...
   $BUILDER.parse(...);
   ```

### 多语言支持

在 `## 检测模式` 下使用子标题区分语言：

```markdown
## 检测模式

### Java

```pattern
// Java pattern
```

### Python

```pattern
# Python pattern
```
```

## 规则命名规范

格式：`<category>-<language>-<name>`

示例：
- `sqli-java-string-concat`
- `xxe-python-lxml`
- `xss-js-innerhtml`
- `err-python-bare-except`

## 规则分类

### 安全规则（references/security/）

| 类别 | 文件 | CWE |
|------|------|-----|
| SQL 注入 | sql-injection.md | CWE-89 |
| XXE | xxe.md | CWE-611 |
| XSS | xss.md | CWE-79 |
| 路径穿越 | path-traversal.md | CWE-22 |
| 命令注入 | privilege-escalation.md | CWE-78 |
| SSRF | ssrf.md | CWE-918 |
| 硬编码密钥 | hardcoded-secrets.md | CWE-798 |
| 反序列化 | deserialization.md | CWE-502 |
| 日志注入 | log-injection.md | CWE-117 |
| 弱随机数 | weak-randomness.md | CWE-330 |
| 越权访问 | authorization.md | CWE-862 |
| 签名绕过 | signature-bypass.md | CWE-345 |

### 设计规则（references/design/）

| 类别 | 文件 |
|------|------|
| 架构合规 | architecture.md |
| API 设计 | api-design.md |
| 数据库设计 | database.md |

### 实现规则（references/implementation/）

| 类别 | 文件 |
|------|------|
| 命名规范 | naming.md |
| 异常处理 | error-handling.md |
| 并发安全 | concurrency.md |
| 空指针防护 | null-safety.md |

## 添加新规则的步骤

### Step 1: 确定规则信息

收集以下信息：
- 规则名称
- 问题描述
- 违规示例（至少 1 个）
- 正确示例（至少 1 个）
- 语言
- 严重程度
- CWE 编号（如果是安全问题）

### Step 2: 生成 Pattern

根据违规示例生成 Semgrep pattern：

1. 识别关键代码模式
2. 使用 `$VAR` 替换变量名
3. 使用 `...` 表示任意代码
4. 添加 `pattern-not` 排除误报

### Step 3: 编写 Markdown 规则文件

按照上述格式编写规则文件，保存到对应目录。

### Step 4: 触发预编译

```bash
python scripts/rule_compiler.py --compile
```

### Step 5: 测试规则

创建测试文件，运行扫描，验证规则是否正确检出。

## 示例：添加日志注入规则

### 需求

"检查日志中是否打印了密码"

### 规则信息

- 规则名称：日志注入 - 打印密码
- 问题描述：日志中打印密码可能导致密码泄露
- 违规示例：`logger.info(f"Password: {password}")`
- 正确示例：`logger.info("User logged in")`
- 语言：python
- 严重程度：ERROR
- CWE：CWE-532

### 生成的 Pattern

```pattern
logger.$METHOD(f"...password...")
```

### 保存位置

`references/security/log-injection.md`

### 触发预编译

```bash
python scripts/rule_compiler.py --compile
```

## 预编译机制

规则文件修改后，需要重新编译：

```bash
# 查看编译状态
python scripts/rule_compiler.py --status

# 编译所有规则
python scripts/rule_compiler.py --compile

# 强制重新编译
python scripts/rule_compiler.py --compile --force
```

编译后的规则保存在 `references/compiled/` 目录中。

## 注意事项

1. **Pattern 质量**：生成的 pattern 应该精确，避免误报
2. **规则命名**：使用统一的命名规范
3. **测试覆盖**：每个新规则都应该有测试案例
4. **文档完整**：规则文件应该包含完整的说明和示例
5. **预编译**：修改规则后必须重新编译
