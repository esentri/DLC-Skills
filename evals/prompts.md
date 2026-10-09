# Trigger smoke tests

Run each prompt in a sample project of the given mode and record which skills
and reference files were loaded. Expected values are the target cut.

| # | Prompt | Project mode | Expected skills | Expected references |
|---|--------|--------------|-----------------|---------------------|
| 1 | Build a value object Money with currency | A | ddd-tactical-java | - |
| 2 | Build a value object Money with currency | B | ddd-tactical-java, domainlifecycles | marker-types |
| 3 | Model and implement the Order aggregate | C (jOOQ) | ddd-tactical-java, domainlifecycles | marker-types, bootstrap-mirror, persistence |
| 4 | Why is my aggregate not persisted completely? | C (jOOQ) | domainlifecycles | persistence |
| 5 | Generate the domain diagram for the order context | B | dlc-diagrammer | - |
| 6 | Show me everything that happens after OrderService#placeOrder | C | dlc-diagrammer | - |
| 7 | Set up DLC in this new Spring Boot 3 project | none | dlc-project-setup | - |
| 8 | Publish an event when an order is shipped and react to it in shipping | C | ddd-tactical-java, domainlifecycles | marker-types, domain-events |
| 9 | Review this entity for DDD smells | A | ddd-tactical-java | modeling-checklist (optional) |
| 10 | Serialize Order as JSON in the REST controller | C | domainlifecycles | jackson-mapping, spring-integration |
| 11 | Introduce a separate bounded context for shipping | B | ddd-tactical-java, domainlifecycles | marker-types |
| 12 | Creating an order needs a sequence ID and a price lookup - where does that go? | C | ddd-tactical-java, domainlifecycles | marker-types |
| 13 | Send the customer an e-mail when the order is shipped | C | ddd-tactical-java, domainlifecycles | marker-types, domain-events |
| 14 | Ordering needs the customer's credit rating from the billing context before placing an order | B | ddd-tactical-java, domainlifecycles | marker-types |
| 15 | Write the Flyway migration for the new Invoice aggregate | C (jOOQ) | dlc-persistence-schema, domainlifecycles | persistence |
| 16 | The app fails at startup with a DLC mapping error for OrderItem | C | dlc-persistence-schema, domainlifecycles | persistence |
| 17 | Who calls Order.cancel() and what breaks if I change its signature? | B | dlc-impact-analysis, domainlifecycles | bootstrap-mirror |
| 18 | What happens after the PlaceOrder command is processed? | C | dlc-impact-analysis | - |

Rule of thumb: two skills competing for the same prompt -> merge them;
a skill used only partially in most prompts -> split it further.
