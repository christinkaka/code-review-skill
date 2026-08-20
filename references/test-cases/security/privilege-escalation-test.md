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
**文件类型**: `.py`
