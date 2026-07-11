"""Doc IR (v1): module-level only. See PLAN.md Phase 1."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Param:
    name: str
    type: str
    default: Optional[str]
    doc: Optional[str]
    type_ref: Optional[str] = None  # fully-qualified "package::type" if resolved cross-file


@dataclass
class Port:
    name: str
    direction: str
    type: str
    doc: Optional[str]
    type_ref: Optional[str] = None  # fully-qualified "package::type" if resolved cross-file


@dataclass
class ModuleDoc:
    name: str
    doc: Optional[str]
    params: List[Param] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)


@dataclass
class Signal:
    name: str
    type: str
    doc: Optional[str]


@dataclass
class ModportPortGroup:
    direction: str
    signals: List[str]
    doc: Optional[str]


@dataclass
class Modport:
    name: str
    doc: Optional[str]
    port_groups: List[ModportPortGroup] = field(default_factory=list)


@dataclass
class InterfaceDoc:
    name: str
    doc: Optional[str]
    params: List[Param] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)
    modports: List[Modport] = field(default_factory=list)


@dataclass
class EnumValue:
    name: str
    value: Optional[str]
    doc: Optional[str]


@dataclass
class StructField:
    name: str
    type: str
    doc: Optional[str]


@dataclass
class Typedef:
    name: str
    doc: Optional[str]
    kind: str  # "enum" | "struct" | "alias"
    base_type: Optional[str] = None       # enum: underlying type (e.g. "logic [1:0]")
    alias_type: Optional[str] = None      # alias: the aliased type (e.g. "logic [15:0]")
    values: List[EnumValue] = field(default_factory=list)   # enum only
    fields: List[StructField] = field(default_factory=list)  # struct only


@dataclass
class PackageDoc:
    name: str
    doc: Optional[str]
    typedefs: List[Typedef] = field(default_factory=list)
