---
name: dlc-persistence-schema
description: Design, write or review the relational schema behind DomainLifeCycles (DLC) aggregates - Flyway (or other) DDL migrations, tables, columns, sequences and foreign keys derived from roots, entities, value objects, List<Identity>/List<Enum> fields; jOOQ code generation setup and regeneration (recordVersionFields, record package); and DLC persistence startup/mapping errors with the jOOQ or JDBC backend (AutoMapping violations, partial aggregates, missing optimistic locking). Use when adding or changing a persisted aggregate, writing a migration, or debugging DLC repository/fetcher mapping. German triggers: Migration, Tabelle, Schema, Flyway, Sequenz, Spalte, Fremdschluessel, DDL, jOOQ-Codegenerierung, Mapping-Fehler.
---

# DLC persistence schema

Targets **DLC 3.5.x**. Upstream: `persistence/readme.md` ("Object relational mapping"),
`jooq-integration/readme.md`, `jdbc-integration/readme.md`.

## Prerequisite - do this first

Load `domainlifecycles` and its `references/persistence.md` (backend choice,
repositories, fetcher). This skill covers only the schema side. Mode C only.

## Workflow

1. **Read the aggregate**: root, entities, embedded value objects (1:1),
   `List<ValueObject>` (1:n), `List<Identity>` / `List<Enum>`, identity value types.
2. **Derive** tables, columns, sequences, FKs with the rules below.
3. **Write the migration** (new versioned file; never edit an applied one).
4. **jOOQ:** regenerate records and compile before touching repositories.
   **JDBC:** nothing to generate - the schema is read at runtime.
5. **Round-trip test:** `insert` -> `findById` -> assert equality of the whole
   aggregate (incl. nested lists) -> `update` -> `deleteById`.

Full example (Order: root + entity + 1:n VO + `List<Identity>`): `references/ddl-example.md`.

## Tables and columns (AutoMapping conventions)

- **One table per entity / aggregate root.** Table name = class name in snake case
  (`OrderPosition` -> `ORDER_POSITION`).
- **Every non-static field -> one column**, snake case
  (`unitPriceNet` -> `UNIT_PRICE_NET`). Only fields are mapped, not getters/setters.
- Identity-typed fields (own id, references to other aggregates) map their raw value
  (`id`, `customer_id`).
- **`concurrency_version`** (`BIGINT NOT NULL` / `NUMBER(18)`) on every entity/root table.
- **1:1 value object -> embedded** as columns in the owning table. Column name =
  the **concatenated field path** from the entity into the value object, in snake
  case: `deliveryAddress.street` -> `DELIVERY_ADDRESS_STREET`, nested VOs append
  further (`price.amount.value` -> `PRICE_AMOUNT_VALUE`). Matching ignores case and
  underscores. Deviating column names: JDBC backend via
  `JdbcValueObjectColumnNameOverride`; jOOQ backend has no override - use a custom
  `RecordMapper`.
- Child entity table: FK column to the parent (or another ancestor) table, e.g.
  `ORDER_ITEM.ORDER_ID`. **No Java field needed** - DLC fills NOT NULL FK columns
  pointing to an ancestor's table automatically. Declare that column **NOT NULL**:
  an unmapped *nullable* column aborts startup as an incomplete mapping.
- Data types: jOOQ natural type mapping must work, else register a `TypeConverter`.
  Excerpt of the upstream table (`persistence/readme.md` -> AutoMapping):

| Java                         | Postgres                 | Oracle            |
|------------------------------|--------------------------|-------------------|
| `long` / `Long`              | `BIGINT`                 | `NUMBER(18)`      |
| `int` / `Integer`            | `INT`                    | `NUMBER(10,0)`    |
| `boolean`                    | `BOOLEAN`                | `NUMBER(1,0) DEFAULT 0 NOT NULL` |
| `BigDecimal`                 | `NUMERIC(19,6)`          | `NUMBER(19,6)`    |
| `String`                     | `VARCHAR(n)`             | `VARCHAR2(n)`     |
| `UUID`                       | `CHAR(36)`               | `CHAR(36)`        |
| Java enum                    | `VARCHAR(50)`            | `VARCHAR2(50)`    |
| `LocalDate`                  | `DATE`                   | `DATE`            |
| `LocalDateTime`              | `TIMESTAMP(6) WITHOUT TIME ZONE` | same      |
| `Instant`, `OffsetDateTime`, `ZonedDateTime` | `TIMESTAMP(6) WITH TIME ZONE` | same |

  Predefined converters exist (e.g. `DefaultInstantToOffsetDateTimeUTCConverter`);
  extend `DefaultTypeConverterProvider` for custom ones.

## 1:n value objects ("record mapped") and scalar lists

- Own table named **`<CONTAINING_TABLE>_<PROPERTY>`** - property name, not type name:
  `Order.actionCodes` -> `ORDER_ACTION_CODES`.
- Nested: `ActionCode.vals` (list) -> `ORDER_ACTION_CODES_VALS`, and so on.
- Requirements:
  - technical **`ID`** `PRIMARY KEY` (not present in Java). UUID-compatible type
    (`UUID`, `CHAR`/`VARCHAR` 32-36, `BINARY(16)`) -> random UUID in memory, no
    sequence; numeric -> sequence **`<TABLE>_SEQ`** required,
  - **`CONTAINER_ID`** `FOREIGN KEY` to the parent entity / containing VO table.
  Both column names are fixed - DLC looks them up literally.
- **`List<Identity>` / `List<Enum>`** (3.4+): same structure, one child table per
  field, single `value` column holding the raw identity / enum value.

```sql
CREATE TABLE order_action_codes (
    id           BIGINT PRIMARY KEY,
    container_id BIGINT NOT NULL REFERENCES "order"(id),
    value        VARCHAR(10) NOT NULL
);
CREATE SEQUENCE order_action_codes_seq START WITH 1000;
```

- Different table name wanted -> `EntityValueObjectRecordTypeConfiguration`
  (jOOQ, record class) / `JdbcEntityValueObjectRecordTypeConfiguration` (JDBC, table name).
  Same mechanism maps a 1:1 VO into its own table.

## Identities and sequences

- Non-UUID `Identity`: sequence **`<IdentityName_snake>_SEQ`** (`OrderId` ->
  `ORDER_ID_SEQ`, `OrderItemId` -> `ORDER_ITEM_ID_SEQ`). Repositories often expose
  `newOrderId()` via `dslContext.nextval(Sequences.ORDER_ID_SEQ)`.
- `UUID` identity: generated in memory, no sequence.
- jOOQ resolves sequences via `dslContext.meta()` at runtime - a new sequence needs no
  regeneration (a new table/column does).

## Foreign keys and keys

- **FKs inside an aggregate are mandatory.** The fetcher follows them to load nested
  entities/VOs; insert/update/delete order is derived from them.
- **FKs between aggregates** (reference by ID columns): be careful - they can
  create FK cycles between aggregates (DLC derives the DML order from FKs and
  rejects cycles). Follow `AGENTS.md`; if it says nothing, **ask**. Don't add them
  silently.
- Only **single-column** PKs and FKs are supported.
- Not resolved automatically (need a custom repository with a `RecordProvider`):
  self-referencing single-valued FK (`parent_id`), and more than one FK between the
  same pair of tables. Self-referencing 1:n collections work.

## Inheritance (entities / roots)

- **Dedicated tables (default):** superclass defines no concrete identity, each
  concrete subclass has its own identity and table. AutoMapping works.
- **Single table:** superclass defines the identity, subclasses none; one table with a
  type discriminator, subclass-only columns nullable; requires a custom `RecordMapper`.
- No joined-table inheritance. VO inheritance does not affect mapping.

## AutoMapping, ignored fields, custom mappers

- All non-static fields must map; violations **abort application startup**.
- Field not to be persisted -> exclude it: an `IgnoredFieldProvider` (column side:
  `IgnoredRecordPropertyProvider`); the JDBC builder documents
  `withIgnoredDomainObjectFields(...)` / `withIgnoredRecordProperties(...)`.
- Deviating structure -> custom `RecordMapper` / `AbstractRecordMapper`, registered via
  `withCustomRecordMappers(...)`; it must map **all** columns.
- JDBC matches columns leniently (lower-cased, underscores stripped).

## jOOQ code generation essentials

- `<recordVersionFields>CONCURRENCY_VERSION</recordVersionFields>` - mandatory.
- Recommended in `<database>`: `<forceIntegerTypesOnZeroScaleDecimals>true`;
  in `<generate>`: `<javaTimeTypes>true`.
- Runtime: `setExecuteWithOptimisticLocking(true)` and an explicit `SQLDialect`
  (Spring autoconfig: `dlc.features.persistence.sql-dialect`).
- Record package: `@EnableDlc(jooqRecordPackage=...)` /
  `dlc.features.persistence.jooq-record-package` is scanned **including
  sub-packages** for `UpdatableRecord` classes - the codegen `packageName` works as
  well as `<packageName>.tables.records`. Prefer the narrower `...tables.records`.
- Run codegen against the migrated schema (Flyway + codegen in the build; see the
  upstream sample project). **Compile before writing repositories** - `Tables`,
  `Sequences` and records must exist.
- Generated jOOQ classes are left out of the 3.5 mirror by default (`org.jooq` supertypes).

## JDBC backend specifics

- Schema read once at startup (`JdbcSchemaMetadata.read(...)`) from the **fully
  migrated** database -> migrations must run before the persistence provider is built.
  Optional narrowing: `dlc.features.persistence.jdbc.schema-pattern`.
- Reserved words / case-sensitive names (e.g. table `ORDER`): default SQL is unquoted;
  use a `JdbcDialect` overriding `quoteIdentifier(...)`.
- No codegen flags: `JdbcPersister` checks/increments `CONCURRENCY_VERSION` itself and
  forces it to `1` on insert.
- Dialects: `H2JdbcDialect`, `PostgresJdbcDialect`, `OracleJdbcDialect`,
  `MySqlJdbcDialect` (emulated sequences), `SqlServerJdbcDialect`.

## Migration rules

- One new versioned migration per change; applied migrations are immutable.
- Prefer backward-compatible steps: add nullable column / new table first, backfill,
  then tighten (`NOT NULL`, drop old column) in a later migration.
- New table checklist: PK, `concurrency_version` (entity/root), FK to parent,
  `<TABLE>_SEQ` or `<ID>_SEQ` sequence.
- Renaming a Java field or class = renaming a column/table (or an explicit mapping).
- Own SQL bulk updates on aggregate tables bypass the repositories: with the transaction
  cache on, call `clearCurrentTransactionCache()` afterwards.

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Startup aborts with mapping error | field without column (name mismatch, missing column, field to ignore), wrong table name for a VO list, record package wrong / records not regenerated |
| "jOOQ Records not found" | wrong `jooqRecordPackage`, or build not re-run after migration |
| Aggregate loads partially (missing items / list values) | FK inside the aggregate not declared |
| Concurrent updates not detected | jOOQ: `recordVersionFields` missing in codegen or optimistic locking off at runtime |
| Insert fails on id generation | sequence missing or misnamed (`<ID>_SEQ`, `<TABLE>_SEQ`) |
| JDBC: syntax error on `ORDER` etc. | identifier needs quoting - `quoteIdentifier` |
| JDBC: new column/table ignored | schema snapshot read before migration, restart after migrating |
| Self/duplicate FK relation not loaded | needs a `RecordProvider` |
