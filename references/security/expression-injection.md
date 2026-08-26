# 表达式注入 - SpEL 用户可控数据流入表达式求值（数据流分析）

> 用户可控数据（HTTP 请求参数/头）流入 Spring Expression Language（SpEL）表达式解析与求值。攻击者构造 `T(java.lang.Runtime).getRuntime().exec(...)` 类表达式可实现任意代码执行（RCE）。基于 Semgrep taint 模式做过程内数据流追踪。

```yaml
id: spel-taint
languages: [java]
severity: CRITICAL
cwe: CWE-917
owasp: A03:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流 + Spring 入口方法参数
- **污点汇聚**：`Expression.getValue(...)` 求值点（污点经 `parseExpression`
  返回值传播到 Expression 对象，求值时触发执行）。双 sink 形态：
  类型化元变量覆盖声明变量场景；链式 pattern
  `$P.parseExpression(...).getValue(...)` 覆盖链式调用场景——semgrep
  类型化元变量对链式调用返回值不做类型推断（PoC 实证，类型化 sink
  漏报链式场景），且只类型化时 `cookie.getValue()` 等 Cookie 取值调用
  被正确排除（java-sec-code Cookies/Deserialize/Shiro 实测 6 处
  cookie.getValue 误命中过宽 sink `$E.getValue(...)`）
- **净化器**：`SimpleEvaluationContext`（只读数据绑定模式，禁止方法调用与
  类型引用）——以 sink 排除模式表达，非数据流切断

`parser.parseExpression(value).getValue()` 命中（污点随解析返回值传播，
无参 getValue 使用默认上下文，等价 StandardEvaluationContext 语义）；
`expression.getValue(standardEvaluationContext)` 命中（Standard 上下文
允许 `T()` 类型引用与任意方法调用，OpenMetadata CVE-2024-28253 同型）；
`expression.getValue(simpleEvaluationContext)` 不报（Simple 上下文禁止
方法调用，RCE 被切断）；
`parser.parseExpression(value)` 后仅调用 `getExpressionString()` 不报
（解析不执行，求值点才是漏洞触发位置）；
`cookie.getValue()` 不报（Cookie 取值 API，非 SpEL 求值——类型化 sink
+ parseExpression 方法名特征双重收窄）。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
spring-entrypoint-param
```

```pattern-sinks
(org.springframework.expression.Expression $E).getValue(...)
$P.parseExpression(...).getValue(...)
```

```pattern-sinks-not
$E.getValue((org.springframework.expression.spel.support.SimpleEvaluationContext $CTX), ...)
$P.parseExpression(...).getValue((org.springframework.expression.spel.support.SimpleEvaluationContext $CTX), ...)
```

---

# 表达式注入 - QLExpress 用户可控数据流入表达式执行（数据流分析）

> 用户可控数据流入阿里 QLExpress（com.ql.util.express）表达式执行 API。QLExpress 表达式可实例化任意对象（`new java.net.URLClassLoader(...)` 等），污点直达 `ExpressRunner.execute` 即 RCE。基于 Semgrep taint 模式做过程内数据流追踪。

```yaml
id: qlexpress-taint
languages: [java]
severity: CRITICAL
cwe: CWE-917
owasp: A03:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流 + Spring 入口方法参数
- **污点汇聚**：`ExpressRunner.execute(...)` 第一个参数（表达式字符串）
- **净化器**：无数据流净化。`QLExpressRunStrategy.setForbidInvokeSecurityRiskMethods(true)`
  全局安全策略（禁止调用高风险方法）以 sink 排除块豁免——该加固是
  静态全局配置，不在污点传播路径上，无法用 sanitizer 表达

sink 采用类型化元变量 `(com.ql.util.express.ExpressRunner $R).execute(...)`：
`execute` 是高频方法名，`ExecutorService.execute()`（线程池提交）、
`ExpressRunner` 同名调用若不类型化会大量误命中（sqli-taint 类型化
sink 的同型教训，见 sql-injection.md 2026-08-26 注记）。

`runner.execute(userInput, context, null, true, false)` 命中；
`setForbidInvokeSecurityRiskMethods(true)` 后的 `execute` 不报
（全局策略禁止反射/Runtime 调用）；
常量表达式 `runner.execute("1+2", ...)` 不报（无污点源）。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
spring-entrypoint-param
```

```pattern-sinks
(com.ql.util.express.ExpressRunner $R).execute(...)
```

```pattern-sinks-not-inside
QLExpressRunStrategy.setForbidInvokeSecurityRiskMethods(true);
...
$X.execute(...);
```

---

# 脚本注入 - 用户可控数据流入脚本引擎执行（数据流分析）

> 用户可控数据流入 javax.script 脚本引擎（Nashorn/JS/Groovy 等被 ScriptEngineManager 加载的引擎）的 `eval` 或 GroovyShell 的 `evaluate`。脚本内容完全受控即任意代码执行（RCE）。基于 Semgrep taint 模式做过程内数据流追踪。

```yaml
id: script-engine-taint
languages: [java]
severity: CRITICAL
cwe: CWE-94
owasp: A03:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流 + Spring 入口方法参数
- **污点汇聚**：`ScriptEngine.eval(...)` 与 `GroovyShell.evaluate(...)`
  （脚本内容参数）
- **净化器**：无。脚本引擎无安全上下文概念，污点流入即风险，
  引擎选择（js/groovy/nashorn）不改变可控脚本的 RCE 本质

`engine.eval(taintedCmd, bindings)` 命中（污点经 `String.format` 拼接
传播仍命中——Nashorn `load()` 外链脚本加载场景同型）；
`groovyShell.evaluate(userContent)` 命中（Groovy 脚本可执行
`"cmd".execute()`）；
常量脚本 `engine.eval("print('hello')")` 不报（无污点源）。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
spring-entrypoint-param
```

```pattern-sinks
(javax.script.ScriptEngine $E).eval(...)
(groovy.lang.GroovyShell $S).evaluate(...)
```
