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


def fix_file(path: str) -> bool:
    """Returns True if the file was modified."""
    tree = pyslang.syntax.SyntaxTree.fromFile(path, pyslang.SourceManager())
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    # module and interface declarations share the same syntax shape
    # (ModuleDeclarationSyntax, differentiated only by .kind) -- --fix scaffolds
    # their header (params/ports) doc comments identically. Body constructs
    # (interface signals/modports) aren't scaffolded here yet.
    mod = next(m for m in tree.root.members if hasattr(m, "header"))
    header = mod.header

    # (offset, text_to_insert), applied back-to-front so earlier offsets stay valid.
    insertions = []

    if _leading_doc(mod) is None:
        offset = mod.getFirstToken().range.start.offset
        insertions.append((offset, "/**\n * @brief TODO\n */\n"))

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

    if not insertions:
        return False

    with open(path) as f:
        text = f.read()
    for offset, snippet in sorted(insertions, reverse=True):
        text = text[:offset] + snippet + text[offset:]
    with open(path, "w") as f:
        f.write(text)
    return True
