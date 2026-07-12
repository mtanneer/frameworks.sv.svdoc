"""svdoc --fix: insert `///< TODO` next to undocumented ports/params, and a
`/** @brief TODO */` stub above an undocumented module, in place. Mirrors
`ruff --fix` — scaffolds missing docs rather than guessing their content.
"""

import pyslang

from .parser import _leading_doc, _trailing_doc


def _end_offset(node) -> int:
    """node may be a raw Token (comma, closing paren) or a syntax node."""
    tok = node.getLastToken() if hasattr(node, "getLastToken") else node
    return tok.range.end.offset


def _brief_stub(text: str, offset: int) -> str:
    """A `/** @brief TODO */` block stub, indented to match the column the
    node it precedes starts at (mid-file insertions -- e.g. above a nested
    modport -- land at the modport's own indentation, not column 0)."""
    line_start = text.rfind("\n", 0, offset) + 1
    indent = text[line_start:offset]
    return f"/**\n{indent} * @brief TODO\n{indent} */\n{indent}"


def fix_file(path: str) -> bool:
    """Scaffold missing doc comments in place, in ``path``, and save the result.

    Inserts ``///< TODO`` next to any undocumented port/parameter, and a
    ``/** @brief TODO */`` stub above the module/interface/package itself if
    it has no doc comment. Idempotent: re-running on an already-documented
    file makes no changes.

    :param path: Path to the ``.sv`` file to fix in place.
    :returns: ``True`` if the file was modified, ``False`` if it was already
        fully documented.
    :raises ValueError: If the file fails to parse cleanly.
    """
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    with open(path) as f:
        text = f.read()

    # module and interface declarations share the same syntax shape
    # (ModuleDeclarationSyntax, differentiated only by .kind) -- --fix scaffolds
    # their header (params/ports) doc comments identically. Interface bodies
    # (signals/modports) are scaffolded separately below, since modules don't
    # have those constructs.
    mod = next(m for m in tree.root.members if hasattr(m, "header"))
    header = mod.header

    # (offset, text_to_insert), applied back-to-front so earlier offsets stay valid.
    insertions = []

    if _leading_doc(mod) is None:
        offset = mod.getFirstToken().range.start.offset
        insertions.append((offset, _brief_stub(text, offset)))

    if header.parameters:
        raw = list(header.parameters.declarations)
        for i, node in enumerate(raw):
            if node.kind != pyslang.syntax.SyntaxKind.ParameterDeclaration:
                continue
            has_comma = i + 1 < len(raw)
            # trailing ///< doc for this item is leading trivia on the node
            # AFTER its separator (see parser._trailing_doc) -- for the last
            # item there's no comma, so the lookup and insertion point are
            # both the item itself, right before the closing paren.
            lookup = raw[i + 2] if has_comma and i + 2 < len(raw) else header.parameters.closeParen
            if _trailing_doc(lookup) is None:
                offset = _end_offset(raw[i + 1]) if has_comma else _end_offset(node)
                insertions.append((offset, "  ///< TODO"))

    if header.ports:
        raw = list(header.ports.ports)
        for i, node in enumerate(raw):
            if not hasattr(node, "declarator"):
                continue
            has_comma = i + 1 < len(raw)
            lookup = raw[i + 2] if has_comma and i + 2 < len(raw) else header.ports.closeParen
            if _trailing_doc(lookup) is None:
                offset = _end_offset(raw[i + 1]) if has_comma else _end_offset(node)
                insertions.append((offset, "  ///< TODO"))

    if mod.kind == pyslang.syntax.SyntaxKind.InterfaceDeclaration:
        members = list(mod.members)
        for i, m in enumerate(members):
            next_node = members[i + 1] if i + 1 < len(members) else mod.endmodule
            if m.kind == pyslang.syntax.SyntaxKind.DataDeclaration and _trailing_doc(next_node) is None:
                insertions.append((_end_offset(m), "  ///< TODO"))
            elif m.kind == pyslang.syntax.SyntaxKind.ModportDeclaration and _leading_doc(m) is None:
                offset = m.getFirstToken().range.start.offset
                insertions.append((offset, _brief_stub(text, offset)))

    if not insertions:
        return False

    for offset, snippet in sorted(insertions, reverse=True):
        text = text[:offset] + snippet + text[offset:]
    with open(path, "w") as f:
        f.write(text)
    return True
