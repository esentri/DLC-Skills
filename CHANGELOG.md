# Changelog

All notable changes to the DLC-Skills are documented here.
Versions follow [Semantic Versioning](https://semver.org/) (see "Releases & versioning"
in the README). Each release states the DomainLifeCycles version it targets.

## [Unreleased]

## [0.10.3] - 2026-10-28

Targets **DomainLifeCycles 3.5.x**.

### Changed
- `ddd-tactical-java` (application services, read models), `domainlifecycles`
  (`SKILL.md`, `references/marker-types.md`): CQRS light is the default - if a
  single aggregate satisfies the read need, the aggregate is returned, no read
  model. A read model + query handler only when the aggregate cannot
  structurally provide the data (several aggregates, part of an aggregate,
  derived/aggregated values). Application service output: the aggregate, a read
  model or a simple confirmation. `AGENTS.md` may demand the stricter rule
  "never expose aggregates" (every read via read model). New evals #103
  (CQRS light) and #104 (`AGENTS.md` override).

## [0.10.2] - 2026-10-16

Targets **DomainLifeCycles 3.5.x**.

### Changed
- `domainlifecycles` (`SKILL.md`, `references/domain-events.md`): event listener
  methods carry `@DomainEventListener` only - no `@Transactional`, `@Async`,
  `@EventListener`, `@TransactionalEventListener` or similar, unless `AGENTS.md`
  says otherwise. New eval #100.
- `ubiquitous-language`: `deprecated` terms get a `Replaced by` column (glossary
  template, migrated when an existing glossary is written next). Only the user
  deprecates; deprecated rows are kept; `check` suggests `Replaced by`; `build`
  does not re-add deprecated terms as candidates but reports code still using
  them. Template has a deprecated example row; eval glossaries migrated; new evals
  #101 (check) and #102 (build).

## [0.10.1] - 2026-10-15

Targets **DomainLifeCycles 3.5.x** (validation extender activation in
`@PostConstruct` needs 3.5.1+).

### Fixed
- JDBC backend + Flyway/Liquibase with the Spring starter: the DLC autoconfig read
  the schema before the migrations ran (`Couldn't find table for '...'`).
  `dlc-persistence-schema` now always adds a `DependsOnDatabaseInitializationDetector`
  for `JdbcSchemaMetadata` (registered in `spring.factories`); `dlc-project-setup`,
  `persistence.md` and `spring-integration.md` point to it.
- Validation extender activation (`validation.md`, `dlc-project-setup`): with DLC
  3.5.1+ `@PostConstruct` in the application class as recommended by the DLC docs;
  with DLC 3.5.0 as first statement in `main` - 3.5.0 silently leaves classes
  unextended that are loaded during the activation (fixed in DLC 3.5.1). Varargs
  signature `extend(String...)` (the upstream `extend(List.of(...))` does not
  compile); effective once per JVM; parameters are the mirror base packages (one
  constant), matched as string prefix; the `DomainBuilderConfiguration` overload is
  not needed. Plain unit tests get a JUnit
  `LauncherSessionListener` that activates the extender once per test JVM.
  `validate()` runs before Bean Validation - cross-field checks must be null-safe.
- `dlc-project-setup`: JDBC backend excludes the jOOQ integration the starter brings
  along; verification includes an invalid value object in a unit and a Spring test.

### Changed
- Eval #67 expects the activation in `main` (sample project uses DLC 3.5.0, judge) and
  the launcher session listener, and forbids `extend(List.of(...))`; new eval #99
  (JDBC + Flyway startup ordering).

## [0.10.0] - 2026-10-14

Targets **DomainLifeCycles 3.5.x**.

### Added
- `ubiquitous-language` (plugin `ddd-tactical-java`): glossary of domain terms in
  `docs/ubiquitous-language.md` - `build` from existing code (per bounded context,
  candidates, questions to the user instead of guesses), `check` code or changes
  against it. While implementing, new domain terms are added as `candidate`
  automatically (rule in `ddd-tactical-java`, only if the glossary exists).
  `Glossary:` line in `templates/AGENTS.md.snippet` (asked for by `dlc-project-setup`);
  `new-aggregate` uses the glossary.
- Evals #93-#98 for the ubiquitous language (triggering, check, build with
  questions, candidates while implementing, no glossary created without one).

### Changed
- README: release checklist bumps the pinned `ref` before tagging (the tag must
  contain it); `npx skills` example for plain DDD installs both framework-agnostic
  skills.

## [0.9.0] - 2026-10-13

Targets **DomainLifeCycles 3.5.x**.

### Added
- `ddd-tactical-java`: framework-agnostic tactical DDD rules - bounded contexts,
  invariants, building blocks (aggregates, entities, value objects, identities,
  domain events, domain services, factories, repositories, application services,
  domain commands, read models / query handlers, outbound ports incl. synchronous
  cross-context calls), default package layout, legacy contexts, review red flags,
  modelling checklist. Commands are named in the imperative (`CancelOrder`,
  `CheckeEin`); domain events only where a listener exists.
- `domainlifecycles`: mode detection (A plain DDD / B marker types / C runtime),
  marker catalogue and conventions, references per DLC module (marker types,
  bootstrap & mirror, persistence, Jackson, domain events, validation, Spring) -
  incl. jOOQ and JDBC fetcher queries, `@Query` for read-only methods with the
  validation extender, `springdoc.use-fqn=true` for SpringDoc.
- `dlc-persistence-schema`: tables, columns, sequences, FKs and migrations for DLC
  aggregates, jOOQ codegen, mapping troubleshooting, DDL example.
- `dlc-impact-analysis`: call graph and flows as text via DLC static analysis.
- `dlc-diagrammer`: domain and flow diagrams via build plugin or Java API.
- `dlc-diagram-viewer`: run the DLC Diagram Viewer with Docker Compose and upload
  the domain model incl. static analysis via the build plugin.
- `dlc-project-setup`: mode decision incl. plain DDD, dependencies, bootstrap,
  bounded contexts, A -> B migration, upgrade pitfalls.
- `new-aggregate`: explicit workflow from model to tested implementation.
- Claude Code marketplace (`dlc-plugins`), templates for `AGENTS.md` and
  `.claude/settings.json` (latest and pinned).
- Automated eval suite (`evals/suite.json`, `evals/run.sh`, `claude plugin eval`):
  triggering, negative tests, AGENTS.md activation and rule adherence.
