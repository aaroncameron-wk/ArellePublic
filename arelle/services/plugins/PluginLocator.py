"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from abc import abstractmethod, ABC

from arelle.services.plugins.EntryPointRef import EntryPointRef


class PluginLocator(ABC):

    @abstractmethod
    def get(self, plugin_base: str, search: str) -> EntryPointRef | None:
        pass

    @abstractmethod
    def normalize_module_filename(self, moduleFilename: str) -> str | None:
        pass
