"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from abc import abstractmethod, ABC
from importlib.metadata import EntryPoint
from typing import Any


class PluginParser(ABC):

    @abstractmethod
    def parse_plugin_info(
            self,
            moduleURL: str,
            moduleFilename: str,
            entryPoint: EntryPoint | None,
    ) -> dict[str, Any] | None:
        pass
