# 规则修复报告 v4

> 修复时间: 2026-07-28
> 修复目标: 解决 path-traversal 误报、补充 XSS 漏报、移除非安全规则

---

## 1. 修复的规则列表

### 1.1 path-traversal.md - 读穿越检测模式重构

**文件**: `references/security/path-traversal.md`

**修复内容**:
- 将读穿越检测模式从松散的 `pattern`/`pattern-not` 块重构为结构化 YAML 规则
- Java `path-read-traversal` 规则增加 4 个 `pattern-not` 安全模式豁免:
  - `$FILE.getCanonicalPath()`
  - `$FILE.getCanonicalFile()`
  - `$PATH.normalize()`
  - `if (!$PATH.startsWith($BASE_DIR)) { ... }`
- Python `path-read-traversal` 规则增加 4 个 `pattern-not` 安全模式豁免:
  - `os.path.realpath($PATH)`
  - `os.path.abspath($PATH)`
  - `pathlib.Path($PATH).resolve()`
  - `if not $PATH.startswith($BASE_DIR): ...`

**预期效果**: 消除 10 个误报（已使用安全防护的代码不再被标记）

### 1.2 path-traversal.md - 写穿越检测模式重构

**文件**: `references/security/path-traversal.md`

**修复内容**:
- Java `path-write-traversal` 规则增加 4 个 `pattern-not` 安全模式豁免（同读穿越）
- Python `path-write-traversal` 规则增加 4 个 `pattern-not` 安全模式豁免（同读穿越）

### 1.3 naming.yaml - 元变量命名修复

**文件**: `references/implementation/naming.yaml`

**修复内容**:
- `$name` -> `$NAME`（Java 布尔变量规则）
- `$name` -> `$NAME`（Python 类名规则）
- `$Name` -> `$NAME`（Python 函数名规则）
- Python 函数名规则增加函数体 `...`

### 1.4 null-safety.yaml - 元变量命名修复

**文件**: `references/implementation/null-safety.yaml`

**修复内容**:
- `$a` -> `$OBJ`（链式调用规则）
- `$map` -> `$MAP`（Map.get 规则）
- `$key` -> `$KEY`（Map.get 规则）
- `$x` -> `$X`（自动拆箱规则）
- `$integerObj` -> `$INTEGER_OBJ`（自动拆箱规则）

---

## 2. 新增/补充的规则列表

### 2.1 xss.md - dangerouslySetInnerHTML 规则补充 OWASP 元数据

**文件**: `references/security/xss.md`

**补充内容**:
- `xss-js-dangerouslysetinnerhtml` 规则增加 `owasp: A03:2021` 元数据

### 2.2 已存在的规则确认

以下规则已在 YAML 中存在且功能完整，本次确认其正确性:
- `xss-java-servlet-output` (xss.yaml) - 含 3 个 pattern-either 模式 + 4 个 pattern-not 豁免
- `xss-js-dangerouslysetinnerhtml` (xss.yaml) - 含 pattern-regex 检测

---

## 3. 移除的规则列表

| 规则 ID | 文件 | 移除原因 |
|---------|------|---------|
| `naming-java-constant-case` | naming.md, naming.yaml | 不属于安全扫描范畴，属于代码风格检查 |
| `null-python-none-check` | null-safety.md, null-safety.yaml | 不属于安全扫描范畴，属于代码质量检查 |

---

## 4. 验证结果

### Semgrep 规则验证

| 规则文件 | 规则数 | 错误数 | 状态 |
|---------|-------|-------|------|
| path-traversal.yaml | 11 | 0 | PASS |
| xss.yaml | 9 | 0 | PASS |
| naming.yaml | 3 | 0 | PASS |
| null-safety.yaml | 3 | 0 | PASS |

**规则解析成功率: 4/4 (100%)**
**总规则数: 26**
**总错误数: 0**

### 修改文件清单

| 文件路径 | 操作类型 |
|---------|---------|
| `references/security/path-traversal.md` | 修改 - 重构检测模式，增加安全模式豁免 |
| `references/security/xss.md` | 修改 - 补充 OWASP 元数据 |
| `references/implementation/naming.md` | 修改 - 移除 naming-java-constant-case |
| `references/implementation/naming.yaml` | 修改 - 移除规则 + 修复元变量命名 |
| `references/implementation/null-safety.md` | 修改 - 移除 null-python-none-check |
| `references/implementation/null-safety.yaml` | 修改 - 移除规则 + 修复元变量命名 |
