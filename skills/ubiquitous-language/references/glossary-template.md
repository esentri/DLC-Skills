# Glossary template (`docs/ubiquitous-language.md`)

Copy the structure below. Keep the header text in the project file so readers
know how the status works. Columns:

| Column | Content |
|---|---|
| Term | the domain expert's word (umlauts allowed) |
| Definition | one or two sentences in domain language; `?` if unknown - never invented |
| Code | identifiers using the term: types, methods, enum constants (`Order`, `Order.cancel()`, `OrderStatus.CANCELLED`) |
| Status | `candidate` / `confirmed` / `deprecated` |
| Avoid | rejected synonyms / old names - must not be used in code |
| Replaced by | only for `deprecated`: the term to use instead; empty if the concept was dropped |
| Open question | what still has to be clarified; empty when resolved |

```markdown
# Ubiquitous Language

Domain terms of this project, one section per bounded context.
Status: `candidate` = proposed, not agreed yet (added by developers or the agent) -
`confirmed` = agreed with the team, only changed by agreement - `deprecated` = no
longer used, see "Replaced by" (only set by the team).

## Ordering (`com.example.shop.ordering`)

| Term | Definition | Code | Status | Avoid | Replaced by | Open question |
|---|---|---|---|---|---|---|
| Bestellung | Verbindlicher Kaufauftrag eines Kunden über einen oder mehrere Artikel. | `Bestellung`, `BestellungId` | confirmed | Auftrag, Order | | |
| Bestellung aufgeben | Kunde schickt den Warenkorb verbindlich ab; erzeugt eine Bestellung. | `GibBestellungAuf`, `BestellungAufgegeben` | confirmed | | | |
| Stornieren | ? | `Bestellung.storniere()`, `StorniereBestellung` | candidate | | | Gleich "Widerruf"? Bis wann erlaubt? |
| Kunde | | `Kunde`, `KundeId` | candidate | | | Synonym zu "Kaeufer" in `Rechnung`? |

## Shipping (`com.example.shop.shipping`)

| Term | Definition | Code | Status | Avoid | Replaced by | Open question |
|---|---|---|---|---|---|---|
| Lieferpaket | Frühere Bezeichnung für Sendung. | `Sendung.lieferpaketNummer()` | deprecated | | Sendung | |
| Sendung | Physisches Paket mit einer oder mehreren Bestellpositionen. | `Sendung` | confirmed | Lieferung, Paket, Lieferpaket | | |
```

Rules for editing:
- Sort rows alphabetically by term within a section.
- One row per concept; IDs, status enums, events and commands of a concept go into
  its `Code` cell (or get their own row if they carry their own meaning).
- A rename in the glossary (confirmed term replaced): the old row becomes
  `deprecated` with `Replaced by` = new term (only after the user agreed), the old
  word goes into `Avoid` of the new term. `Code` of the deprecated row lists the
  identifiers still to be renamed.
- `deprecated` rows are never deleted.
