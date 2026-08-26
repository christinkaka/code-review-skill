# 命令注入 - 用户可控数据流入操作系统命令执行（数据流分析）

> 用户可控数据（HTTP 请求参数/头）流入 `Runtime.exec` 或 `ProcessBuilder`。直接拼接命令或参数即任意命令执行（RCE）；`sh -c` 形态下单引号内拼接即可注入任意 shell 命令。基于 Semgrep taint 模式做过程内数据流追踪。

```yaml
id: cmdi-taint
languages: [java]
severity: CRITICAL
cwe: CWE-78
owasp: A03:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流 + Spring 入口方法参数
- **污点汇聚**：命令执行三类形态
  - 类型化声明 receiver：`(Runtime $R).exec(...)`——
    `Runtime run = Runtime.getRuntime(); run.exec(cmd)` 声明变量场景。
    **必须用简单名而非全限定名**：`java.lang.Runtime` 是隐式导入，
    代码声明写 `Runtime`，semgrep 类型化元变量不做隐式导入解析
    （PoC 实证全限定名零命中，简单名命中；与 sqli-taint 的
    `java.sql.Statement` 相反——后者需显式 import，全限定名有效）
  - 链式：`Runtime.getRuntime().exec(...)`——类型化元变量对链式调用
    返回值不做类型推断（spel-taint 双 sink 同型），需单列
  - `new ProcessBuilder(...)`——构造器污点实参（含数组初始化器内拼接，
    `new String[]{"sh","-c","ls "+tainted}` 的污点经数组传播实测命中）
- **净化器**：约定式命令过滤函数 `$X.cmdFilter(...)`——**必须带
  receiver 元变量**：semgrep 方法调用 pattern 默认全匹配含 receiver，
  无 receiver 的 `cmdFilter(...)` 不匹配静态调用
  `SecurityUtil.cmdFilter(...)`（PoC 实证；与 ssrf-taint 的
  isAllowedUrl/isSafeUrl 无 receiver 写法差异源于调用形态——
  后者验证用例为局部函数调用形态）

`run.exec(userCmd)` 命中（声明 receiver，java-sec-code Rce.java
runtime/exec 同型）；
`Runtime.getRuntime().exec(request.getParameter(...))` 命中（链式）；
`new ProcessBuilder(new String[]{"sh","-c","curl "+host})` 命中
（数组初始化器拼接，header 污点经数组传播）；
`cmdFilter(filepath)` 过滤后的命令拼接不报（约定式净化）；
`Runtime.getRuntime().exec("touch /tmp/x")` 不报（常量命令无污点源，
含 main 方法——非入口方法，入口点锚定不生效）。

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
(Runtime $R).exec(...)
Runtime.getRuntime().exec(...)
new ProcessBuilder(...)
```

```pattern-sanitizers
$X.cmdFilter(...)
```

## 违规示例

```java
@GetMapping("/codeinject")
public String codeInject(String filepath) throws IOException {
    // 单引号内拼接即可注入：filepath = /tmp;cat /etc/passwd
    String[] cmdList = new String[]{"sh", "-c", "ls -la " + filepath};
    ProcessBuilder builder = new ProcessBuilder(cmdList);
    return WebUtils.convertStreamToString(builder.start().getInputStream());
}
```

## 正确示例

```java
// 白名单字符匹配的过滤函数（非法输入返回 null，拒绝执行）
String filtered = SecurityUtil.cmdFilter(filepath);
if (filtered == null) {
    return "rejected";
}
String[] cmdList = new String[]{"sh", "-c", "ls -la " + filtered};
ProcessBuilder builder = new ProcessBuilder(cmdList);
```
