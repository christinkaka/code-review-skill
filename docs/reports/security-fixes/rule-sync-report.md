# 规则同步报告

> 生成时间: 2026-07-28
> 范围: YAML 规则文件 -> Markdown 规约文件

---

## 1. 同步的规则列表

以下 7 条规则从 YAML 文件同步到对应的 MD 规约文件：

### 1.1 Python XXE 细粒度规则（3 条）

来源: `xxe.yaml` -> 目标: `xxe.md`

| 规则 ID | 语言 | 严重级别 | 说明 |
|---------|------|---------|------|
| `xxe-python-lxml-parser` | Python | ERROR | 检测 `etree.XMLParser()` 默认配置（resolve_entities 默认为 True） |
| `xxe-python-lxml-parse` | Python | ERROR | 检测 `etree.parse()` 未传入安全解析器 |
| `xxe-python-lxml-resolve-entities` | Python | ERROR | 检测显式设置 `resolve_entities=True` |

### 1.2 TypeScript XSS 规则（2 条）

来源: `xss.yaml` -> 目标: `xss.md`

| 规则 ID | 语言 | 严重级别 | 说明 |
|---------|------|---------|------|
| `xss-js-outerhtml` | JS/TS | ERROR | 检测 `outerHTML` 直接赋值用户输入 |
| `xss-js-dangerouslysetinnerhtml` | JS/TS | ERROR | 检测 React `dangerouslySetInnerHTML` 使用 |

### 1.3 TypeScript SSRF 规则（1 条）

来源: `ssrf.yaml` -> 目标: `ssrf.md`

| 规则 ID | 语言 | 严重级别 | 说明 |
|---------|------|---------|------|
| `ssrf-js-http-get` | JS/TS | ERROR | 检测 `http.get()` SSRF 风险 |

### 1.4 Python 提权规则（1 条）

来源: `privilege-escalation.yaml` -> 目标: `privilege-escalation.md`

| 规则 ID | 语言 | 严重级别 | 说明 |
|---------|------|---------|------|
| `priv-python-check-output-shell-true` | Python | ERROR | 检测 `subprocess.check_output(shell=True)` |

---

## 2. 修复的规则列表

以下 3 条规则在 MD 文件中修复了模式不匹配问题：

### 2.1 xss-java-servlet-output（模式扩展）

文件: `xss.md`

**修复内容**: 增加 `println()` 和 `print()` 模式的匹配。

修复前仅检测 `$RESPONSE.getWriter().write($USER_INPUT)`，修复后同时检测：
- `$RESPONSE.getWriter().write($USER_INPUT)` (原有)
- `$RESPONSE.getWriter().println($USER_INPUT)` (新增)
- `$RESPONSE.getWriter().print($USER_INPUT)` (新增)

同步增加了相应的 `pattern-not` 排除模式。

### 2.2 sqli-java-statement-concat（新增规则）

文件: `sql-injection.md`

**修复内容**: 新增 `sqli-java-statement-concat` 规则，匹配 `executeQuery()` 方法调用。

```yaml
id: sqli-java-statement-concat
languages: [java]
severity: ERROR
cwe: CWE-89
```

检测模式:
```
Statement $STMT = ...;
...
$STMT.executeQuery($SQL);
```

### 2.3 xss-js-dangerouslysetinnerhtml（正则修复）

文件: `xss.md`

**修复内容**: 修复 `pattern-regex` 以匹配实际代码格式中的空格变化。

修复前:
```
dangerouslySetInnerHTML=\{\{__html:\s*[^}]+\}\}
```

修复后:
```
dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*[^}]+\s*\}\s*\}
```

与 YAML 源文件中的正则保持一致，支持 JSX 属性中各种空格格式。

---

## 3. 验证结果

### 3.1 单规则 Semgrep 验证

对所有修改过的 MD 文件中的每条规则进行独立 Semgrep 验证：

| 文件 | 规则总数 | 验证通过 | 验证失败 | 通过率 |
|------|---------|---------|---------|--------|
| `xxe.md` | 9 | 9 | 0 | 100% |
| `xss.md` | 9 | 9 | 0 | 100% |
| `ssrf.md` | 7 | 7 | 0 | 100% |
| `privilege-escalation.md` | 10 | 10 | 0 | 100% |
| `sql-injection.md` | 6 | 6 | 0 | 100% |
| **合计** | **41** | **41** | **0** | **100%** |

### 3.2 全量安全规则验证

对 `references/security/` 目录下所有 16 个 MD 文件进行全量验证：

| 指标 | 数值 |
|------|------|
| 检查文件数 | 16 |
| 解析规则总数 | 70 |
| 有效规则数 | 70 |
| 规则解析成功率 | 100% |

所有新增和修复的规则均通过 Semgrep 语法验证，无解析错误。

---

## 4. 变更文件清单

| 文件路径 | 变更类型 | 说明 |
|---------|---------|------|
| `references/security/xxe.md` | 新增 3 条规则 | xxe-python-lxml-parser, xxe-python-lxml-parse, xxe-python-lxml-resolve-entities |
| `references/security/xss.md` | 新增 1 条 + 修复 2 条 | 新增 xss-js-outerhtml; 修复 xss-java-servlet-output, xss-js-dangerouslysetinnerhtml |
| `references/security/ssrf.md` | 新增 1 条规则 | ssrf-js-http-get |
| `references/security/privilege-escalation.md` | 新增 1 条规则 | priv-python-check-output-shell-true |
| `references/security/sql-injection.md` | 新增 1 条规则 | sqli-java-statement-concat |
