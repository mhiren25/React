"""
llm/handoff.py — IntelliJ Copilot Chat handoff file generator.

After all mechanical transforms are applied, this module:
  1. Scans for remaining LLM-needed blocks (Criteria, UserType)
  2. Inserts TODO[hibernate-migration] comments inline in the Java files
  3. Generates a single markdown handoff file listing every task,
     the exact Copilot Chat prompt to use, and the code block to migrate —
     ready to open in IntelliJ and work through top to bottom.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from utils.files import find_java_files, read_file, write_file


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class HandoffTask:
    kind: str           # "CRITERIA" | "USERTYPE"
    file_rel: str       # relative path from module root
    line_start: int     # 1-based line number in file
    description: str    # human label
    prompt: str         # exact prompt to paste into Copilot Chat
    code_block: str     # the code to migrate


# ── Criteria detection + extraction ───────────────────────────────────────────

CRITERIA_SIGNALS = [
    "import org.hibernate.Criteria;",
    "import org.hibernate.criterion.Restrictions;",
    "import org.hibernate.criterion.Projections;",
    "import org.hibernate.criterion.Order;",
    "import org.hibernate.criterion.Criterion;",
    "createCriteria(",
    "Restrictions.",
    "Projections.",
]

CRITERIA_USAGE = ["createCriteria(", "Restrictions.", "Projections."]


def _has_criteria(content: str) -> bool:
    return any(p in content for p in CRITERIA_SIGNALS)


def _extract_methods_with_criteria(content: str) -> list[tuple[int, int, str]]:
    """
    Extract (start_line_0based, end_line_0based, method_text) for every
    method body that contains Criteria API usage.
    Uses simple brace-depth matching — good enough for well-formatted Java.
    """
    results = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.search(r"\b(public|private|protected)\b.*\{", line):
            depth = line.count("{") - line.count("}")
            start = i
            j = i + 1
            while j < len(lines) and depth > 0:
                depth += lines[j].count("{") - lines[j].count("}")
                j += 1
            method_text = "\n".join(lines[start:j])
            if any(p in method_text for p in CRITERIA_USAGE):
                results.append((start, j, method_text))
            i = j
        else:
            i += 1
    return results


def _criteria_prompt(method_text: str) -> str:
    return (
        "Migrate this Hibernate 5 Criteria API Java method to Hibernate 7 CriteriaBuilder.\n\n"
        "Context:\n"
        "- Pure Hibernate native API — no JPA, no Spring, no EntityManager\n"
        "- Use session.getCriteriaBuilder() and keep the existing session variable name\n"
        "- Database is Oracle\n"
        "- Use org.hibernate.query.criteria imports\n\n"
        "Rules:\n"
        "- Migrate only this method — do not change surrounding code\n"
        "- Preserve all variable names, especially the result list variable\n"
        "- Output ONLY the migrated method — no explanation, no markdown fences\n"
        "- Add a // TODO comment for any Restriction with no direct CriteriaBuilder equivalent\n\n"
        "Method to migrate:\n"
        "```java\n"
        f"{method_text}\n"
        "```"
    )


# ── UserType detection ────────────────────────────────────────────────────────

def _has_usertype(content: str) -> bool:
    return (
        "implements UserType" in content
        or "implements CompositeUserType" in content
        or "import org.hibernate.usertype.UserType" in content
    )


def _usertype_prompt(class_source: str) -> str:
    return (
        "Migrate this Hibernate 5 UserType implementation to the Hibernate 7 UserType<T> generic interface.\n\n"
        "Key interface changes in Hibernate 7:\n"
        "- `nullSafeGet` signature: `(ResultSet rs, int position, SharedSessionContractImplementor session, Object owner)`\n"
        "- `nullSafeSet` signature: `(PreparedStatement st, T value, int index, SharedSessionContractImplementor session)`\n"
        "- `sqlTypes()` returning `int[]` is replaced by `getSqlType()` returning a single `int`\n"
        "- `returnedClass()` now returns `Class<T>` (typed)\n"
        "- `SessionImplementor` is replaced by `SharedSessionContractImplementor`\n\n"
        "Rules:\n"
        "- Preserve the exact type conversion logic — do not change the behaviour\n"
        "- Do not change the class name\n"
        "- Pure Hibernate, no JPA, no Spring\n"
        "- Output ONLY the migrated class — no explanation, no markdown fences\n\n"
        "Class to migrate:\n"
        "```java\n"
        f"{class_source}\n"
        "```"
    )


# ── TODO comment injection ────────────────────────────────────────────────────

_TODO_CRITERIA = (
    "// TODO[hibernate-migration][CRITERIA] Migrate this method to CriteriaBuilder.\n"
    "// Open COPILOT-HANDOFF.md in IntelliJ, find this task, paste the prompt into Copilot Chat.\n"
)

_TODO_USERTYPE = (
    "// TODO[hibernate-migration][USERTYPE] Migrate this class to Hibernate 7 UserType<T>.\n"
    "// Open COPILOT-HANDOFF.md in IntelliJ, find this task, paste the prompt into Copilot Chat.\n"
)


def _insert_todo_before_line(content: str, line_idx: int, todo: str) -> str:
    """Insert a TODO comment before the given 0-based line index."""
    lines = content.split("\n")
    lines.insert(line_idx, todo.rstrip("\n"))
    return "\n".join(lines)


# ── Main scan + generate ──────────────────────────────────────────────────────

def generate(
    module_path: Path,
    dry_run: bool,
    console,
    extra_tasks: list[dict] | None = None,
) -> tuple[int, Path | None]:
    """
    Scan module for Criteria and UserType blocks needing Copilot.
    Accepts extra_tasks from other transforms (e.g. c3p0 AbstractConnectionCustomizer).
    - Inserts TODO comments inline in Java files
    - Generates COPILOT-HANDOFF.md in the module root
    Returns (task_count, handoff_file_path).
    """
    tasks: list[HandoffTask] = []
    java_files = find_java_files(module_path)
    todo_offset_map: dict[Path, int] = {}

    # ── Inject extra tasks from other transforms first ────────────────────────
    for t in (extra_tasks or []):
        tasks.append(HandoffTask(
            kind=t["kind"],
            file_rel=t["file_rel"],
            line_start=t["line_start"],
            description=t["description"],
            prompt=t["prompt"],
            code_block=t["code_block"],
        ))  # tracks line offset from insertions

    # ── Criteria tasks ────────────────────────────────────────────────────────
    criteria_files = [f for f in java_files if _has_criteria(read_file(f))]

    for java_file in criteria_files:
        original = read_file(java_file)
        content = original
        rel = str(java_file.relative_to(module_path))
        offset = todo_offset_map.get(java_file, 0)
        methods = _extract_methods_with_criteria(original)

        if not methods:
            console.warn(f"{rel}: Criteria imports found but no method extracted — check manually")
            continue

        for start_0, _end, method_text in methods:
            task_num = len(tasks) + 1
            display_line = start_0 + 1 + offset

            task = HandoffTask(
                kind="CRITERIA",
                file_rel=rel,
                line_start=display_line,
                description=f"Criteria API method at line {display_line}",
                prompt=_criteria_prompt(method_text),
                code_block=method_text,
            )
            tasks.append(task)
            console.info(f"  [Task {task_num}] CRITERIA  {rel}:{display_line}")

            # Insert TODO comment inline in file
            todo = f"    {_TODO_CRITERIA.strip()}\n"
            content = _insert_todo_before_line(content, start_0 + offset, todo)
            offset += 1  # account for the inserted line

        todo_offset_map[java_file] = offset
        if not dry_run and content != original:
            write_file(java_file, content)

    # ── UserType tasks ────────────────────────────────────────────────────────
    usertype_files = [f for f in java_files if _has_usertype(read_file(f))]

    for java_file in usertype_files:
        original = read_file(java_file)
        rel = str(java_file.relative_to(module_path))
        task_num = len(tasks) + 1

        task = HandoffTask(
            kind="USERTYPE",
            file_rel=rel,
            line_start=1,
            description=f"UserType implementation — full class",
            prompt=_usertype_prompt(original),
            code_block=original,
        )
        tasks.append(task)
        console.info(f"  [Task {task_num}] USERTYPE  {rel}")

        # Insert TODO at top of file (after package declaration if present)
        content = original
        lines = content.split("\n")
        insert_at = 0
        for idx, line in enumerate(lines):
            if line.strip().startswith("package "):
                insert_at = idx + 1
                break
        todo = _TODO_USERTYPE.rstrip("\n")
        lines.insert(insert_at, todo)
        content = "\n".join(lines)

        if not dry_run and content != original:
            write_file(java_file, content)

    # ── Write handoff markdown ────────────────────────────────────────────────
    # NOTE: early-exit check is AFTER extra_tasks are injected (lines above)
    # so that Spring-orm / NativeQuery / c3p0 tasks still produce the file
    # even when there are no Criteria or UserType blocks in this module.
    if not tasks:
        console.skip("No handoff tasks found — COPILOT-HANDOFF.md not written")
        return 0, None

    handoff_path = module_path / "COPILOT-HANDOFF.md"
    handoff_content = _build_handoff_md(module_path.name, tasks)

    if not dry_run:
        write_file(handoff_path, handoff_content)
        console.success(f"Handoff file written: COPILOT-HANDOFF.md ({len(tasks)} task(s))")
    else:
        console.dry(f"Would write COPILOT-HANDOFF.md with {len(tasks)} task(s)")

    return len(tasks), handoff_path if not dry_run else None


# ── Markdown builder ──────────────────────────────────────────────────────────

def _build_handoff_md(module_name: str, tasks: list[HandoffTask]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    criteria_tasks = [t for t in tasks if t.kind == "CRITERIA"]
    usertype_tasks = [t for t in tasks if t.kind == "USERTYPE"]
    c3p0_tasks = [t for t in tasks if t.kind == "C3P0-CUSTOMIZER"]
    nq_tasks = [t for t in tasks if t.kind == "NATIVE-QUERY"]
    spring_tasks = [t for t in tasks if t.kind == "SPRING-ORM"]

    lines = [
        f"# Copilot Chat Handoff — `{module_name}`",
        f"",
        f"Generated: {now}  ",
        f"Total tasks: **{len(tasks)}** "
        f"({len(criteria_tasks)} Criteria, {len(usertype_tasks)} UserType, "
        f"{len(nq_tasks)} NativeQuery, {len(c3p0_tasks)} c3p0, "
        f"{len(spring_tasks)} Spring-orm)",
        f"",
        f"## How to use this file",
        f"",
        f"1. Open this file in IntelliJ alongside the Java file listed in each task",
        f"2. Open **GitHub Copilot Chat** panel (View → Tool Windows → GitHub Copilot)",
        f"3. Navigate to the Java file and line number shown in each task",
        f"4. Copy the prompt from the task into Copilot Chat",
        f"5. Review the suggestion, apply it to the file",
        f"6. Delete the `TODO[hibernate-migration]` comment from the Java file",
        f"7. Check the box below when done",
        f"",
        f"---",
        f"",
        f"## Task List",
        f"",
    ]

    # Quick checklist at the top
    for i, task in enumerate(tasks, 1):
        lines.append(f"- [ ] **Task {i}** — {task.kind} — `{task.file_rel}` line {task.line_start}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Full task details
    for i, task in enumerate(tasks, 1):
        lines += [
            f"## Task {i} — {task.kind}",
            f"",
            f"**File:** `{task.file_rel}`  ",
            f"**Line:** {task.line_start}  ",
            f"**What:** {task.description}",
            f"",
            f"### Step 1 — Open the file in IntelliJ",
            f"",
            f"Navigate to `{task.file_rel}` at line {task.line_start}.",
            f"Look for the `TODO[hibernate-migration][{task.kind}]` comment.",
            f"",
            f"### Step 2 — Paste this prompt into Copilot Chat",
            f"",
            f"```",
            task.prompt,
            f"```",
            f"",
            f"### Step 3 — Current code (for reference)",
            f"",
            f"```java",
            task.code_block,
            f"```",
            f"",
            f"### Step 4 — After applying",
            f"",
            f"- [ ] Applied Copilot suggestion to the file",
            f"- [ ] Deleted the `TODO[hibernate-migration]` comment",
            f"- [ ] Verified file still makes sense (spot-check logic)",
            f"",
            f"---",
            f"",
        ]

    # Footer
    lines += [
        f"## After completing all tasks",
        f"",
        f"Run the compile check from the module root:",
        f"",
        f"```bash",
        f"./gradlew compileJava",
        f"```",
        f"",
        f"Then verify no TODOs remain:",
        f"",
        f"```bash",
        f"grep -rn \"TODO\\[hibernate-migration\\]\" src/",
        f"```",
        f"",
        f"Then commit:",
        f"",
        f"```bash",
        f"git add -A && git commit -m \"chore(hibernate-migration): complete LLM rewrites for {module_name}\"",
        f"```",
    ]

    return "\n".join(lines) + "\n"
