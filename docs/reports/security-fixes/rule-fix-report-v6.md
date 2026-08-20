# 规则修复报告 v6 - xss-java-servlet-output

> 修复日期：2026-07-28
> 修复目标：补充 `xss-java-servlet-output` 规则，消除 2 个漏报，达到 100% 检出率

---

## 1. 问题分析

### 1.1 漏报详情

| 文件 | 行号 | 漏洞描述 | 修复前状态 |
|------|------|----------|-----------|
| `java/xss/Vulnerable.java` | 28-30 | `request.getParameter()` + `out.println("..." + userName + "...")` | 漏报 |
| `java/xss/Vulnerable.java` | 42-44 | `request.getParameter()` + `out.println("..." + comment + "...")` | 漏报 |

### 1.2 根因分析

原有规则使用 `$RESPONSE.getWriter().println($PARAM)` 模式，要求直接链式调用。但实际漏洞代码采用两步写法：

```java
// 步骤 1：获取 PrintWriter 局部变量
PrintWriter out = response.getWriter();
// 步骤 2：通过局部变量输出（含字符串拼接）
out.println("<h1>Welcome, " + userName + "</h1>");
```

原有规则存在两个不匹配：
1. **间接调用**：代码使用局部变量 `out` 而非 `response.getWriter()` 链式调用
2. **字符串拼接**：参数嵌入字符串拼接表达式 `"..." + userName + "..."`，而非直接传递

---

## 2. 修复方案

### 2.1 规则模式调整

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| 输出匹配 | `$RESPONSE.getWriter().println($PARAM)` | `$OUT.println(... + $PARAM + ...)` |
| 数据流源 | 无（仅匹配 `$USER_INPUT`） | `String $PARAM = $REQUEST.getParameter(...)` |
| 拼接支持 | 不支持 | 支持 `... + $PARAM + ...` 省略号表达式 |
| 局部变量 | 要求链式调用 | 使用 `$OUT` 元变量匹配任意 PrintWriter |
| 排除规则 | 4 条（基于链式调用） | 4 条（基于局部变量 + 安全函数） |

### 2.2 新增规则定义

```yaml
- id: xss-java-servlet-output
  languages: [java]
  patterns:
    - pattern-either:
        # 字符串拼接 + println（最常见模式）
        - pattern: |
            String $PARAM = $REQUEST.getParameter(...);
            ...
            $OUT.println(... + $PARAM + ...);
        # 直接输出参数
        - pattern: |
            String $PARAM = $REQUEST.getParameter(...);
            ...
            $OUT.println($PARAM);
        # 字符串拼接 + write
        - pattern: |
            String $PARAM = $REQUEST.getParameter(...);
            ...
            $OUT.write(... + $PARAM + ...);
        # 字符串拼接 + print
        - pattern: |
            String $PARAM = $REQUEST.getParameter(...);
            ...
            $OUT.print(... + $PARAM + ...);
    # 排除：使用独立安全变量
    - pattern-not: |
        String $PARAM = $REQUEST.getParameter(...);
        ...
        $SAFE = encodeHtml($PARAM);
        ...
        $OUT.println(... + $SAFE + ...);
    - pattern-not: |
        String $PARAM = $REQUEST.getParameter(...);
        ...
        $SAFE = HtmlUtils.htmlEscape($PARAM);
        ...
        $OUT.println(... + $SAFE + ...);
    # 排除：原地转义参数
    - pattern-not: |
        String $PARAM = $REQUEST.getParameter(...);
        ...
        $PARAM = encodeHtml($PARAM);
        ...
        $OUT.println(... + $PARAM + ...);
    - pattern-not: |
        String $PARAM = $REQUEST.getParameter(...);
        ...
        $PARAM = HtmlUtils.htmlEscape($PARAM);
        ...
        $OUT.println(... + $PARAM + ...);
  message: "XSS 风险：Servlet 响应直接写入用户输入"
  severity: ERROR
  metadata:
    cwe: CWE-79
    owasp: "A03:2021"
```

### 2.3 关键技术点

1. **`$OUT` 元变量**：匹配任意变量名（如 `out`），不要求显式声明为 `response.getWriter()` 的返回值，从而覆盖局部变量间接调用的场景。

2. **`... + $PARAM + ...` 省略号表达式**：Semgrep 支持在二元表达式中使用 `...` 匹配任意数量的操作数。`... + $PARAM + ...` 可匹配任何包含 `$PARAM` 的字符串拼接表达式，如 `"<h1>" + userName + "</h1>"`。

3. **双重排除策略**：
   - 独立安全变量：`$SAFE = encodeHtml($PARAM)` 后使用 `$SAFE`
   - 原地转义：`$PARAM = encodeHtml($PARAM)` 后使用 `$PARAM`

---

## 3. 验证结果

### 3.1 规则语法验证

```
$ semgrep --config xss.yaml --validate
Configuration is valid - found 0 configuration error(s), and 9 rule(s).
```

- 规则解析成功率：**9/9 = 100%**
- 配置错误数：**0**

### 3.2 漏洞检出验证

```
$ semgrep --config xss.yaml --include '*.java' test-validation/java/xss/
Findings: 2 (2 blocking)
Rules run: 3
Targets scanned: 2
```

| 文件 | 行号 | 规则 ID | 状态 |
|------|------|---------|------|
| `Vulnerable.java` | 28-30 | `xss-java-servlet-output` | 已检出 |
| `Vulnerable.java` | 42-44 | `xss-java-servlet-output` | 已检出 |
| `Safe.java` | - | - | 未检出（正确） |

### 3.3 误报验证

- `Safe.java`（doGet + doPost）：0 个误报
- 安全代码使用 `encodeHtml()` 转义后输出，被 `pattern-not` 正确排除

---

## 4. 预期效果评估

| 指标 | 修复前 | 修复后 | 达标 |
|------|--------|--------|------|
| 检出率 | 24/26 = 92.3% | 26/26 = **100%** | Yes |
| 精确率 | 24/27 = 88.9% | 26/29 = **89.7%** | Yes |
| F1 Score | 90.6% | **94.7%** | Yes |

---

## 5. 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `code-review-skill/references/security/xss.md` | 修改 | 更新规则定义区块（第 75-127 行） |
| `code-review-skill/references/security/xss.yaml` | 修改 | 同步更新规则定义（第 7-58 行） |

---

## 6. 修复操作日志

| 序号 | 操作 | 结果 |
|------|------|------|
| 1 | 分析漏报根因：原有规则要求链式调用，无法匹配局部变量 + 字符串拼接 | 确认 2 个不匹配点 |
| 2 | 设计新规则模式：`$OUT.println(... + $PARAM + ...)` | 通过 Semgrep 模式测试 |
| 3 | 迭代测试 5 种模式变体（直接调用/局部变量/拼接/省略号） | 确定最优模式 |
| 4 | 更新 xss.md 规则定义 | 完成 |
| 5 | 同步更新 xss.yaml 规则定义 | 完成 |
| 6 | Semgrep 语法验证 | 9 rules, 0 errors |
| 7 | 漏洞检出验证 | 2 findings on Vulnerable.java, 0 on Safe.java |
