# KB: {Feature Name}

**Feature slug:** `{feature-slug}`
**Last updated:** {YYYY-MM-DD}
**Generated from:** `python scripts/prepare_copilot_prompt.py --feature {feature-slug} --merge`

---

## Business summary

<!-- TODO: 2-3 sentences describing what this feature does and why it exists.
     What business action does it automate? What is the end state? -->

---

## GUIs involved

<!--
  One section per GUI. If the feature only touches one GUI, remove the other.
  If more GUIs are added later, copy the section block and fill in.
-->

### {GUI Name 1}

| Action | Wrapper / Method | Key parameters |
|--------|-----------------|----------------|
| <!-- action --> | `<!-- wrapper_name(...) -->` | <!-- params --> |

---

### {GUI Name 2}

| Action | Wrapper / Method | Key parameters |
|--------|-----------------|----------------|
| <!-- action --> | `<!-- wrapper_name(...) -->` | <!-- params --> |

---

## Wrapper / method reference

<!--
  List all wrappers relevant to this feature.
  Format: module_path.ClassName.method_name(param: type) -> return_type
  Notes: what the wrapper does, any important side effects or return values
-->

- `<!-- module.Class.method(params) -->` — <!-- description -->

---

## Reusable assertions

```python
# Replace with real assertion patterns from your test files

# assert <condition>, "<message>"
```

---

## Test data schema (XML)

```xml
<TestData>
  <!-- Group by logical sections -->
  <Account>
    <BR><!-- REPLACE: valid BR account --></BR>
    <Custody><!-- REPLACE: valid custody account --></Custody>
  </Account>
  <{FeatureSection}>
    <!-- add data fields here -->
  </{FeatureSection}>
</TestData>
```

---

## Related KB docs

| Feature | KB doc | Relationship |
|---------|--------|-------------|
| <!-- feature --> | `docs/kb/<!-- slug -->.md` | <!-- depends on / required by / extends --> |

---

## Missing wrappers / gaps

| Gap | Proposed helper signature | Found in scenario |
|-----|--------------------------|------------------|
| <!-- description --> | `def <!-- helper_name -->(<!-- params -->) -> <!-- type -->:` | <!-- file --> |

---

## Notes

<!-- Preconditions, state machine summary, environment dependencies, known issues -->

---

## Change log

| Date | Change | Author |
|------|--------|--------|
| {YYYY-MM-DD} | Initial stub | <!-- name --> |
