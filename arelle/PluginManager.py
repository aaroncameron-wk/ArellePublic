"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import EntryPoint
from typing import TYPE_CHECKING, Any, Iterator

from .PluginContext import PluginContext

if TYPE_CHECKING:
    from .Cntlr import Cntlr

_GLOBAL_PLUGIN_CONTEXT: PluginContext | None = None


def init(cntlr: Cntlr, loadPluginConfig: bool = True) -> None:
    global _GLOBAL_PLUGIN_CONTEXT
    _GLOBAL_PLUGIN_CONTEXT = PluginContext(cntlr)
    _GLOBAL_PLUGIN_CONTEXT.init(loadPluginConfig)


def reset() -> None:  # force reloading modules and plugin infos
    if _GLOBAL_PLUGIN_CONTEXT is not None:
        _GLOBAL_PLUGIN_CONTEXT.reset()


def orderedPluginConfig():
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.ordered_plugin_config()


def save(cntlr: Cntlr) -> None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.save(cntlr)


def close():  # close all loaded methods
    if _GLOBAL_PLUGIN_CONTEXT is not None:
        return _GLOBAL_PLUGIN_CONTEXT.close()


def logPluginTrace(message: str, level: int) -> None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.log_plugin_trace(message, level)


def modulesWithNewerFileDates():
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.modules_with_newer_file_dates()


def freshenModuleInfos():
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.freshen_module_infos()


def normalizeModuleFilename(moduleFilename: str) -> str | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.normalize_module_filename(moduleFilename)


def getModuleFilename(moduleURL: str, reload: bool, normalize: bool, base: str | None) -> tuple[str | None, EntryPoint | None]:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.get_module_filename(moduleURL, reload, normalize, base)


def parsePluginInfo(moduleURL: str, moduleFilename: str, entryPoint: EntryPoint | None) -> dict | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.parse_plugin_info(moduleURL, moduleFilename, entryPoint)


def moduleModuleInfo(
    moduleURL: str | None = None,
    entryPoint: EntryPoint | None = None,
    reload: bool = False,
    parentImportsSubtree: bool = False,
) -> dict | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.module_module_info(moduleURL, entryPoint, reload, parentImportsSubtree)


def moduleInfo(pluginInfo):
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.module_info(pluginInfo)


def loadModule(moduleInfo: dict[str, Any], packagePrefix: str = "") -> None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.load_module(moduleInfo, packagePrefix)


def pluginClassMethods(className: str) -> Iterator[Callable[..., Any]]:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    for pluginClassMethod in _GLOBAL_PLUGIN_CONTEXT.plugin_class_methods(className):
        yield pluginClassMethod


def addPluginModule(name: str) -> dict[str, Any] | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.add_plugin_module(name)


def reloadPluginModule(name):
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.reload_plugin_module(name)


def removePluginModule(name):
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.remove_plugin_module(name)


def addPluginModuleInfo(plugin_module_info: dict[str, Any]) -> dict[str, Any] | None:
    assert _GLOBAL_PLUGIN_CONTEXT is not None
    return _GLOBAL_PLUGIN_CONTEXT.add_plugin_module_info(plugin_module_info)
