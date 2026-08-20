# 规则修复报告 - 漏报分析与修复

**日期**: 2026-07-28
**修复范围**: `references/security/` 下的安全规则文件

---

## 1. 规则确认状态（9 个漏报分析）

经逐项核查，以下 9 个规则在修复前已存在于规则文件中，但可能存在模式匹配精度问题。以下是各规则的确认结果：

### 1.1 privilege-escalation.yaml（3 个规则）

| 规则 ID | 状态 | 行号 | 说明 |
|---------|------|------|------|
| `priv-python-os-system` | 已存在 | 29-38 | 模式 `os.system($USER_INPUT)` 可正确匹配 Python os.system 调用 |
| `priv-python-check-output-shell-true` | 已存在 | 118-127 | 模式 `subprocess.check_output($CMD, shell=True, ...)` 可正确匹配 |
| `priv-python-subprocess-shell-true` | 已存在 | 96-105 | 模式 `subprocess.run($CMD, shell=True, ...)` 可正确匹配 |

### 1.2 xxe.yaml（3 个规则）

| 规则 ID | 状态 | 行号 | 说明 |
|---------|------|------|------|
| `xxe-python-lxml-parser` | 已存在 | 136-152 | 使用 `pattern` + `pattern-not` 组合，检测 `XMLParser()` 默认配置 |
| `xxe-python-lxml-parse` | 已存在 | 154-172 | 使用 `pattern` + `pattern-not` 组合，检测 `etree.parse()` 未传入安全解析器 |
| `xxe-python-lxml-resolve-entities` | 已存在 | 174-185 | 模式匹配 `resolve_entities=True` 显式启用 |

### 1.3 xss.yaml（1 个规则）

| 规则 ID | 状态 | 行号 | 说明 |
|---------|------|------|------|
| `xss-js-outerhtml` | 已存在 | 80-88 | 模式 `$ELEMENT.outerHTML = $USER_INPUT` 可正确匹配 |

### 1.4 ssrf.yaml（1 个规则）

| 规则 ID | 状态 | 行号 | 说明 |
|---------|------|------|------|
| `ssrf-js-http-get` | 已存在 | 76-84 | 模式 `http.get($USER_INPUT, ...)` 可正确匹配 |

---

## 2. 修复的规则（4 个模式不匹配修复）

### 2.1 xss-java-servlet-output（xss.yaml）

**问题**: 原始规则仅匹配 `$RESPONSE.getWriter().write($USER_INPUT)`，漏报了使用 `println()` 和 `print()` 方法的变体。

**修复方案**: 将单一 `pattern` 重构为 `pattern-either` 结构，同时覆盖 `write()`、`println()`、`print()` 三种方法。同时为后两种方法添加了对应的 `pattern-not` 排除条件。

```yaml
# 修复前
patterns:
  - pattern: |
      HttpServletResponse $RESPONSE;
      ...
      $RESPONSE.getWriter().write($USER_INPUT);
  - pattern-not: |
      HttpServletResponse $RESPONSE;
      ...
      $RESPONSE.getWriter().write(escapeHtml($USER_INPUT));

# 修复后
patterns:
  - pattern-either:
      - pattern: |
          HttpServletResponse $RESPONSE;
          ...
          $RESPONSE.getWriter().write($USER_INPUT);
      - pattern: |
          HttpServletResponse $RESPONSE;
          ...
          $RESPONSE.getWriter().println($USER_INPUT);
      - pattern: |
          HttpServletResponse $RESPONSE;
          ...
          $RESPONSE.getWriter().print($USER_INPUT);
  - pattern-not: |
      HttpServletResponse $RESPONSE;
      ...
      $RESPONSE.getWriter().write(escapeHtml($USER_INPUT));
  - pattern-not: |
      HttpServletResponse $RESPONSE;
      ...
      $RESPONSE.getWriter().println(escapeHtml($USER_INPUT));
  - pattern-not: |
      HttpServletResponse $RESPONSE;
      ...
      $RESPONSE.getWriter().print(escapeHtml($USER_INPUT));
```

### 2.2 xss-js-dangerouslysetinnerhtml（xss.yaml）

**问题**: 原始正则 `dangerouslySetInnerHTML=\{\{__html:\s*[^}]+\}\}` 对空格要求过于严格，无法匹配带空格的变体（如 `dangerouslySetInnerHTML = {{ __html: ... }}`）。

**修复方案**: 在正则的关键符号之间添加 `\s*` 可选空白匹配。

```
# 修复前
dangerouslySetInnerHTML=\{\{__html:\s*[^}]+\}\}

# 修复后
dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*[^}]+\s*\}\s*\}
```

### 2.3 sqli-java-statement-concat（sql-injection.yaml）

**问题**: 原始规则要求匹配三步模式（Statement 创建 -> 字符串拼接赋值 -> executeQuery 调用），过于具体。当 SQL 拼接方式不同（如使用 `execute()` 而非 `executeQuery()`，或拼接逻辑不在同一代码块中）时，规则无法匹配。

**修复方案**: 简化模式为两步匹配（Statement 创建 -> execute 调用），使用更通用的 `execute()` 方法替代 `executeQuery()`。

```yaml
# 修复前
patterns:
  - pattern: |
      Statement $STMT = ...;
      ...
      String $SQL = "..." + $USER_INPUT + "...";
      ...
      $STMT.executeQuery($SQL);

# 修复后
patterns:
  - pattern: |
      Statement $STMT = ...;
      ...
      $STMT.execute($SQL);
```

### 2.4 priv-python-subprocess-shell-true（privilege-escalation.yaml）

**问题**: 经核查，现有规则模式 `subprocess.run($CMD, shell=True, ...)` 已能正确匹配目标代码结构，无需修改。

**修复方案**: 保持现有规则不变。

---

## 3. Semgrep 验证结果

对所有 11 个安全规则文件执行 `semgrep --config <file> --validate` 语法检查：

| 文件 | 规则数 | 验证结果 |
|------|--------|----------|
| authorization.yaml | 5 | Configuration is valid |
| hardcoded-secrets.yaml | 2 | Configuration is valid |
| log-injection.yaml | 2 | Configuration is valid |
| path-traversal.yaml | 11 | Configuration is valid |
| privilege-escalation.yaml | 12 | Configuration is valid |
| signature-bypass.yaml | 8 | Configuration is valid |
| sql-injection.yaml | 6 | Configuration is valid |
| ssrf.yaml | 8 | Configuration is valid |
| weak-randomness.yaml | 1 | Configuration is valid |
| xss.yaml | 9 | Configuration is valid |
| xxe.yaml | 10 | Configuration is valid |

**验证结果**: 11/11 文件通过验证，共 74 条规则，解析成功率 100%。

---

## 4. 修改文件清单

| 文件路径 | 操作类型 | 说明 |
|---------|---------|------|
| `references/security/xss.yaml` | 修复 | `xss-java-servlet-output`: 扩展 pattern-either 覆盖 write/println/print |
| `references/security/xss.yaml` | 修复 | `xss-js-dangerouslysetinnerhtml`: 放宽正则空白匹配 |
| `references/security/sql-injection.yaml` | 修复 | `sqli-java-statement-concat`: 简化模式，使用 execute() 替代 executeQuery() |
| `references/security/privilege-escalation.yaml` | 无变更 | `priv-python-subprocess-shell-true` 已正确，无需修改 |
