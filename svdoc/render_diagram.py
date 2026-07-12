"""Diagram renderers: Doc/hierarchy IR -> Mermaid or Graphviz dot text.

Both formats are plain text -- no `graphviz` binding or `dot` binary
dependency, matching the existing md/html renderers' IR-only contract.
"""

from .ir import Instance, ModuleDoc

# Depth past which hierarchical diagrams collapse remaining children into a
# single placeholder node, to keep large SoC-scale trees readable.
DEFAULT_MAX_DEPTH = 4


def _sanitize_id(path: str) -> str:
    """Turn a hierarchical path (may contain `.`, `[`, `]`) into a safe node id."""
    return path.replace(".", "_").replace("[", "_").replace("]", "_")


def render_module_symbol_mermaid(mod: ModuleDoc) -> str:
    """Single-module box + ports, as a Mermaid flowchart."""
    lines = ["flowchart LR", f'  subgraph {_sanitize_id(mod.name)}["{mod.name}"]']
    for p in mod.ports:
        pid = f"{_sanitize_id(mod.name)}_{_sanitize_id(p.name)}"
        lines.append(f'    {pid}["{p.name}: {p.direction}"]')
    lines.append("  end")
    return "\n".join(lines) + "\n"


def render_module_symbol_dot(mod: ModuleDoc) -> str:
    """Single-module box + ports, as Graphviz dot source."""
    lines = [f'digraph "{mod.name}" {{', "  rankdir=LR;", "  node [shape=box];"]
    label_rows = "|".join(f"<{p.name}> {p.name}: {p.direction}" for p in mod.ports)
    label = f"{{{mod.name}|{{{label_rows}}}}}" if mod.ports else mod.name
    lines.append(f'  "{mod.name}" [shape=record, label="{label}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_hierarchy_mermaid(root: Instance, max_depth: int = DEFAULT_MAX_DEPTH) -> str:
    """Hierarchical instance tree as a Mermaid flowchart, depth-limited."""
    lines = ["flowchart TD"]

    def add_node(node_id, inst, parent_id=None):
        label = f"{inst.name}\\n({inst.module})"
        lines.append(f'  {node_id}["{label}"]')
        if parent_id:
            lines.append(f"  {parent_id} --> {node_id}")

    def walk(inst, depth, parent_id):
        node_id = _sanitize_id(inst.path)
        add_node(node_id, inst, parent_id)
        if depth >= max_depth and inst.children:
            more_id = f"{node_id}_more"
            lines.append(f'  {more_id}["... {len(inst.children)} more"]')
            lines.append(f"  {node_id} --> {more_id}")
            return
        for child in inst.children:
            walk(child, depth + 1, node_id)

    walk(root, 0, None)
    return "\n".join(lines) + "\n"


def render_hierarchy_dot(root: Instance, max_depth: int = DEFAULT_MAX_DEPTH) -> str:
    """Hierarchical instance tree as Graphviz dot source, depth-limited."""
    lines = [f'digraph "{root.name}" {{', "  node [shape=box];"]

    def walk(inst, depth, parent_id):
        node_id = _sanitize_id(inst.path)
        label = f"{inst.name}\\n({inst.module})"
        lines.append(f'  "{node_id}" [label="{label}"];')
        if parent_id:
            lines.append(f'  "{parent_id}" -> "{node_id}";')
        if depth >= max_depth and inst.children:
            more_id = f"{node_id}_more"
            lines.append(f'  "{more_id}" [label="... {len(inst.children)} more", style=dashed];')
            lines.append(f'  "{node_id}" -> "{more_id}";')
            return
        for child in inst.children:
            walk(child, depth + 1, node_id)

    walk(root, 0, None)
    lines.append("}")
    return "\n".join(lines) + "\n"
