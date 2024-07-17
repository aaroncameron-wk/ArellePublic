"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import EntryPoint
from typing import Any


@dataclass
class EntryPointRef:
    aliases: set[str]
    entryPoint: EntryPoint | None
    moduleFilename: str | None
    moduleInfo: dict[str, Any] | None
