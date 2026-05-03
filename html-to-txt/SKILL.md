---
name: html-to-txt
description: >
  Convert HTML documentation (single file or whole folder tree) to flat plaintext via
  pandoc + aggressive regex cleanup. Output is one .txt per source file, plus an
  optional consolidated <foldername>.txt where each source becomes one line. Ideal
  for prepping doc sites for LLM context, embeddings, grep/RAG indexes, or full-text
  search. Trigger: "convert this HTML doc(s) to text", "flatten this docs site",
  "strip HTML/markdown formatting from these files", or `/html-to-txt`.
---

# HTML → flat plaintext

## Purpose

Take HTML doc(s) and produce clean single-line plaintext. Removes every markdown/HTML
construct that pandoc emits (links, attribute spans, fenced divs, headings, bold/italic,
code fences, escape sequences, table separators, raw HTML tags, comments). Keeps the
substantive prose and code identifiers.

Output formats:
- **`--file`**: one `<stem>.txt` next to script (or to `--out`).
- **`--folder`**: a `converted_<foldername>/` dir containing one `<stem>.txt` per
  source file PLUS a consolidated `<foldername>.txt` inside that same dir where each
  source contributes exactly one line.

## When to use

Use this skill when the user asks to:
- Convert HTML docs (especially Sphinx/pandoc/RST-generated sites) to plaintext
- Strip markdown/HTML formatting from a `.md`/`.html` file
- Flatten a documentation site for LLM ingestion, embedding, or full-text search
- Prepare a single-line-per-file corpus for retrieval/RAG
- Mentions of pandoc + cleanup pipelines for docs

Do NOT use for:
- Source code files (`.py`, `.ts`, etc.) — this is text/docs only
- Binary HTML (PDFs, images embedded in HTML)
- Cases where the user wants to preserve markdown structure (this destroys it)

## Prerequisites

- Python 3.12+ (uses `Path.walk()`, PEP 695 generics, modern type-hints)
- `pandoc` on PATH

If `pandoc` missing: tell the user to install it (`choco install pandoc` /
`brew install pandoc` / `apt install pandoc`) before retrying. Do not try to
substitute another converter — the regex cleanup is tuned to pandoc's output.

## Process

1. Script lives at `<this_dir>/scripts/html_to_txt.py`. Locate it relative to this
   `SKILL.md`.
2. Pick mode based on user request:
   - Single file → `--file <path>`
   - Folder (recurse) → `--folder <path>`
3. Pick output location:
   - Default: sibling of script. Folder mode emits `converted_<foldername>/`.
   - User-specified: pass `--out <dir>`.
4. Run:

```
python "<skill_dir>/scripts/html_to_txt.py" --file <html_path> [--out <dir>]
python "<skill_dir>/scripts/html_to_txt.py" --folder <folder_path> [--out <dir>]
```

5. Report final path(s) + char-count delta to user.

## CLI

```
python html_to_txt.py --file path/to/page.html [--out OUT]
python html_to_txt.py --folder path/to/site   [--out OUT]
```

`--file` and `--folder` are mutually exclusive and one is required.
`--out` is optional. Default = directory containing the script.

## Folder-mode behavior

Recursive walk, with these exclusions hard-coded:
- Filename `index.html` (case-insensitive, any depth)
- Any path with a folder segment named `changelog` (case-insensitive)
- Filenames containing `metadata` (case-insensitive)
- Dotfiles (`.foo.html`)

Name-clash resolution: when two source files share a stem (e.g.
`a/events.html` and `b/events.html`), the second is renamed by prefixing the
parent dir name (`b_events.txt`). Numeric suffix as last resort.

After per-file conversion, the script writes a consolidated `<foldername>.txt`
inside the same `converted_<foldername>/` dir. One source file = one line. Stray
newlines inside cleaned text are scrubbed defensively before writing.

The staging dir is **not** deleted; both per-file outputs and the consolidated file
remain side-by-side. If user wants only the consolidated output, they can keep that
file and discard the rest manually.

## Single-file mode behavior

Pandoc HTML → markdown intermediate (in a tempfile) → run cleanup → write
`<stem>.txt`. No folder created. No consolidation.

## What gets stripped

- Markdown links `[text](url)` → `text`
- Pandoc spans `[text]{.class}` → `text`
- Inline code `` `text` `` → `text`
- Headings (`#`–`######`)
- Bold/italic (`*`, `**`, `***`)
- Fenced div markers (`:::`, with attrs and directive words like
  `highlight`, `note`, `versionadded`, `See also`, etc.)
- Pandoc table separator rows (long `----` runs)
- Raw HTML tags + comments
- Markdown escape sequences (`\_`, `\*`, `\|`, `\Any`, ...)
- Stray brackets/braces from upstream cleanup
- Multiple whitespace collapsed to single space; all `\n`/`\r` removed

What stays: prose, identifiers, code samples (minus their fences), `{` `}` inside
inline Python dict literals (legit content).

## Examples

### Single file
```
python scripts/html_to_txt.py --file ~/Downloads/sqlalchemy/sqlelement.html
# -> <skill_dir>/sqlelement.txt (~208,000 chars from ~780,000)
```

### Whole site
```
python scripts/html_to_txt.py --folder ~/Downloads/sqlalchemy_20
# -> <skill_dir>/converted_sqlalchemy_20/
#    + 194 per-file .txt
#    + sqlalchemy_20.txt (194 lines, 5MB consolidated)
```

### Custom output dir
```
python scripts/html_to_txt.py --folder ./docs --out ./out
# -> ./out/ contains per-file .txt and docs.txt consolidated
```

## Guidelines for agents

- Always pass absolute paths to `--file` / `--folder` to avoid CWD ambiguity.
- Quote paths with spaces (Windows: PowerShell tolerates double quotes).
- For `--folder` mode, expect per-file progress output (`[i/N] name.html -> stem.txt
  (orig -> final)`) plus a final `Per-file done` and `Wrote N lines` line. Surface
  the final path + char counts; don't dump the full file list to the user unless asked.
- Pandoc may emit `[WARNING] Reference not found ...` lines on broken cross-refs.
  These are harmless source-doc issues; exit code is still 0 and output is unaffected.
  Don't treat them as failures.
- The cleanup is destructive — markdown structure (headings, list nesting, bold,
  links) is lost. If user wants to preserve formatting, this is the wrong tool.
- The consolidated file is intended for LLM context windows / single-shot ingestion.
  If the user only wants per-file outputs, point them at the per-file `.txt`s and
  ignore `<foldername>.txt`.

## Boundaries

- Only `.html` source files. Other extensions are silently skipped during folder walk.
- Script never deletes source HTML files or modifies them.
- Script never writes outside `--out` (or its default sibling-of-script location).
- Re-running on the same folder overwrites previous outputs (idempotent).
- `pandoc` failure on one file in batch mode is reported per-line and the run continues
  with remaining files; no partial-state cleanup.
