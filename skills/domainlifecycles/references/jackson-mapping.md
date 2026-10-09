# JSON mapping with Jackson (Mode C)

Modules: `jackson3-integration` (recommended) or `jackson2-integration` (legacy,
all classes `@Deprecated`). Upstream: `jackson3-integration/readme.md`,
`jackson2-integration/readme.md`.

## What it does
- Serialises/deserialises aggregates, entities, value objects, events, commands
  and read models via the Domain Mirror and DLC builders - no DTO boilerplate needed.
- `Identity` types and single-valued value objects are written as plain JSON values
  (`"orderId": 42`). Deserialisation accepts both the plain and the nested
  `{"value": 42}` form.

## Activation
- Spring Boot: automatic via the starter - Jackson 3: `DlcJacksonAutoConfiguration`
  (`dlc.features.jackson.enabled`); Jackson 2: `DlcJackson2AutoConfiguration`
  (`dlc.features.jackson2.enabled`).
- Without autoconfig, declare the module as a bean (constructors differ!):

| | Jackson 3 | Jackson 2 |
|---|---|---|
| Module | `io.domainlifecycles.jackson3.module.DlcJacksonModule` | `io.domainlifecycles.jackson2.module.DlcJacksonModule` |
| Constructor | `(builderProvider, entityIdentityProvider, identityFactory, classProvider)` | `(builderProvider, entityIdentityProvider)` |
| `EntityIdentityProvider` | `io.domainlifecycles.jackson3.api` | `io.domainlifecycles.persistence.provider` |

```java
@Bean
DlcJacksonModule dlcJacksonModule(List<? extends JacksonMappingCustomizer<?>> customizers,
                                  DomainObjectBuilderProvider builderProvider,
                                  EntityIdentityProvider entityIdentityProvider,
                                  IdentityFactory identityFactory,
                                  ClassProvider classProvider) {
    var module = new DlcJacksonModule(builderProvider, entityIdentityProvider, identityFactory, classProvider);
    customizers.forEach(c -> module.registerCustomizer(c, c.instanceType));
    return module;
}
```

## Customisation
- `JacksonMappingCustomizer<T>` per domain type, registered via
  `module.registerCustomizer(...)`. Callbacks: `beforeObjectRead`,
  `afterFieldRead`, `afterObjectRead` (most common), `beforeFieldWrite`,
  `beforeObjectWrite`.
- Read callbacks work on `DomainObjectMappingContext.domainObjectBuilder` -
  **before** the object is built (e.g. fill a server-side `timestamp`).
- Return `MappingAction.CONTINUE_WITH_DEFAULT_ACTION` to keep the default mapping,
  `MappingAction.SKIP_DEFAULT_ACTION` to replace it.
- Upstream customizer examples still show Jackson 2 types in signatures - check
  the actual Jackson 3 API.

## IDs for new entities
- Identities are never null. For entities created from outside (e.g. REST) without
  an ID, an `EntityIdentityProvider` assigns one during mapping.
- `JooqEntityIdentityProvider` uses a sequence per ID type named
  `<schema>.<id_type_snake_case>_seq` (e.g. `DeliveryAddressId` ->
  `shop.delivery_address_id_seq`).

## Rules
- Don't add `@JsonCreator`/`@JsonProperty` to domain objects - it leaks
  infrastructure into the domain and fights the DLC mapping.
- Validation still runs: invalid JSON must fail in the domain, not be fixed in a
  customizer.
