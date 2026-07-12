"""AST walker: pyslang SyntaxTree -> Doc IR. See PLAN.md Phase 1 (modules) and
Phase 2 (interfaces/modports).
"""

import re
from typing import Optional

import pyslang

from .ir import (
    EnumValue,
    InterfaceDoc,
    Modport,
    ModportPortGroup,
    ModuleDoc,
    PackageDoc,
    Param,
    Port,
    Signal,
    StructField,
    Subroutine,
    Typedef,
)

_DOC_KINDS = (
    pyslang.parsing.TriviaKind.BlockComment,
    pyslang.parsing.TriviaKind.LineComment,
)


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
    tok = (
        next_node.getFirstToken() if hasattr(next_node, "getFirstToken") else next_node
    )
    for t in tok.trivia:
        if t.kind == pyslang.parsing.TriviaKind.LineComment:
            return _clean(t.getRawText())
    return None


def _parse_params(header) -> list:
    if not header.parameters:
        return []
    params = []
    decls = [
        d
        for d in header.parameters.declarations
        if d.kind == pyslang.syntax.SyntaxKind.ParameterDeclaration
    ]
    for i, d in enumerate(decls):
        next_node = decls[i + 1] if i + 1 < len(decls) else header.parameters.closeParen
        declarator = d.declarators[0]
        params.append(
            Param(
                name=declarator.name.valueText,
                type=_type_str(d.type),
                default=_type_str(declarator.initializer.expr)
                if declarator.initializer
                else None,
                doc=_trailing_doc(next_node),
            )
        )
    return params


def _port_direction_and_type(port_header) -> tuple:
    """Port headers come in different syntax shapes depending on whether the
    port is a plain data type (VariablePortHeader, has .direction/.dataType)
    or an interface reference (InterfacePortHeader, e.g. `some_if.modport
    name` -- no direction, "type" is the interface[.modport] name instead)."""
    if port_header.kind == pyslang.syntax.SyntaxKind.InterfacePortHeader:
        iface_name = _type_str(port_header.nameOrKeyword)
        modport = _type_str(port_header.modport) if port_header.modport else ""
        return "interface", f"{iface_name}{modport}"
    return port_header.direction.valueText, _type_str(port_header.dataType)


def _parse_ports(header) -> list:
    if not header.ports:
        return []
    ports = []
    port_decls = [p for p in header.ports.ports if hasattr(p, "declarator")]
    for i, p in enumerate(port_decls):
        next_node = (
            port_decls[i + 1] if i + 1 < len(port_decls) else header.ports.closeParen
        )
        direction, type_str = _port_direction_and_type(p.header)
        ports.append(
            Port(
                name=p.declarator.name.valueText,
                direction=direction,
                type=type_str,
                doc=_trailing_doc(next_node),
            )
        )
    return ports


def _find_declaration(tree, kind):
    return next(m for m in tree.root.members if m.kind == kind)


def parse_module(path: str) -> ModuleDoc:
    """Parse a ``.sv`` file containing a single module declaration.

    :param path: Path to the ``.sv`` file. Only the first module found in the
        file is parsed.
    :returns: The module's :class:`~svdoc.ir.ModuleDoc`.
    :raises ValueError: If the file fails to parse cleanly.
    """
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
    """Parse a ``.sv`` file containing a single module, interface, or package.

    Dispatches to :func:`parse_module`, :func:`parse_interface`, or
    :func:`parse_package` based on the syntax kind of the first top-level
    declaration found.

    :param path: Path to the ``.sv`` file.
    :returns: A :class:`~svdoc.ir.ModuleDoc`, :class:`~svdoc.ir.InterfaceDoc`,
        or :class:`~svdoc.ir.PackageDoc`, matching whichever construct was found.
    :raises ValueError: If the file fails to parse cleanly.
    """
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")
    kind = next(
        m.kind
        for m in tree.root.members
        if hasattr(m, "header") or hasattr(m, "members")
    )
    if kind == pyslang.syntax.SyntaxKind.InterfaceDeclaration:
        return parse_interface(path)
    if kind == pyslang.syntax.SyntaxKind.PackageDeclaration:
        return parse_package(path)
    return parse_module(path)


def resolve_types(doc, paths: list) -> None:
    """Resolve cross-file port types by elaborating a full ``Compilation``.

    Given a :class:`~svdoc.ir.ModuleDoc` (or :class:`~svdoc.ir.InterfaceDoc`)
    already parsed from a single file via :func:`parse_module` /
    :func:`parse_file`, and the full list of files it should be elaborated
    alongside (e.g. packages it imports types from), patches each
    :class:`~svdoc.ir.Port`'s ``type_ref`` with the fully-qualified
    ``"package::type"`` name for any port whose type resolves to a type
    defined in another file. Mutates ``doc`` in place.

    Only meaningful for modules today: a bare interface never becomes an
    elaborated top-level instance, so this is a no-op when ``doc.name`` can't
    be found among the compilation's top instances.

    :param doc: An already-parsed module (or interface) doc to patch in place.
    :param paths: All ``.sv`` files needed to elaborate ``doc``, including the
        file it was originally parsed from.
    :raises ValueError: If any of the given files fails to parse cleanly.
    """
    # Without an explicit topModules list, slang only elaborates modules that
    # nothing else instantiates -- e.g. in a full multi-module design, most
    # modules are instantiated by something else and would silently vanish
    # from topInstances, making resolve_types() a no-op for them. Forcing
    # doc.name as an explicit top module means it's elaborated on its own
    # regardless of whether other files in `paths` also instantiate it.
    opts = pyslang.ast.CompilationOptions()
    opts.topModules = {doc.name}
    bag = pyslang.Bag()
    bag.compilationOptions = opts

    sm = pyslang.SourceManager()
    comp = pyslang.ast.Compilation(bag)
    for p in paths:
        tree = pyslang.syntax.SyntaxTree.fromFile(p, sm)
        if tree.diagnostics:
            raise ValueError(f"parse errors in {p}: {list(tree.diagnostics)}")
        comp.addSyntaxTree(tree)

    inst = next((i for i in comp.getRoot().topInstances if i.name == doc.name), None)
    if inst is None:
        return

    # Two port symbol shapes: plain data-type ports (SymbolKind.Port, has
    # .type) resolve to a package-qualified type string like "pkg::type".
    # Interface-typed ports (SymbolKind.InterfacePort, e.g. `some_if.modport
    # name`) have no .type but do have .interfaceDef/.modport -- resolved the
    # same way into "ifname::modport" so the HTML renderer's existing
    # pkg::type cross-linking machinery (_type_cell) handles both uniformly.
    resolved = {}
    interface_ports = {}  # port name -> (interface name, modport name)
    for p in inst.body.portList:
        if hasattr(p, "type"):
            resolved[p.name] = str(p.type)
        elif p.kind == pyslang.ast.SymbolKind.InterfacePort and p.interfaceDef:
            resolved[p.name] = f"{p.interfaceDef.name}::{p.modport}"
            interface_ports[p.name] = (p.interfaceDef.name, str(p.modport))

    # For an inline HTML preview of the modport's ins/outs (not just a link
    # to it), parse whichever of `paths` is that interface and grab the
    # matching Modport object directly -- skip files that don't parse as an
    # interface (modules/packages among `paths`), and only do this for
    # interfaces actually referenced by a port, not every file.
    needed_interfaces = {iface for iface, _ in interface_ports.values()}
    interface_docs = {}
    for p in paths:
        if not needed_interfaces:
            break
        parsed = parse_file(p)
        if isinstance(parsed, InterfaceDoc) and parsed.name in needed_interfaces:
            interface_docs[parsed.name] = parsed
            needed_interfaces.discard(parsed.name)

    for port in doc.ports:
        type_str = resolved.get(port.name)
        if type_str and "::" in type_str:
            port.type_ref = type_str
        if port.name in interface_ports:
            iface_name, modport_name = interface_ports[port.name]
            iface_doc = interface_docs.get(iface_name)
            if iface_doc:
                port.modport_preview = next(
                    (mp for mp in iface_doc.modports if mp.name == modport_name),
                    None,
                )


def parse_interface(path: str) -> InterfaceDoc:
    """Parse a ``.sv`` file containing a single interface declaration.

    :param path: Path to the ``.sv`` file. Only the first interface found in
        the file is parsed.
    :returns: The interface's :class:`~svdoc.ir.InterfaceDoc`, including its
        signals and modports.
    :raises ValueError: If the file fails to parse cleanly.
    """
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
            doc.signals.append(
                Signal(
                    name=declarator.name.valueText,
                    type=_type_str(m.type),
                    doc=_trailing_doc(next_node),
                )
            )
        elif m.kind == pyslang.syntax.SyntaxKind.ModportDeclaration:
            item = m.items[0]
            modport = Modport(name=item.name.valueText, doc=_leading_doc(m))
            raw_groups = [g for g in item.ports.ports if hasattr(g, "direction")]
            for j, g in enumerate(raw_groups):
                group_next = (
                    raw_groups[j + 1]
                    if j + 1 < len(raw_groups)
                    else item.ports.closeParen
                )
                # g.ports is comma-interleaved (ModportNamedPort nodes plus
                # comma tokens) when a direction covers multiple signals
                # (e.g. "input a, b, c") -- filter to named-port nodes only.
                signal_names = [
                    p.name.valueText for p in g.ports if hasattr(p, "name")
                ]
                modport.port_groups.append(
                    ModportPortGroup(
                        direction=g.direction.valueText,
                        signals=signal_names,
                        doc=_trailing_doc(group_next),
                    )
                )
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
        values.append(
            EnumValue(
                name=n.name.valueText,
                value=_type_str(n.initializer.expr) if n.initializer else None,
                doc=_trailing_doc(next_node),
            )
        )
    return values


def _parse_struct_fields(struct_type) -> list:
    raw = list(struct_type.members)
    fields = []
    for i, f in enumerate(raw):
        next_node = raw[i + 1] if i + 1 < len(raw) else struct_type.closeBrace
        fields.append(
            StructField(
                name=f.declarators[0].name.valueText,
                type=_type_str(f.type),
                doc=_trailing_doc(next_node),
            )
        )
    return fields


def _parse_subroutine_args(port_list) -> list:
    if port_list is None:
        return []
    # comma-interleaved like params/ports/enum members -- filter to
    # declarators first so next-item lookups skip over comma tokens.
    decls = [p for p in port_list.ports if hasattr(p, "declarator")]
    args = []
    for i, p in enumerate(decls):
        next_node = decls[i + 1] if i + 1 < len(decls) else port_list.closeParen
        args.append(
            Port(
                name=p.declarator.name.valueText,
                direction=p.direction.valueText if p.direction else "input",
                type=_type_str(p.dataType),
                doc=_trailing_doc(next_node),
            )
        )
    return args


def _parse_subroutine(m, kind: str) -> Subroutine:
    proto = m.prototype
    return_type = _type_str(proto.returnType) if kind == "function" else None
    return Subroutine(
        name=str(proto.name).strip(),
        doc=_leading_doc(m),
        kind=kind,
        return_type=return_type,
        args=_parse_subroutine_args(proto.portList),
    )


def parse_package(path: str) -> PackageDoc:
    """Parse a ``.sv`` file containing a single package declaration.

    :param path: Path to the ``.sv`` file. Only the first package found in
        the file is parsed.
    :returns: The package's :class:`~svdoc.ir.PackageDoc`, including its
        typedefs (enums, structs, aliases) and subroutines (functions, tasks).
    :raises ValueError: If the file fails to parse cleanly.
    """
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    pkg = _find_declaration(tree, pyslang.syntax.SyntaxKind.PackageDeclaration)
    doc = PackageDoc(name=pkg.header.name.valueText, doc=_leading_doc(pkg))

    members = list(pkg.members)
    for i, m in enumerate(members):
        next_node = members[i + 1] if i + 1 < len(members) else pkg.endmodule
        if m.kind == pyslang.syntax.SyntaxKind.FunctionDeclaration:
            doc.subroutines.append(_parse_subroutine(m, "function"))
        elif m.kind == pyslang.syntax.SyntaxKind.TaskDeclaration:
            doc.subroutines.append(_parse_subroutine(m, "task"))
        elif m.kind == pyslang.syntax.SyntaxKind.TypedefDeclaration:
            if m.type.kind == pyslang.syntax.SyntaxKind.EnumType:
                doc.typedefs.append(
                    Typedef(
                        name=m.name.valueText,
                        doc=_leading_doc(m),
                        kind="enum",
                        base_type=_type_str(m.type.baseType)
                        if m.type.baseType
                        else None,
                        values=_parse_enum_values(m.type),
                    )
                )
            elif m.type.kind == pyslang.syntax.SyntaxKind.StructType:
                doc.typedefs.append(
                    Typedef(
                        name=m.name.valueText,
                        doc=_leading_doc(m),
                        kind="struct",
                        fields=_parse_struct_fields(m.type),
                    )
                )
            else:
                doc.typedefs.append(
                    Typedef(
                        name=m.name.valueText,
                        doc=_trailing_doc(next_node) or _leading_doc(m),
                        kind="alias",
                        alias_type=_type_str(m.type),
                    )
                )

    return doc
