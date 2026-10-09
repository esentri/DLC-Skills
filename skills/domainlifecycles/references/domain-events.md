# Domain events (Mode C)

Modules: `domain-events-core` plus integrations (`domain-events-spring-bus`,
`domain-events-spring-tx`, `domain-events-jakarta-jta`, `domain-events-gruelbox`,
`domain-events-mq`, `domain-events-activemq-classic5`, `domain-events-jakarta-jms`).
`domain-events-serialization-jackson*` are internal - don't add them yourself.
Upstream: `domain-events-core/readme.md`.
Only the Spring event bus (default) and in-memory are autoconfigured; Gruelbox,
JMS, ActiveMQ and JTA setups need their beans defined by the application.

## Publishing mechanism - check AGENTS.md first

The project's `AGENTS.md` field `Event publishing` decides:
- `DomainEvents` (default) -> static DLC API as below.
- `Spring ApplicationEventPublisher` -> inject `ApplicationEventPublisher` into
  the publishing service (domain or application service) and call
  `publishEvent(event)` there; aggregates return or collect the event instead of
  publishing themselves. Don't introduce `DomainEvents.publish` in such projects.

The event rules (past-tense name, record implementing `DomainEvent`, IDs +
minimal data, `@Publishes` on the publishing method) apply either way.

## Publishing with DomainEvents
```java
public Order ship() {
    ...
    DomainEvents.publish(new OrderShipped(id));
    return this;
}
```
- Static API, no publisher injection.
- Allowed publishers: aggregate roots, entities, domain services and application
  services - always **after** the successful state change.
- Annotate the publishing method with `@Publishes(domainEventTypes = OrderShipped.class)`
  so the Mirror and diagrams know the flow.

## Listening
```java
@DomainEventListener
public void onOrderShipped(OrderShipped event) { ... }
```
- Preferred listeners: application services, domain services and aggregate roots.
  Also supported: repositories (e.g. projecting read models), outbound services
  and query handlers.
- Service listener methods have exactly one parameter, the event; the service
  must be registered with DLC (Spring: autoconfig picks up the beans).
- **Aggregate roots as listeners** require the event to implement
  `AggregateDomainEvent<ID, A>` with `targetId()`. DLC loads the aggregate via its
  repository, calls the listener and updates it in a separate transaction - this
  needs a **transactional** DomainEvents setup:
  ```java
  public record FraudDetected(Customer.CustomerId customerId)
          implements AggregateDomainEvent<Customer.CustomerId, Customer> {
      @Override public Customer.CustomerId targetId() { return customerId; }
  }

  // in Customer
  @DomainEventListener
  public void onFraudDetected(FraudDetected event) { block(); }
  ```
- A listener modifies one aggregate; if it must change several in one
  transaction, it delegates to a domain service.

## Spring Boot default: Spring event bus
- `DomainEvents.publish` hands events to Spring's `ApplicationEventPublisher`.
- Each `@DomainEventListener` is called **after commit, asynchronously, in its own
  transaction** (`REQUIRES_NEW`). A listener failure does not roll back the
  publisher.
- In-memory events instead: `dlc.features.events.inmemory.enabled=true`.

## Channels and routing (manual configuration)
- A channel factory creates the channels. Concrete factories, e.g.
  `InMemoryChannelFactory`, `SpringTxInMemoryChannelFactory`,
  `SpringApplicationEventsPublishingChannelFactory`, `JtaInMemoryChannelFactory`,
  `GruelboxChannelFactory`, plus JMS/ActiveMQ variants.
- Channel kinds: processing channel (`factory.processingChannel(name)`, publish and
  consume inside the application), publishing channel (`factory.publishOnlyChannel(name)`,
  type `PublishingChannel`, forwards to a broker), consuming-only channel.
- A `PublishingRouter` (e.g. `DomainEventTypeBasedRouter`) maps event types to
  channels: `defineDefaultChannel(...)`, `defineExplicitRoute(EventType.class, "channel")`.
  The router only takes effect wrapped in `new ChannelRoutingConfiguration(router)`.
- Upstream JTA docs once name `JakartaJmsChannelFactory` for the JTA in-memory
  setup - the correct class is `JtaInMemoryChannelFactory`.

## Transactional outbox
For reliable delivery to external brokers use `domain-events-gruelbox`
(Gruelbox Transactional Outbox). Events are stored in the same DB transaction as
the aggregate.

## Rules
- Event name = past-tense fact; immutable record.
- Payload = typed IDs + minimal data (value objects). Never aggregates or entities -
  also not for in-memory channels (upstream examples like `OrderShipped(Order order)`
  are not to be copied).
- Don't rely on in-memory, non-transactional channels for cross-aggregate
  consistency in production.
