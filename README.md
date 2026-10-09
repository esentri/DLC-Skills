# DLC-Skills
Tactical DDD Implementation Skills with DLC

Agent skills for tactical Domain-Driven Design in Java, with and without
[DomainLifeCycles (DLC)](https://github.com/esentri/domainlifecycles).
Written in the open [Agent Skills](https://agentskills.io) format (`skills/<name>/SKILL.md`),
so they work in Claude Code, Codex, Cursor and other agents.

Targets **DLC 3.5.x**.

## Skills

| Skill | Purpose | Triggered by |
|-------|---------|--------------|
| `ddd-tactical-java` | Framework-agnostic tactical DDD rules and modelling checklist | DDD vocabulary (aggregate, invariant, value object ...) |
| `domainlifecycles` | DLC marker types and runtime modules; detects mode A/B/C from the build file and loads only the references for modules in use | `io.domainlifecycles` in the build, "DLC" |
| `dlc-diagrammer` | Domain diagrams, flow diagrams, mirror export, Diagram Viewer upload | "diagram", "visualise", "draw the flow of X" |
| `dlc-persistence-schema` | Tables, sequences, FKs and migrations for DLC aggregates; jOOQ codegen; mapping errors | "migration", "table for aggregate", codegen / mapping errors |
| `dlc-impact-analysis` | Call graph and flows as text via DLC static analysis | "who calls X", "what happens after command Y", impact of a change |
| `dlc-project-setup` | Mode decision (A/B/C), adding DLC, A -> B migration, persistence backend, bootstrap | new project / migration / upgrade |
| `new-aggregate` | Explicit workflow: model -> implement -> test | only manual (`/new-aggregate`) |

Modes inside `domainlifecycles` are cumulative: **A** plain DDD ⊂ **B** DLC marker
types ⊂ **C** DLC runtime. `domainlifecycles` always loads `ddd-tactical-java` first;
`ddd-tactical-java` never references DLC.

```
.claude-plugin/marketplace.json     Claude Code marketplace (2 plugins)
skills/
  ddd-tactical-java/                SKILL.md + references/modeling-checklist.md
  domainlifecycles/                 SKILL.md (router) + references/<one file per DLC module>
  dlc-diagrammer/
  dlc-persistence-schema/           SKILL.md + references/ddl-example.md
  dlc-impact-analysis/
  dlc-project-setup/
  new-aggregate/
templates/                          AGENTS.md snippet, .claude/settings.json for projects
evals/prompts.md                    trigger smoke tests
```

## Installation

### Claude Code (recommended)
Per project - commit `templates/claude-settings.json` as `.claude/settings.json`
(or merge it in). Team members get the marketplace offered when they trust the folder.

Manually / fallback:
```bash
claude plugin marketplace add esentri/DLC-Skills
claude plugin install ddd-tactical-java@dlc-plugins
claude plugin install domainlifecycles@dlc-plugins
```
Plugins without a `version` follow the latest commit. Pin with a git tag via
`"ref"` in the marketplace source if a project needs a fixed DLC version.

### Other agents (Codex, Cursor, ...)
```bash
npx skills add esentri/DLC-Skills --skill ddd-tactical-java --skill domainlifecycles
```
Update regularly with `npx skills update` - copied skills do not update themselves.

## Project configuration
Put project decisions (mode, base package, persistence backend) into the project's
`AGENTS.md`, not into the skills - see `templates/AGENTS.md.snippet`. Keep it to a few lines.

## Development
- Keep every `SKILL.md` under ~200 lines; details go into `references/`.
- Source of truth for DLC facts: upstream `llms.txt` and module readmes.
- Validate before pushing: `claude plugin validate .`
- Check triggering with the prompts in `evals/prompts.md` in each supported agent.
- On a DLC release: update version references (`grep -rn "3\.5" skills`) and
  check the upstream `CHANGELOG.md` for API changes.
