# 数据库设计规范

> 统一的数据库操作规范，确保数据一致性、性能和安全性。

---

# 数据库规范 - 多次写操作缺少事务注解

> 方法中执行多次数据库写操作但未添加 @Transactional，可能导致数据不一致。

```yaml
id: db-java-missing-transaction
languages: [java]
severity: WARNING
category: design
```

## 问题说明

当方法中执行多次数据库写操作时，必须使用事务确保原子性。否则，如果中间某步失败，会导致数据不一致。

## 违规示例

```java
@Service
public class OrderService {
    @Autowired
    private OrderRepository orderRepo;
    @Autowired
    private InventoryRepository inventoryRepo;

    public void createOrder(Order order) {
        orderRepo.save(order);  // 步骤 1：创建订单
        inventoryRepo.deduct(order.getItemId(), order.getQuantity());  // 步骤 2：扣减库存
        // 如果步骤 2 失败，订单已创建但库存未扣减，数据不一致
    }
}
```

## 正确示例

```java
@Service
public class OrderService {
    @Autowired
    private OrderRepository orderRepo;
    @Autowired
    private InventoryRepository inventoryRepo;

    @Transactional
    public void createOrder(Order order) {
        orderRepo.save(order);
        inventoryRepo.deduct(order.getItemId(), order.getQuantity());
        // 如果任何一步失败，整个事务回滚，保证数据一致性
    }
}
```

## 检测模式

```pattern
public void $METHOD(...) {
  ...
  $REPO1.save(...);
  ...
  $REPO2.$OP(...);
  ...
}
```

```pattern-not
@Transactional
public void $METHOD(...) {
  ...
}
```

---

# 数据库规范 - 循环中执行数据库查询（N+1 问题）

> 循环中执行数据库查询严重影响性能。

```yaml
id: db-java-n-plus-one
languages: [java]
severity: WARNING
category: design
```

## 问题说明

N+1 查询问题是指在循环中执行数据库查询，导致查询次数与数据量成正比。例如：
- 1 次查询获取订单列表
- N 次查询获取每个订单的详情

这会导致严重的性能问题，特别是数据量大时。

## 违规示例

```java
public List<OrderDetail> getOrderDetails(List<Order> orders) {
    List<OrderDetail> details = new ArrayList<>();
    for (Order order : orders) {
        OrderDetail detail = new OrderDetail();
        detail.setOrder(order);
        detail.setItems(itemRepo.findByOrderId(order.getId()));  // N+1 查询
        details.add(detail);
    }
    return details;
}
```

## 正确示例

```java
public List<OrderDetail> getOrderDetails(List<Order> orders) {
    // 批量查询所有订单的商品
    List<Long> orderIds = orders.stream()
        .map(Order::getId)
        .collect(Collectors.toList());
    
    Map<Long, List<Item>> itemsByOrderId = itemRepo.findByOrderIdIn(orderIds)
        .stream()
        .collect(Collectors.groupingBy(Item::getOrderId));
    
    return orders.stream()
        .map(order -> {
            OrderDetail detail = new OrderDetail();
            detail.setOrder(order);
            detail.setItems(itemsByOrderId.getOrDefault(order.getId(), Collections.emptyList()));
            return detail;
        })
        .collect(Collectors.toList());
}
```

## 检测模式

```pattern
for ($TYPE $ITEM : $LIST) {
  ...
  $REPO.$METHOD($ITEM.getId());
  ...
}
```

---

# 数据库规范 - 使用 SELECT * 查询

> 使用 SELECT * 查询所有字段，影响性能和可维护性。

```yaml
id: db-java-select-star
languages: [java]
severity: WARNING
category: design
```

## 问题说明

使用 `SELECT *` 会：
- 查询不必要的字段，浪费网络带宽
- 表结构变更时可能导致代码错误
- 无法利用覆盖索引优化

## 违规示例

```java
@Query("SELECT * FROM users WHERE status = ?1")
List<User> findActiveUsers(String status);
```

## 正确示例

```java
@Query("SELECT id, username, email FROM users WHERE status = ?1")
List<User> findActiveUsers(String status);
```

## 检测模式

```pattern-regex
@Query\(\s*"SELECT\s+\*\s+FROM
```

---

# 数据库规范 - 缺少索引的查询条件

> 查询条件中的字段缺少索引，影响查询性能。

```yaml
id: db-java-missing-index
languages: [java]
severity: INFO
category: design
```

## 问题说明

在 WHERE 子句中使用的字段应该有索引，否则会导致全表扫描，严重影响查询性能。

## 建议

- 为常用的查询条件字段添加索引
- 为外键字段添加索引
- 为排序字段添加索引
- 定期分析慢查询日志，优化索引

## 检测模式

此规则需要人工审核，建议：
1. 分析慢查询日志
2. 使用 EXPLAIN 分析查询计划
3. 为高频查询条件添加索引

---

# 数据库规范 - 批量操作未使用批量 API

> 循环中逐条执行数据库操作，未使用批量 API。

```yaml
id: db-java-missing-batch
languages: [java]
severity: WARNING
category: design
```

## 问题说明

循环中逐条执行数据库操作会导致：
- 大量的网络往返
- 事务开销增加
- 性能严重下降

## 违规示例

```java
public void saveUsers(List<User> users) {
    for (User user : users) {
        userRepository.save(user);  // 逐条保存
    }
}
```

## 正确示例

```java
public void saveUsers(List<User> users) {
    userRepository.saveAll(users);  // 批量保存
}
```

## 检测模式

```pattern
for ($TYPE $ITEM : $LIST) {
  ...
  $REPO.save($ITEM);
  ...
}
```

```pattern-not
$REPO.saveAll($LIST);
```

---

# 数据库规范 - SQL 注入风险

> 字符串拼接构建 SQL 语句，存在 SQL 注入风险。

```yaml
id: db-java-sql-injection
languages: [java]
severity: ERROR
category: design
```

## 问题说明

SQL 注入是最常见的安全漏洞之一，攻击者可以通过构造恶意输入执行任意 SQL 命令。

## 违规示例

```java
public User findUser(String username) {
    String sql = "SELECT * FROM users WHERE username = '" + username + "'";
    return jdbcTemplate.queryForObject(sql, new UserRowMapper());
}
```

## 正确示例

```java
public User findUser(String username) {
    String sql = "SELECT * FROM users WHERE username = ?";
    return jdbcTemplate.queryForObject(sql, new UserRowMapper(), username);
}
```

## 检测模式

```pattern
"SELECT ... " + $USER_INPUT + " ..."
```

```pattern
"INSERT ... " + $USER_INPUT + " ..."
```

```pattern
"UPDATE ... " + $USER_INPUT + " ..."
```

```pattern
"DELETE ... " + $USER_INPUT + " ..."
```
