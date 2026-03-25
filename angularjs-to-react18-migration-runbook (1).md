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
- [ ] `specs/` folder created at the root of your AngularJS project
- [ ] `react-reference/` snapshot folder created (see setup below — do this once before Phase 0.5)

> **Do NOT open the full-stack React/Java project in IntelliJ.**  
> Copilot will index the entire workspace including all Java files and cause timeouts.  
> Use the `react-reference/` snapshot folder instead — it contains only what Copilot needs.

---

## Folder Structure

Maintain this structure throughout the migration:

```
your-angularjs-project/
├── react-reference/                    ← ONE-TIME SETUP (see below)
│   ├── package.json                    ← copied from React project frontend folder
│   └── folder-structure.md            ← manually written folder tree (see below)
├── specs/
│   ├── API-Layer-Audit.md              ← Phase 0.5 (run once for whole app)
│   ├── [ComponentName].spec.md         ← Phase 0  (per component)
│   ├── [ComponentName].analysis.md     ← Phase 1  (per component)
│   ├── [ComponentName].proposal.md     ← Phase 2  (per component)
│   └── [ComponentName].migration.md    ← Phase 3  (per component)
├── src/                                ← migrated React files live here
```

---

## One-Time Setup — React Reference Snapshot

> **Do this once before starting Phase 0.5.**  
> This replaces all references to the full-stack React/Java project and prevents Copilot from scanning Java files.

### Step 1 — Create the snapshot folder
Inside your AngularJS project root, create:
```
react-reference/
```

### Step 2 — Copy only `package.json`
From your full-stack project, locate the **frontend** `package.json`. It will be in one of these locations:

```
frontend/package.json
src/main/frontend/package.json
client/package.json
webapp/package.json
```

Copy just that file into `react-reference/package.json`.  
Do not copy `pom.xml`, root-level `package.json`, or any other file.

### Step 3 — Create `folder-structure.md`
Manually write a short Markdown file describing only the React frontend folder layout. Keep it to folders that matter for component organisation. Example:

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

Adjust the tree to match your actual React project. This tells Copilot where to place migrated files — get it right once and every phase benefits.

### Step 4 — Verify
Your `react-reference/` folder should contain exactly two files:
```
react-reference/
├── package.json
└── folder-structure.md
```

Nothing else. From this point forward, every prompt in this runbook that references the React project uses `#file:react-reference/package.json` or `#file:react-reference/folder-structure.md` — **never** the actual Java/React project.

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
> **Why split:** IntelliJ Copilot has a short timeout — one large audit prompt will fail. Instead run 4 small focused prompts and manually stitch the outputs into a single `API-Layer-Audit.md` file.

---

### Prompt A — Interceptors
> **File to open:** `app.js` or your main Angular module file

```
You are a backend integration analyst. Scan #file only.

Find every instance of $httpProvider.interceptors.

For each interceptor found document:
- What it does (auth token injection, error handling, request transform, etc.)
- Exact headers or tokens it adds or reads
- Any redirect or retry logic

If none are found, write: "No interceptors detected"

Output Markdown only. No explanations, no preamble.
```

Save output as Section 1 of `specs/API-Layer-Audit.md`

---

### Prompt B — All $http Calls
> **File to open:** One service or controller file at a time  
> **Repeat this prompt for each file — do not open multiple files at once**

```
You are a backend integration analyst. Scan #file only.

List every unique $http call found in this file using this exact table format:
| Method | Endpoint | Called From | Request Payload | Response Shape | Error Handling |

If no $http calls exist in this file, write: "No $http calls in this file"

Output the table only. No explanations, no preamble.
```

Run this once per file. Paste all table outputs together as Section 2 of `specs/API-Layer-Audit.md`

---

### Prompt C — Auth & Error Handling
> **File to open:** Your main Angular module or auth service file

```
You are a backend integration analyst. Scan #file only and answer these 
four questions in Markdown. Keep each answer to bullet points, no prose.

1. Auth mechanism
   - How is the user authenticated? (JWT, cookie, session, etc.)
   - Where is the token stored? ($localStorage, $sessionStorage, cookie, memory)
   - How is it attached to requests?
   - What happens on 401 or session expiry?

2. Shared API services
   - Which services wrap $http and get injected into multiple controllers?
   - Which controllers depend on each?

3. Error handling strategy
   - Is error handling global (interceptor) or per-call?
   - What happens on error? (toast, redirect, silent fail, etc.)
   - Are there retry mechanisms?

4. Loading state
   - How does the app signal loading to the UI?

Output Markdown only. No preamble.
```

Save output as Sections 3–6 of `specs/API-Layer-Audit.md`

---

### Prompt D — React Equivalent Proposal
> **Files to open:** `react-reference/package.json` and `react-reference/folder-structure.md` only  
> **Before running:** Paste your collected Sections 1–6 output directly into this prompt

```
You are a React 18 architect. 

Here is the API audit I have collected from the AngularJS app:

[PASTE YOUR SECTIONS 1-6 OUTPUT HERE]

Using only #file:react-reference/package.json and #file:react-reference/folder-structure.md,
propose the following based strictly on what is already in the reference project:

1. Data-fetching approach to adopt (based on dependencies in package.json only)
2. How to replicate any interceptor behavior in React
3. Where auth token logic should live (based on folder-structure.md conventions)
4. Whether a central API service file is needed and where it should live
5. How loading and error state will be handled consistently

Do not read any other files. Do not scan the workspace.
Output Markdown only. No code. No preamble.
```

Save output as Section 7 of `specs/API-Layer-Audit.md`

---

### Final Step — Assemble the Audit File

Combine all four outputs into `specs/API-Layer-Audit.md` using this structure:

```
# API Layer Audit

## Section 1 — HTTP Interceptors
[Prompt A output]

## Section 2 — All Backend Calls
[Prompt B output — all tables combined]

## Section 3 — Auth Mechanism
[Prompt C output — question 1]

## Section 4 — Shared API Services
[Prompt C output — question 2]

## Section 5 — Error Handling Strategy
[Prompt C output — question 3]

## Section 6 — Loading State Management
[Prompt C output — question 4]

## Section 7 — Proposed React Equivalent
[Prompt D output]
```

> **Review before proceeding** — confirm every endpoint, auth mechanism, and the proposed React pattern.  
> This file is the **single source of truth** for all API calls across the migration.

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
> **Files to open:** Spec + Analysis + API-Layer-Audit + `react-reference/package.json` + `react-reference/folder-structure.md`

### Steps
1. Open the five files via `#file` — use only the snapshot files, not the actual React project
2. Run the prompt below
3. **Do not proceed to Phase 3 until you have reviewed and confirmed this proposal**

### Prompt

```
You are a React 18 architect. Using:
- Approved spec: #file
- Analysis report: #file
- API Layer Audit: #file
- React reference package.json: #file:react-reference/package.json
- React reference folder structure: #file:react-reference/folder-structure.md

Do not read any other files. Do not scan the workspace.

Propose the following. No code yet.

### 1. Target File Path
Where should the migrated React file live?
Base this strictly on the conventions in react-reference/folder-structure.md.

### 2. Dependencies Needed
| Package | Version | Replaces | dep / devDep |
- Match React version from react-reference/package.json exactly
- For data-fetching: use only what is already in react-reference/package.json
- Do not introduce new libraries unless nothing in package.json covers the need

### 3. Component Hierarchy
Simple tree of any sub-components to be split out from this one.

### 4. API Integration Plan
Based on the API-Layer-Audit.md proposal:
- Which API calls does this component own?
- Should they live in this component, a custom hook, or a shared API service?
- How will loading and error state be surfaced in the UI?

### 5. State & Data Flow Plan
Plain English description of how state will be managed,
based strictly on the dependencies already in react-reference/package.json.

Output in Markdown. No code.
Confirm with me before proceeding to Phase 3.
```

### Output
- Save as `specs/[ComponentName].proposal.md`
- Type `Confirmed, proceed to Phase 3` in Copilot Chat only when satisfied
- Pay special attention to the dependency list and file path — changes here are free, changes after code is written are not

---

## Phase 3 — Code Generation & Migration Document
> **Frequency:** Once per component, after explicit confirmation  
> **Files to open:** Spec + Proposal + API-Layer-Audit + `react-reference/package.json` + `react-reference/folder-structure.md`

### Steps
1. Confirm Phase 2 proposal in chat before running this prompt
2. Open the five files via `#file` — snapshot files only, not the actual React project
3. Run the prompt below

### Prompt

```
You are a React 18 engineer. Using:
- Approved spec: #file
- Migration proposal: #file
- API Layer Audit: #file
- React reference package.json: #file:react-reference/package.json
- React reference folder structure: #file:react-reference/folder-structure.md

Do not read any other files. Do not scan the workspace.

Generate the fully migrated React 18 component. Follow these rules strictly:

1. Functional components only — no class components
2. Hooks for all state and side effects
3. Place the file at the exact path proposed in the migration proposal
4. Use the folder conventions from react-reference/folder-structure.md
5. Use only packages present in react-reference/package.json
6. For all backend calls: implement using the exact pattern from the API-Layer-Audit.md 
   proposal — do not deviate or invent a different approach
7. Auth token handling must follow what is documented in the API-Layer-Audit.md
8. Preserve every business rule from the spec exactly — 
   do not simplify, omit, or alter behavior
9. Handle loading and error states as documented in the API-Layer-Audit.md proposal
10. Add this comment block at the top of the generated file:
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
| One file per `#file` reference | Opening too many files at once is the main cause of timeouts |
| One component per Copilot Chat session | Prevents context bleed between components |
| Keep prompts focused on one task only | Multi-task prompts time out — split them like Phase 0.5 |
| Type `continue` if output is truncated | Copilot will resume from where it stopped |
| Use `@workspace` sparingly | Useful for broad scans, but reduces precision and increases timeout risk |
| Start a new session for each phase if in doubt | Keeps context clean and avoids accumulated token bloat |
| Paste collected output into Prompt D manually | Avoids re-opening multiple files which triggers timeouts |

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

*Runbook version 1.2 — AngularJS to React 18 — GitHub Copilot / IntelliJ (timeout-safe, snapshot-isolated)*
