# Validation (Mode B and C)

Modules: `assertions` (`io.domainlifecycles.assertion.DomainAssertions` - some
upstream docs show another package, check the import), `bean-validations`,
`validation-extender` (Byte Buddy). Upstream: `validation-extender/readme.md`.

Invariants are always checked on construction - an invalid domain object must
never exist. The project's `AGENTS.md` ("Validation style") overrides the
defaults below. **Validation is not part of the Spring autoconfig** - it must be
activated explicitly.

## Choose the style from the build file

| Build contains | Style |
|---|---|
| `validation-extender` | Bean Validation annotations where possible + `DomainAssertions` in `validate()` for the rest; checks run automatically |
| `bean-validations`, no extender | Bean Validation annotations + `DomainAssertions`; `validate()` calls `BeanValidations.validate(this)` and is called from the constructor |
| neither | `DomainAssertions` only, `validate()` called from the constructor |

No DLC at all (Mode A): standard Java exceptions, see `ddd-tactical-java`.
Don't use `IllegalArgumentException` guard clauses in a DLC project unless
`AGENTS.md` asks for it.

## Decision order - each invariant is checked exactly once

1. **Declarative field invariant** (null, length, range, format) -> Bean
   Validation annotation on the field / record component
   (`@NotNull`, `@NotBlank`, `@Size`, `@Min`, `@Max`, `@Positive`, `@Digits`,
   `@Past`, `@Future`, `@Pattern`, `@Email`) - only if Bean Validation is used.
2. **Invariant without a fitting annotation** (relations between fields,
   business conditions) -> `DomainAssertions` in `validate()`.
3. **Precondition of a state transition** (depends on the current state and the
   requested change) -> `DomainAssertions` guard at the start of the aggregate /
   entity method. With the extender, simple parameter preconditions can also be
   Bean Validation annotations on the method parameters.

Never check the same rule twice (annotation **and** assertion, or `validate()`
**and** a guard).

## Without validation extender
```java
@Builder
public Order(long concurrencyVersion, OrderId id, CustomerId customerId, List<OrderItem> items) {
    super(concurrencyVersion);
    this.id = id;
    this.customerId = customerId;
    this.items = items;
    validate();
}

@Override
public void validate() {
    BeanValidations.validate(this);   // only if Bean Validation annotations are used
    DomainAssertions.isNotNull(customerId, "Customer is required.");
    DomainAssertions.hasSizeMax(items, 100, "An order has at most 100 items.");
}

public Order ship() {
    DomainAssertions.equals(status, OrderStatus.PENDING, "Only pending orders can be shipped.");
    status = OrderStatus.SHIPPED;
    return this;
}
```
- Every DLC domain object is `Validatable`; `validate()` holds all invariants of
  the building block and is called explicitly at the end of the constructor.
- Throws `DomainAssertionException` - a domain error, not a technical one.
- Bean Validation annotations are only enforced via `BeanValidations.validate(this)`
  or the extender - never rely on them otherwise.

## With validation extender
```java
public record Price(@NotNull @PositiveOrZero @Digits(integer = 10, fraction = 2) BigDecimal amount)
        implements ValueObject {}

public final class Order extends AggregateRootBase<Order.OrderId> {
    @NotNull private final CustomerId customerId;
    @NotNull @Size(max = 100) private final List<OrderItem> items;
    ...
    @Override
    public void validate() {
        // only rules Bean Validation cannot express (cross-field, state-dependent)
        DomainAssertions.isTrue(deliveryDate == null || !deliveryDate.isBefore(orderDate),
            "Delivery date must not be before order date.");
    }

    @Query   // read-only method: excluded from instrumentation
    public Price totalPrice() { ... }
}
```
- Byte Buddy inserts `validate()` and Bean Validation at the end of **every
  constructor** and of **every method that is not a getter** (`get*`/`is*` without
  parameters). Annotated method parameters and return values are checked too.
- Read-only methods that don't follow the getter convention (`items()`,
  `totalPrice()`, `hasStatus(...)`) are validated as well - mark them with
  `@Query` or `@ExcludeValidation` (both `io.domainlifecycles.validation.extend`,
  module `validation-extender`) to exclude them.
- Activate as early as possible after application start, e.g. in Spring:
  ```java
  @PostConstruct
  public void postConstruct() {
      ValidationDomainClassExtender.extend(List.of("com.example.shop"));
  }
  ```

## Gotchas
- Without a Bean Validation provider (e.g. Hibernate Validator) at runtime,
  constraints are **skipped with only a log warning**.
- `@Valid` is not needed - DLC always validates the complete object graph.
- `DomainAssertions` on an `Optional` only check if a value is present.

## Rules
- Invariants belong in the domain, not in controllers or DTOs.
- One style per project; don't mix guard-clause exceptions with DomainAssertions.
