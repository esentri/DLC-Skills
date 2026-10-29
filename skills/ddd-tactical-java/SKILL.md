---
name: ddd-tactical-java
description: Tactical Domain-Driven Design in Java, independent of any framework. Use when modelling, implementing or reviewing domain code: aggregates, entities, value objects, typed IDs, invariants, domain events, domain services, factories and factory methods, repositories, application services, domain commands, read models and query handlers, outbound ports/adapters, bounded contexts and communication between them (events, anti-corruption layer). Also for deciding aggregate boundaries and spotting DDD smells such as anemic models (German: Aggregat, Entitaet, Wertobjekt, Invariante, Fachmodell, Fachlogik, Bounded Context, Kontextgrenze, Anwendungsservice, Lesemodell, Befehl, Fabrik).
---

# Tactical DDD in Java

These rules apply in every Java project, with or without a DDD library.
Library-specific skills build on top of these rules and never replace them.

## Workflow: model first, code second

1. **Clarify the language.** Name the concepts with the domain expert's terms. If a
   term is ambiguous, ask instead of inventing one. If the project has a glossary
   (`Glossary:` in `AGENTS.md`, default `docs/ubiquitous-language.md`):
   - use its `confirmed` terms; never a term listed under `Avoid` or `deprecated`
     (a `deprecated` row names the term to use in `Replaced by`),
   - every new domain concept you introduce (type, event, command, business
     method) -> append it as a `candidate` row (format and rules: skill
     `ubiquitous-language`); no questions, never mark anything `confirmed`,
   - list the added candidates in one line at the end of your answer.
   No glossary file -> the glossary rules don't apply: don't create one, don't
   write glossary rows or candidate lists in the answer.
2. **Find the invariants.** List the business rules that must hold *at all times*
   (not "eventually"). These decide the aggregate boundaries.
3. **Cut the aggregates.** One aggregate = one consistency boundary. Keep it as
   small as the invariants allow.
4. **Choose identity and value objects.** Everything without its own lifecycle
   becomes a value object.
5. **Only then write code.** Check every invariant from step 2 is enforced inside
   the aggregate, not in a service or controller.

For a guided checklist see `references/modeling-checklist.md`.

## Bounded contexts

- Each bounded context is a **separate package** (one root package per context,
  e.g. `com.example.shop.ordering`, `com.example.shop.shipping`). Context packages
  are never nested in one another.
- A term means exactly one thing inside its context; the same word may mean
  something different in another context - model it twice rather than sharing.
- No direct code references between contexts' domain models. Cross-context
  communication goes through IDs, domain events or explicit translation
  (anti-corruption layer / outbound ports).
- **Asynchronous (domain events)** is the default for propagating state changes.
  **Synchronous via an outbound port** is fine when a business decision needs an
  immediate answer from the other context (credit check, current price,
  availability) - see "Outbound ports" for the rules.
- Shared kernel only by explicit decision, in its own package.

## Invariants

- Check invariants in the **constructor** - an object must never exist in an
  invalid state. State-changing methods guard their preconditions the same way.
- Without a DDD library: guard clauses throwing standard Java exceptions
  (`IllegalArgumentException` for invalid input, `IllegalStateException` for
  forbidden state transitions, `NullPointerException` via `Objects.requireNonNull`).
- A library-specific skill may define its own mechanism; the
  project's `AGENTS.md` decides the preferred style and wins over both.

## Building block rules

### Value objects
- Immutable. Prefer Java `record`s; otherwise all fields `final`.
- Equality by value only.
- Validate in the constructor (compact record constructor) - an invalid value
  object must never exist.
- Put behaviour on them (`Money.add`, `DateRange.overlaps`), not in utility classes.
- Methods are side-effect free: they never change state, they return a new instance.
- Replace primitives that carry meaning (`String email`, `BigDecimal amount`) with
  value objects.

### Identities
- Typed IDs per entity: `record OrderId(UUID value)`, never raw `Long`/`UUID`/`String`.
- Every entity - including entities inside an aggregate - has a **globally unique**,
  immutable ID, not just one unique within its aggregate.
- Nest the ID type in its entity or put it next to it in the same package.

### Entities
- Equality and `hashCode` based on identity only.
- State changes only through intention-revealing methods (`ship()`, `cancel()`),
  no public setters.
- Behaviour that touches only the entity lives in the entity.
- Inner entities are invisible from outside the aggregate: no external service
  holds a reference to them or manipulates them - every interaction goes
  through the root, which orchestrates them.
- Their lifecycle is bound to the root: deleting the root deletes them.
- Inner entities protect their own invariants too - no method call may leave
  them in an invalid state.

### Aggregates
- Exactly one aggregate root; the outside world talks only to the root.
- **Keep aggregates small:** an aggregate is a minimal consistency boundary, not a
  folder for everything related. It contains only what must be consistent
  atomically and synchronously.
- **Tell, don't ask:** don't pull data out of an aggregate to decide outside;
  call a method and let the aggregate decide based on its own state.
- No "empty" objects: constructors enforce the initial validity.
- Pure: no infrastructure dependencies and no repository calls inside an aggregate.
- Inner entities are never handed out for modification; expose read-only views
  (unmodifiable collections).
- **Reference other aggregates by ID only**, never by object reference.
- A use case changing **one** aggregate needs no domain service: the application
  service loads it, calls the domain method and stores it.
- Several aggregates may change in the **same transaction** only when a domain
  service coordinates them. Otherwise cross-aggregate consistency is eventual,
  via domain events. Using domain events and eventual consistency is preferred.
- The root enforces all invariants of the aggregate after every operation.
- Optimistic locking (a version field) on the root protects the boundary.

### Domain events
- **Only where someone listens.** Model an event only if there is (or is built in
  the same change) at least one listener reacting to it - in this or another
  bounded context, or a concrete consumer behind an outbox/broker. Not every state
  transition is an event: no "just in case" events without a listener. When
  introducing an event, name its listener(s).
- Named as a past-tense fact: `OrderShipped`, `PaymentReceived`.
- Immutable.
- Carry **only IDs and the minimal data** listeners need (typed IDs, value objects).
  Never put aggregates or entities into an event.
- Raised where the fact happens: aggregate root, entity, domain service, or an
  application service after a successful use case step.

### Domain services
- Only for domain logic that does not naturally belong to one entity or value object.
- Stateless. Named in the ubiquitous language (`RoomAssignment.findBestRoom()`).
- May use repository **interfaces** of the domain layer to load and store
  aggregates.
- The place to coordinate changes to **more than one aggregate in one
  transaction** - that is the main reason for a domain service besides logic
  that fits no single aggregate.
- May call **outbound port interfaces** when a business rule needs a synchronous
  answer from an external system. Never a concrete adapter or technology: no
  e-mail clients, no transaction handling, no SQL, no framework APIs.

### Factories
- Choose the simplest creation that keeps the object valid:
  1. Constructor - if creation is trivial.
  2. **Factory method** with a name from the ubiquitous language - a static method
     on the aggregate root, entity or value object (`Order.place(...)`), or a method
     of an aggregate creating an object it is responsible for
     (`calendar.planAppointment(...)` creating an `Appointment` aggregate).
  3. **Dedicated factory** class - if creation is complex, spans several objects,
     picks the concrete type, or needs other services (e.g. an ID from a repository).
- A dedicated factory only creates; it has no other responsibilities.
- A factory (method) returns a fully valid object, never a half-built one.
- Builders are a technical construction aid, not a factory - don't model domain
  creation as builder calls scattered across services.

### Repositories
- One per aggregate root, never for inner entities or value objects.
- Interface in the domain layer, implementation in infrastructure.
- Load and store whole aggregates; collection-like API
  (`findById`, `insert`, `update`, `deleteById`), no generic query builders.
- Always return the **complete** aggregate - never fragments or projections.
- No infrastructure leaks in the interface: no JPA criteria, SQL fragments or
  framework types.
- Business filters to load aggregates for an operation are fine
  (`findOverdueCancellations()`); dashboard or UI queries spanning several
  aggregates go to read models / query handlers.

### Application services
- Coordinate, don't decide: load aggregate, call domain method, store. Only
  process flow ("if the booking exists, check in"), business rules stay in
  aggregates and domain services.
- May call repositories, query handlers and outbound ports directly - no domain
  service needed for single-aggregate commands or read-only use cases.
- Never changes several aggregates itself - delegate that to a domain service.
- Own the transaction - one use case is atomic.
- Bridge to infrastructure: trigger confirmation e-mails, external APIs and
  event publishing via outbound ports.
- Input: domain commands (or simple DTOs mapped to commands). Output: the
  aggregate (see CQRS light under "Read models and query handlers"), a read model
  or a simple confirmation. Callers outside the use case never modify a returned
  aggregate - changes always go through a command.
- Authentication and authorization ("may this user execute this command?") are
  checked here or in interceptors in front of it.

### Outbound ports
- Not a DDD building block but a port in the ports & adapters sense: a facade
  hiding communication with external systems (e-mail, third-party APIs,
  other contexts, external data sources).
- The port **interface** lives in the domain or application layer and speaks the
  ubiquitous language (`CustomerNotifier.notifyOrderShipped(...)`, not
  `sendSmtpMail(...)`); the implementation is an adapter in infrastructure.
- Called by application services; by domain services only when domain logic
  needs a synchronous external answer.
- May react to domain events for decoupled side effects (e.g. notifications).
- Aggregates never call outbound ports.

**Synchronous calls into another bounded context:**
- The port belongs to the **calling** context: its interface uses only the
  caller's language and types - never types of the other context.
- The adapter is the anti-corruption layer: it translates both ways and calls
  only the target context's public interface (application service, query
  handler, API) - never its aggregates, repositories or domain services, even
  inside a monolith.
- Prefer reads. A write in the other context is a separate transaction there;
  no transaction spans two contexts.
- Unavailability is modelled: the adapter handles it or the port returns a
  business result (`CreditRating.UNKNOWN`) - no technical exception reaches the
  aggregate.

### Domain commands
- Named after the business intent (`AssignRoom`), not the data change
  (`UpdateRoomRequest`).
- **Always grammatically imperative** - verb first, as an order to the domain:
  `AssignRoom`, `CancelOrder`, `CheckIn`; in German `WeiseZimmerZu`,
  `StorniereBestellung`, `CheckeEin`. Never a noun or nominalised infinitive
  (`Einchecken`, `Checkin`, `RoomAssignment`, `Stornierung`) and
  never past tense (that is an event).
- Immutable; one command = one business intent = one transaction.
- **Only syntactic validation** in the command: null, blank, format (regex), value
  ranges. No business logic and no checks against system state ("is the room
  free?") - that belongs in aggregates or domain services.
- Commands are part of the domain: created outside (e.g. in an application
  service) and passed into the core unchanged.

### Read models and query handlers
- **Default is CQRS light:** if a single aggregate satisfies the read need,
  return the aggregate (loaded via its repository) - no read model, no query
  handler.
- Introduce a read model + query handler **only** if the aggregate cannot
  structurally provide the information: data spanning several aggregates, only
  a part of an aggregate, or derived/aggregated values (sums, counts, ...).
  "The UI wants a different shape" alone is no reason - map in the adapter.
- `AGENTS.md` may demand a stricter rule ("never expose aggregates"): then
  aggregates never leave the application service, and every read goes through
  a read model + query handler.
- Read models are immutable, shaped purely for their consumer (UI, API client);
  flat or nested, whatever simplifies the client.
- May combine data from several aggregates (denormalised) - unlike aggregates.
- Provided by dedicated query handlers, **never by repositories**.
- Reuse domain value objects and typed IDs (consistent formatting and simple
  calculations), but add no new business logic or validation.
- Query handlers may bypass the domain model and use optimised queries
  (native SQL, views).

## Layering and package layout
- The domain layer has no dependency on persistence, web, messaging or framework
  annotations (except an explicitly chosen DDD library).
- Infrastructure depends on the domain, never the other way round.

Default layout per bounded context (ports & adapters; `AGENTS.md` may define
another one - then follow it):

| Package                 | Contains                                                    |
|-------------------------|-------------------------------------------------------------|
| `<bc>.core.application` | Application services (use cases, entry into the domain core) |
| `<bc>.core.domain`      | Aggregates, entities, value objects, domain services, events, commands, read models, and the **port interfaces**: repositories, query handlers, outbound services |
| `<bc>.inbound`          | Inbound adapters: REST controllers, inbound DTOs            |
| `<bc>.outbound`         | Outbound adapters: repository, query handler and outbound service implementations |
| `<bc>.configuration`    | Framework configuration (e.g. Spring `@Configuration`)      |

Dependency rules:
- `inbound` -> `core.application` only (never directly into the domain).
- `core.application` -> `core.domain`; never the reverse.
- `core.domain` knows neither `inbound`/`outbound` nor `configuration`.
- `outbound` implements port interfaces from `core.domain` (dependency points inwards).
- `configuration` stands outside the layers and may wire all of them.

## Legacy contexts
Contexts listed under `Legacy contexts` in `AGENTS.md` don't follow these rules.
Work with their existing structure there; don't restructure them unasked.

## Review red flags
- Anemic entities with getters/setters and logic in `*Service` classes.
- An aggregate holding a Java reference to another aggregate root.
- An application service changing several aggregates itself instead of via a
  domain service.
- `String`/`Long` parameters where a value object or typed ID belongs.
- Validation only in the controller or DTO layer.
- Repositories for non-root entities.
- Domain events without any listener.
- Commands not named in the imperative (`Einchecken`, `OrderCancellation`
  instead of `CheckeEin`, `CancelOrder`).
- A domain class of one bounded context referencing a type of another context.
- A cross-context adapter calling the other context's repositories or aggregates.
