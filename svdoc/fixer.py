"""svdoc --fix: insert `///< TODO` next to undocumented ports/params, and a
`/** @brief TODO */` stub above an undocumented module, in place. Mirrors
`ruff --fix` — scaffolds missing docs rather than guessing their content.
"""

import os
import tempfile

import pyslang

from .parser import _leading_doc, _source_manager, _trailing_doc, diag_text, syntax_errors


def _end_offset(node) -> int:
    """node may be a raw Token (comma, closing paren) or a syntax node."""
    tok = node.getLastToken() if hasattr(node, "getLastToken") else node
    return tok.range.end.offset


def _local(node, buf) -> bool:
    """True if ``node`` lies wholly in source buffer ``buf``. Nodes produced by
    macro expansion or ``include`` live in other buffers, so their offsets must
    not be spliced into this file's text."""
    return node.getFirstToken().range.start.buffer == buf and node.getLastToken().range.end.buffer == buf


def _brief_stub(text: bytes, offset: int) -> bytes:
    """A `/** @brief TODO */` block stub, indented to match the column the
    node it precedes starts at (mid-file insertions -- e.g. above a nested
    modport -- land at the modport's own indentation, not column 0)."""
    line_start = text.rfind(b"\n", 0, offset) + 1
    indent = text[line_start:offset].decode("utf-8", "replace")
    return f"/**\n{indent} * @brief TODO\n{indent} */\n{indent}".encode()


def _trailing_stub(text: bytes, offset: int) -> bytes:
    """`///< TODO` stub. If code follows on the same line (e.g. `)(`), the line
    comment would swallow it, so break the line after the stub instead."""
    eol = text.find(b"\n", offset)
    rest = text[offset : eol if eol != -1 else len(text)]
    return b"  ///< TODO" if not rest.strip() else b"  ///< TODO\n"


def _trailing_items(raw, close, text, insertions, is_item):
    """Trailing ``///< TODO`` for each comma-interleaved item in ``raw``
    (enum values, subroutine args): same lookup/insertion rule as ports."""
    for i, node in enumerate(raw):
        if not is_item(node):
            continue
        has_comma = i + 1 < len(raw)
        lookup = raw[i + 2] if has_comma and i + 2 < len(raw) else close
        if _trailing_doc(lookup) is None:
            offset = _end_offset(raw[i + 1]) if has_comma else _end_offset(node)
            insertions.append((offset, _trailing_stub(text, offset)))


def _leading_brief(m, text, insertions):
    if _leading_doc(m) is None:
        offset = m.getFirstToken().range.start.offset
        insertions.append((offset, _brief_stub(text, offset)))


def _scaffold_package(pkg, text, insertions):
    """Typedefs (enum/struct/alias), their values/fields, functions/tasks and
    their args -- mirrors what parse_package reads."""
    kinds = pyslang.syntax.SyntaxKind
    members = list(pkg.members)
    buf = pkg.getFirstToken().range.start.buffer
    for i, m in enumerate(members):
        if not _local(m, buf):
            continue
        next_node = members[i + 1] if i + 1 < len(members) else pkg.endmodule
        if m.kind in (kinds.FunctionDeclaration, kinds.TaskDeclaration):
            _leading_brief(m, text, insertions)
            pl = m.prototype.portList
            if pl is not None:
                _trailing_items(list(pl.ports), pl.closeParen, text, insertions, lambda n: hasattr(n, "declarator"))
        elif m.kind == kinds.TypedefDeclaration:
            if m.type.kind == kinds.EnumType:
                _leading_brief(m, text, insertions)
                _trailing_items(list(m.type.members), m.type.closeBrace, text, insertions, lambda n: hasattr(n, "name"))
            elif m.type.kind == kinds.StructType:
                _leading_brief(m, text, insertions)
                fields = list(m.type.members)
                for j, f in enumerate(fields):
                    nxt = fields[j + 1] if j + 1 < len(fields) else m.type.closeBrace
                    if _trailing_doc(nxt) is None:
                        insertions.append((_end_offset(f), _trailing_stub(text, _end_offset(f))))
            elif _trailing_doc(next_node) is None:  # alias: trailing or leading doc both count
                _leading_brief(m, text, insertions)


def fix_file(path: str, include_dirs: list | None = None) -> bool:
    """Scaffold missing doc comments in place, in ``path``, and save the result.

    Inserts ``///< TODO`` next to any undocumented port/parameter, and a
    ``/** @brief TODO */`` stub above the module/interface/package itself if
    it has no doc comment. In packages, also scaffolds typedefs (enum values,
    struct fields) and functions/tasks (and their arguments). Idempotent: re-running on an already-documented
    file makes no changes.

    :param path: Path to the ``.sv`` file to fix in place.
    :returns: ``True`` if the file was modified, ``False`` if it was already
        fully documented.
    :raises ValueError: If the file fails to parse cleanly.
    """
    tree = pyslang.syntax.SyntaxTree.fromFile(path, _source_manager(include_dirs))
    if syntax_errors(tree):
        raise ValueError(f"parse errors in {path}: {diag_text(tree)}")

    # pyslang offsets are byte offsets: splice bytes, not str.
    with open(path, "rb") as f:
        text = f.read()
    nl = b"\r\n" if b"\r\n" in text else b"\n"

    # module and interface declarations share the same syntax shape
    # (ModuleDeclarationSyntax, differentiated only by .kind) -- --fix scaffolds
    # their header (params/ports) doc comments identically. Interface bodies
    # (signals/modports) are scaffolded separately below, since modules don't
    # have those constructs.
    mod = next((m for m in tree.root.members if hasattr(m, "header")), None)
    if mod is None:
        raise ValueError(f"no module or interface declaration found in {path}")
    header = mod.header
    buf = mod.getFirstToken().range.start.buffer

    # (offset, text_to_insert), applied back-to-front so earlier offsets stay valid.
    insertions = []

    if _leading_doc(mod) is None:
        offset = mod.getFirstToken().range.start.offset
        insertions.append((offset, _brief_stub(text, offset)))

    if header.parameters:
        raw = list(header.parameters.declarations)
        for i, node in enumerate(raw):
            if node.kind != pyslang.syntax.SyntaxKind.ParameterDeclaration or not _local(node, buf):
                continue
            has_comma = i + 1 < len(raw)
            # trailing ///< doc for this item is leading trivia on the node
            # AFTER its separator (see parser._trailing_doc) -- for the last
            # item there's no comma, so the lookup and insertion point are
            # both the item itself, right before the closing paren.
            lookup = raw[i + 2] if has_comma and i + 2 < len(raw) else header.parameters.closeParen
            if _trailing_doc(lookup) is None:
                offset = _end_offset(raw[i + 1]) if has_comma else _end_offset(node)
                insertions.append((offset, _trailing_stub(text, offset)))

    if header.ports:
        raw = list(header.ports.ports)
        for i, node in enumerate(raw):
            if not hasattr(node, "declarator") or not _local(node, buf):
                continue
            has_comma = i + 1 < len(raw)
            lookup = raw[i + 2] if has_comma and i + 2 < len(raw) else header.ports.closeParen
            if _trailing_doc(lookup) is None:
                offset = _end_offset(raw[i + 1]) if has_comma else _end_offset(node)
                insertions.append((offset, _trailing_stub(text, offset)))

    if mod.kind == pyslang.syntax.SyntaxKind.InterfaceDeclaration:
        members = list(mod.members)
        for i, m in enumerate(members):
            if not _local(m, buf):
                continue
            next_node = members[i + 1] if i + 1 < len(members) else mod.endmodule
            if m.kind == pyslang.syntax.SyntaxKind.DataDeclaration and _trailing_doc(next_node) is None:
                insertions.append((_end_offset(m), _trailing_stub(text, _end_offset(m))))
            elif m.kind == pyslang.syntax.SyntaxKind.ModportDeclaration and _leading_doc(m) is None:
                offset = m.getFirstToken().range.start.offset
                insertions.append((offset, _brief_stub(text, offset)))

    if mod.kind == pyslang.syntax.SyntaxKind.PackageDeclaration:
        _scaffold_package(mod, text, insertions)

    if not insertions:
        return False

    for offset, snippet in sorted(insertions, reverse=True):
        if nl != b"\n":
            snippet = snippet.replace(b"\n", nl)
        text = text[:offset] + snippet + text[offset:]

    # never write output that doesn't parse cleanly
    # (path= lets `include resolve relative to the file, same as the first parse)
    check = pyslang.syntax.SyntaxTree.fromText(
        text.decode("utf-8"), _source_manager(include_dirs), os.path.basename(path), os.path.abspath(path)
    )
    if syntax_errors(check):
        raise ValueError(f"--fix would corrupt {path}: {diag_text(check)}; file left unchanged")

    # atomic write: temp file in same dir, then rename
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(text)
        os.chmod(tmp, os.stat(path).st_mode)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    return True
