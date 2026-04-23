#!/usr/bin/env python3
"""
prepare_copilot_prompt.py — COSTA KB Generator (Copilot Agent Mode)
====================================================================
Greps your test project for a given feature, builds a focused prompt
with explicit file references, and copies it to your clipboard.

You then paste it directly into GitHub Copilot Chat (VS Code or IntelliJ).
Copilot agent reads only the referenced files — no timeout, no full scan.

USAGE
─────
  # Discover what features exist in your project
  python scripts/prepare_copilot_prompt.py --list

  # Generate and copy prompt for a feature
  python scripts/prepare_copilot_prompt.py --feature blocking
  python scripts/prepare_copilot_prompt.py --feature blocking --gui "Topaz OMS"
  python scripts/prepare_copilot_prompt.py --feature etd-orders --grep-extra buy_to_open etd_call

  # After Copilot writes docs/kb/blocking.md, validate it was written:
  python scripts/prepare_copilot_prompt.py --feature blocking --verify

HOW IT WORKS
────────────
  1. Script greps test files for feature-related terms
  2. Builds a Copilot agent prompt with:
       - Explicit #file: references for VS Code agent mode
       - Full relative paths for IntelliJ Copilot Chat
       - Tight extraction instructions (no full project scan)
       - Direct instruction to WRITE docs/kb/<feature>.md
  3. Copies prompt to clipboard
  4. You paste into Copilot Chat and press Enter
  5. Copilot agent reads only referenced files, writes the KB doc

COPILOT CHAT TIPS
─────────────────
  VS Code   : Make sure you are in Agent mode (not Ask or Edit).
              The prompt uses #file: references which agent mode resolves.
  IntelliJ  : Use Copilot Chat panel. Paste prompt as-is.
              File paths are relative to project root.
  Both      : If Copilot asks "should I create the file?" — say Yes.
              If it times out, re-run with --max-files 2
"""

import os
import re
import sys
import argparse
import textwrap
import subprocess
from pathlib import Path
from datetime import date
from collections import defaultdict


# ── Configuration (edit these to match your project layout) ──────────────────

TESTS_DIR   = "tests"           # Root folder of your .py test files
CONFIG_DIRS = ["config", "resources", "testdata"]  # XML/config folders
KB_DIR      = "docs/kb"         # Where KB docs should be written

# Max files included per prompt. Keep low to avoid Copilot timeout.
DEFAULT_MAX_FILES = 5

# Max lines read from each file before truncating
MAX_LINES_PER_FILE = 150

# Extra terms automatically added to grep for each feature slug
# Extend this as you learn your project's naming conventions
FEATURE_SYNONYMS: dict[str, list[str]] = {
    "blocking":   ["block_order", "manual_block", "add_to_block", "BlockOrder", "Blocking"],
    "etd-orders": ["etd_order", "buy_to_open", "ETDOrder", "place_etd", "etd_call"],
    "allocation": ["allocation_mode", "avg_price", "alloc_mode", "AllocationMode"],
    "fill":       ["fill_order", "order_fill", "FillOrder", "filled", "ExecutionReport"],
}


# ── File discovery ─────────────────────────────────────────────────────────────

def find_test_files(tests_dir: str) -> list[Path]:
    root = Path(tests_dir)
    if not root.exists():
        print(f"[ERROR] Tests directory not found: '{tests_dir}'")
        print(f"        Set TESTS_DIR in the script or use --tests-dir")
        sys.exit(1)
    return sorted(root.rglob("test_*.py")) + sorted(root.rglob("*_test.py"))


def grep_files(files: list[Path], terms: list[str]) -> list[Path]:
    """Return files containing ANY of the search terms (case-insensitive)."""
    if not terms:
        return []
    pattern = re.compile(
        "|".join(re.escape(t) for t in terms), re.IGNORECASE
    )
    matched = []
    for f in files:
        try:
            if pattern.search(f.read_text(encoding="utf-8", errors="ignore")):
                matched.append(f)
        except Exception:
            pass
    return matched


def find_xml_companion(py_path: Path) -> Path | None:
    """Look for an XML data file paired with the given .py test file."""
    stem = py_path.stem  # e.g. test_etd_block
    candidates = [py_path.parent / f"{stem}.xml"]
    for d in CONFIG_DIRS:
        p = Path(d)
        candidates += [
            p / f"{stem}.xml",
            p / f"{stem.removeprefix('test_')}.xml",
        ]
    return next((c for c in candidates if c.exists()), None)


# ── Feature/GUI discovery (for --list) ────────────────────────────────────────

def discover_features_and_guis(files: list[Path]) -> tuple[dict, dict]:
    features: dict[str, list[Path]] = defaultdict(list)
    guis:     dict[str, list[Path]] = defaultdict(list)

    feat_re    = re.compile(r"[Ff]eatures?\s*:\s*\[([^\]]+)\]")
    gui_re     = re.compile(r"[Gg][Uu][Ii]s?\s*:\s*\[([^\]]+)\]")
    systems_re = re.compile(r"[Ss]ystems?\s+involved\s*:((?:\s*-\s*.+)+)")
    class_re   = re.compile(r"^class\s+Test(\w+)\s*[:(]", re.MULTILINE)

    def slugify(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")

        for m in feat_re.finditer(text):
            for item in m.group(1).split(","):
                slug = slugify(item.strip())
                if slug:
                    features[slug].append(f)

        for m in gui_re.finditer(text):
            for item in m.group(1).split(","):
                name = item.strip().strip("\"'")
                if name:
                    guis[name].append(f)

        m = systems_re.search(text)
        if m:
            for line in m.group(1).splitlines():
                name = re.sub(r"^\s*-\s*", "", line).strip()
                if name:
                    guis[name].append(f)

        # Fallback: CamelCase class names → feature slugs
        if not feat_re.search(text):
            for m in class_re.finditer(text):
                slug = slugify(
                    re.sub(r"([A-Z])", r" \1", m.group(1)).strip()
                )
                if slug:
                    features[slug].append(f)

    return dict(features), dict(guis)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def read_truncated(path: Path, max_lines: int = MAX_LINES_PER_FILE) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        return f"# [ERROR reading {path}: {e}]"
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + (
        f"\n# ... [TRUNCATED — {len(lines) - max_lines} more lines in {path}]"
    )


def file_ref(path: Path, ide: str) -> str:
    """Format a file reference for the target IDE."""
    rel = str(path)
    if ide == "vscode":
        return f"#file:{rel}"
    else:  # intellij — just the path, Copilot Chat resolves it
        return rel


def build_prompt(
    feature:      str,
    matched_files: list[Path],
    gui_filter:   str | None,
    ide:          str,
    max_files:    int,
    inline_code:  bool,
) -> str:
    """
    Build the full Copilot agent prompt.

    Strategy:
      - Reference files explicitly so Copilot agent reads only them
      - Embed truncated code inline as fallback (if inline_code=True)
      - Give Copilot a precise output contract so it writes the file directly
      - Keep total prompt short enough to avoid timeout
    """

    slug     = re.sub(r"[^a-z0-9]+", "-", feature.lower()).strip("-")
    today    = date.today().isoformat()
    out_path = f"{KB_DIR}/{slug}.md"

    # Limit files and note if truncated
    total_found = len(matched_files)
    files = matched_files[:max_files]
    truncation_note = (
        f"\n> NOTE: {total_found - max_files} more matching files were found "
        f"but excluded to keep this prompt focused. Re-run with "
        f"`--max-files {min(total_found, max_files + 3)}` to include more.\n"
        if total_found > max_files else ""
    )

    gui_scope = (
        f"\n**Scope:** Extract information for GUI **{gui_filter}** only. "
        f"Ignore actions/wrappers from other GUIs.\n"
        if gui_filter else
        "\n**Scope:** Extract information for ALL GUIs found in these files.\n"
    )

    # File references block
    file_refs = "\n".join(file_ref(f, ide) for f in files)

    # Companion XML files
    xml_companions = []
    for f in files:
        xml = find_xml_companion(f)
        if xml:
            xml_companions.append(xml)
    xml_refs = (
        "\n**Test data files (XML):**\n" +
        "\n".join(file_ref(x, ide) for x in xml_companions)
        if xml_companions else ""
    )

    # Optional inline code blocks (for IntelliJ or when file refs don't resolve)
    inline_blocks = ""
    if inline_code:
        blocks = []
        for f in files:
            code = read_truncated(f)
            blocks.append(f"### {f}\n```python\n{code}\n```")
            xml = find_xml_companion(f)
            if xml:
                blocks.append(
                    f"### {xml}\n```xml\n"
                    + read_truncated(xml, max_lines=60)
                    + "\n```"
                )
        inline_blocks = "\n\n---\n\n**File contents for reference:**\n\n" + "\n\n".join(blocks)

    prompt = textwrap.dedent(f"""\
        You are a COSTA test automation architect. Your job is to read the
        provided test files and generate a Knowledge Base documentation file.

        **DO NOT** scan the whole workspace. Read ONLY the files listed below.
        **DO NOT** write any test code. Only produce the KB markdown document.
        **IGNORE** SOAP/REST request builders — treat wrappers as black boxes.

        ---

        ## Your task

        Analyse the files below and extract knowledge about the feature:
        **{feature}**
        {gui_scope}
        Then **write the file `{out_path}`** with the structure defined below.
        {truncation_note}
        ---

        ## Files to read

        {file_refs}
        {xml_refs}

        ---

        ## Required output — write exactly this file: `{out_path}`

        Use this structure (keep all headings verbatim):

        ```markdown
        # KB: {feature.title()}

        **Feature slug:** `{slug}`
        **Last updated:** {today}
        **Generated from:** Copilot agent — @workspace /kb {feature}

        ---

        ## Business summary
        (2-3 sentences: what this feature automates and what the end state is)

        ---

        ## GUIs involved

        For EACH GUI found, create a sub-section:

        ### <GUI Name>

        | Action | Wrapper / Method | Key parameters |
        |--------|-----------------|----------------|
        | <action> | `<wrapper_name(...)>` | <params> |

        ---

        ## Wrapper / method reference

        List every wrapper or helper function called in the test files that
        relates to this feature.
        Format: `module_or_file.function_name(param: type) -> return_type`
        Add a one-line description for each.

        ---

        ## Reusable assertions

        ```python
        # Copy exact assert statements from the test files
        # One per line as Python comments or real assert lines
        ```

        ---

        ## Test data schema (XML)

        ```xml
        <TestData>
          <!-- Mirror the XML data file structure, one element per field -->
          <!-- Mark environment-specific values: <!-- REPLACE: description --> -->
        </TestData>
        ```

        ---

        ## Related KB docs

        | Feature | KB doc | Relationship |
        |---------|--------|-------------|
        | <!-- related feature --> | `docs/kb/<slug>.md` | <!-- depends-on / required-by --> |

        ---

        ## Missing wrappers / gaps

        | Gap | Proposed helper signature | Found in |
        |-----|--------------------------|---------|
        | <!-- action with no wrapper --> | `def helper(...) -> type` | <!-- file --> |

        ---

        ## Change log

        | Date | Change | Author |
        |------|--------|--------|
        | {today} | Generated by Copilot agent | automated |
        ```

        ---

        ## Rules

        - Write the file directly — do not ask for confirmation.
        - If a wrapper's full signature is not visible in the truncated file,
          write `<!-- VERIFY SIGNATURE -->` next to it.
        - If no XML companion was found, leave the Test data schema section
          with placeholder comments.
        - Do not invent wrapper names — only use names seen in the files.
        - Mark any action that has no wrapper as `[MISSING]` in the gaps table.
        {inline_blocks}
    """)

    return prompt


# ── Clipboard ──────────────────────────────────────────────────────────────────

def copy_to_clipboard(text: str) -> bool:
    """Try to copy text to clipboard. Returns True on success."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode("utf-16"), check=True)
            return True
        else:
            # Linux — try xclip then xsel
            for cmd in [["xclip", "-selection", "clipboard"],
                        ["xsel", "--clipboard", "--input"]]:
                try:
                    subprocess.run(cmd, input=text.encode(), check=True)
                    return True
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return False


def save_prompt_file(prompt: str, feature: str) -> Path:
    """Save prompt to a staging file as fallback when clipboard fails."""
    slug = re.sub(r"[^a-z0-9]+", "-", feature.lower()).strip("-")
    staging = Path("copilot_prompts")
    staging.mkdir(exist_ok=True)
    out = staging / f"kb_{slug}.txt"
    out.write_text(prompt, encoding="utf-8")
    return out


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_list(tests_dir: str) -> None:
    files = find_test_files(tests_dir)
    print(f"\n[scan] {len(files)} test file(s) in '{tests_dir}'\n")

    features, guis = discover_features_and_guis(files)

    print(f"── Features found ({len(features)}) " + "─" * 40)
    if features:
        for slug, flist in sorted(features.items()):
            unique = sorted(set(str(f) for f in flist))
            print(f"\n  {slug}")
            for fp in unique[:4]:
                print(f"    · {fp}")
            if len(unique) > 4:
                print(f"    · ... and {len(unique) - 4} more")
    else:
        print("  (none found — test files may have no [SCENARIO] blocks or")
        print("   recognisable class names. Try --list after adding Features:[])")

    print(f"\n── GUIs / Systems found ({len(guis)}) " + "─" * 38)
    if guis:
        for name, flist in sorted(guis.items()):
            print(f"  {name:<40} {len(set(str(f) for f in flist))} file(s)")
    else:
        print("  (none found)")

    print(f"\nTip: run --feature <slug> to generate a Copilot prompt.")
    print(f"     Add synonyms with --grep-extra if your slug isn't listed above.")


def cmd_prepare(
    feature:    str,
    gui_filter: str | None,
    tests_dir:  str,
    grep_extra: list[str],
    max_files:  int,
    ide:        str,
    inline:     bool,
    dry_run:    bool,
) -> None:
    files = find_test_files(tests_dir)
    print(f"[scan] {len(files)} test file(s) in '{tests_dir}'")

    # Build grep terms: slug variants + known synonyms + user extras
    slug = re.sub(r"[^a-z0-9]+", "-", feature.lower()).strip("-")
    base_terms = [
        feature,
        slug,
        slug.replace("-", "_"),
        slug.replace("-", ""),
        feature.replace("-", " "),
    ]
    synonym_terms = FEATURE_SYNONYMS.get(slug, [])
    gui_terms     = [gui_filter] if gui_filter else []
    all_terms     = list(dict.fromkeys(
        base_terms + synonym_terms + grep_extra + gui_terms
    ))

    print(f"[grep] terms: {all_terms}")
    matched = grep_files(files, all_terms)

    if not matched:
        print(f"\n[WARN] No test files matched for feature '{feature}'.")
        print(f"       Options:")
        print(f"         1. Add synonyms: --grep-extra <term1> <term2>")
        print(f"         2. Check tests dir: --tests-dir <path>")
        print(f"         3. Run --list to see what's discoverable")
        return

    print(f"[match] {len(matched)} file(s) matched:")
    for f in matched:
        xml = find_xml_companion(f)
        xml_note = f"  (+ {xml.name})" if xml else ""
        print(f"  · {f}{xml_note}")

    if len(matched) > max_files:
        print(f"\n[NOTE] {len(matched)} files found, using top {max_files}.")
        print(f"       Increase with --max-files {len(matched)} to include all.")

    prompt = build_prompt(
        feature       = feature,
        matched_files = matched,
        gui_filter    = gui_filter,
        ide           = ide,
        max_files     = max_files,
        inline_code   = inline,
    )

    if dry_run:
        print("\n" + "═" * 60)
        print(prompt[:4000])
        if len(prompt) > 4000:
            print(f"\n... [preview truncated — full prompt is {len(prompt)} chars]")
        print("═" * 60)
        print("\n[dry-run] No files written, clipboard not set.")
        return

    # Try clipboard first
    copied = copy_to_clipboard(prompt)

    if copied:
        print(f"\n✓ Prompt copied to clipboard ({len(prompt)} chars)")
    else:
        saved = save_prompt_file(prompt, feature)
        print(f"\n[clipboard unavailable] Prompt saved to: {saved}")
        print(f"Open that file and copy its contents manually.")

    # Always save a copy so it can be re-pasted
    saved = save_prompt_file(prompt, feature)

    out_path = f"{KB_DIR}/{slug}.md"
    print(f"""
─────────────────────────────────────────────────────────────
 NEXT STEPS
─────────────────────────────────────────────────────────────

 1. Open Copilot Chat in {'VS Code (switch to Agent mode)' if ide == 'vscode' else 'IntelliJ'}
 2. Paste the prompt  {'(already in clipboard)' if copied else f'from: {saved}'}
 3. Press Enter — Copilot will read the {min(len(matched), max_files)} file(s)
    and write: {out_path}

 VS Code:   Make sure you are in ✦ Agent mode (not Ask or Edit)
 IntelliJ:  Use the Copilot Chat panel, paste as-is

 If Copilot times out:
   python scripts/prepare_copilot_prompt.py --feature {feature} --max-files 2

 To verify the KB doc was written:
   python scripts/prepare_copilot_prompt.py --feature {feature} --verify
─────────────────────────────────────────────────────────────
""")


def cmd_verify(feature: str) -> None:
    """Check that the KB doc was written and looks complete."""
    slug = re.sub(r"[^a-z0-9]+", "-", feature.lower()).strip("-")
    kb_path = Path(KB_DIR) / f"{slug}.md"

    if not kb_path.exists():
        print(f"[FAIL] {kb_path} does not exist yet.")
        print(f"       Paste the prompt into Copilot Chat and let it write the file.")
        return

    text = kb_path.read_text(encoding="utf-8")
    checks = {
        "Has business summary":       bool(re.search(r"## Business summary", text)),
        "Has GUI section":            bool(re.search(r"## GUIs involved", text)),
        "Has wrapper reference":      bool(re.search(r"## Wrapper", text)),
        "Has assertions section":     bool(re.search(r"## Reusable assertions", text)),
        "Has test data schema":       bool(re.search(r"## Test data schema", text)),
        "No unfilled TODO placeholders": "<!-- TODO" not in text,
        "Has at least one wrapper":   bool(re.search(r"`\w+\(", text)),
    }

    all_pass = all(checks.values())
    print(f"\n[verify] {kb_path}\n")
    for check, passed in checks.items():
        icon = "✓" if passed else "✗"
        print(f"  {icon}  {check}")

    if all_pass:
        print(f"\n✓ KB doc looks complete. Commit it and Copilot will use it automatically.")
    else:
        print(f"\n✗ Some sections need attention. Open {kb_path} and fill in missing parts.")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="COSTA KB Generator — builds a Copilot agent prompt from your test files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python scripts/prepare_copilot_prompt.py --list
              python scripts/prepare_copilot_prompt.py --feature blocking
              python scripts/prepare_copilot_prompt.py --feature blocking --gui "Topaz OMS"
              python scripts/prepare_copilot_prompt.py --feature etd-orders --grep-extra buy_to_open
              python scripts/prepare_copilot_prompt.py --feature blocking --ide intellij
              python scripts/prepare_copilot_prompt.py --feature blocking --max-files 2
              python scripts/prepare_copilot_prompt.py --feature blocking --verify
        """),
    )

    parser.add_argument("--feature", "-f",
        help="Feature name to process (e.g. 'blocking', 'etd-orders')")
    parser.add_argument("--gui", "-g",
        help="Restrict extraction to one GUI (e.g. 'Topaz OMS')")
    parser.add_argument("--list", "-l", action="store_true",
        help="Discover and list all features/GUIs in the test project")
    parser.add_argument("--verify", action="store_true",
        help="Check that docs/kb/<feature>.md was written correctly")
    parser.add_argument("--grep-extra", nargs="*", default=[], metavar="TERM",
        help="Extra grep terms to broaden file matching")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES,
        metavar="N",
        help=f"Max test files per prompt (default: {DEFAULT_MAX_FILES}). "
             f"Lower this if Copilot times out.")
    parser.add_argument("--ide", choices=["vscode", "intellij"], default="vscode",
        help="Target IDE for file reference format (default: vscode)")
    parser.add_argument("--inline", action="store_true",
        help="Embed file contents inline in prompt (use when #file: refs don't resolve)")
    parser.add_argument("--tests-dir", default=TESTS_DIR,
        help=f"Root directory of test files (default: {TESTS_DIR})")
    parser.add_argument("--dry-run", action="store_true",
        help="Print prompt preview without copying to clipboard")

    args = parser.parse_args()

    if args.list:
        cmd_list(args.tests_dir)
        return

    if not args.feature:
        parser.print_help()
        print("\nTip: start with --list to discover features in your project.")
        return

    if args.verify:
        cmd_verify(args.feature)
        return

    cmd_prepare(
        feature    = args.feature,
        gui_filter = args.gui,
        tests_dir  = args.tests_dir,
        grep_extra = args.grep_extra or [],
        max_files  = args.max_files,
        ide        = args.ide,
        inline     = args.inline,
        dry_run    = args.dry_run,
    )


if __name__ == "__main__":
    main()
