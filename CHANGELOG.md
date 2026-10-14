# Changelog

All notable changes to the DLC-Skills are documented here.
Versions follow [Semantic Versioning](https://semver.org/) (see "Releases & versioning"
in the README). Each release states the DomainLifeCycles version it targets.

## [Unreleased]

### Added
- `ubiquitous-language` (plugin `ddd-tactical-java`): glossary of domain terms in
  `docs/ubiquitous-language.md` - `build` from existing code (per bounded context,
  candidates, questions to the user instead of guesses), `check` code or changes
  against it. While implementing, new domain terms are added as `candidate`
  automatically (rule in `ddd-tactical-java`, only if the glossary exists).
  `Glossary:` line in `templates/AGENTS.md.snippet`; `new-aggregate` uses the glossary.

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
