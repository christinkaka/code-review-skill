# 用户输入流入文件路径操作（目录穿越）

## 问题描述

当 HTTP 请求参数、上传文件的原始文件名这类用户可控数据，经过赋值或拼接后流入
文件读写操作时，攻击者可以构造 `../` 读取或覆盖服务器上的任意文件（如
`/etc/passwd`、crontab）。这类漏洞的关键在于"数据从哪来、流到哪里去"，
单看某一行的代码形态无法判断。

## 检测方式

数据流追踪（污点分析）：跟踪用户输入如何传播到文件操作，只报真实的数据流，
常量拼接、以及经过净化处理（basename、路径规范化）的场景不算违规。

## 违规场景

- 用户通过请求参数传入文件名或路径，代码用它构造 File 对象或打开文件流
- 文件上传场景直接使用 getOriginalFilename() 的返回值作为保存路径
- 上述数据经过中间变量赋值、字符串拼接后到达文件操作，同样违规

## 安全做法

- 取文件名部分（basename，如 getName()）再拼接固定目录，杜绝目录部分可控
- 对路径做规范化（normalize/getCanonicalPath）并校验仍在基准目录内
- 用白名单正则校验文件名后才使用

## 严重等级

CRITICAL - 可导致任意文件读写，覆盖系统关键文件实现持久化攻击

## 示例代码

### 违规代码

```java
import java.io.File;
import java.nio.file.Files;
import javax.servlet.http.HttpServletRequest;

class Download {
    String read(HttpServletRequest request) throws Exception {
        String userPath = request.getParameter("path");
        File f = new File("/data", userPath);
        return new String(Files.readAllBytes(f.toPath()));
    }
}
```

### 安全代码

```java
import java.io.File;
import java.nio.file.Files;
import javax.servlet.http.HttpServletRequest;

class Download {
    String read(HttpServletRequest request) throws Exception {
        String userPath = request.getParameter("path");
        String nameOnly = new File(userPath).getName();
        File f = new File("/data", nameOnly);
        return new String(Files.readAllBytes(f.toPath()));
    }
}
```
