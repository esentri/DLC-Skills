# Evals

All sections are automated for Claude Code with `claude plugin eval`, except #37
(see below). The cases live in **`evals/suite.json`** (single source of truth); the
tables here describe them and serve as a manual checklist for other agents
(Codex, Cursor, ...): run each prompt in a sample project of the given mode and
check whether the expected skills load and the result follows the rule.

Sample projects: **A** = plain Java, no DLC; **B** = DLC `types`/`type-utils`;
**C** = Spring Boot 4 + DLC `spring-boot-starter` + jOOQ (unless stated otherwise). Unless the column
`AGENTS.md` says otherwise, the project's `AGENTS.md` contains the snippet from
`templates/AGENTS.md.snippet` with the matching mode.

Rule of thumb: two skills competing for the same prompt -> merge them or sharpen
the descriptions; a skill used only partially in most prompts -> split it further.

## Running the automated suite

```bash
evals/run.sh --runs 1                 # all cases once
evals/run.sh                          # 3 runs per case (default)
evals/run.sh --tag rules --runs 1     # one section: triggering | negative | agents-md | rules
evals/run.sh --case 'r4*'             # subset by case name (only one --case is honoured)
```

| Section | Cases | Case names | Graders |
|---|---|---|---|
| 1. Triggering | #1-#31 | `t..` | expected skills loaded, forbidden not loaded, references read |
| 2. Negative tests | #32-#35 (+ `new-aggregate` forbidden everywhere = #36) | `n..` | forbidden skills not loaded |
| 3. AGENTS.md activation | #38-#42 | `a..` | skills + regexes / LLM judge on the answer, with per-case `AGENTS.md` variants |
| 4. Rule adherence | #43-#54 | `r..` | regexes on the answer (deterministic) + LLM judge (Haiku, 3 votes) for rules regexes can't express |

- `evals/generate.py` turns the JSON into `evals/cases/<case>/case.yaml` + `setup.sh`
  (scaffolds the sample project; `agents` overrides lines of `AGENTS.md`, `legacy`
  adds a non-DDD legacy context). `run.sh` regenerates automatically.
- Triggering / negative prompts end with "Do not modify any files - explain how you
  would do it."; agents-md / rules prompts with "... show the complete code in your
  answer" - all runs are read-only, rule checks grade the code in the final answer.
- Cost: roughly 0.2-0.4 USD per run, judge calls < 0.01 USD. Use `--runs 1` while
  iterating and `--max-cost-usd` in CI.
- Reports: `evals/results/<timestamp>/report.html` (git-ignored). Add `--keep-temp`
  to inspect a run's trace (`<kept dir>/out/trace.jsonl`).

## 1. Triggering and 2. Negative tests

See the cases `t..` / `n..` in `evals/suite.json`.

## 3. Activation via AGENTS.md

Automated as cases `a38`-`a42`. **#37 stays manual:** `claude plugin eval` never
loads `CLAUDE.md` or `.claude/` and does not auto-load `AGENTS.md` (the agent may
read it on its own), so "without the skill-loading line" cannot be measured
realistically in the sandbox - check it in a real project session.

| # | Prompt | Mode | AGENTS.md | Expected |
|---|--------|------|-----------|----------|
| 37 | Implement the Invoice aggregate | C | **without** the skill-loading line | baseline: note whether domainlifecycles loads at all (known gap) |
| 38 | Implement the Invoice aggregate | C | with the skill-loading line | ddd-tactical-java + domainlifecycles load |
| 39 | Publish an event when an invoice is paid | C | `Event publishing: Spring ApplicationEventPublisher` | uses `ApplicationEventPublisher` in a service; no `DomainEvents.publish` |
| 40 | Add a method to change the address in the umschreibungen context | C | `Legacy contexts: ...umschreibungen` | follows the existing structure, no restructuring |
| 41 | Add a value object Iban | C | `Validation style: DomainAssertions` | DomainAssertions in `validate()` called from the constructor; no extender, no `IllegalArgumentException` |
| 42 | Add a value object Iban | B | `Mode: A` (build file has DLC) | AGENTS.md wins: no DLC types |

## 4. Rule adherence (check the generated code)

Automated as cases `r43`-`r54`.

| # | Prompt | Mode | Check |
|---|--------|------|-------|
| 43 | When an order is shipped, notify shipping | C | event record implements `DomainEvent`, carries only IDs / minimal data (no `Order` inside); `@Publishes` on the publishing method |
| 44 | Placing an order must reserve stock in the Stock aggregate in the same transaction | C | coordination in a domain service, not in the application service |
| 45 | Add a use case to rename a customer | C | application service loads -> calls domain method -> updates; no domain service; parameter is a `DomainCommand` record |
| 46 | Add an OrderItem entity to Order | C | extends `EntityBase`; exactly one public all-args `@Builder` constructor; typed globally unique ID record; no public setters |
| 47 | Return order totals per customer for the UI | C | `ReadModel` record + `QueryHandler`, not a repository method returning projections |
| 48 | Reference the customer from the order | B | typed `CustomerId` field, no object reference to `Customer` |
| 49 | Add the PaymentGateway call for the order checkout | C | port interface extends `OutboundService` in `core.domain`, adapter in `outbound`; aggregate does not call it |
| 50 | Create the shipping bounded context | B | own root package with `package-info.java` + `@BoundedContext`; default package layout |
| 51 | Ordering needs the credit rating from billing | B | port owned by ordering with ordering types; adapter calls billing's application service / query handler only |
| 52 | Write the migration for an Order with a list of action code value objects | C | table `ORDER_ACTION_CODES` with `ID`, `CONTAINER_ID`, sequence or UUID id; NOT NULL FK; `concurrency_version` on entity tables only |
| 53 | Add the domain service OrderPricing in a Spring project | C | no `@Service` annotation (ServiceKind autoconfig registers it) |
| 54 | Who calls OrderService.place (it is overloaded)? | B | resolves all overloads via `getMethods()`, not the by-name `flowTo` only |
