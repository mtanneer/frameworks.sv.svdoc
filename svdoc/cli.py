"""svdoc CLI (v1): `svdoc <file.sv>` prints to terminal; `--out md` writes a .md file."""
import argparse
import pathlib
import sys

from .fixer import fix_file
from .ir import InterfaceDoc
from .parser import parse_file
from .render_md import render, render_interface


def main(argv=None):
    ap = argparse.ArgumentParser(prog="svdoc")
    ap.add_argument("file", help="path to a .sv file containing one module or interface")
    ap.add_argument("--out", choices=["md"], help="write rendered doc to a file instead of stdout")
    ap.add_argument("--fix", action="store_true",
                     help="insert ///< TODO stubs next to undocumented ports/params in place")
    args = ap.parse_args(argv)

    if args.fix:
        changed = fix_file(args.file)
        print(f"{'fixed' if changed else 'no changes needed for'} {args.file}")
        return

    doc = parse_file(args.file)
    text = render_interface(doc) if isinstance(doc, InterfaceDoc) else render(doc)

    if args.out == "md":
        out_path = pathlib.Path(args.file).with_suffix(".md")
        out_path.write_text(text)
        print(f"wrote {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
