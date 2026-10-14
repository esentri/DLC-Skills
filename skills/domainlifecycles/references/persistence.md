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
  codegen (no build-time DB, licensing). Reads the schema once at startup - with
  Spring Boot + Flyway/Liquibase it needs the `DependsOnDatabaseInitializationDetector`
  from `dlc-persistence-schema` ("JDBC backend specifics"), otherwise startup fails
  with `Couldn't find table for '...'`.
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
Pattern for every custom finder: select **root records only** (filter, sort, page
on the root table), then hand each one to `fetchDeep(...)`. The fetcher loads all
child tables itself - no hand-written joins or child queries.
`fetchDeep(id)` / `fetchDeep(record)` return a `FetcherResult`; `.resultValue()` is
an `Optional<A>`.

Prerequisite: the foreign keys inside the aggregate are defined in the database -
the fetcher follows them.

### jOOQ
```java
dslContext.select().from(ORDER).where(...).orderBy(ORDER.ID).offset(o).limit(n)
   .fetch().stream()
   .map(r -> getFetcher().fetchDeep(r.into(ORDER)).resultValue().get());
```

### JDBC
No generated records: rows come back as the generic `JdbcRecord`, and the
`ResultSet` -> `JdbcRecord` mapping is done by the static helpers in
`io.domainlifecycles.jdbc.util.JdbcRecordMapper`. Connection, dialect and schema
metadata are **not** exposed by `JdbcAggregateRepository` - keep the injected
`JdbcDomainPersistenceProvider` and read `connectionProvider` / `dialect` /
`schemaMetadata` from it (with the Spring starter it is a bean).

```java
class JdbcOrderRepository extends JdbcAggregateRepository<Order, Order.OrderId>
        implements OrderRepository {

    private final JdbcDomainPersistenceProvider provider;

    JdbcOrderRepository(JdbcDomainPersistenceProvider provider,
                        PersistenceEventPublisher publisher) {
        super(Order.class, provider, publisher);
        this.provider = provider;
    }

    private TableMetadata orderTable() {
        return provider.schemaMetadata.table("ORDER"); // physical name, case-insensitive
    }
}
```

Choose the variant by query shape:

1. **By id** - nothing to write: `findById(id)` (or `getFetcher().fetchDeep(id)`).
2. **Equality filter on one column** - `selectByColumn` (SQL built by the dialect,
   so identifier quoting and UUID normalisation are applied):
   ```java
   public List<Order> findByCustomer(CustomerId customerId) {
       return JdbcRecordMapper.selectByColumn(provider.connectionProvider, provider.dialect,
               orderTable(), "CUSTOMER_ID", customerId.value()).stream()
           .map(r -> getFetcher().fetchDeep(r).resultValue().orElseThrow())
           .toList();
   }
   ```
   Single row: `selectOneByColumn(...)` (returns `null` if none, fails if > 1).
3. **Anything else (filters, sorting, paging)** - own SQL via `selectWithSql`
   (`selectOne` for at most one row):
   ```java
   public List<Order> findPendingPaged(int offset, int pageSize) {
       var table = orderTable();
       var sql = "SELECT * FROM " + table.qualifiedName()
               + " WHERE STATUS = ? ORDER BY ID OFFSET ? ROWS FETCH NEXT ? ROWS ONLY";
       return JdbcRecordMapper.selectWithSql(provider.connectionProvider, table, sql,
               OrderStatus.PENDING.name(), offset, pageSize).stream()
           .map(r -> getFetcher().fetchDeep(r).resultValue().orElseThrow())
           .toList();
   }
   ```
   - The query must return **every column of the root table** (`SELECT *`, or
     `SELECT o.*` when joining/filtering via other tables) - `mapRow` reads all
     columns the table metadata declares.
   - Use `?` parameters, never string concatenation of values. Parameters are bound
     as-is: convert UUIDs etc. to the physical column type yourself.
   - The SQL is not touched by the dialect: paging syntax and identifier quoting
     must fit the target database.
4. **Performance (N+1 on large collections)** - a `RecordProvider` pre-fetches child
   records (e.g. one query for all items). Attach it to a **dedicated**
   `JdbcAggregateFetcher`, never to `getFetcher()`: `withRecordProvider` mutates the
   fetcher, and the repository's default fetcher is shared by `findById`/`update`.
   Extend `JdbcRecordProvider` to get `selectByColumn`/`selectWithSql`/... as
   instance helpers:
   ```java
   public Optional<Order> findWithItems(Order.OrderId id) {
       var fetcher = new JdbcAggregateFetcher<Order, Order.OrderId>(Order.class, provider);
       var itemTable = provider.schemaMetadata.table("ORDER_ITEM");
       fetcher.withRecordProvider(
           new JdbcRecordProvider(provider) {
               @Override
               public Collection<JdbcRecord> provideCollection(JdbcRecord parent) {
                   return selectByColumn(itemTable, "ORDER_ID", parent.get("ID"));
               }
           },
           Order.class,           // entity containing the property
           OrderItem.class,       // property element type
           List.of("orderItems")); // property path from that entity
       return fetcher.fetchDeep(id).resultValue();
   }
   ```
   Override `provide(parent)` instead for a single (1:1) child.
5. **Read side outside a repository** (query handler, read service needing full
   aggregates) - `new JdbcAggregateFetcher<>(Order.class, provider)` plus variant 2/3
   for the root rows. Read-only: writes still go through the repository.

`JdbcRecord` values are read by physical column name: `record.get("ID")`.

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
