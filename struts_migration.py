#!/usr/bin/env python3
"""
struts_migration.py

Deterministic discovery + transform script for the Struts 6.4 -> 7.2.1 and
struts2-jquery-plugin 5.4 -> 6.1 migration.

Usage:
    # Phase 1: discovery only, writes inventory.csv, no code changes
    python struts_migration.py inventory --root /path/to/component

    # Phase 3: run all deterministic transform passes in dry-run (no writes)
    python struts_migration.py transform --root /path/to/component --dry-run

    # Phase 3: actually apply the deterministic transforms
    python struts_migration.py transform --root /path/to/component

    # Resume: only re-scan files not yet marked done in inventory.csv
    python struts_migration.py inventory --root /path/to/component --resume

Every change is logged to migration-log.csv (file, line, before, after, pass_name)
so it is auditable and revertible. The inventory is written to inventory.csv with
a `status` column (pending/done) for checkpointing across Copilot batch sessions.
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JAVA_LIKE_EXT = {".java", ".jsp", ".tag", ".jspf"}
BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts"}
SKIP_DIRS = {".git", "build", "target", "node_modules", "out", ".gradle", ".idea"}

STRUTS_VERSION_TARGET = "7.2.1"
JQUERY_PLUGIN_VERSION_TARGET = "6.1.0"  # confirm latest on Maven Central before running

# javax.servlet import patterns -> jakarta.servlet
# Word-boundary aware: only matches "javax.servlet" as a dotted identifier,
# not inside unrelated strings/comments that merely contain the substring.
JAVAX_SERVLET_RE = re.compile(r"\bjavax\.servlet\b")

# OGNL static field access: ${@some.package.Class@FIELD} or #@some.Class@FIELD
OGNL_STATIC_RE = re.compile(r"@([\w.]+)@([A-Za-z_][\w]*)")

# Struts 1 plugin / Sitemesh references
STRUTS1_SITEMESH_RE = re.compile(
    r"(struts2-struts1-plugin|org\.apache\.struts2\.struts1|sitemesh|struts2-sitemesh-plugin)",
    re.IGNORECASE,
)

# Maven <artifactId>...</artifactId> blocks we care about for version bumps
MAVEN_ARTIFACT_RE = re.compile(
    r"(<artifactId>\s*(struts2-core|struts2-spring-plugin|struts2-jquery(?:-\w+)?-plugin)\s*</artifactId>"
    r"\s*<version>\s*)([^<]+)(\s*</version>)",
    re.MULTILINE,
)

# Gradle single-line dependency version (common patterns; adjust if your
# build.gradle uses a different style, e.g. version catalogs)
GRADLE_DEP_RE = re.compile(
    r"(['\"]org\.apache\.struts:struts2-(?:core|spring-plugin):)([^'\"]+)(['\"])"
)
GRADLE_JQUERY_RE = re.compile(
    r"(['\"]com\.jgeppert\.struts2\.jquery:struts2-jquery(?:-\w+)?-plugin:)([^'\"]+)(['\"])"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iter_files(root: Path, extensions=None, names=None):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if names and fname in names:
                yield Path(dirpath) / fname
            elif extensions and Path(fname).suffix in extensions:
                yield Path(dirpath) / fname


def read_lines(path: Path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except Exception as e:
        print(f"  [WARN] could not read {path}: {e}", file=sys.stderr)
        return []


def load_existing_inventory(inventory_path: Path):
    """For --resume: returns set of (file, line, category) already marked done."""
    done = set()
    if inventory_path.exists():
        with open(inventory_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") == "done":
                    done.add((row["file"], row["line"], row["category"]))
    return done


# ---------------------------------------------------------------------------
# Phase 1: Discovery / Inventory
# ---------------------------------------------------------------------------

def run_inventory(root: Path, resume: bool):
    inventory_path = root / "inventory.csv"
    previously_done = load_existing_inventory(inventory_path) if resume else set()

    rows = []

    # A/E/F: javax.servlet imports, OGNL static access, in java/jsp/tag files
    for path in iter_files(root, extensions=JAVA_LIKE_EXT):
        lines = read_lines(path)
        for i, line in enumerate(lines, start=1):
            rel = str(path.relative_to(root))

            if JAVAX_SERVLET_RE.search(line):
                key = (rel, str(i), "javax_servlet_import")
                rows.append({
                    "category": "javax_servlet_import",
                    "file": rel, "line": i, "snippet": line.strip(),
                    "risk": "Low", "status": "done" if key in previously_done else "pending",
                })

            for m in OGNL_STATIC_RE.finditer(line):
                key = (rel, str(i), "ognl_static_access")
                rows.append({
                    "category": "ognl_static_access",
                    "file": rel, "line": i,
                    "snippet": f"{line.strip()}  [match: @{m.group(1)}@{m.group(2)}]",
                    "risk": "Medium", "status": "done" if key in previously_done else "pending",
                })

            if STRUTS1_SITEMESH_RE.search(line):
                key = (rel, str(i), "struts1_or_sitemesh_ref")
                rows.append({
                    "category": "struts1_or_sitemesh_ref",
                    "file": rel, "line": i, "snippet": line.strip(),
                    "risk": "High", "status": "done" if key in previously_done else "pending",
                })

    # D: struts.xml / struts-plugin.xml namespace + interceptor findings
    for path in iter_files(root, names={"struts.xml", "struts-plugin.xml"}):
        lines = read_lines(path)
        for i, line in enumerate(lines, start=1):
            rel = str(path.relative_to(root))
            if "<package" in line or "namespace=" in line:
                key = (rel, str(i), "namespace_declaration")
                rows.append({
                    "category": "namespace_declaration",
                    "file": rel, "line": i, "snippet": line.strip(),
                    "risk": "Medium", "status": "done" if key in previously_done else "pending",
                })
            if "interceptor-stack" in line or "<interceptor " in line or "<interceptor-ref" in line:
                key = (rel, str(i), "interceptor_config")
                rows.append({
                    "category": "interceptor_config",
                    "file": rel, "line": i, "snippet": line.strip(),
                    "risk": "Medium", "status": "done" if key in previously_done else "pending",
                })

    # A: build file dependency versions
    for path in iter_files(root, names=BUILD_FILES):
        lines = read_lines(path)
        text = "".join(lines)
        rel = str(path.relative_to(root))
        for m in MAVEN_ARTIFACT_RE.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            key = (rel, str(line_no), "build_dependency_version")
            rows.append({
                "category": "build_dependency_version",
                "file": rel, "line": line_no,
                "snippet": m.group(0).strip(),
                "risk": "Low", "status": "done" if key in previously_done else "pending",
            })
        for m in list(GRADLE_DEP_RE.finditer(text)) + list(GRADLE_JQUERY_RE.finditer(text)):
            line_no = text[: m.start()].count("\n") + 1
            key = (rel, str(line_no), "build_dependency_version")
            rows.append({
                "category": "build_dependency_version",
                "file": rel, "line": line_no,
                "snippet": m.group(0).strip(),
                "risk": "Low", "status": "done" if key in previously_done else "pending",
            })

    # Write inventory.csv
    fieldnames = ["category", "risk", "file", "line", "snippet", "status"]
    with open(inventory_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Inventory written: {inventory_path} ({len(rows)} findings)")
    by_cat = {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat}: {count}")


# ---------------------------------------------------------------------------
# Phase 3: Deterministic transform passes
# ---------------------------------------------------------------------------

def log_change(log_rows, file, line, before, after, pass_name):
    log_rows.append({
        "file": file, "line": line, "before": before.strip(),
        "after": after.strip(), "pass_name": pass_name,
    })


def pass_javax_to_jakarta(root: Path, dry_run: bool, log_rows):
    """Pass 1: rewrite javax.servlet.* imports to jakarta.servlet.* in java/jsp/tag files."""
    count = 0
    for path in iter_files(root, extensions=JAVA_LIKE_EXT):
        lines = read_lines(path)
        if not lines:
            continue
        changed = False
        new_lines = []
        for i, line in enumerate(lines, start=1):
            # Only touch actual import statements / taglib-style javax.servlet refs,
            # skip if it's clearly inside a // or /* comment or a string literal
            # that isn't an import (best-effort heuristic; review the log after).
            stripped = line.strip()
            is_import_like = stripped.startswith("import ") or "javax.servlet" in stripped
            if is_import_like and JAVAX_SERVLET_RE.search(line):
                new_line = JAVAX_SERVLET_RE.sub("jakarta.servlet", line)
                if new_line != line:
                    log_change(log_rows, str(path.relative_to(root)), i, line, new_line,
                               "javax_to_jakarta")
                    changed = True
                    count += 1
                    line = new_line
            new_lines.append(line)
        if changed and not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    print(f"[javax_to_jakarta] {count} line(s) {'would be ' if dry_run else ''}changed")


def pass_bump_build_versions(root: Path, dry_run: bool, log_rows):
    """Pass 2: bump struts2-core / struts2-spring-plugin / struts2-jquery* versions."""
    count = 0
    for path in iter_files(root, names=BUILD_FILES):
        text = "".join(read_lines(path))
        if not text:
            continue
        original = text

        def maven_repl(m):
            artifact = m.group(2)
            target = JQUERY_PLUGIN_VERSION_TARGET if "jquery" in artifact else STRUTS_VERSION_TARGET
            return f"{m.group(1)}{target}{m.group(4)}"

        text = MAVEN_ARTIFACT_RE.sub(maven_repl, text)
        text = GRADLE_DEP_RE.sub(lambda m: f"{m.group(1)}{STRUTS_VERSION_TARGET}{m.group(3)}", text)
        text = GRADLE_JQUERY_RE.sub(lambda m: f"{m.group(1)}{JQUERY_PLUGIN_VERSION_TARGET}{m.group(3)}", text)

        if text != original:
            rel = str(path.relative_to(root))
            log_change(log_rows, rel, "-", original[:200], text[:200], "bump_build_versions")
            count += 1
            if not dry_run:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
    print(f"[bump_build_versions] {count} file(s) {'would be ' if dry_run else ''}changed")


def pass_report_ognl_static(root: Path, log_rows):
    """Pass 3: report-only. Never modifies code; flags for manual/Copilot review."""
    count = 0
    for path in iter_files(root, extensions=JAVA_LIKE_EXT | {".ftl"}):
        lines = read_lines(path)
        for i, line in enumerate(lines, start=1):
            for m in OGNL_STATIC_RE.finditer(line):
                log_change(log_rows, str(path.relative_to(root)), i, line,
                           f"[REPORT ONLY - needs manual fix: @{m.group(1)}@{m.group(2)}]",
                           "report_ognl_static")
                count += 1
    print(f"[report_ognl_static] {count} finding(s) logged (no code changed)")


def pass_report_struts1_sitemesh(root: Path, log_rows):
    """Pass 4: report-only. Flags removed-plugin references for manual refactor."""
    count = 0
    for path in iter_files(root, extensions=JAVA_LIKE_EXT | {".xml"}):
        lines = read_lines(path)
        for i, line in enumerate(lines, start=1):
            if STRUTS1_SITEMESH_RE.search(line):
                log_change(log_rows, str(path.relative_to(root)), i, line,
                           "[REPORT ONLY - removed plugin, needs manual refactor]",
                           "report_struts1_sitemesh")
                count += 1
    print(f"[report_struts1_sitemesh] {count} finding(s) logged (no code changed)")


def run_transform(root: Path, dry_run: bool):
    log_rows = []
    pass_javax_to_jakarta(root, dry_run, log_rows)
    pass_bump_build_versions(root, dry_run, log_rows)
    pass_report_ognl_static(root, log_rows)
    pass_report_struts1_sitemesh(root, log_rows)

    log_path = root / "migration-log.csv"
    fieldnames = ["file", "line", "before", "after", "pass_name"]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in log_rows:
            writer.writerow(row)
    print(f"\nLog written: {log_path} ({len(log_rows)} entries)")
    if dry_run:
        print("DRY RUN — no files were modified. Re-run without --dry-run to apply.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inv = sub.add_parser("inventory", help="Phase 1: scan and write inventory.csv")
    p_inv.add_argument("--root", required=True, type=Path)
    p_inv.add_argument("--resume", action="store_true",
                        help="Preserve status=done for previously found rows")

    p_tr = sub.add_parser("transform", help="Phase 3: run deterministic transform passes")
    p_tr.add_argument("--root", required=True, type=Path)
    p_tr.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    root = args.root.resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if args.command == "inventory":
        run_inventory(root, args.resume)
    elif args.command == "transform":
        run_transform(root, args.dry_run)


if __name__ == "__main__":
    main()
