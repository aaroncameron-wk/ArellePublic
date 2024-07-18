"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

import ast
import os
import time
from collections import defaultdict
from importlib.metadata import EntryPoint
from typing import Any, TYPE_CHECKING

from arelle import FileSource
from arelle.services.plugins.PluginParser import PluginParser

if TYPE_CHECKING:
    from arelle.Cntlr import Cntlr


class CorePluginParser(PluginParser):

    def __init__(self, controller: Cntlr):
        self._controller = controller

    def parse_plugin_info(
        self,
        moduleURL: str,
        moduleFilename: str,
        entryPoint: EntryPoint | None,
    ) -> dict[str, Any] | None:
        moduleDir, moduleName = os.path.split(moduleFilename)
        f = FileSource.openFileStream(self._controller, moduleFilename)
        tree = ast.parse(f.read(), filename=moduleFilename)
        constantStrings = {}
        functionDefNames = set()
        methodDefNamesByClass = defaultdict(set)
        moduleImports = []
        moduleInfo = {"name": None}
        isPlugin = False
        for item in tree.body:
            if isinstance(item, ast.Assign):
                attr = item.targets[0].id
                if attr == "__pluginInfo__":
                    isPlugin = True
                    f.close()
                    classMethods = []
                    importURLs = []
                    for i, key in enumerate(item.value.keys):
                        _key = key.value
                        _value = item.value.values[i]
                        _valueType = _value.__class__.__name__
                        if _key == "import":
                            if _valueType == 'Constant':
                                importURLs.append(_value.value)
                            elif _valueType in ("List", "Tuple"):
                                for elt in _value.elts:
                                    importURLs.append(elt.value)
                        elif _valueType == 'Constant':
                            moduleInfo[_key] = _value.value
                        elif _valueType == 'Name':
                            if _value.id in constantStrings:
                                moduleInfo[_key] = constantStrings[_value.id]
                            elif _value.id in functionDefNames:
                                classMethods.append(_key)
                        elif _valueType == 'Attribute':
                            if _value.attr in methodDefNamesByClass[_value.value.id]:
                                classMethods.append(_key)
                        elif _valueType in ("List", "Tuple"):
                            values = [elt.value for elt in _value.elts]
                            if _key == "imports":
                                importURLs = values
                            else:
                                moduleInfo[_key] = values

                    moduleInfo['classMethods'] = classMethods
                    moduleInfo['importURLs'] = importURLs
                    moduleInfo["moduleURL"] = moduleURL
                    moduleInfo["path"] = moduleFilename
                    moduleInfo["status"] = 'enabled'
                    moduleInfo["fileDate"] = time.strftime('%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(moduleFilename)))
                    if entryPoint:
                        moduleInfo["moduleURL"] = moduleFilename  # pip-installed plugins need absolute filepath
                        moduleInfo["entryPoint"] = {
                            "module": getattr(entryPoint, 'module', None),  # TODO: Simplify after Python 3.8 retired
                            "name": entryPoint.name,
                            "version": entryPoint.dist.version if hasattr(entryPoint, 'dist') else None,
                        }
                        if not moduleInfo.get("version"):
                            moduleInfo["version"] = entryPoint.dist.version  # If no explicit version, retrieve from entry point
                elif isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):  # possible constant used in plugininfo, such as VERSION
                    for assignmentName in item.targets:
                        constantStrings[assignmentName.id] = item.value.value
            elif isinstance(item, ast.ImportFrom):
                if item.level == 1:  # starts with .
                    if item.module is None:  # from . import module1, module2, ...
                        for importee in item.names:
                            if importee.name == '*':  # import all submodules
                                for _file in os.listdir(moduleDir):
                                    if _file != moduleName and os.path.isfile(_file) and _file.endswith(".py"):
                                        moduleImports.append(_file)
                            elif (os.path.isfile(os.path.join(moduleDir, importee.name + ".py"))
                                  and importee.name not in moduleImports):
                                moduleImports.append(importee.name)
                    else:
                        modulePkgs = item.module.split('.')
                        modulePath = os.path.join(*modulePkgs)
                        if (os.path.isfile(os.path.join(moduleDir, modulePath) + ".py")
                                and modulePath not in moduleImports):
                            moduleImports.append(modulePath)
                        for importee in item.names:
                            _importeePfxName = os.path.join(modulePath, importee.name)
                            if (os.path.isfile(os.path.join(moduleDir, _importeePfxName) + ".py")
                                    and _importeePfxName not in moduleImports):
                                moduleImports.append(_importeePfxName)
            elif isinstance(item, ast.FunctionDef):  # possible functionDef used in plugininfo
                functionDefNames.add(item.name)
            elif isinstance(item, ast.ClassDef):  # possible ClassDef used in plugininfo
                for classItem in item.body:
                    if isinstance(classItem, ast.FunctionDef):
                        methodDefNamesByClass[item.name].add(classItem.name)
        moduleInfo["moduleImports"] = moduleImports
        f.close()
        return moduleInfo if isPlugin else None
