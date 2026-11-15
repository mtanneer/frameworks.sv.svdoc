"""Markdown renderer: Doc IR -> Obsidian-friendly .md string."""

from .ir import ClassDoc, InterfaceDoc, ModuleDoc, PackageDoc


def _type_cell(type_str: str, type_ref: str) -> str:
    """Relative-link cell, convention-based like the HTML renderer:
    ``pkg::member`` -> ``[pkg::member](pkg.md#member)`` (plain Markdown link,
    works in Obsidian and GitHub; target existence is not verified)."""
    if not type_ref:
        return f"`{type_str}`"
    pkg, _, member = type_ref.partition("::")
    return f"[`{type_ref}`]({pkg}.md#{member})"


def _params_section(params) -> list:
    if not params:
        return []
    lines = [
        "## Parameters",
        "",
        "| Name | Type | Default | Description |",
        "|---|---|---|---|",
    ]
    for p in params:
        lines.append(f"| `{p.name}` | {_type_cell(p.type, p.type_ref)} | `{p.default or ''}` | {p.doc or ''} |")
    lines.append("")
    return lines


def _ports_section(ports) -> list:
    if not ports:
        return []
    lines = [
        "## Ports",
        "",
        "| Name | Direction | Type | Description |",
        "|---|---|---|---|",
    ]
    for p in ports:
        lines.append(f"| `{p.name}` | {p.direction} | {_type_cell(p.type, p.type_ref)} | {p.doc or ''} |")
    lines.append("")
    return lines


def render(mod: ModuleDoc) -> str:
    """Render a :class:`~svdoc.ir.ModuleDoc` to an Obsidian-friendly Markdown string."""
    lines = [f"# Module: `{mod.name}`", ""]
    if mod.doc:
        lines += [mod.doc, ""]
    lines += _params_section(mod.params)
    lines += _ports_section(mod.ports)
    return "\n".join(lines)


def render_interface(iface: InterfaceDoc) -> str:
    """Render an :class:`~svdoc.ir.InterfaceDoc` to an Obsidian-friendly Markdown string."""
    lines = [f"# Interface: `{iface.name}`", ""]
    if iface.doc:
        lines += [iface.doc, ""]
    lines += _params_section(iface.params)
    lines += _ports_section(iface.ports)

    if iface.signals:
        lines += ["## Signals", "", "| Name | Type | Description |", "|---|---|---|"]
        for s in iface.signals:
            lines.append(f"| `{s.name}` | `{s.type}` | {s.doc or ''} |")
        lines.append("")

    if iface.modports:
        lines += ["## Modports", ""]
        for mp in iface.modports:
            lines.append(f"### `{mp.name}`")
            lines.append("")
            if mp.doc:
                lines += [mp.doc, ""]
            lines += ["| Direction | Signals | Description |", "|---|---|---|"]
            for g in mp.port_groups:
                lines.append(f"| {g.direction} | {', '.join(f'`{s}`' for s in g.signals)} | {g.doc or ''} |")
            lines.append("")

    return "\n".join(lines)


def render_package(pkg: PackageDoc) -> str:
    """Render a :class:`~svdoc.ir.PackageDoc` to an Obsidian-friendly Markdown string."""
    lines = [f"# Package: `{pkg.name}`", ""]
    if pkg.doc:
        lines += [pkg.doc, ""]

    for t in pkg.typedefs:
        lines.append(f"## `{t.name}`")
        lines.append("")
        if t.doc:
            lines += [t.doc, ""]

        if t.kind == "enum":
            lines.append(f"Enum (`{t.base_type}`)" if t.base_type else "Enum")
            lines += ["", "| Value | Number | Description |", "|---|---|---|"]
            for v in t.values:
                lines.append(f"| `{v.name}` | {v.value or ''} | {v.doc or ''} |")
            lines.append("")
        elif t.kind == "struct":
            lines.append("Packed struct")
            lines += ["", "| Field | Type | Description |", "|---|---|---|"]
            for f in t.fields:
                lines.append(f"| `{f.name}` | `{f.type}` | {f.doc or ''} |")
            lines.append("")
        else:
            lines.append(f"Alias for `{t.alias_type}`")
            lines.append("")

    for s in pkg.subroutines:
        lines.append(f"## `{s.name}`")
        lines.append("")
        if s.doc:
            lines += [s.doc, ""]
        header = f"Function returning `{s.return_type}`" if s.kind == "function" else "Task"
        lines.append(header)
        lines.append("")
        if s.args:
            lines += ["| Name | Direction | Type | Description |", "|---|---|---|---|"]
            for a in s.args:
                lines.append(f"| `{a.name}` | {a.direction} | `{a.type}` | {a.doc or ''} |")
            lines.append("")

    for c in pkg.classes:
        label = "Virtual class" if c.is_virtual else "Class"
        lines += [f"## {label} `{c.name}`", ""] + _class_body(c, "###")

    return "\n".join(lines)


def _class_body(c: ClassDoc, level: str) -> list:
    """Shared body for a class, used by both the standalone page and package
    sections. ``level`` is the heading prefix for the class's sub-sections."""
    lines = []
    if c.doc:
        lines += [c.doc, ""]
    if c.extends:
        lines += [f"Extends `{c.extends}`", ""]
    for sec in _params_section(c.params):
        lines.append(sec.replace("## ", f"{level} ", 1) if sec.startswith("## ") else sec)
    if c.properties:
        lines += [f"{level} Properties", "", "| Name | Type | Qualifiers | Description |", "|---|---|---|---|"]
        for p in c.properties:
            lines.append(f"| `{p.name}` | `{p.type}` | {' '.join(p.qualifiers)} | {p.doc or ''} |")
        lines.append("")
    if c.methods:
        lines += [f"{level} Methods", ""]
        for s in c.methods:
            quals = " ".join(s.qualifiers)
            kind = f"function returning `{s.return_type}`" if s.kind == "function" and s.return_type else s.kind
            lines.append(f"{level}# `{s.name}`")
            lines.append("")
            if s.doc:
                lines += [s.doc, ""]
            head = f"{quals + ' ' if quals else ''}{kind}"
            lines += [head[0].upper() + head[1:], ""]
            if s.args:
                lines += ["| Name | Direction | Type | Description |", "|---|---|---|---|"]
                for a in s.args:
                    lines.append(f"| `{a.name}` | {a.direction} | `{a.type}` | {a.doc or ''} |")
                lines.append("")
    return lines


def render_class(c: ClassDoc) -> str:
    """Render a :class:`~svdoc.ir.ClassDoc` to an Obsidian-friendly Markdown string."""
    label = "Virtual class" if c.is_virtual else "Class"
    return "\n".join([f"# {label}: `{c.name}`", ""] + _class_body(c, "##"))
