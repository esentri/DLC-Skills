# DLC marker types (Mode B and C)

Modules: `io.domainlifecycles:types` (interfaces), `io.domainlifecycles:type-utils`
(base classes), optional `io.domainlifecycles:builder`.
Upstream: `concepts/readme.md`.

Marker types alone add value without any DLC runtime: concepts become explicit in
the code and can be analysed and drawn by the DLC diagrammer / Diagram Viewer.

## Identity

```java
public record OrderId(@NotNull Long value) implements Identity<Long> {}
```
- One record per entity type, usually nested in the entity (`Order.OrderId`).
- `Identity<V>` exposes `V value()`.

## Value object

```java
public record Price(@NotNull @PositiveOrZero BigDecimal amount) implements ValueObject {
    public Price add(Price other) { return new Price(amount.add(other.amount)); }
}
```
- Prefer records. For classes extend `ValueObjectBase` (correct `equals`/`hashCode`).
- **Enums must not implement `ValueObject`** - DLC treats them as value objects anyway.
- No object references to entities/aggregates - typed IDs only.

## Entity (inside an aggregate)

```java
@Getter
public final class OrderItem extends EntityBase<OrderItem.OrderItemId> {
    public record OrderItemId(@NotNull Long value) implements Identity<Long> {}

    private final OrderItemId id;
    @NotNull private final Product.ProductId productId;
    @PositiveOrZero private int quantity;

    @Builder
    public OrderItem(long concurrencyVersion, OrderItemId id,
                      Product.ProductId productId, int quantity) {
        super(concurrencyVersion);
        this.id = id;
        this.productId = productId;
        this.quantity = quantity;
    }
}
```
- `Entity<ID>` requires `ID id()` and `long concurrencyVersion()`.
- The ID field is recognised by type; `@Entity.Id` marks it explicitly if ambiguous.

## Aggregate root

```java
@Getter
public final class Order extends AggregateRootBase<Order.OrderId> {
    public record OrderId(@NotNull Long value) implements Identity<Long> {}

    private final OrderId id;
    @NotNull private final Customer.CustomerId customerId;   // reference by ID
    @NotNull private final List<OrderItem> items;
    @NotNull private OrderStatus status;

    @Builder
    public Order(long concurrencyVersion, OrderId id, Customer.CustomerId customerId,
                  OrderStatus status, List<OrderItem> items) {
        super(concurrencyVersion);
        ...
    }

    public Order ship() {
        DomainAssertions.equals(status, OrderStatus.PENDING,
            "Can't ship an order that is not pending.");
        status = OrderStatus.SHIPPED;
        return this;
    }
}
```

## Repository (interface in the domain layer)

```java
public interface OrderRepository extends Repository<Order.OrderId, Order> {
    Order.OrderId newOrderId();
    Stream<Order> findByStatus(OrderStatus status);
}
```
`Repository<ID, A>` already declares `findById`, `insert`, `update`, `deleteById`.

## Services and other kinds

| Type                 | Use for                                               |
|----------------------|-------------------------------------------------------|
| `DomainService`      | Domain logic spanning entities; usually an interface extending it + impl |
| `ApplicationService` | Use-case orchestration, transaction boundary          |
| `Factory`            | Dedicated creation class, see "Factories" below       |
| `DomainCommand`      | Immutable command record entering the domain          |
| `ReadModel` + `QueryHandler<R>` | Query side, decoupled from aggregates      |
| `OutboundService`    | Outbound port to external systems, see below          |

## Outbound services

Port interface in the domain/application layer, adapter in infrastructure:
```java
// domain or application layer
public interface CustomerNotifier extends OutboundService {
    void notifyOrderShipped(Customer.CustomerId customerId, Order.OrderId orderId);
}

// infrastructure
@Component
class SmtpCustomerNotifier implements CustomerNotifier {
    @Override
    public void notifyOrderShipped(Customer.CustomerId customerId, Order.OrderId orderId) { ... }
}
```
- Callers (application services; domain services only for synchronous external
  answers a business rule needs) depend on the interface, never the adapter.
- May listen to domain events with `@DomainEventListener` for decoupled side effects.
- Method names and parameters use domain types (typed IDs, value objects), no
  technical DTOs of the external system.

## Bounded contexts

One root package per context, annotated in its `package-info.java`:
```java
@BoundedContext("Ordering")
package com.example.shop.ordering;

import io.domainlifecycles.domain.types.BoundedContext;
```
- The name is optional (`@BoundedContext`); the package name is always the key.
- Context packages must not be nested (the Mirror rejects overlaps with a
  `MirrorException`).
- Without any annotation the whole model is one single bounded context.
- jMolecules' `@org.jmolecules.ddd.annotation.BoundedContext` is recognised too
  when `mirror-jmolecules` is on the classpath.

## Factories and factory methods

Dedicated factory - every public method returning a domain object is a factory
method, no annotation needed:
```java
public class OrderFactory implements Factory {
    private final OrderRepository orderRepository;

    public OrderFactory(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public Order createFor(PlaceOrder placeOrder) {
        return Order.builder()
            .id(orderRepository.newOrderId())
            .customerId(placeOrder.customerId())
            .status(OrderStatus.PENDING)
            .build();
    }
}
```
Creating methods elsewhere are marked with `@FactoryMethod`:
```java
public final class Calendar extends AggregateRootBase<CalendarId> {
    @FactoryMethod
    public Appointment planAppointment(AppointmentTitle title) { ... }
}

public record Money(BigDecimal amount, Currency currency) implements ValueObject {
    @FactoryMethod
    public static Money euros(BigDecimal amount) { return new Money(amount, EUR); }
}
```
- Factory methods can create aggregates, entities, value objects, read models,
  domain commands or domain events; the return type is the created type.
- A `Factory` must not have public methods that create no domain object, and a
  `DomainService` whose public methods are all factory methods should be a
  `Factory` - the Mirror logs warnings for both.
- Builders (e.g. Lombok `@Builder`) are a technical means, never factory methods.

## Event wiring annotations

- `@Publishes(domainEventTypes = {OrderShipped.class})` on methods that publish.
- `@DomainEventListener` on listener methods (`@ListensTo` is deprecated since 3.0).

These make event flows visible to the Mirror and the diagrammer even in Mode B.

## Builder

With the `builder` module DLC instantiates domain objects generically via their
builders - needed by Jackson mapping and persistence in Mode C.

Conventions (Lombok):
- Entities and aggregate roots have **exactly one `public` all-args constructor**
  taking every field, annotated with `@Builder`.
- Value object records are annotated with `@Builder` as well.
- A setter prefix is optional: plain `@Builder` (`.id(...)`) works, and so does
  `@Builder(setterPrefix = "set")` (`.setId(...)`) - follow the project's
  existing convention and keep it consistent.
- Constructor parameter names must match the field names exactly (Lombok
  guarantees this; check hand-written constructors).
- Invariant checks run inside that constructor (records: compact canonical
  constructor), so the builder can never produce an invalid object.
