# 目录穿越测试案例

## 案例 1: 文件下载接口 - 读穿越

### 违规代码 - Java 文件下载未校验路径

```java
@GetMapping("/download")
public void downloadFile(@RequestParam String filename, HttpServletResponse response) throws IOException {
    // 直接使用用户输入的文件名，未校验路径
    File file = new File("/var/www/uploads", filename);
    
    // 攻击者可传入 ../../../etc/passwd 读取系统文件
    if (file.exists()) {
        response.setContentType("application/octet-stream");
        response.setHeader("Content-Disposition", "attachment; filename=\"" + file.getName() + "\"");
        Files.copy(file.toPath(), response.getOutputStream());
    }
}
```

**预期命中**: `path-read-traversal`
**严重等级**: ERROR
**攻击向量**: `GET /download?filename=../../../etc/passwd`
**风险**: 读取 `/etc/passwd`、数据库配置等敏感文件

---

## 案例 2: 文件上传接口 - 写穿越（高危）

### 违规代码 - Spring Boot 文件上传未校验文件名

```java
@PostMapping("/upload")
public String uploadFile(@RequestParam("file") MultipartFile file) throws IOException {
    String uploadDir = "/var/www/uploads";
    
    // 直接使用原始文件名，未校验
    String filename = file.getOriginalFilename();
    File dest = new File(uploadDir, filename);
    
    // 攻击者可上传文件，文件名为 ../../../var/spool/cron/crontabs/root
    // 文件内容为定时任务，实现持久化攻击
    file.transferTo(dest);
    
    return "success";
}
```

**预期命中**: `path-upload-traversal`, `path-write-traversal`
**严重等级**: CRITICAL
**攻击向量**: 
```bash
curl -X POST http://target/upload \
  -F "file=@malicious.sh;filename=../../../var/spool/cron/crontabs/root"
```
**风险**: 覆盖 crontab 添加定时任务，获取持久化权限

---

## 案例 3: 配置加载 - 配置穿越

### 违规代码 - 动态加载配置文件

```java
@GetMapping("/config")
public String loadConfig(@RequestParam String configName) throws IOException {
    // 动态加载配置文件，路径未校验
    String configPath = "/etc/myapp/" + configName;
    
    // 攻击者可传入 ../../database.yml 读取数据库配置
    Properties props = new Properties();
    props.load(new FileInputStream(configPath));
    
    return props.getProperty("db.password");
}
```

**预期命中**: `path-config-traversal`
**严重等级**: HIGH
**攻击向量**: `GET /config?configName=../../database.yml`
**风险**: 读取数据库密码、API 密钥等敏感配置

---

## 案例 4: 日志文件写入 - 日志穿越

### 违规代码 - 动态日志文件路径

```java
@PostMapping("/log")
public void writeLog(@RequestParam String logFile, @RequestParam String message) throws IOException {
    // 日志文件路径使用用户输入
    String logPath = "/var/log/myapp/" + logFile;
    
    // 攻击者可传入 ../../../etc/passwd 覆盖系统文件
    // 或传入 ../../app.log 注入恶意日志
    try (FileWriter writer = new FileWriter(logPath, true)) {
        writer.write(message + "\n");
    }
}
```

**预期命中**: `path-log-traversal`, `path-write-traversal`
**严重等级**: HIGH
**攻击向量**: 
```bash
POST /log?logFile=../../../etc/crontab&message=* * * * * /bin/bash -c 'reverse_shell'
```
**风险**: 覆盖系统日志隐藏攻击痕迹，或覆盖 crontab 执行恶意命令

---

## 案例 5: Python Flask 文件上传 - 写穿越

### 违规代码 - Flask 文件上传未校验

```python
from flask import Flask, request
import os

app = Flask(__name__)
UPLOAD_DIR = '/var/www/uploads'

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filename = file.filename  # 未校验文件名
    
    # 攻击者可传入 ../../../root/.ssh/authorized_keys
    # 注入 SSH 公钥获取远程访问权限
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)
    
    return "success"
```

**预期命中**: `path-upload-traversal`, `path-write-traversal`
**严重等级**: CRITICAL
**攻击向量**:
```bash
curl -X POST http://target/upload \
  -F "file=@attacker.pub;filename=../../../root/.ssh/authorized_keys"
```
**风险**: 覆盖 SSH 公钥，获取远程访问权限

---

## 案例 6: Node.js 文件写入 - 写穿越

### 违规代码 - Express 文件写入未校验

```javascript
const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const UPLOAD_DIR = '/var/www/uploads';

app.post('/save', (req, res) => {
    const filename = req.body.filename;
    const content = req.body.content;
    
    // 未校验文件名，攻击者可传入 ../../../etc/hosts
    const filepath = path.join(UPLOAD_DIR, filename);
    fs.writeFileSync(filepath, content);
    
    res.send("success");
});
```

**预期命中**: `path-write-traversal`
**严重等级**: CRITICAL
**攻击向量**:
```bash
curl -X POST http://target/save \
  -H "Content-Type: application/json" \
  -d '{"filename":"../../../etc/hosts","content":"127.0.0.1 attacker.com"}'
```
**风险**: 覆盖 `/etc/hosts` 进行 DNS 劫持

---

## 案例 7: 正确的文件上传实现

### 正确代码 - 文件名白名单 + 路径规范化

```java
@PostMapping("/upload")
public String uploadFile(@RequestParam("file") MultipartFile file) throws IOException {
    String uploadDir = "/var/www/uploads";
    String filename = file.getOriginalFilename();
    
    // 1. 文件名白名单校验（只允许字母、数字、下划线、点）
    if (filename == null || !filename.matches("^[a-zA-Z0-9_\\.]+$")) {
        throw new SecurityException("Invalid filename");
    }
    
    // 2. 文件类型校验
    String ext = filename.substring(filename.lastIndexOf('.') + 1).toLowerCase();
    List<String> allowedTypes = Arrays.asList("jpg", "png", "pdf", "doc");
    if (!allowedTypes.contains(ext)) {
        throw new SecurityException("Invalid file type");
    }
    
    // 3. 生成安全的文件名（UUID + 扩展名）
    String safeFilename = UUID.randomUUID().toString() + "." + ext;
    
    // 4. 路径规范化 + 边界校验
    Path baseDir = Paths.get(uploadDir).toAbsolutePath().normalize();
    Path target = baseDir.resolve(safeFilename).normalize();
    
    if (!target.startsWith(baseDir)) {
        throw new SecurityException("Path traversal detected");
    }
    
    file.transferTo(target.toFile());
    return "success";
}
```

**预期命中**: 无
**说明**: 正确实现了文件名白名单、类型校验、UUID 重命名、路径规范化

---

## 案例 8: 系统关键文件引用检测

### 违规代码 - 直接引用系统关键文件

```java
public void backupSystemFiles() throws IOException {
    // 直接引用系统关键文件，应使用白名单或配置化
    String[] systemFiles = {
        "/etc/passwd",
        "/etc/shadow",
        "/etc/crontab",
        "/etc/ssh/sshd_config"
    };
    
    for (String file : systemFiles) {
        // 备份逻辑...
    }
}
```

**预期命中**: `path-system-files`
**严重等级**: WARNING
**说明**: 代码中直接引用系统关键文件路径，应检查是否有用户输入影响

---

## 案例 9: 路径穿越模式检测

### 违规代码 - 包含路径穿越模式

```java
public String resolvePath(String userInput) {
    // 代码中包含路径穿越模式，可能是硬编码或注释
    String pattern = "../";  // 应检查是否有用户输入拼接
    
    if (userInput.contains(pattern)) {
        // 简单的穿越检测，但不够完善
        throw new SecurityException("Path traversal detected");
    }
    
    return userInput;
}
```

**预期命中**: `path-traversal-pattern`
**严重等级**: WARNING
**说明**: 代码中包含路径穿越模式，应检查是否有用户输入影响

---

## 案例 10: Python 文件读取 - 读穿越

### 违规代码 - Python 文件读取未校验

```python
from flask import Flask, request, send_file
import os

app = Flask(__name__)

@app.route('/read')
def read_file():
    filename = request.args.get('filename')
    
    # 直接使用用户输入，未校验路径
    # 攻击者可传入 ../../../etc/passwd
    filepath = os.path.join('/var/www/data', filename)
    
    if os.path.exists(filepath):
        return send_file(filepath)
    else:
        return "File not found", 404
```

**预期命中**: `path-read-traversal`
**严重等级**: ERROR
**攻击向量**: `GET /read?filename=../../../etc/passwd`
**风险**: 读取系统敏感文件
