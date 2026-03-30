# AngularJS → React 18 Migration Runbook
> **Tool:** GitHub Copilot Chat in IntelliJ IDEA  
> **Target:** React 18 (matching conventions from existing reference component)  
> **Approach:** Spec-first, phased migration — every prompt does ONE thing, touches ONE file

---

## Prerequisites

Before starting any migration, confirm the following:

- [ ] GitHub Copilot plugin installed and signed in (IntelliJ IDEA 2023.1+)
- [ ] Copilot Chat panel open (`View → Tool Windows → GitHub Copilot Chat`)
- [ ] AngularJS project open as the **active project** in IntelliJ
- [ ] `specs/` folder created at the root of your AngularJS project
- [ ] `react-reference/` snapshot folder created (see One-Time Setup below)

> **Do NOT open the full-stack React/Java project in IntelliJ.**  
> Copilot indexes the entire workspace including Java files and causes timeouts.  
> Use the `react-reference/` snapshot folder instead — it contains only what Copilot needs.

---

## Folder Structure

```
your-angularjs-project/
├── react-reference/                    ← ONE-TIME SETUP (see below)
│   ├── package.json                    ← copied from React project frontend folder
│   └── folder-structure.md            ← manually written folder tree
├── specs/
│   ├── API-Layer-Audit.md              ← Phase 0.5 (assembled from 5 sub-prompts)
│   ├── [ComponentName].spec.md         ← Phase 0  (assembled from 5 sub-prompts)
│   ├── [ComponentName].analysis.md     ← Phase 1  (assembled from 4 sub-prompts)
│   ├── [ComponentName].proposal.md     ← Phase 2  (assembled from 5 sub-prompts)
│   └── [ComponentName].migration.md    ← Phase 3-B (migration document)
├── src/                                ← migrated React files live here
```

---

## One-Time Setup — React Reference Snapshot

> **Do this once before starting Phase 0.5.**

### Step 1 — Create the snapshot folder
Inside your AngularJS project root, create: `react-reference/`

### Step 2 — Copy only `package.json`
Find the **frontend** `package.json` in your full-stack project. Common locations:
```
frontend/package.json
src/main/frontend/package.json
client/package.json
webapp/package.json
```
Copy it to `react-reference/package.json`. Do not copy `pom.xml` or any other file.

### Step 3 — Create `folder-structure.md`
Manually write a short Markdown file describing your React frontend folder layout:

```markdown
# React Frontend Folder Structure

src/
├── components/        ← shared/reusable UI components
│   └── [ComponentName]/
│       ├── index.jsx
│       └── [ComponentName].module.css
├── pages/             ← route-level page components
│   └── [PageName]/
│       └── index.jsx
├── hooks/             ← custom hooks
├── services/          ← API service files and axios instances
├── context/           ← React Context providers
├── utils/             ← pure utility functions
└── App.jsx
```

Adjust to match your actual project. Save as `react-reference/folder-structure.md`.

### Step 4 — Verify
`react-reference/` should contain exactly:
```
react-reference/
├── package.json
└── folder-structure.md
```

---

## HTML Templates — How They Fit

In AngularJS, every component is split across two files:
```
userController.js   ← behaviour, state, business logic
user.html           ← template, directives, bindings
```

Both files are half the same component. `ng-repeat`, `ng-if`, `ng-model`, `ng-click`
all live in the HTML — not the JS. The runbook handles this in two ways:

- **Phase 0.5** has a dedicated sub-prompt for `index.html` (app shell, routing, global layout)
- **Phases 0, 1, and 2** have specific sub-prompts where the HTML template is pasted
  inline alongside the JS file — marked with 🔶 **Paste HTML template inline**

> **Which sub-prompts need the HTML template pasted in:**
>
> | Sub-prompt | Needs HTML? | Why |
> |---|---|---|
> | 0-A Purpose & Type | ❌ No | JS only — HTML adds nothing here |
> | 0-B Inputs & Outputs | ❌ No | JS only |
> | 0-C State | ❌ No | State lives in JS only |
> | **0-D Business Rules** | ✅ **Yes** | Logic expressed in both JS and HTML |
> | **0-E UI Behaviour** | ✅ **Yes** | All ng-if / ng-repeat / ng-model are in HTML |
> | 1-A Complexity Rating | ❌ No | JS only |
> | **1-B Pattern Mapping** | ✅ **Yes** | HTML contains most Angular directives |
> | 1-C API Verification | ❌ No | Uses spec only |
> | **1-D Risks & Blockers** | ✅ **Yes** | Custom directives and template issues |
> | 2-A File Path | ❌ No | Uses spec only |
> | 2-B Dependencies | ❌ No | Uses pattern mapping only |
> | **2-C Component Hierarchy** | ✅ **Yes** | Template structure drives split decisions |
> | 2-D API Integration Plan | ❌ No | Uses audit only |
> | 2-E State & Data Flow | ❌ No | Uses spec only |

> **AppController / MarketFeeController (layout-level controllers):**  
> These are attached directly in `index.html` — use `index.html` as their HTML template
> in all 🔶 sub-prompts instead of a separate component template.  
> Also add this note to 2-C and 3-A-1 for these controllers:  
> *"This controller is layout-level, attached in index.html. Propose it as a React  
> Context provider or layout wrapper in App.jsx — not a page or route component."*

---

## Phase Overview

```
Phase 0.5 — API Layer Audit        5 prompts      — run ONCE for the whole app
Phase 0   — Spec Generation        5 prompts      — run per component
Phase 1   — Analysis & Gap Report  4 prompts + gate check — run per component
Phase 2   — Migration Proposal     5 prompts      — run per component
Phase 3   — Code Generation        per component
            3-A-1:  Imports & shell
            3-A-2:  State & hooks
            3-A-3a: Data fetching (useEffect)
            3-A-3b: Event handlers
            3-A-3c: Business logic functions
            3-A-4:  JSX & return        ← split by UI region if template is large
            3-A-5:  Assembly check
            3-A-5F: Fix errors          ← only if 3-A-5 finds issues (see decision tree)
            3-C-1:  State & communication review
            3-C-2:  Data fetching review
            3-C-3:  Business logic review
            3-C-4:  Template coverage (once per UI region — no full spec paste)
            3-C-5:  Final sign-off (paste 3-C-1 to 3-C-4 outputs — no file open)
            3-B:    Migration document
            3-D:    Sub-component generation ← only if proposal Section 3 lists sub-components
Phase 4   — Local Testing          one-time setup + per component checklist
```

> **Golden rule:** One prompt = one task = one file open.  
> Save each output before running the next prompt.  
>
> **On blockers:** After Phase 1, the only manual check needed is whether any
> unknown third-party library equivalents were flagged. Everything else is
> caught and fixed automatically by Phase 3-C-1 through 3-C-4. No React knowledge required.

---

## Re-run Reference Guide

Use this table whenever a step fails or produces incomplete output. It shows exactly which prompts to re-run and what to replace — no need to restart from scratch.

| Situation | Re-run these prompts | Replace / update |
|---|---|---|
| Ran Phases 0–2 on JS only (no HTML) | 0-D, 0-E, 1-B, 1-D, 2-C | Sections 4+5 of spec, Sections 2+4 of analysis, Section 3 of proposal |
| Spec has wrong business rules | 0-D only | Section 4 of spec |
| Spec has wrong UI behaviour | 0-E only | Section 5 of spec |
| Pattern mapping missed HTML patterns | 1-B only | Section 2 of analysis |
| Blockers missing HTML issues | 1-D only | Section 4 of analysis |
| Component hierarchy wrong | 2-C only | Section 3 of proposal |
| 3-A-5 finds trivial errors (typo, missing import, brace) | None — fix manually | Edit file directly |
| 3-A-5 finds logic gap (wrong state reference, bad useEffect) | 3-A-5F targeted fix prompt | Edit specific lines |
| 3-A-5 finds whole section missing or wrong | Re-run the relevant 3-A sub-prompt | Replace that section in the file |
| 3-A-3 times out | 3-A-3a, 3-A-3b, 3-A-3c separately | Replace 3-A-3 output |
| 3-A-4 times out | One prompt per JSX region | Replace 3-A-4 output |
| Sub-components missing after 3-B | 3-D-2, 3-D-3a/3b/3c/3d, 3-D-4, 3-D-5 for each missing one | Create new files, update parent imports |
| 3-C-1 flags shared state issue | 3-C-1 targeted fix | Edit specific lines in component |
| 3-C-2 flags missing error handling | 3-C-2 targeted fix | Edit specific lines in component |
| 3-C-3 flags missing business logic | 3-A-3c re-run for that rule | Replace business logic section |
| 3-C-4 flags missing template coverage | 3-A-4 for the affected region only | Replace that JSX region |
| 3-C-4 times out | Run once per UI region — paste only that region's spec items | Run 4 times total |
| 3-C-5 times out | Already fixed — 3-C-5 reads no file, only collected outputs | Re-paste 3-C-1 to 3-C-4 outputs |

---

## If You Already Ran Phases 0–2 on JS Files Only

You do not need to start over. Run only these targeted repairs per component:

| Re-run | Replace in existing file |
|---|---|
| 0-D (with HTML pasted) | Section 4 of `[ComponentName].spec.md` |
| 0-E (with HTML pasted) | Section 5 of `[ComponentName].spec.md` |
| 1-B (with HTML pasted) | Section 2 of `[ComponentName].analysis.md` |
| 1-D (with HTML pasted) | Section 4 of `[ComponentName].analysis.md` |
| 2-C (with HTML pasted) | Section 3 of `[ComponentName].proposal.md` |

Everything else (0-A, 0-B, 0-C, 1-A, 1-C, 2-A, 2-B, 2-D, 2-E) is unaffected by HTML.

---

## Phase 0.5 — API Layer Audit
> **Frequency:** Once for the whole app  
> **Rule:** Open only the file mentioned in each sub-prompt. Start a new chat session for each prompt.

---

### 0.5-A — Interceptors
> **Open:** `app.js` or your main Angular module file

```
You are a backend integration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Find every instance of $httpProvider.interceptors.
For each interceptor found document:
- What it does (auth token injection, error handling, request transform, etc.)
- Exact headers or tokens it adds or reads
- Any redirect or retry logic

If none found, write: "No interceptors detected"

Output Markdown only. No preamble.
```

**Save output → paste as Section 1 of `specs/API-Layer-Audit.md`**

---

### 0.5-B — $http Calls
> **Open:** One controller or service file at a time  
> **Repeat for every file in your app — one file per prompt run**

```
You are a backend integration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

List every unique $http call in this file:
| Method | Endpoint | Called From | Request Payload | Response Shape | Error Handling |

If no $http calls exist, write: "No $http calls in this file"

Output the table only. No preamble.
```

**Save output → combine all tables as Section 2 of `specs/API-Layer-Audit.md`**

---

### 0.5-C — Auth & Error Handling
> **Open:** Your auth service file or main Angular module

```
You are a backend integration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Answer these four questions in bullet points only. No prose.

1. Auth mechanism: How is the user authenticated? Where is the token stored?
   How is it attached to requests? What happens on 401 or session expiry?

2. Shared API services: Which services wrap $http and inject into multiple
   controllers? Which controllers depend on each?

3. Error handling: Is it global (interceptor) or per-call? What happens on
   error (toast, redirect, silent fail)? Any retry logic?

4. Loading state: How does the app signal loading to the UI?

Output Markdown only. No preamble.
```

**Save output → paste as Sections 3–6 of `specs/API-Layer-Audit.md`**

---

### 0.5-D — React Equivalent Proposal
> **Open:** `react-reference/package.json` only  
> **Before running:** paste your Sections 1–6 output into the prompt below

```
You are a React 18 architect.
Read only #file:react-reference/package.json.
Do not read any other files. Do not scan the workspace.

Here is the API audit collected from the AngularJS app:
[PASTE SECTIONS 1-6 OUTPUT HERE]

Based only on the dependencies in package.json, propose:
1. Data-fetching approach to adopt (match what is already in package.json)
2. How to replicate interceptor behavior in React
3. Where auth token logic should live
4. Whether a central API service file is needed and what it exports
5. How loading and error state will be handled consistently

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 7 of `specs/API-Layer-Audit.md`**

---

### 0.5-E — index.html Audit
> **Open:** `index.html`

```
You are a frontend analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Document the following from index.html:

1. App bootstrap
   - How is the Angular app initialised? (ng-app directive and where it sits)

2. Layout-level controllers
   - List every ng-controller found directly in index.html
   - For each: where in the DOM it is attached, what scope it covers
   - Note explicitly: these are layout controllers, not route controllers

3. Layout structure
   - What is the top-level HTML structure?
   - Are there layout elements (header, nav, sidebar, footer) that wrap
     the whole app, outside of the routing placeholder?

4. Routing placeholder
   - Where is ng-view or ui-view placed in the document?
   - Is there a default route or redirect defined here?

5. Global scripts and styles
   - List every script tag and stylesheet link
   - Flag any third-party libraries loaded via CDN

6. Migration notes
   - What parts of index.html must exist in the React app?
     (root div, router setup, global styles, layout wrapper components, etc.)

Output Markdown only. No preamble.
```

**Save output → paste as Section 8 of `specs/API-Layer-Audit.md`**

---

### 0.5 — Assemble the Audit File

Combine all five outputs into `specs/API-Layer-Audit.md`:

```markdown
# API Layer Audit

## Section 1 — HTTP Interceptors
[0.5-A output]

## Section 2 — All Backend Calls
[0.5-B output — all tables combined]

## Section 3 — Auth Mechanism
[0.5-C output — question 1]

## Section 4 — Shared API Services
[0.5-C output — question 2]

## Section 5 — Error Handling Strategy
[0.5-C output — question 3]

## Section 6 — Loading State Management
[0.5-C output — question 4]

## Section 7 — Proposed React Equivalent
[0.5-D output]

## Section 8 — index.html Audit
[0.5-E output]
```

> **Review before proceeding.** This is the API and app-shell contract for the entire migration.

---

## Phase 0 — Spec Generation
> **Frequency:** Per component file  
> **Rule:** Open only the AngularJS JS file. For sub-prompts marked 🔶, paste the HTML template inline.  
> New chat session per prompt.

---

### 0-A — Purpose & Type
> **Open:** The AngularJS component JS file (e.g. `userController.js`)

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

For each controller, service, directive, or filter in this file, output:

## Component Name: [name]
**Type:** [Controller / Service / Directive / Filter]
**Purpose:** [Plain English — what does this do and why does it exist]
**Dependencies:** [List every injected dependency by name]

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 1 of `specs/[ComponentName].spec.md`**

---

### 0-B — Inputs & Outputs
> **Open:** Same AngularJS JS file

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

For each controller, service, directive, or filter in this file, output:

## [Component Name] — Inputs & Outputs

### Inputs
- Every route param, query param, injected dependency, or passed argument
- Include inferred type where possible

### Outputs
- Every event emitted, return value, or data exposed to the view

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 2 of `specs/[ComponentName].spec.md`**

---

### 0-C — State
> **Open:** Same AngularJS JS file

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

For each controller, service, directive, or filter in this file, output:

## [Component Name] — State

List every variable stored on $scope or the service object:
| Variable | Type | Initial Value | What triggers a change |

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 3 of `specs/[ComponentName].spec.md`**

---

### 0-D — Business Rules & API Calls 🔶 Paste HTML template inline
> **Open:** The AngularJS JS file  
> **Before running:** paste the full contents of the corresponding HTML template into the prompt  
> **AppController / MarketFeeController:** paste `index.html` as the template

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Here is the HTML template for this component:
[PASTE FULL CONTENTS OF [ComponentName].html HERE]

For each controller, service, directive, or filter in this file, output:

## [Component Name] — Business Rules & API Calls

### API Calls
List every backend call made, the condition that triggers it, and what
the result is used for. Do not describe $http syntax — describe the intent.

### Business Rules
List every conditional check, validation, and calculation in plain English.
Include logic expressed in BOTH the JS file and the HTML template above.
Focus on WHAT the rule enforces and WHY, not HOW Angular implements it.

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 4 of `specs/[ComponentName].spec.md`**

---

### 0-E — UI Behaviour 🔶 Paste HTML template inline
> **Open:** The AngularJS JS file  
> **Before running:** paste the full contents of the corresponding HTML template into the prompt  
> **AppController / MarketFeeController:** paste `index.html` as the template

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Here is the HTML template for this component:
[PASTE FULL CONTENTS OF [ComponentName].html HERE]

For each controller, service, directive, or filter in this file, output:

## [Component Name] — UI Behaviour

### Template Structure
Describe the top-level layout of the template in plain English
(e.g. "A form with three sections — personal details, address, and submit button").

### Show / Hide Rules
List every ng-if, ng-show, ng-hide condition from the template in plain English.

### List Rendering
List every ng-repeat: what collection it iterates, what each item renders,
and any filters or ordering applied.

### Form Bindings
List every ng-model binding — what field it represents and what it binds to.

### Dynamic Styles
List every ng-class condition and what CSS class it applies.

### User Interactions
List every ng-click, ng-change, ng-submit handler and what it triggers.

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 5 of `specs/[ComponentName].spec.md`**

---

### 0 — Assemble the Spec File

Combine all five outputs into `specs/[ComponentName].spec.md`:

```markdown
# Spec: [ComponentName]

## Section 1 — Purpose & Type
[0-A output]

## Section 2 — Inputs & Outputs
[0-B output]

## Section 3 — State
[0-C output]

## Section 4 — Business Rules & API Calls
[0-D output — includes HTML template logic]

## Section 5 — UI Behaviour
[0-E output — includes HTML template behaviour]
```

> **Review carefully before proceeding.**  
> Correct any misunderstood business rules — all subsequent phases trust this spec.

---

## Phase 1 — Analysis & Gap Report
> **Frequency:** Per component  
> **Rule:** Open only the files mentioned per sub-prompt. For sub-prompts marked 🔶, paste HTML inline.  
> New chat session per prompt.

---

### 1-A — Complexity Rating
> **Open:** The AngularJS JS file

```
You are a migration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Rate this component: Low / Medium / High complexity for migrating to React 18.
Justify in exactly one sentence.

Output Markdown only. No preamble.
```

**Save output → paste as Section 1 of `specs/[ComponentName].analysis.md`**

---

### 1-B — Pattern Mapping 🔶 Paste HTML template inline
> **Open:** The AngularJS JS file  
> **Before running:** paste the full contents of the corresponding HTML template into the prompt  
> **AppController / MarketFeeController:** paste `index.html` as the template

```
You are a migration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Here is the HTML template for this component:
[PASTE FULL CONTENTS OF [ComponentName].html HERE]

List every AngularJS pattern found across BOTH the JS file and the HTML template,
and its React 18 equivalent:
| AngularJS Pattern Found | Location (JS / HTML) | React 18 Equivalent | Notes |

Use these mappings:
- Controller → Functional component + hooks
- $scope / two-way binding → useState / useReducer
- Service / Factory → Custom hook or Context provider
- Directive → Reusable functional component
- $http → Per API-Layer-Audit proposal
- ui-router / ngRoute → React Router v6
- $rootScope events → Context API or Zustand
- Filters → Pure utility functions
- ng-repeat → Array.map()
- ng-if / ng-show / ng-hide → Conditional rendering
- ng-model → Controlled input with useState
- ng-class → Dynamic className with clsx
- Custom directives in template → Reusable React components

Output the table only. No preamble.
```

**Save output → paste as Section 2 of `specs/[ComponentName].analysis.md`**

---

### 1-C — API Call Verification
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the API-Layer-Audit Section 2 table into the prompt

```
You are a migration analyst. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the master API-Layer-Audit backend calls table:
[PASTE API-LAYER-AUDIT SECTION 2 TABLE HERE]

From the spec in #file, list every backend call this component makes.
For each call confirm whether it appears in the audit table above.
Flag any call NOT present in the audit table with: ⚠️ NOT IN AUDIT

Output Markdown only. No preamble.
```

**Save output → paste as Section 3 of `specs/[ComponentName].analysis.md`**

---

### 1-D — Risks & Blockers 🔶 Paste HTML template inline
> **Open:** The AngularJS JS file  
> **Before running:** paste the full contents of the corresponding HTML template into the prompt  
> **AppController / MarketFeeController:** paste `index.html` as the template

```
You are a migration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Here is the HTML template for this component:
[PASTE FULL CONTENTS OF [ComponentName].html HERE]

List every pattern across BOTH the JS file and the HTML template that cannot
be automatically converted to React 18 and will need attention. For each, describe:
- What the pattern is and where it was found (JS or HTML)
- Why it cannot be auto-converted
- What the developer must decide or do manually

If no blockers exist, write: "No blockers identified"

Output Markdown only. No preamble.
```

**Save output → paste as Section 4 of `specs/[ComponentName].analysis.md`**

---

### 1 — Assemble the Analysis File

Combine all four outputs into `specs/[ComponentName].analysis.md`:

```markdown
# Analysis: [ComponentName]

## Section 1 — Complexity Rating
[1-A output]

## Section 2 — Pattern Mapping
[1-B output — includes HTML patterns]

## Section 3 — API Call Verification
[1-C output]

## Section 4 — Risks & Blockers
[1-D output — includes HTML blockers]
```

### ✅ After Assembling — One Gate Check Only

Read Section 4 and answer this single question:

> **Does any blocker mention a third-party AngularJS library with no known React equivalent?**  
> (e.g. `ui-grid`, `ng-file-upload`, `angular-material`, `angular-chart.js`)

**If YES:** Find the React equivalent library yourself, add it to `react-reference/package.json`, then proceed to Phase 2.

**If NO:** Proceed to Phase 2 immediately. All other blockers are handled automatically by Phase 3-C — no action needed now.

---

## Phase 2 — Migration Proposal
> **Frequency:** Per component  
> **Rule:** Open only the files mentioned per sub-prompt. For sub-prompts marked 🔶, paste HTML inline.  
> New chat session per prompt.

---

### 2-A — Target File Path
> **Open:** `react-reference/folder-structure.md`  
> **Before running:** paste the component name and type from the spec

```
You are a React 18 architect. Read #file:react-reference/folder-structure.md only.
Do not read any other files. Do not scan the workspace.

Component being migrated: [PASTE COMPONENT NAME AND TYPE FROM SPEC HERE]
(e.g. "UserController — Controller")

Based strictly on the folder conventions in folder-structure.md, propose:
- The exact file path for the migrated React component
- The exact file path for any custom hook that should be extracted
- The file naming convention to use

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 1 of `specs/[ComponentName].proposal.md`**

---

### 2-B — Dependencies
> **Open:** `react-reference/package.json`  
> **Before running:** paste the pattern mapping table from `[ComponentName].analysis.md` Section 2

```
You are a React 18 architect. Read #file:react-reference/package.json only.
Do not read any other files. Do not scan the workspace.

Here is the pattern mapping for this component:
[PASTE ANALYSIS SECTION 2 PATTERN MAPPING TABLE HERE]

Based only on what is already in package.json, produce a dependency table:
| Package | Version | Replaces | dep / devDep |

- Use exact versions from package.json
- Do not add any package not already in package.json unless it is
  absolutely required and has no equivalent already present
- Flag any new additions with: ⚠️ NEW DEPENDENCY

Output the table only. No preamble.
```

**Save output → paste as Section 2 of `specs/[ComponentName].proposal.md`**

---

### 2-C — Component Hierarchy 🔶 Paste HTML template inline
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the full contents of the corresponding HTML template into the prompt  
> **AppController / MarketFeeController:** paste `index.html` and add the layout-level note

```
You are a React 18 architect. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the HTML template for this component:
[PASTE FULL CONTENTS OF [ComponentName].html HERE]

[FOR AppController / MarketFeeController ONLY — add this line:]
Note: This controller is layout-level, attached in index.html. Propose it as a
React Context provider or layout wrapper in App.jsx — not a page or route component.

Using the UI Behaviour section of the spec AND the HTML template above,
propose a component hierarchy tree. Show which parts should be split into
separate React components, driven by the actual template structure.
Keep it as a simple indented tree with one-line descriptions.

If no split is needed, write: "Single component — no split required"

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 3 of `specs/[ComponentName].proposal.md`**

---

### 2-D — API Integration Plan
> **Open:** `specs/API-Layer-Audit.md`  
> **Before running:** paste the component's API calls from spec Section 4

```
You are a React 18 architect. Read #file:specs/API-Layer-Audit.md only.
Do not read any other files. Do not scan the workspace.

This component makes these API calls:
[PASTE SPEC SECTION 4 API CALLS HERE]

Based on the React Equivalent Proposal in API-Layer-Audit Section 7, answer:
1. Should these calls live in the component, a custom hook, or a shared service?
2. Where exactly should the custom hook or service file live?
3. How will loading state be managed and surfaced in the UI?
4. How will errors be caught and surfaced in the UI?

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 4 of `specs/[ComponentName].proposal.md`**

---

### 2-E — State & Data Flow Plan
> **Open:** `specs/[ComponentName].spec.md`

```
You are a React 18 architect. Read #file only.
Do not read any other files. Do not scan the workspace.

Based on the State section of this spec, describe in plain English:
1. Which state variables become useState hooks
2. Which state variables become useReducer (if any are complex/related)
3. Whether any state needs to be lifted to a Context provider
4. Initial values and types for each state variable

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 5 of `specs/[ComponentName].proposal.md`**

---

### 2 — Assemble the Proposal File

Combine all five outputs into `specs/[ComponentName].proposal.md`:

```markdown
# Migration Proposal: [ComponentName]

## Section 1 — Target File Path
[2-A output]

## Section 2 — Dependencies
[2-B output]

## Section 3 — Component Hierarchy
[2-C output — informed by HTML template structure]

## Section 4 — API Integration Plan
[2-D output]

## Section 5 — State & Data Flow Plan
[2-E output]
```

> **Review all five sections before proceeding.**  
> Only move to Phase 3 when you are satisfied with the full proposal.

---

## Phase 3 — Code Generation & Migration Document
> **Frequency:** Per component — only after Phase 2 is confirmed  
> **Order:** 3-A-1 → 3-A-2 → 3-A-3a → 3-A-3b → 3-A-3c → 3-A-4 → 3-A-5 → 3-C → 3-B  
> **Why 3-A is split:** Generating a complete React component in one prompt causes
> timeouts — especially for layout-level controllers like AppController. Each sub-prompt
> generates one focused section, keeping responses small and resumable.

---

### 3-A-1 — Imports & Component Shell
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste proposal Sections 1 and 2 inline  
> **AppController / MarketFeeController:** add the layout-level note

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the migration proposal — Sections 1 and 2 only:
[PASTE proposal.md SECTIONS 1 AND 2 HERE]

[FOR AppController / MarketFeeController ONLY — add this line:]
Note: This is a layout-level controller. Generate it as a React Context provider
or layout wrapper component for App.jsx — not a page or route component.

Generate ONLY the top of the React component file:
1. The comment block header:
   // Migrated from: [original AngularJS JS file path]
   // Template: [original HTML template file path]
   // Spec: specs/[ComponentName].spec.md
   // Migration date: [today's date]
   // AngularJS pattern replaced: [Controller / Service / Directive]

2. All import statements needed for this component
   (based on dependencies in proposal Section 2 only)

3. Any constants or config values defined outside the component function

4. The component function signature and opening brace only:
   export default function [ComponentName]() {

Do NOT write any hooks, JSX, or logic yet. Stop at the opening brace.

Output code only. No preamble.
```

**Save output → create `src/[path]/[ComponentName].jsx` with this content**

---

### 3-A-2 — State & Hooks
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste spec Section 3 and proposal Section 5 inline

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the component state from the spec (Section 3):
[PASTE spec.md SECTION 3 HERE]

Here is the state & data flow plan from the proposal (Section 5):
[PASTE proposal.md SECTION 5 HERE]

Generate ONLY the hooks section inside the component function:
1. All useState declarations with correct initial values and types
2. All useReducer declarations if identified in the state plan
3. All useRef declarations
4. All useContext calls if Context is being consumed
5. Any custom hook calls (e.g. useFetchMarketFees())

Do NOT write useEffect, handlers, or JSX yet.
Assume the component function opening brace already exists above this code.
Do NOT write the closing brace.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[ComponentName].jsx` after the opening brace**

---

### 3-A-3a — Data Fetching (useEffect)
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste spec Section 4 API Calls part and proposal Section 4 and API-Layer-Audit Section 7 inline

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the API Calls section from the spec (Section 4 — API Calls part only):
[PASTE spec.md SECTION 4 API CALLS PART ONLY HERE]

Here is the API integration plan from the proposal (Section 4):
[PASTE proposal.md SECTION 4 HERE]

Here is the API Layer Audit React proposal (Section 7):
[PASTE API-Layer-Audit.md SECTION 7 HERE]

Generate ONLY the useEffect hooks inside the component function,
continuing after the useState/useRef hooks already written above:
1. One useEffect per distinct data fetch identified in the spec
2. Each useEffect must:
   - Call the correct API endpoint per the audit
   - Set loading state to true before the call, false after
   - Set data state on success
   - Set error state on failure
   - Include correct dependency array

Do NOT write event handlers, business logic functions, or JSX yet.
Assume hooks section already exists above. Do NOT write the closing brace.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[ComponentName].jsx` after the hooks section**

---

### 3-A-3b — Event Handlers
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste spec Section 5 User Interactions part only

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the User Interactions section from the spec (Section 5 — User Interactions part only):
[PASTE spec.md SECTION 5 USER INTERACTIONS PART ONLY HERE]

Generate ONLY the event handler functions inside the component function,
continuing after the useEffect hooks already written above:
1. One function per user interaction identified in the spec
2. Name every handler with the handle* or on* prefix
3. Each handler must:
   - Perform the action described in the spec
   - Update the relevant state variables
   - Make any API calls described for that interaction
4. Do NOT inline logic — keep each handler as a named function

Do NOT write business logic helpers or JSX yet.
Assume hooks and useEffects already exist above. Do NOT write the closing brace.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[ComponentName].jsx` after the useEffect section**

---

### 3-A-3c — Business Logic Functions
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste spec Section 4 Business Rules part only

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the Business Rules section from the spec (Section 4 — Business Rules part only):
[PASTE spec.md SECTION 4 BUSINESS RULES PART ONLY HERE]

Generate ONLY the business logic helper functions inside the component function,
continuing after the event handlers already written above:
1. One function per distinct business rule, validation, or calculation in the spec
2. Each function must:
   - Implement the rule exactly as described in the spec — do not simplify
   - Accept the minimum parameters needed
   - Return a value or update state as described
3. Do not duplicate logic already handled in event handlers above

Do NOT write JSX yet.
Assume hooks, useEffects, and handlers already exist above. Do NOT write the closing brace.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[ComponentName].jsx` after the event handlers section**

---

### 3-A-4 — JSX & Return
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste spec Section 5 and proposal Section 3 inline

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the UI behaviour from the spec (Section 5):
[PASTE spec.md SECTION 5 HERE]

Here is the component hierarchy from the proposal (Section 3):
[PASTE proposal.md SECTION 3 HERE]

Generate ONLY the return statement and closing brace of the component,
continuing after the handlers and logic already written above:
1. The return( opening
2. Complete JSX implementing every item in the UI Behaviour spec:
   - Every show/hide rule as conditional rendering
   - Every ng-repeat as Array.map()
   - Every ng-model as controlled input with onChange + useState value
   - Every ng-click / ng-submit as onClick / onSubmit handler
   - Every ng-class as dynamic className
3. The closing ) of return
4. The closing } of the component function

Assume all state, hooks, and handlers already exist above this code.
Reference them by the exact variable and function names from steps 3-A-2 and 3-A-3.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[ComponentName].jsx` after the handlers section**

> **If 3-A-4 also times out — large templates:**  
> Split the JSX by UI section. Run one prompt per major block (form, table, modal, nav),
> pasting only the relevant part of spec Section 5 each time:
>
> ```
> Generate ONLY the JSX for the [form / table / modal / nav] section.
> The component structure is:
> [PASTE ONLY THE RELEVANT PART OF spec.md SECTION 5 HERE]
> Assume all state and handlers already exist above.
> Do not write the closing brace or return closing parenthesis.
> Output code only. No preamble.
> ```
>
> Paste each JSX block inside the `return (` statement manually, one block at a time.

---

### 3-A-5 — Assembly Check
> **Open:** `src/[path]/[ComponentName].jsx` — the file you have been building through 3-A-1 to 3-A-4  
> **When to run:** After all parts have been appended and all JSX region slots have been filled  
> **What it checks:** Seams between the four generated sections — name mismatches, missing imports, unclosed brackets, duplicate declarations

```
You are a React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

This file was assembled in parts. Check for these specific issues:

1. Missing imports — are all hooks, components, and utilities imported?
2. Undefined variables — does the JSX reference any variable not declared
   in the hooks or handlers above it?
3. Unclosed brackets — are all { } ( ) correctly matched?
4. Duplicate declarations — were any variables declared more than once?
5. Name mismatches — does the JSX use the exact same names as the
   declarations above?

For each issue found:
- Location: [line area or function name]
- Problem: [what is wrong]
- Fix: [exact corrected line]

If no issues found, write: "Assembly looks correct"

Output Markdown only. No preamble.
```

**Apply any fixes to the component file, then proceed to 3-C-1.**

---

### 3-A-5F — Fix Assembly Errors
> **Only run this if 3-A-5 found issues**  
> **Decision tree — choose the right fix type before running any prompt:**

```
3-A-5 found errors
│
├── Trivial error (missing import, typo, wrong variable name, missing brace)
│   └── Fix manually in the file — faster than a prompt, no risk of timeout
│       Then re-run 3-A-5 to confirm
│
├── Logic gap (handler references undeclared state, wrong useEffect dependency)
│   └── Run the targeted fix prompt below — ONE error per prompt run
│       Then re-run 3-A-5 to confirm
│
└── Whole section wrong or missing
    └── Re-run the relevant 3-A sub-prompt (3-A-2, 3-A-3a, 3-A-3b, 3-A-3c, or 3-A-4)
        Replace only that section in the file
        Then re-run 3-A-5 to confirm
```

**Targeted fix prompt (for logic gaps only — run once per error):**

> **Open:** `src/[path]/[ComponentName].jsx`

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Fix ONLY this specific issue in the file:

Location: [PASTE LOCATION FROM 3-A-5 OUTPUT]
Problem:  [PASTE PROBLEM FROM 3-A-5 OUTPUT]
Suggested fix: [PASTE FIX FROM 3-A-5 OUTPUT]

Output ONLY the corrected lines — not the whole file.
Show 2–3 lines before and after the fix for context.
Do not change anything else in the file.

Output code only. No preamble.
```

Apply the output manually to the correct location in the file.  
Re-run 3-A-5 after all errors are resolved before proceeding to 3-C-1.

---

### 3-C — Self-Review & Fix
> **Open:** `src/[path]/[ComponentName].jsx` for all sub-prompts  
> **Why split:** The component file is large, and pasting the full spec plus blockers into one prompt pushes over the context limit. Each sub-prompt checks one concern only and pastes only the spec section relevant to that concern.  
> **New chat session for each sub-prompt.**

---

#### 3-C-1 — State & Communication Review
> **Open:** `src/[path]/[ComponentName].jsx`  
> **Before running:** paste analysis Section 4 (blockers) inline only — no spec needed here

```
You are a senior React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here are the blockers identified during analysis:
[PASTE specs/[ComponentName].analysis.md SECTION 4 HERE]

Review the component in #file and check for ONLY these two issues:

1. Shared state risk
   Is any state that was shared across controllers now isolated inside
   a single component? If yes, flag it — it should be in a Context
   provider or Zustand store instead.

2. Cross-component communication
   Were any $rootScope broadcast/on patterns converted to prop callbacks?
   If yes, flag them — they likely need Context API instead.

For each issue found output:
- Location: [function name or line area]
- Problem: [plain English explanation]
- Fix: [exact corrected code snippet]

If no issues found, write: "No state or communication issues found"

Output Markdown only. No preamble.
```

**Apply any fixes to the component file.**

---

#### 3-C-2 — Data Fetching Review
> **Open:** `src/[path]/[ComponentName].jsx`  
> **Before running:** paste spec Section 4 (API Calls part only) inline

```
You are a senior React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here are the API calls this component should make (from the spec):
[PASTE spec.md SECTION 4 API CALLS PART ONLY HERE]

Review the component in #file and check for ONLY these two issues:

1. Data fetching timing
   Were any route resolve blocks converted to useEffect?
   If yes, flag whether this causes a render-before-data problem
   where the component renders with no data before the fetch completes.

2. Missing error handling
   For every API call in the spec above — is the error caught and
   surfaced to the user in the UI?
   Flag exactly where error handling is absent.

For each issue found output:
- Location: [function name or line area]
- Problem: [plain English explanation]
- Fix: [exact corrected code snippet]

If no issues found, write: "No data fetching issues found"

Output Markdown only. No preamble.
```

**Apply any fixes to the component file.**

---

#### 3-C-3 — Business Logic Review
> **Open:** `src/[path]/[ComponentName].jsx`  
> **Before running:** paste spec Section 4 (Business Rules part only) inline

```
You are a senior React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here are the business rules this component must implement (from the spec):
[PASTE spec.md SECTION 4 BUSINESS RULES PART ONLY HERE]

Review the component in #file and check for ONLY this issue:

Business logic assumptions
For each business rule listed above, confirm it is implemented in the component.
Flag every place where the component makes an assumption, simplifies a rule,
or omits a rule that is explicitly in the spec above.

For each issue found output:
- Location: [function name or line area]
- Problem: [which rule is missing or wrong]
- Fix: [exact corrected code snippet]

If no issues found, write: "No business logic issues found"

Output Markdown only. No preamble.
```

**Apply any fixes to the component file.**

---

#### 3-C-4 — Template Coverage Review
> **Open:** `src/[path]/[ComponentName].jsx`  
> **Before running:** paste **only the spec Section 5 items for one UI region at a time**  
> **Run once per visual region** — same regions as your 3-A-4 JSX split (Header, Filter Bar, Rules Grid, Fee Details Form)  
> **Why split by region:** Pasting the entire Section 5 alongside a large component file exceeds the context limit

```
You are a senior React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the UI behaviour for the [REGION NAME] region only (from the spec):
[PASTE ONLY THE [REGION NAME] ITEMS FROM spec.md SECTION 5 HERE]

Review the component in #file and check for ONLY this issue in the [REGION NAME] JSX:

Template coverage for [REGION NAME]
For each item in the spec above, confirm it is implemented in the JSX:
- Every show/hide rule implemented as conditional rendering
- Every list rendered with Array.map() and a key prop
- Every form field implemented as a controlled input
- Every user interaction wired to the correct handler
- Every dynamic style implemented with clsx or equivalent

Flag any item from the spec that is missing, incomplete, or implemented
differently from what the spec describes.

For each issue found output:
- Location: [JSX line area or section]
- Problem: [which spec item is missing or wrong]
- Fix: [exact corrected JSX snippet]

If no issues found, write: "No template coverage issues in [REGION NAME]"

Output Markdown only. No preamble.
```

**Run this prompt four times** — once for each region:
- Header region → paste only header items from Section 5
- Filter Bar region → paste only filter bar items from Section 5
- Rules Grid region → paste only rules grid items from Section 5
- Fee Details Form region → paste only fee details form items from Section 5

**Apply any fixes after each run before moving to the next region.**  
Collect all four outputs to paste into 3-C-5.

---

#### 3-C-5 — Final Sign-Off
> **Open:** Nothing — no file reference needed  
> **Before running:** paste the outputs from 3-C-1, 3-C-2, 3-C-3, and 3-C-4 inline  
> **Why no file:** The component file is large enough to cause a timeout on its own. This step works from the review outputs already collected — not the file itself.

```
You are a senior React 18 code reviewer.
Do not open or read any files. Do not scan the workspace.

Here are the results of the four review checks already completed:

3-C-1 State & Communication output:
[PASTE 3-C-1 OUTPUT HERE]

3-C-2 Data Fetching output:
[PASTE 3-C-2 OUTPUT HERE]

3-C-3 Business Logic output:
[PASTE 3-C-3 OUTPUT HERE]

3-C-4 Template Coverage output:
[PASTE 3-C-4 OUTPUT HERE]

Based on these four review outputs only, produce a final sign-off summary:

## 3-C Review Summary — [ComponentName]

### Issues Found & Fixed
List every issue that was flagged across all four checks and confirmed fixed.
| Check | Issue | Status |

### Issues Still Open
List any issue that was flagged but could not be auto-fixed and needs
manual attention.
| Check | Issue | Action needed |

### Verdict
One of:
- "Component is ready — proceed to 3-B" (no open issues)
- "Open issues remain — resolve before proceeding to 3-B" (list them)

Output Markdown only. No preamble.
```

**Save output → `specs/[ComponentName].review-summary.md`**  
If verdict is "Component is ready" — proceed to 3-B.  
If open issues remain — resolve them first, then re-run only the relevant 3-C check.

---

### 3-B — Generate the Migration Document
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the full analysis and proposal inline  
> **Important:** Run only after 3-C-5 final sign-off is clean

```
You are a technical writer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the analysis report:
[PASTE FULL specs/[ComponentName].analysis.md CONTENT HERE]

Here is the migration proposal:
[PASTE FULL specs/[ComponentName].proposal.md CONTENT HERE]

Generate a migration document in Markdown:

# Migration Document: [ComponentName] — AngularJS → React 18

## Overview
Source JS file, HTML template file, component type, complexity rating, migration date.

## What Changed
Bullet list of every AngularJS construct (from both JS and HTML) and its React equivalent.

## Template Migration
How the HTML template was converted to JSX — key structural decisions made.

## API & Backend Changes
How $http calls were migrated, auth handling, loading and error state approach.

## New File Location
Where the migrated file lives and why.

## Dependency Changes
| Removed (AngularJS) | Added (React) | Reason |

## Assumptions Made
Every assumption from the code generation step.

## Issues Found & Fixed in Review
Every issue flagged by the self-review step and how it was resolved.

## Manual Steps Required
Any remaining items that could not be handled automatically.

## Testing Recommendations
What to validate to confirm the migrated component matches the spec.
```

**Save output → `specs/[ComponentName].migration.md`**

---

### 3-D — Sub-Component Generation
> **When to run:** After 3-B — only if `specs/[ComponentName].proposal.md` Section 3 lists sub-components that do not yet exist as files in `src/`  
> **How to check:** Open proposal Section 3 and compare every item in the hierarchy tree against your `src/` folder. Any listed component without a matching file needs 3-D.

---

#### 3-D-1 — Identify Missing Sub-Components

Open `specs/[ComponentName].proposal.md` Section 3 and list every sub-component that does not exist yet:

```
Example hierarchy from proposal Section 3:

MarketFeeController
├── MarketFeeHeader     ← check src/ — exists? ✅ / missing? ❌
├── FilterBar           ← check src/ — exists? ✅ / missing? ❌
├── RulesGrid           ← check src/ — exists? ✅ / missing? ❌
│   └── RuleRow         ← check src/ — exists? ✅ / missing? ❌
└── FeeDetailsForm      ← check src/ — exists? ✅ / missing? ❌
```

Run the steps below for each missing sub-component in order — parent before child.

---

#### 3-D-2 — Extract Mini-Spec for Sub-Component
> **Open:** `specs/[ComponentName].spec.md`  
> **Run once per missing sub-component**

```
You are a software analyst. Read #file only.
Do not read any other files. Do not scan the workspace.

From the UI Behaviour section of this spec, extract everything that belongs
to the [SubComponentName] sub-component only.

Produce a mini-spec in this format:

## [SubComponentName] — Mini Spec

### Purpose
One sentence describing what this sub-component renders and why it exists.

### Props
List every piece of data and every callback this sub-component needs from its parent.
| Prop name | Type | What it is |

### UI Behaviour
- Every show/hide rule that belongs to this sub-component
- Every list rendering (Array.map) that belongs here
- Every form binding (controlled input) that belongs here
- Every user interaction (onClick, onChange, onSubmit) that belongs here

### Notes
Any special behaviour, conditional rendering, or edge cases.

Output Markdown only. No preamble.
```

**Save output → `specs/[SubComponentName].mini-spec.md`**

---

#### 3-D-3 — Generate the Sub-Component
> **Why split:** A 170-line mini-spec with a full code generation request still times out.  
> Split into three focused prompts — shell, logic, JSX — same principle as the main component  
> but simpler because sub-components have no API calls and less state.

---

##### 3-D-3a — Shell, Props & State
> **Open:** `specs/[SubComponentName].mini-spec.md`  
> **Before running:** paste parent proposal Section 1 inline

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the parent component's file path convention:
[PASTE parent proposal.md SECTION 1 HERE]

Generate ONLY the top of the sub-component file:
1. Comment block at the top:
   // Sub-component of: [ParentComponentName]
   // Extracted from: [original AngularJS template file]
   // Migration date: [today's date]

2. All import statements
   (React, PropTypes, clsx if needed, child sub-components if any)

3. PropTypes declaration — one entry per prop in the mini-spec Props section

4. The component function signature and opening brace:
   export default function [SubComponentName]({ prop1, prop2, ... }) {

5. Any useState declarations needed for internal state
   (only state that is NOT passed as a prop — internal UI state only)

Do NOT write handlers or JSX yet. Stop after the useState declarations.
Do NOT write the closing brace.

Output code only. No preamble.
```

**Save output → create `src/[path]/[SubComponentName].jsx` with this content**

---

##### 3-D-3b — Handlers & Logic
> **Open:** `specs/[SubComponentName].mini-spec.md`  
> **Before running:** paste only the User Interactions part of the mini-spec UI Behaviour section

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here are the user interactions for this sub-component:
[PASTE ONLY THE USER INTERACTIONS PART OF THE MINI-SPEC UI BEHAVIOUR HERE]

Generate ONLY the event handler functions inside the component function,
continuing after the useState declarations already written above:
1. One named function per user interaction
2. Use handle* or on* prefix for all handlers
3. Handlers receive event or data values as parameters
4. Handlers call the relevant callback prop (e.g. onFilterChange, onRowSelect)
   or update internal state — based on the mini-spec

Do NOT write JSX yet.
Assume props and useState already exist above. Do NOT write the closing brace.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[SubComponentName].jsx` after the useState section**

---

##### 3-D-3c — JSX & Return
> **Open:** `specs/[SubComponentName].mini-spec.md`  
> **Before running:** paste the UI Behaviour section of the mini-spec (all parts except User Interactions — those are already handled in 3-D-3b)

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the UI behaviour for this sub-component (show/hide, lists, form bindings, styles):
[PASTE MINI-SPEC UI BEHAVIOUR HERE — exclude the User Interactions part]

Generate ONLY the return statement and closing brace of the sub-component,
continuing after the handlers already written above:
1. The return( opening
2. Complete JSX implementing every item above:
   - Show/hide rules as conditional rendering
   - Lists as Array.map() with key prop
   - Form bindings as controlled inputs (value + onChange)
   - Dynamic styles as className with clsx
3. All interaction handlers wired to the correct JSX elements
   (use the exact handler names from 3-D-3b)
4. The closing ) of return
5. The closing } of the component function

Assume all props, state, and handlers already exist above.

Output code only. No preamble.
```

**Append output → add to `src/[path]/[SubComponentName].jsx` after the handlers section**

---

##### 3-D-3d — Sub-Component Assembly Check
> **Open:** `src/[path]/[SubComponentName].jsx`  
> **Run after all three parts are appended**

```
You are a React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

This sub-component was assembled in parts. Check for:
1. Missing imports — are React, PropTypes, and all utilities imported?
2. Prop usage — does the JSX use the exact same prop names as the
   destructured params in the function signature?
3. Handler wiring — does every interactive element reference a handler
   that exists in the file?
4. PropTypes completeness — is every prop used in the JSX declared in PropTypes?
5. Unclosed brackets — are all { } ( ) matched?

For each issue:
- Location: [line area]
- Problem: [what is wrong]
- Fix: [exact corrected line]

If no issues, write: "Assembly looks correct"

Output Markdown only. No preamble.
```

Apply any fixes, then proceed to 3-D-4.

---

#### 3-D-4 — Wire Sub-Component Into Parent
> **Open:** `src/[path]/[ComponentName].jsx` (the parent file)

**Step 1 — Add the import** at the top of the parent file:

```jsx
import [SubComponentName] from './[SubComponentName]'
```

**Step 2 — Replace the inline JSX region** in the parent's return statement with the sub-component tag. If you are unsure which props to pass, run this prompt:

> **Open:** `specs/[SubComponentName].mini-spec.md`

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

The parent component has these state variables and handlers:
[PASTE JUST THE VARIABLE AND FUNCTION NAMES FROM THE PARENT — not the full code]

Based on the Props section of this mini-spec, write the JSX tag for this
sub-component with all props correctly mapped from the parent's state and handlers.

Output the JSX tag only. One line per prop. No preamble.
```

Paste the generated tag into the correct slot in the parent's return statement.

---

#### 3-D-5 — Re-run Assembly Check on Parent
> **Open:** `src/[path]/[ComponentName].jsx`  
> **Run after all sub-components have been wired in**

Re-run the 3-A-5 assembly check prompt on the parent file to confirm:
- All sub-component imports are present
- All prop names match between parent state/handlers and sub-component tags
- No JSX region placeholders remain

Apply any fixes using the 3-A-5F decision tree, then the parent component is complete and ready for 3-C-1.

---

#### 3-D — Sub-Component Flow Summary

```
For each missing sub-component (parent before child):

  3-D-2   →  Extract mini-spec from parent spec
              Save as specs/[SubComponentName].mini-spec.md

  3-D-3a  →  Shell, props & state     → creates src/[path]/[SubComponentName].jsx
  3-D-3b  →  Handlers & logic         → appended
  3-D-3c  →  JSX & return             → appended
  3-D-3d  →  Sub-component assembly check → fix any issues

  3-D-4   →  Add import to parent
              Replace JSX region with <SubComponent props />

After all sub-components are wired in:

  3-D-5   →  Re-run 3-A-5 on parent file
              Fix any import or prop mismatches
```

> **Trivially small sub-components** (e.g. a single table row with no logic, under ~30 lines):  
> Skip 3-D-2 and 3-D-3 entirely — write the component by hand directly in `src/`.  
> It is faster than running any prompts for something that simple.

---

## Phase 4 — Local Setup & Testing
> **When to run:** After Phase 3 is complete for all components  
> **Goal:** Run the migrated React app locally and verify it behaves identically
> to the original AngularJS app using real sample data

---

### Why Two Testing Modes

| Mode | When to use | What it needs |
|---|---|---|
| **Mode B — MSW mocks** | Component testing without backend | Sample JSON from browser network tab |
| **Mode A — Real backend** | Full integration testing | Java backend running locally |

Always validate with Mode B first, then Mode A.

---

### One-Time Setup — MSW (Mock Service Worker)

MSW intercepts API calls at the network level. Your components make real `fetch`/`axios`
calls and MSW returns your sample JSON — components behave exactly as they would in
production, without the backend running.

**Step 1 — Install MSW**

```bash
npm install msw --save-dev
npx msw init public/ --save
```

**Step 2 — Create the mock folder structure**

```
src/
└── mocks/
    ├── handlers.js        ← one handler per API endpoint
    ├── browser.js         ← MSW browser setup
    └── data/
        ├── market-fees.json
        ├── market-fee-by-id.json
        └── [endpoint].json
```

**Step 3 — Create `src/mocks/browser.js`**

```javascript
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
```

**Step 4 — Start MSW in `src/index.jsx` (development only)**

```javascript
async function enableMocking() {
  if (process.env.NODE_ENV !== 'development') return
  if (process.env.VITE_USE_MOCKS !== 'true') return
  const { worker } = await import('./mocks/browser')
  return worker.start({
    onUnhandledRequest: 'warn'
  })
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(<App />)
})
```

Create `.env.local` in your React project root:
```
VITE_USE_MOCKS=true
```

> `onUnhandledRequest: 'warn'` prints a console warning for every API call
> with no mock handler — tells you immediately if you missed an endpoint.

---

### Collecting Sample Data From the AngularJS App

Do this for every endpoint in `specs/API-Layer-Audit.md` Section 2.

1. Open the AngularJS app in the browser
2. Open DevTools → Network tab → filter by `Fetch/XHR`
3. Navigate to the part of the app that triggers each API call
4. Click the request → Response tab → copy the full JSON
5. Save as `src/mocks/data/[descriptive-name].json`

Name files to match the endpoint:
```
GET  /api/market-fees      → src/mocks/data/market-fees.json
GET  /api/market-fees/:id  → src/mocks/data/market-fee-by-id.json
POST /api/market-fees      → src/mocks/data/market-fee-create.json
```

Collect **at least two variants** for list endpoints — one with data, one empty.

---

### Copilot Prompt — Generate MSW Handlers From Audit

Use this prompt to generate `handlers.js` automatically instead of writing it by hand.

> **Open:** `specs/API-Layer-Audit.md`  
> **Before running:** paste Section 2 table inline

```
You are a React 18 test engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the complete list of API endpoints from the audit:
[PASTE API-LAYER-AUDIT SECTION 2 TABLE HERE]

Generate a complete MSW handlers.js file using msw v2 syntax (http, HttpResponse).

Rules:
1. One handler per endpoint row in the table
2. Import each response from ./data/[descriptive-name].json
3. Use the HTTP method and endpoint path exactly as shown in the table
4. For endpoints with :id or path params, use the MSW params syntax
5. For POST/PUT handlers, read the request body with await request.json()
6. Add a commented-out error handler variant below each handler
7. Add a comment above each handler showing the endpoint and what it does

Output only the handlers.js file. No preamble.
```

**Save output → `src/mocks/handlers.js`**  
Then fill the corresponding JSON files in `src/mocks/data/` with your network tab captures.

---

### Running Locally — Mode B (MSW mocks, no backend needed)

**Step 1 — Confirm `.env.local` has `VITE_USE_MOCKS=true`**

**Step 2 — Start the React app**

```bash
npm run dev
```

**Step 3 — Open browser DevTools console and confirm:**
```
[MSW] Mocking enabled.
```

If this message is missing, recheck Step 4 of the MSW setup.

**Step 4 — For each migrated component, verify against spec Section 5:**

| Spec says | Verify in browser |
|---|---|
| Show/hide rules | Toggle the condition — confirm element appears/disappears |
| List rendering | Confirm list renders with mock data and empty state when empty |
| Form bindings | Type into fields — confirm values are captured |
| User interactions | Click every button — confirm correct action fires |
| Loading state | Check network tab — confirm loading indicator shows during fetch |
| Error state | Uncomment MSW error handler, reload, confirm error is surfaced |

---

### Running Locally — Mode A (Real Java backend)

**Step 1 — Start the Java backend**

```bash
./mvnw spring-boot:run
# or
./gradlew bootRun
```

**Step 2 — Switch off MSW**

Update `.env.local`:
```
VITE_USE_MOCKS=false
```

**Step 3 — Configure the API proxy (prevents CORS issues)**

For Vite — add to `vite.config.js`:
```javascript
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
}
```

For Create React App — add to `package.json`:
```json
"proxy": "http://localhost:8080"
```

**Step 4 — Start the React app**

```bash
npm run dev
```

Repeat the same verification checklist as Mode B with real data from the backend.

---

### Copilot Prompt — Generate Component Test Checklist

> **Open:** `specs/[ComponentName].spec.md`

```
You are a QA engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Generate a manual test checklist for this component in Markdown.
For each item in the spec, produce a testable step:

## [ComponentName] — Manual Test Checklist

### API & Data
- [ ] one checkbox per API call — what to trigger it and what to verify

### UI Behaviour
- [ ] one checkbox per show/hide rule — what condition to set and what to look for
- [ ] one checkbox per list — what data state to use and what to verify
- [ ] one checkbox per form binding — what to type and what to confirm
- [ ] one checkbox per user interaction — what to click and what should happen

### Error States
- [ ] one checkbox per API call — enable MSW error handler and verify error is shown

### Empty States
- [ ] one checkbox per list — use empty mock data and verify empty state renders

Output Markdown only. No preamble.
```

**Save output → `specs/[ComponentName].test-checklist.md`**

---

## Key Rules for Using Copilot in IntelliJ

| Rule | Why it matters |
|---|---|
| One prompt = one task | Multi-task prompts are the primary cause of timeouts |
| One `#file` per prompt | Multiple open files trigger workspace indexing and timeouts |
| Always include "Do not scan the workspace" | Suppresses Copilot's background indexing behaviour |
| Paste HTML template inline — never open it as `#file` | Keeps token count predictable, prevents workspace scan |
| Paste context inline, don't open more files | Keeps token count low, prevents Java files being scanned |
| New chat session per prompt | Prevents accumulated context causing slowdowns |
| Type `continue` if output is truncated | Copilot resumes from where it stopped |
| If 3-A-3 times out, use 3-A-3a/3b/3c | Splits data fetching, handlers, and business logic into separate prompts |
| If 3-A-4 times out, split JSX by UI section | One prompt per major block — form, table, modal, nav |
| Never reference the full-stack React/Java project | Always use `react-reference/` snapshot files instead |
| Save every output before the next prompt | Each prompt depends on the previous — losing output means re-running |

---

## AngularJS → React 18 Pattern Cheat Sheet

| AngularJS | Location | React 18 Equivalent |
|---|---|---|
| Controller | JS | Functional component + hooks |
| `$scope` / two-way binding | JS | `useState` / `useReducer` |
| Service / Factory | JS | Custom hook or Context provider |
| Directive | JS | Reusable functional component |
| `$http` | JS | Adopt from API-Layer-Audit proposal |
| `ui-router` / `ngRoute` | JS | React Router v6 |
| `$rootScope` events | JS | Context API or Zustand |
| Filters | JS | Pure utility functions |
| `ng-repeat` | HTML | `Array.map()` |
| `ng-if` / `ng-show` / `ng-hide` | HTML | Conditional rendering (`&&`, ternary) |
| `ng-model` | HTML | Controlled input with `useState` |
| `ng-class` | HTML | Dynamic `className` with `clsx` |
| `ng-click` / `ng-submit` | HTML | `onClick` / `onSubmit` handler |
| `ng-change` | HTML | `onChange` handler |
| Custom directive in template | HTML | Reusable React component |
| HTTP interceptor | JS | Axios instance with interceptors |
| `$httpProvider.interceptors` | JS | Axios request/response interceptors |
| `index.html` app shell | HTML | `index.html` + `App.jsx` + router setup |
| `ng-view` / `ui-view` | HTML | `<Routes>` / `<Outlet>` in React Router v6 |
| Layout controller in `index.html` | HTML | Context provider or layout wrapper in `App.jsx` |

---

## Migration Checklist (Per Component)

> **Re-run marker legend:**  
> 🔶 = paste HTML inline  
> 🔁 = may need to re-run if a later step fails (see Re-run Reference Guide above)  
> ⚠️ = only run if condition is met

### Phase 0.5 — API Layer Audit *(run once for the whole app)*
- [ ] 0.5-A — Interceptors output saved
- [ ] 0.5-B — $http calls output saved (one run per file)
- [ ] 0.5-C — Auth & error handling output saved
- [ ] 0.5-D — React equivalent proposal output saved
- [ ] 0.5-E — index.html audit output saved
- [ ] `specs/API-Layer-Audit.md` assembled and reviewed

### Phase 0 — Spec Generation
- [ ] 0-A — Purpose & type output saved
- [ ] 0-B — Inputs & outputs output saved
- [ ] 0-C — State output saved
- [ ] 0-D — Business rules & API calls saved (HTML pasted inline) 🔶 🔁
- [ ] 0-E — UI behaviour saved (HTML pasted inline) 🔶 🔁
- [ ] `specs/[ComponentName].spec.md` assembled and reviewed

### Phase 1 — Analysis
- [ ] 1-A — Complexity rating saved
- [ ] 1-B — Pattern mapping saved (HTML pasted inline) 🔶 🔁
- [ ] 1-C — API call verification saved
- [ ] 1-D — Risks & blockers saved (HTML pasted inline) 🔶 🔁
- [ ] `specs/[ComponentName].analysis.md` assembled
- [ ] Gate check: any unknown third-party library blockers?
  - [ ] If YES — React equivalent added to `react-reference/package.json`
  - [ ] If NO  — proceed directly to Phase 2

### Phase 2 — Proposal
- [ ] 2-A — Target file path saved
- [ ] 2-B — Dependencies saved
- [ ] 2-C — Component hierarchy saved (HTML pasted inline) 🔶 🔁
- [ ] 2-D — API integration plan saved
- [ ] 2-E — State & data flow plan saved
- [ ] `specs/[ComponentName].proposal.md` assembled and confirmed

### Phase 3 — Code Generation
- [ ] 3-A-1  — Imports & shell generated, file created in `src/`
- [ ] 3-A-2  — State & hooks appended 🔁
- [ ] 3-A-3a — Data fetching (useEffect) appended 🔁
- [ ] 3-A-3b — Event handlers appended 🔁
- [ ] 3-A-3c — Business logic functions appended 🔁
- [ ] 3-A-4  — JSX & return appended (split by UI region if needed) 🔁
- [ ] 3-A-5  — Assembly check run on `src/[path]/[ComponentName].jsx`
- [ ] 3-A-5F — ⚠️ Only if 3-A-5 found errors:
  - [ ] Trivial errors fixed manually
  - [ ] Logic gap errors fixed with targeted fix prompt (one per error)
  - [ ] Missing sections fixed by re-running relevant 3-A sub-prompt
  - [ ] 3-A-5 re-run to confirm all errors resolved
- [ ] 3-C-1  — State & communication review run, fixes applied
- [ ] 3-C-2  — Data fetching review run, fixes applied
- [ ] 3-C-3  — Business logic review run, fixes applied
- [ ] 3-C-4  — Template coverage run once per UI region (4 runs total), fixes applied
- [ ] 3-C-5  — Final sign-off run (paste 3-C-1 to 3-C-4 outputs — no file open), verdict is "ready"
- [ ] 3-B    — `specs/[ComponentName].migration.md` saved
- [ ] 3-D    — ⚠️ Only if proposal Section 3 lists sub-components not yet in `src/`:
  - [ ] 3-D-2  — Mini-spec extracted for each missing sub-component
  - [ ] 3-D-3a — Shell, props & state generated, file created in `src/`
  - [ ] 3-D-3b — Handlers & logic appended
  - [ ] 3-D-3c — JSX & return appended
  - [ ] 3-D-3d — Sub-component assembly check run, issues fixed
  - [ ] 3-D-4  — Import added and JSX region wired in parent for each
  - [ ] 3-D-5  — 3-A-5 re-run on parent file, all prop/import issues fixed

### Phase 4 — Testing
- [ ] Sample JSON collected from network tab for all endpoints
- [ ] MSW handlers generated and JSON files filled
- [ ] Mode B: React app runs with mocks, all UI behaviour verified
- [ ] Mode B: Loading, error, and empty states verified
- [ ] Mode A: Java backend running, proxy configured
- [ ] Mode A: All API calls return real data successfully
- [ ] Mode A: Auth token attached correctly (check network tab)
- [ ] Mode A: Full user flow works end to end
- [ ] `specs/[ComponentName].test-checklist.md` saved

---

*Runbook version 2.2 — AngularJS to React 18 — GitHub Copilot / IntelliJ*  
*(HTML-aware · fully split · timeout-safe · self-reviewing · sub-component aware · with local testing)*
