"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from importlib.metadata import EntryPoint
from typing import Any, Iterator, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from arelle.Cntlr import Cntlr



class PluginContext(ABC):

    @abstractmethod
    def add_plugin_module(self, name: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def generate_module_info(
            self,
            moduleURL: str | None = None,
            entryPoint: EntryPoint | None = None,
            reload: bool = False,
            parentImportsSubtree: bool = False,
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def get_controller(self) -> Cntlr:
        pass

    @abstractmethod
    def get_plugin_base(self) -> str:
        pass

    @abstractmethod
    def init(self, loadPluginConfig: bool = True) -> None:
        pass

    @abstractmethod
    def modules_with_newer_file_dates(self) -> list[str]:
        pass

    @abstractmethod
    def normalize_module_filename(self, moduleFilename: str) -> str | None:
        pass

    @abstractmethod
    def parse_plugin_info(
            self,
            moduleURL: str,
            moduleFilename: str,
            entryPoint: EntryPoint | None,
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def plugin_class_methods(self, className: str) -> Iterator[Callable[..., Any]]:
        pass

    @abstractmethod
    def reload_plugin_module(self, name: str) -> bool:
        pass

    @abstractmethod
    def remove_plugin_module(self, name: str) -> None:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def save(self, cntlr: Cntlr) -> None:
        pass
