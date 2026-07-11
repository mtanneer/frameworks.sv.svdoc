"""svdoc CLI (v1): `svdoc <file.sv>` prints to terminal; `--out md` writes a .md file."""
import argparse
import pathlib
import sys

from .fixer import fix_file
from .ir import InterfaceDoc, ModuleDoc, PackageDoc
from .parser import parse_file, resolve_types
from .render_md import render, render_interface, render_package

_RENDERERS = {
    ModuleDoc: render,
    InterfaceDoc: render_interface,
    PackageDoc: render_package,
}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="svdoc")
    ap.add_argument("file", help="path to the .sv file containing the module/interface/package to document")
    ap.add_argument("more_files", nargs="*",
                     help="additional .sv files (e.g. packages it depends on) used only to "
                          "resolve cross-file types -- not documented themselves")
    ap.add_argument("--out", choices=["md"], help="write rendered doc to a file instead of stdout")
    ap.add_argument("--fix", action="store_true",
                     help="insert ///< TODO stubs next to undocumented ports/params in place")
    args = ap.parse_args(argv)

    if args.fix:
        changed = fix_file(args.file)
        print(f"{'fixed' if changed else 'no changes needed for'} {args.file}")
        return

    doc = parse_file(args.file)
    if args.more_files and isinstance(doc, ModuleDoc):
        resolve_types(doc, [args.file] + args.more_files)
    text = _RENDERERS[type(doc)](doc)

    if args.out == "md":
        out_path = pathlib.Path(args.file).with_suffix(".md")
        out_path.write_text(text)
        print(f"wrote {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
