"""
See COPYRIGHT.md for copyright information.
"""
from dataclasses import dataclass
from importlib.metadata import EntryPoint


@dataclass
class EntryPointRef:
    aliases: set[str]
    entryPoint: EntryPoint | None
    moduleFilename: str | None
    moduleInfo: dict | None
