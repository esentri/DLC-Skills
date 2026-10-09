---
name: dlc-impact-analysis
description: Answer call-graph and impact questions in DomainLifeCycles (DLC) projects as text the agent reasons about - "who calls X?", "what happens after command/event Z?", "what breaks if I change method Y?", "which paths lead to aggregate A?" - by running DLC static analysis (SootupStaticAnalyzer, DomainCalls callersOf/callsFor, DomainCallFlowAnalyzer flowFrom/flowTo, FlowConfig) in a small JUnit test and interpreting Flow output and diagnostics. Use during refactoring, review or debugging ("Wer ruft auf", "was passiert nach", Auswirkungen, Aufrufkette, Abhaengigkeiten, impact analysis, call hierarchy). Not for pictures - diagrams go to dlc-diagrammer.
---

# DLC impact analysis (call graph and flows as text)

Targets DLC 3.5.x. Upstream: `static-analysis/readme.md`,
`static-analysis-serialization-jackson3/readme.md`, `dlc-plugins/readme.md`.

## Prerequisite
Load `domainlifecycles` first (Mode B or C is enough). Picture wanted ->
`dlc-diagrammer` (`includeFlowsFrom` / `includeFlowsTo`).

**Rule:** never hand-roll a call graph with grep/regex when this analysis is
available. grep is only a quick pre-check (does the name exist, which file).
grep misses events, command processing, interface dispatch and overrides.

## Checklist before running
- Classes implement DLC marker types; event wiring via `@Publishes`,
  `@DomainEventListener` (or Spring `@EventListener`,
  `@TransactionalEventListener`, `@ApplicationModuleListener`).
- Code is **compiled** - the analysis reads bytecode, not sources.
- Mirror initialised over the right packages (`references/bootstrap-mirror.md`
  of `domainlifecycles`). The mirror is the boundary: only calls whose target is
  a mirrored type are recorded.
- Dependency, test scope is fine:
  - Gradle: `testImplementation 'io.domainlifecycles:static-analysis-sootup:3.5.0'`
  - Maven: `io.domainlifecycles:static-analysis-sootup:3.5.0`, `<scope>test</scope>`
  It brings `io.domainlifecycles:static-analysis` transitively.

## Pick the question -> API
| Question | Call |
|---|---|
| What does method M call directly? | `domainCalls.callsFor(domainMethod)` |
| Who calls method M directly? | `domainCalls.callersOf(domainMethod)` |
| What happens after command C / event E? | `analyzer.flowFrom(commandMirror / eventMirror)` |
| What does method M set in motion? | `analyzer.flowFrom("pkg.Type", "method")` (`Optional`, first overload only) |
| What leads into method M (transitive callers)? | `analyzer.flowTo("pkg.Type", "method")` (`Optional`, first overload only) |
| Which paths lead to aggregate / read model / service A? | `analyzer.flowTo(typeMirror)` |
| Who publishes event E? | `analyzer.flowTo(eventMirror)` |

No `flowTo(DomainCommandMirror)` - a command is never a backward target; it only
appears as a reached leaf.

The by-name `flowFrom`/`flowTo(typeName, methodName)` use **only the first
overload** of that name. For overloaded methods, and for `callsFor`/`callersOf`,
build `DomainMethod`s from the type's `MethodMirror`s:
```java
DomainTypeMirror type = domainMirror.getDomainTypeMirror("com.example.shop.order.Order").orElseThrow();
List<DomainMethod> cancelMethods = type.getMethods().stream()
    .filter(m -> m.getName().equals("cancel"))
    .map(m -> new DomainMethod(type.getTypeName(), m))
    .toList();
cancelMethods.forEach(m -> {
    System.out.println(m + " called by " + domainCalls.callersOf(m));
    System.out.println(analyzer.flowTo(m));
});
```

## Template (copy into `src/test/java`, adapt names, run once)
```java
class ImpactProbeTest {

    @Test
    void probe() {
        Domain.initialize(new ReflectiveDomainMirrorFactory("com.example.shop"));
        DomainMirror domainMirror = Domain.getDomainMirror();

        DomainCalls domainCalls = new SootupStaticAnalyzer()
            .analyze(domainMirror, DomainClasspath.ofMirroredTypes(domainMirror));

        if (!domainCalls.isComplete()) {
            domainCalls.diagnostics(Diagnostic.Severity.WARNING).forEach(System.out::println);
        }

        FlowConfig config = FlowConfig.defaults()
            .withMaxDepth(5)
            .excludingAccessors();
        FlowAnalyzer analyzer = new DomainCallFlowAnalyzer(domainMirror, domainCalls, config);

        // forward: what happens after the command
        var command = (DomainCommandMirror) domainMirror
            .getDomainTypeMirror("com.example.shop.order.PlaceOrder").orElseThrow();
        Flow after = analyzer.flowFrom(command);
        System.out.println(after);
        System.out.println("reached types: " + after.reachedTypeNames());
        System.out.println("truncated: " + after.truncated());

        // backward: who leads into this method
        analyzer.flowTo("com.example.shop.order.OrderService", "placeOrder")
            .ifPresentOrElse(System.out::println,
                () -> System.out.println("type or method unknown to the mirror"));

        // backward: all entry channels into an aggregate
        var target = domainMirror.getDomainTypeMirror("com.example.shop.order.Order").orElseThrow();
        System.out.println(analyzer.flowTo(target));
    }
}
```
- Run only this test (`mvn -Dtest=ImpactProbeTest test` / `gradle test --tests ImpactProbeTest`),
  read stdout. Resolve imports via IDE/compiler. Delete the probe afterwards
  unless the user wants to keep it.
- Inside a `@SpringBootTest` the mirror is already initialised - use
  `Domain.getDomainMirror()`, never call `Domain.initialize` again.

## Reading the output
`Flow#toString()` is an indented tree, one step per line, breadth first:
```
yourdomain.order.PlaceOrder
  COMMAND_PROCESS -> yourdomain.order.OrderService.placeOrder(yourdomain.order.PlaceOrder)
    CALL -> yourdomain.order.Orders.findById(yourdomain.order.OrderId)
      IMPLEMENTATION -> yourdomain.order.OrdersImpl.findById(yourdomain.order.OrderId)
    CALL -> yourdomain.order.Order.place()
      EVENT_PUBLISH -> yourdomain.order.OrderPlaced
        EVENT_LISTEN -> yourdomain.notification.NotificationService.onOrderPlaced(yourdomain.order.OrderPlaced)
```
- Step kinds: `CALL`, `IMPLEMENTATION`, `EVENT_PUBLISH`, `EVENT_LISTEN`,
  `COMMAND_PROCESS`, plus `CREATES` (factory methods) and `PROVIDES_READ_MODEL`.
- In `flowTo` every kind is reversed: `CALL` = "called by", `IMPLEMENTATION` =
  "overridden supertype method", `EVENT_LISTEN` = "published by",
  `COMMAND_PROCESS` = "processed command".
- Several `EVENT_LISTEN` children: all run. Several `IMPLEMENTATION` children:
  alternatives, exactly one runs per execution.
- `Step#depth()` = shortest distance from the start; `Step#cyclic()` = cycle,
  not expanded further; `Flow#truncated()` = cut by `withMaxDepth`.

**Impact answer** for "what breaks if I change Y": run `flowTo` on Y (callers,
publishers, entry commands = blast radius) and `flowFrom` on Y (what Y drives).
Report both lists, name entry points (commands, listeners, non-domain classes
like controllers), and state the limitations below that apply.

## FlowConfig
- `FlowConfig.defaults()` - unlimited depth, events and implementations
  followed, nothing filtered (accessors included).
- `.excludingAccessors()` - drop `command.id()`, getters; almost always wanted.
- `.withMaxDepth(n)` - bound large flows; check `truncated()`.
- `.withFollowImplementations(false)` - only types named at call sites.
- `.withMethodFilter(...)` - any other predicate.

## Completeness and scope
- `isComplete()` false / `WARNING` diagnostics -> result likely incomplete, fix
  the cause (usually a mirrored type missing from the classpath).
  `INFO` = deliberately skipped (e.g. bridge methods). Never report "nobody
  calls X" without checking this.
- `DomainClasspath.ofMirroredTypes(...)` derives the bytecode locations; add
  more via `DomainClasspath.ofTypes(...)` and `merge(...)`.
- **Infrastructure implementations** (repository / outbound-service adapters)
  outside the analysed packages are missed - the flow ends at the interface.
  Java API: include their package in the mirror. Build plugins: widen
  `staticAnalysisPackages` (defaults to `domainModelPackages`).

## Limitations (from the docs)
- Constructors and static initialisers are invisible (`new X(...)`, `super(...)`);
  creation shows up only via `Factory` / `@FactoryMethod` (`CREATES`).
- A call through an interface is recorded on the interface; implementations
  come only as `IMPLEMENTATION` flow edges.
- Calls on JDK / library / framework types (`toString()`, `Supplier.get()`,
  `map(Object::toString)`) and on DLC's own types are not recorded.
  `new SootupStaticAnalyzer(cacheSize, true)` restores expansion - noisy, avoid.
- Anything not on the analysed classpath - reported as a `Diagnostic`, not guessed.

## Optional: JSON export (hand `DomainCalls` to another tool)
`io.domainlifecycles:static-analysis-serialization-jackson3:3.5.0`
```java
DomainCallsSerializer serializer = new JacksonDomainCallsSerializer(true); // pretty print
String json = serializer.serialize(domainCalls);
DomainCalls back = serializer.deserialize(json, domainMirror); // same mirror required
```
`static-analysis-serialization-jackson2` is legacy (`@Deprecated`); use only in
Jackson-2-only projects.
