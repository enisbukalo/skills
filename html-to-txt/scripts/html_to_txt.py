"""Convert HTML docs to flat plaintext.

Per file: pandoc HTML -> markdown -> flatten newlines ->
regex-strip every markdown/HTML construct -> write as .txt.

Folder mode: recurse, convert each, then consolidate every .txt into a
single <foldername>.txt next to the script (one source file = one line),
and delete the per-file .txt staging dir.

CLI:
    python html_to_txt.py --file path/to/page.html [--out OUT]
    python html_to_txt.py --folder path/to/site   [--out OUT]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

EXCLUDED_NAMES: frozenset[str] = frozenset({"index.html"})
EXCLUDED_DIR_NAMES: frozenset[str] = frozenset({"changelog"})
EXCLUDED_NAME_SUBSTRINGS: tuple[str, ...] = ("metadata",)

# Compile-once regexes. Order matters; see clean_markdown() for sequencing.
_RX_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_RX_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_RX_FENCED_DIV_ATTRS_WORDS = re.compile(r":{3,}\s*\{[^}]*\}\s*[A-Za-z][\w\s]*")
_RX_FENCED_DIV_ATTRS = re.compile(r":{3,}\s*\{[^}]*\}")
_RX_FENCED_DIV_DIRECTIVE = re.compile(
    r":{3,}\s+(?:highlight|note|warning|deprecated|versionadded|versionchanged"
    r"|See\s+also|admonition|container|topic|seealso|attention|caution|danger"
    r"|error|hint|important|tip)",
    re.IGNORECASE,
)
_RX_FENCED_DIV_BARE = re.compile(r":{3,}")
_RX_HEADERLINK_FUNC = re.compile(r"\[\[function\].*?\{\.headerlink\s*\}\]")
_RX_ROLE_COLON = re.compile(
    r"(?:Parameters|Returns|Raises|Yields)\s*\[\:\]\s*\{\.colon\s*\}"
)
_RX_EMPTY_SPAN = re.compile(r"\[\s*\]\s*\{[^}]*\}")
_RX_PILCROW_LINK = re.compile(r"\[\xb6\]\s*\([^)]*\)")
_RX_PARAGRAPH_LINK = re.compile(r"\[paragraph\]\s*\([^)]*\)")
_RX_INLINE_CODE_LINK = re.compile(r"\[`([^`]*)`\]\s*\([^)]*\)")
_RX_LINK_TITLE = re.compile(r"\[([^\[\]]+)\]\s*\([^)]*\"[^\"]*\"\s*\)")
_RX_LINK = re.compile(r"\[([^\[\]]+)\]\s*\([^)]*\)")
_RX_SPAN = re.compile(r"\[([^\[\]]*)\]\s*\{[^}]*\}")
_RX_SPAN_DOUBLE = re.compile(r"\[\[([^\[\]]*)\]\]\s*\{[^}]*\}")
_RX_INLINE_CODE = re.compile(r"\[`([^`]*)`\]")
_RX_ORPHAN_ATTR = re.compile(r"\]\s*\{[^}]*\}")
_RX_ORPHAN_LINK_TITLE = re.compile(r"\]\s*\([^)]*\"[^\"]*\"\s*\)")
_RX_ORPHAN_LINK = re.compile(r"\]\s*\([^)]*\)")
_RX_STRAY_ATTR_BLOCK = re.compile(r"\{[#\.][^}]*\}")
_RX_MD_ESCAPE = re.compile(
    r"\\([A-Za-z_\*\[\]\|`\\\.\-\(\)\{\}\<\>\#\+\!\:\;\,\?\/\=\&\$\@\%\^\~\"\'])"
)
_RX_HEADING = re.compile(r"(^|[\.\!\?\s])#{1,6}\s+")
_RX_BOLD_ITALIC = re.compile(r"\*{1,3}")
_RX_DASH_ROW = re.compile(r"-{4,}(?:\s+-{4,})*")
_RX_WHITESPACE = re.compile(r"[ \t]{2,}")


def _loop_sub(rx: re.Pattern[str], repl: str, text: str, max_passes: int = 8) -> str:
    """Apply substitution repeatedly until fixed point or max_passes."""
    for _ in range(max_passes):
        new = rx.sub(repl, text)
        if new == text:
            return new
        text = new
    return text


def clean_markdown(content: str) -> str:
    """Flatten + strip every markdown/HTML construct from pandoc output."""
    content = content.replace("\r", "").replace("\n", "")

    content = _RX_HTML_COMMENT.sub("", content)
    content = _RX_HTML_TAG.sub("", content)

    content = _RX_FENCED_DIV_ATTRS_WORDS.sub("", content)
    content = _RX_FENCED_DIV_ATTRS.sub("", content)
    content = _RX_FENCED_DIV_DIRECTIVE.sub("", content)
    content = _RX_FENCED_DIV_BARE.sub("", content)

    content = _RX_HEADERLINK_FUNC.sub("", content)
    content = _RX_ROLE_COLON.sub("", content)
    content = _RX_EMPTY_SPAN.sub("", content)
    content = _RX_PILCROW_LINK.sub("", content)
    content = _RX_PARAGRAPH_LINK.sub("", content)

    content = _RX_INLINE_CODE_LINK.sub(r"\1", content)
    content = _RX_LINK_TITLE.sub(r"\1", content)
    content = _RX_LINK.sub(r"\1", content)

    content = _loop_sub(_RX_SPAN, r"\1", content, max_passes=8)
    content = _loop_sub(_RX_SPAN_DOUBLE, r"\1", content, max_passes=4)
    content = _RX_INLINE_CODE.sub(r"\1", content)

    content = _RX_ORPHAN_ATTR.sub("", content)
    content = _RX_ORPHAN_LINK_TITLE.sub("", content)
    content = _RX_ORPHAN_LINK.sub("", content)

    content = _RX_STRAY_ATTR_BLOCK.sub("", content)
    content = _loop_sub(_RX_MD_ESCAPE, r"\1", content, max_passes=4)

    content = content.replace("[[", "").replace("]]", "")
    content = content.replace("[", "").replace("]", "")

    content = _RX_HEADING.sub(r"\1", content)
    content = content.replace("`", "")
    content = _RX_BOLD_ITALIC.sub("", content)
    content = _RX_DASH_ROW.sub(" ", content)
    content = _RX_WHITESPACE.sub(" ", content)
    return content.strip()


def convert_one(
    html_path: Path,
    out_dir: Path,
    out_stem: str | None = None,
) -> tuple[int, int]:
    """Convert one HTML file. Returns (raw_md_chars, final_txt_chars)."""
    stem = out_stem or html_path.stem
    txt_path = out_dir / f"{stem}.txt"

    tmp = tempfile.NamedTemporaryFile(
        suffix=".md", dir=out_dir, delete=False, mode="w", encoding="utf-8"
    )
    tmp.close()
    tmp_path = Path(tmp.name)

    try:
        subprocess.run(
            [
                "pandoc",
                "-f",
                "html+raw_html",
                "-t",
                "markdown",
                "-o",
                str(tmp_path),
                str(html_path),
            ],
            check=True,
        )
        raw = tmp_path.read_text(encoding="utf-8")
        cleaned = clean_markdown(raw)
        txt_path.write_text(cleaned, encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)

    return len(raw), len(cleaned)


def _is_excluded(filename: str) -> bool:
    if filename.startswith("."):
        return True
    lf = filename.lower()
    if not lf.endswith(".html"):
        return True
    if lf in EXCLUDED_NAMES:
        return True
    return any(s in lf for s in EXCLUDED_NAME_SUBSTRINGS)


def find_html_files(root: Path) -> list[Path]:
    """Walk root, yield .html paths honoring exclusion rules."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in root.walk():
        dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDED_DIR_NAMES]
        for f in filenames:
            if _is_excluded(f):
                continue
            out.append(dirpath / f)
    return sorted(out)


def assign_unique_stems(paths: Iterable[Path]) -> dict[Path, str]:
    """Map each src Path to a unique output stem.

    On collision, prefix with parent dir(s). Numeric suffix as last resort.
    """
    used: dict[str, Path] = {}
    result: dict[Path, str] = {}
    for src in paths:
        parts = src.parts
        stem = src.stem
        candidate = stem
        depth = 2
        while candidate in used and used[candidate] != src:
            if depth <= len(parts):
                candidate = "_".join([*parts[-depth:-1], stem])
                depth += 1
            else:
                n = 1
                while f"{stem}_{n}" in used:
                    n += 1
                candidate = f"{stem}_{n}"
                break
        used[candidate] = src
        result[src] = candidate
    return result


def consolidate_txt_dir(staging_dir: Path, final_path: Path) -> tuple[int, int]:
    """Concat every .txt in staging_dir into final_path, one line per file.

    Returns (file_count, total_chars_written). Each source file contributes
    exactly one line (its content already single-line from clean_markdown).
    """
    final_resolved = final_path.resolve()
    txt_files = sorted(
        p for p in staging_dir.iterdir()
        if p.suffix == ".txt" and p.resolve() != final_resolved
    )
    total_chars = 0
    with final_path.open("w", encoding="utf-8") as out:
        for i, src in enumerate(txt_files):
            line = src.read_text(encoding="utf-8")
            # Defensive: scrub any stray newlines so one-file = one-line holds.
            line = line.replace("\r", " ").replace("\n", " ")
            if i > 0:
                out.write("\n")
            out.write(line)
            total_chars += len(line)
    return len(txt_files), total_chars


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert HTML docs to flat plaintext via pandoc + cleanup."
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", type=Path, help="Single .html input.")
    g.add_argument(
        "--folder", type=Path, help="Recursively process .html in folder."
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory. Default: sibling of script.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent

    if args.file is not None:
        out_dir = (args.out or script_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        src = args.file.resolve()
        if not src.is_file():
            sys.exit(f"error: {src} is not a file")
        print(f"Converting {src} -> {out_dir / (src.stem + '.txt')}")
        orig, final = convert_one(src, out_dir)
        print(f"Done. {orig} -> {final} chars ({orig - final} removed)")
        return

    folder = args.folder.resolve()
    if not folder.is_dir():
        sys.exit(f"error: {folder} is not a directory")
    default_out = script_dir / f"converted_{folder.name}"
    out_dir = (args.out or default_out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_html_files(folder)
    if not files:
        print(f"No matching .html files found under {folder}")
        return
    stems = assign_unique_stems(files)

    print(f"Found {len(files)} html files. Output -> {out_dir}")
    total_orig = total_final = 0
    for i, src in enumerate(files, 1):
        try:
            orig, final = convert_one(src, out_dir, stems[src])
        except subprocess.CalledProcessError as e:
            print(f"[{i}/{len(files)}] FAILED {src}: pandoc exit {e.returncode}")
            continue
        total_orig += orig
        total_final += final
        print(
            f"[{i}/{len(files)}] {src.name} -> {stems[src]}.txt "
            f"({orig} -> {final})"
        )
    print(
        f"Per-file done. Total {total_orig} -> {total_final} chars "
        f"({total_orig - total_final} removed)"
    )

    # Consolidate: one .txt per source file -> one line in <foldername>.txt,
    # written into the same output dir alongside per-file .txt outputs.
    final_path = out_dir / f"{folder.name}.txt"
    print(f"Consolidating {out_dir} -> {final_path}")
    n_files, n_chars = consolidate_txt_dir(out_dir, final_path)
    print(f"Wrote {n_files} lines ({n_chars} chars) to {final_path}")


if __name__ == "__main__":
    main()
