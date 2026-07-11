"""Markdown renderer: Doc IR -> Obsidian-friendly .md string."""
from .ir import InterfaceDoc, ModuleDoc, PackageDoc


def _params_section(params) -> list:
    if not params:
        return []
    lines = ["## Parameters", "", "| Name | Type | Default | Description |", "|---|---|---|---|"]
    for p in params:
        lines.append(f"| `{p.name}` | `{p.type}` | `{p.default or ''}` | {p.doc or ''} |")
    lines.append("")
    return lines


def _ports_section(ports) -> list:
    if not ports:
        return []
    lines = ["## Ports", "", "| Name | Direction | Type | Description |", "|---|---|---|---|"]
    for p in ports:
        lines.append(f"| `{p.name}` | {p.direction} | `{p.type_ref or p.type}` | {p.doc or ''} |")
    lines.append("")
    return lines


def render(mod: ModuleDoc) -> str:
    lines = [f"# Module: `{mod.name}`", ""]
    if mod.doc:
        lines += [mod.doc, ""]
    lines += _params_section(mod.params)
    lines += _ports_section(mod.ports)
    return "\n".join(lines)


def render_interface(iface: InterfaceDoc) -> str:
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

    return "\n".join(lines)
