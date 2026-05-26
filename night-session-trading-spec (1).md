# NIGHT Session Trading Support — Design Specification

**Version:** 1.1  
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
7. [Java POJO Change](#7-java-pojo-change)
8. [Code Changes](#8-code-changes)
9. [Expiry Scenarios](#9-expiry-scenarios)
10. [Holiday Calendar Behaviour](#10-holiday-calendar-behaviour)
11. [Validation Rules](#11-validation-rules)
12. [Regression Test Matrix](#12-regression-test-matrix)
13. [Migration & Rollout Plan](#13-migration--rollout-plan)
14. [Out of Scope](#14-out-of-scope)

---

## 1. Background

The application allows businesses to configure **Market Hours** (static, per-market defaults) and **Market Hour Rules** (dynamic, per-market + currency + trading session). These rules are evaluated when a trade is received or modified to determine:

- When a trade expires
- When a trade should be put on hold (e.g. after market close)
- When a held trade should be released (e.g. next market open)

### How Rule Evaluation Works Today

1. All `MarketHourRule` rows for the market are loaded and **sorted by `OPENINGHOUR` + `OPENINGMIN` ascending**
2. Each rule is matched against the trade using **two criteria** — both must be true:
   - `trade.tradingSession` matches `rule.tradingSession`
   - Trade timestamp (in market timezone) falls within `[openingTime, closingTime]`
3. All matching rules are collected
4. The rule with the **maximum `getExpiryOffsetClosingTime()`** is selected as the winning rule
5. `getExpiryOffsetClosingTime()` is computed as:
   ```
   Calendar set to today's date in market TZ
       with hour   = CLOSINGHOUR
       with minute = CLOSINGMIN
       + EXPIRY_OFFSET minutes
   → calendar.getTime() returned as long (epoch ms)
   ```
6. This winning rule's expiry time drives hold/release and expiry logic downstream

The system assumes a trading day runs from `00:00` to `23:59` in market timezone. All rule matching, date attribution, and expiry calculation are based on this assumption.

---

## 2. Problem Statement

NASDAQ is introducing a **Night Trading Session** running from `21:00` to `04:00` (spanning midnight) in market timezone. Several other markets are expected to follow.

This introduces three problems the current system cannot handle:

### Problem 1 — Sort Order Breaks for NIGHT

Current sort is by `OPENINGHOUR` + `OPENINGMIN` ascending. NIGHT opens at `21:00`, which sorts **last** — after AFTER_HOURS (`16:00`). But NIGHT is chronologically **first** in the logical trading day (it starts the night before). Wrong sort order means wrong rule precedence.

### Problem 2 — Midnight-Spanning Session Window Match Always Fails

The existing window match logic checks:

```
tradeTime >= openingTime AND tradeTime <= closingTime
```

For a NIGHT rule with `openingTime = 21:00` and `closingTime = 04:00`, this condition **always evaluates to false** because `21:00 > 04:00`.

### Problem 3 — Trading Date Attribution is Wrong

A trade placed at `21:30 on Tuesday` night belongs to **Wednesday's trading day** (next business day), not Tuesday. The current system would attribute it to Tuesday, causing:

- `getExpiryOffsetClosingTime()` building a `Calendar` on Tuesday instead of Wednesday — wrong expiry epoch
- Wrong holiday calendar lookup
- Wrong date in audit and reporting

---

## 3. Key Design Decisions

| Decision | Resolution | Rationale |
|---|---|---|
| What triggers NIGHT-specific logic? | `trade.tradingSession` contains `NIGHT` | Trade explicitly declares its session; no inference from timestamp needed |
| Where does the logical trading day boundary config live? | `MARKET_HOUR_RULE` — 4 new integer columns on the NIGHT rule row | Consistent with existing column structure (`OPENINGHOUR`/`OPENINGMIN` pattern); single source of truth; deleting the rule removes config automatically |
| What if no NIGHT rule configured for a market? | Reject — throw `MarketConfigurationException` | Silent fallback to `MarketHour` defaults would produce wrong expiry times with no visibility |
| How is NIGHT ordered in sort? | Force NIGHT to sort first via comparator — not by wall-clock `OPENINGHOUR` | `21:00` sorts after `16:00` numerically but is first in the logical trading day |
| Multi-session window calculation | Contiguous span: earliest start → latest end, max `getExpiryOffsetClosingTime()` wins | Existing behaviour — unchanged |
| Expiry for NIGHT rules | Same `getExpiryOffsetClosingTime()` formula — but Calendar base date is the **resolved trading date** instead of today | Same formula, same field, same comparison — only the base date changes for NIGHT |
| Java POJO | Keep 4 integer fields matching DB columns | Consistent with existing POJO structure |

---

## 4. Scope of Change

### What Changes

| Layer | Change |
|---|---|
| `MARKET_HOUR_RULE` table | 4 new integer columns for trading day boundary |
| `TradingSession` Java enum | Add `NIGHT` value with `tradingDayOrder() = 0` |
| `MarketHourRule` Java POJO | 4 new integer fields + 2 derived helper methods |
| Rule sort comparator | NIGHT forced to sort first |
| Session window match | Add midnight-spanning `else` branch |
| `getExpiryOffsetClosingTime()` | Use resolved trading date as Calendar base for NIGHT rules |
| `TradingDateResolver` | New Spring component — called only when trade has NIGHT session |
| Data | One new `MARKET_HOUR_RULE` row per market supporting NIGHT |

### What Does NOT Change

| Layer | Status |
|---|---|
| `MARKET_HOUR` table | No changes |
| All existing `MARKET_HOUR_RULE` rows | No changes — new columns are nullable |
| All existing REGULAR / PRE_MARKET / AFTER_HOURS trade paths | Zero behaviour change |
| Trade storage format (epoch timestamp) | No changes |
| API contracts | No changes |
| `getExpiryOffsetClosingTime()` formula itself | No changes — only the Calendar base date input changes for NIGHT |
| Max-expiry rule selection logic | No changes |

---

## 5. Schema Changes

### 5.1 `MARKET_HOUR_RULE` — Four New Integer Columns

These follow the exact same pattern as the existing `OPENINGHOUR` / `OPENINGMIN` / `CLOSINGHOUR` / `CLOSINGMIN` columns.

```sql
ALTER TABLE MARKET_HOUR_RULE
  ADD TRADINGDAY_OPENINGHOUR  NUMBER(2) NULL,
  ADD TRADINGDAY_OPENINGMIN   NUMBER(2) NULL,
  ADD TRADINGDAY_CLOSINGHOUR  NUMBER(2) NULL,
  ADD TRADINGDAY_CLOSINGMIN   NUMBER(2) NULL;

COMMENT ON COLUMN MARKET_HOUR_RULE.TRADINGDAY_OPENINGHOUR
  IS 'Hour component of TradingDayOpeningTime. Populated ONLY for NIGHT session rules. '
     'Together with TRADINGDAY_OPENINGMIN defines the start of the logical trading day '
     '(e.g. 21 for NASDAQ meaning 21:00). NULL for all other session types.';

COMMENT ON COLUMN MARKET_HOUR_RULE.TRADINGDAY_OPENINGMIN
  IS 'Minute component of TradingDayOpeningTime. Populated ONLY for NIGHT session rules. '
     '(e.g. 0 for NASDAQ meaning 21:00). NULL for all other session types.';

COMMENT ON COLUMN MARKET_HOUR_RULE.TRADINGDAY_CLOSINGHOUR
  IS 'Hour component of TradingDayClosingTime. Populated ONLY for NIGHT session rules. '
     'Together with TRADINGDAY_CLOSINGMIN defines the end of the logical trading day '
     '(e.g. 20 for NASDAQ meaning 20:02). NULL for all other session types.';

COMMENT ON COLUMN MARKET_HOUR_RULE.TRADINGDAY_CLOSINGMIN
  IS 'Minute component of TradingDayClosingTime. Populated ONLY for NIGHT session rules. '
     '(e.g. 2 for NASDAQ meaning 20:02). NULL for all other session types.';
```

> **Why nullable?** All existing rule rows have no concept of a trading day boundary. NULL explicitly signals "traditional 00:00–23:59 trading day". No default value is set to avoid implying a boundary where none exists.

> **Why integers not VARCHAR?** Consistent with existing `OPENINGHOUR`, `OPENINGMIN`, `CLOSINGHOUR`, `CLOSINGMIN` columns on `MARKET_HOUR_RULE`.

### 5.2 DB Constraint

```sql
-- Only NIGHT session rules may carry trading day boundary values
ALTER TABLE MARKET_HOUR_RULE ADD CONSTRAINT CHK_TRADING_DAY_BOUNDARY
  CHECK (
    TRADING_SESSION = 'NIGHT'
    OR (
      TRADINGDAY_OPENINGHOUR IS NULL AND
      TRADINGDAY_OPENINGMIN  IS NULL AND
      TRADINGDAY_CLOSINGHOUR IS NULL AND
      TRADINGDAY_CLOSINGMIN  IS NULL
    )
  );
```

### 5.3 NIGHT Enum Value in Session Constraint / Reference Table

```sql
-- If TradingSession is enforced via CHECK constraint, extend it:
ALTER TABLE MARKET_HOUR_RULE DROP CONSTRAINT CHK_TRADING_SESSION;
ALTER TABLE MARKET_HOUR_RULE ADD CONSTRAINT CHK_TRADING_SESSION
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
  OPENINGHOUR,             -- session window start: 21:00
  OPENINGMIN,
  CLOSINGHOUR,             -- session window end:   04:00
  CLOSINGMIN,
  EXPIRY_OFFSET,           -- expire 2 min after closing = 04:02
  TRADINGDAY_OPENINGHOUR,  -- logical trading day start: 21:00
  TRADINGDAY_OPENINGMIN,
  TRADINGDAY_CLOSINGHOUR,  -- logical trading day end:   20:02
  TRADINGDAY_CLOSINGMIN,
  CURRENCY
  -- ... other existing columns
)
VALUES (
  'NASDAQ',
  'NIGHT',
  21, 0,    -- OPENINGHOUR / OPENINGMIN
  4,  0,    -- CLOSINGHOUR / CLOSINGMIN
  2,        -- EXPIRY_OFFSET (minutes)
  21, 0,    -- TRADINGDAY_OPENINGHOUR / TRADINGDAY_OPENINGMIN  (21:00)
  20, 2,    -- TRADINGDAY_CLOSINGHOUR / TRADINGDAY_CLOSINGMIN  (20:02)
  'ALL'
);
```

#### Understanding the Four New Fields for NASDAQ

| Field | Value | Meaning |
|---|---|---|
| `TRADINGDAY_OPENINGHOUR` | `21` | Logical trading day starts at 21:00 (Tuesday night for Wednesday's trades) |
| `TRADINGDAY_OPENINGMIN` | `0` | |
| `TRADINGDAY_CLOSINGHOUR` | `20` | Logical trading day ends at 20:02 (Wednesday evening, after AFTER_HOURS + offset) |
| `TRADINGDAY_CLOSINGMIN` | `2` | |

Together `TRADINGDAY_OPENINGTIME = 21:00` and `TRADINGDAY_CLOSINGTIME = 20:02` make it explicit that this market does **not** use the traditional 00:00–23:59 day. Anyone viewing this rule row immediately understands the market operates on a shifted trading day.

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
     * NIGHT is always first (order = 0) even though its wall-clock opening hour (21)
     * is numerically after PRE_MARKET (e.g. 4) and AFTER_HOURS (e.g. 16).
     *
     * This ordering is used exclusively for the rule sort comparator.
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

## 7. Java POJO Change

Four new integer fields added to `MarketHourRule`, matching the four new DB columns exactly. Two derived helper methods are added for convenience — no behaviour logic lives in the POJO.

```java
public class MarketHourRule {

    // ... existing fields unchanged ...

    // TRADING_SESSION enum — add NIGHT value (see section 6)
    private TradingSession tradingSession;

    // Existing session window fields — UNCHANGED
    private int openingHour;
    private int openingMin;
    private int closingHour;
    private int closingMin;
    private int expiryOffset;

    // NEW — logical trading day boundary, populated ONLY for NIGHT session rules
    // NULL-safe: use hasTradingDayBoundary() before calling helpers below
    private Integer tradingDayOpeningHour;  // maps to TRADINGDAY_OPENINGHOUR
    private Integer tradingDayOpeningMin;   // maps to TRADINGDAY_OPENINGMIN
    private Integer tradingDayClosingHour;  // maps to TRADINGDAY_CLOSINGHOUR
    private Integer tradingDayClosingMin;   // maps to TRADINGDAY_CLOSINGMIN

    /**
     * Returns true if this rule defines a non-traditional logical trading day boundary.
     * Only NIGHT session rules will return true.
     */
    public boolean hasTradingDayBoundary() {
        return tradingDayOpeningHour != null
            && tradingDayOpeningMin  != null
            && tradingDayClosingHour != null
            && tradingDayClosingMin  != null;
    }

    /**
     * Convenience: returns the trading day opening time as a LocalTime.
     * Call only after confirming hasTradingDayBoundary() == true.
     */
    public LocalTime getTradingDayOpeningTime() {
        return LocalTime.of(tradingDayOpeningHour, tradingDayOpeningMin);
    }

    /**
     * Convenience: returns the trading day closing time as a LocalTime.
     * Call only after confirming hasTradingDayBoundary() == true.
     */
    public LocalTime getTradingDayClosingTime() {
        return LocalTime.of(tradingDayClosingHour, tradingDayClosingMin);
    }

    // ... getters / setters for all fields ...
}
```

---

## 8. Code Changes

### 8.1 Rule Sort Comparator

**Location:** Wherever the `MarketHourRule` list is sorted before evaluation.

**Problem:** Current sort is by `OPENINGHOUR` + `OPENINGMIN` ascending. NIGHT (hour=21) sorts **last**, but must be **first** in the logical trading day.

```java
// BEFORE
rules.sort(Comparator
    .comparingInt(MarketHourRule::getOpeningHour)
    .thenComparingInt(MarketHourRule::getOpeningMin));

// AFTER
private static final Comparator<MarketHourRule> TRADING_DAY_ORDER =
    Comparator
        .comparingInt((MarketHourRule r) ->
            r.getTradingSession() == TradingSession.NIGHT ? 0 : 1
        )
        .thenComparingInt(MarketHourRule::getOpeningHour)
        .thenComparingInt(MarketHourRule::getOpeningMin);

rules.sort(TRADING_DAY_ORDER);
```

> **How it works:** NIGHT rules get bucket `0`, all others get bucket `1`. Within each bucket, existing sort by `openingHour` + `openingMin` is preserved exactly. Zero behaviour change for all non-NIGHT rules.

---

### 8.2 Session Window Match — Midnight-Spanning Check

**Location:** The method that checks whether a trade's timestamp falls within a rule's `[openingTime, closingTime]` window.

**Problem:** When `openingHour > closingHour` (e.g. 21 > 4), the standard `>=` / `<=` check always returns false.

```java
private boolean isWithinSessionWindow(LocalTime tradeTime, MarketHourRule rule) {
    LocalTime open  = LocalTime.of(rule.getOpeningHour(), rule.getOpeningMin());
    LocalTime close = LocalTime.of(rule.getClosingHour(), rule.getClosingMin());

    if (!open.isAfter(close)) {
        // Normal session: openingTime <= closingTime (e.g. 09:30 to 16:00)
        // Existing behaviour — untouched
        return !tradeTime.isBefore(open) && !tradeTime.isAfter(close);
    } else {
        // Midnight-spanning session: openingTime > closingTime (e.g. 21:00 to 04:00)
        // Valid if time is >= 21:00 (evening) OR <= 04:00 (early morning)
        return !tradeTime.isBefore(open) || !tradeTime.isAfter(close);
    }
}
```

> **Impact on existing rules:** Zero. The `else` branch is only reachable when `openingHour > closingHour`, which never occurs for any existing rule today.

---

### 8.3 `TradingDateResolver` — New Component

**Purpose:** Single, centralised component that resolves the logical trading date for a trade. All code that needs a trading date for a NIGHT trade must route through here.

```java
@Component
public class TradingDateResolver {

    private final HolidayCalendarRepository holidayRepo;
    private final MarketHourRuleRepository  ruleRepo;

    /**
     * Resolves the logical trading date for a trade against a given market.
     *
     * For non-NIGHT trades:
     *   Returns the calendar date in market timezone. Identical to existing behaviour.
     *
     * For NIGHT trades:
     *   The night session physically starts on calendar day T (e.g. Tuesday 21:00)
     *   but belongs to trading day T+1 (Wednesday).
     *
     *   Resolution rules (all times in market timezone):
     *
     *   Case 1 — tradeTime >= TradingDayOpeningTime (e.g. >= 21:00):
     *     Trade submitted on the "evening side" of the night session.
     *     Trading date = next business day after calendar date.
     *     Example: Tuesday 21:30 → Wednesday
     *
     *   Case 2 — tradeTime <= session closingTime (e.g. <= 04:00):
     *     Trade submitted on the "early morning side" of the night session.
     *     Calendar date is already the next day (Wednesday 03:00).
     *     Trading date = calendar date (Wednesday).
     *     Example: Wednesday 03:00 → Wednesday
     *
     *   Case 3 — tradeTime between closingTime and TradingDayOpeningTime (e.g. 04:01–20:59):
     *     Trade tagged as NIGHT but submitted outside the night session window.
     *     Should be caught by upstream validation. Treated conservatively as calendar date.
     */
    public LocalDate resolve(Trade trade, MarketHour market) {
        if (!trade.getSessions().contains(TradingSession.NIGHT)) {
            // All non-NIGHT trades — zero change from existing behaviour
            return toMarketLocalDate(trade.getTimestamp(), market.getTimezone());
        }

        MarketHourRule nightRule = ruleRepo
            .findByMarketIdAndSession(market.getMarketId(), TradingSession.NIGHT)
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

        ZoneId     tz      = ZoneId.of(market.getTimezone());
        LocalTime  time    = Instant.ofEpochMilli(epochMillis).atZone(tz).toLocalTime();
        LocalDate  calDate = Instant.ofEpochMilli(epochMillis).atZone(tz).toLocalDate();

        LocalTime tradingDayOpen  = nightRule.getTradingDayOpeningTime(); // 21:00
        LocalTime sessionClose    = LocalTime.of(
            nightRule.getClosingHour(), nightRule.getClosingMin());       // 04:00

        if (!time.isBefore(tradingDayOpen)) {
            // Case 1: >= 21:00 on Tuesday night → Wednesday's trading day
            return nextBusinessDay(calDate.plusDays(1), market);
        }

        if (!time.isAfter(sessionClose)) {
            // Case 2: <= 04:00 on Wednesday morning → still Wednesday's trading day
            return calDate; // calDate is already Wednesday
        }

        // Case 3: outside night session window — treat as calendar date
        return calDate;
    }

    /**
     * Advances from the given candidate date, skipping weekends and market holidays,
     * until a valid business day is found.
     *
     * Holiday check always uses the TARGET trading date (not the submission date).
     *
     * Example: Friday 21:30 trade
     *   plusDays(1) = Saturday → weekend → Sunday → weekend → Monday
     *   Monday = holiday? → Tuesday → valid ✅
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
        return date.getDayOfWeek() == DayOfWeek.SATURDAY
            || date.getDayOfWeek() == DayOfWeek.SUNDAY;
    }

    private LocalDate toMarketLocalDate(long epochMillis, String timezone) {
        return Instant.ofEpochMilli(epochMillis)
            .atZone(ZoneId.of(timezone))
            .toLocalDate();
    }
}
```

---

### 8.4 `getExpiryOffsetClosingTime()` — Use Resolved Trading Date for NIGHT

**Location:** The method (or the code that calls it) that builds the `Calendar` object for expiry comparison.

**Current behaviour:** Calendar is built using today's date in market timezone, then `CLOSINGHOUR` / `CLOSINGMIN` / `EXPIRY_OFFSET` are applied.

**Problem for NIGHT:** A NIGHT trade placed at Tuesday 21:30 resolves to Wednesday's trading day. The session closes at `04:00`. The Calendar must be built on **Wednesday** at `04:00`, not Tuesday at `04:00`. Using Tuesday would produce an expiry epoch in the past, causing the trade to expire immediately.

**Fix:** Pass the resolved trading date into the Calendar construction. The formula itself does not change.

```java
/**
 * Computes the expiry epoch (ms) for a rule against a given base date.
 *
 * Formula is identical to existing getExpiryOffsetClosingTime() —
 * the only change is that calendarBaseDate is now passed in instead
 * of always being derived from "today".
 *
 * For non-NIGHT rules: calendarBaseDate == today (existing behaviour, zero change).
 * For NIGHT rules:     calendarBaseDate == resolved trading date (e.g. Wednesday).
 *
 * NIGHT closing time (04:00) lands on the SAME calendar day as the resolved
 * trading date (Wednesday morning), so no further date adjustment is needed.
 *
 * @param rule              the matched MarketHourRule
 * @param calendarBaseDate  the logical trading date to anchor the Calendar to
 * @param marketTimezone    the market's timezone
 */
public long getExpiryOffsetClosingTime(
        MarketHourRule rule,
        LocalDate calendarBaseDate,
        ZoneId marketTimezone) {

    // Build Calendar anchored to calendarBaseDate in market timezone
    // This is the same construction as today — only the date input changes
    Calendar cal = Calendar.getInstance(TimeZone.getTimeZone(marketTimezone));
    cal.set(Calendar.YEAR,         calendarBaseDate.getYear());
    cal.set(Calendar.MONTH,        calendarBaseDate.getMonthValue() - 1); // Calendar months are 0-based
    cal.set(Calendar.DAY_OF_MONTH, calendarBaseDate.getDayOfMonth());
    cal.set(Calendar.HOUR_OF_DAY,  rule.getClosingHour());
    cal.set(Calendar.MINUTE,       rule.getClosingMin());
    cal.set(Calendar.SECOND,       0);
    cal.set(Calendar.MILLISECOND,  0);

    // Add expiry offset — identical to existing logic
    cal.add(Calendar.MINUTE, rule.getExpiryOffset());

    return cal.getTime().getTime(); // epoch ms
}
```

**Calling code — how calendarBaseDate is determined:**

```java
// In your rule evaluation service, where matching rules are collected
// and the max-expiry winner is selected:

LocalDate calendarBaseDate;

if (trade.getSessions().contains(TradingSession.NIGHT)) {
    // NIGHT trades: use resolved trading date (next business day)
    calendarBaseDate = tradingDateResolver.resolve(trade, market);
} else {
    // All other trades: use today's calendar date — ZERO change from existing
    calendarBaseDate = toMarketLocalDate(trade.getTimestamp(), market.getTimezone());
}

// Existing max-expiry selection logic — unchanged
MarketHourRule winner = matchingRules.stream()
    .max(Comparator.comparingLong(rule ->
        getExpiryOffsetClosingTime(rule, calendarBaseDate, marketTimezone)))
    .orElse(null);
```

---

### 8.5 Service Layer Validation on Rule Save

Enforced when a `MarketHourRule` is created or updated via the admin/configuration layer.

```java
public void validateRule(MarketHourRule rule) {

    boolean isNight     = rule.getTradingSession() == TradingSession.NIGHT;
    boolean hasBoundary = rule.hasTradingDayBoundary();

    // Non-NIGHT rules must not carry boundary fields
    if (!isNight && hasBoundary) {
        throw new InvalidMarketHourRuleException(
            "TRADINGDAY_OPENINGHOUR/MIN and TRADINGDAY_CLOSINGHOUR/MIN are only valid " +
            "for NIGHT session rules. Session: " + rule.getTradingSession()
        );
    }

    // NIGHT rules must carry all four boundary fields
    if (isNight && !hasBoundary) {
        throw new InvalidMarketHourRuleException(
            "NIGHT session rules must specify all four trading day boundary fields: " +
            "TRADINGDAY_OPENINGHOUR, TRADINGDAY_OPENINGMIN, " +
            "TRADINGDAY_CLOSINGHOUR, TRADINGDAY_CLOSINGMIN."
        );
    }

    // NIGHT rules must be midnight-spanning: openingHour must be > closingHour
    if (isNight) {
        LocalTime open  = LocalTime.of(rule.getOpeningHour(), rule.getOpeningMin());
        LocalTime close = LocalTime.of(rule.getClosingHour(), rule.getClosingMin());
        if (!open.isAfter(close)) {
            throw new InvalidMarketHourRuleException(
                "NIGHT session openingTime must be after closingTime (session must span " +
                "midnight). Got openingTime=" + open + ", closingTime=" + close
            );
        }
    }

    // Hour fields must be in range 0–23, minute fields in range 0–59
    if (isNight) {
        validateHourMin("TRADINGDAY_OPENINGHOUR", rule.getTradingDayOpeningHour(),
                        "TRADINGDAY_OPENINGMIN",  rule.getTradingDayOpeningMin());
        validateHourMin("TRADINGDAY_CLOSINGHOUR", rule.getTradingDayClosingHour(),
                        "TRADINGDAY_CLOSINGMIN",  rule.getTradingDayClosingMin());
    }
}

private void validateHourMin(String hourField, int hour, String minField, int min) {
    if (hour < 0 || hour > 23) {
        throw new InvalidMarketHourRuleException(
            hourField + " must be between 0 and 23. Got: " + hour);
    }
    if (min < 0 || min > 59) {
        throw new InvalidMarketHourRuleException(
            minField + " must be between 0 and 59. Got: " + min);
    }
}
```

---

## 9. Expiry Scenarios

All scenarios assume NASDAQ NIGHT rule:
`OPENINGHOUR=21, OPENINGMIN=0, CLOSINGHOUR=4, CLOSINGMIN=0, EXPIRY_OFFSET=2`.

```
── NIGHT only ──────────────────────────────────────────────────────────────────
Trade sessions:       NIGHT
Trade placed:         Tuesday 21:30 market TZ
Calendar date:        Tuesday
Resolved trading date: Wednesday  (21:30 >= 21:00 → next business day)
Calendar base date:   Wednesday
getExpiryOffsetClosingTime:
  Calendar set to Wednesday, hour=4, min=0, + 2min = Wednesday 04:02
Expiry epoch:         Wednesday 04:02 market TZ

── NIGHT + PRE_MARKET ──────────────────────────────────────────────────────────
Trade sessions:       NIGHT, PRE_MARKET
Trade placed:         Tuesday 22:00
Resolved trading date: Wednesday
Matching rules:       NIGHT (expiryTime = Wed 04:02), PRE_MARKET (expiryTime = Wed 09:30)
Max expiryTime:       Wednesday 09:30  → PRE_MARKET rule wins
Expiry epoch:         Wednesday 09:30

── NIGHT + PRE_MARKET + REGULAR ────────────────────────────────────────────────
Trade sessions:       NIGHT, PRE_MARKET, REGULAR
Trade placed:         Tuesday 21:30
Resolved trading date: Wednesday
Max expiryTime:       Wednesday 16:00  → REGULAR rule wins
Expiry epoch:         Wednesday 16:00

── NIGHT + PRE_MARKET + REGULAR + AFTER_HOURS ──────────────────────────────────
Trade sessions:       NIGHT, PRE_MARKET, REGULAR, AFTER_HOURS
Trade placed:         Tuesday 21:30
Resolved trading date: Wednesday
Max expiryTime:       Wednesday 20:00  → AFTER_HOURS rule wins
Expiry epoch:         Wednesday 20:00

── REGULAR only — placed during night hours (no NIGHT session on trade) ────────
Trade sessions:       REGULAR (or none → defaults to REGULAR)
Trade placed:         Tuesday 22:00
Calendar base date:   Tuesday  (no date shift — NIGHT not on trade)
Market closed:        Hold till Wednesday REGULAR openingTime
Expiry:               Existing hold/release logic — zero change

── NIGHT trade on the early-morning side (after midnight) ──────────────────────
Trade sessions:       NIGHT
Trade placed:         Wednesday 03:00
Calendar date:        Wednesday
tradeTime (03:00) <= sessionClose (04:00) → Case 2
Resolved trading date: Wednesday  (calDate returned as-is)
Calendar base date:   Wednesday
Expiry epoch:         Wednesday 04:02
```

---

## 10. Holiday Calendar Behaviour

Holiday calendar checks always use the **resolved trading date**, not the physical submission date. This is handled automatically by routing through `TradingDateResolver` before any holiday check.

| Scenario | Trade Placed | Calendar Date | Resolved Trading Date | Holiday Check On | Result |
|---|---|---|---|---|---|
| Normal Wednesday | Tue 21:30 | Tuesday | Wednesday | Wednesday | ✅ Valid |
| Wednesday is holiday | Tue 21:30 | Tuesday | Wednesday → Thursday | Thursday | Hold till Thu open |
| Normal Monday | Fri 21:30 | Friday | Monday | Monday | ✅ Valid |
| Monday is holiday | Fri 21:30 | Friday | Monday → Tuesday | Tuesday | Hold till Tue open |
| Early morning, NIGHT trade | Wed 03:00 | Wednesday | Wednesday | Wednesday | ✅ Valid |
| Wed is holiday, early morning | Wed 03:00 | Wednesday | Wednesday → Thursday | Thursday | Hold till Thu open |

> `nextBusinessDay()` inside `TradingDateResolver` iterates forward skipping both weekends and market-specific holidays until a valid trading day is found. The holiday calendar used is always the **target market's** per-market calendar.

---

## 11. Validation Rules

| Rule | Enforced At |
|---|---|
| All four `TRADINGDAY_*` fields must be NULL for non-NIGHT rules | DB constraint + service layer |
| NIGHT rules must have all four `TRADINGDAY_*` fields populated | Service layer |
| NIGHT rule `openingTime` must be after `closingTime` (midnight-spanning) | Service layer |
| Hour fields 0–23, minute fields 0–59 | Service layer |
| Trade with NIGHT session, market has no NIGHT rule → `MarketConfigurationException` | `TradingDateResolver` |
| Trade tagged NIGHT but placed outside night session window → caught at trade intake | Trade intake validation layer |

---

## 12. Regression Test Matrix

| # | Trade Sessions | Trade Placed At (market TZ) | Market Condition | Expected Trading Date | Expected Expiry / Behaviour |
|---|---|---|---|---|---|
| 1 | `REGULAR` | Tue 22:00 | NASDAQ, normal | Tuesday | Hold till Wed 09:30 (market closed) |
| 2 | `NIGHT` | Tue 21:30 | NASDAQ, normal | Wednesday | Wed 04:02 |
| 3 | `NIGHT` | Wed 03:00 | NASDAQ, normal | Wednesday | Wed 04:02 |
| 4 | `NIGHT` | Wed 10:00 | NASDAQ, normal | Wednesday | Validation error — outside night window |
| 5 | `NIGHT + PRE_MARKET` | Tue 21:30 | NASDAQ, normal | Wednesday | Wed 09:30 |
| 6 | `NIGHT + REGULAR` | Tue 22:00 | NASDAQ, normal | Wednesday | Wed 16:00 |
| 7 | `NIGHT + PRE_MARKET + AFTER_HOURS` | Tue 21:30 | NASDAQ, normal | Wednesday | Wed 20:00 |
| 8 | `NIGHT` | Fri 21:30 | NASDAQ, Mon normal | Monday | Mon 04:02 |
| 9 | `NIGHT` | Fri 21:30 | NASDAQ, Mon = holiday | Tuesday | Tue 04:02 |
| 10 | `NIGHT` | Wed 03:00 | NASDAQ, Wed = holiday | Thursday | Thu 04:02 |
| 11 | `NIGHT` | Tue 21:30 | Market with no NIGHT rule | — | `MarketConfigurationException` |
| 12 | `PRE_MARKET + AFTER_HOURS` | Any | Any legacy market | Calendar date | Existing behaviour — unchanged |
| 13 | `REGULAR` | Any | Any legacy market | Calendar date | Existing behaviour — unchanged |
| 14 | `NIGHT` | Tue 21:30 | NASDAQ, normal | Wednesday | `getExpiryOffsetClosingTime` epoch = Wed 04:02 (not Tue 04:02) |
| 15 | `NIGHT + PRE_MARKET` | Tue 21:30 | NASDAQ, normal | Wednesday | Max expiry = Wed 09:30 wins over Wed 04:02 |

---

## 13. Migration & Rollout Plan

### Phase 1 — Schema (zero risk, deploy independently)

```sql
-- Add 4 new nullable columns to MARKET_HOUR_RULE
ALTER TABLE MARKET_HOUR_RULE
  ADD TRADINGDAY_OPENINGHOUR  NUMBER(2) NULL,
  ADD TRADINGDAY_OPENINGMIN   NUMBER(2) NULL,
  ADD TRADINGDAY_CLOSINGHOUR  NUMBER(2) NULL,
  ADD TRADINGDAY_CLOSINGMIN   NUMBER(2) NULL;

-- Add boundary constraint
ALTER TABLE MARKET_HOUR_RULE ADD CONSTRAINT CHK_TRADING_DAY_BOUNDARY
  CHECK (TRADING_SESSION = 'NIGHT'
         OR (TRADINGDAY_OPENINGHOUR IS NULL AND TRADINGDAY_OPENINGMIN  IS NULL
         AND TRADINGDAY_CLOSINGHOUR IS NULL AND TRADINGDAY_CLOSINGMIN  IS NULL));

-- Extend session constraint / reference table to include NIGHT
```

No existing rows are touched. No behaviour change.

### Phase 2 — Code (deploy behind feature flag)

- Add `NIGHT` to `TradingSession` enum
- Add 4 new fields + helpers to `MarketHourRule` POJO
- Deploy sort comparator fix (NIGHT branch unreachable — no NIGHT rules in DB yet)
- Deploy `isWithinSessionWindow()` midnight-span fix (unreachable — no NIGHT rules yet)
- Deploy `TradingDateResolver` (guarded by `trade.getSessions().contains(NIGHT)`)
- Deploy updated `getExpiryOffsetClosingTime()` call site (NIGHT branch unreachable)
- Deploy service layer validation

All new code paths are **dead code** until Phase 3 data is inserted.

### Phase 3 — NASDAQ configuration

```sql
INSERT INTO MARKET_HOUR_RULE
  (MARKET_ID, TRADING_SESSION, OPENINGHOUR, OPENINGMIN, CLOSINGHOUR, CLOSINGMIN,
   EXPIRY_OFFSET, TRADINGDAY_OPENINGHOUR, TRADINGDAY_OPENINGMIN,
   TRADINGDAY_CLOSINGHOUR, TRADINGDAY_CLOSINGMIN, CURRENCY)
VALUES
  ('NASDAQ', 'NIGHT', 21, 0, 4, 0, 2, 21, 0, 20, 2, 'ALL');
```

Run full regression test matrix (all 15 cases).  
Smoke test all downstream consumers: expiry, hold/release, reporting, settlement, audit.

### Phase 4 — Subsequent markets

Repeat Phase 3 data insert only — **zero code changes required**.

---

## 14. Out of Scope

| Topic | Notes |
|---|---|
| Night Session cancellation on holiday eves | `nextBusinessDay()` handles date shift automatically, but business must confirm whether Night Session itself should be open or cancelled when the resolved trading date is a holiday |
| UI / admin console changes for configuring NIGHT rules | Separate ticket — service layer validation in section 11 must be enforced by the UI |
| Intraday modification of a NIGHT trade crossing midnight | Modification flow re-runs same evaluation; `TradingDateResolver` is re-invoked — should work, needs explicit test |
| Markets where Night Session definition changes seasonally | Not considered — treat as rule delete + reinsert |
| Migrating legacy `Calendar` usage to `java.time` | Out of scope — `getExpiryOffsetClosingTime()` fix works within existing `Calendar` pattern |
