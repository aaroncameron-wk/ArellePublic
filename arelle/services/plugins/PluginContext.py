"""
See COPYRIGHT.md for copyright information.
"""
from abc import ABC, abstractmethod
from importlib.metadata import EntryPoint
from typing import Any, Iterator, Callable


class PluginContext(ABC):

    @abstractmethod
    def add_plugin_module(self, name: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def generate_module_info(
            self,
            moduleURL: str | None = None,
            entryPoint: EntryPoint | None = None,
            reload: bool = False,
            parentImportsSubtree: bool = False,
    ) -> dict | None:
        pass

    @abstractmethod
    def get_controller(self):
        pass

    @abstractmethod
    def get_plugin_base(self):
        pass

    @abstractmethod
    def init(self, loadPluginConfig: bool = True) -> None:
        pass

    @abstractmethod
    def modules_with_newer_file_dates(self):
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
    ) -> dict | None:
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
    def save(self, cntlr) -> None:
        pass
