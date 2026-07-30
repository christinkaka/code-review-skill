# 数据库规范测试案例

## 违规代码 - 多次写操作缺少 @Transactional

```java
@Service
public class OrderService {
    @Autowired
    private OrderRepository orderRepo;
    @Autowired
    private InventoryRepository inventoryRepo;

    public void createOrder(Order order) {
        orderRepo.save(order);
        inventoryRepo.deduct(order.getItemId(), order.getQuantity());
    }
}
```

**预期命中**: `db-java-missing-transaction`
**文件类型**: `.java`

---

## 违规代码 - N+1 查询

```java
public List<OrderDetail> getOrderDetails(List<Order> orders) {
    List<OrderDetail> details = new ArrayList<>();
    for (Order order : orders) {
        OrderDetail detail = new OrderDetail();
        detail.setOrder(order);
        detail.setItems(itemRepo.findByOrderId(order.getId()));
        details.add(detail);
    }
    return details;
}
```

**预期命中**: `db-java-n-plus-one`
**文件类型**: `.java`

---

## 正确代码 - 使用 @Transactional

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
    }
}
```

**预期命中**: 无
**文件类型**: `.java`
