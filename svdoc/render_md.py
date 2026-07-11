"""Markdown renderer: Doc IR -> Obsidian-friendly .md string."""
from .ir import InterfaceDoc, ModuleDoc


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
        lines.append(f"| `{p.name}` | {p.direction} | `{p.type}` | {p.doc or ''} |")
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
