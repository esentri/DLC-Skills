# Changelog

All notable changes to the DLC-Skills are documented here.
Versions follow [Semantic Versioning](https://semver.org/) (see "Releases & versioning"
in the README). Each release states the DomainLifeCycles version it targets.

## [Unreleased]

### Added
- `domainlifecycles` persistence reference: JDBC fetcher usage - finders via
  `JdbcRecordMapper` (`selectByColumn`, `selectWithSql`), `RecordProvider` on a
  dedicated `JdbcAggregateFetcher`, fetcher outside a repository.
- `ddd-tactical-java`: domain commands are always named in the imperative
  (`CancelOrder`, `CheckeEin` - not `Einchecken`); domain events only where a
  listener exists. Both also in the modelling checklist, review red flags and
  `new-aggregate`.
- `domainlifecycles`: with the validation extender, read-only non-getter methods
  get `@Query` - rule now in SKILL.md itself, not only in the validation reference.
- Evals #89-#92: imperative command name, events only with listener, `@Query`
  import, `springdoc.use-fqn`.
- `domainlifecycles` Spring reference: `springdoc.use-fqn=true` is mandatory with
  SpringDoc (also in `dlc-project-setup`).

### Fixed
- `domainlifecycles` validation reference: `@Query` / `@ExcludeValidation` are in
  `io.domainlifecycles.validation.extend`, not `io.domainlifecycles.core.validation`.

## [0.9.0] - 2026-10-09

Targets **DomainLifeCycles 3.5.x**.

### Added
- `ddd-tactical-java`: framework-agnostic tactical DDD rules - bounded contexts,
  invariants, building blocks (aggregates, entities, value objects, identities,
  domain events, domain services, factories, repositories, application services,
  domain commands, read models / query handlers, outbound ports incl. synchronous
  cross-context calls), default package layout, legacy contexts, review red flags,
  modelling checklist.
- `domainlifecycles`: mode detection (A plain DDD / B marker types / C runtime),
  marker catalogue and conventions, references per DLC module (marker types,
  bootstrap & mirror, persistence, Jackson, domain events, validation, Spring).
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
