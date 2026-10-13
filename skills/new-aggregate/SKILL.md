---
name: new-aggregate
description: Guided end-to-end workflow for a new aggregate - from domain modelling to a tested implementation (with DomainLifeCycles if the project uses it). Invoke explicitly, e.g. "/new-aggregate Order".
disable-model-invocation: true
---

# New aggregate: model -> implement -> verify

Follow the steps in order. Don't write production code before step 2 is confirmed.

1. **Load `ddd-tactical-java`.** Work through its
   `references/modeling-checklist.md` with the developer: language, invariants,
   boundary, lifecycle, IDs, value objects, events.
2. **Summarise the model** (roots, entities, value objects, invariants, events,
   references by ID) in max. 15 lines and get confirmation.
3. **Load `domainlifecycles`** and determine the mode from the build file.
   Mode A -> plain Java following `ddd-tactical-java` only.
4. **Implement** in the bounded context's package, in this order: identities and
   value objects -> entities -> aggregate root with invariants -> creation
   (constructor, factory method or factory) -> domain events (only those with a
   listener) -> repository interface ->
   (Mode C) repository implementation, schema migration (load
   `dlc-persistence-schema`), application service.
5. **Test:** one unit test per invariant (it must fail when violated);
   Mode C additionally an insert/find round-trip.
6. **Cross-check:** every invariant from step 2 is enforced in the aggregate or a
   value object; no object references to other aggregates; changes to several
   aggregates in one transaction only via a domain service; every domain event
   has a listener; commands are named in the imperative.
