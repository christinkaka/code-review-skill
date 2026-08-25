# 签名绕过 - 使用不安全的签名算法

> 使用 MD5withRSA 签名算法，MD5 已被证明不安全。

```yaml
id: sig-java-weak-algorithm
languages: [java]
severity: ERROR
cwe: CWE-328
```

## 正确示例

```java
Signature sig = Signature.getInstance("SHA256withRSA");
```

## 检测模式

```pattern
Signature.getInstance("MD5withRSA")
```

---

# 签名绕过 - 签名验证流程不完整

> 签名验证流程不完整，缺少 verify() 调用或结果检查。

```yaml
id: sig-java-verify-skip
languages: [java]
severity: ERROR
cwe: CWE-345
```

## 问题说明

初始化了签名验证但未检查 verify() 的返回值，等同于没有验证。

## 检测模式

```pattern
Signature $SIG = ...;
...
$SIG.initVerify(...);
...
$SIG.update(...);
```

```pattern-not
Signature $SIG = ...;
...
$SIG.initVerify(...);
...
$SIG.update(...);
...
if (!$SIG.verify(...)) { ... }
```

---

# 签名绕过 - 协议版本跳过签名验证（控制流漏洞）

> 基于协议版本的条件分支跳过签名验证，攻击者可伪造请求。

```yaml
id: sig-bypass-version-skip
languages: [java]
severity: CRITICAL
cwe: CWE-345
```

## 问题说明

当代码根据协议版本号进行条件分支，且低版本路径不包含签名验证逻辑时，
攻击者可以设置低版本号来完全绕过签名校验。这是一种控制流漏洞，
验证逻辑被条件分支跳过而非正确执行。

常见的等价模式包括：
- `if (version == 1)` -- 显式匹配 V1
- `if (checkVersionInt < 2)` -- 数值比较跳过 V1
- `if (version <= 1)` -- 小于等于比较
- `if (version != 2)` -- 不等于比较

## 违规示例

```java
// 模式 1: 显式版本比较
if (version == 1) {
    // V1 协议：直接处理请求，跳过签名验证
    processRequest(data);
} else {
    // V2 协议：验证签名
    if (!verifySignature(data, signature)) {
        throw new SecurityException("Invalid signature");
    }
    processRequest(data);
}

// 模式 2: 数值比较（等价于模式 1）
int checkVersionInt = Integer.parseInt(checkVersion.substring(1));
if (checkVersionInt < 2) {
    super.doPost(pRequest, pResponse);  // 跳过签名验证
    return;
} else {
    if (!checkHeaderSign(...)) return;
}
```

## 正确示例

```java
// 所有协议版本都必须验证签名
if (!verifySignature(data, signature)) {
    throw new SecurityException("Invalid signature");
}

if (version == 1) {
    processRequestV1(data);
} else {
    processRequestV2(data);
}
```

## 检测模式

> 2026-08-25 盲评修正：原 `if ($VAR == 1)` 类 pattern 匹配一切 `== 1`
> 比较（实测 `size() == 1` 误报 6/6，CRITICAL 级语义错配）。漏洞的
> 真实结构需双证据：**变量名含版本语义 + 分支内提前 return**（低版本
> 短路返回，跳过后续验证逻辑）。

```pattern-regex
\bif\s*\(\s*\w*(?:ersion|ERSION)\w*\s*(?:==|!=|<|<=)\s*\d+\s*\)\s*\{[^{}]*\breturn\b
```

---

# 签名绕过 - 版本检查条件分支（正则补充）

> 版本检查条件分支可能跳过签名验证，需要人工确认。

```yaml
id: sig-bypass-version-check-regex
languages: [java]
severity: WARNING
cwe: CWE-345
```

## 检测模式

使用正则匹配所有包含版本变量名和数值比较的 if 条件。

```pattern
if (checkVersionInt < 2) {
  ...
}
```

---

# 签名绕过 - 签名密钥硬编码

> 签名密钥硬编码在源码中，存在密钥泄露风险。

```yaml
id: sig-java-hardcoded-key
languages: [java]
severity: ERROR
cwe: CWE-798
```

## 检测模式

```pattern
SecretKeySpec $KEY = new SecretKeySpec("...".getBytes(), ...);
```

```pattern
$KEY_BYTES = "...".getBytes();
...
new SecretKeySpec($KEY_BYTES, ...);
```

---

# 签名绕过 - Python 签名验证被显式禁用

> 签名验证被显式禁用（verify=False），存在伪造风险。

```yaml
id: sig-python-verify-false
languages: [python]
severity: ERROR
cwe: CWE-345
```

## 检测模式

```pattern
$VERIFIER.verify(..., verify=False)
```

---

# 签名绕过 - Python 使用 MD5 进行签名校验

> 使用 MD5 进行签名/校验，MD5 存在碰撞攻击风险。

```yaml
id: sig-python-weak-hash
languages: [python]
severity: WARNING
cwe: CWE-328
```

## 正确示例

```python
hashlib.sha256(data)
```

## 检测模式

```pattern
hashlib.md5(...)
```

---

# 签名绕过 - JWT 解码未强制要求时间戳

> JWT 解码未强制要求 exp/iat 字段，可能接受过期或无时间戳的 token。

```yaml
id: sig-python-no-timestamp
languages: [python]
severity: WARNING
cwe: CWE-345
```

## 检测模式

```pattern
jwt.decode($TOKEN, $KEY, algorithms=[...])
```

```pattern-not
jwt.decode($TOKEN, $KEY, algorithms=[...], options={"require": ["exp", "iat"]})
```
