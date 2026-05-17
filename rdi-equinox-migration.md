# RDI → Equinox Migration: Options & Recommendation

## Overview

We are migrating instrument/listing data from the existing **RDI platform** (fed by SIX) to a new platform, **Equinox**, over approximately one year. During this migration both sources must run in parallel — some instruments will remain on SIX/RDI while others move to Equinox.

The core problem this document addresses: **how does RDM Cache / Instrument Static tell Autobot/BBF which source an instrument belongs to?**

---

## Current Flow (unchanged baseline)

```
SIX FI Feed
  → RDI App (TBRDI tables + PL/SQL + RDISWX/RDISDX services)
    → SwxEnricher / SdxEnricher
      → Listing table (REF schema)
        → Serving layer → RDM Cache / Instrument Static → Autobot/BBF
```

---

## Context: PROD vs Non-PROD Behaviour

| Environment | Migration approach | Source discrimination |
|-------------|-------------------|----------------------|
| **PROD** | Instruments migrate by full **TradingSegment** — all instruments in a segment move together | TradingSegment may be a sufficient discriminator (all instruments in a segment belong to one platform) |
| **Non-PROD** | Partial migration — a segment may have 50 instruments on Equinox and 50 still on SIX | TradingSegment is **not** a reliable discriminator; instrument-level identification is needed |

> ⚠️ **Risk note:** The PROD assumption (full-segment atomic migration) has been communicated but is not yet confirmed. If PROD ever performs a partial segment migration (e.g. phased rollout, hotfix, or rollback), TradingSegment becomes unreliable in PROD as well. The instrument-level approach described in this document should be retained as a safety net for PROD, at negligible additional cost.

---

## Option 1 — Modify existing PL/SQL (Union approach)

### Description

- New tables (`TBEQUI*`) are added to the **existing schema** (same as `TBRDI*`).
- The **existing PL/SQL packages are modified** to `UNION ALL` data from both `TBRDI*` (SIX) and `TBEQUI*` (Equinox) tables and add a `SOURCE_SYSTEM` flag to the output.
- The flag is exposed via the **existing RDISWX/RDISDX web services** — no new service needed.
- **Existing SwxEnricher and SdxEnricher are completely unchanged** — they continue to read from existing services and load the Listing table as-is.
- **TopicLoader** (existing standalone component) is modified to read from the existing service, filter for Equinox instruments using the source flag, and maintain two new topics:
  - `SWX_Equinox_Topic`
  - `SDX_Equinox_Topic`
- **Autobot/BBF** checks topic membership to determine the source — no change to RDM Cache / Instrument Static.

### What changes

| Component | Change |
|-----------|--------|
| Existing schema | Add `TBEQUI*` tables |
| Existing PL/SQL | Modified — UNION ALL + source flag added |
| Existing services | No change (flag exposed automatically via PL/SQL) |
| SwxEnricher / SdxEnricher | **No change** |
| Listing table | **No change** |
| RDM Cache / Instrument Static | **No change** |
| TopicLoader | Modified — filters Equinox instruments, maintains 2 new topics |
| Autobot/BBF | Modified — checks topic membership |

### Effort

~2–3 person-weeks

### Pros

- Lowest upfront effort.
- Existing enrichers and serving layer completely untouched.
- No new schema or services to provision.

### Cons

- **Highest regression risk** — modifying core PL/SQL that processes every instrument daily. Any bug affects SIX data too, not just Equinox.
- Topics must be kept in sync with live data — stale topics cause silent misrouting.
- Technical debt accumulates in the existing PL/SQL and must be cleaned up post-migration.
- Only viable if the migration completes within ~3 months and the team accepts the regression risk.

---

## Option 2 — New RDIEQUINOX schema (shared foundation)

Both Option 2a and Option 2b share the same greenfield infrastructure build. They differ **only** in how Autobot/BBF identifies the source after data is loaded.

### Shared foundation (required for both 2a and 2b)

This is a significant, standalone piece of work:

- **New DB schema** (`RDIEQUINOX`) with its own tables (`TBEQUI*`), PL/SQL packages, and services (EquinoxService SWX + EquinoxService SDX).
- **Two new enrichers**: `SwxEquinoxEnricher` and `SdxEquinoxEnricher` — read from the new EquinoxService and load into the existing Listing table in REF schema.
- **Existing schema, enrichers, services, and Listing table are completely untouched.**

```
Equinox Feed
  → RDIEQUINOX schema (TBEQUI* tables + new PL/SQL + EquinoxService SWX/SDX)
    → SwxEquinoxEnricher / SdxEquinoxEnricher
      → Listing table (REF schema — same table, new rows from Equinox)
```

---

## Option 2a — New schema + SOURCE_SYSTEM column

### Description

On top of the shared foundation, a new column `SOURCE_SYSTEM` is added to the **Listing table** in the REF schema. `SwxEquinoxEnricher` / `SdxEquinoxEnricher` populate it when loading Equinox data. The serving layer is updated to expose this field. RDM Cache / Instrument Static is updated to surface an `isEquinox()` filter. Autobot/BBF uses this filter directly.

### What changes (on top of shared foundation)

| Component | Change |
|-----------|--------|
| Listing table (REF schema) | Add `SOURCE_SYSTEM` column — **schema migration required** |
| SwxEquinoxEnricher / SdxEquinoxEnricher | Populate `SOURCE_SYSTEM` when loading |
| Serving layer | Updated to expose `SOURCE_SYSTEM` field |
| RDM Cache / Instrument Static | **Library change** — add `isEquinox()` / source filter |
| Autobot/BBF | Updated to use new filter |
| TopicLoader | **No change** |

### Effort

~6–8 person-weeks (including shared foundation)

### Pros

- Source is persisted on the row — fully auditable. You can always query which instruments came from where.
- No dependency on a nightly sync job — source is always correct in the Listing table.
- Simpler for Autobot/BBF — reads a field, not a topic.

### Cons

- Five downstream touch points (see table above), each requiring its own change, test, and release.
- DB schema migration on the Listing table, though low-risk, requires coordination.
- More components to change than Option 2b.

---

## Option 2b — New schema + Topic lookup ✅ Recommended

### Description

On top of the shared foundation, the existing **TopicLoader** is modified to call the new EquinoxService (SWX and SDX) and write all returned Equinox instrument IDs into two new topic tables in the REF schema:

- `SWX_Equinox_Topic`
- `SDX_Equinox_Topic`

The existing serving layer already exposes topic table data alongside Listing data — **no serving layer change is needed**. RDM Cache / Instrument Static requires **no change**. Autobot/BBF checks topic membership directly to determine the source.

### What changes (on top of shared foundation)

| Component | Change |
|-----------|--------|
| Listing table (REF schema) | **No change** |
| Serving layer | **No change** |
| RDM Cache / Instrument Static | **No change** |
| TopicLoader | Modified — calls EquinoxService, populates 2 new topic tables |
| Autobot/BBF | Updated — checks topic membership (instrument in topic → Equinox, else SIX) |

### Effort

~5–7 person-weeks (including shared foundation)

### Pros

- Only two additional touch points beyond the shared foundation (TopicLoader + Autobot/BBF).
- No schema change on the Listing table.
- No RDM Cache / Instrument Static library change or release.
- Rollback is clean — drop the topics, done.
- TopicLoader is a well-understood, standalone component — extension is low risk.

### Cons

- Topics must be refreshed daily — if the TopicLoader job fails, topic data becomes stale and Autobot/BBF may misroute instruments. Monitoring and alerting on this job is essential.
- Source is not persisted in the Listing table — less auditable than 2a.
- An extra lookup step in Autobot/BBF (though topic data is in-memory and latency is negligible at current scale).

> ⚠️ **Stale topic risk in non-PROD:** Topic staleness is a test environment problem, not a production incident. Monitoring the TopicLoader job is sufficient mitigation. If PROD ever moves to this approach (as a safety net for partial segment migrations), production-grade alerting on the job is mandatory.

---

## Comparison

| Aspect | Option 1 | Option 2a | Option 2b ✅ |
|--------|----------|-----------|------------|
| **Effort** | 2–3 weeks | 6–8 weeks | 5–7 weeks |
| **New schema** | No (adds tables to existing schema) | Yes — full greenfield build | Yes — same as 2a |
| **New enrichers** | No | Yes (SwxEquinox, SdxEquinox) | Yes — same as 2a |
| **Core PL/SQL modified** | Yes ⚠️ | No | No |
| **Listing table change** | No | Yes (add column) | No |
| **RDM Cache / Instrument Static change** | No | Yes (library change) | No |
| **TopicLoader change** | Yes | No | Yes |
| **Autobot/BBF change** | Yes | Yes | Yes |
| **Regression risk** | High | Low | Low |
| **Auditability** | Medium | High | Medium |
| **Rollback** | Complex (revert PL/SQL + drop tables) | Drop column + decommission schema | Drop topics + decommission schema |
| **Stale data risk** | Topic sync daily | None (persisted) | Topic sync daily |

---

## Recommendation

**Option 2b** is recommended for a one-year migration with the current scale (~100k instruments, daily loads in non-PROD).

The key reason over 2a: Option 2a requires five downstream touch points — Listing table migration, serving layer change, RDM Cache / Instrument Static library change, and Autobot/BBF change — compared to Option 2b's two (TopicLoader + Autobot/BBF). The schema change in 2a is not the blocker; the library release cycle for RDM Cache / Instrument Static is.

The key reason over Option 1: Option 1 modifies core PL/SQL that processes all instruments. Any regression is not limited to Equinox instruments — it affects the entire SIX feed. This risk is disproportionate to the effort saved.

**Option 1** remains viable only if the migration must complete within ~3 months and the team explicitly accepts the PL/SQL regression risk.

**If PROD requires instrument-level discrimination** (i.e. TradingSegment proves insufficient), Option 2b's topic approach can be extended to PROD at minimal additional cost. This should be confirmed before the migration begins and monitored throughout.

---

## Next Steps

1. Confirm whether TradingSegment is a sufficient PROD discriminator — or whether topics/column are needed in PROD from day one.
2. Validate TopicLoader job monitoring and alerting capability for daily refreshes.
3. Confirm team capacity and finalise effort estimates.
4. If Option 2b is approved: begin design of the RDIEQUINOX schema as the first deliverable (shared by both 2a and 2b — can be started before the discrimination approach is finalised).
5. Present options and recommendation to business for funding approval.
