# 规则修复报告 v5

> 日期: 2026-07-28
> 修复范围: path-traversal (路径穿越), xss (跨站脚本)

---

## 1. 恢复的规则列表

| 规则 ID | 文件 | 操作 | 说明 |
|---------|------|------|------|
| `path-traversal-java-file` | `path-traversal.yaml` | 更新 | 原规则 severity 从 WARNING 提升为 ERROR；pattern 从 `new File($BASE_DIR, $USER_INPUT)` 修正为 `new File($DIR, $USER_INPUT)`；message 更新为 "路径穿越风险：File 构造使用用户输入" |
| `path-traversal-java-file` | `path-traversal.md` | 新增 | 该规则在 md 文档中缺失，已在 "path-read-traversal" 检测模式章节中补充完整的 YAML 规则定义 |

### 变更详情

**path-traversal.yaml (line 57-77)**
- `pattern`: `new File($BASE_DIR, $USER_INPUT)` -> `new File($DIR, $USER_INPUT)` (更通用的变量名)
- `severity`: `WARNING` -> `ERROR` (提升严重级别，匹配安全风险等级)
- `message`: 简化为 "路径穿越风险：File 构造使用用户输入"

**path-traversal.md (line 77-97)**
- 新增 `### path-traversal-java-file` 章节，包含完整 YAML 规则块

---

## 2. 新增的规则列表

| 规则 ID | 文件 | 语言 | 说明 |
|---------|------|------|------|
| `xss-java-servlet-output` | `xss.md` | Java | 在 md 文档中新增完整 YAML 规则定义，包含 pattern-either (write/println/print) 和 pattern-not (HtmlUtils.htmlEscape/escapeHtml) |
| `xss-js-dangerouslysetinnerhtml` | `xss.md` | JavaScript, TypeScript | 在 md 文档中新增完整 YAML 规则定义，使用 pattern-regex 匹配 dangerouslySetInnerHTML 用法 |

### 变更详情

**xss.md - xss-java-servlet-output (line 75-107)**
- 新增 `### xss-java-servlet-output 规则定义` 章节
- 规则包含 3 个 pattern-either 分支 (write/println/print)
- 规则包含 2 个 pattern-not 排除 (HtmlUtils.htmlEscape/escapeHtml)
- severity: ERROR, CWE-79, OWASP A03:2021

**xss.md - xss-js-dangerouslysetinnerhtml (line 281-292)**
- 新增 `### xss-js-dangerouslysetinnerhtml 规则定义` 章节
- 使用 pattern-regex 匹配 `dangerouslySetInnerHTML={{__html: ...}}` 模式
- severity: ERROR, CWE-79, OWASP A03:2021

> 注: 这两个规则在 `xss.yaml` 中已存在，本次是在 `xss.md` 文档中补充对应的 YAML 规则定义块。

---

## 3. 修复的规则列表

| 规则 ID | 文件 | 操作 | 说明 |
|---------|------|------|------|
| `path-config-traversal` | `path-traversal.md` | 优化 | 将简单的 pattern 块替换为完整的 YAML 规则，增加 3 个 pattern-not 安全防护识别 |

### 变更详情

**path-traversal.md - path-config-traversal (line 418-433)**

修复前 (简单 pattern，无误报排除):
```
pattern: new FileInputStream($USER_INPUT)
pattern: open($USER_INPUT, "r")
```

修复后 (完整 YAML 规则，含安全防护识别):
```yaml
- id: path-config-traversal
  languages: [java, python, javascript, typescript]
  patterns:
    - pattern-either:
        - pattern: new FileInputStream($USER_INPUT)
        - pattern: open($USER_INPUT, ...)
    - pattern-not: |
        $FILE.getCanonicalPath()
    - pattern-not: |
        os.path.realpath($USER_INPUT)
    - pattern-not: |
        pathlib.Path($USER_INPUT).resolve()
  message: "路径穿越风险：配置文件路径使用用户输入"
  severity: HIGH
```

新增的 pattern-not 安全防护:
1. `$FILE.getCanonicalPath()` - Java 路径规范化
2. `os.path.realpath($USER_INPUT)` - Python realpath 解析
3. `pathlib.Path($USER_INPUT).resolve()` - Python pathlib 路径解析

预期效果: 消除已使用路径规范化/解析的代码的误报 (预计减少约 7 个误报)。

---

## 4. 验证结果

### Semgrep YAML 规则文件验证

| 文件 | 状态 | 规则数 |
|------|------|--------|
| `authorization.yaml` | PASS | 5 |
| `hardcoded-secrets.yaml` | PASS | 2 |
| `log-injection.yaml` | PASS | 2 |
| `path-traversal.yaml` | PASS | 11 |
| `privilege-escalation.yaml` | PASS | 12 |
| `signature-bypass.yaml` | PASS | 8 |
| `sql-injection.yaml` | PASS | 6 |
| `ssrf.yaml` | PASS | 8 |
| `weak-randomness.yaml` | PASS | 1 |
| `xss.yaml` | PASS | 9 |
| `xxe.yaml` | PASS | 9 |

**规则解析成功率: 11/11 (100%)**

### MD 文档验证说明

MD 文件为文档格式，包含嵌入式 YAML 规则块和中文说明文本，无法被 Semgrep 直接解析为 YAML 配置。这是预期行为 -- MD 文件作为人类可读的规则文档，YAML 文件作为机器可执行的 Semgrep 配置。

---

## 5. 修改文件清单

| 文件路径 | 修改类型 |
|---------|---------|
| `references/security/path-traversal.yaml` | 更新 path-traversal-java-file 规则 (severity, pattern, message) |
| `references/security/path-traversal.md` | 新增 path-traversal-java-file 规则定义; 优化 path-config-traversal 检测模式 |
| `references/security/xss.md` | 新增 xss-java-servlet-output YAML 规则定义; 新增 xss-js-dangerouslysetinnerhtml YAML 规则定义 |
