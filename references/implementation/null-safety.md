# 空指针 - Java 链式调用未判空

> 链式调用未做空值检查，任一环节返回 null 将导致 NPE。

```yaml
id: null-java-method-chain
languages: [java]
severity: WARNING
category: implementation
```

## 违规示例

```java
String city = user.getAddress().getCity().getName();
```

## 正确示例

```java
String city = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .map(City::getName)
    .orElse("Unknown");
```

## 检测模式

```pattern
$OBJ.$A().$B().$C()
```

---

# 空指针 - Java Map.get() 直接调用方法

> Map.get() 可能返回 null，直接调用方法会导致 NPE。

```yaml
id: null-java-collection-get
languages: [java]
severity: WARNING
category: implementation
```

## 正确示例

```java
String value = map.getOrDefault(key, "default");
value.toString();
```

## 检测模式

```pattern
$MAP.get($KEY).$METHOD(...)
```

```pattern-not
Paths.get(...).$METHOD(...)
```

```pattern-not
Optional.get(...).$METHOD(...)
```

---

# 空指针 - Java Integer 自动拆箱

> Integer 自动拆箱为 int，若 Integer 为 null 将抛出 NullPointerException。

```yaml
id: null-java-unwrap-boxed
languages: [java]
severity: WARNING
category: implementation
```

## 违规示例

```java
Integer count = getCount();
int c = count;  // 若 count 为 null，NPE
```

## 检测模式

```pattern
int $X = $INTEGER_OBJ;
```

```pattern
Integer $VAR = ...;
...
return $VAR;
```
