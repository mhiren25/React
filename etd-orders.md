# KB: ETD Orders

**Feature slug:** `etd-orders`
**Last updated:** <!-- run prepare_copilot_prompt.py to refresh -->
**Generated from:** `python scripts/prepare_copilot_prompt.py --feature etd-orders`

---

## Business summary

ETD (Exchange Traded Derivatives) order management covers the full lifecycle of
Call/Put orders — placement via SecTrader, tracking in Topaz OMS, and state
transitions through Open → Blocking → Filled / Cancelled. This feature is a
prerequisite for blocking, allocation, and fill-verification scenarios.

---

## GUIs involved

### SecTrader UI

| Action | Wrapper / Method | Key parameters |
|--------|-----------------|----------------|
| Place ETD Call/Put order | `<!-- WRAPPER -->` | ISIN, ETDType, TradingPlace, ContractMonth, Transaction, Validity, Quantity |
| Capture external order id after submit | `<!-- WRAPPER -->` | Returns string id from submission response |
| Verify order submitted successfully | `<!-- WRAPPER -->` | Checks confirmation indicator |

**ETD order parameter reference:**

| Field | Example value | Notes |
|-------|--------------|-------|
| ISIN | DE0005140008 | From XML fixture |
| ETDType | Call / Put | |
| Currency | EUR | |
| TradingPlace | EUX | |
| ContractMonth | 122026 | MMYYYY format |
| Transaction | Buy / Sell | |
| Validity | T | T = Good till date, D = Day |
| Quantity | 1 | integer |

---

### Topaz OMS UI

| Action | Wrapper / Method | Key parameters |
|--------|-----------------|----------------|
| Find client order by external order id | `<!-- WRAPPER -->` | external_order_id (string) |
| Verify client order state | `<!-- WRAPPER -->` | order_id, expected_state (string) |
| Read order groupId | `<!-- WRAPPER -->` | order_id → returns groupId string |
| Open order details panel | `<!-- WRAPPER -->` | order_id |

---

## Reusable assertions

```python
# External order id was captured after SecTrader submission
assert external_order_id is not None, "External order id not captured"
assert external_order_id != "", "External order id is empty"

# Client order located in Topaz OMS
assert client_order is not None, f"Order not found for external id: {external_order_id}"

# Order state checks
assert order_state == "Open",     f"Expected Open, got {order_state}"
assert order_state == "Blocking", f"Expected Blocking, got {order_state}"

# secondaryGroupId integrity (used in blocking scenarios — see blocking.md)
assert block_order.secondaryGroupId == client_order.groupId, (
    f"secondaryGroupId {block_order.secondaryGroupId} != "
    f"client order groupId {client_order.groupId}"
)
```

---

## Test data schema (XML)

```xml
<TestData>
  <Account>
    <BR><!-- REPLACE: valid BR account --></BR>
    <Custody><!-- REPLACE: valid custody account --></Custody>
  </Account>
  <ETDOrder>
    <ISIN>DE0005140008</ISIN>
    <ETDType>Call</ETDType>
    <Currency>EUR</Currency>
    <TradingPlace>EUX</TradingPlace>
    <ContractMonth>122026</ContractMonth>
    <Transaction>Buy</Transaction>
    <Validity>T</Validity>
    <Quantity>1</Quantity>
  </ETDOrder>
</TestData>
```

---

## Related KB docs

| Feature | KB doc | Relationship |
|---------|--------|-------------|
| Manual block flow | `docs/kb/blocking.md` | ETD order is prerequisite for blocking |
| Allocation modes | `docs/kb/allocation.md` | Follows blocking step |
| Fill verification | `docs/kb/etd-fill.md` | Post-execution state checks |

---

## Missing wrappers / gaps

| Gap | Proposed helper signature | Found in scenario |
|-----|--------------------------|------------------|
| <!-- wrapper name --> | <!-- def helper(params) -> type --> | <!-- file --> |

---

## Change log

| Date | Change | Author |
|------|--------|--------|
| <!-- date --> | Initial stub | automated |
