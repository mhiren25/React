# AngularJS → React 18 Migration Runbook
> **Tool:** GitHub Copilot Chat in IntelliJ IDEA  
> **Target:** React 18 (matching conventions from existing reference component)  
> **Approach:** Spec-first, phased migration with human review checkpoints

---

## Prerequisites

Before starting any migration, confirm the following:

- [ ] GitHub Copilot plugin installed and signed in (IntelliJ IDEA 2023.1+)
- [ ] Copilot Chat panel open (`View → Tool Windows → GitHub Copilot Chat`)
- [ ] AngularJS project open as the **active project** in IntelliJ
- [ ] React 18 reference project open in a **separate IntelliJ window**
- [ ] `specs/` folder created at the root of your project

---

## Folder Structure

Maintain this structure throughout the migration:

```
your-project/
├── specs/
│   ├── API-Layer-Audit.md              ← Phase 0.5 (run once for whole app)
│   ├── [ComponentName].spec.md         ← Phase 0  (per component)
│   ├── [ComponentName].analysis.md     ← Phase 1  (per component)
│   ├── [ComponentName].proposal.md     ← Phase 2  (per component)
│   └── [ComponentName].migration.md    ← Phase 3  (per component)
├── src/                                ← migrated React files live here
```

---

## Phase Overview

```
Phase 0.5 — API Layer Audit        Run ONCE for the whole app
Phase 0   — Spec Generation        Run per component
Phase 1   — Analysis & Gap Report  Run per component
Phase 2   — Migration Proposal     Run per component
Phase 3   — Code Generation        Run per component (after confirmation)
```

> **Golden rule:** Complete each phase and save its output before starting the next.  
> Never skip the review step between phases — this is where bugs are cheapest to fix.

---

## Phase 0.5 — API Layer Audit
> **Frequency:** Once per application  
> **Files to open:** AngularJS main module file + all service files + React reference component + React `package.json`

### Steps
1. Open your AngularJS `app.js` (or main module file) in the editor
2. Also open any dedicated API/HTTP service files via `#file` in the prompt
3. Open your React reference component and its `package.json` in another tab
4. Start a **new Copilot Chat session**
5. Run the prompt below

### Prompt

```
You are a backend integration analyst. Scan the AngularJS source files in #file 
and produce a complete API Layer Audit document.

### Section 1 — HTTP Interceptors
- Scan for $httpProvider.interceptors anywhere in the codebase
- For each interceptor found, document:
  - What it does (auth token injection, error handling, request transform, etc.)
  - Exact headers or tokens it adds or reads
  - Any redirect or retry logic
- If no interceptors are found, explicitly state: "No interceptors detected"

### Section 2 — All Backend Calls
List every unique $http call found across all files in this format:
| Method | Endpoint | Called From | Request Payload | Response Shape | Error Handling |

### Section 3 — Auth Mechanism
- How is the user authenticated? (JWT in header, cookie, session token, etc.)
- Where is the token stored? ($localStorage, $sessionStorage, cookie, memory)
- How is it attached to requests? (interceptor, per-call header, etc.)
- What happens on 401 or session expiry?

### Section 4 — Shared API Services
- List any Angular services that act as a central API layer
  (services that wrap $http and are injected into multiple controllers)
- For each, list which controllers depend on it

### Section 5 — Error Handling Strategy
- Is error handling global (interceptor) or per-call (.catch on each $http)?
- What happens on error? (toast, redirect, console.log, silent fail)
- Are there retry mechanisms?

### Section 6 — Loading State Management
- How does the app signal loading to the UI?
  (flags on $scope, ng-show with a boolean, third-party spinner, etc.)

### Section 7 — Proposed React Equivalent
Read the React reference component in #file and its package.json in #file.
Based on the data-fetching pattern already in use in the reference project, 
propose:
- The exact data-fetching approach to adopt (match what the reference uses)
- How to replicate interceptor behavior in React
  (axios instance with interceptors, fetch wrapper, React Query middleware, etc.)
- Where auth token logic should live in the React project
- Whether a central API service file should be created and what it should export
- How loading and error state will be handled consistently

Output this as a Markdown document titled: API-Layer-Audit.md
Do not generate any code yet. This document will be used as a reference 
contract for all subsequent component migrations.
```

### Output
- Copy the response and save as `specs/API-Layer-Audit.md`
- **Review carefully** — confirm every endpoint, auth mechanism, and the proposed React pattern before proceeding
- This document is the **single source of truth** for all API calls across the migration

---

## Phase 0 — Spec Generation
> **Frequency:** Once per component file  
> **Files to open:** The AngularJS component file you are speccing

### Steps
1. Open the target AngularJS file in the editor (e.g. `userController.js`)
2. Start a **new Copilot Chat session** (one session per component)
3. Run the prompt below

> **Tip:** Do one file at a time. Copilot quality drops significantly when given large multi-file inputs in a single prompt.

### Prompt

```
You are a software analyst. Analyze the AngularJS component in #file and generate 
a framework-agnostic specification document.

For each controller, service, directive, or filter found in the file, produce 
one spec block in this format:

---
## Component Name: [name]
**Type:** [Controller / Service / Directive / Filter]
**Purpose:** [Plain English — what does this do and why does it exist]

### Inputs
- Every parameter, route param, query param, or injected dependency
- Include type where inferable

### Outputs
- Events emitted, return values, data exposed to the view

### State
- Every state variable, its type, initial value, and what triggers a change

### API Calls
Reference the API-Layer-Audit.md for full endpoint details.
List only which endpoints this component calls and under what condition.

### Business Rules
- Every conditional, validation, and calculation in plain English
- Focus on WHAT and WHY, not HOW it is implemented in Angular

### UI Behavior
- Show/hide rules
- Dynamic CSS class conditions
- User interaction handlers and what they trigger

### Dependencies
- Other services or components this relies on
---

Do not generate any code.
Output only the specification in Markdown format.
```

### Output
- Save as `specs/[ComponentName].spec.md`
- **Review carefully** — correct any misunderstood business rules before moving to Phase 1
- This is your most important review gate — all subsequent phases trust this spec

---

## Phase 1 — Analysis & Gap Report
> **Frequency:** Once per component  
> **Files to open:** The AngularJS component file + its spec + `API-Layer-Audit.md`

### Steps
1. Keep the AngularJS component file open in the editor
2. Reference `specs/[ComponentName].spec.md` and `specs/API-Layer-Audit.md` via `#file`
3. Run the prompt below in a **continuing or new Copilot Chat session**

### Prompt

```
You are a migration analyst. Using the AngularJS source in #file, the approved 
spec in #file, and the API-Layer-Audit.md in #file:

### Section 1 — Complexity Rating
Rate this component: Low / Medium / High
Justify in one sentence.

### Section 2 — Pattern Mapping
Produce a mapping table:
| AngularJS Pattern Found | React 18 Equivalent | Notes |

Use these standard mappings:
- Controller → Functional component + hooks
- $scope / two-way binding → useState / useReducer
- Service / Factory → Custom hook or Context provider
- Directive → Reusable functional component
- $http → Adopt exact pattern from API-Layer-Audit.md proposal
- ui-router / ngRoute → React Router v6
- $rootScope events → Context API or Zustand
- Filters → Pure utility functions
- ng-repeat → Array.map()
- ng-if / ng-show → Conditional rendering
- ng-model → Controlled input with useState
- ng-class → Dynamic className with clsx

### Section 3 — API Calls in This Component
List every backend call this component makes and confirm it exists 
in the API-Layer-Audit.md. Flag any calls not present in the audit.

### Section 4 — Risks & Blockers
List anything that cannot be auto-converted and needs manual attention.

Output in Markdown. No code.
```

### Output
- Save as `specs/[ComponentName].analysis.md`
- Review the risks and blockers section — resolve any blockers before Phase 2

---

## Phase 2 — Migration Proposal
> **Frequency:** Once per component  
> **Files to open:** Spec + Analysis + API-Layer-Audit + React reference component + React `package.json`

### Steps
1. Open all five files via `#file` in the prompt
2. Run the prompt below
3. **Do not proceed to Phase 3 until you have reviewed and confirmed this proposal**

### Prompt

```
You are a React 18 architect. Using:
- Approved spec: #file
- Analysis report: #file
- API Layer Audit: #file
- React reference component: #file
- React project package.json: #file

Propose the following. No code yet.

### 1. Target File Path
Where should the migrated React file live?
Follow the exact folder and naming conventions from the reference component.

### 2. Dependencies Needed
| Package | Version | Replaces | dep / devDep |
- Match React version from reference package.json exactly
- For data-fetching: use whatever the reference project already uses
- Do not introduce new libraries unless nothing in the reference project covers the need

### 3. Component Hierarchy
Simple tree of any sub-components to be split out from this one.

### 4. API Integration Plan
Based on the API-Layer-Audit.md proposal:
- Which API calls does this component own?
- Should they live in this component, a custom hook, or a shared API service?
- How will loading and error state be surfaced in the UI?

### 5. State & Data Flow Plan
Plain English description of how state will be managed,
based strictly on patterns already in the reference component.

Output in Markdown. No code.
Confirm with me before proceeding to Phase 3.
```

### Output
- Save as `specs/[ComponentName].proposal.md`
- Type `Confirmed, proceed to Phase 3` in Copilot Chat only when you are satisfied with the proposal
- Pay special attention to the dependency list and API integration plan — changes here are free, changes after code is written are not

---

## Phase 3 — Code Generation & Migration Document
> **Frequency:** Once per component, after explicit confirmation  
> **Files to open:** Spec + Proposal + API-Layer-Audit + React reference component

### Steps
1. Confirm Phase 2 proposal in chat before running this prompt
2. Open the four files via `#file`
3. Run the prompt below

### Prompt

```
You are a React 18 engineer. Using:
- Approved spec: #file
- Migration proposal: #file
- API Layer Audit: #file
- React reference component: #file

Generate the fully migrated React 18 component. Follow these rules strictly:

1. Functional components only — no class components
2. Hooks for all state and side effects
3. Match the reference component's file naming, folder structure, and styling exactly
4. For all backend calls: implement using the exact pattern from the API-Layer-Audit.md 
   proposal — do not deviate or invent a different approach
5. Auth token handling must follow what is documented in the API-Layer-Audit.md
6. Preserve every business rule from the spec exactly — 
   do not simplify, omit, or alter behavior
7. Handle loading and error states as documented in the API-Layer-Audit.md proposal
8. Add this comment block at the top of the generated file:
   // Migrated from: [original AngularJS file path]
   // Spec: [spec file path]
   // Migration date: [today's date]
   // AngularJS pattern replaced: [Controller / Service / Directive]

After the component, list any assumptions made that were not in the spec.

---

Then generate a migration document in Markdown with these sections:

# Migration Document: [ComponentName] — AngularJS → React 18

## Overview
Source file, component type, complexity rating, migration date.

## What Changed
Bullet list of every AngularJS construct and its React equivalent.

## API & Backend Changes
How $http calls were migrated, auth handling, loading and error state approach.

## New File Location
Where the migrated file lives and why.

## Dependency Changes
| Removed (AngularJS) | Added (React) | Reason |

## Assumptions Made
Decisions made that were not explicitly in the spec.

## Manual Steps Required
Anything that could not be auto-migrated.

## Testing Recommendations
What to validate to confirm behavior matches the spec.
```

### Output
- Place the generated React component in `src/` following the proposed file path
- Save the migration document as `specs/[ComponentName].migration.md`

---

## Key Rules for Using Copilot in IntelliJ

| Rule | Why it matters |
|---|---|
| Always use `#file` to reference files | More precise than pasting code; respects context limits |
| One component per Copilot Chat session | Prevents context bleed between components |
| Type `continue` if output is truncated | Copilot will resume from where it stopped |
| Use `@workspace` sparingly | Useful for broad scans, but reduces precision for targeted prompts |
| Start a new session for each phase if in doubt | Keeps context clean and focused |

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

- [ ] Phase 0.5 — API-Layer-Audit.md exists and is reviewed *(first component only)*
- [ ] Phase 0 — `[ComponentName].spec.md` saved and reviewed
- [ ] Phase 1 — `[ComponentName].analysis.md` saved, risks reviewed
- [ ] Phase 2 — `[ComponentName].proposal.md` saved and confirmed
- [ ] Phase 3 — React component generated and placed in correct `src/` path
- [ ] Phase 3 — `[ComponentName].migration.md` saved
- [ ] Migrated component verified against the spec manually
- [ ] All backend calls tested against actual API endpoints
- [ ] Auth token handling confirmed working
- [ ] Loading and error states verified in the UI

---

*Runbook version 1.0 — AngularJS to React 18 — GitHub Copilot / IntelliJ*
