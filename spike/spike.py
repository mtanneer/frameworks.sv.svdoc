"""Phase 0 spike: parse example.sv with pyslang, print module/ports/params
and check how doc comments (leading /** */ and trailing ///<) are exposed
via token trivia.
"""

import pyslang

SRC = "spike/example.sv"


def trivia_text(token):
    return [(t.kind, t.getRawText()) for t in token.trivia]


def leading_comment(node):
    """Block/line comment trivia preceding a node's first token."""
    for t in node.getFirstToken().trivia:
        if t.kind in (
            pyslang.parsing.TriviaKind.BlockComment,
            pyslang.parsing.TriviaKind.LineComment,
        ):
            return t.getRawText()
    return None


def main():
    tree = pyslang.syntax.SyntaxTree.fromFile(SRC)
    print("diagnostics:", list(tree.diagnostics))

    root = tree.root
    mod = next(
        m for m in root.members if m.kind == pyslang.syntax.SyntaxKind.ModuleDeclaration
    )
    header = mod.header

    print("\nmodule:", header.name.valueText)
    print("doc comment:\n", leading_comment(mod))

    print("\n-- parameters --")
    decls = [
        d
        for d in header.parameters.declarations
        if d.kind == pyslang.syntax.SyntaxKind.ParameterDeclaration
    ]
    for i, d in enumerate(decls):
        # trailing ///< comment for item i shows up as LEADING trivia on
        # item i+1's first token (or the closing paren token, for the last item).
        next_node = decls[i + 1] if i + 1 < len(decls) else header.parameters.closeParen
        trailing = None
        for t in (
            next_node.getFirstToken().trivia
            if hasattr(next_node, "getFirstToken")
            else next_node.trivia
        ):
            if t.kind == pyslang.parsing.TriviaKind.LineComment:
                trailing = t.getRawText()
                break
        print(f"  {d.declarators[0].name.valueText}: trailing_doc={trailing!r}")

    print("\n-- ports --")
    ports = [
        p for p in header.ports.ports if p.kind != pyslang.syntax.SyntaxKind.Unknown
    ]
    ports = list(header.ports.ports)
    port_decls = [p for p in ports if hasattr(p, "declarator")]
    for i, p in enumerate(port_decls):
        next_node = (
            port_decls[i + 1] if i + 1 < len(port_decls) else header.ports.closeParen
        )
        trailing = None
        tok = (
            next_node.getFirstToken()
            if hasattr(next_node, "getFirstToken")
            else next_node
        )
        for t in tok.trivia:
            if t.kind == pyslang.parsing.TriviaKind.LineComment:
                trailing = t.getRawText()
                break
        print(f"  {p.declarator.name.valueText}: trailing_doc={trailing!r}")


if __name__ == "__main__":
    main()
