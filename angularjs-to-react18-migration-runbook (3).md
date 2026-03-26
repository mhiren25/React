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
  inline alongside the JS file — the sub-prompts that need it are clearly marked with
  🔶 **Paste HTML template inline**

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

---

## Phase Overview

```
Phase 0.5 — API Layer Audit        5 prompts  — run ONCE for the whole app
                                               (includes index.html audit)
Phase 0   — Spec Generation        5 prompts  — run per component
                                               (0-D and 0-E use HTML template)
Phase 1   — Analysis & Gap Report  4 prompts + 1 gate check — run per component
                                               (1-B and 1-D use HTML template)
Phase 2   — Migration Proposal     5 prompts  — run per component
                                               (2-C uses HTML template)
Phase 3   — Code Generation        3 prompts  — run per component (after confirmation)
            3-A: Generate component
            3-C: Self-review & fix  ← catches all blockers automatically
            3-B: Migration document
```

> **Golden rule:** One prompt = one task = one file open.  
> Save each output before running the next prompt.  
>
> **On blockers:** After Phase 1, the only manual check needed is whether any
> unknown third-party library equivalents were flagged. Everything else is
> caught and fixed automatically by Phase 3-C. No React knowledge required.

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

### 0.5-E — index.html Audit ⭐ NEW
> **Open:** `index.html`  
> **Note:** This covers the app shell — routing placeholder, global layout, script loading

```
You are a frontend analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Document the following from index.html:

1. App bootstrap
   - How is the Angular app initialised? (ng-app directive and where it sits)

2. Layout structure
   - What is the top-level HTML structure?
   - Are there layout elements (header, nav, sidebar, footer) that wrap
     the whole app, outside of the routing placeholder?

3. Routing placeholder
   - Where is ng-view or ui-view placed in the document?
   - Is there a default route or redirect defined here?

4. Global scripts and styles
   - List every script tag and stylesheet link
   - Flag any third-party libraries loaded via CDN

5. Migration notes
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

```
You are a React 18 architect. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the HTML template for this component:
[PASTE FULL CONTENTS OF [ComponentName].html HERE]

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
> Type `Confirmed, proceed to Phase 3` in your next Copilot Chat session.

---

## Phase 3 — Code Generation & Migration Document
> **Frequency:** Per component — only after Phase 2 is confirmed  
> **Order:** 3-A (generate) → 3-C (self-review & fix) → 3-B (document)  
> **Rule:** Run 3-C before 3-B — fixes from the review must be applied to the component first.

---

### 3-A — Generate the React Component
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the full proposal and API audit Section 7 inline

```
You are a React 18 engineer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the approved migration proposal for this component:
[PASTE FULL specs/[ComponentName].proposal.md CONTENT HERE]

Here is the approved API Layer Audit React proposal (Section 7 only):
[PASTE API-LAYER-AUDIT SECTION 7 HERE]

Generate the fully migrated React 18 component. Rules:
1. Functional components only — no class components
2. Hooks for all state and side effects
3. Place the file at the exact path in proposal Section 1
4. Use only packages listed in proposal Section 2
5. Follow the component hierarchy in proposal Section 3
6. Implement API calls exactly as described in proposal Section 4
7. Implement state exactly as described in proposal Section 5
8. Render the JSX structure based on the UI Behaviour section of the spec —
   reproduce every show/hide rule, list rendering, form binding, and
   interaction handler documented there
9. Preserve every business rule from the spec — do not alter behaviour
10. Add this comment block at the top:
    // Migrated from: [original AngularJS JS file path]
    // Template: [original HTML template file path]
    // Spec: specs/[ComponentName].spec.md
    // Migration date: [today's date]
    // AngularJS pattern replaced: [Controller / Service / Directive]

After the code, list every assumption made that was not in the spec.
```

**Save output → place React file in `src/` at the path from proposal Section 1**

---

### 3-C — Self-Review & Fix
> **Open:** The generated React component file  
> **Before running:** paste the spec and analysis Section 4 inline  
> **Purpose:** Catches all blocker issues automatically — no React knowledge needed to run this

```
You are a senior React 18 code reviewer. Read #file only.
Do not read any other files. Do not scan the workspace.

Here is the original spec for this component:
[PASTE FULL specs/[ComponentName].spec.md CONTENT HERE]

Here are the blockers identified during analysis:
[PASTE specs/[ComponentName].analysis.md SECTION 4 HERE]

Review the React component in #file and check for these six issues:

1. Shared state risk
   Is any state that was shared across controllers now isolated inside
   a single component? If yes, flag it — it should be in a Context
   provider or Zustand store.

2. Cross-component communication
   Were any $rootScope broadcast/on patterns converted to prop callbacks?
   If yes, flag them — they likely need Context API instead.

3. Data fetching timing
   Were any route resolve blocks converted to useEffect?
   If yes, flag whether this causes a render-before-data problem.

4. Business logic assumptions
   List every place where the component makes an assumption not
   explicitly covered by the spec.

5. Missing error handling
   Are API errors caught and surfaced to the user?
   Flag exactly where error handling is absent.

6. Template coverage
   Does the JSX cover every show/hide rule, list rendering, form binding,
   and interaction documented in the spec UI Behaviour section?
   Flag any that are missing or implemented differently from the spec.

For each issue found output:
- Location: [function name or line area]
- Problem: [plain English explanation]
- Fix: [exact corrected code snippet]

If no issues found, write: "No issues found — component matches spec"

Output Markdown only. No preamble.
```

**Read the output carefully.**  
For each flagged issue, apply the fix snippet to the React component file.  
Once all fixes are applied, proceed to 3-B.

---

### 3-B — Generate the Migration Document
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the analysis and proposal inline  
> **Important:** Run this only after 3-C fixes have been applied

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

## Key Rules for Using Copilot in IntelliJ

| Rule | Why it matters |
|---|---|
| One prompt = one task | Multi-task prompts are the primary cause of timeouts |
| One `#file` per prompt | Multiple open files trigger workspace indexing and timeouts |
| Always include "Do not scan the workspace" | Suppresses Copilot's background indexing behaviour |
| Paste HTML template inline — never open it as `#file` | Keeps token count predictable, prevents workspace scan |
| Paste context inline, don't open more files | Keeps token count low and prevents Java files being scanned |
| New chat session per prompt | Prevents accumulated context from previous prompts causing slowdowns |
| Type `continue` if output is truncated | Copilot resumes from where it stopped |
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

---

## Migration Checklist (Per Component)

### Phase 0.5 — API Layer Audit *(first component only)*
- [ ] 0.5-A — Interceptors output saved
- [ ] 0.5-B — $http calls output saved (one run per file)
- [ ] 0.5-C — Auth & error handling output saved
- [ ] 0.5-D — React equivalent proposal output saved
- [ ] 0.5-E — index.html audit output saved ⭐ NEW
- [ ] `specs/API-Layer-Audit.md` assembled and reviewed

### Phase 0 — Spec Generation
- [ ] 0-A — Purpose & type output saved
- [ ] 0-B — Inputs & outputs output saved
- [ ] 0-C — State output saved
- [ ] 0-D — Business rules & API calls saved (HTML pasted inline) 🔶
- [ ] 0-E — UI behaviour saved (HTML pasted inline) 🔶
- [ ] `specs/[ComponentName].spec.md` assembled and reviewed

### Phase 1 — Analysis
- [ ] 1-A — Complexity rating saved
- [ ] 1-B — Pattern mapping saved (HTML pasted inline) 🔶
- [ ] 1-C — API call verification saved
- [ ] 1-D — Risks & blockers saved (HTML pasted inline) 🔶
- [ ] `specs/[ComponentName].analysis.md` assembled
- [ ] Gate check: any unknown third-party library blockers?
  - [ ] If YES — React equivalent added to `react-reference/package.json`
  - [ ] If NO  — proceed directly to Phase 2

### Phase 2 — Proposal
- [ ] 2-A — Target file path saved
- [ ] 2-B — Dependencies saved
- [ ] 2-C — Component hierarchy saved (HTML pasted inline) 🔶
- [ ] 2-D — API integration plan saved
- [ ] 2-E — State & data flow plan saved
- [ ] `specs/[ComponentName].proposal.md` assembled and confirmed

### Phase 3 — Code Generation
- [ ] 3-A — React component generated and placed in `src/`
- [ ] 3-C — Self-review run, all flagged issues fixed in the component
- [ ] 3-B — `specs/[ComponentName].migration.md` saved
- [ ] All backend calls tested against actual API endpoints
- [ ] Auth token handling confirmed working
- [ ] Loading and error states verified in the UI
- [ ] UI behaviour verified against original HTML template visually

---

*Runbook version 1.5 — AngularJS to React 18 — GitHub Copilot / IntelliJ (HTML-aware, fully split, timeout-safe, self-reviewing)*
