# 架构合规规范

> 统一的架构设计规范，确保系统的可维护性、可扩展性和可靠性。

---

# 架构违规 - Controller 层直接依赖 DAO 层

> Controller 层直接依赖 DAO/Repository 层，违反分层架构规范。

```yaml
id: arch-java-layer-violation
languages: [java]
severity: WARNING
category: design
```

## 问题说明

Controller 应通过 Service 层访问数据，直接依赖 DAO 层会导致：
- 业务逻辑泄露到表现层
- 难以进行单元测试
- 违反单一职责原则
- 代码复用性差

## 违规示例

```java
package com.example.controller;

import com.example.dao.UserDao;

@RestController
public class UserController {
    @Autowired
    private UserDao userDao;  // 直接依赖 DAO 层

    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userDao.findById(id);
    }
}
```

## 正确示例

```java
package com.example.controller;

import com.example.service.UserService;

@RestController
public class UserController {
    @Autowired
    private UserService userService;  // 通过 Service 层访问

    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

## 检测模式

```pattern
package com.$ORG.controller;
...
import com.$ORG.dao.$CLASS;
```

```pattern
package com.$ORG.controller;
...
import com.$ORG.repository.$CLASS;
```

---

# 架构违规 - Service 层跨包直接引用

> Service 层之间存在跨包直接引用，可能导致循环依赖。

```yaml
id: arch-java-circular-dep
languages: [java]
severity: WARNING
category: design
```

## 问题说明

Service 层之间的跨包直接引用会导致：
- 循环依赖风险
- 模块耦合度高
- 难以独立测试和部署
- 违反依赖倒置原则

## 违规示例

```java
package com.example.order;

import com.example.user.UserService;  // 跨包直接引用

@Service
public class OrderService {
    @Autowired
    private UserService userService;

    public Order createOrder(OrderRequest request) {
        User user = userService.findById(request.getUserId());
        // ...
    }
}
```

## 正确示例

```java
package com.example.order;

import com.example.user.api.UserApi;  // 通过接口依赖

@Service
public class OrderService {
    @Autowired
    private UserApi userApi;

    public Order createOrder(OrderRequest request) {
        UserDTO user = userApi.findById(request.getUserId());
        // ...
    }
}
```

## 检测模式

```pattern
package com.$ORG.service.$A;
...
import com.$ORG.service.$B.$CLASS;
```

---

# 架构违规 - Entity 模型泄露到 Controller

> Controller 层直接引用 Entity/Model 层对象，存在数据模型泄露风险。

```yaml
id: arch-java-entity-leak
languages: [java]
severity: WARNING
category: design
```

## 问题说明

应将 Entity 转换为 DTO 后再返回给前端，避免：
- 暴露数据库结构
- 返回不必要的敏感字段
- 前后端耦合过紧
- 难以进行数据转换和校验

## 违规示例

```java
package com.example.controller;

import com.example.entity.User;

@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);  // 直接返回 Entity
    }
}
```

## 正确示例

```java
package com.example.controller;

import com.example.dto.UserDTO;

@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public UserDTO getUser(@PathVariable Long id) {
        User user = userService.findById(id);
        return UserMapper.toDTO(user);  // 转换为 DTO
    }
}
```

## 检测模式

```pattern
package com.$ORG.controller;
...
import com.$ORG.entity.$CLASS;
```

```pattern
package com.$ORG.controller;
...
import com.$ORG.model.$CLASS;
```

---

# 架构违规 - 缺少接口抽象层

> 跨模块调用直接使用实现类，未通过接口抽象。

```yaml
id: arch-java-missing-api-layer
languages: [java]
severity: WARNING
category: design
enabled: false
```

> 2026-08-26 禁用（java-sec-code 盲测期间发现）：原 pattern
> `import com.$ORG.$MODULE.$CLASSImpl;` 中 `$CLASSImpl` 含小写字母，
> 不是合法 semgrep 元变量（要求 `$[A-Z_][A-Z_0-9]*`），整条规则自
> 创建起 rc=2 解析失败从未生效，且每次全量扫描产生"Semgrep 异常退出"
> 噪声。正确表达"类名以 Impl 结尾"需要 metavariable-regex
> （DSL 暂不支持），待 DSL 扩展后重新启用。

## 问题说明

跨模块调用应通过接口（API 层）进行，而不是直接依赖实现类。这样可以：
- 降低模块耦合
- 便于独立测试
- 支持多种实现
- 符合依赖倒置原则

## 违规示例

```java
package com.example.order;

import com.example.user.UserServiceImpl;  // 直接依赖实现类

@Service
public class OrderService {
    @Autowired
    private UserServiceImpl userService;  // 应该依赖接口
}
```

## 正确示例

```java
package com.example.order;

import com.example.user.api.UserService;  // 依赖接口

@Service
public class OrderService {
    @Autowired
    private UserService userService;
}
```

## 检测模式

```pattern
import com.$ORG.$MODULE.$CLASSImpl;
```

---

# 架构违规 - 缺少异常处理层

> Controller 层直接抛出异常，未进行统一异常处理。

```yaml
id: arch-java-missing-exception-handler
languages: [java]
severity: WARNING
category: design
```

## 问题说明

应该使用全局异常处理器（`@ControllerAdvice`）统一处理异常，而不是在每个 Controller 中单独处理。这样可以：
- 统一错误响应格式
- 避免重复代码
- 便于错误日志记录
- 提高代码可维护性

## 违规示例

```java
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        try {
            return userService.findById(id);
        } catch (UserNotFoundException e) {
            return new User();  // 返回空对象
        } catch (Exception e) {
            log.error("Error", e);
            return null;  // 返回 null
        }
    }
}
```

## 正确示例

```java
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);  // 直接抛出异常
    }
}

@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(UserNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleUserNotFound(UserNotFoundException e) {
        return ResponseEntity.status(404)
            .body(new ErrorResponse("USER_NOT_FOUND", e.getMessage()));
    }
}
```

## 检测模式

```pattern
@RestController
class $CLASS {
  ...
  try {
    ...
  } catch ($EXCEPTION $E) {
    ...
  }
  ...
}
```

此规则需要人工审核，建议使用全局异常处理器替代。
