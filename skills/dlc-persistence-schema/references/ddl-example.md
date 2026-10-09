# DDL example: Order aggregate (PostgreSQL, Flyway)

Conventions from `persistence/readme.md` (AutoMapping, record mapped ValueObjects,
scalar lists) and the id-generation sections of `jooq-integration` / `jdbc-integration`.

## Aggregate

```java
public final class Order extends AggregateRootBase<Order.OrderId> {
    public record OrderId(Long value) implements Identity<Long> { }

    private final OrderId id;
    private final Customer.CustomerId customerId;   // other aggregate, by ID
    private OrderStatus status;                     // enum
    private Address deliveryAddress;                // 1:1 VO -> embedded
    private List<OrderItem> items;                  // entities
    private List<ActionCode> actionCodes;           // 1:n VO -> own table
    private List<Voucher.VoucherId> voucherIds;     // List<Identity> -> scalar list
}

public final class OrderItem extends EntityBase<OrderItem.OrderItemId> {
    public record OrderItemId(Long value) implements Identity<Long> { }
    private final OrderItemId id;
    private final Product.ProductId productId;
    private final Price productPrice;               // record Price(BigDecimal amount)
    private int quantity;
}

public record Address(String street, String city) implements ValueObject { }
public record ActionCode(String value) implements ValueObject { }
```
(`concurrencyVersion` is inherited from the base classes.)

## Migration `V7__create_order.sql`

```sql
-- root: table ORDER (reserved word -> quoted; jOOQ quotes itself,
-- JDBC needs a JdbcDialect with quoteIdentifier)
CREATE TABLE "order" (
    id                     BIGINT PRIMARY KEY,
    concurrency_version    BIGINT NOT NULL,
    customer_id            BIGINT NOT NULL,      -- FK to customer: see AGENTS.md / ask
    status                 VARCHAR(50) NOT NULL, -- enum
    delivery_address_street VARCHAR(200) NOT NULL, -- embedded VO: field path
    delivery_address_city  VARCHAR(100) NOT NULL  -- deliveryAddress.city
);
CREATE SEQUENCE order_id_seq START WITH 1000;   -- OrderId -> ORDER_ID_SEQ

-- entity: table ORDER_ITEM, NOT NULL FK to the parent row (mandatory, fetcher;
-- no Java field - DLC fills it)
CREATE TABLE order_item (
    id                  BIGINT PRIMARY KEY,
    concurrency_version BIGINT NOT NULL,
    order_id            BIGINT NOT NULL REFERENCES "order"(id),
    product_id          BIGINT NOT NULL,
    product_price_amount NUMERIC(19,6) NOT NULL,
    quantity            INT NOT NULL
);
CREATE SEQUENCE order_item_id_seq START WITH 1000; -- OrderItemId

-- 1:n VO: <CONTAINING_TABLE>_<PROPERTY>, technical id, <TABLE>_SEQ, container_id FK
CREATE TABLE order_action_codes (
    id           BIGINT PRIMARY KEY,
    container_id BIGINT NOT NULL REFERENCES "order"(id),
    value        VARCHAR(10) NOT NULL
);
CREATE SEQUENCE order_action_codes_seq START WITH 1000;

-- List<Identity>: same structure, single raw "value" column
CREATE TABLE order_voucher_ids (
    id           BIGINT PRIMARY KEY,
    container_id BIGINT NOT NULL REFERENCES "order"(id),
    value        BIGINT NOT NULL
);
CREATE SEQUENCE order_voucher_ids_seq START WITH 1000;
```

Notes:
- No `concurrency_version` on VO / scalar list tables - only entities and roots carry it.
- A `List<OrderStatus>` field would look like `order_voucher_ids` with `value VARCHAR(50)`.
- A UUID identity would use `CHAR(36)` and no `<ID>_SEQ` (generated in memory).
- Nested VO list `ActionCode.vals` -> table `order_action_codes_vals`, `container_id`
  referencing `order_action_codes(id)`, sequence `order_action_codes_vals_seq`.

## Round-trip test (sketch)

```java
var order = Order.builder()...build();          // with items, actionCodes, voucherIds
repository.insert(order);
var loaded = repository.findById(order.getId()).orElseThrow();
assertThat(loaded.getItems()).hasSize(order.getItems().size());
assertThat(loaded.getActionCodes()).containsExactlyInAnyOrderElementsOf(order.getActionCodes());
assertThat(loaded.getVoucherIds()).containsExactlyInAnyOrderElementsOf(order.getVoucherIds());
repository.update(loaded);                      // version check active?
repository.deleteById(order.getId());
```
Partial result (e.g. empty `items`) -> missing FK; startup failure -> mapping
mismatch (see SKILL.md troubleshooting).
