#!/usr/bin/env python3
"""
prepare_copilot_prompt.py — COSTA KB Bootstrap Tool
=====================================================
Solves the Copilot timeout problem by doing all the heavy file work OUTSIDE
Copilot. The script:

  1. Greps your test files to find candidates for a given feature or GUI
  2. Reads and chunks those files into small digestible pieces
  3. Produces ready-to-paste Copilot prompt files — one chunk at a time
  4. Merges Copilot responses into a final KB .md doc

You never feed Copilot the whole project. Each prompt chunk is small and fast.

────────────────────────────────────────────────────────────────────────────
WORKFLOW
────────────────────────────────────────────────────────────────────────────

STEP 1 — Discover what features/GUIs exist:
  python scripts/prepare_copilot_prompt.py --list

STEP 2 — Prepare prompts for a feature (greps + chunks test files):
  python scripts/prepare_copilot_prompt.py --feature blocking
  python scripts/prepare_copilot_prompt.py --feature blocking --gui "Topaz OMS"

  → Writes prompt files to: copilot_prompts/blocking/
    chunk_01_of_03.txt
    chunk_02_of_03.txt
    chunk_03_of_03.txt
    INSTRUCTIONS.txt          ← read this first

STEP 3 — Paste each chunk into Copilot Chat, save responses as:
    copilot_prompts/blocking/response_01.txt
    copilot_prompts/blocking/response_02.txt
    ...

STEP 4 — Merge responses into final KB doc:
  python scripts/prepare_copilot_prompt.py --feature blocking --merge

  → Writes: docs/kb/blocking.md

────────────────────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import glob
import argparse
import textwrap
from pathlib import Path
from datetime import date
from collections import defaultdict


# ── Configuration ─────────────────────────────────────────────────────────────

TESTS_DIR        = "tests"                  # Root of your test .py files
CONFIG_DIRS      = ["config", "resources"]  # Where XML/config files live
KB_DIR           = "docs/kb"               # Output for finished KB docs
PROMPTS_DIR      = "copilot_prompts"       # Staging area for chunk prompts

# How many test files to include per Copilot chunk.
# Keep this low (3-5) to avoid Copilot timeout.
FILES_PER_CHUNK  = 4

# Max lines to read from a single .py file (avoids huge files swamping a chunk)
MAX_LINES_PER_FILE = 120

# Keywords used for grepping when no [SCENARIO] block exists
# Maps feature slug → search terms (case-insensitive OR match)
FEATURE_GREP_MAP = {
    # populated at runtime from --feature arg + common synonyms
    # override by editing this dict or using --grep-extra
}

# XML companion file: if test is test_etd_block.py look for test_etd_block.xml
# in the same dir or in CONFIG_DIRS
FIND_XML_COMPANION = True


# ── Utilities ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def find_test_files(tests_dir: str) -> list[Path]:
    root = Path(tests_dir)
    if not root.exists():
        print(f"[ERROR] Tests directory not found: {tests_dir}")
        sys.exit(1)
    return sorted(root.rglob("test_*.py")) + sorted(root.rglob("*_test.py"))


def grep_files(files: list[Path], terms: list[str]) -> list[Path]:
    """Return files that contain ANY of the search terms (case-insensitive)."""
    matched = []
    pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE)
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(content):
                matched.append(f)
        except Exception:
            pass
    return matched


def read_truncated(path: Path, max_lines: int = MAX_LINES_PER_FILE) -> str:
    """Read a file, truncating to max_lines with a clear marker."""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        return f"# [ERROR reading file: {e}]"

    if len(lines) <= max_lines:
        return "\n".join(lines)

    kept = lines[:max_lines]
    kept.append(
        f"\n# ... [TRUNCATED: showing {max_lines} of {len(lines)} lines. "
        f"Full file: {path}]"
    )
    return "\n".join(kept)


def find_xml_companion(py_path: Path, config_dirs: list[str]) -> Path | None:
    """Look for an XML data file paired with a test .py file."""
    stem = py_path.stem  # e.g. test_etd_block
    candidates = [py_path.parent / f"{stem}.xml"]
    for d in config_dirs:
        candidates.append(Path(d) / f"{stem}.xml")
        # also try without test_ prefix
        candidates.append(Path(d) / f"{stem.removeprefix('test_')}.xml")
    for c in candidates:
        if c.exists():
            return c
    return None


def discover_features_and_guis(files: list[Path]) -> tuple[dict, dict]:
    """
    Scan all test files for:
      - [SCENARIO] blocks (new format with Features/GUIs arrays)
      - Class/method names and import patterns (fallback for files with no comments)
    Returns:
      features_map: {feature_slug: [file, ...]}
      guis_map:     {gui_name:     [file, ...]}
    """
    features_map = defaultdict(list)
    guis_map     = defaultdict(list)

    feature_re = re.compile(r"[Ff]eatures?\s*:\s*\[([^\]]+)\]")
    gui_re     = re.compile(r"[Gg][Uu][Ii]s?\s*:\s*\[([^\]]+)\]")
    systems_re = re.compile(r"[Ss]ystems? involved\s*:((?:\s*-\s*.+)+)")

    # Heuristic patterns for files without [SCENARIO] blocks
    class_re   = re.compile(r"^class\s+Test(\w+)\s*[:(]", re.MULTILINE)
    import_re  = re.compile(r"^(?:from|import)\s+([\w.]+)", re.MULTILINE)

    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")

        # ── Explicit Features array ──────────────────────────────────────────
        for m in feature_re.finditer(text):
            for item in m.group(1).split(","):
                slug = slugify(item.strip())
                if slug:
                    features_map[slug].append(f)

        # ── Explicit GUIs array ──────────────────────────────────────────────
        for m in gui_re.finditer(text):
            for item in m.group(1).split(","):
                name = item.strip().strip('"').strip("'")
                if name:
                    guis_map[name].append(f)

        # ── Systems involved fallback ────────────────────────────────────────
        m = systems_re.search(text)
        if m:
            for line in m.group(1).splitlines():
                name = re.sub(r"^\s*-\s*", "", line).strip()
                if name:
                    guis_map[name].append(f)

        # ── Class name heuristic (no scenario block at all) ──────────────────
        if not feature_re.search(text):
            for m in class_re.finditer(text):
                raw = m.group(1)  # e.g. "ETDOrderBlocking"
                # Split CamelCase into slug: etd-order-blocking
                slug = slugify(
                    re.sub(r"([A-Z])", r" \1", raw).strip()
                )
                if slug:
                    features_map[slug].append(f)

    return dict(features_map), dict(guis_map)


# ── Prompt building ────────────────────────────────────────────────────────────

CHUNK_SYSTEM_HEADER = """\
You are a COSTA test automation architect.
Your task: analyse the provided Python test file(s) and extract structured
knowledge for a KB documentation file. Do NOT run or execute any code.
Respond ONLY with the structured sections listed in the instructions below.
Keep responses concise — this output will be merged into a markdown KB doc.
"""

CHUNK_INSTRUCTION = """\
From the test file(s) below, extract the following for the feature: {feature}
{gui_filter}

Return EXACTLY these sections (use these headings verbatim):

## Wrappers / methods found
List every wrapper or helper function called that relates to {feature}.
Format: `module_or_file.function_name(params)` — one per line.
If params are unknown write `(...)`.

## GUI actions identified
For each GUI ({guis}):
List the UI actions performed and which wrapper handles each.
Format: GUI Name | action description | wrapper_name(...)

## Data fields used
List every test data field/parameter seen (field name and example value).
Format: FieldName: example_value

## Assertions / verifications
List every assert statement or verification step related to {feature}.
One per line, as a Python comment starting with # assert

## Missing wrappers [MISSING]
List any action that has no clear existing wrapper (mark these for human review).
Format: [MISSING] description of needed helper

## Notes
Any other observations relevant to this feature (state machine, preconditions,
dependencies on other features).

────────────────────────────────────────────────────────────────────────────
TEST FILE(S):
────────────────────────────────────────────────────────────────────────────
{file_blocks}
"""

def build_file_block(py_path: Path, config_dirs: list[str]) -> str:
    """Build the text block for one test file, including XML companion if found."""
    lines = [f"### FILE: {py_path}", "```python"]
    lines.append(read_truncated(py_path))
    lines.append("```")

    if FIND_XML_COMPANION:
        xml = find_xml_companion(py_path, config_dirs)
        if xml:
            lines.append(f"\n### DATA FILE: {xml}")
            lines.append("```xml")
            lines.append(read_truncated(xml, max_lines=60))
            lines.append("```")

    return "\n".join(lines)


def build_chunks(
    feature: str,
    matched_files: list[Path],
    gui_filter: str | None,
    config_dirs: list[str],
) -> list[str]:
    """Split matched files into chunks and build one prompt string per chunk."""
    guis_str     = gui_filter if gui_filter else "all GUIs found in the files"
    gui_filter_str = (
        f"Focus ONLY on GUI: {gui_filter}"
        if gui_filter
        else "Cover all GUIs found in the files."
    )

    chunks = []
    for i in range(0, len(matched_files), FILES_PER_CHUNK):
        batch = matched_files[i : i + FILES_PER_CHUNK]
        file_blocks = "\n\n".join(
            build_file_block(f, config_dirs) for f in batch
        )
        prompt = CHUNK_SYSTEM_HEADER + "\n" + CHUNK_INSTRUCTION.format(
            feature     = feature,
            guis        = guis_str,
            gui_filter  = gui_filter_str,
            file_blocks = file_blocks,
        )
        chunks.append(prompt)

    return chunks


# ── Merge responses into KB doc ───────────────────────────────────────────────

SECTION_HEADERS = [
    "Wrappers / methods found",
    "GUI actions identified",
    "Data fields used",
    "Assertions / verifications",
    "Missing wrappers [MISSING]",
    "Notes",
]

def parse_response_sections(text: str) -> dict[str, list[str]]:
    """Extract named sections from a Copilot response."""
    sections = defaultdict(list)
    current = None
    for line in text.splitlines():
        header_match = re.match(r"^##\s+(.+)", line)
        if header_match:
            current = header_match.group(1).strip()
        elif current:
            stripped = line.strip()
            if stripped and not stripped.startswith("──"):
                sections[current].append(stripped)
    return dict(sections)


def merge_sections(all_responses: list[str]) -> dict[str, list[str]]:
    """Merge multiple Copilot responses, deduplicating within each section."""
    merged = defaultdict(list)
    seen   = defaultdict(set)

    for response in all_responses:
        parsed = parse_response_sections(response)
        for section, lines in parsed.items():
            for line in lines:
                if line not in seen[section]:
                    seen[section].add(line)
                    merged[section].append(line)

    return dict(merged)


def render_kb_doc(feature: str, sections: dict[str, list[str]]) -> str:
    """Render the final KB markdown doc from merged sections."""
    slug  = slugify(feature)
    today = date.today().isoformat()

    def section_lines(key: str, default: str = "<!-- none found -->") -> str:
        items = sections.get(key, [])
        return "\n".join(items) if items else default

    # Parse GUI actions into a table
    gui_table_rows = []
    for line in sections.get("GUI actions identified", []):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3:
            gui_table_rows.append(f"| {parts[0]} | {parts[1]} | `{parts[2]}` |")
        elif line.strip():
            gui_table_rows.append(f"| <!-- GUI --> | {line} | <!-- wrapper --> |")

    gui_table = (
        "| GUI | Action | Wrapper |\n"
        "|-----|--------|---------|\n"
        + "\n".join(gui_table_rows)
        if gui_table_rows
        else "| <!-- GUI --> | <!-- action --> | `<!-- wrapper -->` |"
    )

    # Data fields table
    data_rows = []
    for line in sections.get("Data fields used", []):
        kv = re.split(r"\s*:\s*", line, maxsplit=1)
        if len(kv) == 2:
            data_rows.append(f"  <{kv[0].strip()}>{kv[1].strip()}</{kv[0].strip()}>")
        else:
            data_rows.append(f"  <!-- {line} -->")

    xml_data = (
        "<TestData>\n" + "\n".join(data_rows) + "\n</TestData>"
        if data_rows
        else "<TestData>\n  <!-- No data fields auto-detected -->\n</TestData>"
    )

    missing = [
        l for l in sections.get("Missing wrappers [MISSING]", [])
        if l.strip()
    ]
    missing_table_rows = "\n".join(
        f"| {l.removeprefix('[MISSING]').strip()} | <!-- def helper(...) --> | <!-- file --> |"
        for l in missing
    ) or "| <!-- none --> | | |"

    wrappers = "\n".join(
        f"- `{l}`" for l in sections.get("Wrappers / methods found", [])
    ) or "- <!-- No wrappers detected -->"

    notes = "\n".join(
        f"> {l}" for l in sections.get("Notes", [])
    ) or "> <!-- none -->"

    assertions = "\n".join(
        sections.get("Assertions / verifications", [])
    ) or "# <!-- no assertions extracted -->"

    return textwrap.dedent(f"""\
        # KB: {feature.title()}

        **Feature slug:** `{slug}`
        **Last updated:** {today}
        **Generated from:** `python scripts/prepare_copilot_prompt.py --feature {slug} --merge`

        ---

        ## Business summary

        <!-- TODO: write a 2-3 sentence summary of what this feature does -->

        ---

        ## GUI actions involved

        {gui_table}

        ---

        ## Wrapper / method reference

        {wrappers}

        ---

        ## Reusable assertions

        ```python
        {assertions}
        ```

        ---

        ## Test data schema (XML)

        ```xml
        {xml_data}
        ```

        ---

        ## Missing wrappers / gaps

        | Gap | Proposed helper signature | Found in |
        |-----|--------------------------|---------|
        {missing_table_rows}

        ---

        ## Notes

        {notes}

        ---

        ## Change log

        | Date | Change | Author |
        |------|--------|--------|
        | {today} | Auto-generated via prepare_copilot_prompt.py | automated |
    """)


# ── CLI ────────────────────────────────────────────────────────────────────────

def write_instructions(prompt_dir: Path, chunks: list[str], feature: str) -> None:
    """Write an INSTRUCTIONS.txt so the user knows exactly what to do."""
    n = len(chunks)
    steps = "\n".join(
        f"  {i+1}. Paste chunk_{i+1:02d}_of_{n:02d}.txt into Copilot Chat\n"
        f"     Save the response as: response_{i+1:02d}.txt in this folder"
        for i in range(n)
    )
    text = textwrap.dedent(f"""\
        COSTA KB Bootstrap — Instructions for feature: {feature}
        ═══════════════════════════════════════════════════════

        {n} chunk prompt(s) have been prepared. Follow these steps:

        {steps}

        Once ALL response files are saved here, run:
          python scripts/prepare_copilot_prompt.py --feature {feature} --merge

        This will write: docs/kb/{slugify(feature)}.md

        ── Tips for pasting into Copilot ───────────────────────────────────
        • Use Copilot Chat (not inline completion) — paste the full chunk text
        • If Copilot times out, reduce FILES_PER_CHUNK in the script (try 2)
        • Each chunk is independent — paste in any order
        • After --merge, review the .md and fill in <!-- TODO --> sections
    """)
    (prompt_dir / "INSTRUCTIONS.txt").write_text(text, encoding="utf-8")


def cmd_list(tests_dir: str) -> None:
    files = find_test_files(tests_dir)
    print(f"\n[scan] {len(files)} test file(s) found in '{tests_dir}'")
    features, guis = discover_features_and_guis(files)

    print(f"\n── Features ({len(features)}) ──────────────────────────────")
    for slug, flist in sorted(features.items()):
        print(f"  {slug:<35} {len(flist)} file(s)")
        for f in flist[:3]:
            print(f"    · {f}")
        if len(flist) > 3:
            print(f"    · ... and {len(flist)-3} more")

    print(f"\n── GUIs / Systems ({len(guis)}) ─────────────────────────────")
    for name, flist in sorted(guis.items()):
        print(f"  {name:<35} {len(flist)} file(s)")

    print(f"\nTip: run with --feature <slug> to prepare Copilot prompts.")


def cmd_prepare(
    feature: str,
    gui_filter: str | None,
    tests_dir: str,
    grep_extra: list[str],
    dry_run: bool,
) -> None:
    files = find_test_files(tests_dir)
    print(f"[scan] {len(files)} test file(s) in '{tests_dir}'")

    # Build grep terms: feature slug + synonyms + any extras the user provided
    slug_terms = [feature, feature.replace("-", " "), feature.replace("-", "_")]
    terms = list(dict.fromkeys(slug_terms + grep_extra))  # deduplicated, ordered
    if gui_filter:
        terms.append(gui_filter)

    print(f"[grep] searching for: {terms}")
    matched = grep_files(files, terms)

    if not matched:
        print(f"[WARN] No test files matched. Try --grep-extra to add synonyms.")
        print(f"       Example: --grep-extra block manual_block")
        return

    print(f"[match] {len(matched)} file(s) matched:")
    for f in matched:
        print(f"  · {f}")

    config_dirs = [d for d in CONFIG_DIRS if Path(d).exists()]
    chunks = build_chunks(feature, matched, gui_filter, config_dirs)
    n = len(chunks)
    print(f"\n[chunk] {n} chunk(s) of up to {FILES_PER_CHUNK} file(s) each")

    if dry_run:
        print("\n[dry-run] First chunk preview:\n")
        print(chunks[0][:3000])
        print("\n... (truncated for preview)")
        return

    prompt_dir = Path(PROMPTS_DIR) / slugify(feature)
    prompt_dir.mkdir(parents=True, exist_ok=True)

    for i, chunk in enumerate(chunks):
        out = prompt_dir / f"chunk_{i+1:02d}_of_{n:02d}.txt"
        out.write_text(chunk, encoding="utf-8")
        print(f"[write] {out}")

    write_instructions(prompt_dir, chunks, feature)
    print(f"\n[done] Open {prompt_dir}/INSTRUCTIONS.txt and follow the steps.")


def cmd_merge(feature: str) -> None:
    prompt_dir = Path(PROMPTS_DIR) / slugify(feature)
    if not prompt_dir.exists():
        print(f"[ERROR] No prompt directory found: {prompt_dir}")
        print(f"        Run --feature {feature} first to prepare prompts.")
        return

    response_files = sorted(prompt_dir.glob("response_*.txt"))
    if not response_files:
        print(f"[ERROR] No response_*.txt files found in {prompt_dir}")
        print(f"        Paste Copilot responses and save as response_01.txt, etc.")
        return

    print(f"[merge] reading {len(response_files)} response file(s)")
    responses = [f.read_text(encoding="utf-8") for f in response_files]

    sections = merge_sections(responses)
    doc = render_kb_doc(feature, sections)

    kb_dir = Path(KB_DIR)
    kb_dir.mkdir(parents=True, exist_ok=True)
    out = kb_dir / f"{slugify(feature)}.md"

    if out.exists():
        backup = out.with_suffix(f".{date.today().isoformat()}.bak.md")
        out.rename(backup)
        print(f"[backup] existing doc → {backup}")

    out.write_text(doc, encoding="utf-8")
    print(f"[done]  KB doc written to: {out}")
    print(f"\nNext steps:")
    print(f"  1. Open {out}")
    print(f"  2. Fill in the <!-- TODO --> business summary")
    print(f"  3. Verify wrapper signatures against actual project code")
    print(f"  4. Commit to repo — Copilot will load it via features: [{slugify(feature)}]")


def main():
    parser = argparse.ArgumentParser(
        description="COSTA KB Bootstrap — prepare Copilot prompts from existing test files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--feature", "-f",
        help="Feature name to process (e.g. 'blocking', 'etd-orders')"
    )
    parser.add_argument(
        "--gui", "-g",
        help="Optional: restrict extraction to a specific GUI name"
    )
    parser.add_argument(
        "--merge", "-m",
        action="store_true",
        help="Merge saved Copilot responses into a KB .md doc"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Discover and list all features and GUIs found in test files"
    )
    parser.add_argument(
        "--grep-extra", nargs="*", default=[],
        metavar="TERM",
        help="Extra grep terms to broaden file matching (e.g. --grep-extra manual_block block_order)"
    )
    parser.add_argument(
        "--tests-dir", default=TESTS_DIR,
        help=f"Root of test files (default: {TESTS_DIR})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview first chunk to stdout, do not write files"
    )

    args = parser.parse_args()

    if args.list:
        cmd_list(args.tests_dir)
        return

    if not args.feature:
        parser.print_help()
        print("\nTip: start with --list to discover features in your project.")
        return

    if args.merge:
        cmd_merge(args.feature)
    else:
        cmd_prepare(
            feature     = args.feature,
            gui_filter  = args.gui,
            tests_dir   = args.tests_dir,
            grep_extra  = args.grep_extra or [],
            dry_run     = args.dry_run,
        )


if __name__ == "__main__":
    main()
