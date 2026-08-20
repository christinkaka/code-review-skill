# 规则 ID 修复报告

## 修复时间
2026-07-28

## 1. 修复的规则 ID 列表（命名不一致修复）

以下规则 ID 在 `known-issues.json` 中从 `ts` 命名统一为 `js` 命名，与 YAML 规则文件保持一致：

| # | 修复前（known-issues.json） | 修复后（known-issues.json） | 对应 YAML 规则 ID | 规则文件 |
|---|---------------------------|---------------------------|------------------|---------|
| 1 | `xss-ts-innerhtml` | `xss-js-innerhtml` | `xss-js-innerhtml` | xss.yaml |
| 2 | `xss-ts-document-write` | `xss-js-document-write` | `xss-js-document-write` | xss.yaml |
| 3 | `xss-ts-outerhtml` | `xss-js-outerhtml` | `xss-js-outerhtml` | xss.yaml |
| 4 | `xss-ts-dangerously-set-innerhtml` | `xss-js-dangerouslysetinnerhtml` | `xss-js-dangerouslysetinnerhtml` | xss.yaml |
| 5 | `ssrf-ts-fetch-user-input` | `ssrf-js-fetch` | `ssrf-js-fetch` | ssrf.yaml |
| 6 | `ssrf-ts-http-get-user-input` | `ssrf-js-http-get` | `ssrf-js-http-get` | ssrf.yaml |
| 7 | `ssrf-ts-fetch-weak-filter` | `ssrf-js-fetch-weak-filter` | `ssrf-js-fetch-weak-filter` | ssrf.yaml |

**命名规范**：JavaScript/TypeScript 统一使用 `js` 前缀（而非 `ts`），因为规则同时覆盖 `languages: [javascript, typescript]`。

另外修正了 `known-issues.json` 中 `total_issues` 字段：28 -> 26（与实际条目数一致）。

## 2. 新增的规则列表

### 2.1 xss.yaml - 新增 1 条规则

| 规则 ID | 语言 | 说明 |
|---------|------|------|
| `xss-js-outerhtml` | javascript, typescript | 检测 `outerHTML` 直接赋值用户输入的 XSS 风险 |

### 2.2 sql-injection.yaml - 新增 1 条规则

| 规则 ID | 语言 | 说明 |
|---------|------|------|
| `sqli-java-statement-concat` | java | 检测字符串拼接构建 SQL 并通过 Statement.executeQuery() 执行的注入风险 |

### 2.3 path-traversal.yaml - 新增 4 条规则

| 规则 ID | 语言 | 说明 |
|---------|------|------|
| `path-traversal-java-file` | java | 检测 `new File(baseDir, userInput)` 未校验路径穿越 |
| `path-traversal-java-weak-filter` | java | 检测仅使用 `replace("../", "")` 的不完整过滤 |
| `path-traversal-python-os-path-join` | python | 检测 `os.path.join(BASE_DIR, userInput)` 未校验路径穿越 |
| `path-traversal-python-weak-filter` | python | 检测仅使用 `replace('../', '')` 的不完整过滤 |

### 2.4 xxe.yaml - 新增 3 条规则

| 规则 ID | 语言 | 说明 |
|---------|------|------|
| `xxe-python-lxml-parser` | python | 检测 `etree.XMLParser()` 使用默认配置未禁用外部实体 |
| `xxe-python-lxml-parse` | python | 检测 `etree.parse()` 未传入安全解析器 |
| `xxe-python-lxml-resolve-entities` | python | 检测显式设置 `resolve_entities=True` 启用外部实体 |

### 2.5 privilege-escalation.yaml - 新增 3 条规则

| 规则 ID | 语言 | 说明 |
|---------|------|------|
| `priv-python-subprocess-shell-true` | python | 检测 `subprocess.run(cmd, shell=True, ...)` 命令注入 |
| `priv-python-popen-shell-true` | python | 检测 `subprocess.Popen(cmd, shell=True, ...)` 命令注入 |
| `priv-python-check-output-shell-true` | python | 检测 `subprocess.check_output(cmd, shell=True, ...)` 命令注入 |

### 2.6 ssrf.yaml - 新增 2 条规则

| 规则 ID | 语言 | 说明 |
|---------|------|------|
| `ssrf-js-http-get` | javascript, typescript | 检测 `http.get(userInput, ...)` SSRF 风险 |
| `ssrf-js-fetch-weak-filter` | javascript, typescript | 检测仅使用 `includes("localhost")` 的不完整 SSRF 过滤 |

**新增规则总计：14 条**

## 3. 验证结果

### 3.1 Semgrep 语法验证

| 规则文件 | 规则数 | 错误数 | 状态 |
|---------|--------|--------|------|
| authorization.yaml | 5 | 0 | PASS |
| hardcoded-secrets.yaml | 2 | 0 | PASS |
| log-injection.yaml | 2 | 0 | PASS |
| path-traversal.yaml | 11 | 0 | PASS |
| privilege-escalation.yaml | 12 | 0 | PASS |
| signature-bypass.yaml | 8 | 0 | PASS |
| sql-injection.yaml | 6 | 0 | PASS |
| ssrf.yaml | 8 | 0 | PASS |
| weak-randomness.yaml | 1 | 0 | PASS |
| xss.yaml | 9 | 0 | PASS |
| xxe.yaml | 10 | 0 | PASS |
| **合计** | **74** | **0** | **全部通过** |

**规则解析成功率：100%（74/74）**

### 3.2 规则 ID 一致性验证

known-issues.json 中共 21 个唯一规则 ID，全部在 YAML 规则文件中存在对应规则：

- 21/21 规则 ID 完全匹配（100%）
- 0 个缺失规则
- 0 个命名不一致

### 3.3 修复前后对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 规则 ID 一致率（严格匹配） | 7.7%（2/26） | 预期 100% |
| 规则加载错误率 | 30.1%（25/83） | 0%（0/74） |
| known-issues 规则覆盖率 | 部分缺失 | 21/21（100%） |
| 安全规则总数 | 60 | 74 |

## 4. 修改的文件清单

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `test-validation/known-issues.json` | 修改 | 7 个规则 ID 从 ts 重命名为 js；修正 total_issues |
| `references/security/xss.yaml` | 新增规则 | +1 条（xss-js-outerhtml） |
| `references/security/sql-injection.yaml` | 新增规则 | +1 条（sqli-java-statement-concat） |
| `references/security/path-traversal.yaml` | 新增规则 | +4 条 |
| `references/security/xxe.yaml` | 新增规则 | +3 条 |
| `references/security/privilege-escalation.yaml` | 新增规则 | +3 条 |
| `references/security/ssrf.yaml` | 新增规则 | +2 条 |
