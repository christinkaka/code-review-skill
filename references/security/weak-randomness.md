# 弱随机数 - 使用 java.util.Random

> 使用 java.util.Random 生成安全敏感场景的随机值，输出可被预测。

```yaml
id: crypto-weak-random-java
languages: [java]
severity: WARNING
cwe: CWE-330
owasp: A02:2021
```

## 问题说明

`java.util.Random` 使用线性同余生成器（LCG），其输出序列可通过观察少量输出值来预测。
在以下安全敏感场景中，使用可预测的随机数会导致严重安全问题：

- 生成会话令牌
- 生成 CSRF token
- 生成密码重置令牌
- 生成加密密钥
- 生成随机密码

## 违规示例

```java
// 生成会话令牌 - 危险！
Random random = new Random();
String sessionToken = String.valueOf(random.nextLong());

// 生成验证码 - 危险！
int code = new Random().nextInt(999999);
```

## 正确示例

```java
// 使用 SecureRandom（密码学安全伪随机数生成器）
SecureRandom secureRandom = new SecureRandom();
String sessionToken = String.valueOf(secureRandom.nextLong());

// 生成安全的随机字节
byte[] bytes = new byte[32];
secureRandom.nextBytes(bytes);
String token = Base64.getEncoder().encodeToString(bytes);
```

## 检测模式

```pattern
new Random()
```

## 补充说明

`java.util.Random` 在非安全场景（如游戏、模拟、测试数据生成）中使用是可以接受的。
此规则主要针对安全敏感场景，建议人工确认使用上下文。
