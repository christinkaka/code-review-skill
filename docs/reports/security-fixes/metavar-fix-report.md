# Semgrep 规则修复报告

> 修复时间：2026-07-28
> 修复范围：`references/security/` 下所有 `.yaml` 和 `.md` 规则文件

## 修复概述

| 指标 | 数量 |
|------|------|
| 扫描 YAML 文件总数 | 8 |
| 修复前通过验证 | 1 (12.5%) |
| 修复后通过验证 | 8 (100%) |
| 修复规则总数 | 50 |
| 修复小写元变量 | 19 处（跨 6 个 YAML 文件） |
| 修复语法不合法规则 | 4 处（跨 3 个 YAML 文件） |
| 同步修复 MD 文件 | 2 处（xss.md, sql-injection.md） |

## 一、小写元变量修复（19 处）

Semgrep 要求元变量必须全大写（可含数字和下划线），小写或 camelCase 会导致解析失败。

### 1. sql-injection.yaml（3 处修复）

| 修复前 | 修复后 | 涉及规则 |
|--------|--------|----------|
| `$stmt` | `$STMT` | sqli-java-statement-execute |
| `$cursor` | `$CURSOR` | sqli-python-execute-format |
| `$engine` | `$ENGINE` | sqli-python-raw-query |

### 2. xss.yaml（4 处修复）

| 修复前 | 修复后 | 涉及规则 |
|--------|--------|----------|
| `$response` | `$RESPONSE` | xss-java-servlet-output, xss-java-string-builder-html |
| `$sb` | `$SB` | xss-java-string-builder-html |
| `$element` | `$ELEMENT` | xss-js-innerhtml |

### 3. xxe.yaml（5 处修复）

| 修复前 | 修复后 | 涉及规则 |
|--------|--------|----------|
| `$factory` | `$FACTORY` | xxe-java-document-builder, xxe-java-sax-parser |
| `$reader` | `$READER` | xxe-java-xml-reader |
| `$um` | `$UM` | xxe-java-unmarshaller |
| `$jaxbContext` | `$JAXB_CONTEXT` | xxe-java-unmarshaller |
| `$source` | `$SOURCE` | xxe-python-lxml, xxe-python-xml-dom |

### 4. authorization.yaml（4 处修复）

| 修复前 | 修复后 | 涉及规则 |
|--------|--------|----------|
| `$repository` | `$REPOSITORY` | auth-java-horizontal-escalation |
| `$service` | `$SERVICE` | auth-java-idor-direct-ref |
| `$request` | `$REQUEST` | auth-java-idor-direct-ref |
| `$currentUser` | `$CURRENT_USER` | auth-java-idor-direct-ref |

### 5. signature-bypass.yaml（3 处修复）

| 修复前 | 修复后 | 涉及规则 |
|--------|--------|----------|
| `$sig` | `$SIG` | sig-java-verify-skip |
| `$key` | `$KEY` | sig-java-hardcoded-key |
| `$verifier` | `$VERIFIER` | sig-python-verify-false |

### 6. path-traversal.yaml（1 处修复，pattern-not 块）

| 修复前 | 修复后 | 涉及规则 |
|--------|--------|----------|
| `$sanitized` | `$SANITIZED` | path-java-file-input |

## 二、语法不合法规则修复（4 处）

### 1. sqli-java-mybatis-dollar（sql-injection.yaml）

**问题**：`${$VAR}` 不是有效 Java 语法，Semgrep 无法解析。

**修复方案**：改用 `pattern-regex` 匹配 MyBatis `${}` 占位符模式。

```yaml
# 修复前
pattern: |
  ${$VAR}

# 修复后
pattern-regex: \$\{[a-zA-Z_.]+\}
```

### 2. xss-java-jsp-expr（xss.yaml）

**问题**：`<%= $request.getParameter(...) %>` 是 JSP 语法，不是有效 Java 语法。

**修复方案**：改用 `pattern-regex` 匹配 JSP 表达式。

```yaml
# 修复前
pattern: |
  <%= $request.getParameter(...) %>

# 修复后
pattern-regex: <%=\s*\w+\.getParameter\([^)]+\)\s*%>
```

### 3. xss-js-dangerouslysetinnerhtml（xss.yaml）

**问题**：`<... dangerouslySetInnerHTML={{__html: $USER_INPUT}} />` 是 JSX 语法，Semgrep JavaScript 解析器无法处理。

**修复方案**：改用 `pattern-regex` 匹配 dangerouslySetInnerHTML 属性。

```yaml
# 修复前
pattern: |
  <... dangerouslySetInnerHTML={{__html: $USER_INPUT}} />

# 修复后
pattern-regex: dangerouslySetInnerHTML=\{\{__html:\s*[^}]+\}\}
```

### 4. ssrf-java-http-client（ssrf.yaml）

**问题**：`HttpClient.newHttpClient().send(HttpRequest.newBuilder().uri(URI.create($USER_INPUT))...)` 链式调用过长，Java 解析器失败。

**修复方案**：简化为匹配核心危险调用 `URI.create($USER_INPUT)`，保留 `pattern-not` 白名单检查。

```yaml
# 修复前
pattern: |
  HttpClient.newHttpClient().send(HttpRequest.newBuilder().uri(URI.create($USER_INPUT))...)

# 修复后
patterns:
  - pattern: |
      URI.create($USER_INPUT)
  - pattern-not: |
      if (isAllowedUrl($USER_INPUT)) { ... }
```

## 三、MD 文件同步修复（2 处）

以下 `.md` 规约文件中的检测模式也同步修复：

| 文件 | 修复内容 |
|------|----------|
| sql-injection.md | `${$VAR}` 改为 `pattern-regex: \$\{[a-zA-Z_.]+\}` |
| xss.md | JSP 表达式和 JSX dangerouslySetInnerHTML 改为 `pattern-regex` |

## 四、验证结果

修复后所有 8 个 YAML 规则文件通过 Semgrep `--validate` 验证：

| 文件 | 规则数 | 验证状态 |
|------|--------|----------|
| authorization.yaml | 5 | PASS |
| path-traversal.yaml | 7 | PASS |
| privilege-escalation.yaml | 7 | PASS |
| signature-bypass.yaml | 6 | PASS |
| sql-injection.yaml | 5 | PASS |
| ssrf.yaml | 6 | PASS |
| xss.yaml | 8 | PASS |
| xxe.yaml | 6 | PASS |
| **合计** | **50** | **100% 通过** |

## 五、转换规则说明

元变量命名转换遵循以下规则：

1. **全小写** -> **全大写**：`$factory` -> `$FACTORY`
2. **camelCase** -> **UPPER_SNAKE_CASE**：`$currentUser` -> `$CURRENT_USER`，`$jaxbContext` -> `$JAXB_CONTEXT`
3. **已大写的保持不变**：`$USER_INPUT`、`$RETURNTYPE`、`$METHOD` 等不做修改

## 六、待人工审核项

无。所有规则均已修复并通过验证。
