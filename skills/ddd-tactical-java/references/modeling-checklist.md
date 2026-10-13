# Modelling checklist

Work through this with the developer before writing code. Write the answers down
(in the conversation or an ADR), so the implementation can be checked against them.

## 1. Ubiquitous language
- [ ] Which business terms appear in the request? Are they unambiguous?
- [ ] Which bounded context do they belong to? Does a term mean something
      different in another context?
- [ ] Which package is the context's root package?

## 2. Invariants
For each candidate aggregate:
- [ ] Which rules must be true immediately after every change?
- [ ] Which rules may be violated briefly and repaired later (eventual)?
      -> These do **not** justify a bigger aggregate.

## 3. Aggregate boundary
- [ ] Which objects must change together to keep the invariants?
- [ ] Is the aggregate still small enough to load and lock as a whole?
- [ ] Which references point to other aggregates? -> Replace with typed IDs.

## 4. Lifecycle
- [ ] Which states does the root go through? Which transitions are allowed?
- [ ] Which transitions are business facts **someone reacts to**? Only those with a
      listener (name it) become domain events.
- [ ] Which business intents trigger the transitions? -> commands, named in the
      imperative (`CancelOrder`, `CheckeEin`).

## 5. Identity and value objects
- [ ] Who generates the ID (client, DB sequence, factory)?
- [ ] Which attributes are value objects? Which primitives carry meaning?

## 6. Creation
- [ ] Constructor, factory method on the root/another aggregate, or a dedicated
      factory? (see "Factories" in SKILL.md)

## 7. Collaboration
- [ ] Which use cases (application services) change this aggregate?
- [ ] Which other aggregates react to its events?

## Done when
Every invariant from section 2 can be pointed to in a method of the aggregate root
or a value object constructor.
