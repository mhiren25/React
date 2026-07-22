# Copilot Prompt: Struts 6.4 → 7.2.1 + struts2-jquery-plugin 5.4 → 6.1 Migration

## Context to give Copilot up front

```
We are migrating a Java/Spring application from:
  - Apache Struts 6.4.x → 7.2.1
  - struts2-jquery-plugin 5.4.x → 6.1.x

The application currently uses struts2-spring-plugin and it works correctly today.
Do not change Spring wiring unless a Struts 7 change specifically requires it.

Struts 7 is a major version with real breaking changes, not just a dependency bump:
  1. Jakarta EE migration: javax.servlet.* → jakarta.servlet.*, and the minimum
     Java version is now Java 17. Any import of javax.servlet, javax.servlet.http,
     or javax.servlet.jsp must move to the jakarta.* equivalent, and any container
     (Tomcat/etc.) config tied to javax must be checked.
  2. Namespace matching default changed from "loose" to "exact match" for Action
     namespaces. Any hardcoded links or redirects that relied on partial/loose
     namespace matching may 404 after upgrade and need explicit namespace updates.
  3. OGNL security hardening:
     - Static field access via OGNL is restricted by default. Code relying on
       ${@some.Class@FIELD} or similar static access needs the value copied into
       an accessible field/helper class or added to the OGNL context.
     - Only an allowlist of map types can be instantiated from OGNL expressions.
     - An OGNL expression max length is enforced.
     - Struts 7 uses an OGNL allowlist model instead of the old exclusion list —
       POJOs/DTOs used for form/request parameter injection and template rendering
       may need explicit allowlisting.
  4. Removed plugins: the Struts 1 plugin and the Sitemesh plugin are removed in
     Struts 7. If either is referenced anywhere (pom.xml, struts.xml, imports),
     flag it — it needs manual refactoring, not an automated fix.
  5. struts2-jquery-plugin 6.x is the Jakarta-EE-compatible line that supports
     Struts 7 / Java 17 (5.x plugin targets javax/Struts 6 and is NOT compatible
     with Struts 7). Its transitive deps (jakarta.servlet-api, jakarta.servlet.jsp-api,
     jakarta.inject-api, jakarta.interceptor-api) also move to jakarta.* — check for
     version conflicts with other jakarta.* deps already in the module.
  6. Deprecated action-related interfaces flagged since 6.x may be fully removed
     in 7.x — check for compiler errors on anything still using the old
     pre-6.x-deprecated interfaces.

Our own struts-plugin.xml / struts.xml interceptor stacks, validators, and result
types should also be checked against the Struts 7 default stack, since some
defaults changed (e.g., stricter parameter interceptor behavior tied to the OGNL
changes above).
```

---

## Phase 1 — Discovery / Inventory (do this first, across the whole repo)

Ask Copilot to produce an inventory before touching any code:

```
Scan the repository and produce a categorized inventory (as a markdown table) of
every location that needs attention for the Struts 6.4 → 7.2.1 and
struts2-jquery-plugin 5.4 → 6.1 migration. For each finding, give: file path,
line number, current code/config snippet, and which category below it falls into.

Categories to scan for:
A. Build files: pom.xml / build.gradle entries for struts2-core, struts2-spring-plugin,
   struts2-jquery-plugin (and its sibling artifacts: grid/datatables/richtext/tree
   plugins if present), and any explicit servlet-api / jsp-api dependency.
B. javax.servlet.* / javax.servlet.http.* / javax.servlet.jsp.* imports in Java,
   JSP, and tag files.
C. web.xml or WebApplicationInitializer entries referencing javax.servlet.
D. struts.xml / struts-plugin.xml: namespace declarations, action mappings,
   interceptor-stack definitions, result types, and any <constant> overrides
   related to OGNL, static access, or namespace matching.
E. OGNL expressions in JSP/FreeMarker/Velocity templates and in Java
   (ValueStack / ActionContext usage) that reference static fields
   (pattern: @package.Class@FIELD).
F. Any reference to org.apache.struts2.dispatcher (or related) classes whose
   package or class name changed between 6.x and 7.x.
G. Any use of the Struts 1 plugin or Sitemesh plugin.
H. Any custom interceptors, validators, or result types that extend/implement
   Struts framework classes whose signatures may have changed.
I. jQuery plugin tags in JSPs (<sj:.../> etc.) — flag ones using features/attributes
   that changed between plugin 5.x and 6.x.

Output the inventory sorted by category, and add a "risk" column
(Low / Medium / High) based on whether the fix is mechanical or needs judgment.
```

---

## Phase 2 — Classify: scriptable vs. Copilot-assisted

Once you have the inventory back, sort findings into two buckets before doing anything else:

**Scriptable in Python (deterministic, safe to automate):**
- `javax.servlet` → `jakarta.servlet` import rewrites (straightforward find/replace, but verify no `javax.servlet` string literals or comments get corrupted — use an AST-aware or regex-with-word-boundary approach, not naive text replace)
- `pom.xml` / `build.gradle` version bumps for `struts2-core`, `struts2-spring-plugin`, `struts2-jquery-plugin*` artifacts
- Flagging (not fixing) every occurrence of the Struts 1 plugin / Sitemesh plugin for manual review
- Flagging every `@package.Class@FIELD` OGNL static-access pattern for manual review
- Generating the Phase 1 inventory itself (a script can grep/regex most of categories A–G faster and more reliably than an LLM pass)

**Needs Copilot / manual judgment (contextual):**
- Rewriting namespace-dependent action links to use exact namespaces
- Refactoring static-field OGNL access into helper classes or context injection
- Allowlisting specific POJO/DTO classes for OGNL if the app needs anything beyond the default allowlist
- Any code touching the removed Struts 1 / Sitemesh plugins
- Adjusting custom interceptors/validators/result types whose base class signatures changed
- Reviewing jQuery plugin tag usages that changed behavior between 5.x and 6.x

## Phase 3 — Ask Copilot to write the Python script for the deterministic passes

```
Write a Python script that performs the following transform passes across the
monorepo, one pass per function, with a dry-run mode that reports planned changes
before writing:

1. Replace javax.servlet, javax.servlet.http, javax.servlet.jsp imports with the
   jakarta.* equivalents in .java, .jsp, and .tag files. Skip string literals and
   comments containing "javax.servlet" that aren't actual import statements.
2. Bump struts2-core, struts2-spring-plugin version to 7.2.1 and
   struts2-jquery-plugin (and sibling grid/datatables/richtext/tree artifacts)
   to 6.1.x in every pom.xml / build.gradle found.
3. Grep for @[\w.]+@[A-Z_]+ patterns (OGNL static field access) in .jsp/.java/.ftl
   files and output a report file (not a code change) listing file, line, and match.
4. Grep for any reference to org.apache.struts2.sitemesh or the Struts1 plugin
   artifact/package names and output a report file listing file, line, and match.

Log every change made to a migration-log.csv (file, line, before, after, pass_name)
so changes are auditable and revertible.
```

## Phase 4 — Batched handoff (single component, avoid Copilot timeouts)

Since this is one component (not 50+ modules), the risk isn't module count — it's
Copilot trying to read too many files in one go and stalling/timing out. Avoid that
by never letting Copilot do the discovery reading itself; Python already did that
in Phase 1/3. Copilot only ever sees small, pre-scoped batches.

1. **Put the migration rules in `.github/copilot-instructions.md`** (the "Context"
   block from the top of this doc). This is picked up automatically per Copilot
   session so you don't re-paste it into every batch prompt.

2. **Split the inventory into per-category batch files**, e.g.:
   `batch_namespace_fixes.md`, `batch_ognl_static_access.md`,
   `batch_struts1_sitemesh_refs.md`, `batch_custom_interceptors.md`.
   Do the mechanical categories (imports, version bumps) entirely via the Python
   script from Phase 3 — never hand those to Copilot at all.

3. **Within each batch file, cap it at 10–15 findings.** For each finding include
   only: file path, line number, and a ±5 line snippet — not the whole file.
   Example row:
   ```
   File: src/main/java/com/foo/actions/OrderAction.java, line 142
   Snippet:
     140  String path = ${@com.foo.Constants@ORDER_PATH};
   Instruction: Static OGNL field access — copy ORDER_PATH into an accessible
   field on OrderAction or add it to the OGNL context. Confirm no other code
   depends on the old static reference before removing it.
   ```

4. **Feed one batch file per Copilot session/chat**, not the whole inventory at
   once. Ask Copilot to open only the specific files named in that batch.

5. **Checkpoint as you go.** After each batch, mark those inventory rows as
   `done` in the CSV (add a status column). If a session stalls or you have to
   restart, you resume from the first `pending` row instead of re-scanning
   anything.

6. **If a single file is very large** (e.g., a big JSP or a monolithic Action
   class with many findings), don't ask Copilot to fix the whole file in one
   shot either — batch the findings within that file too (e.g., 5 fixes per
   pass), so each Copilot turn stays small and fast.

This keeps every individual Copilot interaction small and bounded regardless of
how large the component's total file count is — the file count only affects how
many batches you generate, not how much any single Copilot call has to chew on.

---

**Note on versions:** double check `7.2.1` and `6.1.x` are still the latest published versions on Maven Central before kicking off the full run — patch releases move fast on both projects, and it's worth pinning the exact version you verified.
