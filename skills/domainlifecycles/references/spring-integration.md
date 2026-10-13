# Spring integration (Mode C)

Modules: `spring-boot-starter` (Spring Boot 4.x) or `spring-boot3-starter`
(Spring Boot 3.x); contains `dlc-spring-boot*-autoconfig`, `spring-web*-integration`,
`spring-doc*-integration`. Upstream: `dlc-spring-boot-autoconfig/readme.md`
(Boot 3: `dlc-spring-boot3-autoconfig/readme.md`).

## Activation
```java
@EnableDlc(dlcMirrorBasePackages = "com.example.shop")   // mandatory, comma-separated
@SpringBootApplication
public class Application { ... }
```
Further `@EnableDlc` attributes: `jooqRecordPackage` (mandatory for jOOQ
persistence), `jooqSqlDialect` (recommended; also selects the JDBC dialect),
`transactionCacheEnabled`, `transactionCacheMaxSize`, `exclude`.
Properties override the annotation for the transaction cache.

## Features need their external libraries
The starter only enables a feature if its external library is a declared
dependency - otherwise the autoconfig stays off **silently**:
jOOQ (jOOQ persistence), Spring Web (web integration), SpringDoc (OpenAPI),
spring-tx (transactional domain events). **Validation is never autoconfigured**
(see `validation.md`).

## Autoconfig modules and toggles

| Autoconfig | Toggle (property) | Notes |
|---|---|---|
| `DlcDomainAutoConfiguration` (mirror) | `dlc.features.mirror.enabled` | packages: `dlc.features.mirror.base-packages` |
| `DlcBuilderAutoConfiguration` | `dlc.features.builder.enabled` | |
| `DlcJacksonAutoConfiguration` (Boot 4, Jackson 3) | `dlc.features.jackson.enabled` | |
| `DlcJackson2AutoConfiguration` (Jackson 2; Boot 3 starter) | `dlc.features.jackson2.enabled` | |
| `DlcJooqPersistenceAutoConfiguration` | `dlc.features.persistence.enabled` | needs jOOQ on the classpath |
| `DlcJdbcPersistenceAutoConfiguration` | `dlc.features.persistence.enabled` | optional `dlc.features.persistence.jdbc.schema-pattern` |
| `DlcServiceKindAutoConfiguration` | `dlc.features.servicekinds.enabled` | see below |
| Domain events (`DlcSpringBusDomainEventsAutoConfiguration`) | `dlc.features.events.springbus.enabled` | default; in-memory only with `dlc.features.events.inmemory.enabled=true` |
| `DlcSpringWebAutoConfiguration` | `dlc.features.springweb.enabled` | needs Spring Web |
| `DlcSpringOpenApiAutoConfiguration` | `dlc.features.openapi.enabled` | needs SpringDoc |

- `dlc.features.persistence.enabled=false` switches persistence off as a whole.
  `dlc.features.persistence.jooq.enabled=false` / `...jdbc.enabled=false` only
  force one backend off when both are on the classpath (jOOQ wins by default).
- Exclude via `@EnableDlc(exclude = ...)`; annotation excludes win over properties.
- Own bean overrides go into a **separate `@Configuration` class**, never into the
  Spring Boot application class.

Common properties:
```properties
dlc.features.mirror.base-packages=com.example.shop
dlc.features.persistence.sql-dialect=POSTGRES
dlc.features.persistence.jooq-record-package=com.example.jooq.tables.records
```

## ServiceKind beans are registered automatically
`DlcServiceKindAutoConfiguration` creates Spring beans for **every class
implementing a `ServiceKind`** in the mirror base packages: repositories, domain
services, application services, query handlers, outbound services, factories
(override the packages with `dlc.features.servicekinds.packages`).
- Don't add `@Service`/`@Component`/`@Repository` to these classes - a bean of
  the same interface type already present makes the autoconfig skip its own
  registration with a warning.
- Domain classes (aggregates, entities, value objects) are never beans.

## Web
- Controllers may take typed IDs and single-valued value objects directly as
  path/query parameters: `@GetMapping("/orders/{id}") Order get(@PathVariable Order.OrderId id)`.
- Controllers call application services, never repositories or aggregates directly.

## OpenAPI (SpringDoc)
- **Mandatory:** `springdoc.use-fqn=true` in `application.properties` whenever
  SpringDoc is on the classpath. The DLC OpenAPI customizer works on fully
  qualified class names and fails at startup without it ("DLC Open API extension
  requires the spring doc config property 'springdoc.use-fqn' to be 'true'!").
- IDs and single-valued value objects are rendered as primitive schemas, matching
  the DLC JSON mapping; Bean Validation constraints appear in the schema.
- Primitive fields are always marked required - use wrapper types for nullable
  fields.

## Troubleshooting
- jOOQ records not found -> rebuild (codegen) and check `jooqRecordPackage`.
- Debug: `logging.level.io.domainlifecycles.autoconfig=DEBUG`.
- DLC < 3.5 on Spring Boot 4.1+: jOOQ and Jackson autoconfig silently don't run -
  upgrade DLC.
