"""
See COPYRIGHT.md for copyright information.
"""
from abc import abstractmethod, ABC

from arelle.services.plugins.EntryPointRef import EntryPointRef


class EntryPointRefFactory(ABC):

    @abstractmethod
    def create_module_info(self, entry_point_ref: EntryPointRef | None, filename: str | None = None) -> dict | None:
        pass

    @abstractmethod
    def get(self, search: str) -> EntryPointRef | None:
        pass
