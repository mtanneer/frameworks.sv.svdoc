"""Repeatable smoke run of svdoc over a directory of real-world .sv files.

Usage: .venv/bin/python scripts/corpus_smoke.py DIR [--include-dir D]...

Parses every .sv under DIR, renders md/html/mmd/dot, runs --fix on a temp COPY and
checks the result still parses. Prints crashes (non-ValueError exceptions); files
that fail to parse cleanly (missing defines etc.) are counted as skipped.
Not part of CI. Clone corpora into tmp/ (ignored by version control).
"""

import argparse
import collections
import pathlib
import shutil
import sys
import tempfile

from svdoc import render_diagram, render_html, render_md
from svdoc.fixer import fix_file
from svdoc.ir import ClassDoc, InterfaceDoc, ModuleDoc, PackageDoc
from svdoc.parser import parse_file

MD = {
    ModuleDoc: render_md.render,
    InterfaceDoc: render_md.render_interface,
    PackageDoc: render_md.render_package,
    ClassDoc: render_md.render_class,
}
HTML = {
    ModuleDoc: render_html.render,
    InterfaceDoc: render_html.render_interface,
    PackageDoc: render_html.render_package,
    ClassDoc: render_html.render_class,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--include-dir", action="append", default=[])
    a = ap.parse_args()
    inc = a.include_dir or None
    files = sorted(pathlib.Path(a.dir).rglob("*.sv"))
    stats = collections.Counter()
    crashes = []
    with tempfile.TemporaryDirectory() as td:
        for f in files:
            try:
                doc = parse_file(str(f), (inc or []) + [str(f.parent)])
            except ValueError:
                stats["skipped (parse errors)"] += 1
                continue
            except Exception as e:  # noqa: BLE001
                crashes.append((f, "parse", repr(e)))
                continue
            stats["parsed"] += 1
            try:
                MD[type(doc)](doc)
                HTML[type(doc)](doc)
                if isinstance(doc, ModuleDoc):
                    render_diagram.render_module_symbol_mermaid(doc)
                    render_diagram.render_module_symbol_dot(doc)
            except Exception as e:  # noqa: BLE001
                crashes.append((f, "render", repr(e)))
            copy = pathlib.Path(td) / f.name
            shutil.copy(f, copy)
            try:
                dirs = (inc or []) + [str(f.parent)]
                fix_file(str(copy), dirs)
                parse_file(str(copy), dirs)
            except ValueError as e:
                if not str(e).startswith("no module or interface"):  # --fix has no class support yet
                    crashes.append((f, "fix", repr(e)[:300]))
            except Exception as e:  # noqa: BLE001
                crashes.append((f, "fix", repr(e)[:300]))
    print(dict(stats), f"{len(crashes)} crashes")
    for c in crashes:
        print(*c)
    sys.exit(1 if crashes else 0)


main()
