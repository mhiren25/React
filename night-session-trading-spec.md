# NIGHT Session Trading Support — Design Specification

**Version:** 1.0  
**Status:** Draft  
**Application:** Market Hour Rules Engine (Java / Spring Boot / Oracle DB)

---

## Table of Contents

1. [Background](#1-background)
2. [Problem Statement](#2-problem-statement)
3. [Key Design Decisions](#3-key-design-decisions)
4. [Scope of Change](#4-scope-of-change)
5. [Schema Changes](#5-schema-changes)
6. [Java Enum Change](#6-java-enum-change)
7. [Code Changes](#7-code-changes)
8. [Expiry Scenarios](#8-expiry-scenarios)
9. [Holiday Calendar Behaviour](#9-holiday-calendar-behaviour)
10. [Validation Rules](#10-validation-rules)
11. [Regression Test Matrix](#11-regression-test-matrix)
12. [Migration & Rollout Plan](#12-migration--rollout-plan)
13. [Out of Scope](#13-out-of-scope)

---

## 1. Background

The application allows businesses to configure **Market Hours** (static, per-market defaults) and **Market Hour Rules** (dynamic, per-market + currency + trading session). These rules are evaluated when a trade is received or modified to determine:

- When a trade expires
- When a trade should be put on hold (e.g. after market close)
- When a held trade should be released (e.g. next market open)

The system today assumes a trading day runs from `00:00` to `23:59` in the market's timezone. All rule matching and date attribution are based on this assumption.

---

## 2. Problem Statement

NASDAQ is introducing a **Night Trading Session** running from `21:00` to `04:00` (spanning midnight) in market timezone. Several other markets are expected to follow.

This introduces two problems the current system cannot handle:

### Problem 1 — Midnight-Spanning Session Window

The existing rule matching logic checks:

```
tradeTime >= openingTime AND tradeTime <= closingTime
```

For a NIGHT rule with `openingTime = 21:00` and `closingTime = 04:00`, this condition **always evaluates to false** because `21:00 > 04:00`.

### Problem 2 — Trading Date Attribution

A trade placed at `21:30 on Tuesday` night belongs to **Wednesday's trading day** (next business day), not Tuesday. The current system would attribute it to Tuesday, causing:

- Wrong expiry time calculation
- Wrong holiday calendar lookup
- Wrong date in audit and reporting

---

## 3. Key Design Decisions

| Decision | Resolution | Rationale |
|---|---|---|
| What triggers date-shift logic? | `trade.tradingSession` contains `NIGHT` | Trade explicitly declares its session; no inference needed |
| Where does overnight trading day boundary live? | `MARKET_HOUR_RULE` — two new columns on the NIGHT rule row | Single source of truth; no sync between tables needed; deleting the rule removes the config automatically |
| What if no NIGHT rule configured for a market? | Treat as unsupported — do not silently fall back to `MarketHour` defaults | Silent fallback would produce wrong expiry times; explicit config error is safer |
| How is NIGHT ordered vs other sessions? | NIGHT always first in trading day (`tradingDayOrder = 0`) regardless of clock time | 21:00 sorts after 16:00 by `LocalTime`; sort must be by trading day semantics, not wall clock |
| Multi-session window calculation | Contiguous span from earliest session start to latest session end | Existing behaviour — unchanged |
| Expiry for NIGHT-only trade | `closingTime + expiryOffset` (e.g. `04:00 + 2min = 04:02`) | Existing `EXPIRY_OFFSET` column already supports this |
| Expiry for NIGHT + other sessions | Latest end time across all sessions on the trade | Existing multi-session logic — unchanged |

---

## 4. Scope of Change

### What changes

| Layer | Change |
|---|---|
| `MARKET_HOUR_RULE` table | 2 new nullable columns: `TRADING_DAY_START`, `TRADING_DAY_END` |
| `TradingSession` Java enum | Add `NIGHT` value with `tradingDayOrder() = 0` |
| Rule sort comparator | NIGHT forced to sort first via `LocalTime.MIN` trick |
| Session window match | Add midnight-spanning `else` branch |
| `TradingDateResolver` | New Spring component — called only when trade has NIGHT session |
| Data | One new `MARKET_HOUR_RULE` row per market supporting NIGHT |

### What does NOT change

| Layer | Status |
|---|---|
| `MARKET_HOUR` table | No changes |
| All existing `MARKET_HOUR_RULE` rows | No changes — new columns are nullable with no impact |
| All existing REGULAR / PRE_MARKET / AFTER_HOURS trade paths | Zero behaviour change |
| Trade storage format (epoch timestamp) | No changes |
| API contracts | No changes |
| Multi-session window calculation logic | No changes — NIGHT plugs into existing mechanism |

---

## 5. Schema Changes

### 5.1 `MARKET_HOUR_RULE` — Two New Columns

```sql
ALTER TABLE MARKET_HOUR_RULE
  ADD TRADING_DAY_START VARCHAR2(5) NULL,
  ADD TRADING_DAY_END   VARCHAR2(5) NULL;

COMMENT ON COLUMN MARKET_HOUR_RULE.TRADING_DAY_START
  IS 'HH:mm in market timezone. Populated ONLY for NIGHT session rules. '
     'Defines the start of the logical trading day (e.g. 21:00 for NASDAQ). '
     'NULL for all other session types.';

COMMENT ON COLUMN MARKET_HOUR_RULE.TRADING_DAY_END
  IS 'HH:mm in market timezone. Populated ONLY for NIGHT session rules. '
     'Defines the end of the logical trading day inclusive (e.g. 20:02 for NASDAQ). '
     'NULL for all other session types.';
```

> **Why nullable?** All existing rule rows have no concept of a trading day boundary — NULL explicitly signals "traditional 00:00–23:59 trading day". No default value is set to avoid implying a boundary where none exists.

### 5.2 DB Constraint

```sql
ALTER TABLE MARKET_HOUR_RULE ADD CONSTRAINT CHK_TRADING_DAY_BOUNDARY
  CHECK (
    TRADING_SESSION = 'NIGHT'
    OR (TRADING_DAY_START IS NULL AND TRADING_DAY_END IS NULL)
  );
```

This enforces that only NIGHT session rules can carry trading day boundary values.

### 5.3 NIGHT Enum Value in Reference / Check Constraint

```sql
-- If TradingSession is enforced via CHECK constraint, extend it:
ALTER TABLE MARKET_HOUR_RULE
  DROP CONSTRAINT CHK_TRADING_SESSION;

ALTER TABLE MARKET_HOUR_RULE
  ADD CONSTRAINT CHK_TRADING_SESSION
  CHECK (TRADING_SESSION IN ('REGULAR', 'PRE_MARKET', 'AFTER_HOURS', 'NIGHT'));

-- If TradingSession is a lookup/reference table, insert the new value:
INSERT INTO TRADING_SESSION_REF (SESSION_CODE, DESCRIPTION, SORT_ORDER)
VALUES ('NIGHT', 'Night Trading Session', 0);
```

### 5.4 Data — NASDAQ Night Session Rule

```sql
INSERT INTO MARKET_HOUR_RULE (
  MARKET_ID,
  TRADING_SESSION,
  OPENING_TIME,
  CLOSING_TIME,
  EXPIRY_OFFSET,
  TRADING_DAY_START,
  TRADING_DAY_END,
  CURRENCY
  -- ... other existing columns
)
VALUES (
  'NASDAQ',
  'NIGHT',
  '21:00',
  '04:00',
  2,          -- expire 2 minutes after 04:00 = 04:02
  '21:00',    -- logical trading day starts at 21:00 the night before
  '20:02',    -- logical trading day ends at 20:02 (after-hours end + offset)
  'ALL'
  -- ... other existing column values
);
```

---

## 6. Java Enum Change

```java
public enum TradingSession {

    NIGHT,        // NEW — always first in the logical trading day
    PRE_MARKET,
    REGULAR,
    AFTER_HOURS;

    /**
     * Canonical ordering within a trading day.
     *
     * NIGHT is always first (order = 0) even though its wall-clock start time (21:00)
     * is numerically after PRE_MARKET (04:00) and AFTER_HOURS (16:00).
     *
     * This ordering is used for session window calculation and sort logic only.
     * It must NOT be used to sort by wall-clock time.
     */
    public int tradingDayOrder() {
        return switch (this) {
            case NIGHT       -> 0;
            case PRE_MARKET  -> 1;
            case REGULAR     -> 2;
            case AFTER_HOURS -> 3;
        };
    }
}
```

---

## 7. Code Changes

### 7.1 Rule Sort Comparator

**Location:** Wherever `MarketHourRule` list is sorted before evaluation (likely in your rule evaluation service or repository layer).

**Problem:** Current sort is by `openingTime` ascending. NIGHT (`21:00`) sorts last, but must be first.

**Fix:**

```java
// BEFORE
rules.sort(Comparator.comparing(MarketHourRule::getOpeningTime));

// AFTER
private static final Comparator<MarketHourRule> TRADING_DAY_ORDER =
    Comparator.comparing((MarketHourRule r) ->
        r.getTradingSession() == TradingSession.NIGHT
            ? LocalTime.MIN   // 00:00 — forces NIGHT before PRE_MARKET (04:00)
            : r.getOpeningTime()
    );

rules.sort(TRADING_DAY_ORDER);
```

> **Impact on existing rules:** Zero. All non-NIGHT rules continue to sort by `openingTime` exactly as before. The `LocalTime.MIN` trick only affects NIGHT rules.

---

### 7.2 Session Window Match — Midnight-Spanning Check

**Location:** The method that checks whether a trade's time falls within a rule's `[openingTime, closingTime]` window.

**Problem:** `21:00 <= tradeTime <= 04:00` is always false with standard comparison when `openingTime > closingTime`.

**Fix:**

```java
private boolean isWithinSessionWindow(LocalTime tradeTime, MarketHourRule rule) {
    LocalTime open  = rule.getOpeningTime();  // e.g. 21:00
    LocalTime close = rule.getClosingTime();  // e.g. 04:00

    if (!open.isAfter(close)) {
        // Normal session: openingTime <= closingTime (e.g. 09:30 to 16:00)
        // Existing behaviour — untouched
        return !tradeTime.isBefore(open) && !tradeTime.isAfter(close);
    } else {
        // Midnight-spanning session: openingTime > closingTime (e.g. 21:00 to 04:00)
        // Valid if time is >= 21:00 (evening side) OR <= 04:00 (early morning side)
        return !tradeTime.isBefore(open) || !tradeTime.isAfter(close);
    }
}
```

> **Impact on existing rules:** Zero. The `else` branch is only reachable when `openingTime > closingTime`, which never occurs for any existing rule.

---

### 7.3 `TradingDateResolver` — New Component

**Purpose:** Single, centralised place where trading date is resolved. All existing callers of `toLocalDate()` that need a trading date must route through this component.

```java
@Component
public class TradingDateResolver {

    private final HolidayCalendarRepository holidayRepo;

    /**
     * Resolves the logical trading date for a trade against a given market.
     *
     * For non-NIGHT trades:
     *   Returns the calendar date in market timezone. Behaviour identical to today.
     *
     * For NIGHT trades:
     *   The night session physically starts on calendar day T (e.g. Tuesday 21:00)
     *   but belongs to trading day T+1 (e.g. Wednesday).
     *
     *   Rules:
     *   - tradeTime >= TRADING_DAY_START (e.g. >= 21:00)
     *       → trading date = next business day after calendar date
     *   - tradeTime <= closingTime (e.g. <= 04:00, early morning side of session)
     *       → trading date = calendar date (already the "next" calendar day)
     *   - tradeTime between closingTime and TRADING_DAY_START (e.g. 04:01 to 20:59)
     *       → NIGHT trade outside night window — should be caught by validation upstream
     *       → treated conservatively as calendar date
     *
     * NASDAQ example (TRADING_DAY_START=21:00, closingTime=04:00):
     *   Tuesday  21:30  →  Wednesday  (>= 21:00, shift to next biz day)
     *   Wednesday 03:00  →  Wednesday  (<= 04:00, already next calendar day)
     *   Wednesday 10:00  →  Wednesday  (normal window, calendar date)
     */
    public LocalDate resolve(Trade trade, MarketHour market) {
        if (!trade.getSessions().contains(TradingSession.NIGHT)) {
            // All non-NIGHT trades — zero change from existing behaviour
            return toMarketLocalDate(trade.getTimestamp(), market.getTimezone());
        }

        MarketHourRule nightRule = findNightRule(market.getMarketId())
            .orElseThrow(() -> new MarketConfigurationException(
                "Trade declares NIGHT session but no NIGHT MarketHourRule configured " +
                "for market: " + market.getMarketId()
            ));

        return resolveForNightSession(trade.getTimestamp(), market, nightRule);
    }

    private LocalDate resolveForNightSession(
            long epochMillis,
            MarketHour market,
            MarketHourRule nightRule) {

        ZoneId tz         = ZoneId.of(market.getTimezone());
        ZonedDateTime zdt = Instant.ofEpochMilli(epochMillis).atZone(tz);
        LocalTime time    = zdt.toLocalTime();
        LocalDate calDate = zdt.toLocalDate();

        LocalTime tradingDayStart = LocalTime.parse(nightRule.getTradingDayStart()); // 21:00
        LocalTime nightClose      = LocalTime.parse(nightRule.getClosingTime());     // 04:00

        if (!time.isBefore(tradingDayStart)) {
            // 21:00 onwards on Tuesday night → belongs to Wednesday's trading day
            return nextBusinessDay(calDate.plusDays(1), market);
        }

        if (!time.isAfter(nightClose)) {
            // 00:00 to 04:00 Wednesday morning → still Wednesday's trading day
            // calDate is already Wednesday (the next calendar day)
            return calDate;
        }

        // 04:01 to 20:59 — outside night session window
        // Should be caught by upstream validation; treat conservatively
        return calDate;
    }

    /**
     * Advances from the given date until a non-weekend, non-holiday date is found.
     * Holiday check uses the TARGET trading date, not the trade submission date.
     *
     * Example: Friday 21:30 trade → tries Saturday → weekend → tries Sunday → weekend
     *          → tries Monday → checks Monday holiday calendar → if holiday, tries Tuesday
     */
    private LocalDate nextBusinessDay(LocalDate from, MarketHour market) {
        LocalDate candidate = from;
        while (isWeekend(candidate)
                || holidayRepo.isHoliday(market.getMarketId(), candidate)) {
            candidate = candidate.plusDays(1);
        }
        return candidate;
    }

    private boolean isWeekend(LocalDate date) {
        DayOfWeek dow = date.getDayOfWeek();
        return dow == DayOfWeek.SATURDAY || dow == DayOfWeek.SUNDAY;
    }

    private LocalDate toMarketLocalDate(long epochMillis, String timezone) {
        return Instant.ofEpochMilli(epochMillis)
            .atZone(ZoneId.of(timezone))
            .toLocalDate();
    }

    private Optional<MarketHourRule> findNightRule(String marketId) {
        return ruleRepo.findByMarketIdAndSession(marketId, TradingSession.NIGHT);
    }
}
```

---

### 7.4 Calling `TradingDateResolver` in Existing Evaluation Code

**Location:** Wherever your rule evaluation service resolves the trading date before rule lookup and expiry calculation.

```java
// BEFORE
LocalDate tradingDate = toMarketLocalDate(trade.getTimestamp(), market.getTimezone());

// AFTER
LocalDate tradingDate = tradingDateResolver.resolve(trade, market);
// For all non-NIGHT trades: identical result to before
// For NIGHT trades: returns next business day
```

---

### 7.5 Service Layer Validation on Rule Save

Prevent misconfiguration at the point of saving a `MarketHourRule`:

```java
public void validateRule(MarketHourRule rule) {

    boolean isNight = rule.getTradingSession() == TradingSession.NIGHT;
    boolean hasBoundary = rule.getTradingDayStart() != null
                       || rule.getTradingDayEnd() != null;

    // Non-NIGHT rules must not carry boundary fields
    if (!isNight && hasBoundary) {
        throw new InvalidMarketHourRuleException(
            "TRADING_DAY_START and TRADING_DAY_END are only valid for NIGHT session rules. " +
            "Session: " + rule.getTradingSession()
        );
    }

    // NIGHT rules must carry both boundary fields
    if (isNight && !hasBoundary) {
        throw new InvalidMarketHourRuleException(
            "NIGHT session rules must specify both TRADING_DAY_START and TRADING_DAY_END."
        );
    }

    // NIGHT rules must have openingTime > closingTime (midnight-spanning)
    if (isNight) {
        LocalTime open  = LocalTime.parse(rule.getOpeningTime());
        LocalTime close = LocalTime.parse(rule.getClosingTime());
        if (!open.isAfter(close)) {
            throw new InvalidMarketHourRuleException(
                "NIGHT session openingTime must be after closingTime " +
                "(session spans midnight). Got: " + open + " to " + close
            );
        }
    }
}
```

---

## 8. Expiry Scenarios

All scenarios assume NASDAQ with NIGHT rule: `openingTime=21:00`, `closingTime=04:00`, `expiryOffset=2min`.

```
── NIGHT only ──────────────────────────────────────────────────────────────────
Trade sessions:   NIGHT
Trade placed:     Tuesday 21:30
Trading date:     Wednesday  (21:30 >= 21:00 → next business day)
Window start:     Tuesday 21:00  (tradingDate-1 @ openingTime)
Window end:       Wednesday 04:02  (tradingDate @ closingTime + offset)
Expiry:           Wednesday 04:02

── NIGHT + PRE_MARKET ──────────────────────────────────────────────────────────
Trade sessions:   NIGHT, PRE_MARKET
Trade placed:     Tuesday 22:00
Trading date:     Wednesday
Window start:     Tuesday 21:00
Window end:       Wednesday 09:30  (PRE_MARKET closingTime)
Expiry:           Wednesday 09:30

── NIGHT + PRE_MARKET + REGULAR ────────────────────────────────────────────────
Trade sessions:   NIGHT, PRE_MARKET, REGULAR
Trade placed:     Tuesday 21:30
Trading date:     Wednesday
Window start:     Tuesday 21:00
Window end:       Wednesday 16:00  (REGULAR closingTime)
Expiry:           Wednesday 16:00

── NIGHT + PRE_MARKET + REGULAR + AFTER_HOURS ──────────────────────────────────
Trade sessions:   NIGHT, PRE_MARKET, REGULAR, AFTER_HOURS
Trade placed:     Tuesday 21:30
Trading date:     Wednesday
Window start:     Tuesday 21:00
Window end:       Wednesday 20:00  (AFTER_HOURS closingTime)
Expiry:           Wednesday 20:00

── REGULAR only — placed during night hours (no NIGHT session on trade) ────────
Trade sessions:   REGULAR (or none, defaulting to REGULAR)
Trade placed:     Tuesday 22:00
Trading date:     Tuesday  (no date shift — NIGHT not on trade)
Market closed:    Hold till Wednesday REGULAR openingTime (09:30)
Date resolver:    Returns raw calendar date — zero change from today
```

---

## 9. Holiday Calendar Behaviour

Holiday calendar checks always use the **resolved trading date**, not the physical submission date. This is handled automatically by routing through `TradingDateResolver` before any holiday check.

| Scenario | Physical Date | Resolved Trading Date | Holiday Check On | Result |
|---|---|---|---|---|
| Tue 21:30, Wed normal | Tuesday | Wednesday | Wednesday | ✅ Valid trading day |
| Tue 21:30, Wed is holiday | Tuesday | Wednesday → Thursday | Thursday | Hold till Thu open |
| Fri 21:30, Mon normal | Friday | Monday | Monday | ✅ Valid trading day |
| Fri 21:30, Mon is holiday | Friday | Monday → Tuesday | Tuesday | Hold till Tue open |
| Wed 03:00 (early morning, NIGHT trade) | Wednesday | Wednesday | Wednesday | ✅ Valid trading day |

> The `nextBusinessDay()` method inside `TradingDateResolver` iterates forward skipping both weekends and holidays until it finds a valid trading day. Holiday calendar used is always the **target market's** calendar.

---

## 10. Validation Rules

| Rule | Enforced At |
|---|---|
| `TRADING_DAY_START` and `TRADING_DAY_END` must be NULL for non-NIGHT rules | DB constraint + service layer |
| NIGHT rules must have both `TRADING_DAY_START` and `TRADING_DAY_END` populated | Service layer |
| NIGHT rule `openingTime` must be after `closingTime` (midnight-spanning) | Service layer |
| Trade with `NIGHT` session on a market with no NIGHT rule → reject with `MarketConfigurationException` | `TradingDateResolver` |
| Trade placed outside night session window but tagged as NIGHT → caught upstream in trade validation | Trade intake validation layer |

---

## 11. Regression Test Matrix

| # | Trade Sessions | Trade Placed At | Market Condition | Expected Trading Date | Expected Expiry / Behaviour |
|---|---|---|---|---|---|
| 1 | `REGULAR` | Tue 22:00 | NASDAQ, normal | Tuesday | Hold till Wed 09:30 (market closed) |
| 2 | `NIGHT` | Tue 21:30 | NASDAQ, normal | Wednesday | Wed 04:02 |
| 3 | `NIGHT` | Wed 03:00 | NASDAQ, normal | Wednesday | Wed 04:02 |
| 4 | `NIGHT` | Wed 10:00 | NASDAQ, normal | Wednesday | Wed 04:02 (outside window — validation error upstream) |
| 5 | `NIGHT + PRE_MARKET` | Tue 21:30 | NASDAQ, normal | Wednesday | Wed 09:30 |
| 6 | `NIGHT + REGULAR` | Tue 22:00 | NASDAQ, normal | Wednesday | Wed 16:00 |
| 7 | `NIGHT + PRE_MARKET + AFTER_HOURS` | Tue 21:30 | NASDAQ, normal | Wednesday | Wed 20:00 |
| 8 | `NIGHT` | Fri 21:30 | NASDAQ, Mon normal | Monday | Mon 04:02 |
| 9 | `NIGHT` | Fri 21:30 | NASDAQ, Mon = holiday | Tuesday | Tue 04:02 |
| 10 | `NIGHT` | Tue 21:30 | Market with no NIGHT rule | — | `MarketConfigurationException` |
| 11 | `PRE_MARKET + AFTER_HOURS` | Any | Any legacy market | Calendar date | Existing behaviour unchanged |
| 12 | `REGULAR` | Any | Any legacy market | Calendar date | Existing behaviour unchanged |

---

## 12. Migration & Rollout Plan

### Phase 1 — Schema (zero risk, deploy independently)

```sql
-- Step 1: Add new columns (nullable, no impact on existing rows)
ALTER TABLE MARKET_HOUR_RULE ADD TRADING_DAY_START VARCHAR2(5) NULL;
ALTER TABLE MARKET_HOUR_RULE ADD TRADING_DAY_END   VARCHAR2(5) NULL;

-- Step 2: Add constraint
ALTER TABLE MARKET_HOUR_RULE ADD CONSTRAINT CHK_TRADING_DAY_BOUNDARY
  CHECK (TRADING_SESSION = 'NIGHT'
         OR (TRADING_DAY_START IS NULL AND TRADING_DAY_END IS NULL));

-- Step 3: Extend NIGHT into session enum / reference table
```

### Phase 2 — Code (deploy behind feature flag)

- Add `NIGHT` to `TradingSession` enum
- Deploy sort comparator fix (NIGHT branch unreachable — no NIGHT rules exist yet)
- Deploy `isWithinSessionWindow()` midnight-span fix (unreachable — no NIGHT rules yet)
- Deploy `TradingDateResolver` (guard: `trade.getSessions().contains(NIGHT)`)
- All new code paths are **dead code** until Phase 3 data is inserted

### Phase 3 — NASDAQ configuration

```sql
INSERT INTO MARKET_HOUR_RULE
  (MARKET_ID, TRADING_SESSION, OPENING_TIME, CLOSING_TIME,
   EXPIRY_OFFSET, TRADING_DAY_START, TRADING_DAY_END, CURRENCY)
VALUES
  ('NASDAQ', 'NIGHT', '21:00', '04:00', 2, '21:00', '20:02', 'ALL');
```

- Run full regression test matrix (all 12 cases)
- Smoke test all downstream consumers: expiry, hold/release, reporting, settlement, audit

### Phase 4 — Subsequent markets

- Repeat Phase 3 data insert only
- **Zero code changes required**

---

## 13. Out of Scope

| Topic | Notes |
|---|---|
| Night Session on holiday eves (e.g. Night session starts Tuesday, Wednesday is holiday) | Handled automatically by `nextBusinessDay()` — but business should confirm expected behaviour |
| UI / admin console changes to configure NIGHT rules | Separate ticket — validation rules in section 10 must be enforced |
| Intraday modification of a NIGHT trade that crosses midnight | Existing modification flow routes through same `TradingDateResolver` — should work, needs explicit test |
| Markets where Night Session definition changes seasonally | Not considered — treat as a rule update (delete + reinsert) |
