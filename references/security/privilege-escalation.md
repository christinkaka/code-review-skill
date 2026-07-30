# 提权 - Runtime.exec 执行用户可控命令

> Runtime.exec() 执行用户可控命令，存在命令注入和提权风险。

```yaml
id: priv-java-runtime-exec
languages: [java]
severity: ERROR
cwe: CWE-78
owasp: A03:2021
```

## 问题说明

攻击者可以通过构造恶意输入执行任意系统命令，获取服务器控制权。

## 违规示例

```java
String cmd = request.getParameter("cmd");
Runtime.getRuntime().exec(cmd);  // 攻击者可传入 rm -rf /
```

## 检测模式

```pattern
Runtime.getRuntime().exec($USER_INPUT)
```

---

# 提权 - ProcessBuilder 使用用户输入

> ProcessBuilder 使用用户输入，存在命令注入风险。

```yaml
id: priv-java-process-builder
languages: [java]
severity: ERROR
cwe: CWE-78
```

## 检测模式

```pattern
new ProcessBuilder($USER_INPUT).start()
```

---

# 提权 - Python os.system 执行用户可控命令

> os.system() 执行用户可控命令，存在命令注入风险。

```yaml
id: priv-python-os-system
languages: [python]
severity: ERROR
cwe: CWE-78
```

## 正确示例

```python
subprocess.run([cmd, arg1, arg2], shell=False, check=True)
```

## 检测模式

```pattern
os.system($USER_INPUT)
```

---

# 提权 - Python eval 执行用户可控代码

> eval() 执行用户可控代码，存在任意代码执行风险。

```yaml
id: priv-python-eval
languages: [python]
severity: ERROR
cwe: CWE-95
```

## 检测模式

```pattern
eval($USER_INPUT)
```

---

# 提权 - Python exec 执行用户可控代码

> exec() 执行用户可控代码，存在任意代码执行风险。

```yaml
id: priv-python-exec
languages: [python]
severity: ERROR
cwe: CWE-95
```

## 检测模式

```pattern
exec($USER_INPUT)
```

---

# 提权 - Python subprocess shell=True

> subprocess 使用 shell=True 执行命令，存在命令注入风险。

```yaml
id: priv-python-subprocess-shell
languages: [python]
severity: ERROR
cwe: CWE-78
```

## 检测模式

```pattern
subprocess.call($CMD, shell=True)
```

---

# 提权 - Python subprocess.run() 使用用户输入

> subprocess.run() 使用用户输入，存在命令注入风险。

```yaml
id: priv-python-subprocess-run
languages: [python]
severity: ERROR
cwe: CWE-78
```

## 违规示例

```python
cmd = request.args.get('cmd')
subprocess.run(cmd, shell=True)  # 危险：命令注入
```

## 正确示例

```python
subprocess.run([cmd, arg1, arg2], shell=False, check=True)
```

## 检测模式

```pattern-regex
subprocess\.run\((?!\s*\[)[^[\];]*shell\s*=\s*True
```

```pattern-not
shlex.quote($ARG)
```

---

# 提权 - Python subprocess.Popen() 使用用户输入

> subprocess.Popen() 使用用户输入，存在命令注入风险。

```yaml
id: priv-python-subprocess-popen
languages: [python]
severity: ERROR
cwe: CWE-78
```

## 违规示例

```python
cmd = request.args.get('cmd')
subprocess.Popen(cmd, shell=True)  # 危险：命令注入
```

## 正确示例

```python
subprocess.Popen([cmd, arg1, arg2], shell=False)
```

## 检测模式

```pattern-regex
subprocess\.Popen\((?!\s*\[)[^[\];]*\)
```

---

# 提权 - Node.js child_process.exec 执行用户可控命令

> child_process.exec() 执行用户可控命令，存在命令注入风险。

```yaml
id: priv-js-child-process
languages: [javascript, typescript]
severity: ERROR
cwe: CWE-78
```

## 正确示例

```javascript
child_process.execFile(cmd, [args])
```

## 检测模式

```pattern
child_process.exec($USER_INPUT, ...)
```

---

# 提权 - Python subprocess.check_output shell=True

> subprocess.check_output() 使用 shell=True 执行命令，存在命令注入风险。

```yaml
id: priv-python-check-output-shell-true
languages: [python]
severity: ERROR
cwe: CWE-78
```

## 违规示例

```python
output = subprocess.check_output(cmd, shell=True)  # 危险：命令注入
```

## 正确示例

```python
output = subprocess.check_output([cmd, arg1, arg2], shell=False)
```

## 检测模式

```pattern
subprocess.check_output($CMD, shell=True, ...)
```

---

# 提权 - Python 解释器参数注入（PowerShell -Command）

> subprocess 调用 PowerShell 并传递动态构建的脚本字符串，解释器参数注入风险。

```yaml
id: priv-python-subprocess-powershell
languages: [python]
severity: WARNING
cwe: CWE-78
```

## 违规示例

```python
import subprocess

def resolve_shortcut(shortcut_path: str) -> str:
    # 危险：PowerShell 脚本由字符串拼接构建
    escaped = shortcut_path.replace("'", "''")
    script = f"$shell.New-Object -ComObject WScript.Shell; $shortcut.CreateShortcut('{escaped}')"
    
    # 攻击面：配置篡改 -> PowerShell 命令注入
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )
```

## 正确示例

```python
import subprocess
import shlex

def resolve_shortcut(shortcut_path: str) -> str:
    # 使用列表形式传递参数，避免解析器执行
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", 
         f"$s = New-Object -ComObject WScript.Shell; $s.CreateShortcut('{shlex.quote(shortcut_path)}').TargetPath"],
        capture_output=True,
        text=True,
    )
```

## 检测模式

```pattern
subprocess.run(["powershell", ...], ...)
```

---

# 提权 - Python 解释器参数注入（Bash -c）

> subprocess 调用 Bash 并传递动态构建的命令字符串，解释器参数注入风险。

```yaml
id: priv-python-subprocess-bash
languages: [python]
severity: WARNING
cwe: CWE-78
```

## 违规示例

```python
import subprocess

def run_bash_cmd(user_input: str):
    # 危险：Bash -c 参数由字符串拼接构建
    cmd = f"echo {user_input} | grep something"
    
    # 攻击面：user_input 包含 `; rm -rf /` -> 任意命令执行
    subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
    )
```

## 正确示例

```python
import subprocess
import shlex

def run_bash_cmd(user_input: str):
    # 使用 shlex.quote() 转义用户输入
    safe_input = shlex.quote(user_input)
    cmd = f"echo {safe_input} | grep something"
    
    subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
    )
```

## 检测模式

```pattern
subprocess.run(["bash", "-c", ...], ...)
```

---

# 提权 - Python 解释器参数注入（Python -c）

> subprocess 调用 Python 解释器并传递动态构建的代码字符串，解释器参数注入风险。

```yaml
id: priv-python-subprocess-python
languages: [python]
severity: WARNING
cwe: CWE-78
```

## 违规示例

```python
import subprocess

def eval_python_expr(expression: str):
    # 危险：Python -c 参数由外部输入构建
    code = f"print({expression})"
    
    # 攻击面：expression = "__import__('os').system('rm -rf /')" -> RCE
    subprocess.run(
        ["python", "-c", code],
        capture_output=True,
        text=True,
    )
```

## 正确示例

```python
# 直接评估，不通过子进程
def eval_python_expr(expression: str):
    # 使用安全的表达式解析器，而非 subprocess + Python -c
    import ast
    tree = ast.parse(expression, mode='eval')
    result = eval(compile(tree, '<string>', 'eval'))
```

## 检测模式

```pattern
subprocess.run(["python", "-c", ...], ...)
```
