"""svdoc build: a flat multi-page HTML site (one page per construct) with a
navigable index, so cross-links between pages always resolve correctly --
avoids the relative-path problem of generating standalone pages into
whatever directories the source files happen to live in.
"""

import pathlib
import re
from html import escape

from . import render_html
from .ir import InterfaceDoc, ModuleDoc, PackageDoc
from .parser import parse_file, resolve_types

_UNSAFE_NAME_CHARS = re.compile(r"[^\w.-]")


def _safe_page_name(name: str) -> str:
    """Sanitize a construct name for use as an output filename. SV escaped
    identifiers (``\\../../foo``) parse without error and can contain path
    separators, so page filenames can't trust ``doc.name`` directly."""
    return _UNSAFE_NAME_CHARS.sub("_", name)

_RENDERERS = {
    ModuleDoc: render_html.render,
    InterfaceDoc: render_html.render_interface,
    PackageDoc: render_html.render_package,
}
_KIND_LABELS = {
    ModuleDoc: "Module",
    InterfaceDoc: "Interface",
    PackageDoc: "Package",
}


def build_site(paths: list, out_dir: str) -> str:
    """Parse every file in ``paths`` and write one HTML page per construct
    into a single flat ``out_dir``, plus an ``index.html`` linking to all of
    them. Because every page lands in the same directory, the convention-based
    cross-links in :mod:`svdoc.render_html` (``pkg_name.html#member``) always
    resolve correctly, regardless of where the source ``.sv`` files live.

    :param paths: All ``.sv`` files to document. Each is parsed independently
        (one construct per file, same as :func:`svdoc.parser.parse_file`);
        cross-file type resolution runs against the full set for every module.
    :param out_dir: Directory to write the site into. Created if missing.
    :returns: Path to the written ``index.html``.
    :raises ValueError: If any file fails to parse cleanly.
    """
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    docs = [parse_file(p) for p in paths]
    for doc in docs:
        if isinstance(doc, ModuleDoc):
            resolve_types(doc, paths)

    index_lines = ["<h1>svdoc site</h1>", "<ul>"]
    for doc in sorted(docs, key=lambda d: (_KIND_LABELS[type(d)], d.name)):
        page_name = f"{_safe_page_name(doc.name)}.html"
        (out / page_name).write_text(_RENDERERS[type(doc)](doc))
        label = _KIND_LABELS[type(doc)]
        index_lines.append(
            f'<li>{label}: <a href="{escape(page_name)}">{escape(doc.name)}</a></li>'
        )
    index_lines.append("</ul>")

    index_html = render_html.page("svdoc site", index_lines)
    index_path = out / "index.html"
    index_path.write_text(index_html)
    return str(index_path)
