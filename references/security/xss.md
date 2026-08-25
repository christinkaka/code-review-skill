# XSS - 用户可控数据流入 HTTP 响应（数据流分析）

> 用户可控数据（HTTP 请求参数/头）经赋值、拼接、字符串构造传播后流入 HTTP 响应输出 API。基于 Semgrep taint 模式做过程内数据流追踪，替代纯模式匹配。

```yaml
id: xss-taint
languages: [java]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/查询串/输入流
- **污点汇聚**：HTTP 响应输出 API（PrintWriter.write/println/print、ServletOutputStream.write/print）
- **净化器**：HTML 转义函数（HtmlUtils.htmlEscape、escapeHtml、StringEscapeUtils.escapeHtml4、ESAPI.encoder().encodeForHTML）

`request.getParameter("name")` 之后 `response.getWriter().write("Hello, " + name)` 命中（污点随字符串拼接传播）；
常量字符串输出无污点源，不报；
经 `HtmlUtils.htmlEscape(...)` 转义后的数据不报。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
```

```pattern-sinks
$WRITER.write(...)
$WRITER.println(...)
$WRITER.print(...)
$OUT.write(...)
$OUT.print(...)
$OUT.println(...)
```

```pattern-sanitizers
HtmlUtils.htmlEscape(...)
escapeHtml(...)
StringEscapeUtils.escapeHtml4(...)
ESAPI.encoder().encodeForHTML(...)
```

---

# XSS - JavaScript innerHTML 直接赋值

> innerHTML 直接赋值用户输入，存在 DOM 型 XSS 风险。

```yaml
id: xss-js-innerhtml
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 违规示例

```javascript
element.innerHTML = userInput;
```

## 正确示例

```javascript
element.textContent = userInput;
// 或使用 DOMPurify
element.innerHTML = DOMPurify.sanitize(userInput);
```

## 检测模式

```pattern
$ELEMENT.innerHTML = $USER_INPUT
```

```pattern-not
$ELEMENT.textContent = $USER_INPUT
```

```pattern-not
$ELEMENT.innerHTML = DOMPurify.sanitize($USER_INPUT)
```

```pattern-not
$ELEMENT.innerHTML = encodeHtml($USER_INPUT)
```

```pattern-not
$ELEMENT.innerHTML = ""
```

```pattern-not
$ELEMENT.innerHTML = ''
```

```pattern-not
$ELEMENT.innerHTML = `${encodeHtml($X)}`
```

```pattern-not
$ELEMENT.innerHTML = `${DOMPurify.sanitize($X)}`
```

---

# XSS - JavaScript document.write 写入用户输入

> document.write() 直接写入用户输入，存在 XSS 风险。

```yaml
id: xss-js-document-write
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 违规示例

```javascript
document.write(userInput);
```

## 检测模式

```pattern
document.write($USER_INPUT)
```

---

# XSS - JavaScript outerHTML 直接赋值

> outerHTML 直接赋值用户输入，存在 XSS 风险。

```yaml
id: xss-js-outerhtml
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 违规示例

```javascript
element.outerHTML = userInput;
```

## 检测模式

```pattern
$ELEMENT.outerHTML = $USER_INPUT
```

---

# XSS - React dangerouslySetInnerHTML 使用用户输入

> dangerouslySetInnerHTML 使用用户输入，存在 XSS 风险。

```yaml
id: xss-js-dangerouslysetinnerhtml
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 违规示例

```jsx
<div dangerouslySetInnerHTML={{__html: userInput}} />
```

## 检测模式

```pattern-regex
dangerouslySetInnerHTML\s*[:=]\s*\{?\s*\{?\s*__html\s*:\s*[^}]+,?\s*\}\s*\}?
```

---

# XSS - Python Flask Markup 不安全使用

> Flask Markup 直接包装用户输入，未做 HTML 转义，存在 XSS 风险。

```yaml
id: xss-python-flask-markup
languages: [python]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 问题说明

`Markup` 会将字符串标记为安全（不再转义），如果其中包含用户输入，攻击者可以注入恶意脚本。

## 违规示例

```python
from flask import Markup

@app.route('/greet')
def greet():
    name = request.args.get('name')
    return str(Markup(f"<b>Hello, {name}</b>"))
```

## 正确示例

```python
from flask import escape

@app.route('/greet')
def greet():
    name = request.args.get('name')
    return f"<b>Hello, {escape(name)}</b>"
```

## 检测模式

```pattern
Markup(...)
```
