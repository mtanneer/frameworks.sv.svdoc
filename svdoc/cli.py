"""svdoc CLI (v1): `svdoc <file.sv>` prints to terminal; `--out md`/`--out html`
writes a file; `svdoc build <files...>` writes a multi-page linked HTML site.
"""

import argparse
import pathlib
import sys

from . import render_html, render_md
from .build import build_site
from .fixer import fix_file
from .ir import InterfaceDoc, ModuleDoc, PackageDoc
from .parser import parse_file, resolve_types

_RENDERERS = {
    "md": {
        ModuleDoc: render_md.render,
        InterfaceDoc: render_md.render_interface,
        PackageDoc: render_md.render_package,
    },
    "html": {
        ModuleDoc: render_html.render,
        InterfaceDoc: render_html.render_interface,
        PackageDoc: render_html.render_package,
    },
}
_EXTENSIONS = {"md": ".md", "html": ".html"}


def _run_single(args):
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


def _run_build(args):
    index_path = build_site(args.files, args.out_dir)
    print(f"wrote {len(args.files)} file(s) to a site at {index_path}")


def _build_parser():
    ap = argparse.ArgumentParser(prog="svdoc build")
    ap.add_argument("files", nargs="+", help=".sv files to document")
    ap.add_argument("--out-dir", required=True, help="directory to write the site into")
    return ap


def _single_parser():
    ap = argparse.ArgumentParser(
        prog="svdoc",
        epilog="Also available: `svdoc build <files...> --out-dir <dir>` to "
        "generate a multi-page linked HTML site.",
    )
    ap.add_argument(
        "file",
        help="path to the .sv file containing the module/interface/package to document",
    )
    ap.add_argument(
        "more_files",
        nargs="*",
        help="additional .sv files (e.g. packages it depends on) used only to "
        "resolve cross-file types -- not documented themselves",
    )
    ap.add_argument(
        "--out",
        choices=["md", "html"],
        help="write rendered doc to a file in this format instead of printing to stdout",
    )
    ap.add_argument(
        "--fix",
        action="store_true",
        help="insert ///< TODO stubs next to undocumented ports/params in place",
    )
    return ap


def main(argv=None):
    """Entry point for the ``svdoc`` command (registered via ``pyproject.toml``).

    Two modes, dispatched on whether the first argument is the literal
    ``build`` subcommand (argparse subparsers don't mix cleanly with a
    same-position positional argument, so this is checked manually rather
    than via ``add_subparsers``):

    - ``svdoc <file.sv> [more_files...]`` — document a single module/interface/
      package, optionally resolving cross-file types against ``more_files``,
      printing Markdown to stdout or writing a single Markdown/HTML file
      (``--out``), or scaffolding missing doc comments in place (``--fix``).
    - ``svdoc build <files...> --out-dir <dir>`` — document every given file
      into a single flat multi-page HTML site (one page per construct plus
      an ``index.html``), so cross-links between pages always resolve
      correctly regardless of where the source files live on disk.

    :param argv: Argument list to parse (as :func:`sys.argv`\\ ``[1:]`` would
        appear). Defaults to ``sys.argv[1:]`` when ``None``.
    """
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] == "build":
        args = _build_parser().parse_args(argv[1:])
        _run_build(args)
        return

    args = _single_parser().parse_args(argv)
    _run_single(args)


if __name__ == "__main__":
    sys.exit(main())
