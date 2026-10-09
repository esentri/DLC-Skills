# Persistence (Mode C)

Modules: `jooq-integration` **or** `jdbc-integration` (same programming model).
Upstream: `persistence/readme.md`, `jooq-integration/readme.md`,
`jdbc-integration/readme.md`.

Tables, columns, sequences, migrations and jOOQ codegen: load the skill
`dlc-persistence-schema`.

## Choosing the backend
- Default: **jOOQ** (`JooqAggregateRepository`) - type-safe, needs jOOQ code
  generation at build time. DLC supports jOOQ 3.19.x and 3.21.x - on Java 21 the
  jOOQ version managed by Spring Boot 4.1 (3.21) is fine; Java 17 projects need
  jOOQ 3.19.x (jOOQ 3.21 requires Java 21).
- **JDBC** (`JdbcAggregateRepository`) if the team cannot or will not run jOOQ
  codegen (no build-time DB, licensing). Reads the schema at runtime.
- The Spring starters contain both; jOOQ wins when usable (see
  `spring-integration.md` for the toggles).

## Repository implementation

jOOQ:
```java
class JooqOrderRepository extends JooqAggregateRepository<Order, Order.OrderId>
        implements OrderRepository {

    JooqOrderRepository(DSLContext dslContext, JooqDomainPersistenceProvider provider,
                        PersistenceEventPublisher publisher) {
        super(Order.class, dslContext, provider, publisher);
    }

    @Override
    public Order.OrderId newOrderId() {
        return new Order.OrderId(dslContext.nextval(Sequences.ORDER_ID_SEQ));
    }
}
```
JDBC (no `DSLContext`):
```java
class JdbcOrderRepository extends JdbcAggregateRepository<Order, Order.OrderId>
        implements OrderRepository {

    JdbcOrderRepository(JdbcDomainPersistenceProvider provider,
                        PersistenceEventPublisher publisher) {
        super(Order.class, provider, publisher);
    }
}
```
- Inject the interface `PersistenceEventPublisher`; an implementation such as a
  Spring-based publisher is application code.
- Own SQL in a JDBC repository uses `provider.connectionProvider` / `.dialect` /
  `.schemaMetadata`.
- Interface stays in the domain layer, implementation in infrastructure. With the
  Spring starter the repository is registered automatically (no `@Repository`).
- `insert`, `update`, `deleteById`, `findById` come from the base class and always
  handle the **whole aggregate**: `insert` fails for existing rows, `update` diffs
  against the persisted state, `deleteById` returns `Optional<A>`.

## Queries via Fetcher
Load complete aggregates from a root record:
```java
dslContext.select().from(ORDER).where(...).fetch().stream()
   .map(r -> getFetcher().fetchDeep(r.into(ORDER)).resultValue().get());
```
Prerequisite: the foreign keys inside the aggregate are defined in the database -
the fetcher follows them.

## Optimistic locking
- Every entity/root carries `concurrencyVersion`; each write of the aggregate
  increments the root's version.
- jOOQ needs **both** `settings().setExecuteWithOptimisticLocking(true)` at runtime
  (the Spring autoconfig does this) **and** `recordVersionFields` in the codegen -
  otherwise the version is silently not checked (details: `dlc-persistence-schema`).
- A conflict (jOOQ backend: `org.jooq.exception.DataChangedException`) means a stale
  aggregate: reload and reapply, never overwrite.

## Persistence actions
Repositories emit `PersistenceAction`s (INSERT/UPDATE/DELETE per domain object) -
use them for change tracking, not for business logic.

## Transaction cache (optional)
- Not a read cache: it never changes what `findById`/fetcher return. It only saves
  the extra SELECT that `update()`/`deleteById()` need right after a fetch of the
  same aggregate in the same transaction; an entry is consumed on use.
- Off by default: `dlc.features.persistence.transaction-cache.enabled=true` or
  `@EnableDlc(transactionCacheEnabled = true)`; `...max-size` (default 256).
- Needs Spring 6.2+ / Spring Boot 3.4+ - before, it stays off and logs a warning.
- After changing an aggregate of the running transaction **outside** DLC
  repositories (own SQL/jOOQ bulk update, stored procedure, trigger) call
  `domainPersistenceProvider.transactionCacheProvider.clearCurrentTransactionCache()`.

## Typical failures
- Partial aggregate loaded -> missing FK constraint inside the aggregate.
- Mapping errors at startup -> see `dlc-persistence-schema` troubleshooting.
- Class not found by persistence -> outside the mirror base packages.
