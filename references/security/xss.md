# XSS - Servlet 响应直接写入用户输入

> Servlet 响应直接写入用户输入未做 HTML 转义，存在反射型 XSS 风险。

```yaml
id: xss-java-servlet-output
languages: [java]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 问题说明

将用户输入直接写入 HTTP 响应，攻击者可以注入恶意脚本（`<script>alert(1)</script>`），在其他用户的浏览器中执行。

## 违规示例

```java
String name = request.getParameter("name");
response.getWriter().write("Hello, " + name);
```

## 正确示例

```java
String name = request.getParameter("name");
response.getWriter().write("Hello, " + HtmlUtils.htmlEscape(name));
```

## 检测模式

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.println(... + $PARAM + ...);
```

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.println($PARAM);
```

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.write(... + $PARAM + ...);
```

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.write(... + $PARAM);
```

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.write($PARAM);
```

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.print(... + $PARAM + ...);
```

```pattern
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.print(... + $PARAM);
```

```pattern-not
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.println(HtmlUtils.htmlEscape($PARAM));
```

```pattern-not
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.println(escapeHtml($PARAM));
```

```pattern-not
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.write(HtmlUtils.htmlEscape($PARAM));
```

```pattern-not
String $PARAM = $REQUEST.getParameter(...);
...
$OUT.write(escapeHtml($PARAM));
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
