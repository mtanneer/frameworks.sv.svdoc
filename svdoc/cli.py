"""svdoc CLI (v1): `svdoc <file.sv>` prints to terminal; `--out md`/`--out html` writes a file."""
import argparse
import pathlib
import sys

from . import render_html, render_md
from .fixer import fix_file
from .ir import InterfaceDoc, ModuleDoc, PackageDoc
from .parser import parse_file, resolve_types

_RENDERERS = {
    "md": {ModuleDoc: render_md.render, InterfaceDoc: render_md.render_interface, PackageDoc: render_md.render_package},
    "html": {ModuleDoc: render_html.render, InterfaceDoc: render_html.render_interface, PackageDoc: render_html.render_package},
}
_EXTENSIONS = {"md": ".md", "html": ".html"}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="svdoc")
    ap.add_argument("file", help="path to the .sv file containing the module/interface/package to document")
    ap.add_argument("more_files", nargs="*",
                     help="additional .sv files (e.g. packages it depends on) used only to "
                          "resolve cross-file types -- not documented themselves")
    ap.add_argument("--out", choices=["md", "html"],
                     help="write rendered doc to a file in this format instead of printing to stdout")
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

    if args.out:
        text = _RENDERERS[args.out][type(doc)](doc)
        out_path = pathlib.Path(args.file).with_suffix(_EXTENSIONS[args.out])
        out_path.write_text(text)
        print(f"wrote {out_path}")
    else:
        print(_RENDERERS["md"][type(doc)](doc))


if __name__ == "__main__":
    sys.exit(main())
