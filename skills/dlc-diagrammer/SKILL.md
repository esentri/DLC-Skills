---
name: dlc-diagrammer
description: Generate, configure or troubleshoot DomainLifeCycles (DLC) domain diagrams - full model, a single aggregate/bounded context, or one business flow (includeFlowsFrom / includeFlowsTo via static analysis), via the dlc-gradle-plugin / dlc-maven-plugin or the domain-diagrammer API, including mirror export. Use when the user wants to visualise, draw or analyse a domain model as diagram files ("Diagramm", "Domänenmodell anzeigen", "draw the flow of X"). For call-graph answers as text use dlc-impact-analysis; for running the DLC Diagram Viewer or uploading the model to it use dlc-diagram-viewer.
---

# DLC domain diagrams

Targets DLC 3.5.x. Upstream: `domain-diagrammer/readme.md`, `dlc-plugins/readme.md`.

> **STOP - before reading on: invoke the skill `domainlifecycles` now if it is not
> loaded yet** (mode check, marker types the diagram depends on).

## Prerequisites (check first)
- The domain classes implement DLC marker types (Mode B is enough, see
  `domainlifecycles` skill). Unmarked classes don't appear or appear as non-domain.
- The model is self-contained in `domainModelPackages`.
- SVG output: Docker must be available (the plugin starts a Kroki container).
  `nomnoml` output needs no Docker.

## Pick the way
1. **Build plugin (default)** - reproducible, part of the build. The plugin is
   separate from the Spring Boot starters; never add it as a dependency.
2. **Java API** (`domain-diagrammer` module) - in a test or tool. Initialise the
   mirror with `factory.setGenericTypeResolver(new TypeMetaResolver())` before
   `Domain.initialize(factory)`. The API produces Nomnoml text only; render it
   with `nomnoml-cli` or use the plugin for SVG.
- For "who calls what" answers as **text** (refactoring, review) use the skill
  `dlc-impact-analysis` instead of a diagram.

## Gradle
```groovy
plugins { id 'io.domainlifecycles.dlc-gradle-plugin' version '3.5.0' }

dlcGradlePlugin {
    diagram {
        fileOutputDir = layout.buildDirectory
        diagrams {
            orderOverview {
                domainModelPackages = ["com.example.shop"]
                explicitlyIncludedPackages = ["com.example.shop.order"]
                format = "svg"            // or "nomnoml"
                fileName = "order"
            }
        }
    }
}
```
No plugin marker artifact on the Gradle Plugin Portal: `pluginManagement` needs
`mavenCentral()` and a resolution strategy (see upstream readme). Run `gradle createDiagram`.

## Maven
```xml
<plugin>
  <groupId>io.domainlifecycles</groupId>
  <artifactId>dlc-maven-plugin</artifactId>
  <version>3.5.0</version>
  <executions><execution>
    <id>orderDiagram</id><phase>compile</phase>
    <goals><goal>createDiagram</goal></goals>
    <configuration>
      <fileOutputDir>target</fileOutputDir>
      <diagrams><diagram>
        <domainModelPackages><domainModelPackage>com.example.shop</domainModelPackage></domainModelPackages>
        <format>nomnoml</format>
      </diagram></diagrams>
    </configuration>
  </execution></executions>
</plugin>
```
Run `mvn dlc:createDiagram@orderDiagram`. Maven goal names (from the plugin code):
`createDiagram`, `serializeMirror`, `uploadDomainModel`. The upstream readme is
wrong in two places: `mvn dlc:renderJson@...` (correct: `serializeMirror`) and
`<goal>domainModelUpload</goal>` (correct: `uploadDomainModel`). Gradle tasks:
`createDiagram`, `serializeMirror`, `domainModelUpload`.

## Narrowing a diagram
Structural (cheap, no static analysis):
- `explicitlyIncludedPackages` - one bounded context / aggregate package.
- `classesBlacklist` - drop single classes.
- `includeConnectedTo` - everything connected to the given classes;
  `includeConnectedToIngoing` / `includeConnectedToOutgoing` with
  `includeConnectedToIngoingDepth` / `...OutgoingDepth` (0 = complete path);
  `excludeConnectedToIngoing` / `excludeConnectedToOutgoing`. A class must not be
  included and excluded at once.
- Overview of many aggregates: `showOnlyAggregateFrames = true`.

**Flow diagrams** (static bytecode analysis, run by the plugin itself - no extra
dependency needed; the Java API needs `static-analysis-sootup`):
- `includeFlowsFrom = ["com.example.shop.order.OrderService#placeOrder"]`
  (type, optionally `#method`) - everything reachable from that entry point,
  following calls, published events and processed commands.
- `includeFlowsTo` - backward ("what leads here"). A domain command cannot be a
  target (throws).
- Flows only narrow: classes outside the diagram's packages or on the blacklist
  stay out.
- Per diagram: `showOnlyFlowMethods` (default true), `showFlowCallRelations`
  (build fails without a flow setting), `flowMaxDepth`, `flowFollowEvents`,
  `flowFollowImplementations`, `flowExcludeAccessors`, `staticAnalysisPackages`.
- `staticAnalysisPackages` defaults to `domainModelPackages` - add infrastructure
  packages, otherwise flows stop at repository/outbound interfaces because the
  implementations are not found.
- `staticAnalysisCacheSize` belongs on the surrounding `diagram` task / Maven
  `<configuration>`, not on a single diagram.

Never hand-roll call-graph analysis - use flows here or `dlc-impact-analysis`.

## Generated and non-domain code
- Classes without a marker type in the scanned packages are mirrored as
  non-domain classes and drawn when connected to a service kind
  (`showNonDomainClasses`, default true).
- jOOQ-generated code is excluded by default
  (`nonDomainExcludedSupertypePackages`, default `["org.jooq"]` - setting it
  replaces the default, so re-add `org.jooq`). Exclude other generated code with
  `nonDomainExcludedPackages`.

## Factories in diagrams
- `Factory` classes are drawn with stereotype `<<Factory>>` (`showFactories`,
  `showFactoryFields`, `showFactoryMethods`).
- `@FactoryMethod` methods are marked `«factory»`; a class creating another
  aggregate is connected by a `<<creates>>` relation (switch off with
  `showFactoryRelations`). Builders never count as factories.
- Missing `<<creates>>` arrows -> the creating method lacks `@FactoryMethod`, or
  the creator is not a `Factory`.

## Mirror export and Diagram Viewer
- Goal / task `serializeMirror`: writes the Domain Mirror as JSON at build time.
- Uploading the model (with static analysis) to the DLC Diagram Viewer, and
  running the viewer locally with Docker Compose -> skill `dlc-diagram-viewer`.

## Troubleshooting
- Class missing -> outside `domainModelPackages`, or no DLC marker type.
- Event arrows missing -> publisher lacks `@Publishes`, listener lacks
  `@DomainEventListener` (`@ListensTo` is deprecated).
- Flow ends at an interface -> widen `staticAnalysisPackages`.
- Diagram cluttered with generated classes -> `nonDomainExcludedPackages`.
- Jackson conflicts in the plugin classpath -> see upstream "Troubleshooting / Jackson".
