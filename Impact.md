# BookingCenter Migration — Impact Analysis Prompt

Paste one of the prompts below into **GitHub Copilot Agent (`@workspace`)** inside IntelliJ.  
Try **Prompt A** first. If it times out, use **Prompt B** with a narrowed scope.

---

## Context (read before using either prompt)

Two options are on the table for the BookingCenter migration:

- **Option 1** — Add a new BookingCenter `"f"`. The shorthand code (`mandatorCode = "001"`) stays the same but now matches **two** booking centers instead of one. Any flow that looks up by this shorthand and expects a single result will break.
- **Option 2** — Keep `"e"` as the only BookingCenter. Introduce `legalEntityId` as a routing field passed between services. Only flows that need to distinguish between two legal entities need to change. Everything else is untouched.

**Known field aliases** — search for these alongside the canonical names:

| Canonical Field | Also appears as |
|---|---|
| `bookingCenterId` | `topazCode`, `topazId`, `mercuryWSId`, `bcId` *(add yours)* |
| `mandatorCode` | `entityId`, `mandator` *(add yours)* |
| `legalEntityId` | `leiCode` *(add yours)* |

---

## Prompt A — Full Workspace

```
You are a senior Java architect analysing the impact of a BookingCenter migration across this codebase.

OPTION 1: A new BookingCenter "f" is added. mandatorCode stays "001" but now matches two booking centers.
OPTION 2: legalEntityId becomes an inter-service routing field. bookingCenterId and mandatorCode are unchanged.

Scan @workspace. For each Gradle module that touches any of these fields —
  bookingCenterId / topazCode / topazId / mercuryWSId / bcId
  mandatorCode / entityId / mandator
  legalEntityId / leiCode
— answer at MODULE level only (not class or method detail):

1. Does this module READ any of these fields from a service call, event, or DB result?
2. Does this module PASS any of these fields to another module, service, or event stream?
3. Is mandatorCode used to look up a single BookingCenter (not a list)?
   → If YES: this module breaks under Option 1.
4. Is "e" hardcoded as the only valid bookingCenterId anywhere?
   → If YES: this module silently ignores Option 1's new "f" value.
5. Does any outbound SOAP/REST call or event payload lack a legalEntityId field?
   → If YES: this module needs a change under Option 2.
6. Do any config files (.properties, .yml, .yaml, .xml, .env, or any other config format)
   contain hardcoded values for any of these fields?
   → If YES: flag the file and value — these are silent failures under both options
     that won't show up in Java code analysis.
7. Scan all files matching *fm2*.xml. These contain custom DSL rule conditions evaluated
   via reflection at runtime. Look for expressions in any of these forms:
     Context.BookingCenter == 'e'        Context.BookingCenter == "e"
     BookingCenter == 'e'                BookingCenter == "e"
     Context.MandatorCode == '001'       MandatorCode == '001'
     Context.EntityId == '001'           EntityId == '001'
     Context.LegalEntityId              LegalEntityId
     Context.TopazCode / Context.TopazId / Context.MercuryWSId / Context.BcId
     (and any variant without the Context. prefix)
   For each match: flag the file name, the exact expression, and which field it references.
   → Any expression hardcoding "e" or "001" is a silent failure under Option 1.
   → Any expression that has no legalEntityId condition may need one added under Option 2.

Then produce a single impact summary:

FLOW MAP
For each affected module, one line:
  [Module] → reads [field] → passes to [downstream module/service]

OPTION 1 IMPACT
Which modules break and why (one sentence each). Which are safe.

OPTION 2 IMPACT
Which modules need a change and why (one sentence each). Which need no change.

CONFIG RISKS
List any config files with hardcoded field values. These need manual updates regardless of which option is chosen.

DSL RULE RISKS
List every *fm2*.xml file containing a hardcoded field expression. For each: file name, expression found, risk under Option 1 and Option 2.

OVERALL ASSESSMENT
Which option affects fewer modules. Which option carries silent-failure risk vs explicit change risk.
Do not suggest solutions. Facts and impact only.
```

---

## Prompt B — Reduced Scope (use if Prompt A times out)

Replace `[PATTERN]` with a name pattern matching your modules (e.g. `booking`, `order`, `service-`).  
Run this multiple times with different patterns to cover all modules.

```
You are a senior Java architect analysing the impact of a BookingCenter migration.

OPTION 1: A new BookingCenter "f" is added. mandatorCode stays "001" but now matches two booking centers.
OPTION 2: legalEntityId becomes an inter-service routing field. bookingCenterId and mandatorCode are unchanged.

Scan only modules whose name contains [PATTERN]. For each matching module that touches any of these fields —
  bookingCenterId / topazCode / topazId / mercuryWSId / bcId
  mandatorCode / entityId / mandator
  legalEntityId / leiCode
— answer at MODULE level only (not class or method detail):

1. Does this module READ any of these fields from a service call, event, or DB result?
2. Does this module PASS any of these fields to another module, service, or event stream?
3. Is mandatorCode used to look up a single BookingCenter (not a list)?
   → If YES: this module breaks under Option 1.
4. Is "e" hardcoded as the only valid bookingCenterId anywhere?
   → If YES: this module silently ignores Option 1's new "f" value.
5. Does any outbound SOAP/REST call or event payload lack a legalEntityId field?
   → If YES: this module needs a change under Option 2.
6. Do any config files (.properties, .yml, .yaml, .xml, .env, or any other config format)
   contain hardcoded values for any of these fields?
   → If YES: flag the file and value — these are silent failures under both options
     that won't show up in Java code analysis.
7. Scan all files matching *fm2*.xml. These contain custom DSL rule conditions evaluated
   via reflection at runtime. Look for expressions in any of these forms:
     Context.BookingCenter == 'e'        Context.BookingCenter == "e"
     BookingCenter == 'e'                BookingCenter == "e"
     Context.MandatorCode == '001'       MandatorCode == '001'
     Context.EntityId == '001'           EntityId == '001'
     Context.LegalEntityId              LegalEntityId
     Context.TopazCode / Context.TopazId / Context.MercuryWSId / Context.BcId
     (and any variant without the Context. prefix)
   For each match: flag the file name, the exact expression, and which field it references.
   → Any expression hardcoding "e" or "001" is a silent failure under Option 1.
   → Any expression that has no legalEntityId condition may need one added under Option 2.

Then produce a single impact summary:

FLOW MAP
For each affected module, one line:
  [Module] → reads [field] → passes to [downstream module/service]

OPTION 1 IMPACT
Which modules break and why (one sentence each). Which are safe.

OPTION 2 IMPACT
Which modules need a change and why (one sentence each). Which need no change.

CONFIG RISKS
List any config files with hardcoded field values. These need manual updates regardless of which option is chosen.

DSL RULE RISKS
List every *fm2*.xml file containing a hardcoded field expression. For each: file name, expression found, risk under Option 1 and Option 2.

OVERALL ASSESSMENT
Which option affects fewer modules. Which option carries silent-failure risk vs explicit change risk.
Do not suggest solutions. Facts and impact only.
```
