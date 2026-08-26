# 开放重定向 - 用户可控 URL 流入重定向 API（模式匹配）

> 用户可控 URL 参数未经白名单校验直接流入 `sendRedirect`，导致钓鱼攻击或凭证泄露。
> 基于 Semgrep pattern 模式做语法结构匹配，通过 pattern-not 排除加固形态。

```yaml
id: redirect-pattern-2
languages: [java]
severity: HIGH
cwe: CWE-601
owasp: A01:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头（`$REQ.getParameter(...)` / `$REQ.getHeader(...)`）
- **污点汇聚**：`sendRedirect` 调用，且 URL 来自用户可控变量
- **加固豁免**：通过 pattern-not 排除以下加固形态
  - `isAllowedDomain(url)` 白名单校验
  - `url.startsWith("/")` 相对路径限制

**实测行为合同**（PoC 矩阵验证）：
- `resp.sendRedirect(req.getParameter("url"))` 命中（直接拼接）
- `String url = req.getParameter("url"); resp.sendRedirect(url)` 命中（变量传播）
- `if (isAllowedDomain(url)) { resp.sendRedirect(url); }` 不命中（白名单加固）
- `if (url.startsWith("/")) { resp.sendRedirect(url); }` 不命中（相对路径限制）
- `resp.sendRedirect("https://trusted.com")` 不命中（常量 URL，无污点源）

## 检测模式

```pattern
String $URL = $REQ.getParameter(...);
...
$RESP.sendRedirect($URL);
```

```pattern-not
String $URL = $REQ.getParameter(...);
...
if (isAllowedDomain($URL)) {
  ...
  $RESP.sendRedirect($URL);
}
```

```pattern-not
String $URL = $REQ.getParameter(...);
...
if ($URL.startsWith(...)) {
  ...
  $RESP.sendRedirect($URL);
}
```

```pattern-not
String $URL = $REQ.getParameter(...);
...
if ($CHECK($URL) == null) {
  ...
  return;
}
...
$RESP.sendRedirect($URL);
```

## 已知边界

- **Spring `redirect:` 前缀**：`return "redirect:" + url` 形态未覆盖（字符串拼接，pattern 难以表达）
- **Spring RedirectView**：`new RedirectView(url)` 形态未覆盖（需补充 sink）
- **URL 解析后校验 host**：`URI uri = new URI(url); if (trustedHosts.contains(uri.getHost()))` 形态未覆盖

这些边界可在后续迭代中通过扩展 sink 或新增 pattern 规则覆盖。
