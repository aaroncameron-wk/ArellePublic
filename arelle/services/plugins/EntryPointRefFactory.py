"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Any

from arelle.services.plugins.EntryPointRef import EntryPointRef


class EntryPointRefFactory(ABC):

    @abstractmethod
    def create_module_info(
        self,
        entry_point_ref: EntryPointRef | None,
        filename: str | None = None,
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def get(self, search: str) -> EntryPointRef | None:
        pass
