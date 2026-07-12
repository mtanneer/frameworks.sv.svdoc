"""Doc IR (v1): module-level only. See PLAN.md Phase 1."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Param:
    """A single module/interface/subroutine parameter.

    :ivar name: Parameter identifier.
    :ivar type: Declared type as written in source (e.g. ``"int"``).
    :ivar default: Default value expression, or ``None`` if unset.
    :ivar doc: Extracted doc comment, or ``None`` if undocumented.
    :ivar type_ref: Fully-qualified ``"package::type"`` name if resolved
        cross-file via :func:`svdoc.parser.resolve_types`; ``None`` otherwise.
    """

    name: str
    type: str
    default: Optional[str]
    doc: Optional[str]
    type_ref: Optional[str] = None


@dataclass
class Port:
    """A single module/interface/subroutine port or argument.

    Also reused for subroutine arguments (see :attr:`Subroutine.args`), since
    the shape (name, direction, type, doc) is identical.

    :ivar name: Port identifier.
    :ivar direction: ``"input"``, ``"output"``, ``"inout"``, etc.
    :ivar type: Declared type as written in source, including any packed
        dimensions (e.g. ``"logic [7:0]"``).
    :ivar doc: Extracted doc comment, or ``None`` if undocumented.
    :ivar type_ref: Fully-qualified ``"package::type"`` name if resolved
        cross-file via :func:`svdoc.parser.resolve_types`; ``None`` otherwise.
    :ivar modport_preview: For an interface-typed port (``direction ==
        "interface"``), the resolved :class:`Modport` from the interface file,
        if it was found among the files passed to
        :func:`svdoc.parser.resolve_types`; ``None`` otherwise.
    """

    name: str
    direction: str
    type: str
    doc: Optional[str]
    type_ref: Optional[str] = None
    modport_preview: Optional["Modport"] = None


@dataclass
class ModuleDoc:
    """Doc IR for a single SystemVerilog module."""

    name: str
    doc: Optional[str]
    params: List[Param] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)


@dataclass
class Signal:
    """A variable declared in an interface body (outside any modport)."""

    name: str
    type: str
    doc: Optional[str]


@dataclass
class ModportPortGroup:
    """One direction-grouped clause within a modport, e.g. ``output valid, data``."""

    direction: str
    signals: List[str]
    doc: Optional[str]


@dataclass
class Modport:
    """A single ``modport`` declaration inside an interface."""

    name: str
    doc: Optional[str]
    port_groups: List[ModportPortGroup] = field(default_factory=list)


@dataclass
class InterfaceDoc:
    """Doc IR for a single SystemVerilog interface, including its modports."""

    name: str
    doc: Optional[str]
    params: List[Param] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)
    modports: List[Modport] = field(default_factory=list)


@dataclass
class EnumValue:
    """A single named value within an ``enum`` typedef."""

    name: str
    value: Optional[str]
    doc: Optional[str]


@dataclass
class StructField:
    """A single field within a packed ``struct`` typedef."""

    name: str
    type: str
    doc: Optional[str]


@dataclass
class Typedef:
    """A single ``typedef`` declared in a package: enum, packed struct, or alias.

    :ivar kind: One of ``"enum"``, ``"struct"``, or ``"alias"`` — determines
        which of ``base_type``/``values``, ``fields``, or ``alias_type`` is populated.
    :ivar base_type: For ``kind="enum"``, the underlying integer type
        (e.g. ``"logic [1:0]"``).
    :ivar alias_type: For ``kind="alias"``, the type being aliased.
    :ivar values: For ``kind="enum"``, the enum's named values in declaration order.
    :ivar fields: For ``kind="struct"``, the struct's fields in declaration order.
    """

    name: str
    doc: Optional[str]
    kind: str
    base_type: Optional[str] = None
    alias_type: Optional[str] = None
    values: List[EnumValue] = field(default_factory=list)
    fields: List[StructField] = field(default_factory=list)


@dataclass
class Subroutine:
    """A ``function`` or ``task`` declared in a package.

    :ivar kind: ``"function"`` or ``"task"``.
    :ivar return_type: Declared return type; always ``None`` for tasks.
    :ivar args: Arguments, reusing :class:`Port`'s name/direction/type/doc shape.
    """

    name: str
    doc: Optional[str]
    kind: str
    return_type: Optional[str] = None
    args: List[Port] = field(default_factory=list)


@dataclass
class PackageDoc:
    """Doc IR for a single SystemVerilog package: its typedefs and subroutines."""

    name: str
    doc: Optional[str]
    typedefs: List[Typedef] = field(default_factory=list)
    subroutines: List[Subroutine] = field(default_factory=list)
