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
│   ├── API-Layer-Audit.md              ← Phase 0.5 (assembled from 4 sub-prompts)
│   ├── [ComponentName].spec.md         ← Phase 0  (assembled from 5 sub-prompts)
│   ├── [ComponentName].analysis.md     ← Phase 1  (assembled from 4 sub-prompts)
│   ├── [ComponentName].proposal.md     ← Phase 2  (assembled from 5 sub-prompts)
│   └── [ComponentName].migration.md    ← Phase 3B (migration document)
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

## Phase Overview

```
Phase 0.5 — API Layer Audit        4 prompts  — run ONCE for the whole app
Phase 0   — Spec Generation        5 prompts  — run per component
Phase 1   — Analysis & Gap Report  4 prompts  — run per component
Phase 2   — Migration Proposal     5 prompts  — run per component
Phase 3   — Code Generation        2 prompts  — run per component (after confirmation)
```

> **Golden rule:** One prompt = one task = one file open.  
> Save each output before running the next prompt.  
> Never skip a review step — that is where bugs are cheapest to fix.

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

### 0.5 — Assemble the Audit File

Combine all four outputs into `specs/API-Layer-Audit.md`:

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
```

> **Review before proceeding.** This is the API contract for the entire migration.

---

## Phase 0 — Spec Generation
> **Frequency:** Per component file  
> **Rule:** Open only the AngularJS component file being specced. One file per prompt. New chat session per prompt.

---

### 0-A — Purpose & Type
> **Open:** The AngularJS component file (e.g. `userController.js`)

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
> **Open:** Same AngularJS component file

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
> **Open:** Same AngularJS component file

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

### 0-D — Business Rules & API Calls
> **Open:** Same AngularJS component file

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

For each controller, service, directive, or filter in this file, output:

## [Component Name] — Business Rules & API Calls

### API Calls
List every backend call made, the condition that triggers it, and what
the result is used for. Do not describe $http syntax — describe the intent.

### Business Rules
List every conditional check, validation, and calculation in plain English.
Focus on WHAT the rule enforces and WHY, not HOW Angular implements it.

Output Markdown only. No code. No preamble.
```

**Save output → paste as Section 4 of `specs/[ComponentName].spec.md`**

---

### 0-E — UI Behaviour
> **Open:** Same AngularJS component file

```
You are a software analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

For each controller, service, directive, or filter in this file, output:

## [Component Name] — UI Behaviour

### Show / Hide Rules
List every ng-if, ng-show, ng-hide condition in plain English.

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
[0-D output]

## Section 5 — UI Behaviour
[0-E output]
```

> **Review carefully before proceeding.**  
> Correct any misunderstood business rules — all subsequent phases trust this spec.

---

## Phase 1 — Analysis & Gap Report
> **Frequency:** Per component  
> **Rule:** Open only the files mentioned per sub-prompt. New chat session per prompt.

---

### 1-A — Complexity Rating
> **Open:** The AngularJS component file

```
You are a migration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

Rate this component: Low / Medium / High complexity for migrating to React 18.
Justify in exactly one sentence.

Output Markdown only. No preamble.
```

**Save output → paste as Section 1 of `specs/[ComponentName].analysis.md`**

---

### 1-B — Pattern Mapping
> **Open:** The AngularJS component file

```
You are a migration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

List every AngularJS pattern found and its React 18 equivalent:
| AngularJS Pattern Found | React 18 Equivalent | Notes |

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
- ng-if / ng-show → Conditional rendering
- ng-model → Controlled input with useState
- ng-class → Dynamic className with clsx

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

### 1-D — Risks & Blockers
> **Open:** The AngularJS component file

```
You are a migration analyst. Scan #file only.
Do not read any other files. Do not scan the workspace.

List every pattern in this file that cannot be automatically converted to React 18
and will need manual attention. For each, describe:
- What the pattern is
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
[1-B output]

## Section 3 — API Call Verification
[1-C output]

## Section 4 — Risks & Blockers
[1-D output]
```

> **Review Section 4 carefully.** Resolve any blockers before starting Phase 2.

---

## Phase 2 — Migration Proposal
> **Frequency:** Per component  
> **Rule:** Open only the files mentioned per sub-prompt. New chat session per prompt.

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

### 2-C — Component Hierarchy
> **Open:** `specs/[ComponentName].spec.md`

```
You are a React 18 architect. Read #file only.
Do not read any other files. Do not scan the workspace.

Based on the UI Behaviour section of this spec, propose a component hierarchy tree.
Show which parts of this component should be split into separate React components.
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
[2-C output]

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
> **Rule:** Phase 3 is split into two separate prompts to avoid timeout. Code first, document second.

---

### 3-A — Generate the React Component
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the full proposal inline into the prompt

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
8. Preserve every business rule from the spec — do not alter behaviour
9. Add this comment block at the top:
   // Migrated from: [original AngularJS file path]
   // Spec: specs/[ComponentName].spec.md
   // Migration date: [today's date]
   // AngularJS pattern replaced: [Controller / Service / Directive]

After the code, list every assumption made that was not in the spec.
```

**Save output → place React file in `src/` at the path from proposal Section 1**

---

### 3-B — Generate the Migration Document
> **Open:** `specs/[ComponentName].spec.md`  
> **Before running:** paste the analysis and proposal inline

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
Source file, component type, complexity rating, migration date.

## What Changed
Bullet list of every AngularJS construct and its React 18 equivalent.

## API & Backend Changes
How $http calls were migrated, auth handling, loading and error state approach.

## New File Location
Where the migrated file lives and why.

## Dependency Changes
| Removed (AngularJS) | Added (React) | Reason |

## Assumptions Made
Every assumption from the code generation step.

## Manual Steps Required
Every item from analysis Section 4 (Risks & Blockers).

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
| Paste context inline, don't open more files | Keeps token count low and prevents Java files being scanned |
| New chat session per prompt | Prevents accumulated context from previous prompts causing slowdowns |
| Type `continue` if output is truncated | Copilot resumes from where it stopped |
| Never reference the full-stack React/Java project | Always use `react-reference/` snapshot files instead |
| Save every output before the next prompt | Each prompt depends on the previous — losing output means re-running |

---

## AngularJS → React 18 Pattern Cheat Sheet

| AngularJS | React 18 Equivalent |
|---|---|
| Controller | Functional component + hooks |
| `$scope` / two-way binding | `useState` / `useReducer` |
| Service / Factory | Custom hook or Context provider |
| Directive | Reusable functional component |
| `$http` | Adopt from API-Layer-Audit proposal |
| `ui-router` / `ngRoute` | React Router v6 |
| `$rootScope` events | Context API or Zustand |
| Filters | Pure utility functions |
| `ng-repeat` | `Array.map()` |
| `ng-if` / `ng-show` | Conditional rendering (`&&`, ternary) |
| `ng-model` | Controlled input with `useState` |
| `ng-class` | Dynamic `className` with `clsx` |
| HTTP interceptor | Axios instance with interceptors |
| `$httpProvider.interceptors` | Axios request/response interceptors |

---

## Migration Checklist (Per Component)

### Phase 0.5 — API Layer Audit *(first component only)*
- [ ] 0.5-A — Interceptors output saved
- [ ] 0.5-B — $http calls output saved (one run per file)
- [ ] 0.5-C — Auth & error handling output saved
- [ ] 0.5-D — React equivalent proposal output saved
- [ ] `specs/API-Layer-Audit.md` assembled and reviewed

### Phase 0 — Spec Generation
- [ ] 0-A — Purpose & type output saved
- [ ] 0-B — Inputs & outputs output saved
- [ ] 0-C — State output saved
- [ ] 0-D — Business rules & API calls output saved
- [ ] 0-E — UI behaviour output saved
- [ ] `specs/[ComponentName].spec.md` assembled and reviewed

### Phase 1 — Analysis
- [ ] 1-A — Complexity rating saved
- [ ] 1-B — Pattern mapping saved
- [ ] 1-C — API call verification saved
- [ ] 1-D — Risks & blockers saved
- [ ] `specs/[ComponentName].analysis.md` assembled, blockers reviewed

### Phase 2 — Proposal
- [ ] 2-A — Target file path saved
- [ ] 2-B — Dependencies saved
- [ ] 2-C — Component hierarchy saved
- [ ] 2-D — API integration plan saved
- [ ] 2-E — State & data flow plan saved
- [ ] `specs/[ComponentName].proposal.md` assembled and confirmed

### Phase 3 — Code Generation
- [ ] 3-A — React component generated and placed in `src/`
- [ ] 3-B — `specs/[ComponentName].migration.md` saved
- [ ] Migrated component verified against spec manually
- [ ] All backend calls tested against actual API endpoints
- [ ] Auth token handling confirmed working
- [ ] Loading and error states verified in the UI

---

*Runbook version 1.3 — AngularJS to React 18 — GitHub Copilot / IntelliJ (fully split, timeout-safe)*
