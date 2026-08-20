# API 设计测试案例

## 违规代码 - @RequestBody 缺少 @Valid

```java
@PostMapping("/users")
public Result<Void> createUser(@RequestBody CreateUserRequest request) {
    userService.create(request);
    return Result.success();
}
```

**预期命中**: `api-java-missing-validation`
**文件类型**: `.java`

---

## 违规代码 - 返回值未使用统一包装

```java
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

**预期命中**: `api-java-missing-response-wrapper`
**文件类型**: `.java`

---

## 正确代码 - 使用 @Valid + 统一返回包装

```java
@RestController
public class UserController {
    @PostMapping("/users")
    public Result<Void> createUser(@Valid @RequestBody CreateUserRequest request) {
        userService.create(request);
        return Result.success();
    }
}
```

**预期命中**: 无
**文件类型**: `.java`
