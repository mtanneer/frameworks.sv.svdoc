"""svdoc CLI (v1): `svdoc <file.sv>` prints to terminal; `--out md` writes a .md file."""
import argparse
import pathlib
import sys

from .parser import parse_module
from .render_md import render


def main(argv=None):
    ap = argparse.ArgumentParser(prog="svdoc")
    ap.add_argument("file", help="path to a .sv file containing one module")
    ap.add_argument("--out", choices=["md"], help="write rendered doc to a file instead of stdout")
    args = ap.parse_args(argv)

    mod = parse_module(args.file)
    text = render(mod)

    if args.out == "md":
        out_path = pathlib.Path(args.file).with_suffix(".md")
        out_path.write_text(text)
        print(f"wrote {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
