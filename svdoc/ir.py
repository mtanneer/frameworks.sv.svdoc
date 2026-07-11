"""Doc IR (v1): module-level only. See PLAN.md Phase 1."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Param:
    name: str
    type: str
    default: Optional[str]
    doc: Optional[str]


@dataclass
class Port:
    name: str
    direction: str
    type: str
    doc: Optional[str]


@dataclass
class ModuleDoc:
    name: str
    doc: Optional[str]
    params: List[Param] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)
