"""AST walker: pyslang SyntaxTree -> Doc IR (module-only, Phase 1)."""
import re
from typing import Optional

import pyslang

from .ir import ModuleDoc, Param, Port

_DOC_KINDS = (pyslang.parsing.TriviaKind.BlockComment, pyslang.parsing.TriviaKind.LineComment)


def _clean(text: str) -> str:
    """Strip comment delimiters (/** */, ///<, //) and leading '*'/whitespace."""
    text = text.strip()
    text = re.sub(r"^/\*\*?|\*/$", "", text)
    text = re.sub(r"^///<?|^//", "", text)
    lines = [re.sub(r"^\s*\*\s?", "", ln) for ln in text.splitlines()]
    return "\n".join(ln.strip() for ln in lines).strip()


def _leading_doc(node) -> Optional[str]:
    for t in node.getFirstToken().trivia:
        if t.kind in _DOC_KINDS:
            return _clean(t.getRawText())
    return None


def _trailing_doc(next_node) -> Optional[str]:
    """Doxygen ///< trailing comments attach as leading trivia on the *next*
    item in the list (see Phase 0 spike findings in PLAN.md)."""
    tok = next_node.getFirstToken() if hasattr(next_node, "getFirstToken") else next_node
    for t in tok.trivia:
        if t.kind == pyslang.parsing.TriviaKind.LineComment:
            return _clean(t.getRawText())
    return None


def parse_module(path: str) -> ModuleDoc:
    tree = pyslang.syntax.SyntaxTree.fromFile(path)
    if tree.diagnostics:
        raise ValueError(f"parse errors in {path}: {list(tree.diagnostics)}")

    mod = next(
        m for m in tree.root.members
        if m.kind == pyslang.syntax.SyntaxKind.ModuleDeclaration
    )
    header = mod.header
    doc = ModuleDoc(name=header.name.valueText, doc=_leading_doc(mod))

    if header.parameters:
        decls = [
            d for d in header.parameters.declarations
            if d.kind == pyslang.syntax.SyntaxKind.ParameterDeclaration
        ]
        for i, d in enumerate(decls):
            next_node = decls[i + 1] if i + 1 < len(decls) else header.parameters.closeParen
            declarator = d.declarators[0]
            doc.params.append(Param(
                name=declarator.name.valueText,
                type=str(d.type).strip(),
                default=str(declarator.initializer.expr).strip() if declarator.initializer else None,
                doc=_trailing_doc(next_node),
            ))

    if header.ports:
        port_decls = [p for p in header.ports.ports if hasattr(p, "declarator")]
        for i, p in enumerate(port_decls):
            next_node = port_decls[i + 1] if i + 1 < len(port_decls) else header.ports.closeParen
            doc.ports.append(Port(
                name=p.declarator.name.valueText,
                direction=p.header.direction.valueText,
                type=str(p.header.dataType).strip(),
                doc=_trailing_doc(next_node),
            ))

    return doc
