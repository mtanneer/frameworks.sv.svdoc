"""Doc IR (v1): module-level only. See PLAN.md Phase 1."""

from dataclasses import dataclass, field
from typing import Optional


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
    default: str | None
    doc: str | None
    type_ref: str | None = None


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
    doc: str | None
    type_ref: str | None = None
    modport_preview: Optional["Modport"] = None


@dataclass
class ModuleDoc:
    """Doc IR for a single SystemVerilog module."""

    name: str
    doc: str | None
    params: list[Param] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)


@dataclass
class Signal:
    """A variable declared in an interface body (outside any modport)."""

    name: str
    type: str
    doc: str | None


@dataclass
class ModportPortGroup:
    """One direction-grouped clause within a modport, e.g. ``output valid, data``."""

    direction: str
    signals: list[str]
    doc: str | None


@dataclass
class Modport:
    """A single ``modport`` declaration inside an interface."""

    name: str
    doc: str | None
    port_groups: list[ModportPortGroup] = field(default_factory=list)


@dataclass
class InterfaceDoc:
    """Doc IR for a single SystemVerilog interface, including its modports."""

    name: str
    doc: str | None
    params: list[Param] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    modports: list[Modport] = field(default_factory=list)


@dataclass
class EnumValue:
    """A single named value within an ``enum`` typedef."""

    name: str
    value: str | None
    doc: str | None


@dataclass
class StructField:
    """A single field within a packed ``struct`` typedef."""

    name: str
    type: str
    doc: str | None


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
    doc: str | None
    kind: str
    base_type: str | None = None
    alias_type: str | None = None
    values: list[EnumValue] = field(default_factory=list)
    fields: list[StructField] = field(default_factory=list)


@dataclass
class Subroutine:
    """A ``function`` or ``task`` declared in a package.

    :ivar kind: ``"function"`` or ``"task"``.
    :ivar return_type: Declared return type; always ``None`` for tasks.
    :ivar args: Arguments, reusing :class:`Port`'s name/direction/type/doc shape.
    """

    name: str
    doc: str | None
    kind: str
    return_type: str | None = None
    args: list[Port] = field(default_factory=list)


@dataclass
class PackageDoc:
    """Doc IR for a single SystemVerilog package: its typedefs and subroutines."""

    name: str
    doc: str | None
    typedefs: list[Typedef] = field(default_factory=list)
    subroutines: list[Subroutine] = field(default_factory=list)


@dataclass
class ParamValue:
    """A single parameter's resolved (post-override) value on one instance."""

    name: str
    value: str


@dataclass
class PortConnection:
    """A single port's connected expression on one instance.

    :ivar expr: Connected expression text, for plain data-type ports.
        ``None`` for interface-typed ports (see ``interface_instance``/
        ``modport`` instead) or unconnected ports.
    :ivar interface_instance: For an interface-typed port, the name of the
        sibling interface instance it's bound to (e.g. ``"hs"``); ``None``
        for plain data-type ports.
    :ivar modport: For an interface-typed port, the modport name used
        (e.g. ``"producer"``); ``None`` for plain data-type ports.
    """

    name: str
    expr: str | None
    interface_instance: str | None = None
    modport: str | None = None


@dataclass
class Instance:
    """One elaborated instance in a module hierarchy.

    :ivar path: Full hierarchical path (e.g. ``"top.g[0].u_leaf2"``), unique
        within the hierarchy even under generate-block array expansion.
    :ivar name: Instance name as written (e.g. ``"u_leaf2"``).
    :ivar module: Name of the module/interface definition being instantiated.
    :ivar params: Resolved parameter values (post any ``#(...)`` overrides).
    :ivar connections: Port name -> connected expression, in port-list order.
    :ivar children: Instances directly nested inside this one.
    :ivar is_interface: ``True`` if this instance is of an ``interface``
        definition rather than a ``module``.
    """

    path: str
    name: str
    module: str
    params: list[ParamValue] = field(default_factory=list)
    connections: list[PortConnection] = field(default_factory=list)
    children: list["Instance"] = field(default_factory=list)
    is_interface: bool = False
