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


def _module_children_and_interface_edges(inst: Instance):
    """Split ``inst.children`` into real module instances and interface-mediated
    edges between them.

    Interface instances (``is_interface``) are plumbing, not architecture --
    they're dropped as their own nodes. Instead, for each interface instance
    among the children, every module-instance sibling with a port connected
    to it (via ``PortConnection.interface_instance``) is paired up and
    connected directly, labeled with the modport(s) involved.

    :returns: ``(module_children, edges)`` where ``edges`` is a list of
        ``(instance_a, modport_a, instance_b, modport_b)`` tuples.
    """
    module_children = [c for c in inst.children if not c.is_interface]
    interface_children = [c for c in inst.children if c.is_interface]

    edges = []
    for iface in interface_children:
        users = []
        for mod_child in module_children:
            for conn in mod_child.connections:
                if conn.interface_instance == iface.name:
                    users.append((mod_child, conn.modport))
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                (inst_a, modport_a), (inst_b, modport_b) = users[i], users[j]
                edges.append((inst_a, modport_a, inst_b, modport_b))

    return module_children, edges


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
        module_children, edges = _module_children_and_interface_edges(inst)
        if depth >= max_depth and module_children:
            more_id = f"{node_id}_more"
            lines.append(f'  {more_id}["... {len(module_children)} more"]')
            lines.append(f"  {node_id} --> {more_id}")
            return
        for child in module_children:
            walk(child, depth + 1, node_id)
        for inst_a, modport_a, inst_b, modport_b in edges:
            label = f"{modport_a}/{modport_b}" if modport_a != modport_b else modport_a
            lines.append(f"  {_sanitize_id(inst_a.path)} -.{label}.-> {_sanitize_id(inst_b.path)}")

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
        module_children, edges = _module_children_and_interface_edges(inst)
        if depth >= max_depth and module_children:
            more_id = f"{node_id}_more"
            lines.append(f'  "{more_id}" [label="... {len(module_children)} more", style=dashed];')
            lines.append(f'  "{node_id}" -> "{more_id}";')
            return
        for inst_a, modport_a, inst_b, modport_b in edges:
            label = f"{modport_a}/{modport_b}" if modport_a != modport_b else modport_a
            a_id, b_id = _sanitize_id(inst_a.path), _sanitize_id(inst_b.path)
            lines.append(f'  "{a_id}" -> "{b_id}" [label="{label}", style=dashed, dir=none];')
        for child in module_children:
            walk(child, depth + 1, node_id)

    walk(root, 0, None)
    lines.append("}")
    return "\n".join(lines) + "\n"
