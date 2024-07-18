"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import EntryPoint
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from .Cntlr import Cntlr

_GLOBAL_PLUGIN_CONTEXT = None


def addPluginModule(name: str) -> dict[str, Any] | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.add_plugin_module(name)


def close():  # close all loaded methods
    if _GLOBAL_PLUGIN_CONTEXT is not None:
        return _GLOBAL_PLUGIN_CONTEXT.close()


def init(cntlr: Cntlr, loadPluginConfig: bool = True) -> None:
    global _GLOBAL_PLUGIN_CONTEXT
    from .core.plugins.CorePluginContext import CorePluginContext
    from .core.plugins.CorePluginLocator import CorePluginLocator
    from .core.plugins.CorePluginParser import CorePluginParser
    plugin_parser = CorePluginParser(cntlr)
    plugin_locator = CorePluginLocator(cntlr, plugin_parser)
    _GLOBAL_PLUGIN_CONTEXT = CorePluginContext(cntlr, plugin_locator, plugin_parser)
    _GLOBAL_PLUGIN_CONTEXT.init(loadPluginConfig)


def moduleModuleInfo(
        moduleURL: str | None = None,
        entryPoint: EntryPoint | None = None,
        reload: bool = False,
        parentImportsSubtree: bool = False,
) -> dict | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.generate_module_info(moduleURL, entryPoint, reload, parentImportsSubtree)


def modulesWithNewerFileDates():
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.modules_with_newer_file_dates()


def pluginClassMethods(className: str) -> Iterator[Callable[..., Any]]:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    for pluginClassMethod in _GLOBAL_PLUGIN_CONTEXT.plugin_class_methods(className):
        yield pluginClassMethod


def reloadPluginModule(name):
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.reload_plugin_module(name)


def removePluginModule(name):
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.remove_plugin_module(name)


def reset() -> None:  # force reloading modules and plugin infos
    if _GLOBAL_PLUGIN_CONTEXT is not None:
        _GLOBAL_PLUGIN_CONTEXT.reset()


def save(cntlr: Cntlr) -> None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.save(cntlr)


def getContext():
    return _GLOBAL_PLUGIN_CONTEXT
