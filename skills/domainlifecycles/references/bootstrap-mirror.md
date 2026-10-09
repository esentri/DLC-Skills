# Bootstrap and Domain Mirror (Mode C)

Module: `io.domainlifecycles:mirror`. Upstream: `mirror/readme.md`.

The Domain Mirror is DLC's reflective metamodel of all bounded contexts. Every
runtime module (persistence, Jackson, events, diagrammer) reads it - so it must be
initialised **once, before** any of them is used.

## Plain Java

```java
Domain.initialize(new ReflectiveDomainMirrorFactory("com.example.shop"));
```
- Pass the base package(s) of the domain model.
- In tests **without** a Spring context, initialise in a `@BeforeAll` / static block.

## Spring Boot

With `spring-boot-starter` / `spring-boot3-starter` the mirror is initialised by the
autoconfig. Configure the packages:

```java
@EnableDlc(dlcMirrorBasePackages = "com.example.shop")
@SpringBootApplication
public class Application { ... }
```
or `dlc.features.mirror.base-packages=com.example.shop`.
Do **not** call `Domain.initialize` manually in addition - also not in
`@SpringBootTest`s; use `Domain.getDomainMirror()` there.

## Bounded contexts in the Mirror
Resolution order:
1. Packages set explicitly via `AbstractDomainMirrorFactory#setBoundedContextPackages(...)`.
2. Otherwise packages annotated with `@BoundedContext` (`package-info.java`).
3. Otherwise the whole scanned model is a single bounded context.

Prefer the annotations (option 2) - the boundaries then live in the code. Nested
context packages fail initialisation with a `MirrorException`.

## Typical failures
- "Domain not initialized" -> bootstrap missing or runs too late.
- A class is not recognised -> outside the configured base packages, or it
  doesn't implement a DLC marker type.
- Build-time mirror export (no runtime reflection): see `dlc-diagrammer` /
  plugin goal `serializeMirror`.
