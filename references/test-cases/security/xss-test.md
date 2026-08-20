# XSS 测试案例

## 违规代码 - Servlet 直接写入用户输入

```java
protected void doGet(HttpServletRequest request, HttpServletResponse response)
        throws ServletException, IOException {
    String name = request.getParameter("name");
    response.getWriter().write("Hello, " + name);
}
```

**预期命中**: `xss-java-servlet-output`
**文件类型**: `.java`

---

## 违规代码 - JavaScript innerHTML

```javascript
function displayUserContent(userInput) {
    const container = document.getElementById('content');
    container.innerHTML = userInput;
}
```

**预期命中**: `xss-js-innerhtml`
**文件类型**: `.js`

---

## 违规代码 - React dangerouslySetInnerHTML

```jsx
function UserComment({ comment }) {
    return <div dangerouslySetInnerHTML={{__html: comment}} />;
}
```

**预期命中**: `xss-js-dangerouslysetinnerhtml`
**文件类型**: `.jsx`

---

## 违规代码 - Python Flask Markup

```python
from flask import Markup

@app.route('/greet')
def greet():
    name = request.args.get('name')
    return str(Markup(f"<b>Hello, {name}</b>"))
```

**预期命中**: `xss-python-flask-markup`
**文件类型**: `.py`

---

## 正确代码 - Servlet 使用 HTML 转义

```java
protected void doGet(HttpServletRequest request, HttpServletResponse response)
        throws ServletException, IOException {
    String name = request.getParameter("name");
    response.getWriter().write("Hello, " + HtmlUtils.htmlEscape(name));
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - JavaScript textContent

```javascript
function displayUserContent(userInput) {
    const container = document.getElementById('content');
    container.textContent = userInput;
}
```

**预期命中**: 无
**文件类型**: `.js`
