# Django/Flask 框架安全规则

> 针对 Django 和 Flask 框架的常见安全漏洞检测规则。

---

# Django - mark_safe 未转义用户输入

> Django `mark_safe()` 将字符串标记为安全 HTML，绕过自动转义。若参数包含用户输入，将导致 XSS 漏洞。

```yaml
id: django-mark-safe-xss
languages: [python]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 风险说明

Django 模板默认对变量进行 HTML 转义，但 `mark_safe()` 会禁用转义。若将用户输入传入 `mark_safe()`，攻击者可注入恶意脚本。

## 违规示例

```python
from django.utils.safestring import mark_safe

def show_comment(request):
    comment = request.POST.get('comment', '')
    safe_html = mark_safe(comment)  # 用户输入未转义，XSS 风险
    return render(request, 'show.html', {'html': safe_html})
```

## 正确示例

```python
from django.utils.html import escape
from django.utils.safestring import mark_safe

def show_comment(request):
    comment = request.POST.get('comment', '')
    safe_html = mark_safe(escape(comment))  # 先转义再标记为安全
    return render(request, 'show.html', {'html': safe_html})
```

## 检测模式

```pattern
mark_safe($USER_INPUT)
```

```pattern-not
mark_safe(escape($USER_INPUT))
```

```pattern-not
mark_safe(html.escape($USER_INPUT))
```

---

# Django - format_html 使用用户输入

> `format_html()` 用于安全构造 HTML，但若第一个参数（格式字符串）包含用户输入，仍可能导致 XSS。

```yaml
id: django-format-html-xss
languages: [python]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 风险说明

`format_html()` 会对参数进行转义，但格式字符串本身若包含用户输入，转义将失效。

## 违规示例

```python
from django.utils.html import format_html

def show_link(request):
    url = request.GET.get('url', '')
    # 危险：url 在格式字符串中，不会被转义
    html = format_html(url + '<br/>')  # XSS 风险
    return HttpResponse(html)
```

## 正确示例

```python
from django.utils.html import format_html

def show_link(request):
    url = request.GET.get('url', '')
    # 安全：url 作为参数传入，会被自动转义
    html = format_html('<a href="{}">Link</a>', url)
    return HttpResponse(html)
```

## 检测模式

```pattern
format_html($USER_INPUT + ...)
```

```pattern
format_html(... + $USER_INPUT)
```

---

# Django - raw SQL 查询

> Django `raw()` / `extra()` / `RawSQL()` 执行原始 SQL，若包含用户输入将导致 SQL 注入。

```yaml
id: django-raw-sql-injection
languages: [python]
severity: CRITICAL
cwe: CWE-89
owasp: A03:2021
```

## 风险说明

Django ORM 提供 `raw()`、`extra()`、`RawSQL()` 等方法执行原始 SQL。若 SQL 字符串包含用户输入（通过字符串拼接或格式化），将导致 SQL 注入。

## 违规示例

```python
from django.contrib.auth.models import User

def search_user(request):
    username = request.GET.get('username', '')
    # 危险：字符串拼接构建 SQL
    users = User.objects.raw('SELECT * FROM auth_user WHERE username = \'' + username + '\'')
    return users
```

```python
def filter_posts(request):
    category = request.GET.get('category', '')
    # 危险：format 构建 SQL
    posts = Post.objects.extra(where=["category = '{}'".format(category)])
    return posts
```

## 正确示例

```python
def search_user(request):
    username = request.GET.get('username', '')
    # 安全：使用参数化查询
    users = User.objects.raw('SELECT * FROM auth_user WHERE username = %s', [username])
    return users
```

```python
def filter_posts(request):
    category = request.GET.get('category', '')
    # 安全：使用 ORM 查询
    posts = Post.objects.filter(category=category)
    return posts
```

## 检测模式

```pattern
$MODEL.objects.raw($SQL + ...)
```

```pattern
$MODEL.objects.raw(... + $SQL)
```

```pattern
$MODEL.objects.raw($SQL.format(...))
```

```pattern
$MODEL.objects.raw(f"...")
```

```pattern
$MODEL.objects.extra(where=[... .format(...)])
```

```pattern
RawSQL($SQL + ..., ...)
```

```pattern
RawSQL($SQL.format(...), ...)
```

---

# Django - DEBUG 模式开启

> 生产环境中 `DEBUG = True` 会暴露敏感信息（堆栈跟踪、数据库查询、环境变量）。

```yaml
id: django-debug-enabled
languages: [python]
severity: WARNING
cwe: CWE-215
owasp: A05:2021
```

## 风险说明

Django 在 `DEBUG = True` 模式下会显示详细的错误页面，包含堆栈跟踪、SQL 查询、环境变量等敏感信息。生产环境必须关闭 DEBUG。

## 违规示例

```python
# settings.py
DEBUG = True  # 生产环境不应开启
ALLOWED_HOSTS = ['*']
```

## 正确示例

```python
# settings.py
import os
DEBUG = os.environ.get('DEBUG', 'False') == 'True'  # 从环境变量读取
ALLOWED_HOSTS = ['example.com']
```

## 检测模式

```pattern
DEBUG = True
```

---

# Flask - render_template_string SSTI

> Flask `render_template_string()` 使用用户输入构造 Jinja2 模板，将导致服务端模板注入（SSTI）。

```yaml
id: flask-ssti-render-template-string
languages: [python]
severity: CRITICAL
cwe: CWE-1336
owasp: A03:2021
```

## 风险说明

`render_template_string()` 将字符串作为 Jinja2 模板渲染。若模板字符串包含用户输入，攻击者可注入模板代码执行任意命令。

## 违规示例

```python
from flask import render_template_string, request

@app.route('/greet')
def greet():
    name = request.args.get('name', 'World')
    # 危险：用户输入直接嵌入模板
    template = f'<h1>Hello {name}!</h1>'
    return render_template_string(template)
```

## 正确示例

```python
from flask import render_template, request

@app.route('/greet')
def greet():
    name = request.args.get('name', 'World')
    # 安全：使用模板文件，变量通过参数传递
    return render_template('greet.html', name=name)
```

或

```python
from flask import render_template_string, request
from markupsafe import escape

@app.route('/greet')
def greet():
    name = request.args.get('name', 'World')
    # 安全：先转义再嵌入模板
    template = f'<h1>Hello {escape(name)}!</h1>'
    return render_template_string(template)
```

## 检测模式

```pattern
render_template_string($TEMPLATE + ...)
```

```pattern
render_template_string(... + $TEMPLATE)
```

```pattern
render_template_string(f"...")
```

```pattern
render_template_string($TEMPLATE.format(...))
```

```pattern-not
render_template_string(escape($TEMPLATE))
```

---

# Flask - Markup 未转义用户输入

> Flask `Markup()` 将字符串标记为安全 HTML，若参数包含用户输入将导致 XSS。

```yaml
id: flask-markup-xss
languages: [python]
severity: ERROR
cwe: CWE-79
owasp: A03:2021
```

## 风险说明

Flask 的 `Markup` 类（来自 markupsafe）将字符串标记为安全 HTML，绕过自动转义。若参数包含用户输入，将导致 XSS。

## 违规示例

```python
from markupsafe import Markup
from flask import request

@app.route('/show')
def show():
    content = request.args.get('content', '')
    safe_html = Markup(content)  # 用户输入未转义，XSS 风险
    return f'<div>{safe_html}</div>'
```

## 正确示例

```python
from markupsafe import Markup, escape
from flask import request

@app.route('/show')
def show():
    content = request.args.get('content', '')
    safe_html = Markup(escape(content))  # 先转义再标记为安全
    return f'<div>{safe_html}</div>'
```

## 检测模式

```pattern
Markup($USER_INPUT)
```

```pattern-not
Markup(escape($USER_INPUT))
```

---

# Python - yaml.load 未使用 SafeLoader

> `yaml.load()` 默认使用不安全的 Loader，可执行任意 Python 代码。应使用 `yaml.safe_load()` 或显式指定 `Loader=yaml.SafeLoader`。

```yaml
id: python-unsafe-yaml-load
languages: [python]
severity: ERROR
cwe: CWE-502
owasp: A08:2021
```

## 风险说明

PyYAML 的 `yaml.load()` 默认使用 `Loader=yaml.FullLoader`（旧版本为 `yaml.Loader`），可反序列化任意 Python 对象。攻击者可构造恶意 YAML 文件执行任意代码。

## 违规示例

```python
import yaml

def load_config(config_file):
    with open(config_file) as f:
        # 危险：使用不安全的 Loader
        config = yaml.load(f)
    return config
```

## 正确示例

```python
import yaml

def load_config(config_file):
    with open(config_file) as f:
        # 安全：使用 safe_load
        config = yaml.safe_load(f)
    return config
```

或

```python
import yaml

def load_config(config_file):
    with open(config_file) as f:
        # 安全：显式指定 SafeLoader
        config = yaml.load(f, Loader=yaml.SafeLoader)
    return config
```

## 检测模式

```pattern
yaml.load($FILE)
```

```pattern-not
yaml.safe_load($FILE)
```

```pattern-not
yaml.load($FILE, Loader=yaml.SafeLoader)
```

```pattern-not
yaml.load($FILE, Loader=SafeLoader)
```

---

# Python - Jinja2 模板注入

> 使用用户输入构造 Jinja2 `Template` 对象将导致服务端模板注入（SSTI）。

```yaml
id: python-jinja2-ssti
languages: [python]
severity: CRITICAL
cwe: CWE-1336
owasp: A03:2021
```

## 风险说明

Jinja2 的 `Template` 类将字符串作为模板渲染。若模板字符串包含用户输入，攻击者可注入模板代码执行任意命令。

## 违规示例

```python
from jinja2 import Template

def render_greeting(name):
    # 危险：用户输入直接嵌入模板
    template = Template(f'Hello {name}!')
    return template.render()
```

## 正确示例

```python
from jinja2 import Template

def render_greeting(name):
    # 安全：使用占位符，变量通过 render 参数传递
    template = Template('Hello {{ name }}!')
    return template.render(name=name)
```

## 检测模式

```pattern
Template($TEMPLATE + ...)
```

```pattern
Template(... + $TEMPLATE)
```

```pattern
Template(f"...")
```

```pattern
Template($TEMPLATE.format(...))
```
