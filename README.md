# DLC-Skills
Tactical DDD Implementation Skills with DLC

Agent skills for tactical Domain-Driven Design in Java, with and without
[DomainLifeCycles (DLC)](https://github.com/esentri/domainlifecycles).
Written in the open [Agent Skills](https://agentskills.io) format (`skills/<name>/SKILL.md`),
so they work in Claude Code, Codex, Cursor and other agents.

Targets **DLC 3.5.x**.

## Skills

| Skill | Plugin | Purpose | Triggered by |
|-------|--------|---------|--------------|
| `ddd-tactical-java` | `ddd-tactical-java` | Framework-agnostic tactical DDD: bounded contexts, invariants, building blocks, application layer, outbound ports, package layout, review red flags, modelling checklist | DDD vocabulary (aggregate, invariant, value object, bounded context ...) |
| `domainlifecycles` | `domainlifecycles` | DLC marker types and runtime modules; detects mode A/B/C and loads only the references for the modules in use | DLC types / `io.domainlifecycles` in the build, "DLC" |
| `dlc-persistence-schema` | `domainlifecycles` | Tables, sequences, FKs and migrations for DLC aggregates; jOOQ codegen; mapping errors | "migration", "table for aggregate", codegen / mapping errors |
| `dlc-impact-analysis` | `domainlifecycles` | Call graph and flows as text via DLC static analysis | "who calls X", "what happens after command Y", impact of a change |
| `dlc-diagrammer` | `domainlifecycles` | Domain and flow diagrams, mirror export (Diagram Viewer upload once released) | "diagram", "visualise", "draw the flow of X" |
| `dlc-project-setup` | `domainlifecycles` | Mode decision (A/B/C), adding DLC, A -> B migration, persistence backend, bootstrap, upgrades | new project / migration / upgrade |
| `new-aggregate` | `domainlifecycles` | Explicit workflow: model -> implement -> test | manual (`/new-aggregate`); Claude Code never triggers it automatically (`disable-model-invocation`), other agents may |

Modes are cumulative: **A** plain DDD (only `ddd-tactical-java`) ⊂ **B** DLC marker
types ⊂ **C** DLC runtime. All DLC skills build on `domainlifecycles`, which always
loads `ddd-tactical-java` first; `ddd-tactical-java` never references DLC, so it can
be used in any Java project.

```
.claude-plugin/marketplace.json     Claude Code marketplace (2 plugins)
skills/
  ddd-tactical-java/                SKILL.md + references/modeling-checklist.md
  domainlifecycles/                 SKILL.md (router) + references/<one file per DLC module>
  dlc-persistence-schema/           SKILL.md + references/ddl-example.md
  dlc-impact-analysis/
  dlc-diagrammer/
  dlc-project-setup/
  new-aggregate/
templates/
  AGENTS.md.snippet                 project decisions + skill-loading line for AGENTS.md
  claude-settings.json              .claude/settings.json, latest + auto-update
  claude-settings.pinned.json       .claude/settings.json, pinned release
evals/
  prompts.md                        description of all evals, checklist for other agents
  suite.json                        automated cases (all sections)
  generate.py, run.sh               generate cases + run `claude plugin eval`
CHANGELOG.md                        releases
```

## Installation

The repository is the distribution: everything on GitHub is immediately installable.
There is no registry to publish to. If the repository is private, users need read
access to it (their Git credentials are used).

### Claude Code (recommended) - plugin marketplace
The marketplace is `dlc-plugins` (`.claude-plugin/marketplace.json`) with two plugins:

| Plugin | Skills |
|---|---|
| `ddd-tactical-java` | `ddd-tactical-java` |
| `domainlifecycles` | `domainlifecycles`, `dlc-persistence-schema`, `dlc-impact-analysis`, `dlc-diagrammer`, `dlc-project-setup`, `new-aggregate` (enable together with `ddd-tactical-java`) |

**Per project (preferred):** commit one of the templates as `.claude/settings.json`
(or merge it into an existing one). Team members are offered the marketplace once
they trust the project folder.

| Template | Behaviour |
|---|---|
| `templates/claude-settings.json` | follows `main` (latest), auto-update on |
| `templates/claude-settings.pinned.json` | fixed release via `"ref": "vX.Y.Z"`, updated deliberately |

Plain-DDD projects without DLC only enable `ddd-tactical-java@dlc-plugins`.

**Manually / fallback** (if the project settings are not picked up):
```bash
claude plugin marketplace add esentri/DLC-Skills          # latest
claude plugin marketplace add esentri/DLC-Skills#v1.0.0   # pinned release
claude plugin install ddd-tactical-java@dlc-plugins
claude plugin install domainlifecycles@dlc-plugins
```

### Other agents (Codex, Cursor, Windsurf, ...) - `npx skills`
The [skills CLI](https://github.com/vercel-labs/skills) (Vercel, open source) clones
the repository directly from GitHub and installs every `skills/<name>/SKILL.md` -
nothing has to be registered anywhere.

```bash
# into the current project (default), all skills of this repo
npx skills add esentri/DLC-Skills --skill '*'

# plain DDD projects: only the framework-agnostic skill
npx skills add esentri/DLC-Skills --skill ddd-tactical-java

# options: -a <agent> (e.g. -a codex -a cursor), -g (global, user directory),
#          --copy (copy instead of symlink), -y (no prompts)
```
- Project installs land in the agents' skill directories inside the project and can
  be committed - then the whole team has the same state without running the CLI.
- **No automatic updates:** run `npx skills update` (`-p` project, `-g` global)
  regularly, or after each release listed in `CHANGELOG.md`.
- Pinning a release is not documented by the CLI; use the plugin marketplace if a
  project needs a fixed version.
- Telemetry: the CLI sends anonymous usage data (for public GitHub repositories incl.
  repo/skill identifiers). Disable with `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`.

## Updates

| Channel | How users receive changes |
|---|---|
| Plugin, latest + auto-update | automatically, a few minutes into a session; active after restart or `/reload-plugins` |
| Plugin, latest without auto-update | `claude plugin marketplace update dlc-plugins`, then `claude plugin update domainlifecycles@dlc-plugins` (and `ddd-tactical-java@dlc-plugins`), then `/reload-plugins` |
| Plugin, pinned | change `"ref"` in `.claude/settings.json` to the new tag, then update as above |
| `npx skills` | `npx skills update` |

Auto-update is **off by default** for team marketplaces. It can also be switched on
per user via `/plugin` -> Marketplaces -> `dlc-plugins` -> Enable auto-update.
(Verify that your Claude Code version honours the `autoUpdate` key in
`extraKnownMarketplaces`; otherwise use the menu.)

## Releases & versioning

- **`main` is the latest state.** The marketplace entries deliberately carry no
  `version` field, so Claude Code uses the commit SHA as version - every merged
  change reaches "latest" users without a manual version bump. (If a `version` were
  set, changes would only be delivered after bumping it.)
- **Releases are Git tags** `vMAJOR.MINOR.PATCH`, documented in `CHANGELOG.md`:
  - **MAJOR** - a rule changes in a way that changes generated code
    (e.g. transaction or validation rules, a removed convention),
  - **MINOR** - new skill, new reference, new rules that extend existing behaviour,
  - **PATCH** - corrections, clarifications, wording.
- **DLC coupling:** every release names the DomainLifeCycles version it targets
  ("Targets DLC 3.5.x" in `CHANGELOG.md`, README and the skills). A new DLC minor
  with API changes is at least a MINOR release of the skills. Only if older DLC
  lines must be supported in parallel, a maintenance branch (e.g. `dlc-3.5`) is
  created and tagged from there.
- **Release channels:** not used yet. If needed, follow the Claude Code pattern of a
  second marketplace with its own `name` pointing to a different ref (e.g. `stable`).

### Release checklist
1. Changes merged to `main`, `claude plugin validate .` passes.
2. Run `evals/run.sh` (automated suite) and check #37 manually.
3. Move the `[Unreleased]` entries in `CHANGELOG.md` to the new version with date
   and targeted DLC version.
4. Tag and push: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.
5. Bump the `ref` in `templates/claude-settings.pinned.json` and in the examples
   of this README.
6. Announce the release (pinned projects update deliberately).

## Evals

Skills are prompts - whether they fire for the right requests (and stay silent for
the wrong ones) has to be measured, not assumed. `evals/` holds four kinds of evals:

| Section in `evals/prompts.md` | What it checks | How it runs |
|---|---|---|
| 1. Triggering | the right skills (and reference files) load for a request, incl. German prompts | automated |
| 2. Negative tests | skills stay silent: no DLC in plain-DDD projects, nothing for non-domain tasks, `new-aggregate` never auto-invoked | automated |
| 3. Activation via `AGENTS.md` | the skill-loading line and project overrides (event publishing, legacy contexts, validation style, mode) take effect | automated (except #37) |
| 4. Rule adherence | generated code follows the team rules (events with IDs only, domain service for multi-aggregate transactions, read models, ports, `@BoundedContext`, ...) | automated |

### Automated suite
Uses Claude Code's [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals).

```
evals/suite.json        all cases: prompt, mode, expected / forbidden skills, references,
                        AGENTS.md overrides, answer regexes, LLM-judge rubrics
        |  evals/generate.py
        v
evals/cases/<case>/     case.yaml (prompt, limits, graders) + setup.sh (scaffolds the sample project)
        |  evals/run.sh
        v
evals/.build/dlc-skills temporary plugin with all skills + cases -> claude plugin eval
        v
evals/results/<timestamp>/report.html, aggregate-result.json
```

- **One source of truth:** add or change cases only in `evals/suite.json`;
  `evals/cases/` is generated (and git-ignored). `run.sh` regenerates on every run.
- **Sample projects:** each case scaffolds a small Java project in its mode -
  `none` (empty project, no `AGENTS.md`), `A` (plain DDD), `B` (DLC marker types),
  `C` (Spring Boot 4 + DLC `spring-boot-starter` + jOOQ, Java 21) - with `pom.xml`, `AGENTS.md` and a few domain
  classes, so the skills' mode detection has real evidence.
- **Graders:**
  - skills: expected skills must be loaded (`tool_used: Skill`), forbidden skills
    must not be, expected reference files must be read (weight 0.5);
    `new-aggregate` is forbidden in every case,
  - rules: regexes over the final answer (`answer_must` / `answer_must_not`,
    deterministic) and, for rules a regex can't express, an LLM judge (`judge`,
    Haiku, PASS in 2 of 3 votes, < 0.01 USD per run).
- **AGENTS.md variants:** `agents` overrides single lines of the scaffolded
  `AGENTS.md` (e.g. `Event publishing`, `Legacy contexts`, `Mode`); `legacy` adds a
  non-DDD legacy context to the sample project.
- **Read-only runs:** only read tools are allowed. Triggering prompts end with "Do
  not modify any files - explain how you would do it."; rule prompts ask for the
  complete code in the answer, which the graders check. No baseline arm without the
  plugin (`--ablation none`).
- **Why the build step:** the repository root is a marketplace whose plugins share
  `"./"` as source without a `plugin.json`; `claude plugin eval` does not load such
  a root. `run.sh` therefore assembles one temporary plugin containing all skills -
  the same combination a DLC project enables.

Running:
```bash
evals/run.sh --runs 1                         # all 52 cases once (~15 USD)
evals/run.sh                                  # 3 runs per case (default, ~45 USD)
evals/run.sh --case 't1*' --runs 1            # subset by case name (one --case only)
evals/run.sh --tag rules                      # triggering | negative | agents-md | rules | mode-a/-b/-c/-none
evals/run.sh --threshold 0.8 --max-cost-usd 20 --json results.json   # CI
```
Each run is a full Claude Code session on your own credentials (~0.2-0.4 USD per run).
Triggering is probabilistic - single failures happen; judge a case over its 3 runs.
Exit code 0 = all cases at or above `--threshold` (default 1.0), 1 = below / error,
2 = cost ceiling hit. Open `evals/results/<timestamp>/report.html` for per-case
grader verdicts.

Adding a case: append an entry to `evals/suite.json` (`id`, `mode`, `prompt`,
`expect`, optional `section`, `forbid` - `"*"` = all skills -, `reads`, `agents`,
`legacy`, `answer_must`, `answer_must_not`, `judge`, `note`; see the docstring of
`evals/generate.py`), then run it alone, e.g. `evals/run.sh --case 'r55*' --runs 1`.
Add `--keep-temp` to inspect a run's trace.

Reading results: a skill missing in many cases -> sharpen its `description`; two
skills competing for the same prompts -> merge them or separate their trigger words;
a forbidden skill firing -> narrow its description.

### Manual
- **#37** (no skill-loading line in `AGENTS.md`): `claude plugin eval` does not
  auto-load `AGENTS.md` or `CLAUDE.md`, so this can only be checked in a real
  project session.
- **Other agents** (Codex, Cursor, ...): `claude plugin eval` only covers Claude
  Code - use the tables in `evals/prompts.md` as a checklist (the scaffolds from
  `evals/cases/*/setup.sh` can be reused).

## Project configuration
Copy `templates/AGENTS.md.snippet` into the project's `AGENTS.md` (read by Claude
Code, Codex, Cursor ...; let `CLAUDE.md` import it with `@AGENTS.md` instead of
duplicating it). It holds only project decisions, never library knowledge:

| Field | Purpose |
|---|---|
| skill-loading line | makes the agent load `ddd-tactical-java` (+ `domainlifecycles`) for any domain work - prompts rarely mention "DLC", so this is what reliably activates the DLC skills |
| `Mode` | A / B / C - overrides the build-file detection |
| `Domain base package` | root package of the domain model |
| `Persistence` | jOOQ / JDBC / none |
| `Validation style` | extender + Bean Validation / `BeanValidations.validate` / DomainAssertions / Java exceptions |
| `Event publishing` | `DomainEvents` / Spring `ApplicationEventPublisher` |
| `Package layout` | default (from `ddd-tactical-java`) or a described deviation |
| `Legacy contexts` | contexts where the skill rules are not binding |
| `Code language` | language of domain terms, umlaut replacement in identifiers |
| `Deviations from the skills` | conscious exceptions to skill rules |

`dlc-project-setup` fills it in when setting up a project.

## Development
- Keep every `SKILL.md` well below 500 lines; details go into `references/`.
- Record every change under `[Unreleased]` in `CHANGELOG.md`.
- Source of truth for DLC facts: upstream `llms.txt`, module readmes and - where the
  docs are ambiguous - the DLC source code. Team decisions that deliberately deviate
  from upstream examples (e.g. events carry IDs only, public `@Builder`
  constructors) stay as they are.
- Validate before pushing: `claude plugin validate .`
- Run the evals (see "Evals") after changing a skill `description` or adding a skill.
- On a DLC release: update version references (`grep -rn "3\.5" skills`) and
  check the upstream `CHANGELOG.md` for API changes.
