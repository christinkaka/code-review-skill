# 空指针防护测试案例

## 违规代码 - Java 链式调用未判空

```java
public String getCityName(User user) {
    return user.getAddress().getCity().getName();
}
```

**预期命中**: `null-java-method-chain`
**文件类型**: `.java`

---

## 违规代码 - Java Map.get() 直接调用方法

```java
public void processConfig(Map<String, String> config) {
    String value = config.get("key").trim();
    System.out.println(value);
}
```

**预期命中**: `null-java-collection-get`
**文件类型**: `.java`

---

## 违规代码 - Java Integer 自动拆箱

```java
public int getCount(Map<String, Integer> map) {
    Integer count = map.get("count");
    return count;  // 自动拆箱，若 count 为 null 则 NPE
}
```

**预期命中**: `null-java-unwrap-boxed`
**文件类型**: `.java`

---

## 正确代码 - 使用 Optional 链式调用

```java
public String getCityName(User user) {
    return Optional.ofNullable(user)
        .map(User::getAddress)
        .map(Address::getCity)
        .map(City::getName)
        .orElse("Unknown");
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Map.getOrDefault

```java
public void processConfig(Map<String, String> config) {
    String value = config.getOrDefault("key", "").trim();
    System.out.println(value);
}
```

**预期命中**: 无
**文件类型**: `.java`
