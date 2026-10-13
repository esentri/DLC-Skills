---
name: domainlifecycles
description: Implementing DDD building blocks with the DomainLifeCycles (DLC) Java library - marker types and annotations (AggregateRoot, Entity, ValueObject, Identity, DomainEvent, DomainCommand, Repository, DomainService, ApplicationService, ReadModel, QueryHandler, OutboundService, Factory, @FactoryMethod, @BoundedContext, @Publishes, @DomainEventListener), base classes (AggregateRootBase, EntityBase), Domain Mirror, persistence (jOOQ/JDBC repositories, fetcher), Jackson mapping, domain events (DomainEvents.publish, channels, outbox), DomainAssertions and Bean Validation, Spring Boot starter (@EnableDlc). Use for any domain code in a project whose build file contains io.domainlifecycles, or when the user mentions DLC or DomainLifeCycles.
---

# DomainLifeCycles (DLC)

Targets **DLC 3.5.x**. Upstream docs: https://github.com/esentri/domainlifecycles
(machine-readable summary: `llms.txt` in the repo root).

> **STOP - before reading on: invoke the skill `ddd-tactical-java` now if it is
> not loaded yet** - also for small changes, queries or read models. This skill
> only adds the DLC side; the DDD rules (boundaries, references by ID, read models
> vs. repositories, application layer) live there.

## Prerequisite - do this first

This skill builds on `ddd-tactical-java`. Load it before writing code.
DLC makes DDD concepts explicit; it does not decide aggregate boundaries,
invariants or references-by-ID for you. Without those rules any DLC
implementation is incomplete.

## Determine the mode - ALWAYS before any code change

1. **Project override:** read `AGENTS.md` (or `CLAUDE.md`). An explicit DLC mode
   there wins over everything below.
2. **Scan the build file:**
   `grep -rnE "io\.domainlifecycles" --include=pom.xml --include="build.gradle*" --include="*.toml" .`
   - no match -> **Mode A: plain DDD.** STOP here, apply only `ddd-tactical-java`.
     Do not introduce DLC types.
   - only `types`, `type-utils`, `assertions` (optionally `mirror`, `builder`)
     -> **Mode B: marker level.** Read `references/marker-types.md`.
   - additionally `spring-boot-starter`, `spring-boot3-starter`, `jooq-integration`,
     `jdbc-integration`, `jackson*-integration`, `domain-events-*`,
     `validation-extender`, `spring-web*-integration`, `spring-doc*-integration`
     -> **Mode C: runtime.** Read `references/marker-types.md` and
     `references/bootstrap-mirror.md`, plus the reference for each module present
     (table below).
3. **Cross-check in code:** is there a `Domain.initialize(...)` bootstrap or
   `@EnableDlc`? Do existing aggregates implement `AggregateRoot<ID>` /
   extend `AggregateRootBase<ID>`? If this contradicts step 2 -> ask, don't assume.
4. **Greenfield without a decision** -> ask which mode the team wants. Don't choose.

Mode C includes B, B includes A. Never skip a level.

## Marker catalogue (package `io.domainlifecycles.domain.types`)

| DDD concept        | DLC type                                   |
|--------------------|--------------------------------------------|
| Aggregate root     | `AggregateRoot<ID>` / base: `AggregateRootBase<ID>` |
| Entity             | `Entity<ID>` / base: `EntityBase<ID>`      |
| Value object       | `ValueObject` (records preferred) / base: `ValueObjectBase` |
| Identity           | `Identity<V>` (records: `record OrderId(Long value) implements Identity<Long>`) |
| Domain event       | `DomainEvent`                              |
| Domain service     | `DomainService`                            |
| Repository         | `Repository<ID, A extends AggregateRoot<ID>>` |
| Factory            | `Factory` (dedicated class), `@FactoryMethod` (creating method elsewhere) |
| Bounded context    | `@BoundedContext("Name")` on the context's `package-info.java` |
| Application service| `ApplicationService`                       |
| Domain command     | `DomainCommand`                            |
| Read model / query | `ReadModel`, `QueryHandler<R>`             |
| Outbound port      | `OutboundService`                          |
| Event wiring       | `@Publishes(domainEventTypes=...)`, `@DomainEventListener` (`@ListensTo` is deprecated) |

Base classes live in `io.domainlifecycles.domain.types.base` (module `type-utils`).

## Rules you need without loading a reference

- **Prefer the base classes** `AggregateRootBase<ID>` / `EntityBase<ID>` (correct
  `equals`/`hashCode`, `concurrencyVersion`). Implement `AggregateRoot<ID>` /
  `Entity<ID>` directly only if another superclass is unavoidable.
- `ValueObject`, `Identity`, `DomainEvent`, `DomainCommand` and `ReadModel` are
  always Java **records** implementing the marker interface.
- Every `ApplicationService` method that processes a command takes exactly one
  `DomainCommand` record as its parameter.
- Read models are served by a `QueryHandler<R>`, never by a `Repository`.
- Outbound ports: the port **interface** extends `OutboundService` (domain or
  application layer), the adapter implements it in infrastructure. Callers depend
  on the interface only.
- Cross-context port: the interface lives in the calling `@BoundedContext`
  package, the adapter in that context's infrastructure package and calls only
  the target context's `ApplicationService` / `QueryHandler`. In the Mirror and
  diagrams a domain type referencing another context's type is a red flag.
- Every bounded context root package gets a `package-info.java` with
  `@BoundedContext` - the Mirror derives the context boundaries from it.
- A `Factory` class only creates; its public methods returning domain objects are
  factory methods **without** annotation. Creating methods anywhere else (static
  creators on roots/entities/value objects, an aggregate creating another
  aggregate, a domain service with other operations) get `@FactoryMethod`.
  Builders are never annotated.
- Entities and roots: exactly one `public` all-args constructor annotated with
  Lombok `@Builder`; value object records get `@Builder` too. Invariants are
  enforced inside that constructor.
- Enums are value objects but **must not** implement `ValueObject`.
- Entities/roots carry a `long concurrencyVersion` (passed to the base constructor);
  never invent a separate version field.
- `equals`/`hashCode` of entities depend on the identity only - use the base classes
  or records and don't override them by hand.
- Invariants are checked on construction. Style (unless `AGENTS.md` says otherwise):
  - `validation-extender` in the build -> Bean Validation annotations wherever
    they can express the rule, the rest via `DomainAssertions` in `validate()`.
    The extender validates after **every non-getter method** - so any read-only
    method not named `get*`/`is*` without parameters (`hasStatus(...)`,
    `totalPrice()`, `items()`) gets `@Query`
    (`import io.domainlifecycles.validation.extend.Query;`).
  - no validation extender -> `DomainAssertions` only, called from the constructor.
  Details: `references/validation.md`.
- References to other aggregates are typed `Identity` fields, never object references
  (the Mirror and persistence rely on this).

## Module references - load only what the project uses

| Module(s) in build file                                   | Read                              |
|-----------------------------------------------------------|-----------------------------------|
| `types`, `type-utils`, `builder`                          | `references/marker-types.md`      |
| `mirror`, any runtime module                              | `references/bootstrap-mirror.md`  |
| `jooq-integration`, `jdbc-integration`, `persistence*`    | `references/persistence.md`       |
| `jackson3-integration`, `jackson2-integration`            | `references/jackson-mapping.md`   |
| `domain-events-*`, or any event publishing               | `references/domain-events.md`     |
| `assertions`, `bean-validations`, `validation-extender`   | `references/validation.md`        |
| `spring-boot*-starter`, `spring-web*`, `spring-doc*`      | `references/spring-integration.md`|

Related skills: tables / migrations / jOOQ codegen -> `dlc-persistence-schema`;
"who calls what" as text -> `dlc-impact-analysis`; diagrams -> `dlc-diagrammer`;
Diagram Viewer (run locally, upload model) -> `dlc-diagram-viewer`;
new project / build setup -> `dlc-project-setup`; full new-aggregate flow ->
`new-aggregate`.
