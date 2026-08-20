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
