# 签名绕过测试案例

## 违规代码 - 使用 MD5withRSA

```java
public byte[] sign(byte[] data, PrivateKey key) throws Exception {
    Signature sig = Signature.getInstance("MD5withRSA");
    sig.initSign(key);
    sig.update(data);
    return sig.sign();
}
```

**预期命中**: `sig-java-weak-algorithm`
**文件类型**: `.java`

---

## 违规代码 - 签名密钥硬编码

```java
public SecretKey getKey() {
    byte[] keyBytes = "my-secret-key-12345678".getBytes();
    return new SecretKeySpec(keyBytes, "HmacSHA256");
}
```

**预期命中**: `sig-java-hardcoded-key`
**文件类型**: `.java`

---

## 违规代码 - Python 使用 MD5

```python
import hashlib

def hash_data(data):
    return hashlib.md5(data.encode()).hexdigest()
```

**预期命中**: `sig-python-weak-hash`
**文件类型**: `.py`

---

## 违规代码 - JWT 未校验时间戳

```python
import jwt

def decode_token(token, secret):
    return jwt.decode(token, secret, algorithms=["HS256"])
```

**预期命中**: `sig-python-no-timestamp`
**文件类型**: `.py`

---

## 正确代码 - 使用 SHA256withRSA

```java
public byte[] sign(byte[] data, PrivateKey key) throws Exception {
    Signature sig = Signature.getInstance("SHA256withRSA");
    sig.initSign(key);
    sig.update(data);
    return sig.sign();
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Python SHA-256

```python
import hashlib

def hash_data(data):
    return hashlib.sha256(data.encode()).hexdigest()
```

**预期命中**: 无
**文件类型**: `.py`
