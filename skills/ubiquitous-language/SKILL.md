---
name: ubiquitous-language
description: Maintain the project's ubiquitous language (UL) as a glossary file and check code against it. Two modes - "build" extracts domain terms from existing Java domain code into docs/ubiquitous-language.md (per bounded context, terms as candidates, asks the user about synonyms, ambiguous or unclear terms instead of guessing), "check" reviews code, a package or a change/diff against the glossary (avoided synonyms, deprecated terms, unknown domain terms, technical names in the domain, terms from another context). Framework-agnostic. Use for "create a glossary", "extract the domain terms", "check the naming against the ubiquitous language" (German: Glossar, Fachbegriffe, Ubiquitous Language, Begriffe sammeln, Fachsprache pruefen, Benennung pruefen).
---

# Ubiquitous language: glossary and checks

The glossary is the single written source of the domain terms. It is owned by the
team and the domain experts - the agent collects and checks, it never decides what
a term means.

## Glossary file

- Path: `Glossary:` in the project's `AGENTS.md`; default
  `docs/ubiquitous-language.md`. `Glossary: none` switches the feature off.
- Format: `references/glossary-template.md`. One section per bounded context (the
  same word may mean different things in two contexts), one table row per term.
- Written in the language of the domain experts (umlauts allowed); the `Code`
  column holds the identifiers as they appear in code (see `Code language` in
  `AGENTS.md`).
- Status per term:
  - `candidate` - found or introduced, not yet agreed. Anyone (also the agent) may add.
  - `confirmed` - agreed with the team. **Only the user confirms**.
  - `deprecated` - must no longer be used; `Avoid` / `Note` say what replaces it.
- Never delete or rewrite a `confirmed` row on your own; propose the change instead.

## Mode `build` - glossary from existing code

1. **Scope.** Ask which bounded contexts / packages if the project has several and
   the user didn't say. Default: all domain packages (`*.core.domain` in the
   default layout of `ddd-tactical-java`); skip `Legacy contexts` from `AGENTS.md`.
2. **Collect** per context: aggregates, entities, value objects, identities, enums
   and their constants, domain events, commands, domain services and their
   business methods, read models; Javadoc and class comments as definition
   sources. (DLC projects: the Domain Mirror lists the same types - optional.)
3. **Derive terms.** One row per *concept*, not per class: `Order`, `OrderId`,
   `OrderStatus`, `PlaceOrder`, `OrderPlaced` are one term "Order" plus the events
   / commands that name its lifecycle. Lifecycle verbs (`cancel`, `ship`) become
   terms of their own when they carry business meaning.
4. **Flag problems** (column `Open question`):
   - likely synonyms (`Customer` / `Client` / `Buyer`; `Kunde` / `Kaeufer`),
   - homonyms: same name, different meaning in two contexts - fine if separate
     sections, a problem inside one context,
   - technical names in the domain (`Manager`, `Handler`, `Data`, `Info`, `Helper`,
     `Util`, `Dto`, `Entity` suffixes),
   - mixed languages for one concept (`OrderPosition` next to `Bestellung`),
   - unclear abbreviations, generic words (`Item`, `Type`, `Status` without context),
   - commands not in the imperative, events not in past tense.
5. **Ask, don't guess.** Batch the open points into rounds of at most 4 questions
   (e.g. "Are Kunde and Kaeufer the same? Which term should stay?" with the options
   found in code). Definitions come from Javadoc or the user - never invent one;
   otherwise write `?` and keep the question in `Open question`.
6. **Write** the file (create `docs/` if needed). Existing file: merge - add new
   rows as `candidate`, update `Code` / `Open question` of existing rows, never
   overwrite definitions or status without asking. Apply the user's answers
   (`Avoid` gets the rejected synonyms). Report: terms added, questions still open.

Renaming code is **not** part of `build` - offer it as a separate step afterwards.

## Mode `check` - code against the glossary

1. **Target.** As given (files, package, class); default: uncommitted changes
   (`git diff HEAD`), or the branch against `main` if the user says "branch" /
   "PR". No glossary -> say so and offer `build`; don't check against guesses.
2. **Check** every domain identifier in the target (types, methods, fields,
   enum constants, packages):
   - uses a term from `Avoid` or a `deprecated` term -> finding with the
     replacement,
   - names a domain concept the glossary does not know -> new `candidate`
     (offer to add it),
   - uses a term of another context's section in this context -> finding (an
     outbound port / translation should use this context's language),
   - technical names in the domain, commands not imperative, events not past
     tense -> finding (rules: `ddd-tactical-java`),
   - code still uses a term whose glossary row is `candidate` with an open
     question -> mention, no finding.
3. **Report** findings as a list `file:line - identifier - problem - suggestion`,
   most important first; then the proposed new candidates. Change nothing
   automatically: offer to rename (and to add the candidates) after the report.

## While implementing (automatic candidates)

Applies whenever domain code is written and the glossary file exists (rule also
in `ddd-tactical-java`):
- Use `confirmed` terms; never a term from `Avoid` or a `deprecated` one.
- New domain concept you introduce (a type, an event, a command, a business
  method name not covered yet) -> append a `candidate` row with `Code` filled and
  `Definition` from the user's request or `?`. No questions, no confirmations.
- List the added candidates in one line at the end of the answer.
- No glossary file -> nothing of the above: don't create one, no glossary rows or
  candidate lists in the answer; at most mention `build` once.
