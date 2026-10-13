---
name: dlc-project-setup
description: Set up or migrate a Java project for tactical DDD with or without DomainLifeCycles (DLC) - choosing the mode (plain DDD without DLC, marker types only, or full runtime), moving a plain-DDD project to DLC marker types, adding dependencies or the Spring Boot starter, jOOQ code generation vs. plain JDBC persistence, Flyway schema, mirror bootstrap and the AGENTS.md mode declaration. Use for new DLC projects, adding DLC to an existing build (Maven or Gradle), or upgrading DLC versions.
---

# DLC project setup

Targets DLC 3.5.x. Upstream: `getting-started/english/index_en.md`, `llms.txt`,
`sample-project/`.

## Step 1 - decide the mode with the developer (never choose silently)

| Mode | What you get | Dependencies |
|------|--------------|--------------|
| A: plain DDD | Tactical DDD rules only (`ddd-tactical-java`), no library | none |
| B: markers | Explicit DDD concepts, diagrams, no runtime magic | `types`, `type-utils`, optional `assertions`, `builder` |
| C: runtime | + persistence, JSON, events, validation, Spring | `spring-boot-starter` (Boot 4.x) or `spring-boot3-starter` (Boot 3.x), or single modules |

Record the decision in the project's `AGENTS.md` (template:
`templates/AGENTS.md.snippet` in the skills repo):
```markdown
## DomainLifeCycles
Mode: C (runtime, Spring Boot starter, jOOQ persistence)
Domain base package: com.example.shop
Validation style: BeanValidation+DomainAssertions (validation extender)
```
Always ask for the validation style too: validation extender -> Bean
Validation + DomainAssertions (automatic); Bean Validation without extender ->
`BeanValidations.validate(this)` in `validate()`; otherwise DomainAssertions only.

### Mode A - short path
1. Record it in `AGENTS.md`, so later sessions know the absence of DLC is
   deliberate:
   ```markdown
   ## DomainLifeCycles
   For any work on domain code, load the skill `ddd-tactical-java` first.
   Mode: A
   Domain base package: com.example.shop
   Validation style: Java exceptions (no DLC)
   Package layout: default
   ```
2. Create one root package per bounded context with the default package layout
   from `ddd-tactical-java` (no `@BoundedContext` annotation in Mode A).
3. Skip steps 2-6; verify with a unit test per invariant.

## Step 2 - dependencies (group `io.domainlifecycles`, version `3.5.0`)

Mode B (Gradle):
```groovy
implementation 'io.domainlifecycles:types:3.5.0'
implementation 'io.domainlifecycles:type-utils:3.5.0'
implementation 'io.domainlifecycles:assertions:3.5.0'
```
Mode C with Spring Boot 4.x / 3.x:
```groovy
implementation 'io.domainlifecycles:spring-boot-starter:3.5.0'    // Spring Boot 4.x
implementation 'io.domainlifecycles:spring-boot3-starter:3.5.0'   // Spring Boot 3.x
```
Use a version property / version catalog; never mix DLC versions.

External libraries - starter features stay **silently off** without them:
- always: SLF4J provider
- jOOQ backend: jOOQ 3.19.x or 3.21.x (3.21 requires Java 21 - on Java 17 pin
  3.19.x, e.g. via `<jooq.version>`; on Java 21 the Spring Boot 4.1 managed version
  works)
- JDBC driver for the database
- Spring Web (web integration), SpringDoc (OpenAPI - requires
  `springdoc.use-fqn=true`), spring-tx (transactional events)
- Bean Validation: a provider such as Hibernate Validator (without it constraints
  are skipped with only a warning); Byte Buddy for the validation extender
- Lombok (optional builders), Gruelbox (outbox)

## Step 3 - persistence backend (Mode C)
- **jOOQ (default):** needs a jOOQ codegen build step against a schema
  (Flyway migrations + Testcontainers or H2). Set
  `dlc.features.persistence.jooq-record-package` (= codegen `packageName`) and
  `sql-dialect`.
- **JDBC:** no codegen; choose when build-time DB access or jOOQ licensing is a problem.
- Schema, migrations and codegen settings (incl. `recordVersionFields`): load the
  skill `dlc-persistence-schema`. Repositories: `domainlifecycles`,
  `references/persistence.md`.
- Transaction cache (optional) needs Spring Boot 3.4+ / Spring 6.2+. Ask for enablement if setup permits.

## Step 4 - bootstrap
- Spring Boot with the starter: only `@EnableDlc(dlcMirrorBasePackages = "com.example.shop")`.
  The autoconfig initialises the mirror - **no `Domain.initialize(...)`**, neither in
  the application nor in `@SpringBootTest`s.
- Without Spring autoconfig (plain Java, or plain unit tests without a Spring
  context): `Domain.initialize(new ReflectiveDomainMirrorFactory("com.example.shop"))`
  once at startup / in the test setup.
- Validation is **not** autoconfigured: with the validation extender call
  `ValidationDomainClassExtender.extend(...)` early (e.g. `@PostConstruct`), see
  `domainlifecycles`, `references/validation.md`.
- With the Spring starter, service kinds (repositories, domain/application
  services, query handlers, outbound services, factories) become beans
  automatically - don't annotate them with `@Service`/`@Component`.

## Step 5 - bounded contexts
Create one root package per bounded context with a `package-info.java`
annotated `@BoundedContext("<Name>")` (works in Mode B and C). Don't nest context
packages. Details: `domainlifecycles` skill, `references/marker-types.md`.

## Step 6 - optional build plugin
Diagrams, mirror export, Diagram Viewer upload -> `dlc-diagrammer` skill.
The plugin is independent of the starters.

## Step 7 - verify
- Build compiles, a smoke test loads the mirror (`Domain` initialised, a known
  aggregate is resolvable).
- Mode C: an insert + `findById` round-trip test for one aggregate.

## Moving from Mode A to Mode B
Makes the existing model explicit and diagrammable; runtime behaviour does not change.
1. Add `io.domainlifecycles:types` and `io.domainlifecycles:type-utils` (optionally
   `assertions`, `builder`) - see step 2.
2. Mark the building blocks (see `domainlifecycles`, `references/marker-types.md`):
   - aggregate roots / entities: extend `AggregateRootBase<ID>` / `EntityBase<ID>`
     (adds `concurrencyVersion` to the constructor); remove hand-written
     `equals`/`hashCode`,
   - typed IDs: `implements Identity<V>`; value objects: `implements ValueObject`
     (not enums),
   - services, repositories, factories, commands, events, read models, query
     handlers, outbound ports: their marker interfaces; `@Publishes` /
     `@DomainEventListener` / `@FactoryMethod` where applicable.
3. Add `package-info.java` with `@BoundedContext` to each context root package.
4. Decide whether invariants stay as Java exceptions or move to `DomainAssertions`
   (one style per project) and update `AGENTS.md` (`Mode: B`, validation style).
5. Optionally add the build plugin and generate a first diagram (`dlc-diagrammer`)
   to check that every class is recognised.

## Upgrading DLC
Read `CHANGELOG.md` upstream for every version between old and new; bump all DLC
artifacts and the build plugin together. Known pitfalls:
- DLC < 3.5 on Spring Boot 4.1+: jOOQ and Jackson autoconfig silently don't run.
- `@ListensTo` is deprecated -> `@DomainEventListener`.
- Jackson 2 integration is deprecated -> `jackson3-integration`.
