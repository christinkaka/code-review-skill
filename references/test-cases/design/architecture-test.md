# 架构合规测试案例

## 违规代码 - Controller 直接依赖 DAO

```java
package com.example.controller;

import com.example.dao.UserDao;

@RestController
public class UserController {
    @Autowired
    private UserDao userDao;

    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userDao.findById(id);
    }
}
```

**预期命中**: `arch-java-layer-violation`
**文件类型**: `.java`

---

## 违规代码 - Entity 泄露到 Controller

```java
package com.example.controller;

import com.example.entity.User;

@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

**预期命中**: `arch-java-entity-leak`
**文件类型**: `.java`

---

## 违规代码 - RESTful 命名不规范

```java
@RestController
public class UserController {
    @GetMapping("/getUser")
    public User getUser(@RequestParam Long id) {
        return userService.findById(id);
    }
}
```

**预期命中**: `api-java-rest-naming`
**文件类型**: `.java`

---

## 正确代码 - Controller 通过 Service 层访问

```java
package com.example.controller;

import com.example.dto.UserDTO;

@RestController
public class UserController {
    @Autowired
    private UserService userService;

    @ApiOperation(value = "获取用户信息")
    @GetMapping("/users/{id}")
    public Result<UserDTO> getUser(@PathVariable Long id) {
        return Result.success(userService.findUserDTOById(id));
    }
}
```

**预期命中**: 无
**文件类型**: `.java`
