# API 设计规范

> 统一的 API 设计规范，确保接口的一致性、安全性和可维护性。

---

# API 规范 - RESTful 接口命名不规范

> GET 接口应使用名词复数形式，不应使用动词前缀。

```yaml
id: api-java-rest-naming
languages: [java]
severity: WARNING
category: design
```

## 问题说明

RESTful API 应遵循以下命名规范：
- 使用名词复数表示资源集合（如 `/users`、`/orders`）
- 避免使用动词前缀（如 `/getUser`、`/createOrder`）
- HTTP 方法本身已表达操作语义（GET=查询、POST=创建、PUT=更新、DELETE=删除）

## 违规示例

```java
@GetMapping("/getUser")
public User getUser(@RequestParam Long id) {
    return userService.findById(id);
}

@PostMapping("/createOrder")
public Order createOrder(@RequestBody OrderRequest request) {
    return orderService.create(request);
}
```

## 正确示例

```java
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) {
    return userService.findById(id);
}

@PostMapping("/orders")
public Order createOrder(@RequestBody OrderRequest request) {
    return orderService.create(request);
}
```

## 检测模式

```pattern-regex
@(Get|Post|Put|Delete)Mapping\("/(get|create|update|delete)[^"]*"\)
```

---

# API 规范 - Controller 返回值未使用统一包装类

> Controller 返回值未使用统一包装类（如 Result<T>），建议统一响应格式。

```yaml
id: api-java-missing-response-wrapper
languages: [java]
severity: INFO
category: design
```

## 问题说明

统一的响应格式有助于：
- 前端统一处理响应
- 标准化错误码和错误信息
- 便于日志记录和监控

## 违规示例

```java
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

## 正确示例

```java
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public Result<User> getUser(@PathVariable Long id) {
        User user = userService.findById(id);
        return Result.success(user);
    }
}
```

## 检测模式

```pattern
@RestController
class $CLASS {
  ...
  public $RETURNTYPE $METHOD(...) {
    ...
    return $DATA;
  }
}
```

```pattern-not
@RestController
class $CLASS {
  ...
  public Result<$TYPE> $METHOD(...) {
    ...
    return Result.success(...);
  }
}

```pattern-not
@RestController
class $CLASS {
  ...
  @PreAuthorize(...)
  ...
  public $RETURNTYPE $METHOD(...) {
    ...
    return $DATA;
  }
}

---

# API 规范 - @RequestBody 缺少 @Valid 注解

> @RequestBody 参数缺少 @Valid 注解，入参校验未启用。

```yaml
id: api-java-missing-validation
languages: [java]
severity: WARNING
category: design
```

## 问题说明

使用 `@Valid` 注解可以启用 Bean Validation，自动校验请求参数的合法性，避免手动编写校验逻辑。

## 违规示例

```java
@PostMapping("/users")
public Result<Void> createUser(@RequestBody CreateUserRequest request) {
    userService.create(request);
    return Result.success();
}
```

## 正确示例

```java
@PostMapping("/users")
public Result<Void> createUser(@Valid @RequestBody CreateUserRequest request) {
    userService.create(request);
    return Result.success();
}
```

## 检测模式

```pattern
@PostMapping(...)
public $RETURNTYPE $METHOD(@RequestBody $TYPE $PARAM) {
  ...
}
```

```pattern-not
@PostMapping(...)
public $RETURNTYPE $METHOD(@Valid @RequestBody $TYPE $PARAM) {
  ...
}
```

---

# API 规范 - 缺少 API 文档注解

> Controller 方法缺少 Swagger/OpenAPI 文档注解，影响接口可读性。

```yaml
id: api-java-missing-doc
languages: [java]
severity: INFO
category: design
enabled: false
```

## 问题说明

API 文档注解（如 `@ApiOperation`、`@ApiParam`）有助于：
- 自动生成 API 文档
- 提高接口可读性
- 便于前后端协作

## 违规示例

```java
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) {
    return userService.findById(id);
}
```

## 正确示例

```java
@ApiOperation(value = "获取用户信息", notes = "根据用户 ID 查询用户详情")
@GetMapping("/users/{id}")
public User getUser(
    @ApiParam(value = "用户 ID", required = true) 
    @PathVariable Long id) {
    return userService.findById(id);
}
```

## 检测模式

```pattern
@GetMapping(...)
public $RETURNTYPE $METHOD(...) {
  ...
}
```

```pattern-not
@ApiOperation(...)
@GetMapping(...)
public $RETURNTYPE $METHOD(...) {
  ...
}
```

---

# API 规范 - 接口缺少版本控制

> API 接口缺少版本号，不利于后续升级和维护。

```yaml
id: api-java-missing-version
languages: [java]
severity: INFO
category: design
```

## 问题说明

API 版本控制有助于：
- 平滑升级接口
- 保持向后兼容
- 支持多版本并存

## 违规示例

```java
@RestController
@RequestMapping("/users")
public class UserController {
    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

## 正确示例

```java
@RestController
@RequestMapping("/api/v1/users")
public class UserController {
    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

## 检测模式

```pattern
@RestController
@RequestMapping("/$RESOURCE")
class $CLASS {
  ...
}
```

```pattern-not
@RestController
@RequestMapping("/api/v$VERSION/$RESOURCE")
class $CLASS {
  ...
}
```
