"""AST walker: pyslang SyntaxTree -> Doc IR. See PLAN.md Phase 1 (modules) and
Phase 2 (interfaces/modports).
"""
import re
from typing import Optional

import pyslang

from .ir import (
    EnumValue, InterfaceDoc, Modport, ModportPortGroup, ModuleDoc, PackageDoc,
    Param, Port, Signal, StructField, Typedef,
)

_DOC_KINDS = (pyslang.parsing.TriviaKind.BlockComment, pyslang.parsing.TriviaKind.LineComment)


def _clean(text: str) -> str:
    """Strip comment delimiters (/** */, ///<, //) and leading '*'/whitespace."""
    text = text.strip()
    text = re.sub(r"^/\*\*?|\*/$", "", text)
    text = re.sub(r"^///<?|^//", "", text)
    lines = [re.sub(r"^\s*\*\s?", "", ln) for ln in text.splitlines()]
    return "\n".join(ln.strip() for ln in lines).strip()


def _leading_doc(node) -> Optional[str]:
    """A node's own doc comment is the LAST block/line comment in its leading
    trivia -- an earlier one may belong to a preceding sibling's trailing
    ///< comment (see _trailing_doc), so take the one closest to the node."""
    doc = None
    for t in node.getFirstToken().trivia:
        if t.kind in _DOC_KINDS:
            doc = t.getRawText()
    return _clean(doc) if doc else None


def _type_str(node) -> str:
    """str(node) includes leading trivia (whitespace, and any comments that
    belong to a preceding sibling's trailing ///< doc) -- strip comment lines
    so only the actual type text remains."""
    text = re.sub(r"//.*", "", str(node))
    return " ".join(text.split())


def _trailing_doc(next_node) -> Optional[str]:
    """Doxygen ///< trailing comments attach as leading trivia on the *next*
    item in the list (see Phase 0 spike findings in PLAN.md)."""
    tok = next_node.getFirstToken() if hasattr(next_node, "getFirstToken") else next_node
    for t in tok.trivia:
        if t.kind == pyslang.parsing.TriviaKind.LineComment:
            return _clean(t.getRawText())
    return None


def _parse_params(header) -> list:
    if not header.parameters:
        return []
    params = []
    decls = [
        d for d in header.parameters.declarations
        if d.kind == pyslang.syntax.SyntaxKind.ParameterDeclaration
    ]
    for i, d in enumerate(decls):
        next_node = decls[i + 1] if i + 1 < len(decls) else header.parameters.closeParen
        declarator = d.declarators[0]
        params.append(Param(
            name=declarator.name.valueText,
            type=_type_str(d.type),
            default=_type_str(declarator.initializer.expr) if declarator.initializer else None,
            doc=_trailing_doc(next_node),
        ))
    return params


def _parse_ports(header) -> list:
    if not header.ports:
        return []
    ports = []
    port_decls = [p for p in header.ports.ports if hasattr(p, "declarator")]
    for i, p in enumerate(port_decls):
        next_node = port_decls[i + 1] if i + 1 < len(port_decls) else header.ports.closeParen
        ports.append(Port(
            name=p.declarator.name.valueText,
            direction=p.header.direction.valueText,
            type=_type_str(p.header.dataType),
            doc=_trailing_doc(next_node),
        ))
    return ports


def _find_declaration(tree, kind):
    return next(m for m in tree.root.members if m.kind == kind)


def parse_module(path: str) -> ModuleDoc:
    # fromFile's default SourceManager caches file contents by path across
    # calls in the same process, so a fresh SourceManager avoids seeing a
    # stale read of a file that was modified earlier in this process
    # (e.g. by --fix, or in tests that fix then re-parse the same path).
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    mod = _find_declaration(tree, pyslang.syntax.SyntaxKind.ModuleDeclaration)
    header = mod.header
    return ModuleDoc(
        name=header.name.valueText,
        doc=_leading_doc(mod),
        params=_parse_params(header),
        ports=_parse_ports(header),
    )


def parse_file(path: str):
    """Parse a .sv file containing a single module, interface, or package,
    returning whichever of ModuleDoc / InterfaceDoc / PackageDoc matches."""
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")
    kind = next(m.kind for m in tree.root.members if hasattr(m, "header") or hasattr(m, "members"))
    if kind == pyslang.syntax.SyntaxKind.InterfaceDeclaration:
        return parse_interface(path)
    if kind == pyslang.syntax.SyntaxKind.PackageDeclaration:
        return parse_package(path)
    return parse_module(path)


def resolve_types(doc, paths: list) -> None:
    """Cross-file type resolution: given a ModuleDoc/InterfaceDoc already
    parsed from a single file, and the full list of files it should be
    elaborated alongside, patch Port/Param.type_ref with the fully-qualified
    "package::type" name for any port/param whose type resolves to a type
    defined in a package (only possible with the other files present).
    Mutates doc in place; a no-op if the construct isn't found as a
    top-level instance (interfaces aren't instantiated on their own, so this
    only actually resolves anything useful for modules today)."""
    sm = pyslang.SourceManager()
    comp = pyslang.ast.Compilation()
    for p in paths:
        tree = pyslang.syntax.SyntaxTree.fromFile(p, sm)
        if tree.diagnostics:
            raise ValueError(f"parse errors in {p}: {list(tree.diagnostics)}")
        comp.addSyntaxTree(tree)

    inst = next((i for i in comp.getRoot().topInstances if i.name == doc.name), None)
    if inst is None:
        return

    resolved = {p.name: str(p.type) for p in inst.body.portList}
    for port in doc.ports:
        type_str = resolved.get(port.name)
        if type_str and "::" in type_str:
            port.type_ref = type_str


def parse_interface(path: str) -> InterfaceDoc:
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    iface = _find_declaration(tree, pyslang.syntax.SyntaxKind.InterfaceDeclaration)
    header = iface.header
    doc = InterfaceDoc(
        name=header.name.valueText,
        doc=_leading_doc(iface),
        params=_parse_params(header),
        ports=_parse_ports(header),
    )

    members = list(iface.members)
    for i, m in enumerate(members):
        next_node = members[i + 1] if i + 1 < len(members) else iface.endmodule
        if m.kind == pyslang.syntax.SyntaxKind.DataDeclaration:
            declarator = m.declarators[0]
            doc.signals.append(Signal(
                name=declarator.name.valueText,
                type=_type_str(m.type),
                doc=_trailing_doc(next_node),
            ))
        elif m.kind == pyslang.syntax.SyntaxKind.ModportDeclaration:
            item = m.items[0]
            modport = Modport(name=item.name.valueText, doc=_leading_doc(m))
            raw_groups = [g for g in item.ports.ports if hasattr(g, "direction")]
            for j, g in enumerate(raw_groups):
                group_next = raw_groups[j + 1] if j + 1 < len(raw_groups) else item.ports.closeParen
                modport.port_groups.append(ModportPortGroup(
                    direction=g.direction.valueText,
                    signals=[p.name.valueText for p in g.ports],
                    doc=_trailing_doc(group_next),
                ))
            doc.modports.append(modport)

    return doc


def _parse_enum_values(enum_type) -> list:
    # members is comma-interleaved (like params/ports) -- filter to just the
    # declarators so "next item" lookups skip over comma tokens, same fix as
    # the param/port comma-interleaving bug found in Phase 1's --fix.
    decls = [n for n in enum_type.members if hasattr(n, "name")]
    values = []
    for i, n in enumerate(decls):
        next_node = decls[i + 1] if i + 1 < len(decls) else enum_type.closeBrace
        values.append(EnumValue(
            name=n.name.valueText,
            value=_type_str(n.initializer.expr) if n.initializer else None,
            doc=_trailing_doc(next_node),
        ))
    return values


def _parse_struct_fields(struct_type) -> list:
    raw = list(struct_type.members)
    fields = []
    for i, f in enumerate(raw):
        next_node = raw[i + 1] if i + 1 < len(raw) else struct_type.closeBrace
        fields.append(StructField(
            name=f.declarators[0].name.valueText,
            type=_type_str(f.type),
            doc=_trailing_doc(next_node),
        ))
    return fields


def parse_package(path: str) -> PackageDoc:
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    pkg = _find_declaration(tree, pyslang.syntax.SyntaxKind.PackageDeclaration)
    doc = PackageDoc(name=pkg.header.name.valueText, doc=_leading_doc(pkg))

    members = list(pkg.members)
    for i, m in enumerate(members):
        if m.kind != pyslang.syntax.SyntaxKind.TypedefDeclaration:
            continue
        next_node = members[i + 1] if i + 1 < len(members) else pkg.endmodule
        if m.type.kind == pyslang.syntax.SyntaxKind.EnumType:
            doc.typedefs.append(Typedef(
                name=m.name.valueText, doc=_leading_doc(m), kind="enum",
                base_type=_type_str(m.type.baseType) if m.type.baseType else None,
                values=_parse_enum_values(m.type),
            ))
        elif m.type.kind == pyslang.syntax.SyntaxKind.StructType:
            doc.typedefs.append(Typedef(
                name=m.name.valueText, doc=_leading_doc(m), kind="struct",
                fields=_parse_struct_fields(m.type),
            ))
        else:
            doc.typedefs.append(Typedef(
                name=m.name.valueText, doc=_trailing_doc(next_node) or _leading_doc(m),
                kind="alias", alias_type=_type_str(m.type),
            ))

    return doc
