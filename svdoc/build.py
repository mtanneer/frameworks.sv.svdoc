"""svdoc build: a flat multi-page HTML site (one page per construct) with a
navigable index, so cross-links between pages always resolve correctly --
avoids the relative-path problem of generating standalone pages into
whatever directories the source files happen to live in.
"""

import pathlib
import re
import warnings
from html import escape

from . import render_html, render_md
from .ir import ClassDoc, InterfaceDoc, ModuleDoc, PackageDoc
from .parser import build_hierarchy, parse_file, resolve_types

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
    ClassDoc: render_html.render_class,
}
_MD_RENDERERS = {
    ModuleDoc: render_md.render,
    InterfaceDoc: render_md.render_interface,
    PackageDoc: render_md.render_package,
    ClassDoc: render_md.render_class,
}
_KIND_LABELS = {
    ModuleDoc: "Module",
    InterfaceDoc: "Interface",
    PackageDoc: "Package",
    ClassDoc: "Class",
}


def build_site(
    paths: list,
    out_dir: str,
    include_dirs: list | None = None,
    fmt: str = "html",
    diagrams: bool = True,
    strict: bool = False,
) -> str:
    """Parse every file in ``paths`` and write one HTML page per construct
    into a single flat ``out_dir``, plus an ``index.html`` linking to all of
    them. Because every page lands in the same directory, the convention-based
    cross-links in :mod:`svdoc.render_html` (``pkg_name.html#member``) always
    resolve correctly, regardless of where the source ``.sv`` files live.

    :param paths: All ``.sv`` files to document. Each is parsed independently
        (one construct per file, same as :func:`svdoc.parser.parse_file`);
        cross-file type resolution runs against the full set for every module.
    :param out_dir: Directory to write the site into. Created if missing.
    :param include_dirs: Optional directories to search for ```include``
        targets that don't live alongside any file in ``paths`` (e.g. a
        shared ``include/`` directory separate from per-module source dirs).
    :param fmt: ``"html"`` (default) or ``"md"``. Markdown mode writes
        ``<name>.md`` pages cross-linked by relative links plus an
        ``index.md`` of ``[[wikilinks]]`` (Obsidian-friendly).
    :param diagrams: Embed a module symbol diagram in every module page, plus
        an instance-hierarchy diagram for modules that instantiate others
        (Mermaid; ``False`` to opt out).
    :param strict: Raise on the first file that fails to parse. By default such
        files (parse errors, or no module/interface/package/class, e.g.
        program-only files) are skipped with a :class:`UserWarning`.
    :returns: Path to the written index file.
    :raises ValueError: If ``strict`` and any file fails to parse cleanly.

    Pages are named after the construct, so two constructs with the same name
    (even in different directories) would overwrite each other. The first one
    (in ``paths`` order) wins; later ones are skipped with a warning.
    """
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    docs = []
    good_paths = []
    seen = {}  # page name -> source path that claimed it
    for p in paths:
        try:
            doc = parse_file(p, include_dirs)
        except ValueError as e:
            if strict:
                raise
            warnings.warn(f"skipping {p}: {e}", stacklevel=2)
            continue
        page = _safe_page_name(doc.name)
        if page in seen:
            warnings.warn(
                f"skipping {p}: page name '{page}' already used by {seen[page]} (would overwrite it)",
                stacklevel=2,
            )
            continue
        seen[page] = p
        docs.append(doc)
        good_paths.append(p)
    paths = good_paths
    for doc in docs:
        if isinstance(doc, ModuleDoc):
            resolve_types(doc, paths, include_dirs)

    def render_doc(doc, renderers):
        if diagrams and isinstance(doc, ModuleDoc):
            hierarchy = build_hierarchy(doc.name, paths, include_dirs)
            return renderers[ModuleDoc](doc, diagrams=True, hierarchy=hierarchy)
        return renderers[type(doc)](doc)

    if fmt == "md":
        md = ["# svdoc site", ""]
        for doc in sorted(docs, key=lambda d: (_KIND_LABELS[type(d)], d.name)):
            name = _safe_page_name(doc.name)
            (out / f"{name}.md").write_text(render_doc(doc, _MD_RENDERERS))
            md.append(f"- {_KIND_LABELS[type(doc)]}: [[{name}]]")
        index_path = out / "index.md"
        index_path.write_text("\n".join(md) + "\n")
        return str(index_path)

    index_lines = ["<h1>svdoc site</h1>", "<ul>"]
    for doc in sorted(docs, key=lambda d: (_KIND_LABELS[type(d)], d.name)):
        page_name = f"{_safe_page_name(doc.name)}.html"
        (out / page_name).write_text(render_doc(doc, _RENDERERS))
        label = _KIND_LABELS[type(doc)]
        index_lines.append(f'<li>{label}: <a href="{escape(page_name)}">{escape(doc.name)}</a>')
        if isinstance(doc, PackageDoc) and doc.classes:
            index_lines.append("<ul>")
            for c in doc.classes:
                index_lines.append(
                    f'<li>Class: <a href="{escape(page_name)}#{escape(c.name)}">{escape(c.name)}</a></li>'
                )
            index_lines.append("</ul>")
        index_lines.append("</li>")
    index_lines.append("</ul>")

    index_html = render_html.page("svdoc site", index_lines)
    index_path = out / "index.html"
    index_path.write_text(index_html)
    return str(index_path)
