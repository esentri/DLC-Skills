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
- `validate()` runs **before** the Bean Validation constraints. Cross-field
  checks in `validate()` must be null-safe (skip them while a `@NotNull` field is
  still null) - otherwise a missing value ends in a `NullPointerException`
  instead of the `DomainAssertionException` from `@NotNull`.

## Activating the validation extender

Choose by the DLC version in the build file:

| DLC version | Activation in the application |
|---|---|
| 3.5.1 and later | `@PostConstruct` in the Spring Boot application class (DLC docs) |
| 3.5.0 and earlier | first statement in `main`, before `SpringApplication.run` |

DLC 3.5.1+ (as recommended by the DLC docs):
```java
@EnableDlc(dlcMirrorBasePackages = ShopApplication.DOMAIN_BASE_PACKAGE)
@SpringBootApplication
public class ShopApplication {

    public static final String DOMAIN_BASE_PACKAGE = "com.example.shop";

    public static void main(String[] args) {
        SpringApplication.run(ShopApplication.class, args);
    }

    @PostConstruct
    public void postConstruct() {
        ValidationDomainClassExtender.extend(DOMAIN_BASE_PACKAGE);
    }
}
```
DLC <= 3.5.0 - bug: a domain class loaded for the first time *during* the
activation stays unextended, silently (e.g. a value object only referenced by a
command record Spring already loaded while creating the beans - invalid value
objects are then accepted). `@PostConstruct` is affected; activate before any
domain class is loaded instead:
```java
public static void main(String[] args) {
    // DLC <= 3.5.0: before any domain class is loaded (fixed in 3.5.1, then @PostConstruct)
    ValidationDomainClassExtender.extend(DOMAIN_BASE_PACKAGE);
    SpringApplication.run(ShopApplication.class, args);
}
```
- Signature in 3.5: `extend(String... basePackages)`. Older versions of the
  upstream readme show `extend(List.of(...))` - that does not compile.
- Parameters: the same base package(s) as the mirror (`dlcMirrorBasePackages` /
  `Domain base package` in `AGENTS.md`) - keep them in one constant. Matching is
  a plain **string prefix** on the package name: sub-packages are included, but
  so are siblings with the same prefix (`com.example.shop` also covers
  `com.example.shopping`). A misspelled package or no argument extends nothing,
  without any error. Only concrete `Validatable` classes are touched, so passing
  the base package is enough - never list single classes.
- Use the plain `extend(String...)`. The overload
  `extend(DomainBuilderConfiguration, String...)` only excludes a non-static
  method named like the builder method from validation; the DLC autoconfig uses
  the default builder configuration itself, so there is nothing to align.
- Effective **once per JVM**: further calls are ignored (log
  `DLCDomainExtensions already processed!`), also with other packages - pass all
  base packages in the first call.
- The log lines `<class> extended validate call!` list only the classes already
  loaded at activation time - not a complete list of extended classes.
- Plain Java without Spring: call `extend(...)` first thing in `main`, before
  `Domain.initialize(...)`.

### Tests - always register a launcher session listener
Plain unit tests have no Spring context, so the activation in the application
class never runs there - the result would depend on whether a Spring test ran
before in the same JVM. Activate the extender once per test JVM, before any test
runs (with DLC <= 3.5.0 this also avoids the bug above):
```java
// src/test/java/com/example/shop/ValidationExtenderLauncherSessionListener.java
public class ValidationExtenderLauncherSessionListener implements LauncherSessionListener {

    @Override
    public void launcherSessionOpened(LauncherSession session) {
        ValidationDomainClassExtender.extend(ShopApplication.DOMAIN_BASE_PACKAGE);
    }
}
```
```text
# src/test/resources/META-INF/services/org.junit.platform.launcher.LauncherSessionListener
com.example.shop.ValidationExtenderLauncherSessionListener
```
- Needs `org.junit.platform:junit-platform-launcher` on the test **compile**
  classpath (Gradle `testImplementation`, Maven scope `test`).
- The later call from the application class in a `@SpringBootTest` is ignored -
  harmless.
- Don't call `extend(...)` in `@BeforeAll` of single test classes instead - only
  the first call per JVM counts, so the result depends on which tests run.
- Byte Buddy attaches an agent at runtime: add `-XX:+EnableDynamicAgentLoading`
  to the JVM args of tests and `bootRun` to silence the JDK 21+ warning.

## Gotchas
- Without a Bean Validation provider (e.g. Hibernate Validator) at runtime,
  constraints are **skipped with only a log warning**.
- `@Valid` is not needed - DLC always validates the complete object graph.
- `DomainAssertions` on an `Optional` only check if a value is present.

## Rules
- Invariants belong in the domain, not in controllers or DTOs.
- One style per project; don't mix guard-clause exceptions with DomainAssertions.
