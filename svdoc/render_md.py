"""Markdown renderer (v1): one ModuleDoc -> one Obsidian-friendly .md string."""
from .ir import ModuleDoc


def render(mod: ModuleDoc) -> str:
    lines = [f"# Module: `{mod.name}`", ""]
    if mod.doc:
        lines += [mod.doc, ""]

    if mod.params:
        lines += ["## Parameters", "", "| Name | Type | Default | Description |",
                   "|---|---|---|---|"]
        for p in mod.params:
            lines.append(f"| `{p.name}` | `{p.type}` | `{p.default or ''}` | {p.doc or ''} |")
        lines.append("")

    if mod.ports:
        lines += ["## Ports", "", "| Name | Direction | Type | Description |",
                   "|---|---|---|---|"]
        for p in mod.ports:
            lines.append(f"| `{p.name}` | {p.direction} | `{p.type}` | {p.doc or ''} |")
        lines.append("")

    return "\n".join(lines)
