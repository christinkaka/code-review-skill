# 越权 - Controller 方法缺少鉴权注解

> Controller 方法缺少鉴权注解，可能存在未授权访问风险。

```yaml
id: auth-java-missing-annotation
languages: [java]
severity: WARNING
cwe: CWE-862
owasp: A01:2021
```

## 问题说明

Spring MVC Controller 方法如果没有 `@PreAuthorize`、`@Secured` 或 `@RolesAllowed` 注解，且没有全局拦截器覆盖，则任何人都可以访问该接口。

## 检测模式

```pattern
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @GetMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @PostMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern-not
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @PreAuthorize(...)
  @GetMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern-not
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @PreAuthorize(...)
  @PostMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern-not
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @Secured(...)
  @GetMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern-not
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @Secured(...)
  @PostMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern-not
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @RolesAllowed(...)
  @GetMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

```pattern-not
@RestController
@RequestMapping(...)
class $CLASS {
  ...
  @RolesAllowed(...)
  @PostMapping(...)
  public $RETURNTYPE $METHOD(...) {
    ...
  }
  ...
}
```

---

# 越权 - 水平越权（未校验资源归属）

> 接口通过请求参数直接查询资源，未校验当前用户对该资源的所有权。

```yaml
id: auth-java-horizontal-escalation
languages: [java]
severity: WARNING
cwe: CWE-862
```

## 问题说明

攻击者可以修改请求参数中的 ID（如 `?orderId=100`），访问其他用户的资源。

## 违规示例

```java
@GetMapping("/order")
public Order getOrder(@RequestParam String orderId) {
    return orderRepository.findById(orderId);  // 未校验当前用户是否是订单所有者
}
```

## 正确示例

```java
@GetMapping("/order")
public Order getOrder(@RequestParam String orderId, Authentication auth) {
    Order order = orderRepository.findById(orderId);
    if (!order.getUserId().equals(auth.getName())) {
        throw new AccessDeniedException("无权访问");
    }
    return order;
}
```

## 检测模式

```pattern
@GetMapping(...)
public $RETURNTYPE $METHOD(@RequestParam(...) String $ID) {
  ...
  $REPOSITORY.findById($ID);
  ...
}
```

---

# 越权 - IDOR 直接对象引用

> 直接使用请求中的 ID 执行删除操作，未校验资源归属。

```yaml
id: auth-java-idor-direct-ref
languages: [java]
severity: WARNING
cwe: CWE-862
```

## 检测模式

```pattern
$SERVICE.delete($REQUEST.getId());
```

```pattern-not
if ($REQUEST.getId().equals($CURRENT_USER.getId())) { ... }
```

---

# 越权 - Flask 路由缺少登录校验

> Flask 路由缺少 @login_required 装饰器，可能存在未授权访问。

```yaml
id: auth-python-missing-login-required
languages: [python]
severity: WARNING
cwe: CWE-862
```

## 检测模式

```pattern
@app.route(...)
def $FUNC(...):
  ...
  session.$METHOD(...)
  ...
```

```pattern-not
@login_required
@app.route(...)
def $FUNC(...):
  ...
  session.$METHOD(...)
  ...
```

---

# 越权 - Django CBV 未继承 LoginRequiredMixin

> Django CBV 未继承 LoginRequiredMixin，可能存在未授权访问。

```yaml
id: auth-python-django-mixin
languages: [python]
severity: WARNING
cwe: CWE-862
```

## 检测模式

```pattern
class $VIEW(View):
  ...
```

```pattern-not
class $VIEW(LoginRequiredMixin, View):
  ...
```
