# 越权访问测试案例

## 违规代码 - Controller 缺少鉴权注解

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

**预期命中**: `auth-java-missing-annotation`
**文件类型**: `.java`

---

## 违规代码 - 水平越权（未校验资源归属）

```java
@GetMapping("/order")
public Order getOrder(@RequestParam String orderId) {
    return orderRepository.findById(orderId);
}
```

**预期命中**: `auth-java-horizontal-escalation`
**文件类型**: `.java`

---

## 违规代码 - Flask 路由缺少登录校验

```python
@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    return render_template('profile.html', user=get_user(user_id))
```

**预期命中**: `auth-python-missing-login-required`
**文件类型**: `.py`

---

## 正确代码 - Controller 使用 @PreAuthorize

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @PreAuthorize("hasRole('USER')")
    @ApiOperation(value = "获取用户信息")
    @GetMapping("/{id}")
    public Result<User> getUser(@PathVariable Long id) {
        return Result.success(userService.findById(id));
    }
}
```

**预期命中**: 无
**文件类型**: `.java`

---

## 正确代码 - Flask 使用 @login_required

```python
from flask_login import login_required

@app.route('/profile')
@login_required
def profile():
    user_id = session.get('user_id')
    return render_template('profile.html', user=get_user(user_id))
```

**预期命中**: 无
**文件类型**: `.py`
