Good questions — let me answer both clearly and concisely.

---

## Why Night Session columns on `MarketHour` and not `MarketHourRule`?

`MarketHourRule` is **per-currency, per-session, per-market** — it can have dozens of rows for the same market. If you put `nightSessionStart/End` there, you'd need to keep it **identical across every rule row for the same market**, because the night session boundary is a market-level fact, not a per-currency fact. NASDAQ's night session starts at 21:00 whether you're trading USD, EUR, or any other currency.

That's a **data integrity trap** — nothing stops two rule rows for the same market having different values, and your system would have to decide which one to trust.

`MarketHour` has exactly **one row per market** — the right place for a fact that belongs to the market as a whole.

Think of it this way:
- `MarketHour` = *"what is this market like?"* → one truth per market
- `MarketHourRule` = *"how do we behave for this currency/session combo?"* → many rows, rule-specific behaviour

Night session window is a *"what is this market like"* fact.

---

## Why not `TradingDayStart` / `TradingDayEnd` on `MarketHourRule`?

Your original proposal was essentially: add two fields to `MarketHourRule` that define the **logical trading day boundary** (e.g. 20:01 → 20:00 next day) so the system knows when a new trading day begins.

Three problems with that:

**1. Same data integrity trap as above.** Every rule row for NASDAQ would need to carry the same boundary values. Redundant and fragile.

**2. It conflates two different concepts.** The trading day boundary (when does a new day start?) and the session window (when is THIS session active?) are separate concerns. Mixing them into one row makes the model harder to reason about.

**3. You don't actually need them as explicit fields.** The trading day boundary is already *implied* by `nightSessionEnd` on `MarketHour`. If night session ends at 04:00, then the trading day boundary is 04:00. Storing it separately would be **redundant data** that can drift out of sync.

---

## Better names than `TradingDayStart` / `TradingDayEnd`

If you did want explicit boundary fields (say for documentation clarity), here are better names:

| Name | Why better |
|---|---|
| `tradingDayAnchorStart` / `tradingDayAnchorEnd` | "Anchor" signals it's a reference point, not a session window |
| `dayBoundaryOpen` / `dayBoundaryClose` | Clear it's a boundary, not market open/close |
| `sessionDayStart` / `sessionDayEnd` | Signals it scopes the whole day's sessions |

But honestly — **don't add them**. They'd be derived values from `nightSessionStart/End`. Derived values stored as columns are a maintenance burden. Compute the boundary from the night session config when you need it.
