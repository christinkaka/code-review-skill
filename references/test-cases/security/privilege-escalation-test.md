# 提权测试案例

## 违规代码 - Java Runtime.exec

```java
public void executeCommand(String userInput) throws IOException {
    Runtime.getRuntime().exec(userInput);
}
```

**预期命中**: `priv-java-runtime-exec`
**文件类型**: `.java`

---

## 违规代码 - Python os.system

```python
import os

def run_command(user_input):
    os.system(user_input)
```

**预期命中**: `priv-python-os-system`
**文件类型**: `.py`

---

## 违规代码 - Python eval

```python
def calculate(expression):
    return eval(expression)
```

**预期命中**: `priv-python-eval`
**文件类型**: `.py`

---

## 违规代码 - Python subprocess shell=True

```python
import subprocess

def run_cmd(cmd):
    subprocess.call(cmd, shell=True)
```

**预期命中**: `priv-python-subprocess-shell`
**文件类型**: `.py`

---

## 违规代码 - Node.js child_process.exec

```javascript
const child_process = require('child_process');

function execute(userInput) {
    child_process.exec(userInput);
}
```

**预期命中**: `priv-js-child-process`
**文件类型**: `.js`

---

## 正确代码 - Python subprocess shell=False

```python
import subprocess

def run_cmd(cmd, args):
    subprocess.run([cmd] + args, shell=False, check=True)
```

**预期命中**: 无

---

## 违规代码 - Python 解释器参数注入（PowerShell -Command）

```python
import subprocess

def resolve_shortcut(shortcut_path: str) -> str:
    escaped = shortcut_path.replace("'", "''")
    script = f"$shell = New-Object -ComObject WScript.Shell"
    
    # 危险：PowerShell 脚本由字符串拼接构建
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )
```

**预期命中**: `priv-python-subprocess-powershell`
**文件类型**: `.py`

---

## 违规代码 - Python 解释器参数注入（Bash -c）

```python
import subprocess

def run_bash_cmd(user_input: str):
    cmd = f"echo {user_input} | grep something"
    
    # 危险：Bash -c 参数由字符串拼接构建
    subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
    )
```

**预期命中**: `priv-python-subprocess-bash`
**文件类型**: `.py`

---

## 违规代码 - Python 解释器参数注入（Python -c）

```python
import subprocess

def eval_python_expr(expression: str):
    code = f"print({expression})"
    
    # 危险：Python -c 参数由外部输入构建
    subprocess.run(
        ["python", "-c", code],
        capture_output=True,
        text=True,
    )
```

**预期命中**: `priv-python-subprocess-python-c`
**文件类型**: `.py`
**文件类型**: `.py`
